# AegisPulse — Autonomous Multi-Agent SRE Incident Commander

**Student:** Prathamesh Linge | **Course:** Artificial Intelligence (BTCOC701) | **Activity:** CAS Activity-I

AegisPulse is a **Goal-Based, Model-Based, Utility-Based Multi-Agent SRE War-Room** that monitors live HTTP endpoints, resolves DNS-over-HTTPS health, correlates anomalies with recent public GitHub commits and Hacker News outage chatter, challenges false positives via an adversarial Critic sub-agent, and compiles MTTR-ranked remediation runbooks.

## Multi-Agent Hierarchy
- **Lead Agent:** `AegisPulse Incident Commander`
- **Sub-Agent 1:** `TelemetryProbeAgent` (Live HTTP latency probes + Google DoH DNS checks)
- **Sub-Agent 2:** `CommitCorrelatorAgent` (GitHub REST Commits API + HN Algolia outage signals)
- **Sub-Agent 3:** `HypothesisCriticAgent` (Bayesian false-positive guardrail & severity scoring)
- **Sub-Agent 4:** `RunbookStrategistAgent` (Utility-ranked remediation & rollback staging)

## Resilient 90/10 Intelligence Stack
- **90% Keyless Autonomous Engine:** All telemetry collection, baseline EWMA memory, commit suspicion scoring, and critic gating operate without any API key.
- **10% LLM Enrichment with Auto-Fallback:** Google Gemini (`gemini-3.1-flash-lite`) -> Groq (`qwen/qwen3.8-27b`) -> Universal Keyless Synthesizer.

## Local Run & Tests
```bash
pip install -r requirements.txt
pytest -q
streamlit run app.py
```
