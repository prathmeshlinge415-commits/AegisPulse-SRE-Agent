"""Automated pytest suite for AegisPulse multi-agent SRE commander."""

from __future__ import annotations

from pathlib import Path

from agents.llm_router import synthesize_with_fallback
from agents.memory import IncidentMemoryStore
from agents.orchestrator import AegisPulseCommander
from agents.subagents import HypothesisCriticAgent, SubAgentContext


def test_memory_deduplicates_commit_shas(tmp_path: Path) -> None:
    store = IncidentMemoryStore(tmp_path / "mem.json")
    probes = [{"url": "https://api.github.com", "ok": True, "latency_ms": 120.0}]
    s1 = store.update_after_run(probes, ["sha1", "sha2"], "SEV-3 NOMINAL", 10.0, "ok", "org/repo")
    s2 = store.update_after_run(probes, ["sha2", "sha3"], "SEV-3 NOMINAL", 11.0, "ok2", "org/repo")
    assert s1["seen_commit_shas"] == ["sha1", "sha2"]
    assert s2["seen_commit_shas"] == ["sha1", "sha2", "sha3"]
    assert s2["total_autonomous_runs"] == 2


def test_critic_flags_outage_vs_nominal() -> None:
    critic = HypothesisCriticAgent()
    ctx_down = SubAgentContext(
        endpoints=["https://down.example"],
        target_repo="a/b",
        service_keyword="test",
        baseline_latency={},
        seen_shas=set(),
        probes=[{"url": "https://down.example", "ok": False, "latency_ms": 5000, "drift_pct": 0}],
        dns_checks=[{"healthy": False}],
        suspect_commits=[{"suspicion_score": 80}],
    )
    critic.run(ctx_down)
    assert ctx_down.critic_verdict["severity"] == "SEV-1 CRITICAL"
    assert ctx_down.critic_verdict["risk_score"] >= 70

    ctx_ok = SubAgentContext(
        endpoints=["https://ok.example"],
        target_repo="a/b",
        service_keyword="test",
        baseline_latency={},
        seen_shas=set(),
        probes=[{"url": "https://ok.example", "ok": True, "latency_ms": 95, "drift_pct": 2.0}],
        dns_checks=[{"healthy": True}],
        suspect_commits=[{"suspicion_score": 10}],
    )
    critic.run(ctx_ok)
    assert ctx_ok.critic_verdict["severity"] == "SEV-3 NOMINAL"


def test_llm_router_universal_fallback_never_fails(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    res = synthesize_with_fallback(
        prompt="Summarize",
        system_instruction="Be brief",
        universal_fallback_fn=lambda: "Deterministic SRE fallback brief",
        gemini_key="",
        groq_key="",
    )
    assert res.fallback_used is True
    assert res.provider == "Universal Keyless Engine"
    assert "Deterministic SRE fallback brief" in res.text


def test_full_commander_cycle_with_mocked_sensors(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "agents.subagents.probe_http_endpoint",
        lambda url: {"url": url, "host": "api.github.com", "ok": True, "status_code": 200, "latency_ms": 110.0, "server": "GitHub", "source": "mock"},
    )
    monkeypatch.setattr(
        "agents.subagents.resolve_dns_doh",
        lambda host: {"host": host, "status": 0, "resolved_ips": ["140.82.121.6"], "healthy": True, "source": "mock"},
    )
    monkeypatch.setattr(
        "agents.subagents.fetch_github_commits",
        lambda repo: {"repo": repo, "commits": [{"sha": "abc1234", "full_sha": "abc123456", "message": "fix: hotfix pool timeout", "author": "dev", "date": "", "url": ""}], "source": "mock", "ok": True},
    )
    monkeypatch.setattr(
        "agents.subagents.fetch_hn_outage_signals",
        lambda kw: {"query": kw, "signals": [], "source": "mock", "ok": True},
    )

    commander = AegisPulseCommander(memory_store=IncidentMemoryStore(tmp_path / "mem.json"))
    out = commander.run_cycle(["https://api.github.com"], target_repo="streamlit/streamlit", gemini_key="", groq_key="")
    assert len(out["messages"]) == 5
    assert out["verdict"]["severity"] in {"SEV-1 CRITICAL", "SEV-2 DEGRADED", "SEV-3 NOMINAL"}
    assert out["memory"]["total_autonomous_runs"] == 1
