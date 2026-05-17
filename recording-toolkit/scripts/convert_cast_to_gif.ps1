# Convert asciinema .cast to .gif using agg
# Requires: cargo install agg
param([Parameter(Mandatory)][string]$InputFile)
if (-not (Test-Path $InputFile)) { Write-Error "Input file not found: $InputFile"; exit 1 }
if (-not (Get-Command agg -ErrorAction SilentlyContinue)) { Write-Error "agg not found. Install with: cargo install agg"; exit 1 }
$OutputFile = [System.IO.Path]::ChangeExtension($InputFile, ".gif")
agg "$InputFile" "$OutputFile"
if ($LASTEXITCODE -ne 0) { Write-Error "agg failed with exit code $LASTEXITCODE"; exit $LASTEXITCODE }
Write-Host "Created: $OutputFile"
