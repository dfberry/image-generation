# One-key CLI recording (PowerShell)
# NOTE: asciinema requires WSL on Windows. Run this script from WSL or Linux/macOS.
$repoRoot = (git rev-parse --show-toplevel)
if ($LASTEXITCODE -ne 0) { Write-Error "Not in a git repository"; exit 1 }
if (-not (Get-Command asciinema -ErrorAction SilentlyContinue)) { Write-Error "asciinema not found. Install with: pip install asciinema (requires WSL on Windows)"; exit 1 }
$dir = Join-Path $repoRoot "recordings\cli"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$filename = Get-Date -Format "yyyyMMdd-HHmm"
asciinema rec "$dir\$filename.cast"
