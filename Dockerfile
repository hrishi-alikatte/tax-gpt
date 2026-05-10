FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    RAG_AUTO_BUILD_INDEX=1 \
    RAG_INDEX_DIR=/tmp/chroma_db_vd_2025_te3_large

WORKDIR /app

COPY requirements-cloudrun.txt pyproject.toml CLAUDE.md AGENTS.md ./
COPY main.py ./
COPY TaxAI2025 ./TaxAI2025
COPY demo ./demo
COPY docs ./docs
COPY data ./data

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-cloudrun.txt \
    && python -m pip install -e .

EXPOSE 8080

CMD ["python", "main.py"]
