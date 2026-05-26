#!/bin/bash
set -euo pipefail

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "Missing DEEPSEEK_API_KEY. Please export your DeepSeek API key first." >&2
  exit 1
fi

export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"

INPUT_CSV="${1:-Injury Severity.CSV}"
OUTPUT_PATH="${2:-results/extraction_results.jsonl}"

python main.py \
  --input-csv "$INPUT_CSV" \
  --text-col "abstract" \
  --output-path "$OUTPUT_PATH"

echo "Structured extraction completed: $OUTPUT_PATH"
