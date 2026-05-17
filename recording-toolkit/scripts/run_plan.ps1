# Recording plan runner — PowerShell wrapper that calls run_plan.sh via WSL.
# asciinema requires a Unix terminal; this script translates Windows paths and invokes WSL.
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
  -NoConvert     Skip GIF conversion after recording
  -Output        Override output .cast file path
  -Config        Path to recording-config.json for convert settings
  -Help          Show this help

This script translates Windows paths to WSL paths and calls run_plan.sh via WSL.
asciinema requires a Unix terminal and cannot run natively on Windows.

Examples:
  .\run_plan.ps1 recordings\plans\copilot-cli-test.json
  .\run_plan.ps1 recordings\plans\copilot-cli-test.json -DryRun
  .\run_plan.ps1 recordings\plans\copilot-cli-test.json -NoConvert
"@
    exit 0
}

# --- Validate WSL is available ---
if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Error "WSL not found. asciinema requires WSL on Windows. Install WSL: https://learn.microsoft.com/windows/wsl/install"
    exit 1
}

# --- Path translation helper (Windows → WSL /mnt/...) ---
function ConvertTo-WslPath {
    param([string]$WinPath)
    if ([string]::IsNullOrEmpty($WinPath)) { return "" }
    $abs = [System.IO.Path]::GetFullPath($WinPath)
    # Convert drive letter: C:\foo\bar → /mnt/c/foo/bar
    if ($abs -match '^([A-Za-z]):\\(.*)$') {
        $drive = $Matches[1].ToLower()
        $rest  = $Matches[2] -replace '\\', '/'
        return "/mnt/$drive/$rest"
    }
    # Already a UNC or forward-slash path — return as-is
    return $abs -replace '\\', '/'
}

# --- Resolve paths ---
$planFileAbs  = [System.IO.Path]::GetFullPath($PlanFile)
if (-not (Test-Path $planFileAbs)) {
    Write-Error "Plan file not found: $planFileAbs"
    exit 1
}

$scriptDir = $PSScriptRoot
$runPlanSh = Join-Path $scriptDir "run_plan.sh"
if (-not (Test-Path $runPlanSh)) {
    Write-Error "run_plan.sh not found at: $runPlanSh"
    exit 1
}

$wslPlanFile  = ConvertTo-WslPath $planFileAbs
$wslRunPlanSh = ConvertTo-WslPath $runPlanSh

# --- Build argument list ---
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

# --- Execute via WSL ---
Write-Host "Invoking: wsl $($wslArgs -join ' ')"
Write-Host ""

wsl @wslArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Error "run_plan.sh exited with code $exitCode"
    exit $exitCode
}
