# =============================================================================
# Create Azure OpenAI Service with DALL-E 3 deployment (PowerShell)
#
# This script provisions the Azure resources needed for cloud-based image
# generation in the story-to-video pipeline, replacing local SDXL/Ollama
# which times out without GPU hardware.
#
# Prerequisites:
#   - Azure CLI installed (az)
#   - Logged in: az login
#   - Subscription selected: az account set --subscription <id>
#
# Usage:
#   .\scripts\create-azure-openai-dalle.ps1
#
# After running, use with story-video:
#   $env:AZURE_OPENAI_ENDPOINT = "<endpoint from output>"
#   $env:AZURE_OPENAI_API_KEY = "<key from output>"
#   story-video render --input story.txt --provider azure
# =============================================================================

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Configuration — override these variables as needed
# ---------------------------------------------------------------------------
$ResourceGroup    = if ($env:RESOURCE_GROUP)       { $env:RESOURCE_GROUP }       else { "rg-story-video-openai" }
$Location         = if ($env:LOCATION)             { $env:LOCATION }             else { "swedencentral" }
$OpenAIName       = if ($env:OPENAI_RESOURCE_NAME) { $env:OPENAI_RESOURCE_NAME } else { "oai-story-video" }
$DeploymentName   = if ($env:DEPLOYMENT_NAME)      { $env:DEPLOYMENT_NAME }      else { "dall-e-3" }
$ModelName        = "dall-e-3"
$ModelVersion     = "3.0"
$Sku              = "S0"

# ---------------------------------------------------------------------------
# Step 1: Create resource group if it doesn't exist
# ---------------------------------------------------------------------------
Write-Host "==> Checking resource group '$ResourceGroup' in '$Location'..."

$rgExists = az group show --name $ResourceGroup 2>$null
if ($rgExists) {
    Write-Host "    Resource group already exists. Skipping creation."
} else {
    Write-Host "    Creating resource group..."
    az group create `
        --name $ResourceGroup `
        --location $Location `
        --output none
    Write-Host "    Done."
}

# ---------------------------------------------------------------------------
# Step 2: Create Azure OpenAI resource if it doesn't exist
# ---------------------------------------------------------------------------
Write-Host "==> Checking Azure OpenAI resource '$OpenAIName'..."

$oaiExists = az cognitiveservices account show `
    --name $OpenAIName `
    --resource-group $ResourceGroup 2>$null
if ($oaiExists) {
    Write-Host "    Azure OpenAI resource already exists. Skipping creation."
} else {
    Write-Host "    Creating Azure OpenAI resource (kind: OpenAI, sku: $Sku)..."
    az cognitiveservices account create `
        --name $OpenAIName `
        --resource-group $ResourceGroup `
        --location $Location `
        --kind "OpenAI" `
        --sku $Sku `
        --output none
    Write-Host "    Done. (This may take a minute to propagate.)"
}

# ---------------------------------------------------------------------------
# Step 3: Deploy DALL-E 3 model if deployment doesn't exist
# ---------------------------------------------------------------------------
Write-Host "==> Checking deployment '$DeploymentName'..."

$deployExists = az cognitiveservices account deployment show `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --deployment-name $DeploymentName 2>$null
if ($deployExists) {
    Write-Host "    Deployment already exists. Skipping."
} else {
    Write-Host "    Deploying model '$ModelName' version '$ModelVersion'..."
    az cognitiveservices account deployment create `
        --name $OpenAIName `
        --resource-group $ResourceGroup `
        --deployment-name $DeploymentName `
        --model-name $ModelName `
        --model-version $ModelVersion `
        --model-format "OpenAI" `
        --sku-capacity 1 `
        --sku-name "Standard" `
        --output none
    Write-Host "    Done."
}

# ---------------------------------------------------------------------------
# Step 4: Retrieve endpoint and key
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "==> Retrieving connection details..."

$Endpoint = az cognitiveservices account show `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --query "properties.endpoint" `
    --output tsv

$Key = az cognitiveservices account keys list `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --query "key1" `
    --output tsv

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================"
Write-Host " Azure OpenAI DALL-E 3 — Ready"
Write-Host "============================================================"
Write-Host ""
Write-Host " Endpoint:    $Endpoint"
Write-Host " API Key:     $Key"
Write-Host " Deployment:  $DeploymentName"
Write-Host ""
Write-Host " Set these environment variables to use with story-video:"
Write-Host ""
Write-Host "   `$env:AZURE_OPENAI_ENDPOINT = `"$Endpoint`""
Write-Host "   `$env:AZURE_OPENAI_API_KEY = `"$Key`""
Write-Host "   `$env:AZURE_OPENAI_DEPLOYMENT = `"$DeploymentName`""
Write-Host ""
Write-Host " Then run:"
Write-Host "   story-video render --input story.txt --provider azure"
Write-Host ""
Write-Host "============================================================"
