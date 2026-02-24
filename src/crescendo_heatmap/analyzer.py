from __future__ import annotations

from .models import Turn, TurnAnalysis


def _risk_band(score: float) -> str:
    if score >= 0.75:
        return "critical"
    if score >= 0.5:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def analyze_turns(turns: list[Turn]) -> list[TurnAnalysis]:
    if not turns:
        return []

    analyzed: list[TurnAnalysis] = []
    prev = turns[0].safety_score
    analyzed.append(TurnAnalysis(turn=turns[0], decay_delta=0.0, risk_band=_risk_band(prev)))

    for turn in turns[1:]:
        delta = turn.safety_score - prev
        analyzed.append(TurnAnalysis(turn=turn, decay_delta=delta, risk_band=_risk_band(turn.safety_score)))
        prev = turn.safety_score

    return analyzed


def summary_stats(analysis: list[TurnAnalysis]) -> dict:
    if not analysis:
        return {
            "turn_count": 0,
            "max_safety_score": 0.0,
            "avg_safety_score": 0.0,
            "net_decay": 0.0,
            "critical_turns": [],
            "turning_points": [],
        }

    scores = [a.turn.safety_score for a in analysis]
    turning_points = [a.turn.index for a in analysis if abs(a.decay_delta) >= 0.2]

    stats: dict = {
        "turn_count": len(analysis),
        "max_safety_score": max(scores),
        "avg_safety_score": sum(scores) / len(scores),
        "net_decay": scores[-1] - scores[0],
        "critical_turns": [a.turn.index for a in analysis if a.risk_band == "critical"],
        "turning_points": turning_points,
    }

    # 2026: per-agent breakdown when multi-agent conversation detected
    agent_ids = [a.turn.agent_id for a in analysis if a.turn.agent_id is not None]
    if agent_ids:
        unique_agents = sorted(set(agent_ids))
        stats["agents"] = unique_agents
        per_agent: dict[str, dict] = {}
        for aid in unique_agents:
            agent_scores = [a.turn.safety_score for a in analysis if a.turn.agent_id == aid]
            per_agent[aid] = {
                "turn_count": len(agent_scores),
                "avg_safety_score": round(sum(agent_scores) / len(agent_scores), 4),
                "max_safety_score": round(max(agent_scores), 4),
            }
        stats["per_agent"] = per_agent

    return stats
