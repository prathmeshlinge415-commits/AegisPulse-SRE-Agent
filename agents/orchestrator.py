"""Lead AegisPulse Incident Commander orchestrating sub-agents, memory, and 10% LLM layer."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .llm_router import SynthesisResult, synthesize_with_fallback
from .memory import IncidentMemoryStore
from .subagents import (
    CommitCorrelatorAgent,
    HypothesisCriticAgent,
    RunbookStrategistAgent,
    SubAgentContext,
    TelemetryProbeAgent,
)


def _universal_sre_fallback(ctx: SubAgentContext) -> str:
    """Keyless deterministic executive war-room brief when Gemini/Groq are unavailable."""
    v = ctx.critic_verdict
    top_commit = ctx.suspect_commits[0] if ctx.suspect_commits else {}
    top_action = ctx.runbook["actions"][0]["action"] if ctx.runbook.get("actions") else "Continue monitoring"
    healthy = len(ctx.probes) - v["down_count"]
    return (
        f"### Autonomous War-Room Assessment ({v['severity']})\n"
        f"- **Service Health**: {healthy}/{len(ctx.probes)} endpoints reachable; "
        f"{v['high_drift_count']} latency drift alerts; {v['dns_failures']} DNS anomalies.\n"
        f"- **Change Correlation**: Top inspected commit `{top_commit.get('sha', 'N/A')}` "
        f"(suspicion {top_commit.get('suspicion_score', 0)}/100) — \"{top_commit.get('message', 'No commit delta')}\".\n"
        f"- **Critic Guardrail**: {v['guardrail_note']}\n"
        f"- **Recommended Lead Action**: {top_action} *(human approval gate enforced before any production rollback)*."
    )


class AegisPulseCommander:
    """Goal-based, Utility-based, Model-based Lead SRE Agent."""

    def __init__(self, memory_store: IncidentMemoryStore | None = None) -> None:
        self.memory = memory_store or IncidentMemoryStore()
        self.subagents = [
            TelemetryProbeAgent(),
            CommitCorrelatorAgent(),
            HypothesisCriticAgent(),
            RunbookStrategistAgent(),
        ]

    def run_cycle(
        self,
        endpoints: list[str],
        target_repo: str = "streamlit/streamlit",
        service_keyword: str = "github",
        gemini_key: str | None = None,
        groq_key: str | None = None,
    ) -> dict[str, Any]:
        """Execute full 4-subagent Sense -> Correlate -> Critique -> Act autonomous loop."""
        prior_state = self.memory.load()
        ctx = SubAgentContext(
            endpoints=[e.strip() for e in endpoints if e.strip()],
            target_repo=target_repo,
            service_keyword=service_keyword,
            baseline_latency=prior_state.get("baseline_latency_ms", {}),
            seen_shas=set(prior_state.get("seen_commit_shas", [])),
        )
        ctx.emit(
            "AegisPulse Commander",
            "TelemetryProbeAgent",
            "DELEGATE",
            f"Dispatching autonomous SRE sweep across {len(ctx.endpoints)} endpoints & repo `{target_repo}`.",
            confidence=0.98,
        )

        for agent in self.subagents:
            agent.run(ctx)

        prompt = (
            f"You are AegisPulse Incident Commander. Summarize this autonomous SRE sweep in 4 crisp bullet points "
            f"(Health, Root-Cause Signal, Critic Check, Top Action). Keep under 120 words.\n"
            f"Verdict: {ctx.critic_verdict}\n"
            f"Probes: {ctx.probes}\n"
            f"Top Suspect Commit: {ctx.suspect_commits[:2]}\n"
            f"Runbook: {ctx.runbook['actions']}"
        )
        synthesis: SynthesisResult = synthesize_with_fallback(
            prompt=prompt,
            system_instruction="Be concise, factual, SRE-grade, and never invent unobserved outages.",
            universal_fallback_fn=lambda: _universal_sre_fallback(ctx),
            gemini_key=gemini_key,
            groq_key=groq_key,
        )

        updated_state = self.memory.update_after_run(
            probe_results=ctx.probes,
            commit_shas=[c["full_sha"] for c in ctx.commits if c.get("full_sha")],
            severity=ctx.critic_verdict["severity"],
            risk_score=ctx.critic_verdict["risk_score"],
            summary=synthesis.text,
            target_repo=target_repo,
        )

        return {
            "verdict": ctx.critic_verdict,
            "probes": ctx.probes,
            "dns_checks": ctx.dns_checks,
            "suspect_commits": ctx.suspect_commits,
            "hn_signals": ctx.hn_signals,
            "runbook": ctx.runbook,
            "messages": [asdict(m) for m in ctx.messages],
            "synthesis": asdict(synthesis),
            "memory": updated_state,
        }
