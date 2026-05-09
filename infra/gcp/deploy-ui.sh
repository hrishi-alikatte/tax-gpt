#!/usr/bin/env bash
set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID before deploying}"
: "${GCP_REGION:=europe-west6}"
: "${ARTIFACT_REPOSITORY:=vaudtaxai}"
: "${UI_SERVICE_NAME:=vaudtaxai-ui}"

IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPOSITORY}/${UI_SERVICE_NAME}:$(git rev-parse --short HEAD)"

echo "Building UI image: ${IMAGE}..."
docker build -t "${IMAGE}" -f "Vaud Tax Guide/Dockerfile.ui" "Vaud Tax Guide"

echo "Pushing image..."
docker push "${IMAGE}"

echo "Deploying to Cloud Run..."
gcloud run deploy "${UI_SERVICE_NAME}" \
  --image="${IMAGE}" \
  --region="${GCP_REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=3000 \
  --memory=1Gi \
  --cpu=1 \
  --set-env-vars="VITE_API_BASE_URL=https://vaudtaxai-web-410743045655.europe-west6.run.app"
