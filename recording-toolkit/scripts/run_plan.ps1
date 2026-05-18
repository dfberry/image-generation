# Recording plan runner — PowerShell wrapper with type routing.
# Desktop plans ("type": "desktop") run natively via Python.
# Terminal plans route to run_plan.sh via WSL (asciinema requires Unix terminal).
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [string]$PlanFile,

    [switch]$DryRun,
    [switch]$NoConvert,
    [string]$Output,
    [string]$Config,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Usage: run_plan.ps1 <plan.json> [options]

Arguments:
  <plan.json>    Path to recording plan JSON file (required)

Options:
  -DryRun        Show what would be executed without recording
  -NoConvert     Skip GIF conversion after recording (terminal plans only)
  -Output        Override output file path
  -Config        Path to recording-config.json
  -Help          Show this help

Plan types:
  "type": "desktop"  — runs natively via Python (demo_plan_runner.py)
  "type": "terminal" — routes to run_plan.sh via WSL (asciinema)

Examples:
  .\run_plan.ps1 recordings\plans\vscode-copilot-demo.json
  .\run_plan.ps1 recordings\plans\vscode-copilot-demo.json -DryRun
  .\run_plan.ps1 recordings\plans\copilot-cli-test.json
"@
    exit 0
}

# --- Resolve plan file path ---
$planFileAbs = [System.IO.Path]::GetFullPath($PlanFile)
if (-not (Test-Path $planFileAbs)) {
    Write-Error "Plan file not found: $planFileAbs"
    exit 1
}

# --- Type routing: read plan type from JSON ---
$planType = "terminal"
try {
    $planContent = Get-Content $planFileAbs -Raw | ConvertFrom-Json
    if ($planContent.type) {
        $planType = $planContent.type
    }
} catch {
    Write-Error "Failed to parse plan JSON: $_"
    exit 1
}

# --- Desktop plans: run natively via Python ---
if ($planType -eq "desktop") {
    $scriptDir = $PSScriptRoot
    $runnerScript = Join-Path $scriptDir "demo_plan_runner.py"

    if (-not (Test-Path $runnerScript)) {
        Write-Error "demo_plan_runner.py not found at: $runnerScript"
        exit 1
    }

    $pythonArgs = @($runnerScript, $planFileAbs)

    if ($DryRun) { $pythonArgs += "--dry-run" }
    if ($Output) { $pythonArgs += "--output"; $pythonArgs += [System.IO.Path]::GetFullPath($Output) }
    if ($Config) { $pythonArgs += "--config"; $pythonArgs += [System.IO.Path]::GetFullPath($Config) }

    Write-Host "Dispatching desktop plan to: python $($pythonArgs -join ' ')"
    python @pythonArgs
    exit $LASTEXITCODE
}

# --- Terminal plans: route to run_plan.sh via WSL ---
if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Error "WSL not found. Terminal plans require WSL. Install: https://learn.microsoft.com/windows/wsl/install"
    exit 1
}

# --- Path translation helper (Windows → WSL /mnt/...) ---
function ConvertTo-WslPath {
    param([string]$WinPath)
    if ([string]::IsNullOrEmpty($WinPath)) { return "" }
    $abs = [System.IO.Path]::GetFullPath($WinPath)
    if ($abs -match '^([A-Za-z]):\\(.*)$') {
        $drive = $Matches[1].ToLower()
        $rest  = $Matches[2] -replace '\\', '/'
        return "/mnt/$drive/$rest"
    }
    return $abs -replace '\\', '/'
}

$scriptDir = $PSScriptRoot
$runPlanSh = Join-Path $scriptDir "run_plan.sh"
if (-not (Test-Path $runPlanSh)) {
    Write-Error "run_plan.sh not found at: $runPlanSh"
    exit 1
}

$wslPlanFile  = ConvertTo-WslPath $planFileAbs
$wslRunPlanSh = ConvertTo-WslPath $runPlanSh

$wslArgs = @("bash", $wslRunPlanSh, $wslPlanFile)

if ($DryRun)    { $wslArgs += "--dry-run" }
if ($NoConvert) { $wslArgs += "--no-convert" }

if ($Output) {
    $wslArgs += "--output"
    $wslArgs += ConvertTo-WslPath ([System.IO.Path]::GetFullPath($Output))
}

if ($Config) {
    $configAbs = [System.IO.Path]::GetFullPath($Config)
    if (-not (Test-Path $configAbs)) {
        Write-Warning "Config file not found: $configAbs"
    }
    $wslArgs += "--config"
    $wslArgs += ConvertTo-WslPath $configAbs
}

Write-Host "Invoking: wsl $($wslArgs -join ' ')"
Write-Host ""

wsl @wslArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Error "run_plan.sh exited with code $exitCode"
    exit $exitCode
}
