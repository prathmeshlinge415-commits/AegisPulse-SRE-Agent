"""Keyless live telemetry sensors for AegisPulse (HTTP probes, DNS-over-HTTPS, GitHub, HN)."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import requests

HEADERS = {"User-Agent": "AegisPulse-SRE-Agent/1.0"}


def probe_http_endpoint(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Measure live HTTP status, latency, and edge server metadata."""
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    target = parsed.geturl()
    t0 = time.perf_counter()
    try:
        resp = requests.get(target, headers=HEADERS, timeout=timeout)
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "url": target,
            "host": parsed.netloc,
            "ok": 200 <= resp.status_code < 400,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "server": resp.headers.get("Server", "unknown"),
            "source": "live-http-probe",
            "error": None,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "url": target,
            "host": parsed.netloc,
            "ok": False,
            "status_code": 0,
            "latency_ms": latency_ms,
            "server": "unreachable",
            "source": "probe-timeout-or-error",
            "error": str(exc)[:140],
        }


def resolve_dns_doh(hostname: str, timeout: float = 4.0) -> dict[str, Any]:
    """Query Google DNS-over-HTTPS API for live A-record resolution."""
    clean_host = hostname.split(":")[0].strip()
    try:
        resp = requests.get(
            "https://dns.google/resolve",
            params={"name": clean_host, "type": "A"},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        answers = [ans.get("data", "") for ans in payload.get("Answer", []) if ans.get("type") == 1]
        return {
            "host": clean_host,
            "status": payload.get("Status", -1),
            "resolved_ips": answers[:4],
            "healthy": payload.get("Status") == 0 and len(answers) > 0,
            "source": "live-dns-google-doh",
        }
    except Exception as exc:
        return {
            "host": clean_host,
            "status": -1,
            "resolved_ips": [],
            "healthy": False,
            "source": "dns-fallback",
            "error": str(exc)[:120],
        }


def fetch_github_commits(repo_slug: str, limit: int = 8, timeout: float = 5.0) -> dict[str, Any]:
    """Fetch latest commits from a public GitHub repository without requiring a token."""
    clean_slug = repo_slug.strip().strip("/")
    url = f"https://api.github.com/repos/{clean_slug}/commits"
    try:
        resp = requests.get(url, params={"per_page": limit}, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        items = resp.json()
        commits = []
        for item in items:
            commit_obj = item.get("commit", {})
            author_obj = commit_obj.get("author", {})
            msg = (commit_obj.get("message") or "").splitlines()[0][:110]
            commits.append(
                {
                    "sha": (item.get("sha") or "")[:7],
                    "full_sha": item.get("sha") or "",
                    "message": msg,
                    "author": author_obj.get("name", "unknown"),
                    "date": author_obj.get("date", ""),
                    "url": item.get("html_url", ""),
                }
            )
        return {"repo": clean_slug, "commits": commits, "source": "live-github-api", "ok": True}
    except Exception as exc:
        backup = [
            {
                "sha": "b71e9a4",
                "full_sha": "b71e9a400000",
                "message": "chore(cache): fallback telemetry snapshot when GitHub rate limit triggers",
                "author": "aegis-fallback",
                "date": "2026-11-15T00:00:00Z",
                "url": f"https://github.com/{clean_slug}",
            }
        ]
        return {
            "repo": clean_slug,
            "commits": backup,
            "source": f"github-backup ({type(exc).__name__})",
            "ok": False,
        }


def fetch_hn_outage_signals(keyword: str, limit: int = 5, timeout: float = 4.5) -> dict[str, Any]:
    """Query Hacker News Algolia API for recent outage/incident chatter."""
    clean_kw = keyword.strip() or "outage"
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": f"{clean_kw} outage OR latency OR down", "tags": "story", "hitsPerPage": limit},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        signals = [
            {
                "title": (h.get("title") or "Untitled signal")[:110],
                "points": int(h.get("points") or 0),
                "comments": int(h.get("num_comments") or 0),
                "created_at": h.get("created_at", ""),
                "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}",
            }
            for h in hits
        ]
        return {"query": clean_kw, "signals": signals, "source": "live-hn-algolia", "ok": True}
    except Exception as exc:
        return {
            "query": clean_kw,
            "signals": [],
            "source": f"hn-backup ({type(exc).__name__})",
            "ok": False,
        }
