import argparse
import json
from pathlib import Path
import time

import pandas as pd

from llm.client import chat, resolve_deepseek_config
from rag.extraction_schema import parse_and_validate_response

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(iterable, **_kwargs):
        return iterable


def build_extraction_prompt(incident_text: str) -> str:
    return f"""
You are a construction safety analysis assistant.
Convert the incident narrative into structured management insights.

Rules:
- Return strict JSON only. No markdown, no code fences.
- severity_level must be an integer in [1, 2, 3, 4].
- core_hazards should be short hazard tags (e.g., "fall from height", "machine entanglement").
- management_gaps should describe management/process deficiencies.
- improvement_actions should be actionable and concise.
- confidence must be a float between 0 and 1.
- reasoning_summary should be 1-3 short sentences.

Output JSON keys:
severity_level, core_hazards, management_gaps, improvement_actions, confidence, reasoning_summary

Incident text:
{incident_text}
""".strip()


def _default_failed_record(error_text: str) -> dict:
    return {
        "severity_level": None,
        "core_hazards": [],
        "management_gaps": [],
        "improvement_actions": [],
        "confidence": None,
        "reasoning_summary": "",
        "parse_error": error_text,
    }


def extract_structured_fields(
    incident_text: str,
    model: str,
    base_url: str,
    retry_count: int = 1,
    sleep_seconds: float = 0.0,
) -> dict:
    prompt = build_extraction_prompt(incident_text)
    last_error = "unknown"
    last_response = ""

    for attempt in range(retry_count + 1):
        response = chat(
            prompt=prompt,
            model=model,
            base_url=base_url,
            temperature=0.0,
            max_tokens=600,
        )
        last_response = response
        try:
            parsed = parse_and_validate_response(response, require_citations=False)
            parsed["parse_error"] = ""
            parsed["raw_response"] = response
            return parsed
        except Exception as exc:
            last_error = str(exc)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            if attempt == retry_count:
                failed = _default_failed_record(last_error)
                failed["raw_response"] = last_response
                return failed

    failed = _default_failed_record(last_error)
    failed["raw_response"] = last_response
    return failed


def write_output(records: list, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()

    if suffix == ".jsonl":
        with output_path.open("w", encoding="utf-8") as f:
            for row in records:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return

    if suffix == ".csv":
        pd.DataFrame(records).to_csv(output_path, index=False)
        return

    if suffix == ".json":
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return

    raise ValueError("Unsupported output extension. Use .jsonl, .csv, or .json")


def parse_args():
    parser = argparse.ArgumentParser(description="Batch structured extraction with DeepSeek API")
    parser.add_argument("--input-csv", default="Injury Severity.CSV", help="Input CSV path")
    parser.add_argument("--text-col", default="abstract", help="Text column name to analyze")
    parser.add_argument(
        "--output-path",
        default="results/extraction_results.jsonl",
        help="Output path (.jsonl/.csv/.json)",
    )
    parser.add_argument("--model", default=None, help="Model name (default from DEEPSEEK_MODEL or deepseek-chat)")
    parser.add_argument("--base-url", default=None, help="DeepSeek base URL override")
    parser.add_argument("--max-rows", type=int, default=0, help="Limit rows for quick tests (0 means all)")
    parser.add_argument("--retry-count", type=int, default=1, help="Retry count for non-JSON output")
    parser.add_argument("--sleep-seconds", type=float, default=0.0, help="Sleep between retries")
    return parser.parse_args()


def main():
    args = parse_args()
    resolved_model, _, resolved_base_url = resolve_deepseek_config(
        model=args.model,
        base_url=args.base_url,
    )

    input_path = Path(args.input_csv)
    output_path = Path(args.output_path)
    df = pd.read_csv(input_path)

    if args.text_col not in df.columns:
        raise ValueError(f"Column '{args.text_col}' not found in {input_path}")

    if args.max_rows and args.max_rows > 0:
        df = df.head(args.max_rows).copy()

    records = []
    parse_errors = 0
    iterator = tqdm(df.itertuples(index=True), total=len(df), desc="Extracting")
    for row in iterator:
        row_index = int(row.Index)
        text_value = getattr(row, args.text_col)
        text = "" if pd.isna(text_value) else str(text_value).strip()

        if not text:
            parsed = _default_failed_record("empty text")
            parsed["raw_response"] = ""
            parse_errors += 1
        else:
            parsed = extract_structured_fields(
                incident_text=text,
                model=resolved_model,
                base_url=resolved_base_url,
                retry_count=args.retry_count,
                sleep_seconds=args.sleep_seconds,
            )
            if parsed.get("parse_error"):
                parse_errors += 1

        record = {
            "row_index": row_index,
            "text_col": args.text_col,
            "input_text": text,
        }
        record.update(parsed)
        records.append(record)

    write_output(records, output_path)
    print(f"Processed rows: {len(records)}")
    print(f"Parse errors: {parse_errors}")
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    main()
