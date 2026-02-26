from __future__ import annotations

from .analyzer import analyze_turns, summary_stats
from .middleware import CrescendoMiddleware
from .models import Turn
from .parser import _heuristic_safety_score


def create_app():
    """Create a FastAPI app for the Crescendo Heatmap API."""
    try:
        from fastapi import FastAPI
    except ImportError:
        raise ImportError(
            "fastapi is required for --api mode. Install it with: pip install fastapi"
        )

    from pydantic import BaseModel

    app = FastAPI(title="Crescendo Heatmap API", version="1.0.0")
    mw = CrescendoMiddleware()

    class TurnInput(BaseModel):
        role: str
        content: str
        safety_score: float | None = None
        agent_id: str | None = None

    class AnalyzeRequest(BaseModel):
        turns: list[TurnInput]

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/analyze")
    def analyze(req: AnalyzeRequest):
        turns: list[Turn] = []
        for i, item in enumerate(req.turns, start=1):
            score = item.safety_score
            if score is None:
                score = _heuristic_safety_score(item.content)
            turns.append(Turn(
                index=i,
                role=item.role,
                content=item.content,
                safety_score=float(score),
                agent_id=item.agent_id,
            ))

        analysis = analyze_turns(turns)
        stats = summary_stats(analysis)
        return {
            "summary": stats,
            "turns": [a.to_dict() for a in analysis],
        }

    return app


def run_server(host: str, port: int) -> None:
    """Start the API server (guarded uvicorn import)."""
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "uvicorn is required for --api mode. Install it with: pip install uvicorn"
        )

    app = create_app()
    print(f"Starting Crescendo Heatmap API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
