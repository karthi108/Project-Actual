[CmdletBinding()]
param(
    [string[]] $PythonExecutables = @('C:\Python314\python.exe', 'C:\Python313\python.exe')
)

$ErrorActionPreference = 'Stop'
uv run --locked ruff check scripts/verify_phase5_live.py
if ($LASTEXITCODE -ne 0) { throw 'Live verification script lint failed' }
uv run --locked ruff format --check scripts/verify_phase5_live.py
if ($LASTEXITCODE -ne 0) { throw 'Live verification script formatting failed' }
# Current testpaths include deterministic model tests, never a large live inference.
& (Join-Path $PSScriptRoot 'verify_phase3.ps1') -PythonExecutables $PythonExecutables
