# 🚀 Aegis-Ops: Step-by-Step Execution Guide

This guide walks you through running the project from scratch on your Windows machine.

---

## 📋 Phase 0: Install Prerequisites

You need these tools installed. Open **PowerShell as Administrator** and run:

### 1. Docker Desktop
```
# Download from: https://www.docker.com/products/docker-desktop/
# After install, enable "Use WSL 2 based engine" in Settings
```

### 2. Minikube (Local Kubernetes)
```powershell
winget install Kubernetes.minikube
```

### 3. kubectl
```powershell
winget install Kubernetes.kubectl
```

### 4. Helm 3
```powershell
winget install Helm.Helm
```

### 5. Git (if not already installed)
```powershell
winget install Git.Git
```

> [!IMPORTANT]
> After installing, **restart your terminal** so all commands are on PATH.

Verify with:
```powershell
docker --version
minikube version
kubectl version --client
helm version
```

---

## 📋 Phase 1: Configure the Project

### Step 1.1 — Replace Placeholders

Open a PowerShell terminal and navigate to the project:

```powershell
cd "C:\Users\Durga prasad\.gemini\antigravity\scratch\aegis-ops"
```

Replace `YOUR_USERNAME` with your actual GitHub username in these files:

| File | What to Change |
|------|---------------|
| `helm\aegis-app\values.yaml` | `image.repository` line |
| `k8s\ai-agent-deployment.yaml` | Container image reference |
| `ai-agent\healing_engine.py` | `self.repo` default value |

> [!TIP]
> Quick find-and-replace in PowerShell:
> ```powershell
> # Replace YOUR_USERNAME across all files (preview first)
> Get-ChildItem -Recurse -Include *.yaml,*.yml,*.py | ForEach-Object {
>     (Get-Content $_.FullName) -replace 'YOUR_USERNAME', 'YourActualGitHubUsername' |
>     Set-Content $_.FullName
> }
> ```

### Step 1.2 — Initialize Git Repository

```powershell
cd "C:\Users\Durga prasad\.gemini\antigravity\scratch\aegis-ops"
git init
git add .
git commit -m "feat: initial Aegis-Ops project"
```

### Step 1.3 — Push to GitHub

```powershell
# Create repo on GitHub first (github.com/new), then:
git remote add origin https://github.com/YOUR_USERNAME/aegis-ops.git
git branch -M main
git push -u origin main
```

---

## 📋 Phase 2: Test Locally WITHOUT Kubernetes (Quick Validation)

Before touching Kubernetes, validate the app runs locally:

### Step 2.1 — Run the App Directly

```powershell
cd "C:\Users\Durga prasad\.gemini\antigravity\scratch\aegis-ops\app"

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

### Step 2.2 — Test the Endpoints

Open a **new terminal** and test:

```powershell
# Health check
curl http://localhost:8000/health

# App status
curl http://localhost:8000/api/status

# Prometheus metrics
curl http://localhost:8000/metrics

# Simulate memory leak
curl -X POST http://localhost:8000/chaos/memory-leak

# Check status again (memory increased)
curl http://localhost:8000/api/status

# Clear the leak
curl -X POST http://localhost:8000/chaos/clear
```

> [!NOTE]
> If `curl` doesn't work in PowerShell, use `Invoke-RestMethod`:
> ```powershell
> Invoke-RestMethod http://localhost:8000/health
> Invoke-RestMethod http://localhost:8000/api/status
> Invoke-RestMethod -Method POST http://localhost:8000/chaos/memory-leak
> ```

### Step 2.3 — Test Docker Build

```powershell
cd "C:\Users\Durga prasad\.gemini\antigravity\scratch\aegis-ops"

# Build the Docker image
docker build -t aegis-app:latest ./app

# Run the container
docker run -d -p 8000:8000 --name aegis-app aegis-app:latest

# Test it
curl http://localhost:8000/health

# Check logs
docker logs aegis-app

# Stop and remove
docker stop aegis-app && docker rm aegis-app
```

✅ **If this works, your app and Docker image are validated!**

---

## 📋 Phase 3: Full Kubernetes Deployment

### Step 3.1 — Start Minikube

```powershell
# Start cluster with enough resources
minikube start --cpus=4 --memory=8192 --driver=docker

# Enable required addons
minikube addons enable metrics-server
minikube addons enable ingress

