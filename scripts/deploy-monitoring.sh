#!/bin/bash
# =============================================================================
# Aegis-Ops: Deploy Monitoring Stack
# Deploys Prometheus, Alertmanager, and Grafana
# =============================================================================
set -euo pipefail

echo "============================================"
echo "  Aegis-Ops: Deploy Monitoring"
echo "============================================"

# ---- Create ConfigMaps from config files ----
echo "Creating Prometheus ConfigMaps..."
kubectl create configmap prometheus-config \
    --namespace=monitoring \
    --from-file=prometheus.yml=monitoring/prometheus/prometheus-config.yaml \
    --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap prometheus-alert-rules \
    --namespace=monitoring \
    --from-file=alert-rules.yaml=monitoring/prometheus/alert-rules.yaml \
    --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap alertmanager-config \
    --namespace=monitoring \
    --from-file=alertmanager.yml=monitoring/prometheus/alertmanager-config.yaml \
    --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap grafana-dashboards \
    --namespace=monitoring \
    --from-file=aegis-ops-dashboard.json=monitoring/grafana/aegis-ops-dashboard.json \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✅ ConfigMaps created"

# ---- Deploy Prometheus ----
echo ""
echo "Deploying Prometheus..."
kubectl apply -f monitoring/kube-manifests/prometheus-deployment.yaml
echo "✅ Prometheus deployed"

# ---- Deploy Alertmanager ----
echo ""
echo "Deploying Alertmanager..."
kubectl apply -f monitoring/kube-manifests/alertmanager-deployment.yaml
echo "✅ Alertmanager deployed"

# ---- Deploy Grafana ----
echo ""
echo "Deploying Grafana..."
kubectl apply -f monitoring/kube-manifests/grafana-deployment.yaml
echo "✅ Grafana deployed"

# ---- Wait for pods ----
echo ""
echo "Waiting for monitoring pods to be ready..."
kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=120s || true
kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=120s || true

echo ""
echo "============================================"
echo "  ✅ Monitoring stack deployed!"
echo ""
echo "  Prometheus: http://$(minikube ip):30090"
echo "  Grafana:    http://$(minikube ip):30030"
echo "    User: admin / Pass: aegis-ops-2024"
echo ""
echo "  Next: Run ./scripts/deploy-app.sh"
echo "============================================"
