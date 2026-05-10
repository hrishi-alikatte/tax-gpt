#!/usr/bin/env bash
# Idempotent: bind api.tax-gpt.online to the API Container App with a
# free Azure-managed cert. Re-runnable safely on transient failures.
#
# Prerequisites:
#  - DNS already in place at the domain provider:
#      CNAME api.tax-gpt.online → <api app default FQDN>
#      TXT   asuid.api.tax-gpt.online → <api app customDomainVerificationId>
#  - `az` logged in with rights on rg-vaudtaxai.
set -euo pipefail

RG="rg-vaudtaxai"
ENV="env-vaudtaxai"
APP="aca-vaudtaxai-api"
HOST="api.tax-gpt.online"
CERT="mc-${HOST//./-}"   # mc-api-tax-gpt-online

echo ">>> Adding hostname (idempotent)"
az containerapp hostname add -n "$APP" -g "$RG" --hostname "$HOST" || true

echo ">>> Creating managed cert (idempotent — CNAME validation)"
az containerapp env certificate create \
  --resource-group "$RG" --name "$ENV" \
  --certificate-name "$CERT" \
  --hostname "$HOST" \
  --validation-method CNAME || true

echo ">>> Polling cert provisioning state..."
for i in $(seq 1 30); do
  state=$(az containerapp env certificate show \
    --resource-group "$RG" --name "$ENV" \
    --certificate-name "$CERT" \
    --query "properties.provisioningState" -o tsv 2>/dev/null || echo "Pending")
  echo "  attempt $i/30: $state"
  case "$state" in
    Succeeded) break ;;
    Failed) echo "Cert issuance failed. Inspect in portal."; exit 1 ;;
  esac
  sleep 20
done

CERT_ID=$(az containerapp env certificate show \
  --resource-group "$RG" --name "$ENV" \
  --certificate-name "$CERT" --query id -o tsv)

echo ">>> Binding cert to hostname"
az containerapp hostname bind \
  -n "$APP" -g "$RG" \
  --hostname "$HOST" \
  --environment "$ENV" \
  --certificate "$CERT_ID" \
  --validation-method CNAME

echo ">>> Done. Verifying..."
az containerapp hostname list -n "$APP" -g "$RG" -o table
echo ""
echo "Try: curl -I https://${HOST}/healthz"
