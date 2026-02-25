# ============================================================
# Stage 1: Builder — install build tools + pip dependencies
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# Stage 2: Production — minimal runtime image
# ============================================================
FROM python:3.11-slim AS production

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy application code
COPY . .

# Own app files by appuser
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check — hits the FastAPI health endpoint every 30s
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" || exit 1

# Cloud Run injects PORT env var; default to 8000 for local dev
# --workers 4 for production concurrency
# --timeout-graceful-shutdown for clean shutdown on SIGTERM (Cloud Run sends SIGTERM)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4 --timeout-graceful-shutdown 30
