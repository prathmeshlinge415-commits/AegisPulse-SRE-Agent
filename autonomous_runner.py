"""Headless autonomous runner for scheduled GitHub Actions or Task Scheduler sweeps."""

from __future__ import annotations

import json
import os

from agents.orchestrator import AegisPulseCommander

DEFAULT_ENDPOINTS = [
    "https://api.github.com",
    "https://pypi.org/pypi/streamlit/json",
    "https://httpbin.org/status/200",
]


def main() -> None:
    endpoints = os.environ.get("AEGIS_ENDPOINTS", "").split(",")
    endpoints = [e.strip() for e in endpoints if e.strip()] or DEFAULT_ENDPOINTS
    repo = os.environ.get("AEGIS_REPO", "streamlit/streamlit")
    keyword = os.environ.get("AEGIS_KEYWORD", "github")

    commander = AegisPulseCommander()
    result = commander.run_cycle(endpoints=endpoints, target_repo=repo, service_keyword=keyword)
    print(
        json.dumps(
            {
                "severity": result["verdict"]["severity"],
                "risk_score": result["verdict"]["risk_score"],
                "provider": result["synthesis"]["provider"],
                "total_runs": result["memory"]["total_autonomous_runs"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
