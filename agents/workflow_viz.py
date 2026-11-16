"""Interactive n8n-style animated multi-agent workflow canvas for Streamlit."""

from __future__ import annotations

import html
import json
import uuid
from typing import Any

import streamlit as st
import streamlit.components.v1 as components


def render_n8n_workflow(
    nodes: list[dict[str, Any]],
    theme: dict[str, str],
    engine_label: str = "Autonomous DAG",
    height: int = 375,
) -> None:
    """Render an interactive n8n-style branching workflow animation with traveling packets."""
    cid = f"wf_{uuid.uuid4().hex[:8]}"
    safe_nodes = []
    for idx, n in enumerate(nodes[:6]):
        safe_nodes.append(
            {
                "idx": idx,
                "title": str(n.get("title", f"Node {idx}")),
                "role": str(n.get("role", "Agent")),
                "phase": str(n.get("phase", "STEP")).upper(),
                "metric": str(n.get("metric", "OK")),
                "payload": str(n.get("payload", "")),
                "confidence": int(round(float(n.get("confidence", 0.9)) * 100))
                if float(n.get("confidence", 0.9)) <= 1.0
                else int(round(float(n.get("confidence", 90)))),
                "color": str(n.get("color", theme.get("accent", "#38BDF8"))),
                "icon": str(n.get("icon", "⚡")),
            }
        )

    is_dark = theme.get("mode", "dark") == "dark"
    bg = theme.get("bg", "#090E17" if is_dark else "#F8FAFC")
    dot = theme.get("dot", "rgba(148,163,184,0.18)" if is_dark else "rgba(15,23,42,0.12)")
    card_bg = theme.get("card_bg", "#111A2B" if is_dark else "#FFFFFF")
    card_border = theme.get("border", "rgba(148,163,184,0.24)" if is_dark else "#CBD5E1")
    text = theme.get("text", "#F8FAFC" if is_dark else "#0F172A")
    muted = theme.get("muted", "#94A3B8" if is_dark else "#475569")
    accent = theme.get("accent", "#00F5D4")
    bar_bg = theme.get("bar_bg", "rgba(15,23,42,0.85)" if is_dark else "rgba(241,245,249,0.95)")

    nodes_json = json.dumps(safe_nodes)
    title_safe = html.escape(engine_label)

    html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
    color: {text};
    overflow: hidden;
  }}
  #{cid} {{
    position: relative;
    width: 100%;
    height: {height - 4}px;
    border-radius: 14px;
    border: 1px solid {card_border};
    background-color: {bg};
    background-image: radial-gradient({dot} 1.3px, transparent 1.3px);
    background-size: 18px 18px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 10px 14px;
    overflow: hidden;
  }}
  .wf-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 4;
    gap: 8px;
  }}
  .wf-pill {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 4px 10px;
    border-radius: 999px;
    background: {bar_bg};
    border: 1px solid {card_border};
  }}
  .live-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: {accent};
    box-shadow: 0 0 8px {accent};
    animation: pulseDot 1.4s infinite ease-in-out;
  }}
  @keyframes pulseDot {{
    0%, 100% {{ transform: scale(1); opacity: 1; }}
    50% {{ transform: scale(1.45); opacity: 0.55; }}
  }}
  .wf-btn {{
    cursor: pointer;
    border: 1px solid {accent};
    background: {accent}22;
    color: {text};
    font-size: 11.5px;
    font-weight: 700;
    padding: 4px 11px;
    border-radius: 8px;
    transition: transform 0.15s ease, background 0.15s ease;
  }}
  .wf-btn:hover {{ transform: translateY(-1px); background: {accent}38; }}
  .wf-stage {{
    position: relative;
    flex: 1;
    width: 100%;
    margin: 6px 0;
  }}
  svg.wf-wires {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1;
  }}
  .wf-grid {{
    position: relative;
    z-index: 3;
    width: 100%;
    height: 100%;
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    grid-template-rows: 1fr 1fr;
    gap: 10px 18px;
    align-items: center;
    padding: 4px 2px;
  }}
  .node-card {{
    position: relative;
    background: {card_bg};
    border: 1.5px solid {card_border};
    border-radius: 11px;
    padding: 8px 10px;
    cursor: pointer;
    transition: transform 0.28s cubic-bezier(.22,1,.36,1), border-color 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease;
    box-shadow: 0 4px 14px rgba(0,0,0,{0.28 if is_dark else 0.07});
    opacity: 0.48;
  }}
  .node-card:hover {{ transform: translateY(-2px); }}
  .node-card.running {{
    opacity: 1;
    transform: scale(1.035);
    border-color: var(--nc);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--nc) 28%, transparent), 0 8px 22px rgba(0,0,0,{0.35 if is_dark else 0.12});
  }}
  .node-card.done {{
    opacity: 1;
    border-color: var(--nc);
  }}
  .node-card.selected {{
    box-shadow: 0 0 0 3px {accent}55, 0 8px 20px rgba(0,0,0,{0.35 if is_dark else 0.14});
  }}
  .node-bar {{
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3.5px;
    border-radius: 11px 11px 0 0;
    background: var(--nc);
  }}
  .node-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 2px;
    font-size: 10px;
    font-weight: 700;
    color: {muted};
    letter-spacing: 0.04em;
  }}
  .node-status {{
    font-size: 9.5px;
    padding: 1px 6px;
    border-radius: 999px;
    background: rgba(148,163,184,0.16);
    color: {muted};
  }}
  .node-card.running .node-status {{
    background: var(--nc);
    color: #090E17;
  }}
  .node-card.done .node-status {{
    background: #10B98126;
    color: #10B981;
    border: 1px solid #10B98155;
  }}
  .node-title {{
    font-size: 12.2px;
    font-weight: 700;
    margin-top: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .node-metric {{
    font-size: 10.8px;
    color: {muted};
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }}
  .conf-track {{
    width: 100%;
    height: 3.5px;
    border-radius: 99px;
    background: rgba(148,163,184,0.18);
    margin-top: 6px;
    overflow: hidden;
  }}
  .conf-fill {{
    height: 100%;
    width: 0%;
    background: var(--nc);
    transition: width 0.55s ease;
  }}
  .wf-inspector {{
    z-index: 4;
    background: {bar_bg};
    border: 1px solid {card_border};
    border-radius: 9px;
    padding: 7px 12px;
    font-size: 11.8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
  }}
  .insp-text {{
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: {text};
  }}
  .insp-tag {{
    font-family: ui-monospace, monospace;
    font-size: 10.5px;
    color: {accent};
    font-weight: 700;
    flex-shrink: 0;
  }}
  /* DAG Grid Placements */
  .pos-0 {{ grid-column: 1; grid-row: 1 / span 2; }}
  .pos-1 {{ grid-column: 2; grid-row: 1; }}
  .pos-2 {{ grid-column: 2; grid-row: 2; }}
  .pos-3 {{ grid-column: 3; grid-row: 1 / span 2; }}
  .pos-4 {{ grid-column: 4; grid-row: 1 / span 2; }}
  .pos-5 {{ grid-column: 5; grid-row: 1 / span 2; }}
</style>
</head>
<body>
<div id="{cid}">
  <div class="wf-top">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <span class="wf-pill"><span class="live-dot"></span> <span id="{cid}_state">EXECUTING N8N DAG...</span></span>
      <span class="wf-pill" style="color:{muted};">{title_safe}</span>
    </div>
    <button class="wf-btn" onclick="replayFlow()">&#8635; Replay Execution</button>
  </div>

  <div class="wf-stage" id="{cid}_stage">
    <svg class="wf-wires" id="{cid}_svg"></svg>
    <div class="wf-grid" id="{cid}_grid"></div>
  </div>

  <div class="wf-inspector">
    <div class="insp-text" id="{cid}_insp">Click any workflow node above to inspect its live sub-agent handoff payload.</div>
    <div class="insp-tag" id="{cid}_conf">CONF --%</div>
  </div>
</div>

<script>
(function() {{
  const NODES = {nodes_json};
  const EDGES = [[0,1],[0,2],[1,3],[2,3],[3,4],[4,5]];
  const grid = document.getElementById("{cid}_grid");
  const svg = document.getElementById("{cid}_svg");
  const stage = document.getElementById("{cid}_stage");
  const stateEl = document.getElementById("{cid}_state");
  const inspEl = document.getElementById("{cid}_insp");
  const confEl = document.getElementById("{cid}_conf");

  NODES.forEach((n) => {{
    const card = document.createElement("div");
    card.className = "node-card pos-" + n.idx;
    card.id = "{cid}_n" + n.idx;
    card.style.setProperty("--nc", n.color);
    card.innerHTML = `
      <div class="node-bar"></div>
      <div class="node-head">
        <span>${{n.icon}} ${{n.phase}}</span>
        <span class="node-status" id="{cid}_st${{n.idx}}">QUEUED</span>
      </div>
      <div class="node-title">${{n.title}}</div>
      <div class="node-metric">${{n.metric}}</div>
      <div class="conf-track"><div class="conf-fill" id="{cid}_cf${{n.idx}}"></div></div>
    `;
    card.onclick = () => selectNode(n.idx);
    grid.appendChild(card);
  }});

  function selectNode(idx) {{
    NODES.forEach((n) => {{
      const el = document.getElementById("{cid}_n" + n.idx);
      if (el) el.classList.toggle("selected", n.idx === idx);
    }});
    const node = NODES[idx];
    if (!node) return;
    inspEl.innerHTML = `<strong>[${{node.phase}}] ${{node.title}}:</strong> ${{node.payload}}`;
    confEl.textContent = `CONF ${{node.confidence}}%`;
  }}

  let edgePaths = [];
  function drawWires() {{
    const sRect = stage.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${{sRect.width}} ${{sRect.height}}`);
    svg.innerHTML = "";
    edgePaths = [];
    EDGES.forEach(([a, b], i) => {{
      const elA = document.getElementById("{cid}_n" + a);
      const elB = document.getElementById("{cid}_n" + b);
      if (!elA || !elB) return;
      const rA = elA.getBoundingClientRect();
      const rB = elB.getBoundingClientRect();
      const x1 = rA.right - sRect.left;
      const y1 = rA.top + rA.height / 2 - sRect.top;
      const x2 = rB.left - sRect.left;
      const y2 = rB.top + rB.height / 2 - sRect.top;
      const dx = Math.max(24, (x2 - x1) * 0.55);
      const d = `M ${{x1}},${{y1}} C ${{x1+dx}},${{y1}} ${{x2-dx}},${{y2}} ${{x2}},${{y2}}`;

      const base = document.createElementNS("http://www.w3.org/2000/svg", "path");
      base.setAttribute("d", d);
      base.setAttribute("fill", "none");
      base.setAttribute("stroke", "{card_border}");
      base.setAttribute("stroke-width", "2.2");
      svg.appendChild(base);

      const glow = document.createElementNS("http://www.w3.org/2000/svg", "path");
      glow.setAttribute("d", d);
      glow.setAttribute("fill", "none");
      glow.setAttribute("stroke", NODES[a].color);
      glow.setAttribute("stroke-width", "2.6");
      glow.setAttribute("stroke-dasharray", "6 5");
      glow.setAttribute("opacity", "0.25");
      svg.appendChild(glow);

      const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("r", "4.2");
      dot.setAttribute("fill", NODES[b].color);
      dot.setAttribute("opacity", "0");
      svg.appendChild(dot);

      edgePaths.push({{ a, b, path: base, glow, dot }});
    }});
  }}

  function animatePacket(edgeIdx, durationMs) {{
    const ep = edgePaths[edgeIdx];
    if (!ep) return;
    const len = ep.path.getTotalLength();
    ep.glow.setAttribute("opacity", "0.95");
    ep.dot.setAttribute("opacity", "1");
    const t0 = performance.now();
    function tick(now) {{
      const p = Math.min(1, (now - t0) / durationMs);
      const pt = ep.path.getPointAtLength(p * len);
      ep.dot.setAttribute("cx", pt.x);
      ep.dot.setAttribute("cy", pt.y);
      if (p < 1) {{
        requestAnimationFrame(tick);
      }} else {{
        ep.dot.setAttribute("opacity", "0");
      }}
    }}
    requestAnimationFrame(tick);
  }}

  let timers = [];
  function clearTimers() {{
    timers.forEach((t) => clearTimeout(t));
    timers = [];
  }}

  function setNodeStatus(idx, mode) {{
    const el = document.getElementById("{cid}_n" + idx);
    const st = document.getElementById("{cid}_st" + idx);
    const cf = document.getElementById("{cid}_cf" + idx);
    if (!el || !st || !cf) return;
    el.classList.remove("running", "done");
    if (mode === "queued") {{
      st.textContent = "QUEUED";
      cf.style.width = "0%";
    }} else if (mode === "running") {{
      el.classList.add("running");
      st.textContent = "RUNNING";
      cf.style.width = "45%";
    }} else {{
      el.classList.add("done");
      st.textContent = "DONE ✓";
      cf.style.width = NODES[idx].confidence + "%";
    }}
  }}

  window.replayFlow = function() {{
    clearTimers();
    drawWires();
    NODES.forEach((n) => setNodeStatus(n.idx, "queued"));
    stateEl.textContent = "EXECUTING WORKFLOW...";

    const seq = [
      [0, () => {{ setNodeStatus(0, "running"); selectNode(0); }}],
      [380, () => {{ setNodeStatus(0, "done"); animatePacket(0, 420); animatePacket(1, 420); }}],
      [620, () => {{ setNodeStatus(1, "running"); setNodeStatus(2, "running"); selectNode(1); }}],
      [1100, () => {{ setNodeStatus(1, "done"); setNodeStatus(2, "done"); animatePacket(2, 420); animatePacket(3, 420); }}],
      [1350, () => {{ setNodeStatus(3, "running"); selectNode(3); }}],
      [1820, () => {{ setNodeStatus(3, "done"); animatePacket(4, 420); }}],
      [2050, () => {{ setNodeStatus(4, "running"); selectNode(4); }}],
      [2520, () => {{ setNodeStatus(4, "done"); animatePacket(5, 420); }}],
      [2750, () => {{ setNodeStatus(5, "running"); selectNode(5); }}],
      [3150, () => {{ setNodeStatus(5, "done"); stateEl.textContent = "6/6 NODES SYNCED · AUTONOMOUS"; }}],
    ];
    seq.forEach(([ms, fn]) => timers.push(setTimeout(fn, ms)));
  }};

  window.addEventListener("resize", () => drawWires());
  setTimeout(() => replayFlow(), 80);

  // Subtle ambient data pulse every 5.5s to show autonomous telemetry cadence
  setInterval(() => {{
    if (!edgePaths.length) return;
    edgePaths.forEach((_, idx) => setTimeout(() => animatePacket(idx, 600), idx * 140));
  }}, 5500);
}})();
</script>
</body>
</html>
"""
    if hasattr(st, "iframe"):
        st.iframe(html_doc, height=height)
    else:
        components.html(html_doc, height=height, scrolling=False)
