# Azure — API deploy runbook

The FastAPI backend runs on **Azure Container Apps**. The React UI no
longer lives here — it deploys to Cloudflare Workers (see
`infra/cloudflare/README.md`). The UI Container App
(`aca-vaudtaxai-ui`) is being torn down.

## Resources

| Kind | Name |
|---|---|
| Resource Group | `rg-vaudtaxai` |
| Container Registry | `acrvaudtaxai` |
| Container Apps Environment | `env-vaudtaxai` (region `westeurope`) |
| API Container App | `aca-vaudtaxai-api` |
| Custom hostname | `api.tax-gpt.online` |

## Build path — runner-side, not ACR Tasks

Subscription disallows `az acr build` (`TasksOperationsNotAllowed`).
Both CI and the local script use `docker buildx build --push` after
`az acr login`. Same image, same tags, no Tasks API.

CI workflow: [.github/workflows/deploy-azure.yml](../../.github/workflows/deploy-azure.yml)

## Files in this folder

| File | What it does |
|---|---|
| `deploy-api.sh` | Manual one-shot deploy from a dev laptop. Mirrors CI. |
| `setup-domain.sh` | Idempotent: bind `api.tax-gpt.online` + provision managed cert. |
| `verify_deploy.sh` | Asserts hostname binding, cert state, DNS, healthz. |

## DNS records (kept at Cloudflare, post-migration)

| Type | Host | Value | Proxy |
|---|---|---|---|
| CNAME | `api` | `<api default FQDN>` (see `az containerapp show`) | DNS-only (grey cloud) |
| TXT | `asuid.api` | `<api customDomainVerificationId>` | n/a |

The `api` record **must** be DNS-only — orange-cloud proxy would
break Azure's TLS termination.

## First-time bring-up

Once after the resources exist:

```bash
./infra/azure/setup-domain.sh   # adds hostname + cert + binds
./infra/azure/verify_deploy.sh  # asserts end-to-end
```

## Recurring deploys

Push to `main` triggers `.github/workflows/deploy-azure.yml`. The CI:
1. Runs pytest.
2. Builds API image on the GitHub runner.
3. Pushes to ACR.
4. `az containerapp update` with the new image tag.
5. Smoke-checks `/healthz` on the default FQDN.

Manual deploy: `./infra/azure/deploy-api.sh` from repo root.

## Troubleshooting tree

### Custom domain dead, default FQDN dead

App is crashing. `az containerapp logs show -n aca-vaudtaxai-api -g rg-vaudtaxai --tail 100`.
Common causes:
- Missing `/healthz` or wrong port → fixed in `main.py`.
- Pydantic schema build crash (forward ref in dataclass with Callable).
- Env var missing (`OPENAI_API_KEY`, `GROQ_API_KEY`, etc.).

### Custom domain dead, default FQDN alive

DNS or hostname binding. Run `./infra/azure/verify_deploy.sh` — it
exits at the first mismatch and tells you which.

Most common: `BindingType: Disabled`. Re-run `./infra/azure/setup-domain.sh`.

### Cert stuck `Pending` for >15 min

- `dig +short asuid.api.tax-gpt.online TXT` — must equal
  `customDomainVerificationId` of the API app.
- DNS may not have propagated. Lower TTL on the asuid record to 5 min.
- CAA records at the apex may forbid `letsencrypt.org` /
  `digicert.com` / `pki.goog`. List CAA: `dig +short tax-gpt.online CAA`.

### `runningState: ActivationFailed`

Container failed startup probe. Inspect Log Analytics:

```bash
WS=$(az containerapp env show -n env-vaudtaxai -g rg-vaudtaxai \
  --query "properties.appLogsConfiguration.logAnalyticsConfiguration.customerId" -o tsv)
az monitor log-analytics query -w "$WS" \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerAppName_s == 'aca-vaudtaxai-api' | order by TimeGenerated desc | take 100" \
  -o table
```

### Connection reset on TLS handshake to custom domain

SNI mismatch — the hostname is added but no cert is bound. Look at:

```bash
az containerapp hostname list -n aca-vaudtaxai-api -g rg-vaudtaxai -o table
```

`BindingType: Disabled` confirms it. `setup-domain.sh` fixes it.

## Tear-down of the UI app (one-shot, after CF UI live)

```bash
az containerapp delete -n aca-vaudtaxai-ui -g rg-vaudtaxai --yes
az acr repository delete --name acrvaudtaxai --repository vaudtaxai-ui --yes
```

This frees the env IP slot and stops the failing UI revisions from
churning system logs.

## Out of scope

- Bicep/Terraform IaC for the env + app themselves (provisioned
  earlier; not redeployed per release).
- Azure Front Door / WAF (Container Apps native ingress is fine for
  hackathon scope).
- Per-PR review apps (free trial doesn't justify the spend).
