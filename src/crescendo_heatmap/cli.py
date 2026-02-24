from __future__ import annotations

import argparse

from .analyzer import analyze_turns, summary_stats
from .parser import load_turns
from .renderer import render_html, write_csv, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a safety decay heatmap for multi-turn conversations")
    parser.add_argument("--input", required=True, help="Input conversation file (.json, .jsonl, .txt)")
    parser.add_argument("--output", default="report.html", help="Output HTML heatmap path")
    parser.add_argument("--json", default=None, help="Optional JSON summary output path")
    parser.add_argument("--csv", default=None, help="Optional CSV output path")
    parser.add_argument(
        "--fail-score",
        type=float,
        default=None,
        help="Optional CI threshold: exit non-zero if max safety score >= this value",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    turns = load_turns(args.input)
    analysis = analyze_turns(turns)
    summary = summary_stats(analysis)

    render_html(analysis, args.output)
    if args.json:
        write_json(analysis, args.json, summary)
    if args.csv:
        write_csv(analysis, args.csv)

    print(
        f"Generated heatmap: {args.output} | turns={summary['turn_count']} | "
        f"max_score={summary['max_safety_score']:.3f} | net_decay={summary['net_decay']:+.3f}"
    )
    if args.fail_score is not None and summary["max_safety_score"] >= args.fail_score:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
