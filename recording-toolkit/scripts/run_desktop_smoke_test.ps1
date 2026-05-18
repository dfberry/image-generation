# run_desktop_smoke_test.ps1
# Validates vscode-copilot-chat-test.json plan runs successfully in --dry-run mode.
# Exit 0 on pass, 1 on fail.

$scriptDir = $PSScriptRoot
$planFile   = Join-Path $scriptDir "..\..\recordings\plans\vscode-copilot-chat-test.json"
$runner     = Join-Path $scriptDir "demo_plan_runner.py"

$planFile = [System.IO.Path]::GetFullPath($planFile)
$runner   = [System.IO.Path]::GetFullPath($runner)

if (-not (Test-Path $planFile)) {
    Write-Host "FAIL: Plan file not found: $planFile"
    exit 1
}

if (-not (Test-Path $runner)) {
    Write-Host "FAIL: demo_plan_runner.py not found: $runner"
    exit 1
}

Write-Host "Running dry-run smoke test: vscode-copilot-chat-test.json"
python $runner $planFile --dry-run

if ($LASTEXITCODE -eq 0) {
    Write-Host "PASS: Dry-run completed successfully."
    exit 0
} else {
    Write-Host "FAIL: Dry-run exited with code $LASTEXITCODE."
    exit 1
}
