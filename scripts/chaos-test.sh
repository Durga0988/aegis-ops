#!/bin/bash
# =============================================================================
# Aegis-Ops: Chaos Testing Script
# Simulates failures to trigger the self-healing pipeline
# =============================================================================
set -euo pipefail

APP_URL="${1:-http://localhost:8000}"

echo "============================================"
echo "  Aegis-Ops: Chaos Engineering Tests"
echo "  Target: ${APP_URL}"
echo "============================================"

# ---- Ensure port-forward is running ----
echo ""
echo "💡 Make sure port-forward is running:"
echo "   kubectl port-forward svc/aegis-app 8000:80 -n aegis-ops"
echo ""

# ---- Test 1: Health Check ----
echo "--- Test 1: Health Check ---"
curl -s "${APP_URL}/health" | python3 -m json.tool
echo ""

# ---- Test 2: Simulate Memory Leak ----
echo "--- Test 2: Simulating Memory Leak (3 rounds of 10MB each) ---"
for i in 1 2 3; do
    echo "  Round $i..."
    curl -s -X POST "${APP_URL}/chaos/memory-leak" | python3 -m json.tool
    sleep 2
done
echo ""

# ---- Test 3: Check Application Status ----
echo "--- Test 3: Application Status ---"
curl -s "${APP_URL}/api/status" | python3 -m json.tool
echo ""

# ---- Test 4: Simulate CPU Spike ----
echo "--- Test 4: Simulating CPU Spike (5 seconds) ---"
curl -s -X POST "${APP_URL}/chaos/cpu-spike" | python3 -m json.tool
echo ""

# ---- Test 5: Simulate Crash ----
echo "--- Test 5: Simulating Application Crash ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${APP_URL}/chaos/crash")
echo "  HTTP Status: ${HTTP_CODE} (expected: 500)"
echo ""

# ---- Test 6: Check Metrics ----
echo "--- Test 6: Prometheus Metrics ---"
curl -s "${APP_URL}/metrics" | grep "aegis_" | head -20
echo ""

echo "============================================"
echo "  ✅ Chaos tests complete!"
echo ""
echo "  Now watch:"
echo "  1. Prometheus: Check for fired alerts"
echo "  2. AI Agent logs: kubectl logs -l app=aegis-ai-agent -n aegis-ops -f"
echo "  3. GitHub Actions: Check for self-healing workflow runs"
echo "  4. Slack/Discord: Check for incident reports"
echo "============================================"
