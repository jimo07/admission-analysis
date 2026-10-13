param([string]$Database = "sfb_test", [string]$OutDir = "")
# Cross-platform Python helper handles credentials and MySQL client discovery.
$ErrorActionPreference = "Stop"
$py = Get-Command python -ErrorAction SilentlyContinue
$scriptArgs = @("backup")
if ($Database) { $scriptArgs += @("--database", $Database) }
if ($OutDir) { $scriptArgs += @("--out-dir", $OutDir) }
if ($py) {
    & $py.Source (Join-Path $PSScriptRoot "db_backup.py") @scriptArgs
} else {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if (-not $py) { throw "Python 3 was not found on PATH." }
    & $py.Source -3 (Join-Path $PSScriptRoot "db_backup.py") @scriptArgs
}
if ($LASTEXITCODE -ne 0) { throw "Backup failed (exit $LASTEXITCODE)." }
