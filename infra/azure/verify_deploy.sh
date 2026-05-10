#!/usr/bin/env bash
# End-to-end assertion of the API deploy state. Exit non-zero on first
# mismatch. Cheap to run; intended for CI smoke + post-deploy sanity.
set -euo pipefail

RG="rg-vaudtaxai"
APP="aca-vaudtaxai-api"
ENV="env-vaudtaxai"
HOST="api.tax-gpt.online"
CERT="mc-${HOST//./-}"

red() { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
fail() { red "FAIL: $*"; exit 1; }
pass() { green "PASS: $*"; }

echo "=== Hostname bound on $APP ==="
bound=$(az containerapp hostname list -n "$APP" -g "$RG" \
  --query "[?name=='$HOST'].bindingType" -o tsv)
[[ "$bound" == "SniEnabled" ]] || fail "hostname binding for $HOST: '$bound' (want SniEnabled)"
pass "hostname binding = SniEnabled"

echo "=== Managed cert state ==="
state=$(az containerapp env certificate show -g "$RG" --name "$ENV" \
  --certificate-name "$CERT" --query "properties.provisioningState" -o tsv 2>/dev/null || echo "Missing")
[[ "$state" == "Succeeded" ]] || fail "cert $CERT state: $state"
pass "managed cert = Succeeded"

echo "=== Active revision health ==="
hs=$(az containerapp revision list -n "$APP" -g "$RG" \
  --query "[?properties.active].properties.healthState | [0]" -o tsv)
[[ "$hs" == "Healthy" ]] || fail "active revision healthState: $hs"
pass "active revision = Healthy"

echo "=== DNS sanity ==="
expected_cname=$(az containerapp show -n "$APP" -g "$RG" \
  --query "properties.configuration.ingress.fqdn" -o tsv)
got_cname=$(dig +short "$HOST" CNAME | sed 's/\.$//')
[[ "$got_cname" == "$expected_cname" ]] \
  || fail "CNAME for $HOST: got '$got_cname', want '$expected_cname'"
pass "CNAME $HOST → $expected_cname"

expected_asuid=$(az containerapp show -n "$APP" -g "$RG" \
  --query "properties.customDomainVerificationId" -o tsv)
got_asuid=$(dig +short "asuid.$HOST" TXT | tr -d '"')
[[ "$got_asuid" == "$expected_asuid" ]] \
  || fail "asuid TXT for asuid.$HOST: got '$got_asuid', want '$expected_asuid'"
pass "asuid.$HOST TXT matches"

echo "=== HTTPS healthz ==="
curl -fsS --max-time 15 "https://$HOST/healthz" >/dev/null \
  || fail "https://$HOST/healthz did not respond 200"
pass "https://$HOST/healthz responds"

green "ALL CHECKS PASSED"
