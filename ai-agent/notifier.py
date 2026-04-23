"""
Aegis-Ops: Notifier
=====================
Sends AI-generated incident summaries to Slack and Discord channels.
"""

import os
import logging
from datetime import datetime, timezone
import httpx

logger = logging.getLogger("aegis-ai-agent.notifier")


class Notifier:
    """Sends incident reports to Slack and Discord."""

    def __init__(self, slack_webhook_url: str = "", discord_webhook_url: str = ""):
        self.slack_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")
        self.discord_url = discord_webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")

    async def send_incident_report(
        self,
        alert_name: str,
        severity: str,
        root_cause: str,
        action: str,
        explanation: str,
        confidence: int,
        pod_name: str,
        github_triggered: bool,
    ):
        """Send incident report to all configured channels."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        status_emoji = "ü"•" if severity == "critical" else "‚ö†Ô∏è"
        action_emoji = "‚ú..." if github_triggered else "‚è∏Ô∏è"

        if self.slack_url:
            await self._send_slack(
                alert_name, severity, root_cause, action,
                explanation, confidence, pod_name,
                github_triggered, timestamp, status_emoji, action_emoji,
            )

        if self.discord_url:
            await self._send_discord(
                alert_name, severity, root_cause, action,
                explanation, confidence, pod_name,
                github_triggered, timestamp, status_emoji, action_emoji,
            )

        logger.info("Notifications sent for alert: %s", alert_name)

    async def _send_slack(self, alert_name, severity, root_cause, action,
                          explanation, confidence, pod_name, github_triggered,
                          timestamp, status_emoji, action_emoji):
        """Send formatted message to Slack via webhook."""
        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} Aegis-Ops Incident Report",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Alert:*\n{alert_name}"},
                        {"type": "mrkdwn", "text": f"*Severity:*\n{severity.upper()}"},
                        {"type": "mrkdwn", "text": f"*Pod:*\n`{pod_name}`"},
                        {"type": "mrkdwn", "text": f"*Confidence:*\n{confidence}%"},
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*ü"ç Root Cause:*\n{root_cause}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*üìã Explanation:*\n{explanation}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{action_emoji} *Action Taken:* `{action}`\n"
                            f"*GitHub Action Triggered:* {'Yes ‚ú...' if github_triggered else 'No ‚ùå'}\n"
                            f"*Time:* {timestamp}"
                        ),
                    },
                },
                {"type": "divider"},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(self.slack_url, json=message)
                r.raise_for_status()
                logger.info("Slack notification sent")
        except Exception as e:
            logger.error("Slack notification failed: %s", e)

    async def _send_discord(self, alert_name, severity, root_cause, action,
                            explanation, confidence, pod_name, github_triggered,
                            timestamp, status_emoji, action_emoji):
        """Send formatted message to Discord via webhook."""
        color = 0xFF0000 if severity == "critical" else 0xFFA500
        message = {
            "embeds": [
                {
                    "title": f"{status_emoji} Aegis-Ops Incident Report",
                    "color": color,
                    "fields": [
                        {"name": "Alert", "value": alert_name, "inline": True},
                        {"name": "Severity", "value": severity.upper(), "inline": True},
                        {"name": "Pod", "value": f"`{pod_name}`", "inline": True},
                        {"name": "ü"ç Root Cause", "value": root_cause, "inline": False},
                        {"name": "üìã Explanation", "value": explanation, "inline": False},
                        {"name": f"{action_emoji} Action", "value": f"`{action}`", "inline": True},
                        {"name": "Confidence", "value": f"{confidence}%", "inline": True},
                        {"name": "Auto-Healed", "value": "Yes ‚ú..." if github_triggered else "No ‚ùå", "inline": True},
                    ],
                    "footer": {"text": f"Aegis-Ops AI Agent ‚Ä¢ {timestamp}"},
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(self.discord_url, json=message)
                r.raise_for_status()
                logger.info("Discord notification sent")
        except Exception as e:
            logger.error("Discord notification failed: %s", e)


