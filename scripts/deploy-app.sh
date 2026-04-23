#!/bin/bash
# =============================================================================
# Aegis-Ops: Deploy Application & AI Agent
# =============================================================================
set -euo pipefail

echo "============================================"
echo "  Aegis-Ops: Deploy Application"
echo "============================================"

# ---- Build Docker images locally (using Minikube's Docker) ----
echo "Configuring Docker to use Minikube's daemon..."
eval $(minikube docker-env)

echo "Building application image..."
docker build -t aegis-app:latest ./app
echo "✅ Application image built"

echo "Building AI Agent image..."
docker build -t aegis-ai-agent:latest ./ai-agent
echo "✅ AI Agent image built"

# ---- Deploy app via Helm ----
echo ""
echo "Deploying application via Helm..."

# Override image for local dev (use local image instead of GHCR)
helm upgrade --install aegis-app ./helm/aegis-app \
    --namespace aegis-ops \
    --create-namespace \
    --set image.repository=aegis-app \
    --set image.tag=latest \
    --set image.pullPolicy=Never \
    --wait --timeout 120s

echo "✅ Application deployed via Helm"

# ---- Deploy AI Agent ----
echo ""
echo "Deploying AI Agent..."
# Update the image reference for local dev
sed 's|ghcr.io/Durga0988/aegis-ops/aegis-ai-agent:latest|aegis-ai-agent:latest|' \
    k8s/ai-agent-deployment.yaml | kubectl apply -f -
echo "✅ AI Agent deployed"

# ---- Wait for pods ----
echo ""
echo "Waiting for application pods..."
kubectl wait --for=condition=ready pod -l app=aegis-app -n aegis-ops --timeout=120s
kubectl wait --for=condition=ready pod -l app=aegis-ai-agent -n aegis-ops --timeout=120s

echo ""
echo "============================================"
echo "  ✅ Application deployed!"
echo ""
echo "  App URL:   http://$(minikube ip):$(kubectl get svc aegis-app -n aegis-ops -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo 'ClusterIP')"
echo "  AI Agent:  Running inside cluster"
echo ""
echo "  Test: kubectl port-forward svc/aegis-app 8000:80 -n aegis-ops"
echo "  Then: curl http://localhost:8000/health"
echo ""
echo "  Next: Run ./scripts/chaos-test.sh to test self-healing"
echo "============================================"
