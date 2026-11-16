"""AegisPulse — Dark Ops Mission Control UI with Live n8n Workflow Animation."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agents.orchestrator import AegisPulseCommander
from agents.workflow_viz import render_n8n_workflow

st.set_page_config(
    page_title="AegisPulse | Autonomous SRE Incident Commander",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

SAMPLES = {
    "Cloud Core APIs (Default)": {
        "endpoints": "https://api.github.com\nhttps://pypi.org/pypi/streamlit/json\nhttps://httpbin.org/status/200",
        "repo": "streamlit/streamlit",
        "keyword": "github",
    },
    "AI Framework Watch (FastAPI)": {
        "endpoints": "https://fastapi.tiangolo.com\nhttps://pypi.org/pypi/fastapi/json\nhttps://api.github.com",
        "repo": "fastapi/fastapi",
        "keyword": "openai",
    },
    "PyData Registry Mesh": {
        "endpoints": "https://pypi.org/pypi/pandas/json\nhttps://pypi.org/pypi/plotly/json\nhttps://httpbin.org/status/200",
        "repo": "plotly/plotly.py",
        "keyword": "cloudflare",
    },
}

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
code, pre, .mono { font-family: 'JetBrains Mono', monospace !important; }
.stApp { background: radial-gradient(circle at 12% 8%, #101c33 0%, #090e17 58%, #060910 100%); }
@keyframes fadeSlide { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
.hero-banner {
    animation: fadeSlide .45s ease-out;
    border: 1px solid rgba(0, 245, 212, 0.30);
    background: linear-gradient(135deg, rgba(17, 26, 43, 0.94), rgba(9, 14, 23, 0.97));
    border-radius: 14px;
    padding: 1.05rem 1.4rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 12px 32px rgba(0,0,0,0.38);
}
.kpi-card {
    background: rgba(17, 26, 43, 0.88);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 12px;
    padding: 0.85rem 1rem;
    transition: transform .22s ease, border-color .22s ease;
}
.kpi-card:hover { transform: translateY(-3px); border-color: #00F5D4; }
.kpi-label { color: #94A3B8; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
.kpi-val { color: #F8FAFC; font-size: 1.45rem; font-weight: 700; margin-top: 0.15rem; }
.badge { display:inline-block; padding:0.25rem 0.7rem; border-radius:999px; font-size:0.78rem; font-weight:700; font-family:'JetBrains Mono',monospace; }
.badge-crit { background: rgba(255,77,109,.18); color:#FF4D6D; border:1px solid #FF4D6D; }
.badge-warn { background: rgba(255,183,3,.18); color:#FFB703; border:1px solid #FFB703; }
.badge-ok { background: rgba(0,245,212,.15); color:#00F5D4; border:1px solid #00F5D4; }
</style>
""",
    unsafe_allow_html=True,
)

if "aegis_ep" not in st.session_state:
    s0 = SAMPLES["Cloud Core APIs (Default)"]
    st.session_state.aegis_ep = s0["endpoints"]
    st.session_state.aegis_repo = s0["repo"]
    st.session_state.aegis_kw = s0["keyword"]


def _apply_sample() -> None:
    s = SAMPLES[st.session_state.aegis_sample]
    st.session_state.aegis_ep = s["endpoints"]
    st.session_state.aegis_repo = s["repo"]
    st.session_state.aegis_kw = s["keyword"]
    st.session_state.aegis_force = True


with st.sidebar:
    st.markdown("### Sample Incidents")
    st.selectbox("Load Sample Scenario", list(SAMPLES.keys()), key="aegis_sample", on_change=_apply_sample)
    st.markdown("### Control Plane")
    endpoints_raw = st.text_area("Endpoints (1 per line)", key="aegis_ep", height=96)
    target_repo = st.text_input("GitHub Repo (owner/repo)", key="aegis_repo")
    service_kw = st.text_input("HN Signal Keyword", key="aegis_kw")

    with st.expander("AI Brain Keys (Optional)"):
        gemini_override = st.text_input("Gemini API Key Override", type="password", placeholder="Auto via Secrets / Env")
        groq_override = st.text_input("Groq API Key Override", type="password", placeholder="Auto-fallback")

    run_btn = st.button("Execute SRE Workflow", type="primary", width="stretch")
    st.caption("Prathamesh Linge · BTCOC701")

if "aegis_result" not in st.session_state or run_btn or st.session_state.pop("aegis_force", False):
    endpoints_list = [line.strip() for line in endpoints_raw.splitlines() if line.strip()]
    with st.spinner("Running 4 sub-agents in parallel..."):
        st.session_state.aegis_result = AegisPulseCommander().run_cycle(
            endpoints=endpoints_list,
            target_repo=target_repo,
            service_keyword=service_kw,
            gemini_key=gemini_override,
            groq_key=groq_override,
        )

