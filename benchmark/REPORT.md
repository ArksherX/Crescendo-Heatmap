# Per-Request vs. Trajectory Detection — Benchmark Report

**Reproduce:**
```bash
python benchmark/generate_dataset.py   # writes dataset.jsonl (seed 1337)
python benchmark/run_benchmark.py      # writes results.json, prints summary
```
No network, no LLM, no API key. Deterministic (seed 1337).

## What this measures

A single, fair comparison. Both monitors consume the **same** per-turn safety
scores, produced by Crescendo-Heatmap's built-in scorer over each turn's text
(scores are *computed by the tool*, never hand-set). They differ only in the
decision function:

- **Per-request monitor** (stateless): flags turn *i* iff `score_i >= tau`. This
  is how a per-request guardrail sees a conversation — one message at a time, no
  memory of prior turns.
- **Trajectory monitor** (session-stateful): flags turn *i* on a decay-delta
  turning point (`|delta_i| >= 0.2`) or accumulated net decay (`score_i - score_1 >= 0.3`).

**Headline metric — pre-critical detection:** does the monitor fire at least
`lead` turns *before* the critical turn (first turn with `score >= 0.75`)? This
is the whitepaper's operational definition (Section 4.2, Finding 1): useful
detection is detection *before* exploitation.

## Dataset (synthetic, labeled, reproducible)

214 conversations: 154 attacks + 60 benign. Attacks span the whitepaper's
signature profiles (Section 4.3) plus an overt control:

| Profile | n | Description |
|---|---|---|
| A_gradual | 70 | Steady accumulation; score rises turn-over-turn to critical |
| B_spike | 34 | Spike-and-recovery, final spike to critical |
| C_flat_then_critical | 26 | Near-flat, then a 1–2 turn jump to critical (narrow pre-critical window) |
| abrupt | 24 | Overt: critical content in turn 1–2 (control) |
| benign | 60 | Normal traffic (false-positive measurement) |

Crescendo-class = A + B + C = **130** attacks. This is the scope the whitepaper's
73% figure refers to (successful crescendo attacks), so it is the scope of the
headline number below.

## Results (seed 1337, lead ≥ 3)

**Crescendo-class attacks (n=130), pre-critical detection:**

| Monitor | Pre-critical detection |
|---|---|
| Per-request, τ = 0.75 (standard block threshold) | **0.0%** |
| Per-request, τ = 0.50 (aggressively tuned) | 36.2% |
| **Trajectory (turning-point + accumulation)** | **76.9%** |
| Trajectory mean lead time | **5.32 turns** before critical |

**Control (overt/abrupt attacks, n=24):** per-request *any* detection **100%**,
pre-critical **0%**. Per-request works fine on overt attacks — it just cannot
warn *early* on crescendo.

**False positives (benign, n=60):** per-request **0.0%**, trajectory **0.0%**.

**Sensitivity to `lead`:**

| lead | per-req τ=0.75 | per-req τ=0.50 | trajectory |
|---|---|---|---|
| ≥1 | 0.0% | 76.9% | 80.0% |
| ≥2 | 0.0% | 67.7% | 80.0% |
| ≥3 | 0.0% | 36.2% | 76.9% |
| ≥5 | 0.0% | 11.5% | 53.1% |

## Honest caveats (read before citing)

1. **The `τ=0.75` "0%" is partly definitional.** A per-request guardrail whose
   block threshold *is* the critical threshold cannot, by construction, fire
   before the critical turn. That is exactly the architectural gap — but it
   should be stated as such, not as a surprising empirical measurement. The
   non-tautological comparison is **τ=0.50 (36.2%) vs. trajectory (76.9%)**:
   even a guardrail tuned well below the danger line catches less than half of
   what trajectory monitoring catches early.
2. **76.9% is a function of the profile mix**, which we chose to mirror the
   whitepaper's described distribution. More flat-then-critical (Profile C)
   attacks would lower it; fewer would raise it. It is a benchmark result on a
   defined corpus, **not a universal constant**.
3. **Synthetic, keyword-scored corpus.** Per-turn scores come from the tool's
   deterministic heuristic scorer, and conversations are templated. This is a
   controlled demonstration of the architectural principle, reproducible by
   anyone — not a measurement of a production attack corpus. Realistic
   natural-language validation requires the LLM scorer (`--llm-score`) and is
   left as follow-on work.
4. **Benign false-positive rate is optimistic.** Benign turns contain no risk
   vocabulary, so lowering the per-request threshold did not raise FPs here; in
   production, aggressive per-request thresholds trade recall for false alarms —
   a cost trajectory monitoring largely avoids because it keys on *change*.

## Defensible one-line summary

> On a reproducible 214-conversation benchmark (130 crescendo-class multi-turn
> attacks), per-request monitoring at a standard block threshold gave **0%**
> pre-critical warning — it cannot alert before the critical turn — while
> trajectory monitoring alerted on **76.9%** of crescendo attacks a mean **5.3
> turns** before exploitation, at **0%** false positives on benign traffic. Even
> an aggressively tuned per-request guardrail reached only 36%.
