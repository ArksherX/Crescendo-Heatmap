# Crescendo-Heatmap Benchmark: per-request vs. trajectory detection

This directory backs the central claim of the project with **runnable code**:
per-request (one-message-at-a-time) monitoring cannot catch multi-turn crescendo
attacks before exploitation; trajectory (session-level) monitoring can.

## Reproduce in two commands (no key, no network)

```bash
python benchmark/generate_dataset.py   # 214 labeled conversations, seed 1337
python benchmark/run_benchmark.py       # prints the table below, writes results.json
```

### Result (seed 1337, alert ≥3 turns before the critical turn)

| Monitor | Pre-critical detection (crescendo-class, n=130) |
|---|---|
| Per-request @ standard block threshold (0.75) | **0.0%** |
| Per-request @ aggressively tuned (0.50) | 36.2% |
| **Trajectory (turning-point + accumulation)** | **76.9%**, mean **5.3 turns** early |
| False positives on benign (n=60) | 0.0% |
| Control — per-request on overt attacks | 100% caught (but 0% *early*) |

Full methodology, sensitivity table, and honest caveats: [`REPORT.md`](REPORT.md).

## Realistic (LLM-scored) validation — optional

The command above uses the tool's deterministic keyword scorer. To validate the
same result on **natural-language** conversations with no keyword tells (scored
by an LLM on meaning):

```bash
pip install anthropic                # or: pip install openai
export ANTHROPIC_API_KEY=...          # or OPENAI_API_KEY
python benchmark/generate_natural.py
python benchmark/llm_validate.py --provider anthropic
```

Each turn is scored **in isolation** (no cross-turn context) — a faithful model
of a per-request classifier — then the same two monitors run on those scores.
Scores are cached in `.llm_cache.json`; commit the cache to make the LLM numbers
reproducible by others without spending tokens.

## Files

| File | Purpose |
|---|---|
| `generate_dataset.py` | Deterministic keyword-scored corpus (214 convs) |
| `generate_natural.py` | Natural-language, keyword-free corpus for LLM scoring |
| `run_benchmark.py` | Two-monitor evaluation (heuristic scorer) |
| `llm_validate.py` | Same evaluation, LLM scorer |
| `REPORT.md` | Methodology, results, caveats |
| `dataset.jsonl`, `results.json` | Generated artifacts |

## How to show this when someone challenges the numbers

1. **Show, don't assert.** `git clone`, then `python benchmark/run_benchmark.py`.
   The table prints in under a second on their machine. A claim backed by a
   command they can run themselves is not arguable.
2. **Lead with the honest framing.** The per-request "0%" at the 0.75 threshold
   is *partly definitional* — a guardrail whose block line is the critical line
   cannot fire before the critical turn. Say that first. Then land the
   non-definitional finding: even a per-request guardrail tuned well below the
   danger line (0.50) catches only 36% early, versus trajectory's 77%.
3. **Name the scope.** The 76.9% is a benchmark result on a defined attack-profile
   mix (mirroring the whitepaper's distribution), not a law of nature. More
   flat-then-critical attacks lower it; fewer raise it. Point to the sensitivity
   table in `REPORT.md`.
4. **Offer the realistic version.** If they push on "synthetic / keyword-scored,"
   run `llm_validate.py` on the natural-language corpus in front of them.
5. **Reconcile with the whitepaper.** This benchmark reproduces the whitepaper's
   73% pre-critical finding (Section 4.2) at 76.9% and adds the per-request
   baseline it lacked.
