import json
from typing import Dict, List, Optional


BASE_REQUIRED_KEYS = [
    "severity_level",
    "core_hazards",
    "management_gaps",
    "improvement_actions",
]

PRE_ASSESS_REQUIRED_KEYS = [
    "risk_level",
    "potential_hazards",
    "preventive_measures",
    "required_ppe",
]


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2:
            cleaned = "\n".join(lines[1:])
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    return cleaned.strip()


def parse_json_response(response_text: str) -> Dict:
    cleaned = _strip_code_fences(response_text)
    return json.loads(cleaned)


def _coerce_string_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        return [text]
    return [str(value).strip()]


def _coerce_severity(value) -> Optional[int]:
    try:
        sev = int(value)
    except Exception:
        return None
    if 1 <= sev <= 4:
        return sev
    return None


def _coerce_citations(data: Dict, allowed_case_ids: List[int] = None) -> List[int]:
    citations = []
    for item in data.get("citations", []):
        try:
            cid = int(item)
        except Exception:
            continue
        citations.append(cid)
    if allowed_case_ids is not None:
        allow = set(int(x) for x in allowed_case_ids)
        citations = [cid for cid in citations if cid in allow]
    return citations


def normalize_extraction_payload(data: Dict, allowed_case_ids: List[int] = None) -> Dict:
    severity = _coerce_severity(data.get("severity_level", data.get("severity")))
    citations = _coerce_citations(data, allowed_case_ids)

    confidence = data.get("confidence")
    try:
        if confidence is not None:
            confidence = float(confidence)
            if confidence < 0 or confidence > 1:
                confidence = None
    except Exception:
        confidence = None

    rationale = data.get("rationale", "")
    reasoning_summary = data.get("reasoning_summary", rationale)

    normalized = {
        "severity_level": severity,
        "core_hazards": _coerce_string_list(data.get("core_hazards")),
        "management_gaps": _coerce_string_list(data.get("management_gaps")),
        "improvement_actions": _coerce_string_list(data.get("improvement_actions")),
        "targeted_actions": _coerce_string_list(data.get("targeted_actions")),
        "citations": citations,
        "confidence": confidence,
        "rationale": str(rationale).strip(),
        "reasoning_summary": str(reasoning_summary).strip(),
    }
    return normalized


def validate_extraction_payload(payload: Dict, require_citations: bool = False) -> List[str]:
    errors: List[str] = []
    for key in BASE_REQUIRED_KEYS:
        if key not in payload:
            errors.append(f"missing key: {key}")

    if payload.get("severity_level") is None:
        errors.append("severity_level must be an int in [1, 4]")

    for key in ["core_hazards", "management_gaps", "improvement_actions"]:
        if not isinstance(payload.get(key), list):
            errors.append(f"{key} must be a list of strings")

    if require_citations:
        citations = payload.get("citations", [])
        if not citations:
            errors.append("citations must be non-empty for RAG responses")
        elif not all(isinstance(cid, int) for cid in citations):
            errors.append("citations must contain integer case ids")

    return errors


def parse_and_validate_response(
    response_text: str,
    require_citations: bool = False,
    allowed_case_ids: List[int] = None,
) -> Dict:
    data = parse_json_response(response_text)
    normalized = normalize_extraction_payload(data, allowed_case_ids=allowed_case_ids)
    errors = validate_extraction_payload(normalized, require_citations=require_citations)
    if errors:
        raise ValueError("; ".join(errors))
    return normalized


# ─── Pre-assessment schema ───

def normalize_pre_assessment_payload(data: Dict, allowed_case_ids: List[int] = None) -> Dict:
    risk_level = _coerce_severity(data.get("risk_level"))
    citations = _coerce_citations(data, allowed_case_ids)
    rationale = data.get("rationale", "")

    return {
        "risk_level": risk_level,
        "potential_hazards": _coerce_string_list(data.get("potential_hazards")),
        "preventive_measures": _coerce_string_list(data.get("preventive_measures")),
        "required_ppe": _coerce_string_list(data.get("required_ppe")),
        "citations": citations,
        "rationale": str(rationale).strip(),
    }


def validate_pre_assessment_payload(payload: Dict, require_citations: bool = False) -> List[str]:
    errors: List[str] = []
    for key in PRE_ASSESS_REQUIRED_KEYS:
        if key not in payload:
            errors.append(f"missing key: {key}")

    if payload.get("risk_level") is None:
        errors.append("risk_level must be an int in [1, 4]")

    for key in ["potential_hazards", "preventive_measures", "required_ppe"]:
        if not isinstance(payload.get(key), list):
            errors.append(f"{key} must be a list of strings")

    if require_citations:
        citations = payload.get("citations", [])
        if not citations:
            errors.append("citations must be non-empty")

    return errors


def parse_and_validate_pre_assessment(
    response_text: str,
    require_citations: bool = False,
    allowed_case_ids: List[int] = None,
) -> Dict:
    data = parse_json_response(response_text)
    normalized = normalize_pre_assessment_payload(data, allowed_case_ids=allowed_case_ids)
    errors = validate_pre_assessment_payload(normalized, require_citations=require_citations)
    if errors:
        raise ValueError("; ".join(errors))
    return normalized
