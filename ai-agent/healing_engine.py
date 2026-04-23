"""
Aegis-Ops: Healing Engine
===========================
Triggers self-healing GitHub Actions via the GitHub REST API
(repository_dispatch). This is the "hand" that executes the AI's decisions.
"""

import os
import json
import logging
from datetime import datetime, timezone
import httpx

logger = logging.getLogger("aegis-ai-agent.healer")


class HealingEngine:
    """Triggers GitHub Actions workflows for automated remediation."""

    def __init__(self, github_token: str = "", github_repo: str = ""):
        self.token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.repo = github_repo or os.getenv("GITHUB_REPO", "Durga0988/aegis-ops")
        self.api_base = "https://api.github.com"

    def trigger_healing(
        self,
        action: str,
        alert_name: str,
        severity: str,
        root_cause: str,
        stable_tag: str = "stable",
    ) -> bool:
        """
        Trigger a self-healing GitHub Action via repository_dispatch.

        Args:
            action: One of 'scale_up', 'rollback', 'restart'
            alert_name: Name of the alert that triggered healing
            severity: Alert severity level
            root_cause: AI-determined root cause
            stable_tag: Tag to rollback to (used for rollback action)

        Returns:
            True if the GitHub Action was triggered successfully
        """
        if not self.token:
            logger.error("GITHUB_TOKEN not set – cannot trigger healing")
            return False

        url = f"{self.api_base}/repos/{self.repo}/dispatches"

        payload = {
            "event_type": "self-healing",
            "client_payload": {
                "action": action,
                "alert_name": alert_name,
                "severity": severity,
                "root_cause": root_cause,
                "stable_tag": stable_tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "triggered_by": "aegis-ai-agent",
            },
        }

        logger.info("Triggering GitHub Action: %s", json.dumps(payload, indent=2))

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(
                    url,
                    headers={
                        "Authorization": f"token {self.token}",
                        "Accept": "application/vnd.github.v3+json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if response.status_code == 204:
                    logger.info(
                        "�... Self-healing GitHub Action triggered: action=%s",
                        action,
                    )
                    return True
                else:
                    logger.error(
                        "❌ GitHub API returned %d: %s",
                        response.status_code,
                        response.text,
                    )
                    return False

        except Exception as e:
            logger.error("Failed to trigger GitHub Action: %s", str(e))
            return False

    def get_workflow_status(self, run_id: int) -> dict:
        """Check the status of a triggered workflow run."""
        try:
            url = f"{self.api_base}/repos/{self.repo}/actions/runs/{run_id}"
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    url,
                    headers={
                        "Authorization": f"token {self.token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "status": data.get("status"),
                    "conclusion": data.get("conclusion"),
                    "html_url": data.get("html_url"),
                }
        except Exception as e:
            logger.error("Failed to check workflow status: %s", str(e))
            return {"error": str(e)}


