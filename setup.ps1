$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python tools/setup_runtime.py
    if ($LASTEXITCODE -ne 0) { throw 'Setup failed. See output above.' }
} finally {
    Pop-Location
}
