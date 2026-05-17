# One-key CLI recording (PowerShell)
# NOTE: asciinema requires WSL on Windows. Run this script from WSL or Linux/macOS.
# Supports config file presets and CLI overrides for terminal dimensions.
[CmdletBinding()]
param(
    [int]$Cols,
    [int]$Rows,
    [double]$IdleLimit,
    [string]$OutputDir,
    [string]$Config,
    [string]$Preset,
    [ValidateSet("landscape", "portrait")]
    [string]$Orientation,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Usage: record_cli.ps1 [options]

Options:
  -Cols          Terminal width in columns (default: 120)
  -Rows          Terminal height in rows (default: 30)
  -IdleLimit     Max idle time in seconds (default: 3)
  -OutputDir     Output directory for .cast files (default: recordings/cli)
  -Config        Path to config JSON file
  -Preset        Preset name from config file
  -Orientation   Preset dimensions: landscape (120x30), portrait (40x80)
  -Help          Show this help

Priority: CLI switches > preset > config defaults > built-in defaults

Examples:
  .\record_cli.ps1
  .\record_cli.ps1 -Preset blog-landscape
  .\record_cli.ps1 -Cols 100 -Rows 25
  .\record_cli.ps1 -Orientation landscape
"@
    exit 0
}

# --- Built-in defaults ---
$settings = @{
    cols            = 120
    rows            = 30
    idle_time_limit = 3
    output_dir      = "recordings/cli"
}

# --- Load config file ---
$configPath = $Config
if (-not $configPath) {
    $autoConfig = Join-Path (Split-Path $PSScriptRoot) "recording-config.json"
    if (Test-Path $autoConfig) { $configPath = $autoConfig }
}

$configData = $null
if ($configPath -and (Test-Path $configPath)) {
    try {
        $configData = Get-Content $configPath -Raw | ConvertFrom-Json
    } catch {
        Write-Warning "Failed to parse config file: $configPath"
    }
}

# Apply config defaults
if ($configData -and $configData.defaults) {
    $d = $configData.defaults
    foreach ($key in @("cols", "rows", "idle_time_limit", "output_dir")) {
        $val = $d.PSObject.Properties[$key]
        if ($val) { $settings[$key] = $val.Value }
    }
}

# --- Apply preset ---
if ($Preset) {
    $presetData = $null
    if ($configData -and $configData.presets) {
        $presetData = $configData.presets.PSObject.Properties[$Preset]
    }
    if (-not $presetData) {
        Write-Error "Preset '$Preset' not found in config file."
        exit 1
    }
    foreach ($prop in $presetData.Value.PSObject.Properties) {
        if ($settings.ContainsKey($prop.Name)) {
            $settings[$prop.Name] = $prop.Value
        }
    }
}

# --- Apply orientation ---
$colsFromCLI = $PSBoundParameters.ContainsKey('Cols')
$rowsFromCLI = $PSBoundParameters.ContainsKey('Rows')
if ($Orientation -eq "landscape" -and -not $colsFromCLI -and -not $rowsFromCLI) {
    $settings.cols = 120; $settings.rows = 30
} elseif ($Orientation -eq "portrait" -and -not $colsFromCLI -and -not $rowsFromCLI) {
    $settings.cols = 40; $settings.rows = 80
}

# --- Apply CLI overrides ---
if ($colsFromCLI)                                    { $settings.cols = $Cols }
if ($rowsFromCLI)                                    { $settings.rows = $Rows }
if ($PSBoundParameters.ContainsKey('IdleLimit'))     { $settings.idle_time_limit = $IdleLimit }
if ($PSBoundParameters.ContainsKey('OutputDir'))     { $settings.output_dir = $OutputDir }

# --- Validate ---
$repoRoot = (git rev-parse --show-toplevel)
if ($LASTEXITCODE -ne 0) { Write-Error "Not in a git repository"; exit 1 }

if (-not (Get-Command asciinema -ErrorAction SilentlyContinue)) {
    Write-Error "asciinema not found. Install with: pip install asciinema (requires WSL on Windows)"
    exit 1
}

# --- Prepare output directory ---
$dir = if ([System.IO.Path]::IsPathRooted($settings.output_dir)) {
    $settings.output_dir
} else {
    Join-Path $repoRoot $settings.output_dir
}
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$filename = Get-Date -Format "yyyyMMdd-HHmm"
$castFile = Join-Path $dir "$filename.cast"

# Set terminal dimensions via environment variables
$env:COLUMNS = $settings.cols
$env:LINES = $settings.rows

Write-Host "Recording with dimensions: $($settings.cols)x$($settings.rows), idle limit: $($settings.idle_time_limit)s"
Write-Host "Output: $castFile"
Write-Host "Press Ctrl+D or type 'exit' to stop recording."

# Build asciinema args
$asciiArgs = @("rec", "--idle-time-limit", $settings.idle_time_limit, $castFile)

asciinema @asciiArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "asciinema failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "Recording saved: $castFile"
