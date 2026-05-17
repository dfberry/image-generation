# Convert asciinema .cast to .gif using agg
# Requires: cargo install agg
# Supports config file presets and full CLI override
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$InputFile,

    [string]$Theme,
    [double]$Speed,
    [int]$FontSize,
    [int]$Cols,
    [int]$Rows,
    [double]$IdleLimit,
    [switch]$NoLoop,
    [int]$FpsCap,
    [double]$LastFrameDuration,
    [string]$WatermarkText,
    [ValidateSet("landscape", "portrait")]
    [string]$Orientation,
    [string]$Config,
    [string]$Preset,
    [string]$OutputFile,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Usage: convert_cast_to_gif.ps1 -InputFile <file.cast> [options]

Options:
  -InputFile          Path to .cast file (required)
  -Theme              Color theme (dark, dracula, github-dark, github-light, monokai, nord, solarized-dark, solarized-light, gruvbox)
  -Speed              Playback speed multiplier (default: 1.5)
  -FontSize           Font size in pixels (default: 14)
  -Cols               Terminal width in columns
  -Rows               Terminal height in rows
  -IdleLimit          Max idle time in seconds (default: 3)
  -NoLoop             Disable GIF animation loop
  -FpsCap             Max frames per second (default: 30)
  -LastFrameDuration  Duration of last frame in seconds (default: 3)
  -WatermarkText      Text to overlay on GIF (requires ImageMagick)
  -Orientation        Preset dimensions: landscape (120x30), portrait (40x80)
  -Config             Path to config JSON file
  -Preset             Preset name from config file
  -OutputFile         Override output file path
  -Help               Show this help

Priority: CLI switches > preset > config defaults > built-in defaults

Examples:
  .\convert_cast_to_gif.ps1 demo.cast
  .\convert_cast_to_gif.ps1 demo.cast -Preset blog-landscape
  .\convert_cast_to_gif.ps1 demo.cast -Theme monokai -FontSize 20 -Orientation landscape
  .\convert_cast_to_gif.ps1 demo.cast -Config .\recording-config.json -Preset compact
"@
    exit 0
}

if (-not $InputFile) {
    Write-Error "Input .cast file is required. Use -Help for usage."
    exit 1
}

# --- Built-in defaults ---
$settings = @{
    theme               = "asciinema"
    speed               = 1.5
    font_size           = 14
    cols                = 0
    rows                = 0
    idle_time_limit     = 3
    loop                = $true
    fps_cap             = 30
    last_frame_duration = 3
    watermark_text      = ""
}

$themeAliases = @{
    "dark"    = "asciinema"
    "light"   = "github-light"
    "gruvbox" = "gruvbox-dark"
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
    foreach ($key in @("theme", "speed", "font_size", "cols", "rows", "idle_time_limit", "loop", "fps_cap", "last_frame_duration", "watermark_text")) {
        $val = $d.PSObject.Properties[$key]
        if ($val) { $settings[$key] = $val.Value }
    }
}

# Merge theme aliases from config
if ($configData -and $configData.theme_aliases) {
    foreach ($prop in $configData.theme_aliases.PSObject.Properties) {
        $themeAliases[$prop.Name] = $prop.Value
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
        $settings[$prop.Name] = $prop.Value
    }
}

# --- Apply orientation (if no explicit cols/rows from CLI) ---
$colsFromCLI = $PSBoundParameters.ContainsKey('Cols')
$rowsFromCLI = $PSBoundParameters.ContainsKey('Rows')
if ($Orientation -eq "landscape" -and -not $colsFromCLI -and -not $rowsFromCLI) {
    $settings.cols = 120; $settings.rows = 30
} elseif ($Orientation -eq "portrait" -and -not $colsFromCLI -and -not $rowsFromCLI) {
    $settings.cols = 40; $settings.rows = 80
}

# --- Apply CLI overrides (highest priority) ---
if ($PSBoundParameters.ContainsKey('Theme'))             { $settings.theme = $Theme }
if ($PSBoundParameters.ContainsKey('Speed'))             { $settings.speed = $Speed }
if ($PSBoundParameters.ContainsKey('FontSize'))          { $settings.font_size = $FontSize }
if ($colsFromCLI)                                        { $settings.cols = $Cols }
if ($rowsFromCLI)                                        { $settings.rows = $Rows }
if ($PSBoundParameters.ContainsKey('IdleLimit'))         { $settings.idle_time_limit = $IdleLimit }
if ($NoLoop)                                             { $settings.loop = $false }
if ($PSBoundParameters.ContainsKey('FpsCap'))            { $settings.fps_cap = $FpsCap }
if ($PSBoundParameters.ContainsKey('LastFrameDuration')) { $settings.last_frame_duration = $LastFrameDuration }
if ($PSBoundParameters.ContainsKey('WatermarkText'))     { $settings.watermark_text = $WatermarkText }

# --- Resolve theme aliases ---
if ($themeAliases.ContainsKey($settings.theme)) {
    $settings.theme = $themeAliases[$settings.theme]
}

# --- Validate inputs ---
if (-not (Test-Path $InputFile)) {
    Write-Error "Input file not found: $InputFile"
    exit 1
}
if (-not (Get-Command agg -ErrorAction SilentlyContinue)) {
    Write-Error "agg not found. Install with: cargo install agg"
    exit 1
}

# --- Build output path ---
if (-not $OutputFile) {
    $OutputFile = [System.IO.Path]::ChangeExtension($InputFile, ".gif")
}

# --- Build agg command ---
$aggArgs = @(
    "`"$InputFile`""
    "`"$OutputFile`""
    "--font-size", $settings.font_size
    "--theme", $settings.theme
    "--speed", $settings.speed
    "--idle-time-limit", $settings.idle_time_limit
    "--fps-cap", $settings.fps_cap
    "--last-frame-duration", $settings.last_frame_duration
)
if ($settings.cols -gt 0)  { $aggArgs += @("--cols", $settings.cols) }
if ($settings.rows -gt 0)  { $aggArgs += @("--rows", $settings.rows) }
if (-not $settings.loop)   { $aggArgs += "--no-loop" }

Write-Host "Running: agg $($aggArgs -join ' ')"
$aggCmd = "agg $($aggArgs -join ' ')"
Invoke-Expression $aggCmd

if ($LASTEXITCODE -ne 0) {
    Write-Error "agg failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "Created: $OutputFile"

# --- Watermark (optional, requires ImageMagick) ---
if ($settings.watermark_text -and $settings.watermark_text -ne "") {
    if (Get-Command magick -ErrorAction SilentlyContinue) {
        Write-Host "Applying watermark: $($settings.watermark_text)"
        magick "$OutputFile" `
            -gravity SouthEast -pointsize 14 -fill "rgba(255,255,255,0.5)" `
            -annotate +10+10 "$($settings.watermark_text)" `
            "$OutputFile"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Watermark applied."
        } else {
            Write-Warning "Watermark failed (exit code $LASTEXITCODE). GIF was still created without watermark."
        }
    } else {
        Write-Warning "ImageMagick (magick) not found - skipping watermark. Install from https://imagemagick.org"
    }
}
