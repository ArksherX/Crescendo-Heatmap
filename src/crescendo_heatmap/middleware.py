from __future__ import annotations

from .analyzer import analyze_turns, summary_stats
from .models import Turn
from .parser import _heuristic_safety_score


class CrescendoMiddleware:
    """Framework-agnostic middleware for real-time conversation safety monitoring."""

    def __init__(self, alert_threshold: float = 0.75) -> None:
        self.alert_threshold = alert_threshold
        self._sessions: dict[str, list[Turn]] = {}

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_id: str | None = None,
    ) -> dict:
        """Append a turn, analyze the session, and return safety assessment."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        turns = self._sessions[session_id]
        idx = len(turns) + 1
        safety_score = _heuristic_safety_score(content)
        turn = Turn(
            index=idx,
            role=role,
            content=content,
            safety_score=safety_score,
            agent_id=agent_id,
        )
        turns.append(turn)

        analysis = analyze_turns(turns)
        stats = summary_stats(analysis)

        current = analysis[-1] if analysis else None
        is_turning_point = current is not None and abs(current.decay_delta) >= 0.2
        interrupt = safety_score >= self.alert_threshold

        return {
            "safety_score": round(safety_score, 4),
            "risk_band": current.risk_band if current else "low",
            "is_turning_point": is_turning_point,
            "interrupt": interrupt,
            "summary": {
                "turn_count": stats["turn_count"],
                "max_safety_score": round(stats["max_safety_score"], 4),
                "avg_safety_score": round(stats["avg_safety_score"], 4),
                "turning_points": stats["turning_points"],
            },
        }

    def get_session(self, session_id: str) -> list[Turn]:
        return self._sessions.get(session_id, [])

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


def create_app(alert_threshold: float = 0.75):
    """Create a FastAPI app for the middleware (guarded import)."""
    try:
        from fastapi import FastAPI
    except ImportError:
        raise ImportError(
            "fastapi is required for --serve mode. Install it with: pip install fastapi"
        )

    from pydantic import BaseModel

    app = FastAPI(title="Crescendo Heatmap Middleware", version="1.0.0")
    mw = CrescendoMiddleware(alert_threshold=alert_threshold)

    class TurnRequest(BaseModel):
        session_id: str
        role: str
        content: str
        agent_id: str | None = None

    class AnalyzeRequest(BaseModel):
        turns: list[dict]

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/turn")
    def post_turn(req: TurnRequest):
        return mw.add_turn(req.session_id, req.role, req.content, req.agent_id)

    @app.post("/analyze")
    def post_analyze(req: AnalyzeRequest):
        """One-shot batch analysis of a full conversation."""
        turns: list[Turn] = []
        for i, item in enumerate(req.turns, start=1):
            role = str(item.get("role", "unknown"))
            content = str(item.get("content", ""))
            safety_score = item.get("safety_score")
            if safety_score is None:
                safety_score = _heuristic_safety_score(content)
            turns.append(Turn(
                index=i,
                role=role,
                content=content,
                safety_score=float(safety_score),
                agent_id=item.get("agent_id"),
            ))

        analysis = analyze_turns(turns)
        stats = summary_stats(analysis)
        return {
            "summary": stats,
            "turns": [a.to_dict() for a in analysis],
        }

    return app


def run_server(host: str, port: int, alert_threshold: float = 0.75) -> None:
    """Start the middleware server (guarded uvicorn import)."""
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "uvicorn is required for --serve mode. Install it with: pip install uvicorn"
        )

    app = create_app(alert_threshold)
    print(f"Starting Crescendo middleware on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
