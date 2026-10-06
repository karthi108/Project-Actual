param(
    [string[]]$PythonExecutables = @('C:\Python314\python.exe', 'C:\Python313\python.exe')
)
$ErrorActionPreference = 'Stop'
$actualProfileProject = Split-Path -Parent $PSScriptRoot
Push-Location $actualProfileProject
try {
    & "$PSScriptRoot/verify_phase6.ps1" -PythonExecutables $PythonExecutables
    if ($LASTEXITCODE -ne 0) { throw 'Phase-7 full regression failed' }
    & uv run --offline --locked ruff check scripts/verify_phase7_profile.py
    if ($LASTEXITCODE -ne 0) { throw 'Profile replay lint failed' }
    & uv run --offline --locked ruff format --check scripts/verify_phase7_profile.py
    if ($LASTEXITCODE -ne 0) { throw 'Profile replay formatting failed' }
    & uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-profile-env-v1.json
    if ($LASTEXITCODE -ne 0) { throw 'CareerLab integrity failed' }
    $actualReplayOutput = & uv run --offline --locked python scripts/verify_phase7_profile.py
    if ($LASTEXITCODE -ne 0) { throw 'Profile replay acceptance failed' }
    $actualReplay = $actualReplayOutput | ConvertFrom-Json
    $actualReplay | Select-Object schema_version, verdict, provider_double_calls, profile_and_job_unchanged, exact_projection_checks, deterministic_selection_matches | ConvertTo-Json -Compress
} finally {
    Pop-Location
}
