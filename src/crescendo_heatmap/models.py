from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class Turn:
    index: int
    role: str
    content: str
    safety_score: float
    agent_id: str | None = None  # 2026: multi-agent support

    def to_dict(self) -> dict:
        d = asdict(self)
        if d["agent_id"] is None:
            d.pop("agent_id")
        return d


@dataclass
class TurnAnalysis:
    turn: Turn
    decay_delta: float
    risk_band: str

    def to_dict(self) -> dict:
        return {
            "turn": self.turn.to_dict(),
            "decay_delta": self.decay_delta,
            "risk_band": self.risk_band,
        }
