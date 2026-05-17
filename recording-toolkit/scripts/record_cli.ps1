# One-key CLI recording (PowerShell)
$dir = Join-Path (git rev-parse --show-toplevel) "recordings\cli"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$filename = Get-Date -Format "yyyyMMdd-HHmm"
asciinema rec "$dir\$filename.cast"
