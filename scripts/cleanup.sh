#!/bin/bash
# Aegis-Ops: Cleanup Script
set -euo pipefail

echo "Cleaning up Aegis-Ops..."
helm uninstall aegis-app -n aegis-ops 2>/dev/null || true
kubectl delete -f k8s/ai-agent-deployment.yaml 2>/dev/null || true
kubectl delete -f monitoring/kube-manifests/ 2>/dev/null || true
kubectl delete namespace aegis-ops 2>/dev/null || true
kubectl delete namespace monitoring 2>/dev/null || true
echo "✅ Cleanup complete"
