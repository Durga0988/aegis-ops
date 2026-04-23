"""
Aegis-Ops AI Agent: Webhook Server
====================================
FastAPI service that receives alerts from Prometheus Alertmanager,
orchestrates log collection, root cause analysis, and triggers
self-healing actions via GitHub Actions.

This is the central "brain" of the Aegis-Ops self-healing pipeline.
"""

import os
import json
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from k8s_log_collector import K8sLogCollector
from root_cause_analyzer import RootCauseAnalyzer
from healing_engine import HealingEngine
from notifier import Notifier

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegis-ai-agent")

# ---------------------------------------------------------------------------
# Configuration (from environment variables)
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Durga0988/aegis-ops")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "aegis-ops")


# ---------------------------------------------------------------------------
# Initialize components
# ---------------------------------------------------------------------------
log_collector = K8sLogCollector(namespace=K8S_NAMESPACE)
analyzer = RootCauseAnalyzer(api_key=OPENAI_API_KEY)
healer = HealingEngine(github_token=GITHUB_TOKEN, github_repo=GITHUB_REPO)
notifier = Notifier(
    slack_webhook_url=SLACK_WEBHOOK_URL,
    discord_webhook_url=DISCORD_WEBHOOK_URL,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  AEGIS-OPS AI AGENT STARTING")
    logger.info("  Namespace : %s", K8S_NAMESPACE)
    logger.info("  Repo      : %s", GITHUB_REPO)
    logger.info("=" * 60)
    yield
    logger.info("Aegis-Ops AI Agent shutting down")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Aegis-Ops AI Agent",
    description="Self-healing infrastructure decision engine",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class AlertManagerPayload(BaseModel):
    """Schema for Prometheus Alertmanager webhook payload."""
    version: str = "4"
    groupKey: str = ""
    status: str = "firing"
    receiver: str = ""
    groupLabels: dict = {}
    commonLabels: dict = {}
    commonAnnotations: dict = {}
    externalURL: str = ""
    alerts: list[dict] = []


class HealingResponse(BaseModel):
    """Response from the AI healing pipeline."""
    alert_name: str
    severity: str
    root_cause: str
    action_taken: str
    github_action_triggered: bool
    timestamp: str


# ---------------------------------------------------------------------------
# Health Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "aegis-ai-agent"}


# ---------------------------------------------------------------------------
# MAIN ENDPOINT: Alertmanager Webhook Receiver
# ---------------------------------------------------------------------------
@app.post("/webhook/alertmanager", response_model=list[HealingResponse])
async def receive_alert(payload: AlertManagerPayload):
    """
    Main webhook endpoint hit by Prometheus Alertmanager.

    Flow:
    1. Parse the alert(s)
    2. For each firing alert:
       a. Collect Kubernetes logs from the affected pod
       b. Send alert metadata + logs to the LLM for Root Cause Analysis
       c. Based on the AI's decision, trigger the appropriate GitHub Action
       d. Notify the team via Slack / Discord
    3. Return a summary of all actions taken
    """
    logger.info("=" * 60)
    logger.info("INCOMING ALERT – Status: %s", payload.status)
    logger.info("Alerts count: %d", len(payload.alerts))
    logger.info("=" * 60)

    results: list[HealingResponse] = []

    for alert in payload.alerts:
        # Safety check: ensure alert is a dictionary
        if not isinstance(alert, dict):
            logger.warning("Expected alert to be a dictionary, but got %s", type(alert))
            continue

        if alert.get("status") != "firing":
            logger.info("Skipping resolved alert: %s", alert.get("labels", {}).get("alertname"))
            continue

        alert_name = alert.get("labels", {}).get("alertname", "Unknown")
        severity = alert.get("labels", {}).get("severity", "unknown")
        pod_name = alert.get("labels", {}).get("pod", "unknown")
        namespace = alert.get("labels", {}).get("namespace", K8S_NAMESPACE)
        description = alert.get("annotations", {}).get("description", "No description")

        logger.info("-" * 40)
        logger.info("Processing alert: %s", alert_name)
        logger.info("Severity: %s | Pod: %s", severity, pod_name)
        logger.info("-" * 40)

        try:
            # ----------------------------------------------------------
            # STEP 1: Collect Kubernetes Logs
            # ----------------------------------------------------------
            logger.info("[Step 1] Collecting logs from pod: %s", pod_name)
            logs = log_collector.get_pod_logs(
                pod_name=pod_name,
                namespace=namespace,
                tail_lines=150,
            )
            logger.info("[Step 1] Collected %d characters of logs", len(logs))

            # ----------------------------------------------------------
            # STEP 2: AI Root Cause Analysis
            # ----------------------------------------------------------
            logger.info("[Step 2] Sending to AI for Root Cause Analysis")
            analysis = analyzer.analyze(
                alert_name=alert_name,
                severity=severity,
                description=description,
                pod_name=pod_name,
                logs=logs,
            )
            root_cause = analysis.get("root_cause", "Unknown")
            recommended_action = analysis.get("action", "none")
            confidence = analysis.get("confidence", 0)
            explanation = analysis.get("explanation", "")

            logger.info("[Step 2] AI Analysis Complete:")
            logger.info("  Root Cause : %s", root_cause)
            logger.info("  Action     : %s", recommended_action)
            logger.info("  Confidence : %d%%", confidence)

            # ----------------------------------------------------------
            # STEP 3: Trigger Self-Healing GitHub Action
            # ----------------------------------------------------------
            github_triggered = False
            if confidence >= 70 and recommended_action != "none":
                logger.info("[Step 3] Triggering self-healing: %s", recommended_action)
                github_triggered = healer.trigger_healing(
                    action=recommended_action,
                    alert_name=alert_name,
                    severity=severity,
                    root_cause=root_cause,
                )
                logger.info("[Step 3] GitHub Action triggered: %s", github_triggered)
            else:
                logger.info(
                    "[Step 3] Skipping healing (confidence=%d%%, action=%s)",
                    confidence,
                    recommended_action,
                )

            # ----------------------------------------------------------
            # STEP 4: Notify Team
            # ----------------------------------------------------------
            logger.info("[Step 4] Sending notifications")
            await notifier.send_incident_report(
                alert_name=alert_name,
                severity=severity,
                root_cause=root_cause,
                action=recommended_action,
                explanation=explanation,
                confidence=confidence,
                pod_name=pod_name,
                github_triggered=github_triggered,
            )

            # Build response
            result = HealingResponse(
                alert_name=alert_name,
                severity=severity,
                root_cause=root_cause,
                action_taken=recommended_action,
                github_action_triggered=github_triggered,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            results.append(result)

        except Exception as e:
            logger.error("Error processing alert %s: %s", alert_name, str(e))
            results.append(
                HealingResponse(
                    alert_name=alert_name,
                    severity=severity,
                    root_cause=f"Error: {str(e)}",
                    action_taken="none",
                    github_action_triggered=False,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

    return results


# ---------------------------------------------------------------------------
# Manual trigger endpoint (for testing)
# ---------------------------------------------------------------------------
@app.post("/test/trigger")
async def manual_trigger(alert_name: str = "TestAlert", severity: str = "warning"):
    """Manually trigger the AI pipeline for testing purposes."""
    test_payload = AlertManagerPayload(
        status="firing",
        alerts=[
            {
                "status": "firing",
                "labels": {
                    "alertname": alert_name,
                    "severity": severity,
                    "pod": "aegis-app-test-pod",
                    "namespace": K8S_NAMESPACE,
                },
                "annotations": {
                    "description": f"Test alert: {alert_name}",
                },
            }
        ],
    )
    return await receive_alert(test_payload)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "webhook_server:app",
        host="0.0.0.0",
        port=int(os.getenv("AGENT_PORT", "5000")),
        reload=False,
    )


