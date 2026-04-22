# Aegis-Ops AI Agent – Multi-Stage Docker Build
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
COPY . .

FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.title="aegis-ai-agent"
RUN groupadd -r aegis && useradd -r -g aegis aegis
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --from=builder /build /app
USER aegis
EXPOSE 5000
CMD ["uvicorn", "webhook_server:app", "--host", "0.0.0.0", "--port", "5000"]
