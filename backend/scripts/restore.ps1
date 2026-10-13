param(
  [Parameter(Mandatory=$true)][string]$DumpFile,
  [Parameter(Mandatory=$true)][string]$TargetDatabase
)
# Restore requires an explicit target schema and confirms it interactively.
$ErrorActionPreference = "Stop"
$py = Get-Command python -ErrorAction SilentlyContinue
$scriptArgs = @("restore", $DumpFile, "--target-database", $TargetDatabase)
if ($py) {
    & $py.Source (Join-Path $PSScriptRoot "db_backup.py") @scriptArgs
} else {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if (-not $py) { throw "Python 3 was not found on PATH." }
    & $py.Source -3 (Join-Path $PSScriptRoot "db_backup.py") @scriptArgs
}
if ($LASTEXITCODE -ne 0) { throw "Restore failed (exit $LASTEXITCODE)." }