# Verify
kubectl cluster-info
kubectl get nodes
```

### Step 3.2 — Create Namespaces & RBAC

```powershell
cd "C:\Users\Durga prasad\.gemini\antigravity\scratch\aegis-ops"

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml

# Verify
kubectl get namespaces
```

### Step 3.3 — Create Secrets

```powershell
# Create secrets for the AI agent (replace with your actual values)
kubectl create secret generic aegis-secrets `
    --namespace=aegis-ops `
    --from-literal=github-token="ghp_your_github_pat_here" `
    --from-literal=openai-api-key="sk-your-key-or-leave-empty" `
    --from-literal=slack-webhook-url="" `
    --from-literal=discord-webhook-url=""
```

> [!TIP]
> **Don't have an OpenAI key?** No problem — the AI agent will automatically fall back to **rule-based analysis**. Just leave it empty.

### Step 3.4 — Deploy Monitoring Stack

```powershell
# Create ConfigMaps from your config files
kubectl create configmap prometheus-config `
    --namespace=monitoring `
    --from-file=prometheus.yml=monitoring/prometheus/prometheus-config.yaml `
    --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap prometheus-alert-rules `
    --namespace=monitoring `
    --from-file=alert-rules.yaml=monitoring/prometheus/alert-rules.yaml `
    --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap alertmanager-config `
    --namespace=monitoring `
    --from-file=alertmanager.yml=monitoring/prometheus/alertmanager-config.yaml `
    --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap grafana-dashboards `
    --namespace=monitoring `
    --from-file=aegis-ops-dashboard.json=monitoring/grafana/aegis-ops-dashboard.json `
    --dry-run=client -o yaml | kubectl apply -f -

# Deploy Prometheus, Alertmanager, Grafana
kubectl apply -f monitoring/kube-manifests/prometheus-deployment.yaml
kubectl apply -f monitoring/kube-manifests/alertmanager-deployment.yaml
kubectl apply -f monitoring/kube-manifests/grafana-deployment.yaml

# Wait for pods
kubectl get pods -n monitoring -w
```

### Step 3.5 — Access Monitoring UIs

```powershell
# Prometheus (open in separate terminal – keep running)
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
# → Open http://localhost:9090

# Grafana (open in another terminal)
kubectl port-forward svc/grafana 3000:3000 -n monitoring
# → Open http://localhost:3000
# → Login: admin / aegis-ops-2024
```

### Step 3.6 — Build & Deploy the Application

```powershell
# Point Docker to Minikube's Docker daemon
# (so images are available inside the cluster without pushing to GHCR)
minikube docker-env --shell powershell | Invoke-Expression

# Build images locally inside Minikube
docker build -t aegis-app:latest ./app
docker build -t aegis-ai-agent:latest ./ai-agent

# Deploy app via Helm
helm upgrade --install aegis-app ./helm/aegis-app `
    --namespace aegis-ops `
    --set image.repository=aegis-app `
    --set image.tag=latest `
    --set image.pullPolicy=Never `
    --wait --timeout 120s

# Deploy AI Agent
kubectl apply -f k8s/ai-agent-deployment.yaml

# Verify everything is running
kubectl get pods -n aegis-ops
kubectl get svc -n aegis-ops
```

### Step 3.7 — Access the Application

```powershell
# Port-forward the app (keep this terminal open)
kubectl port-forward svc/aegis-app 8000:80 -n aegis-ops

# Test it
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

---

## 📋 Phase 4: Chaos Testing (Trigger Self-Healing!)

This is the **demo moment** — simulating failures and watching the AI heal them.

### Step 4.1 — Open Monitoring Windows

Open 3 terminals side-by-side:

```powershell
# Terminal 1: Port-forward app
kubectl port-forward svc/aegis-app 8000:80 -n aegis-ops

# Terminal 2: Watch AI Agent logs (LIVE)
kubectl logs -l app=aegis-ai-agent -n aegis-ops -f

# Terminal 3: Watch all pods
kubectl get pods -n aegis-ops -w
```

### Step 4.2 — Simulate Memory Leak

In a **4th terminal**:

