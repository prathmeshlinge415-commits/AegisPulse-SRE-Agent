"""Model-based persistent memory for AegisPulse SRE incident baselines and history."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_STATE: dict[str, Any] = {
    "agent_name": "AegisPulse Incident Commander",
    "baseline_latency_ms": {},
    "incident_history": [],
    "seen_commit_shas": [],
    "total_autonomous_runs": 0,
    "last_run_utc": None,
}


class IncidentMemoryStore:
    """Stores service latency baselines, deduplicated commit SHAs, and past incident runs."""

    def __init__(self, state_path: Path | str | None = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.path = Path(state_path) if state_path else base_dir / "state" / "incident_memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        """Load state JSON safely, seeding defaults if missing or corrupt."""
        if not self.path.exists():
            return json.loads(json.dumps(DEFAULT_STATE))
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for key, val in DEFAULT_STATE.items():
                data.setdefault(key, json.loads(json.dumps(val)))
            return data
        except Exception:
            return json.loads(json.dumps(DEFAULT_STATE))

    def save(self, state: dict[str, Any]) -> None:
        """Persist updated model state atomically."""
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def update_after_run(
        self,
        probe_results: list[dict[str, Any]],
        commit_shas: list[str],
        severity: str,
        risk_score: float,
        summary: str,
        target_repo: str,
    ) -> dict[str, Any]:
        """Update exponential moving latency baselines and append deduplicated incident entry."""
        state = self.load()
        baselines: dict[str, float] = state["baseline_latency_ms"]
        for probe in probe_results:
            url = probe["url"]
            lat = float(probe.get("latency_ms", 0))
            if probe.get("ok") and lat > 0:
                prev = baselines.get(url)
                baselines[url] = round(lat if prev is None else (0.7 * prev + 0.3 * lat), 2)

        seen = set(state.get("seen_commit_shas", []))
        new_shas = [sha for sha in commit_shas if sha not in seen]
        merged_shas = (state.get("seen_commit_shas", []) + new_shas)[-150:]
        state["seen_commit_shas"] = merged_shas

        state["total_autonomous_runs"] = int(state.get("total_autonomous_runs", 0)) + 1
        now_iso = datetime.now(timezone.utc).isoformat()
        state["last_run_utc"] = now_iso

        state["incident_history"].append(
            {
                "timestamp_utc": now_iso,
                "target_repo": target_repo,
                "severity": severity,
                "risk_score": round(risk_score, 1),
                "new_commits_detected": len(new_shas),
                "summary": summary[:220],
            }
        )
        state["incident_history"] = state["incident_history"][-30:]
        self.save(state)
        return state
