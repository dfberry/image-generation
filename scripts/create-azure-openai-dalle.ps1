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
#   $env:STORY_VIDEO_AZURE_OPENAI_ENDPOINT = "<endpoint from output>"
#   $env:STORY_VIDEO_AZURE_OPENAI_API_KEY = "<key from output>"
#   story-video render --input story.txt --provider azure
# =============================================================================

$ErrorActionPreference = "Stop"

# NOTE: Environment variables set by this script are session-scoped.
# If running in a child scope, dot-source: . .\scripts\create-azure-openai-dalle.ps1

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
    Write-Host "    Done."
    Write-Host "    Waiting for resource to become ready..."
    $State = ""
    for ($i = 1; $i -le 30; $i++) {
        $State = az cognitiveservices account show `
            --name $OpenAIName `
            --resource-group $ResourceGroup `
            --query "properties.provisioningState" `
            --output tsv 2>$null
        if ($State -eq "Succeeded") { break }
        Start-Sleep -Seconds 5
    }
    if ($State -ne "Succeeded") {
        Write-Error "Resource did not reach Succeeded state (current: $State)"
        exit 1
    }
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

if ([string]::IsNullOrWhiteSpace($Endpoint) -or [string]::IsNullOrWhiteSpace($Key)) {
    Write-Error "Could not retrieve endpoint or key. Resource may still be provisioning."
    exit 1
}

$MaskedKey = $Key.Substring(0,4) + "********************************"

# ---------------------------------------------------------------------------
# Step 5: Set environment variables in current session
# ---------------------------------------------------------------------------
$env:STORY_VIDEO_AZURE_OPENAI_ENDPOINT = $Endpoint
$env:STORY_VIDEO_AZURE_OPENAI_API_KEY = $Key
$env:STORY_VIDEO_AZURE_OPENAI_DEPLOYMENT = $DeploymentName

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================"
Write-Host " Azure OpenAI DALL-E 3 — Ready"
Write-Host "============================================================"
Write-Host ""
Write-Host " Endpoint:    $Endpoint"
Write-Host " API Key:     $MaskedKey"
Write-Host " Deployment:  $DeploymentName"
Write-Host ""
Write-Host " ✓ Environment variables SET in current session:"
Write-Host ""
Write-Host "   STORY_VIDEO_AZURE_OPENAI_ENDPOINT=$Endpoint"
Write-Host "   STORY_VIDEO_AZURE_OPENAI_API_KEY=<set - use 'az cognitiveservices account keys list' to retrieve>"
Write-Host "   STORY_VIDEO_AZURE_OPENAI_DEPLOYMENT=$DeploymentName"
Write-Host ""
Write-Host " Ready to use with story-video:"
Write-Host "   story-video render --input story.txt --provider azure"
Write-Host ""
Write-Host " ⚠️  SECURITY: Never commit API keys to source control."
Write-Host "     Use a secret manager (Azure Key Vault) for production workloads."
Write-Host "     If storing locally, ensure .env is in .gitignore."
Write-Host ""
Write-Host " NOTE: These environment variables are session-scoped. If you"
Write-Host " open a new terminal, re-run this script or manually set them."
Write-Host " For persistent use, add these to a .env file and load it."
Write-Host ""
Write-Host "============================================================"
