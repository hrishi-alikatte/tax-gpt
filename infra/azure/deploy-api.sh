#!/usr/bin/env bash
# Manual / local deploy of the FastAPI backend to Azure Container Apps.
# Mirrors what .github/workflows/deploy-azure.yml does on every push to main.
#
# Build happens on this machine (not via `az acr build`) because the
# subscription disallows ACR Tasks. Requires:
#   - logged-in `az` CLI with rights to push to acrvaudtaxai
#   - logged-in `docker` daemon
#   - run from repo root.
set -euo pipefail

RG="rg-vaudtaxai"
ACR="acrvaudtaxai"
APP="aca-vaudtaxai-api"

if [[ ! -f Dockerfile ]]; then
  echo "Run from repo root (Dockerfile expected here)." >&2
  exit 1
fi

TAG=$(git rev-parse HEAD 2>/dev/null || date +%Y%m%d-%H%M%S)
IMAGE="${ACR}.azurecr.io/vaudtaxai-api:${TAG}"

echo ">>> Logging in to ACR..."
az acr login --name "$ACR"

echo ">>> Building + pushing $IMAGE"
docker buildx build \
  --platform linux/amd64 \
  --tag "$IMAGE" \
  --tag "${ACR}.azurecr.io/vaudtaxai-api:latest" \
  --push \
  .

echo ">>> Updating Container App $APP"
az containerapp update \
  --name "$APP" --resource-group "$RG" \
  --image "$IMAGE"

echo ">>> Waiting for new revision to become Healthy..."
sleep 10
FQDN=$(az containerapp show -n "$APP" -g "$RG" \
  --query "properties.configuration.ingress.fqdn" -o tsv)
for i in $(seq 1 20); do
  if curl -fsS --max-time 10 "https://$FQDN/healthz" >/dev/null; then
    echo "OK: https://$FQDN/healthz responds 200"
    exit 0
  fi
  echo "  attempt $i/20: waiting 15s..."
  sleep 15
done
echo "Healthz never came up. Recent logs:" >&2
az containerapp logs show -n "$APP" -g "$RG" --tail 50 || true
exit 1
