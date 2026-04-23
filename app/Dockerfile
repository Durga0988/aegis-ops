# =============================================================================
# Aegis-Ops: Multi-Stage Docker Build
# Stage 1 – Build dependencies in a heavier image
# Stage 2 – Copy only the runtime artefacts into a slim image
# =============================================================================

# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .

# ---- Stage 2: Runtime ----
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="aegis-ops-app" \
      org.opencontainers.image.description="Aegis-Ops Self-Healing Microservice" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/Durga0988/aegis-ops"

# Create non-root user for security
RUN groupadd -r aegis && useradd -r -g aegis aegis

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local
COPY --from=builder /build /app

# Switch to non-root user
USER aegis

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); r.raise_for_status()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
