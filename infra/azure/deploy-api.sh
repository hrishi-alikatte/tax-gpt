#!/usr/bin/env bash
set -euo pipefail

# Deploys the FastAPI backend to Azure Container Apps
RESOURCE_GROUP="rg-vaudtaxai"
ACR_NAME="acrvaudtaxai"
ACA_NAME="aca-vaudtaxai-api"
LOCATION="westeurope"

echo "Building and pushing API image to Azure Container Registry..."
az acr build --registry "${ACR_NAME}" --image "vaudtaxai-api:latest" .

echo "Deploying to Azure Container Apps..."
az containerapp up \
  --name "${ACA_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --environment "env-vaudtaxai" \
  --image "${ACR_NAME}.azurecr.io/vaudtaxai-api:latest" \
  --target-port 8080 \
  --ingress external \
  --query "properties.configuration.ingress.fqdn"
