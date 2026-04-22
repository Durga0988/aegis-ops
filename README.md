# 🛡️ Aegis-Ops: AI-Enhanced Self-Healing Infrastructure Pipeline

> An end-to-end DevSecOps platform that uses AI to detect, diagnose, and automatically remediate Kubernetes infrastructure failures — without human intervention.

![Architecture](docs/aegis-ops-architecture.png)

---

## 🏗️ Architecture Overview

```
Developer → GitHub → CI/CD Pipeline → Docker → GHCR → Helm → Kubernetes
                                                              ↓
                                              Prometheus → Alertmanager
                                                              ↓
                                                     AI Agent (Python)
                                                     ↓           ↓
                                              GitHub Action   Slack/Discord
                                              (Self-Heal)     (Notify)
```

### The Four Stages

| Stage | Component | Purpose |
|-------|-----------|---------|
| **1. CI/CD** | GitHub Actions | Lint → Scan → Build → Push → Deploy |
| **2. Observability** | Prometheus + Grafana | Monitor metrics, detect anomalies |
| **3. AI Engine** | Python FastAPI + LLM | Root Cause Analysis, decision making |
| **4. Self-Healing** | GitHub Actions + Helm | Auto-scale, rollback, restart |

---

## 🛠️ Tech Stack

- **Container Runtime:** Docker (Multi-stage builds)
- **Orchestration:** Kubernetes (Minikube/K3s for local dev)
- **Package Manager:** Helm 3
- **CI/CD:** GitHub Actions
- **Security:** Trivy, Super-Linter, Hadolint
- **Monitoring:** Prometheus, Grafana, Alertmanager
- **AI/LLM:** OpenAI GPT-4 / Ollama (local) / Rule-based fallback
- **Language:** Python 3.12, FastAPI
- **Notifications:** Slack, Discord
- **Registry:** GitHub Container Registry (GHCR)

---

## 📁 Project Structure

```
aegis-ops/
├── .github/workflows/
│   ├── ci-cd-pipeline.yml          # Stage 1: Full CI/CD pipeline
│   └── self-healing.yml            # Stage 4: Auto-recovery actions
├── app/
│   ├── main.py                     # FastAPI app with Prometheus metrics
│   ├── Dockerfile                  # Multi-stage Docker build
│   └── requirements.txt
├── ai-agent/
│   ├── webhook_server.py           # Alertmanager webhook receiver
│   ├── k8s_log_collector.py        # Kubernetes log fetcher
│   ├── root_cause_analyzer.py      # LLM-powered RCA engine
│   ├── healing_engine.py           # GitHub Actions trigger
│   ├── notifier.py                 # Slack/Discord notifications
│   ├── Dockerfile
│   └── requirements.txt
├── helm/aegis-app/
│   ├── Chart.yaml
│   ├── values.yaml                 # Dynamically updated by CI/CD & self-healing
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── hpa.yaml
│       └── serviceaccount.yaml
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus-config.yaml
│   │   ├── alert-rules.yaml
│   │   └── alertmanager-config.yaml
│   ├── grafana/
│   │   └── aegis-ops-dashboard.json
│   └── kube-manifests/
│       ├── prometheus-deployment.yaml
│       ├── alertmanager-deployment.yaml
│       └── grafana-deployment.yaml
├── k8s/
│   ├── namespace.yaml
│   ├── rbac.yaml
│   └── ai-agent-deployment.yaml
└── scripts/
    ├── setup-cluster.sh
    ├── deploy-monitoring.sh
    ├── deploy-app.sh
    ├── chaos-test.sh
    └── cleanup.sh
```

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop
- Minikube or K3s
- kubectl
- Helm 3
- Git

### Step 1: Clone & Setup Cluster

```bash
git clone https://github.com/YOUR_USERNAME/aegis-ops.git
cd aegis-ops

# Set your secrets
export GITHUB_TOKEN="ghp_your_token"
export OPENAI_API_KEY="sk-your-key"          # Optional: uses rule-based fallback
export SLACK_WEBHOOK_URL="https://hooks..."   # Optional

# Setup cluster
chmod +x scripts/*.sh
./scripts/setup-cluster.sh
```

### Step 2: Deploy Monitoring Stack

```bash
./scripts/deploy-monitoring.sh
# Prometheus: http://<minikube-ip>:30090
# Grafana:    http://<minikube-ip>:30030  (admin / aegis-ops-2024)
```

### Step 3: Deploy Application & AI Agent

```bash
./scripts/deploy-app.sh
# Test: kubectl port-forward svc/aegis-app 8000:80 -n aegis-ops
# Then: curl http://localhost:8000/health
```

### Step 4: Run Chaos Tests

```bash
# In a separate terminal, start port-forward:
kubectl port-forward svc/aegis-app 8000:80 -n aegis-ops

# Run chaos tests:
./scripts/chaos-test.sh
```

### Step 5: Watch Self-Healing in Action

```bash
# Watch AI Agent logs
kubectl logs -l app=aegis-ai-agent -n aegis-ops -f

# Check GitHub Actions for self-healing workflow runs
# Check Slack/Discord for incident reports
```

---

## 🔄 Self-Healing Flow

```
1. App starts leaking memory (chaos endpoint)
2. Prometheus detects memory > 200MB threshold
3. Alert rule fires → Alertmanager receives it
4. Alertmanager POSTs webhook to AI Agent
5. AI Agent fetches pod logs from Kubernetes API
6. AI Agent sends alert + logs to LLM for RCA
7. LLM returns: { action: "scale_up", confidence: 85% }
8. AI Agent triggers GitHub Action via repository_dispatch
9. GitHub Action updates Helm values.yaml (memory: 512Mi)
10. GitOps re-deploys with new resource limits
11. Slack/Discord receives incident report with full RCA
```

---

## 🧪 Chaos Endpoints

| Endpoint | Method | Effect |
|----------|--------|--------|
| `/chaos/memory-leak` | POST | Allocates 10MB per call |
| `/chaos/cpu-spike` | POST | Burns CPU for 5 seconds |
| `/chaos/crash` | POST | Returns HTTP 500 |
| `/chaos/clear` | POST | Clears leaked memory |

---

## 📊 Metrics Exposed

| Metric | Type | Description |
|--------|------|-------------|
| `aegis_http_requests_total` | Counter | Total HTTP requests |
| `aegis_http_request_duration_seconds` | Histogram | Request latency |
| `aegis_app_memory_usage_bytes` | Gauge | Current memory usage |
| `aegis_active_connections` | Gauge | Active connections |
| `aegis_errors_total` | Counter | Application errors |

---

## 🔐 GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions |

### Optional (for AI Agent inside K8s):

| Secret | Purpose |
|--------|---------|
| `OPENAI_API_KEY` | For GPT-4 based RCA (falls back to rule-based) |
| `SLACK_WEBHOOK_URL` | Slack notifications |
| `DISCORD_WEBHOOK_URL` | Discord notifications |

---

## 📝 License

MIT License – Built by Durga Prasad as a DevOps portfolio project.
