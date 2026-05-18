#!/bin/bash
# =============================================================================
# Create Azure OpenAI Service with DALL-E 3 deployment
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
#   chmod +x scripts/create-azure-openai-dalle.sh
#   ./scripts/create-azure-openai-dalle.sh
#
# After running, use with story-video:
#   export STORY_VIDEO_AZURE_OPENAI_ENDPOINT=<endpoint from output>
#   export STORY_VIDEO_AZURE_OPENAI_API_KEY=<key from output>
#   story-video render --input story.txt --provider azure
# =============================================================================

set -euo pipefail

# NOTE: Environment variables set by this script are session-scoped.
# To persist env vars to the parent shell, source this script instead of executing it:
#   source ./scripts/create-azure-openai-dalle.sh
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "⚠️  NOTE: Running as script (not sourced). Environment variables will NOT persist."
    echo "   To persist env vars, run: source ${0}"
    echo ""
fi

# ---------------------------------------------------------------------------
# Configuration — override these variables as needed
# ---------------------------------------------------------------------------
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-story-video-openai}"
LOCATION="${LOCATION:-swedencentral}"
OPENAI_RESOURCE_NAME="${OPENAI_RESOURCE_NAME:-oai-story-video}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-dall-e-3}"
MODEL_NAME="dall-e-3"
MODEL_VERSION="3.0"
SKU="S0"

# ---------------------------------------------------------------------------
# Step 1: Create resource group if it doesn't exist
# ---------------------------------------------------------------------------
echo "==> Checking resource group '${RESOURCE_GROUP}' in '${LOCATION}'..."

if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    echo "    Resource group already exists. Skipping creation."
else
    echo "    Creating resource group..."
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --output none
    echo "    Done."
fi

# ---------------------------------------------------------------------------
# Step 2: Create Azure OpenAI resource if it doesn't exist
# ---------------------------------------------------------------------------
echo "==> Checking Azure OpenAI resource '${OPENAI_RESOURCE_NAME}'..."

if az cognitiveservices account show \
    --name "$OPENAI_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "    Azure OpenAI resource already exists. Skipping creation."
else
    echo "    Creating Azure OpenAI resource (kind: OpenAI, sku: ${SKU})..."
    az cognitiveservices account create \
        --name "$OPENAI_RESOURCE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --kind "OpenAI" \
        --sku "$SKU" \
        --output none
    echo "    Done."
    echo "    Waiting for resource to become ready..."
    for i in $(seq 1 30); do
        STATE=$(az cognitiveservices account show \
            --name "$OPENAI_RESOURCE_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --query "properties.provisioningState" \
            --output tsv 2>/dev/null)
        if [[ "$STATE" == "Succeeded" ]]; then
            break
        fi
        sleep 5
    done
    if [[ "$STATE" != "Succeeded" ]]; then
        echo "ERROR: Resource did not reach Succeeded state (current: $STATE)"
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Step 3: Deploy DALL-E 3 model if deployment doesn't exist
# ---------------------------------------------------------------------------
echo "==> Checking deployment '${DEPLOYMENT_NAME}'..."

if az cognitiveservices account deployment show \
    --name "$OPENAI_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --deployment-name "$DEPLOYMENT_NAME" &>/dev/null; then
    echo "    Deployment already exists. Skipping."
else
    echo "    Deploying model '${MODEL_NAME}' version '${MODEL_VERSION}'..."
    az cognitiveservices account deployment create \
        --name "$OPENAI_RESOURCE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --deployment-name "$DEPLOYMENT_NAME" \
        --model-name "$MODEL_NAME" \
        --model-version "$MODEL_VERSION" \
        --model-format "OpenAI" \
        --sku-capacity 1 \
        --sku-name "Standard" \
        --output none
    echo "    Done."
fi

# ---------------------------------------------------------------------------
# Step 4: Retrieve endpoint and key
# ---------------------------------------------------------------------------
echo ""
echo "==> Retrieving connection details..."

ENDPOINT=$(az cognitiveservices account show \
    --name "$OPENAI_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.endpoint" \
    --output tsv)

KEY=$(az cognitiveservices account keys list \
    --name "$OPENAI_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "key1" \
    --output tsv)

if [[ -z "$ENDPOINT" || -z "$KEY" ]]; then
    echo "ERROR: Could not retrieve endpoint or key. Resource may still be provisioning."
    exit 1
fi

MASKED_KEY="${KEY:0:4}********************************"

# ---------------------------------------------------------------------------
# Step 5: Set environment variables in current session
# ---------------------------------------------------------------------------
export STORY_VIDEO_AZURE_OPENAI_ENDPOINT="$ENDPOINT"
export STORY_VIDEO_AZURE_OPENAI_API_KEY="$KEY"
export STORY_VIDEO_AZURE_OPENAI_DEPLOYMENT="$DEPLOYMENT_NAME"

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Azure OpenAI DALL-E 3 — Ready"
echo "============================================================"
echo ""
echo " Endpoint:    ${ENDPOINT}"
echo " API Key:     ${MASKED_KEY}"
echo " Deployment:  ${DEPLOYMENT_NAME}"
echo ""
echo " ✓ Environment variables SET in current session:"
echo ""
echo "   STORY_VIDEO_AZURE_OPENAI_ENDPOINT=${ENDPOINT}"
echo "   STORY_VIDEO_AZURE_OPENAI_API_KEY=<set - use 'az cognitiveservices account keys list' to retrieve>"
echo "   STORY_VIDEO_AZURE_OPENAI_DEPLOYMENT=${DEPLOYMENT_NAME}"
echo ""
echo " Ready to use with story-video:"
echo "   story-video render --input story.txt --provider azure"
echo ""
echo " ⚠️  SECURITY: Never commit API keys to source control."
echo "     Use a secret manager (Azure Key Vault) for production workloads."
echo "     If storing locally, ensure .env is in .gitignore."
echo ""
echo " NOTE: These environment variables are session-scoped. If you"
echo " open a new terminal, re-run this script or manually set them."
echo " For persistent use, add these to a .env file and load it."
echo ""
echo "============================================================"
