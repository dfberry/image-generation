# Convert asciinema .cast to .gif using agg
# Requires: pip install asciinema-agg
param([Parameter(Mandatory)][string]$InputFile)
$OutputFile = [System.IO.Path]::ChangeExtension($InputFile, ".gif")
agg $InputFile $OutputFile
