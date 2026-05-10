# Cloudflare Workers — UI deploy runbook

This is the canonical bring-up doc for the React/TanStack-Start UI on
Cloudflare Workers. The UI was scaffolded by lovable.dev with the
`@cloudflare/vite-plugin` and a `wrangler.jsonc` — Workers is the
build's native target. Container Apps is wrong for it (Bun ≠ workerd
runtime; `getBuiltinModule` crash).

## Architecture after migration

```
api.tax-gpt.online      → Azure Container Apps  (FastAPI / Python)
tax-gpt.online          → Cloudflare Workers     (TanStack Start / React)
www.tax-gpt.online      → Cloudflare Workers     (TanStack Start / React)
```

DNS lives at **Cloudflare** (moved from Namecheap). Workers Custom
Domains require the zone to be on Cloudflare.

---

## One-time setup

### 1. Create the Cloudflare account + Workers project

- Sign up at https://dash.cloudflare.com (free plan covers this app).
- Workers free tier: 100k req/day, no cold-start penalty.

### 2. Move DNS zone to Cloudflare

1. Cloudflare dash → **Add a site** → enter `tax-gpt.online`.
2. Pick **Free** plan.
3. Cloudflare scans existing DNS at Namecheap. Confirm:
   - `api` CNAME → `aca-vaudtaxai-api.lemondesert-1de3b030.westeurope.azurecontainerapps.io`
   - `asuid.api` TXT → `479998261AC80ACD…`
   - Drop the apex `A` record (`20.101.250.120`) — Workers Custom Domain replaces it.
   - Drop the `www` CNAME — Workers Custom Domain replaces it.
   - Drop the apex `asuid` TXT and `asuid.www` TXT — no longer needed (UI not on ACA).
   - Drop the `hosting-site=…` TXT.
4. Cloudflare gives you two nameservers (e.g. `ada.ns.cloudflare.com`, `kai.ns.cloudflare.com`).
5. **Namecheap dashboard** → Domain List → Manage `tax-gpt.online` → **Nameservers** → Custom DNS → paste the two CF nameservers → Save.
6. Wait 5–60 min for nameserver propagation. Cloudflare emails when active.
7. **Important — disable proxy ("orange cloud") on the `api` CNAME.**
   Azure Container Apps uses its own TLS cert; CF proxy would terminate
   TLS itself and break the asuid validation chain. Set `api` to
   "DNS only" (grey cloud).

### 3. Cloudflare API token for CI

1. Cloudflare dash → **My Profile** → **API Tokens** → **Create Token**.
2. Use template **Edit Cloudflare Workers**.
3. Permissions required:
   - Account → Workers Scripts → Edit
   - Account → Workers Routes → Edit
   - Zone → DNS → Edit (for custom-domain triggers)
   - Zone → Workers Routes → Edit
4. Account Resources: select your account.
5. Zone Resources: include `tax-gpt.online`.
6. Copy the token once — Cloudflare doesn't show it again.

Get the **Account ID** from any project page in the dash (right sidebar).

### 4. GitHub repository secrets

GitHub repo → Settings → Secrets and variables → Actions → **New repository secret**:

| Name | Value |
|---|---|
| `CLOUDFLARE_API_TOKEN` | the token from step 3 |
| `CLOUDFLARE_ACCOUNT_ID` | the account ID from step 3 |

### 5. First deploy

Two paths, pick one:

**a) Push to main** — `.github/workflows/deploy-cloudflare.yml` triggers
when anything under `Vaud Tax Guide/` changes. Manual run also works
via the Actions tab → **Run workflow**.

**b) Local one-shot** (sanity check the pipeline before relying on CI):

```bash
cd "Vaud Tax Guide"
bun install
VITE_API_BASE_URL=https://api.tax-gpt.online bun run build
bunx wrangler deploy   # prompts for OAuth on first run
```

After deploy, Workers attaches Custom Domains automatically because
`wrangler.jsonc` declares them under `routes`. CF issues TLS cert
(takes 1–5 min).

### 6. Verify

```bash
dig +short tax-gpt.online      # should resolve to a Cloudflare IP, not 20.101.x.x
dig +short www.tax-gpt.online  # same
curl -I https://tax-gpt.online           # 200, server: cloudflare
curl -I https://www.tax-gpt.online       # 200
curl -I https://api.tax-gpt.online/healthz  # 200, served by Container Apps
```

In the Cloudflare dash:
- **Workers & Pages** → `vaudtaxai-ui` → **Triggers** → Custom Domains shows both hostnames green.
- **Workers & Pages** → `vaudtaxai-ui` → **Logs** for live traces.

---

## Recurring deploys

`.github/workflows/deploy-cloudflare.yml` runs on every push to `main`
that touches `Vaud Tax Guide/**`. Each push deploys a new Worker
version; Cloudflare keeps versions for rollback.

Manual rollback: dash → Workers → `vaudtaxai-ui` → **Deployments** →
choose previous version → **Rollback**.

---

## Troubleshooting

### `curl https://tax-gpt.online` shows Cloudflare error 522 / 1016

The Worker isn't bound to the route. Check:
- `bunx wrangler deployments list` shows a recent deploy.
- `wrangler.jsonc` `routes` matches the hostname.
- DNS has propagated to CF (`dig NS tax-gpt.online` returns CF nameservers).

### TLS error when hitting `api.tax-gpt.online`

The CNAME for `api` may have orange-cloud proxy enabled. Switch to
DNS-only (grey cloud). Azure Container Apps must terminate TLS for its
own managed cert.

### Worker deploy fails with `getBuiltinModule is not defined`

Bun was used as the runtime. Don't run the build output under Bun —
`wrangler deploy` ships it to workerd which has the API. The
`Dockerfile.ui` was the symptom of this; it is no longer used.

### `VITE_API_BASE_URL` isn't picked up

Vite inlines env vars at **build** time. The workflow already sets it
before `bun run build`. Local dev: prefix the build command, or add a
`.env.local` (gitignored).

### Custom Domain stuck in "Pending"

CF needs to issue cert. Takes ≤ 15 min usually. If longer:
- Confirm CAA records at the apex don't disallow `letsencrypt.org` /
  `pki.goog`.
- Re-trigger by removing and re-adding the custom domain in dash.

---

## Out of scope (future)

- Preview deployments per-PR via Cloudflare Pages branch deploys.
- Wrangler bindings for KV / D1 / R2 if the UI needs server state.
- Splitting `wrangler.jsonc` into env-specific configs.
