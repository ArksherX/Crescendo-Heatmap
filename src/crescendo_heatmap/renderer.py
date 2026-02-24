from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path

from .models import TurnAnalysis

# 2026: distinct hues for up to 8 agents in multi-agent view
_AGENT_COLORS = [
    "#3b82f6", "#f59e0b", "#10b981", "#f43f5e",
    "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16",
]


def _score_color(score: float) -> str:
    # Green (safe) -> Red (unsafe)
    score = max(0.0, min(score, 1.0))
    red = int(245 * score)
    green = int(220 * (1.0 - score))
    blue = 90
    return f"rgb({red},{green},{blue})"


def render_html(analysis: list[TurnAnalysis], output_path: str) -> None:
    # Detect multi-agent mode
    agent_ids = [a.turn.agent_id for a in analysis if a.turn.agent_id is not None]
    multi_agent = len(set(agent_ids)) > 0
    unique_agents = sorted(set(agent_ids)) if multi_agent else []
    agent_color_map = {aid: _AGENT_COLORS[i % len(_AGENT_COLORS)] for i, aid in enumerate(unique_agents)}

    rows = []
    for item in analysis:
        color = _score_color(item.turn.safety_score)
        agent_cell = ""
        row_style = ""
        if multi_agent:
            aid = item.turn.agent_id or "—"
            ac = agent_color_map.get(aid, "#94a3b8")
            agent_cell = f"<td><span class='agent-pill' style='background:{ac};'>{escape(aid)}</span></td>"
            row_style = f" style='border-left: 3px solid {ac};'"

        rows.append(
            f"<tr{row_style}>"
            f"<td>{item.turn.index}</td>"
            f"<td>{escape(item.turn.role)}</td>"
            + agent_cell +
            f"<td title='{escape(item.turn.content)}'>{escape(item.turn.content[:120])}</td>"
            f"<td>{item.turn.safety_score:.3f}</td>"
            f"<td>{item.decay_delta:+.3f}</td>"
            f"<td><span class='pill' style='background:{color};'>{item.risk_band}</span></td>"
            "</tr>"
        )

    agent_header = "<th>Agent</th>" if multi_agent else ""

    html = f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Crescendo Heatmap</title>
<style>
:root {{
  --bg: #0f172a;
  --panel: #1e293b;
  --ink: #f1f5f9;
  --muted: #94a3b8;
  --line: #334155;
  --accent: #3b82f6;
}}
body {{ font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif; margin: 0; padding: 24px; background: var(--bg); color: var(--ink); }}
h1 {{ margin: 0 0 4px; color: var(--ink); }}
p {{ margin: 0 0 24px; color: var(--muted); font-size: 14px; }}
.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 16px; box-shadow: 0 10px 35px rgba(0,0,0,0.4); overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; border-bottom: 2px solid var(--accent); padding: 10px 8px; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; }}
td {{ text-align: left; border-bottom: 1px solid var(--line); padding: 9px 8px; vertical-align: top; color: var(--ink); }}
.pill {{ display:inline-block; border-radius: 999px; color: white; font-size: 11px; font-weight: 700; padding: 3px 9px; text-transform: uppercase; letter-spacing: 0.04em; }}
.agent-pill {{ display:inline-block; border-radius: 6px; color: white; font-size: 11px; font-weight: 600; padding: 2px 8px; }}
tr:hover td {{ background: rgba(59,130,246,0.06); }}
</style>
</head>
<body>
  <h1>Crescendo Safety Heatmap</h1>
  <p>Turn-by-turn view of safety score progression and adversarial decay pressure.</p>
  <div class='card'>
    <table>
      <thead>
        <tr><th>#</th><th>Role</th>{agent_header}<th>Content</th><th>Safety Score</th><th>Delta</th><th>Risk Band</th></tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
    Path(output_path).write_text(html, encoding="utf-8")


def write_json(analysis: list[TurnAnalysis], output_path: str, summary: dict) -> None:
    payload = {
        "summary": summary,
        "turns": [a.to_dict() for a in analysis],
    }
    Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(analysis: list[TurnAnalysis], output_path: str) -> None:
    has_agents = any(a.turn.agent_id is not None for a in analysis)
    with Path(output_path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        header = ["turn", "role", "safety_score", "decay_delta", "risk_band", "content"]
        if has_agents:
            header.insert(2, "agent_id")
        writer.writerow(header)
        for item in analysis:
            row = [
                item.turn.index,
                item.turn.role,
                f"{item.turn.safety_score:.3f}",
                f"{item.decay_delta:+.3f}",
                item.risk_band,
                item.turn.content,
            ]
            if has_agents:
                row.insert(2, item.turn.agent_id or "")
            writer.writerow(row)
