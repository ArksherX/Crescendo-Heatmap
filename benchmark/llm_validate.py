"""LLM-scored validation of the per-request vs. trajectory result.

Uses the tool's OWN LLM scorer (crescendo_heatmap.llm_scorer.score_turn) to
assign each turn a safety score IN ISOLATION (empty context) — the faithful
model of a per-request classifier judging a single message. The same two
monitors from run_benchmark.py then consume those scores; only the decision
logic differs.

This removes the "keyword-scored / synthetic" caveat of the heuristic run: the
natural-language corpus (benchmark/dataset_natural.jsonl) has nothing for a
keyword matcher to catch, so any signal comes from the LLM's semantic judgment.

Requirements (NOT needed for the heuristic benchmark):
    pip install anthropic     # or: pip install openai
    export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY

Run:
    python benchmark/generate_natural.py
    python benchmark/llm_validate.py --provider anthropic     # ~N*turns calls
Scores are cached in benchmark/.llm_cache.json, so re-runs are free and the
evaluation is reproducible once the cache is populated (commit the cache to make
the numbers reproducible by others without spending tokens).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
sys.path.insert(0, str(ROOT / "src"))

from crescendo_heatmap.llm_scorer import score_turn, _check_dependencies  # noqa: E402
from crescendo_heatmap.models import Turn  # noqa: E402
import run_benchmark as rb  # noqa: E402  (same directory)

CACHE_PATH = HERE / ".llm_cache.json"


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=0), encoding="utf-8")


def make_llm_scorer(provider: str, model: str | None, cache: dict):
    key_model = model or ("default")

    def scorer(content: str, index: int, rec: dict) -> float:
        ck = f"{provider}::{key_model}::{content}"
        if ck in cache:
            return cache[ck]
        # Score the turn ALONE — no cross-turn context — so this is a true
        # per-request assessment. Trajectory logic is applied afterwards.
        turn = Turn(index=index, role="user", content=content, safety_score=0.0)
        score = score_turn(turn, [], provider, model)
        cache[ck] = score
        return score

    return scorer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(HERE / "dataset_natural.jsonl"))
    ap.add_argument("--provider", choices=["anthropic", "openai"], default="anthropic")
    ap.add_argument("--model", default=None)
    ap.add_argument("--lead", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None, help="score only the first N conversations")
    ap.add_argument("--out", default=str(HERE / "results_llm.json"))
    args = ap.parse_args()

    _check_dependencies(args.provider)  # clear error if pkg/key missing

    records = rb._load(Path(args.dataset))
    if args.limit:
        records = records[: args.limit]

    cache = _load_cache()
    scorer = make_llm_scorer(args.provider, args.model, cache)

    n_turns = sum(len(r["turns"]) for r in records)
    print(f"Scoring {len(records)} conversations / {n_turns} turns "
          f"via {args.provider} (cached: {len(cache)})...", file=sys.stderr)

    try:
        result = rb.evaluate(records, args.lead, scorer=scorer)
    finally:
        _save_cache(cache)  # persist whatever we scored, even on interrupt

    result["summary"]["scorer"] = f"llm:{args.provider}:{args.model or 'default'}"
    result["summary"]["corpus"] = "natural-language (keyword-free)"
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    s = result["summary"]; h = s["headline"]
    print("=" * 68)
    print(f"LLM-SCORED VALIDATION [{s['scorer']}]  (n={s['n_total']}, "
          f"{s['n_attack']} attack / {s['n_benign']} benign; lead>={s['lead_turns_required']})")
    print("=" * 68)
    print(f"Crescendo-class attacks (n={s['n_crescendo_class']}) — pre-critical detection:")
    print(f"  per-request  (tau=0.75): {h['crescendo_class_per_request_075_precritical_pct']:>5}%")
    print(f"  per-request  (tau=0.50): {h['crescendo_class_per_request_050_precritical_pct']:>5}%")
    print(f"  trajectory   (TP+accum): {h['crescendo_class_trajectory_precritical_pct']:>5}%")
    print(f"  trajectory mean lead   : {s['trajectory_mean_lead_turns']} turns")
    print(f"False positives on benign: per-request {s['false_positive_rate']['per_request_075_pct']}%  "
          f"trajectory {s['false_positive_rate']['trajectory_pct']}%")
    print("=" * 68)
    print(f"full results -> {args.out}   (scores cached in {CACHE_PATH.name})")


if __name__ == "__main__":
    main()
