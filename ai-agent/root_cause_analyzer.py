"""
Aegis-Ops: Root Cause Analyzer (LLM-powered)
Sends alert metadata + K8s logs to an LLM for Root Cause Analysis.
Supports: OpenAI, Ollama (local), and rule-based fallback.
"""

import os, json, logging, httpx

logger = logging.getLogger("aegis-ai-agent.rca")

SYSTEM_PROMPT = """You are an expert SRE. Analyze the alert and logs, then respond with ONLY this JSON:
{
    "root_cause": "concise root cause description",
    "category": "memory_leak|cpu_spike|crash_loop|network_error|resource_limits|configuration_error|unknown",
    "action": "scale_up|rollback|restart|none",
    "confidence": 85,
    "explanation": "detailed technical explanation",
    "risk_level": "low|medium|high"
}
Actions: scale_up=resource limits hit, rollback=bad deploy, restart=transient issue, none=needs human.
Only recommend action if confidence >= 70%."""


class RootCauseAnalyzer:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL", "gpt-4")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")

    def analyze(self, alert_name: str, severity: str, description: str, pod_name: str, logs: str) -> dict:
        prompt = self._build_prompt(alert_name, severity, description, pod_name, logs)
        if self.api_key:
            result = self._call_openai(prompt)
            if result:
                return result
        result = self._call_ollama(prompt)
        if result:
            return result
        return self._rule_based_analysis(alert_name, severity, logs)

    def _build_prompt(self, alert_name, severity, description, pod_name, logs) -> str:
        truncated = logs[-4000:] if len(logs) > 4000 else logs
        return f"Alert: {alert_name}\nSeverity: {severity}\nDescription: {description}\nPod: {pod_name}\n\nLogs:\n```\n{truncated}\n```"

    def _call_openai(self, user_prompt: str) -> dict | None:
        try:
            with httpx.Client(timeout=30.0) as c:
                r = c.post("https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}], "temperature": 0.2, "max_tokens": 500})
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"): content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                return json.loads(content)
        except Exception as e:
            logger.error("OpenAI failed: %s", e)
            return None

    def _call_ollama(self, user_prompt: str) -> dict | None:
        try:
            with httpx.Client(timeout=60.0) as c:
                r = c.post(f"{self.ollama_url}/api/generate",
                    json={"model": self.ollama_model, "prompt": f"{SYSTEM_PROMPT}\n\n{user_prompt}", "stream": False, "format": "json"})
                r.raise_for_status()
                return json.loads(r.json().get("response", ""))
        except Exception as e:
            logger.warning("Ollama unavailable: %s", e)
            return None

    def _rule_based_analysis(self, alert_name: str, severity: str, logs: str) -> dict:
        al, ll = alert_name.lower(), logs.lower()
        if "memory" in al or "oom" in ll:
            return {"root_cause": "High memory – possible leak", "category": "memory_leak",
                    "action": "scale_up" if severity == "critical" else "restart", "confidence": 75,
                    "explanation": "Memory alert detected, recommending resource adjustment", "risk_level": "medium"}
        if "cpu" in al or "throttl" in ll:
            return {"root_cause": "CPU throttling detected", "category": "cpu_spike",
                    "action": "scale_up", "confidence": 70, "explanation": "CPU alert, scaling up", "risk_level": "medium"}
        if "crash" in al or "backoff" in ll:
            return {"root_cause": "Pod crash-looping", "category": "crash_loop",
                    "action": "rollback", "confidence": 80, "explanation": "Crash loop, rolling back", "risk_level": "high"}
        if "error" in al:
            return {"root_cause": "High error rate", "category": "configuration_error",
                    "action": "restart", "confidence": 65, "explanation": "Error rate spike, restarting", "risk_level": "medium"}
        return {"root_cause": f"Unknown: {alert_name}", "category": "unknown",
                "action": "none", "confidence": 30, "explanation": "Needs human investigation", "risk_level": "high"}