```powershell
# Hit the memory leak endpoint multiple times
Invoke-RestMethod -Method POST http://localhost:8000/chaos/memory-leak
Invoke-RestMethod -Method POST http://localhost:8000/chaos/memory-leak
Invoke-RestMethod -Method POST http://localhost:8000/chaos/memory-leak
Invoke-RestMethod -Method POST http://localhost:8000/chaos/memory-leak
Invoke-RestMethod -Method POST http://localhost:8000/chaos/memory-leak

# Check the status
Invoke-RestMethod http://localhost:8000/api/status
```

### Step 4.3 — Watch the Pipeline React

What happens now:
1. **Prometheus** detects memory > 200MB → Alert fires
2. **Alertmanager** sends webhook POST to AI Agent
3. **AI Agent** (Terminal 2) shows logs of RCA happening
4. **AI Agent** triggers GitHub Action via REST API
5. **GitHub Actions** tab shows "Self-Healing" workflow running
6. **Slack/Discord** receives incident report

### Step 4.4 — Simulate Other Failures

```powershell
# CPU Spike
Invoke-RestMethod -Method POST http://localhost:8000/chaos/cpu-spike

# Application Crash
try { Invoke-RestMethod -Method POST http://localhost:8000/chaos/crash } catch { $_.Exception.Message }

# Clear everything
Invoke-RestMethod -Method POST http://localhost:8000/chaos/clear
```

---

## 📋 Phase 5: CI/CD Pipeline (GitHub Actions)

Once you've pushed to GitHub, the CI/CD pipeline runs automatically on every push:

### What Triggers It
- Push to `main` or `develop` branch
- Changes in `app/` or `helm/` directories

### Watch It Run
1. Go to `https://github.com/YOUR_USERNAME/aegis-ops/actions`
2. You'll see the **"Aegis-Ops CI/CD Pipeline"** workflow
3. It runs: Lint → Security Scan → Docker Build → Push to GHCR → Update Helm

### To Trigger Self-Healing Manually
The AI agent triggers `self-healing.yml` via GitHub API. You can also test manually:

```powershell
# Trigger self-healing manually via GitHub API
$headers = @{
    "Authorization" = "token ghp_YOUR_TOKEN"
    "Accept" = "application/vnd.github.v3+json"
}
$body = @{
    event_type = "self-healing"
    client_payload = @{
        action = "scale_up"
        alert_name = "HighMemoryUsage"
        severity = "critical"
        root_cause = "Memory leak in application"
    }
} | ConvertTo-Json

Invoke-RestMethod -Method POST `
    -Uri "https://api.github.com/repos/YOUR_USERNAME/aegis-ops/dispatches" `
    -Headers $headers `
    -Body $body `
    -ContentType "application/json"
```

---

## 🧹 Cleanup

```powershell
# Remove app
helm uninstall aegis-app -n aegis-ops

# Remove AI agent
kubectl delete -f k8s/ai-agent-deployment.yaml

# Remove monitoring
kubectl delete -f monitoring/kube-manifests/

# Remove namespaces
kubectl delete namespace aegis-ops
kubectl delete namespace monitoring

# Stop Minikube
minikube stop

# (Optional) Delete cluster entirely
minikube delete
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `minikube start` fails | Ensure Docker Desktop is running. Try `minikube delete` then `minikube start` |
| Pods stuck in `ImagePullBackOff` | You didn't build images inside Minikube. Run `minikube docker-env --shell powershell \| Invoke-Expression` first |
| Prometheus not scraping app | Check pod annotations: `kubectl describe pod -l app=aegis-app -n aegis-ops` |
| AI Agent can't read logs | Verify RBAC: `kubectl auth can-i get pods/log --as system:serviceaccount:aegis-ops:aegis-ai-agent` |
| GitHub Action not triggered | Check your `GITHUB_TOKEN` has `repo` scope. Test the API call manually |
| `helm upgrade` fails | Run `helm lint ./helm/aegis-app` to check for template errors |
| Port-forward disconnects | Just restart it — this is normal for Minikube |

---

## 📊 Summary: What to Demo

For interviews/presentations, show this flow:

```
1. "Here's my app running in Kubernetes"          → curl /health
2. "I have Prometheus monitoring it"               → Show Grafana dashboard
3. "Watch me break it"                             → curl /chaos/memory-leak (x5)
4. "The AI detects it automatically"               → Show AI Agent logs
5. "It triggers a GitHub Action to fix it"          → Show GitHub Actions tab
6. "And notifies the team"                          → Show Slack/Discord message
7. "No human intervention required"                 → 🎤 drop
```
