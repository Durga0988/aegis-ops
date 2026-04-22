#!/bin/bash
# =============================================================================
# Aegis-Ops: Cluster Setup Script
# Sets up Minikube, namespaces, RBAC, and secrets
# =============================================================================
set -euo pipefail

echo "============================================"
echo "  Aegis-Ops: Cluster Setup"
echo "============================================"

# ---- Check prerequisites ----
for cmd in minikube kubectl helm docker; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ $cmd is required but not installed."
        exit 1
    fi
done
echo "✅ All prerequisites found"

# ---- Start Minikube ----
echo ""
echo "Starting Minikube cluster..."
minikube start \
    --cpus=4 \
    --memory=8192 \
    --driver=docker \
    --addons=metrics-server \
    --addons=ingress

echo "✅ Minikube cluster started"

# ---- Create Namespaces ----
echo ""
echo "Creating namespaces..."
kubectl apply -f k8s/namespace.yaml
echo "✅ Namespaces created"

# ---- Apply RBAC ----
echo ""
echo "Applying RBAC..."
kubectl apply -f k8s/rbac.yaml
echo "✅ RBAC applied"

# ---- Create Secrets ----
echo ""
echo "Creating secrets (update with your actual values)..."
kubectl create secret generic aegis-secrets \
    --namespace=aegis-ops \
    --from-literal=github-token="${GITHUB_TOKEN:-your-github-token}" \
    --from-literal=openai-api-key="${OPENAI_API_KEY:-your-openai-key}" \
    --from-literal=slack-webhook-url="${SLACK_WEBHOOK_URL:-}" \
    --from-literal=discord-webhook-url="${DISCORD_WEBHOOK_URL:-}" \
    --dry-run=client -o yaml | kubectl apply -f -
echo "✅ Secrets created"

echo ""
echo "============================================"
echo "  ✅ Cluster setup complete!"
echo "  Next: Run ./scripts/deploy-monitoring.sh"
echo "============================================"
