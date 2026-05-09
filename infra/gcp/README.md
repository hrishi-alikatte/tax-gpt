# Google Cloud Run Deployment Prep

VaudTaxAI targets Google Cloud Run for hosting because Flet web mode needs a
long-running Python process with WebSocket support. Supabase remains the
planned persistence backend; Azure OpenAI and Groq remain the model providers
until a separate provider-migration phase.

No production deployment should run until the Google Cloud project, runtime
secrets, and `tax-gpt.online` domain mapping are confirmed.

## Recommended Defaults

| Setting | Value |
| --- | --- |
| Region | `europe-west6` (Zurich) |
| Artifact Registry repository | `vaudtaxai` |
| Cloud Run service | `vaudtaxai-web` |
| Container port | `8080` via Cloud Run `PORT` |
| Public URL | `https://tax-gpt.online` |

If `europe-west6` is not enabled for the account, use `europe-west1` and keep
the rest of the service shape unchanged.

## One-Time Google Cloud Setup

```bash
gcloud config set project "$GCP_PROJECT_ID"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com
gcloud artifacts repositories create vaudtaxai \
  --repository-format=docker \
  --location=europe-west6 \
  --description="VaudTaxAI Cloud Run images"
```

## Runtime Secrets

Keep `.env` local only. Production values should live in Secret Manager and be
mounted into Cloud Run as secret environment variables:

```bash
gcloud secrets create AZURE_OPENAI_API_KEY --replication-policy=automatic
gcloud secrets create AZURE_OPENAI_ENDPOINT --replication-policy=automatic
gcloud secrets create AZURE_OPENAI_DEPLOYMENT_RAG --replication-policy=automatic
gcloud secrets create AZURE_OPENAI_DEPLOYMENT_EXTRACTION --replication-policy=automatic
gcloud secrets create AZURE_OPENAI_EMBEDDING_DEPLOYMENT --replication-policy=automatic
gcloud secrets create GROQ_API_KEY --replication-policy=automatic
gcloud secrets create SUPABASE_URL --replication-policy=automatic
gcloud secrets create SUPABASE_SERVICE_ROLE_KEY --replication-policy=automatic
```

Only grant the Cloud Run runtime service account access to the secrets it needs.
Do not print, commit, or paste secret values into GitHub Actions logs.

## Manual Build And Deploy

The helper script in this directory builds the container, pushes it to Artifact
Registry, and deploys it to Cloud Run. It assumes the runtime secrets are
already configured on the service or provided through the `--set-secrets` flags
you add during the first production setup.

The Docker image uses `requirements-cloudrun.txt`, a lean runtime dependency
set. The broader `requirements.txt` remains for desktop/dev continuity and still
contains legacy adapters that are not needed in the Cloud Run web process.

```bash
infra/gcp/deploy-cloud-run.sh
```

The first production deployment should be reviewed manually in Google Cloud
Console before DNS is pointed at the service.

## Custom Domain

1. In Cloud Run, add a custom domain mapping for `tax-gpt.online`.
2. Add a second mapping for `www.tax-gpt.online`.
3. In Namecheap DNS, create the records Google provides for each mapping.
4. Wait for Google-managed TLS certificates to become active.
5. Confirm both hostnames redirect or serve the same app.

## Logging, Budgets, And Safety

- Cloud Run writes request and container logs to Cloud Logging by default.
- Create a Google Cloud budget alert before public launch.
- Keep the app-level token-budget guard enabled; it is separate from Google
  Cloud billing controls because Azure OpenAI remains the model provider.
- Use Cloud Run max instances and concurrency limits during the MVP launch to
  avoid surprise spend.
