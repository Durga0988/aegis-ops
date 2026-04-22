"""
Aegis-Ops: Kubernetes Log Collector
=====================================
Connects to the Kubernetes API and extracts pod logs for the AI agent
to analyze. Supports both in-cluster and local (kubeconfig) auth.
"""

import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger("aegis-ai-agent.k8s")


class K8sLogCollector:
    """Collects logs and metadata from Kubernetes pods."""

    def __init__(self, namespace: str = "aegis-ops"):
        self.namespace = namespace
        self._init_k8s_client()

    def _init_k8s_client(self):
        """Initialize the Kubernetes client (in-cluster or kubeconfig)."""
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            try:
                config.load_kube_config()
                logger.info("Loaded kubeconfig from default location")
            except config.ConfigException:
                logger.warning(
                    "Could not load Kubernetes config – "
                    "log collection will return placeholder data"
                )

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def get_pod_logs(
        self,
        pod_name: str,
        namespace: str | None = None,
        tail_lines: int = 150,
        container: str | None = None,
    ) -> str:
        """
        Fetch the last N lines of logs from a specific pod.

        If the exact pod name is not found, tries to find pods by label
        selector matching the app name.
        """
        ns = namespace or self.namespace
        try:
            # Try exact pod name first
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=ns,
                tail_lines=tail_lines,
                container=container,
                timestamps=True,
            )
            logger.info(
                "Successfully fetched %d lines of logs from %s/%s",
                len(logs.splitlines()),
                ns,
                pod_name,
            )
            return logs

        except ApiException as e:
            if e.status == 404:
                logger.warning(
                    "Pod %s not found, searching by label selector", pod_name
                )
                return self._get_logs_by_label(pod_name, ns, tail_lines)
            else:
                logger.error("K8s API error fetching logs: %s", str(e))
                return f"[ERROR] Failed to fetch logs: {e.reason}"

        except Exception as e:
            logger.error("Unexpected error fetching logs: %s", str(e))
            return f"[ERROR] Log collection failed: {str(e)}"

    def _get_logs_by_label(
        self, app_name: str, namespace: str, tail_lines: int
    ) -> str:
        """Fall back to finding pods by the app label."""
        try:
            # Extract base app name (strip random suffixes)
            base_name = "-".join(app_name.split("-")[:2])
            label_selector = f"app={base_name}"

            pods = self.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector,
            )

            if not pods.items:
                return f"[WARNING] No pods found with label {label_selector}"

            # Get logs from the first matching pod
            pod = pods.items[0]
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod.metadata.name,
                namespace=namespace,
                tail_lines=tail_lines,
                timestamps=True,
            )
            logger.info(
                "Fetched logs from matching pod: %s", pod.metadata.name
            )
            return logs

        except Exception as e:
            logger.error("Failed to fetch logs by label: %s", str(e))
            return f"[ERROR] Label-based log collection failed: {str(e)}"

    def get_pod_events(
        self, pod_name: str, namespace: str | None = None
    ) -> list[dict]:
        """Fetch Kubernetes events related to a specific pod."""
        ns = namespace or self.namespace
        try:
            field_selector = f"involvedObject.name={pod_name}"
            events = self.core_v1.list_namespaced_event(
                namespace=ns,
                field_selector=field_selector,
            )
            return [
                {
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "count": event.count,
                    "last_seen": (
                        event.last_timestamp.isoformat()
                        if event.last_timestamp
                        else "N/A"
                    ),
                }
                for event in events.items
            ]
        except Exception as e:
            logger.error("Failed to fetch pod events: %s", str(e))
            return []

    def get_pod_status(
        self, pod_name: str, namespace: str | None = None
    ) -> dict:
        """Get detailed status information for a pod."""
        ns = namespace or self.namespace
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=ns)
            container_statuses = []
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    container_statuses.append(
                        {
                            "name": cs.name,
                            "ready": cs.ready,
                            "restart_count": cs.restart_count,
                            "state": str(cs.state),
                        }
                    )
            return {
                "phase": pod.status.phase,
                "conditions": [
                    {"type": c.type, "status": c.status}
                    for c in (pod.status.conditions or [])
                ],
                "container_statuses": container_statuses,
            }
        except Exception as e:
            logger.error("Failed to get pod status: %s", str(e))
            return {"error": str(e)}

    def get_deployment_info(
        self, deployment_name: str, namespace: str | None = None
    ) -> dict:
        """Get deployment information including current replicas and images."""
        ns = namespace or self.namespace
        try:
            dep = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, namespace=ns
            )
            return {
                "name": dep.metadata.name,
                "replicas": dep.spec.replicas,
                "available_replicas": dep.status.available_replicas or 0,
                "ready_replicas": dep.status.ready_replicas or 0,
                "images": [
                    c.image for c in dep.spec.template.spec.containers
                ],
            }
        except Exception as e:
            logger.error("Failed to get deployment info: %s", str(e))
            return {"error": str(e)}
