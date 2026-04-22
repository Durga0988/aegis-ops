"""
Aegis-Ops: Sample Microservice Application
A FastAPI-based application with Prometheus metrics instrumentation,
health checks, and intentional chaos endpoints for testing self-healing.
"""

import os
import time
import logging
import psutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.responses import Response
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegis-app")

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "aegis_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "aegis_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)
MEMORY_USAGE = Gauge(
    "aegis_app_memory_usage_bytes",
    "Current memory usage of the application in bytes",
)
ACTIVE_CONNECTIONS = Gauge(
    "aegis_active_connections",
    "Number of active connections",
)
ERROR_COUNT = Counter(
    "aegis_errors_total",
    "Total number of application errors",
    ["error_type"],
)

# ---------------------------------------------------------------------------
# In-memory "leak" store used by the /chaos/* endpoints
# ---------------------------------------------------------------------------
memory_leak_store: list[bytes] = []


# ---------------------------------------------------------------------------
# Lifespan – background task to continuously expose memory gauge
# ---------------------------------------------------------------------------
async def _update_memory_gauge():
    """Push current RSS into the Prometheus gauge every call."""
    process = psutil.Process(os.getpid())
    MEMORY_USAGE.set(process.memory_info().rss)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Aegis-Ops application starting up …")
    yield
    logger.info("Aegis-Ops application shutting down …")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Aegis-Ops Microservice",
    description="A self-healing demo microservice with Prometheus metrics",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware – instrument every request
# ---------------------------------------------------------------------------
@app.middleware("http")
async def metrics_middleware(request, call_next):
    ACTIVE_CONNECTIONS.inc()
    start = time.time()
    try:
        response = await call_next(request)
        duration = time.time() - start
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)
        return response
    except Exception as exc:
        ERROR_COUNT.labels(error_type=type(exc).__name__).inc()
        raise
    finally:
        ACTIVE_CONNECTIONS.dec()
        await _update_memory_gauge()


# ---------------------------------------------------------------------------
# Core Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint – simple health banner."""
    return {
        "service": "aegis-ops",
        "status": "healthy",
        "version": "1.0.0",
        "message": "Aegis-Ops Microservice is running",
    }


@app.get("/health")
async def health_check():
    """Kubernetes liveness probe."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    return {"status": "ready", "timestamp": time.time()}


@app.get("/metrics")
async def metrics():
    """Prometheus scrape endpoint."""
    await _update_memory_gauge()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/api/status")
async def app_status():
    """Return detailed application status."""
    process = psutil.Process(os.getpid())
    return {
        "service": "aegis-ops",
        "status": "running",
        "uptime_seconds": time.time() - process.create_time(),
        "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
        "cpu_percent": process.cpu_percent(),
        "leak_store_items": len(memory_leak_store),
    }


# ---------------------------------------------------------------------------
# Chaos Engineering Endpoints  (used to simulate failures for self-healing)
# ---------------------------------------------------------------------------
@app.post("/chaos/memory-leak")
async def simulate_memory_leak():
    """
    Allocate ~10 MB of junk data per call.
    Prometheus will detect the rising memory gauge and Alertmanager will fire.
    """
    chunk = b"X" * (10 * 1024 * 1024)  # 10 MB
    memory_leak_store.append(chunk)
    total_mb = len(memory_leak_store) * 10
    logger.warning(f"CHAOS: Memory leak simulated – total leaked: {total_mb} MB")
    return {
        "chaos": "memory_leak",
        "leaked_mb": total_mb,
        "chunks": len(memory_leak_store),
    }


@app.post("/chaos/cpu-spike")
async def simulate_cpu_spike():
    """Burn CPU for ~5 seconds to trigger CPU alerts."""
    logger.warning("CHAOS: CPU spike initiated")
    end = time.time() + 5
    while time.time() < end:
        _ = sum(i * i for i in range(10_000))
    return {"chaos": "cpu_spike", "duration_seconds": 5}


@app.post("/chaos/crash")
async def simulate_crash():
    """Return HTTP 500 to simulate an application crash."""
    logger.error("CHAOS: Application crash simulated!")
    ERROR_COUNT.labels(error_type="SimulatedCrash").inc()
    raise HTTPException(status_code=500, detail="Simulated application crash")


@app.post("/chaos/clear")
async def clear_memory_leak():
    """Reset the memory leak store (used after self-healing)."""
    memory_leak_store.clear()
    logger.info("Memory leak store cleared")
    return {"status": "cleared", "leaked_mb": 0}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("APP_PORT", "8000")),
        reload=False,
    )
