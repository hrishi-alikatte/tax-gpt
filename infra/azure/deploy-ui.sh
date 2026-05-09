#!/usr/bin/env bash
set -euo pipefail

# Deploys the React UI to Azure Container Apps
RESOURCE_GROUP="rg-vaudtaxai"
ACR_NAME="acrvaudtaxai"
ACA_NAME="aca-vaudtaxai-ui"
LOCATION="westeurope"

echo "Building and pushing UI image to Azure Container Registry..."
az acr build --registry "${ACR_NAME}" --image "vaudtaxai-ui:latest" \
  --build-arg VITE_API_BASE_URL=https://api.tax-gpt.online \
  -f "Vaud Tax Guide/Dockerfile.ui" "Vaud Tax Guide"

echo "Deploying to Azure Container Apps..."
az containerapp up \
  --name "${ACA_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --environment "env-vaudtaxai" \
  --image "${ACR_NAME}.azurecr.io/vaudtaxai-ui:latest" \
  --target-port 3000 \
  --ingress external \
  --query "properties.configuration.ingress.fqdn"
