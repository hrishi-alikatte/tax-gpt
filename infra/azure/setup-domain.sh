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

cert_state () {
  az containerapp env certificate list \
    -g "$RG" -n "$ENV" \
    --query "[?name=='$CERT'].properties.provisioningState | [0]" \
    -o tsv 2>/dev/null || echo "Pending"
}

cert_id () {
  az containerapp env certificate list \
    -g "$RG" -n "$ENV" \
    --query "[?name=='$CERT'].id | [0]" \
    -o tsv
}

echo ">>> Polling cert provisioning state (up to 15 min)..."
for i in $(seq 1 45); do
  state=$(cert_state)
  echo "  attempt $i/45: $state"
  case "$state" in
    Succeeded) break ;;
    Failed) echo "Cert issuance failed. Inspect in portal."; exit 1 ;;
  esac
  sleep 20
done

CERT_ID=$(cert_id)
if [[ -z "$CERT_ID" ]]; then
  echo "Cert ID empty after polling — aborting." >&2
  exit 1
fi

echo ">>> Binding cert to hostname"
az containerapp hostname bind \
  -n "$APP" -g "$RG" \
  --hostname "$HOST" \
  --environment "$ENV" \
  --certificate "$CERT_ID" \
  --validation-method CNAME

echo ">>> Polling binding state (up to 3 min)..."
for i in $(seq 1 18); do
  bt=$(az containerapp hostname list -n "$APP" -g "$RG" \
    --query "[?name=='$HOST'].bindingType | [0]" -o tsv)
  echo "  attempt $i/18: $bt"
  [[ "$bt" == "SniEnabled" ]] && break
  sleep 10
done

echo ">>> Final state:"
az containerapp hostname list -n "$APP" -g "$RG" -o table
echo ""
echo "Try: curl -I https://${HOST}/healthz"
