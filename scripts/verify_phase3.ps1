[CmdletBinding()]
param(
    [string[]] $PythonExecutables = @('C:\Python314\python.exe', 'C:\Python313\python.exe')
)

$ErrorActionPreference = 'Stop'
$actualProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$actualPreviousLocation = Get-Location
$actualPriorTestUrl = [Environment]::GetEnvironmentVariable('ACTUAL_TEST_DATABASE_URL')
$actualRunIdentity = [Guid]::NewGuid().ToString('N')
$actualContainerName = "actual-phase3-test-$actualRunIdentity"
$actualContainerId = $null
$actualSecretPath = [System.IO.Path]::GetFullPath((Join-Path $actualProjectRoot ".env.phase3-$actualRunIdentity"))
$actualImage = 'postgres@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722'

function Invoke-ActualCheck {
    param([string] $Command, [string[]] $Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Phase-3 verification command failed: $Command" }
}

try {
    Set-Location -LiteralPath $actualProjectRoot
    if (-not $actualSecretPath.StartsWith($actualProjectRoot + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Unsafe private test configuration path'
    }
    if ($PythonExecutables.Count -eq 0) { throw 'At least one installed Python interpreter is required' }
    foreach ($actualPython in $PythonExecutables) {
        if (-not (Test-Path -LiteralPath $actualPython -PathType Leaf)) {
            throw 'An explicitly selected Python interpreter is unavailable'
        }
    }
    $actualSecret = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N')
    [System.IO.File]::WriteAllText(
        $actualSecretPath,
        "POSTGRES_USER=actual_test_owner`nPOSTGRES_PASSWORD=$actualSecret`nPOSTGRES_DB=actual_phase3_test`nPOSTGRES_INITDB_ARGS=--auth-host=scram-sha-256`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    & docker run --detach --rm --name $actualContainerName --label "actual.phase3.test=$actualRunIdentity" --env-file $actualSecretPath --tmpfs /var/lib/postgresql:rw,size=512m --publish 127.0.0.1::5432 $actualImage | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Isolated PostgreSQL startup failed' }
    $actualContainerId = (& docker inspect --format '{{.Id}}' $actualContainerName).Trim()
    if ($LASTEXITCODE -ne 0 -or $actualContainerId -notmatch '^[0-9a-f]{64}$') { throw 'Could not identify the created test container' }
    $actualReady = $false
    for ($actualAttempt = 0; $actualAttempt -lt 40; $actualAttempt++) {
        & docker exec $actualContainerId pg_isready -U actual_test_owner -d actual_phase3_test 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $actualReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $actualReady) { throw 'Isolated PostgreSQL did not become ready' }
    $actualPort = (& docker port $actualContainerId 5432/tcp).Trim()
    if ($LASTEXITCODE -ne 0 -or $actualPort -notmatch '^127\.0\.0\.1:([0-9]+)$') { throw 'Test database is not bound only to loopback' }
    $actualPortNumber = $Matches[1]
    $env:ACTUAL_TEST_DATABASE_URL = "postgresql+psycopg://actual_test_owner:$actualSecret@127.0.0.1:$actualPortNumber/actual_phase3_test"
    Write-Output 'Isolated PostgreSQL is ready; credentials are not printed.'
    Invoke-ActualCheck -Command uv -Arguments @('run', '--locked', 'ruff', 'check', 'src', 'tests', 'migrations')
    Invoke-ActualCheck -Command uv -Arguments @('run', '--locked', 'ruff', 'format', '--check', 'src', 'tests', 'migrations')
    Invoke-ActualCheck -Command uv -Arguments @('run', '--locked', 'mypy')
    for ($actualIndex = 0; $actualIndex -lt $PythonExecutables.Count; $actualIndex++) {
        $actualTemp = [System.IO.Path]::GetFullPath((Join-Path $actualProjectRoot ".pytest-tmp-careerlab-phase3-$actualIndex"))
        if (-not $actualTemp.StartsWith($actualProjectRoot + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe pytest temporary directory' }
        Write-Output "Checking installed interpreter $($PythonExecutables[$actualIndex])"
        Invoke-ActualCheck -Command uv -Arguments @('run', '--isolated', '--python', $PythonExecutables[$actualIndex], '--locked', 'pytest', '-q', '--tb=short', "--basetemp=$actualTemp")
    }
}
finally {
    if ($null -ne $actualContainerId) {
        $actualLabels = & docker inspect --format '{{json .Config.Labels}}' $actualContainerId 2>$null
        if ($LASTEXITCODE -eq 0 -and ($actualLabels | ConvertFrom-Json).'actual.phase3.test' -eq $actualRunIdentity) {
            & docker rm --force --volumes $actualContainerId | Out-Null
        }
    }
    if (Test-Path -LiteralPath $actualSecretPath -PathType Leaf) {
        if (-not $actualSecretPath.StartsWith($actualProjectRoot + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe credential cleanup path' }
        Remove-Item -LiteralPath $actualSecretPath
    }
    [Environment]::SetEnvironmentVariable('ACTUAL_TEST_DATABASE_URL', $actualPriorTestUrl)
    Set-Location -LiteralPath $actualPreviousLocation.Path
}
