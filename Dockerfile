FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    RAG_AUTO_BUILD_INDEX=true \
    RAG_INDEX_DIR=/tmp/chroma_db_vd_2025_te3_large

WORKDIR /app

# Install security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-cloudrun.txt pyproject.toml README.md ./
COPY main.py ./
COPY TaxAI2025 ./TaxAI2025
COPY demo ./demo
COPY docs ./docs
COPY data ./data

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-cloudrun.txt \
    && python -m pip install -e .

# Pre-build RAG index at container build time (faster cold start)
RUN python -c "from TaxAI2025.rag.ingest import build_index; build_index()" || echo "Index build deferred to startup"

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8080/healthz || exit 1

CMD ["python", "main.py"]
