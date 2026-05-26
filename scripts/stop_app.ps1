$ErrorActionPreference = "Stop"

$targets = @{}

$processes = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "ConstructionSafetyAssistant.exe" -or (
        $_.Name -in @("python.exe", "pythonw.exe", "py.exe") -and
        $_.CommandLine -match "streamlit" -and
        $_.CommandLine -match "app\.py"
    )
}

foreach ($process in $processes) {
    $targets[$process.ProcessId] = $process
}

if ($targets.Count -eq 0) {
    Write-Host "[INFO] No running Construction Safety Assistant process was found."
    exit 0
}

foreach ($process in ($targets.Values | Sort-Object ProcessId)) {
    Write-Host ("[STOP] {0} PID={1}" -f $process.Name, $process.ProcessId)
    Stop-Process -Id $process.ProcessId -Force
}

Write-Host "[DONE] Construction Safety Assistant has been stopped."
