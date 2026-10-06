param(
    [string[]]$PythonExecutables = @('C:\Python314\python.exe', 'C:\Python313\python.exe')
)
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
Push-Location $repository
try {
    & uv run --locked ruff check scripts/evaluate_phase6_live.py scripts/evaluate_phase6a_live.py scripts/phase6_journal.py scripts/phase6_monitor.py scripts/phase6_cleanup.py scripts/phase6a_results.py scripts/audit_phase6_provenance.py
    if ($LASTEXITCODE -ne 0) { throw 'Phase-6 live helper lint failed' }
    & uv run --locked ruff format --check scripts/evaluate_phase6_live.py scripts/evaluate_phase6a_live.py scripts/phase6_journal.py scripts/phase6_monitor.py scripts/phase6_cleanup.py scripts/phase6a_results.py scripts/audit_phase6_provenance.py
    if ($LASTEXITCODE -ne 0) { throw 'Phase-6 live helper formatting failed' }
    & "$PSScriptRoot/verify_phase5.ps1" -PythonExecutables $PythonExecutables
    if ($LASTEXITCODE -ne 0) { throw 'Phase-0–6 verification failed' }
} finally {
    Pop-Location
}
