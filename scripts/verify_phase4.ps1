[CmdletBinding()]
param(
    [string[]] $PythonExecutables = @('C:\Python314\python.exe', 'C:\Python313\python.exe')
)

$ErrorActionPreference = 'Stop'
# The accepted disposable-PostgreSQL harness runs the current complete testpaths
# and static checks. Reuse its resource isolation, secret handling and cleanup.
& (Join-Path $PSScriptRoot 'verify_phase3.ps1') -PythonExecutables $PythonExecutables
