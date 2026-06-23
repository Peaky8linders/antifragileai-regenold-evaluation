# R106 Live Regenold-Rubric Scorecard — Recent-Rounds Eval Sets

All four recent-rounds eval sets (the 190 questions documented in
`EVAL_QA_ROUNDS_100plus.md`) re-run **live** against the production
Railway endpoint (→ Cloudflare tunnel → Claude Max → Sonnet 4.6), scored
against the Regenold rubric.

- **Ref Correctness Loose/Strict, Ref Conciseness** — wire references vs gold (all sets).
- **Keyword Recall** — gold key-points surfaced in the answer (all sets).
- **Regulatory Tone** — regulator-voice heuristic (all sets).
- **Ans Correctness Loose/Strict, Ans Conciseness** — answer vs gold *prose*; only the
  GraphRAG set carries lawyer-reviewed gold prose, so the Ans axes are reported there only.
- **Coherence** — multi-turn final-turn coherence rate (multi-turn subsets).
- **Latency** — live Stage-2 (Sonnet) round-trip, p50/p95.

| Set | Subset | n | Ans L | Ans S | Ans Conc | Ref L | Ref S | Ref Conc | Kw | Tone | Coh | Latency |
| --- | ------ | - | ----- | ----- | -------- | ----- | ----- | -------- | -- | ---- | --- | ------- |
| GraphRAG benchmark | ground-truth (n_ans=25) | 30 | 0.4917 | 0.6109 | 0.6097 | 0.8536 | 0.7388 | 0.5521 | 0.5900 | 1.0000 | — | p50=17.1s p95=113.7s |
| Paper-V4 | singleturn | 20 | — | — | — | 0.7750 | 0.5485 | 0.4750 | 0.7167 | 1.0000 | — | p50=14.6s p95=63.9s |
| Paper-V4 | tricky | 20 | — | — | — | 0.7167 | 0.5050 | 0.3724 | 0.6000 | 1.0000 | — | p50=12.6s p95=57.4s |
| Paper-V4 | multiturn | 12 | — | — | — | 0.4167 | 0.2467 | 0.2438 | 0.4444 | 1.0000 | 0.4167 | p50=10.0s p95=17.5s |
| Paper-V3 | singleturn | 20 | — | — | — | 0.6167 | 0.4719 | 0.4828 | 0.3333 | 1.0000 | — | p50=13.5s p95=36.9s |
| Paper-V3 | tricky | 20 | — | — | — | 0.7771 | 0.6056 | 0.4731 | 0.3667 | 1.0000 | — | p50=17.3s p95=50.0s |
| Paper-V3 | multiturn | 12 | — | — | — | 0.4444 | 0.2882 | 0.3127 | 0.4028 | 1.0000 | 0.4167 | p50=20.7s p95=42.3s |
| V2 | tricky | 31 | — | — | — | 0.7419 | 0.5774 | 0.4872 | 0.5323 | 1.0000 | — | p50=15.9s p95=35.1s |
| V2 | multiturn | 25 | — | — | — | 0.8333 | 0.6546 | 0.5877 | 0.6467 | 1.0000 | 0.6000 | p50=17.7s p95=49.3s |

## Readout

- **Regulatory Tone = 1.0 on every subset** (190 questions). No tone failures, 0 HTTP failures.
- **GraphRAG ground-truth is the strongest set** — refL **0.854** / refS **0.739**;
  Ans L/S/Conc **0.49 / 0.61 / 0.61** (vs lawyer-reviewed gold prose). `Strict > Loose`
  on the Ans axes = synthesis answers carry correct-but-beyond-gold tokens (verbose, not wrong).
- **Single-turn / tricky are solid** — paper-V4 single refL 0.775, paper-V3 tricky refL 0.777,
  V2 tricky refL 0.742. V2 by-category: near_oos 1.0/1.0, borderline_prohibition 0.90,
  conflict 0.875, role_ambiguity 0.60, gpai 0.50, omnibus 0.667.
- **Multi-turn is the weak axis — but concentrated in the FRESH paper sets.**
  Paper-V3/V4 multi-turn: refL ~0.42, coherence **0.42**. V2 multi-turn (tuned over many
  rounds): refL **0.833**, coherence **0.60**. The fresh paper coreference / fact-shift
  conversations are where the gap is — see `.planning/MULTITURN-IMPROVEMENT-PLAN.md`.
  Root cause in the row data: ~25% of paper multi-turn finals are **scope-gate refusals**
  of in-scope follow-ups (the dominant, addressable failure).
- **Latency** is the live Stage-2 (Sonnet-via-tunnel) cost: p50 ~10–20s, p95 ~35–114s —
  the production-judge path; the deterministic engine floor is sub-20ms.