res = st.session_state.aegis_result
verdict = res["verdict"]
sev = verdict["severity"]
badge_cls = "badge-crit" if "SEV-1" in sev else ("badge-warn" if "SEV-2" in sev else "badge-ok")
avg_lat = round(sum(p["latency_ms"] for p in res["probes"]) / max(len(res["probes"]), 1), 1)
healthy_cnt = sum(1 for p in res["probes"] if p["ok"])
msgs = res["messages"]

st.markdown(
    f"""
<div class="hero-banner">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.6rem;">
    <div>
      <div style="font-size:1.65rem; font-weight:700; color:#F8FAFC;">AegisPulse — Autonomous SRE Commander</div>
      <div class="mono" style="color:#94A3B8; font-size:0.82rem;">HTTP Probes · Google DoH · GitHub Commits · HN Algolia · EWMA Memory</div>
    </div>
    <div><span class="badge {badge_cls}">{sev} · RISK {verdict['risk_score']}/100</span></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="kpi-card"><div class="kpi-label">Endpoints Up</div><div class="kpi-val">{healthy_cnt}/{len(res["probes"])}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-card"><div class="kpi-label">Mean Latency</div><div class="kpi-val">{avg_lat} ms</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-card"><div class="kpi-label">Autonomous Cycles</div><div class="kpi-val">{res["memory"]["total_autonomous_runs"]}</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi-card"><div class="kpi-label">AI Layer ({res["synthesis"]["latency_ms"]}ms)</div><div class="kpi-val" style="font-size:1.0rem;">{res["synthesis"]["model"]}</div></div>', unsafe_allow_html=True)

st.markdown("")
wf_nodes = [
    {"title": "SRE Commander", "role": "Orchestrator", "phase": "TRIGGER", "metric": f"{len(res['probes'])} targets", "payload": f"Loaded EWMA baseline from state/incident_memory.json ({res['memory']['total_autonomous_runs']} runs)", "confidence": 0.99, "color": "#00F5D4", "icon": "🎯"},
    {"title": "TelemetryProbe", "role": "Scout 1", "phase": "SENSE", "metric": f"{avg_lat} ms avg", "payload": msgs[0]["content"] if len(msgs) > 0 else "Probed HTTP + Google DoH", "confidence": msgs[0]["confidence"] if len(msgs) > 0 else 0.95, "color": "#38BDF8", "icon": "📡"},
    {"title": "CommitCorrelator", "role": "Scout 2", "phase": "CORRELATE", "metric": f"{len(res['suspect_commits'])} commits", "payload": msgs[1]["content"] if len(msgs) > 1 else "Scanned GitHub + HN signals", "confidence": msgs[1]["confidence"] if len(msgs) > 1 else 0.88, "color": "#818CF8", "icon": "🔍"},
    {"title": "HypothesisCritic", "role": "Critic", "phase": "EVALUATE", "metric": f"Risk {verdict['risk_score']}/100", "payload": msgs[2]["content"] if len(msgs) > 2 else sev, "confidence": msgs[2]["confidence"] if len(msgs) > 2 else 0.92, "color": "#FFB703", "icon": "⚖️"},
    {"title": "RunbookStrategist", "role": "Planner", "phase": "ACT", "metric": f"{len(res['runbook']['actions'])} actions", "payload": msgs[3]["content"] if len(msgs) > 3 else "Ranked P0/P1/P2 steps", "confidence": msgs[3]["confidence"] if len(msgs) > 3 else 0.94, "color": "#22C55E", "icon": "⚡"},
    {"title": "EWMA Memory + UI", "role": "Persister", "phase": "SYNC", "metric": res["synthesis"]["provider"].split()[0], "payload": f"Persisted {len(res['memory'].get('seen_commit_shas', []))} SHAs + rendered dashboard", "confidence": 0.98, "color": "#00F5D4", "icon": "💾"},
]
render_n8n_workflow(
    wf_nodes,
    theme={"mode": "dark", "bg": "#080E1A", "card_bg": "#111A2B", "border": "rgba(0,245,212,0.28)", "accent": "#00F5D4", "text": "#F8FAFC", "muted": "#94A3B8"},
    engine_label=f"AegisPulse DAG · {res['synthesis']['provider']}",
)

t1, t2, t3 = st.tabs(["Telemetry & Graphs", "Runbook & Signals Matrix", "Agent Bus & Memory"])

with t1:
    g_left, g_right = st.columns([1.45, 1])
    probe_df = pd.DataFrame(res["probes"])
    with g_left:
        if not probe_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Live Latency (ms)", x=probe_df["host"], y=probe_df["latency_ms"], marker_color="#00F5D4", text=probe_df["latency_ms"], textposition="auto"))
            fig.add_trace(go.Bar(name="EWMA Baseline (ms)", x=probe_df["host"], y=probe_df["baseline_ms"], marker_color="#334155"))
            fig.update_layout(barmode="group", title="Endpoint Latency vs EWMA Baseline", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,26,43,0.45)", font=dict(color="#E2E8F0"), height=300, margin=dict(l=10, r=10, t=38, b=10))
            st.plotly_chart(fig, width="stretch")

    with g_right:
        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=float(verdict["risk_score"]),
                delta={"reference": 25},
                title={"text": f"Incident Severity ({sev})", "font": {"color": "#E2E8F0", "size": 15}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "#94A3B8"},
                    "bar": {"color": "#FF4D6D" if verdict["risk_score"] >= 60 else ("#FFB703" if verdict["risk_score"] >= 35 else "#00F5D4")},
                    "bgcolor": "#111A2B",
                    "steps": [
                        {"range": [0, 35], "color": "rgba(0,245,212,0.12)"},
                        {"range": [35, 70], "color": "rgba(255,183,3,0.14)"},
                        {"range": [70, 100], "color": "rgba(255,77,109,0.18)"},
                    ],
                },
            )
        )
        gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#F8FAFC"), height=300, margin=dict(l=15, r=15, t=40, b=10))
        st.plotly_chart(gauge, width="stretch")

    if not probe_df.empty:
        st.dataframe(
            probe_df[["host", "status_code", "latency_ms", "baseline_ms", "drift_pct", "ok", "source"]],
            width="stretch",
            hide_index=True,
            column_config={
                "latency_ms": st.column_config.ProgressColumn("Latency (ms)", min_value=0, max_value=1500, format="%.1f ms"),
                "drift_pct": st.column_config.NumberColumn("Drift %", format="%.1f%%"),
            },
        )

    with st.expander(f"AI Executive Summary ({res['synthesis']['provider']} · {res['synthesis']['model']})", expanded=False):
        st.write(res["synthesis"]["text"])

with t2:
    c_a, c_b = st.columns([1.2, 1])
    with c_a:
        st.markdown("#### Suspect Repository Commits")
        commits_df = pd.DataFrame(res["suspect_commits"])
        if not commits_df.empty:
            st.dataframe(
                commits_df[["sha", "author", "suspicion_score", "message"]],
                width="stretch",
                hide_index=True,
                column_config={"suspicion_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%d/100")},
            )
    with c_b:
        st.markdown("#### Utility-Ranked Remediation Runbook")
        rb_df = pd.DataFrame(res["runbook"]["actions"])
        if not rb_df.empty:
            st.dataframe(
                rb_df,
                width="stretch",
                hide_index=True,
                column_config={"utility": st.column_config.ProgressColumn("Utility", min_value=0, max_value=100, format="%.0f")},
            )
        if res["dns_checks"]:
            st.markdown("#### Google DoH DNS Resolution")
            st.dataframe(pd.DataFrame(res["dns_checks"]), width="stretch", hide_index=True)

with t3:
    msg_df = pd.DataFrame(msgs)
    if not msg_df.empty:
        fig_c = px.bar(msg_df, x="sender", y="confidence", color="phase", title="Sub-Agent Execution Confidence", height=240)
        fig_c.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,26,43,0.45)", font=dict(color="#E2E8F0"), margin=dict(l=10, r=10, t=35, b=10))
        st.plotly_chart(fig_c, width="stretch")
        st.dataframe(msg_df[["phase", "sender", "recipient", "confidence", "content"]], width="stretch", hide_index=True)

    hist = res["memory"].get("incident_history", [])
    if hist:
        hist_df = pd.DataFrame(hist)
        st.plotly_chart(px.area(hist_df, x="timestamp_utc", y="risk_score", markers=True, title="Persistent EWMA Risk History", height=230).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,26,43,0.45)", font=dict(color="#E2E8F0")), width="stretch")

    st.table(
        pd.DataFrame(
            [
                {"PEAS": "Performance", "Spec": "MTTR reduction, drift recall, zero unapproved rollbacks"},
                {"PEAS": "Environment", "Spec": "HTTP APIs, Google DoH, GitHub Commits, HN Algolia"},
                {"PEAS": "Actuators", "Spec": "Animated Ops UI, P0/P1/P2 Runbook, state/incident_memory.json"},
                {"PEAS": "Sensors", "Spec": "HTTP timings, DNS A-records, Commit metadata, EWMA baseline"},
            ]
        )
    )
