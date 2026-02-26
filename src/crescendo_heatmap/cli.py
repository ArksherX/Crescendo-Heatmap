from __future__ import annotations

import argparse
import sys

from .analyzer import analyze_turns, summary_stats
from .parser import load_turns
from .renderer import render_html, write_csv, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a safety decay heatmap for multi-turn conversations")
    parser.add_argument("--input", default=None, help="Input conversation file (.json, .jsonl, .txt)")
    parser.add_argument("--output", default="report.html", help="Output HTML heatmap path")
    parser.add_argument("--json", default=None, help="Optional JSON summary output path")
    parser.add_argument("--csv", default=None, help="Optional CSV output path")
    parser.add_argument(
        "--fail-score",
        type=float,
        default=None,
        help="Optional CI threshold: exit non-zero if max safety score >= this value",
    )
    # Step 4: LLM-based scoring
    parser.add_argument("--llm-score", action="store_true", help="Re-score turns using an LLM")
    parser.add_argument("--llm-provider", choices=["openai", "anthropic"], default="openai", help="LLM provider")
    parser.add_argument("--llm-model", default=None, help="Specific model name (provider default if omitted)")
    # Step 8: Real-time middleware hook
    parser.add_argument("--serve", action="store_true", help="Start real-time middleware HTTP server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host for --serve mode")
    parser.add_argument("--port", type=int, default=8001, help="Server port for --serve mode")
    parser.add_argument("--alert-threshold", type=float, default=0.75, help="Alert threshold for --serve mode")
    # Step 10: REST API mode
    parser.add_argument("--api", action="store_true", help="Start REST API server")
    parser.add_argument("--api-host", default="0.0.0.0", help="API server host")
    parser.add_argument("--api-port", type=int, default=8001, help="API server port")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Step 8: serve mode early branch
    if args.serve:
        from .middleware import run_server
        run_server(args.host, args.port, args.alert_threshold)
        return 0

    # Step 10: API mode early branch
    if args.api:
        from .api import run_server as run_api
        run_api(args.api_host, args.api_port)
        return 0

    # --input is required when not in serve/api mode
    if not args.input:
        print("Error: --input is required when not using --serve or --api", file=sys.stderr)
        return 1

    turns = load_turns(args.input)

    # Step 4: optional LLM re-scoring
    if args.llm_score:
        from .llm_scorer import rescore_with_llm
        turns = rescore_with_llm(turns, args.llm_provider, args.llm_model)

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
