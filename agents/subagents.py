"""Four specialized SRE Sub-Agents operating under AegisPulse Incident Commander."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .tools import (
    fetch_github_commits,
    fetch_hn_outage_signals,
    probe_http_endpoint,
    resolve_dns_doh,
)

SUSPECT_KEYWORDS = {
    "hotfix": 18,
    "rollback": 22,
    "timeout": 20,
    "memory": 17,
    "config": 15,
    "auth": 16,
    "tls": 18,
    "migration": 24,
    "cache": 14,
    "pool": 16,
    "retry": 13,
    "dns": 19,
}


@dataclass
class AgentTraceMessage:
    """Inter-agent bus message emitted during autonomous execution."""

    sender: str
    recipient: str
    phase: str
    content: str
    confidence: float


@dataclass
class SubAgentContext:
    """Shared blackboard passed across sub-agents during an incident sweep."""

    endpoints: list[str]
    target_repo: str
    service_keyword: str
    baseline_latency: dict[str, float]
    seen_shas: set[str]
    probes: list[dict[str, Any]] = field(default_factory=list)
    dns_checks: list[dict[str, Any]] = field(default_factory=list)
    commits: list[dict[str, Any]] = field(default_factory=list)
    hn_signals: list[dict[str, Any]] = field(default_factory=list)
    suspect_commits: list[dict[str, Any]] = field(default_factory=list)
    critic_verdict: dict[str, Any] = field(default_factory=dict)
    runbook: dict[str, Any] = field(default_factory=dict)
    messages: list[AgentTraceMessage] = field(default_factory=list)

    def emit(self, sender: str, recipient: str, phase: str, content: str, confidence: float = 0.9) -> None:
        self.messages.append(
            AgentTraceMessage(
                sender=sender,
                recipient=recipient,
                phase=phase,
                content=content,
                confidence=round(confidence, 2),
            )
        )


class TelemetryProbeAgent:
    """Sub-Agent 1: Executes live HTTP latency probes and DNS-over-HTTPS resolution in parallel."""

    name = "TelemetryProbeAgent"

    def run(self, ctx: SubAgentContext) -> None:
        def _probe_one(url: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
            probe = probe_http_endpoint(url)
            baseline = ctx.baseline_latency.get(probe["url"])
            drift_pct = 0.0
            if baseline and baseline > 0 and probe["ok"]:
                drift_pct = round(((probe["latency_ms"] - baseline) / baseline) * 100.0, 1)
            probe["baseline_ms"] = baseline or probe["latency_ms"]
            probe["drift_pct"] = drift_pct
            dns = resolve_dns_doh(probe["host"]) if probe["host"] else None
            return probe, dns

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(_probe_one, ctx.endpoints))

        for probe, dns in results:
            ctx.probes.append(probe)
            if dns is not None:
                ctx.dns_checks.append(dns)

        down_count = sum(1 for p in ctx.probes if not p["ok"])
        avg_lat = round(sum(p["latency_ms"] for p in ctx.probes) / max(len(ctx.probes), 1), 1)
        ctx.emit(
            self.name,
            "CommitCorrelatorAgent",
            "SENSE",
            f"Probed {len(ctx.probes)} endpoints (down={down_count}, avg={avg_lat}ms) and {len(ctx.dns_checks)} DNS zones.",
            confidence=0.96,
        )


class CommitCorrelatorAgent:
    """Sub-Agent 2: Correlates endpoint anomalies with recent GitHub commits and HN chatter."""

    name = "CommitCorrelatorAgent"

    def run(self, ctx: SubAgentContext) -> None:
        gh = fetch_github_commits(ctx.target_repo)
        hn = fetch_hn_outage_signals(ctx.service_keyword)
        ctx.commits = gh["commits"]
        ctx.hn_signals = hn["signals"]

        scored: list[dict[str, Any]] = []
        for idx, commit in enumerate(ctx.commits):
            msg_lower = commit["message"].lower()
            kw_hits = [kw for kw in SUSPECT_KEYWORDS if kw in msg_lower]
            kw_score = sum(SUSPECT_KEYWORDS[k] for k in kw_hits)
            recency_bonus = max(0, 20 - idx * 3)
            unseen_bonus = 15 if commit["full_sha"] not in ctx.seen_shas else 0
            suspicion = min(100, kw_score + recency_bonus + unseen_bonus)
            scored.append({**commit, "suspicion_score": suspicion, "matched_signals": kw_hits})

        scored.sort(key=lambda c: c["suspicion_score"], reverse=True)
        ctx.suspect_commits = scored[:5]

        top_sha = ctx.suspect_commits[0]["sha"] if ctx.suspect_commits else "none"
        top_score = ctx.suspect_commits[0]["suspicion_score"] if ctx.suspect_commits else 0
        ctx.emit(
            self.name,
            "HypothesisCriticAgent",
            "CORRELATE",
            f"Analyzed {len(ctx.commits)} GitHub commits ({gh['source']}) + {len(ctx.hn_signals)} HN signals. Top suspect `{top_sha}` score={top_score}.",
            confidence=0.88,
        )


class HypothesisCriticAgent:
    """Sub-Agent 3: Adversarial Bayesian critic rejecting false positives before escalation."""

    name = "HypothesisCriticAgent"

    def run(self, ctx: SubAgentContext) -> None:
        down_probes = [p for p in ctx.probes if not p["ok"]]
        high_drift = [p for p in ctx.probes if p.get("drift_pct", 0) > 50 or p.get("latency_ms", 0) > 1200]
        dns_failures = [d for d in ctx.dns_checks if not d.get("healthy")]
        max_commit_score = ctx.suspect_commits[0]["suspicion_score"] if ctx.suspect_commits else 0
        hn_pressure = sum(1 for s in ctx.hn_signals if s.get("points", 0) >= 30)

        risk = 8.0
        risk += len(down_probes) * 32.0
        risk += len(high_drift) * 14.0
        risk += len(dns_failures) * 20.0
        risk += (max_commit_score * 0.22) if (down_probes or high_drift) else (max_commit_score * 0.08)
        risk += min(15.0, hn_pressure * 5.0)
        risk = round(min(99.0, max(3.0, risk)), 1)

        if risk >= 70:
            severity = "SEV-1 CRITICAL"
            false_positive_guard = "Confirmed multi-signal outage/degradation; escalation justified."
        elif risk >= 42:
            severity = "SEV-2 DEGRADED"
            false_positive_guard = "Moderate latency drift or suspect change detected; recommend canary watch."
        else:
            severity = "SEV-3 NOMINAL"
            false_positive_guard = "Critic rejected false-positive escalation: endpoints & DNS within healthy bounds."

        ctx.critic_verdict = {
            "risk_score": risk,
            "severity": severity,
            "down_count": len(down_probes),
            "high_drift_count": len(high_drift),
            "dns_failures": len(dns_failures),
            "guardrail_note": false_positive_guard,
        }
        ctx.emit(
            self.name,
            "RunbookStrategistAgent",
            "CRITIQUE",
            f"Verdict={severity} (Risk {risk}/100). {false_positive_guard}",
            confidence=0.92,
        )


class RunbookStrategistAgent:
    """Sub-Agent 4: Computes utility-optimal remediation plan and rollback actions."""

    name = "RunbookStrategistAgent"

    def run(self, ctx: SubAgentContext) -> None:
        verdict = ctx.critic_verdict
        severity = verdict["severity"]
        top_commit = ctx.suspect_commits[0] if ctx.suspect_commits else None

        actions: list[dict[str, str]] = []
        if verdict["dns_failures"] > 0:
            actions.append(
                {
                    "priority": "P0",
                    "action": "Verify authoritative DNS A-records and flush edge resolver cache",
                    "utility": "High MTTR Gain",
                }
            )
        if verdict["down_count"] > 0 and top_commit:
            actions.append(
                {
                    "priority": "P0",
                    "action": f"Stage canary rollback check on commit {top_commit['sha']} ({top_commit['message'][:60]})",
                    "utility": "Direct Blast-Radius Containment",
                }
            )
        if verdict["high_drift_count"] > 0:
            actions.append(
                {
                    "priority": "P1",
                    "action": "Autoscale upstream worker pool + enable circuit-breaker timeout guard (2500ms)",
                    "utility": "Tail-Latency Stabilization",
                }
            )
        if not actions:
            actions.append(
                {
                    "priority": "P2",
                    "action": "Keep passive autonomous watch enabled; snapshot current latency as clean baseline",
                    "utility": "Zero-Intervention Stability",
                }
            )

        ctx.runbook = {
            "severity": severity,
            "actions": actions,
            "auto_remediation_safe": False,
            "human_approval_required": severity != "SEV-3 NOMINAL",
        }
        ctx.emit(
            self.name,
            "AegisPulse Commander",
            "ACT",
            f"Compiled {len(actions)} utility-ranked runbook step(s) for {severity}.",
            confidence=0.95,
        )
