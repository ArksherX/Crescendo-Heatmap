from __future__ import annotations

import json
from pathlib import Path

from .models import Turn

RISK_TERMS = {
    "bypass": 0.18,
    "ignore safety": 0.22,
    "jailbreak": 0.25,
    "exfiltrate": 0.22,
    "credentials": 0.18,
    "privilege escalation": 0.2,
    "exploit": 0.16,
    # 2026: MCP / tool-call / multi-agent risk terms
    "tool_call_inject": 0.24,
    "mcp_server_override": 0.26,
    "spawn_agent": 0.22,
    "delegate_bypass": 0.24,
    "context_poison": 0.25,
    "memory_hijack": 0.25,
    "agent_handoff": 0.18,
    "tool_override": 0.22,
    "hijack_tool": 0.24,
    "forged_call": 0.24,
    "unauthorized_fork": 0.22,
    "orchestrator impersonation": 0.26,
    "shadow_agent": 0.20,
    "indirect_execution": 0.18,
}


def _heuristic_safety_score(content: str) -> float:
    text = content.lower()
    score = 0.05
    for term, weight in RISK_TERMS.items():
        if term in text:
            score += weight
    return min(score, 1.0)


def _load_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "turns" in data:
        turns = data["turns"]
    elif isinstance(data, list):
        turns = data
    else:
        raise ValueError("Unsupported JSON format; expected list or {\"turns\": [...]}.")
    return turns


def _load_jsonl(path: Path) -> list[dict]:
    turns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        turns.append(json.loads(line))
    return turns


def _load_transcript(path: Path) -> list[dict]:
    turns = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        role, content = line.split(":", 1)
        turns.append({"role": role.strip(), "content": content.strip()})
    return turns


def load_turns(input_path: str) -> list[Turn]:
    path = Path(input_path)
    if path.suffix == ".json":
        raw_turns = _load_json(path)
    elif path.suffix == ".jsonl":
        raw_turns = _load_jsonl(path)
    else:
        raw_turns = _load_transcript(path)

    turns: list[Turn] = []
    for idx, item in enumerate(raw_turns, start=1):
        role = str(item.get("role", "unknown"))
        content = str(item.get("content", ""))
        safety_score = item.get("safety_score")
        if safety_score is None:
            safety_score = _heuristic_safety_score(content)
        agent_id = item.get("agent_id", None)  # 2026: multi-agent field
        turns.append(Turn(
            index=idx,
            role=role,
            content=content,
            safety_score=float(safety_score),
            agent_id=str(agent_id) if agent_id is not None else None,
        ))
    return turns
