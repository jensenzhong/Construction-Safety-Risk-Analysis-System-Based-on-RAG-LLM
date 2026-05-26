$ErrorActionPreference = "Stop"

Write-Host "[1/4] Checking DeepSeek environment variables..."
if (-not $env:DEEPSEEK_API_KEY) {
    Write-Error "Missing DEEPSEEK_API_KEY. Please set your DeepSeek API key before running verification."
    exit 1
}

if (-not $env:DEEPSEEK_BASE_URL) {
    $env:DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
}
if (-not $env:DEEPSEEK_MODEL) {
    $env:DEEPSEEK_MODEL = "deepseek-chat"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python executable not found in PATH."
    exit 1
}

New-Item -ItemType Directory -Path results -Force | Out-Null

Write-Host "[2/4] Running small-batch structured extraction..."
python main.py `
    --input-csv "Injury Severity.CSV" `
    --text-col "abstract" `
    --output-path "results/extraction_smoke.jsonl" `
    --max-rows 3 `
    --retry-count 1 `
    --sleep-seconds 0.2

Write-Host "[3/4] Running synthetic PSM analysis..."
python -m analysis.causal_psm `
    --output-dir "results" `
    --n-samples 4000 `
    --caliper 0.08 `
    --bootstrap 80 `
    --seed 42

Write-Host "[4/4] Validating expected result files..."
$requiredFiles = @(
    "results/extraction_smoke.jsonl",
    "results/psm_matched_sample.csv",
    "results/psm_effect_summary.json",
    "results/psm_report.md"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Error "Missing output artifact: $file"
        exit 1
    }
}

Write-Host "Verification passed. All required artifacts are generated."
