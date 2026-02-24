from crescendo_heatmap.analyzer import analyze_turns, summary_stats
from crescendo_heatmap.models import Turn


def test_analyze_turns_tracks_delta() -> None:
    turns = [
        Turn(index=1, role="user", content="hello", safety_score=0.1),
        Turn(index=2, role="user", content="jailbreak prompt", safety_score=0.6),
    ]
    analysis = analyze_turns(turns)
    assert len(analysis) == 2
    assert analysis[1].decay_delta == 0.5


def test_summary_stats() -> None:
    turns = [
        Turn(index=1, role="user", content="safe", safety_score=0.1),
        Turn(index=2, role="assistant", content="risk", safety_score=0.9),
    ]
    s = summary_stats(analyze_turns(turns))
    assert s["turn_count"] == 2
    assert s["critical_turns"] == [2]
    assert s["turning_points"] == [2]
