param(
    [switch]$Reload
)

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    Write-Error "Missing backend virtual environment. Run: python -m venv .venv"
    exit 1
}

if ($Reload) {
    $env:WATCHFILES_FORCE_POLLING = "true"
    Write-Output "Starting backend with reload + WATCHFILES_FORCE_POLLING=true..."
    & ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload
    exit $LASTEXITCODE
}

Write-Output "Starting backend in stable mode (no --reload)..."
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app
exit $LASTEXITCODE
