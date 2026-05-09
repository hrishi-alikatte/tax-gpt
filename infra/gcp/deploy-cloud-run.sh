#!/usr/bin/env bash
set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID before deploying}"
: "${GCP_REGION:=europe-west6}"
: "${ARTIFACT_REPOSITORY:=vaudtaxai}"
: "${CLOUD_RUN_SERVICE:=vaudtaxai-web}"

IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPOSITORY}/vaudtaxai:$(git rev-parse --short HEAD)"

gcloud config set project "${GCP_PROJECT_ID}"
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

gcloud artifacts repositories describe "${ARTIFACT_REPOSITORY}" \
  --location="${GCP_REGION}" >/dev/null 2>&1 \
  || gcloud artifacts repositories create "${ARTIFACT_REPOSITORY}" \
    --repository-format=docker \
    --location="${GCP_REGION}" \
    --description="VaudTaxAI Cloud Run images"

docker build -t "${IMAGE}" .
docker push "${IMAGE}"

gcloud run deploy "${CLOUD_RUN_SERVICE}" \
  --image="${IMAGE}" \
  --region="${GCP_REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --cpu=1 \
  --concurrency=20 \
  --max-instances=3
