# R94 — Full sub-point coverage + verbatim exact-text output + Groq Stage-0 default

User directives (2026-05-29):
1. **Full coverage incl. sub-points** — every article AND sub-point (e.g.
   Article 111(2), Article 6(1)) must resolve and map correctly across the
   whole Act, not just article-level.
2. **Verbatim exact text, no reformulations** — when a provision is cited,
   the answer quotes the **verbatim EUR-Lex text** for it. Caps relaxed
   ("verbatim quote, drop caps" option). Env-reversible.
3. **Groq Llama 3.3 70B as the default Stage-0 intent provider** (replacing
   Haiku). Test via the intent A/B.
4. **One validation question per article + annex (126)** wired as an eval
   set, plus the MedTech/healthcare use-case questions the user gave (Art.
   111(2) provider+deployer; pre-Aug-2026 high-risk; Art. 6(1)+Annex I
   timeline) and use-case variants.
5. **Reevaluate** — pytest, davidath bench, 276-runner, OOS probe, the new
   per-article coverage eval, intent A/B (Groq vs Haiku), and a live
   representative_100 + judge via the Claude Max wrapper.

## Recon findings (verified)

* Article/annex level coverage: **126/126** present + non-trivial in BOTH
  `OFFICIAL_ARTICLE_TEXT` and `EC_CHECKER_OBLIGATION_MAP`.
* No encoding corruption (0 U+FFFD), no mid-sentence truncation across 126.
* Sub-point extraction works after stripping the title prefix:
  `Article 111(2)` extracts verbatim correctly; 94/113 articles expose
  numbered paragraphs; the rest are genuinely single-block (amendment
  articles 102–110, single-list articles 16/32/39/66/85/87/94) OR
  parenthesised (Art. 3 definitions "(1)…(68)").
* **Confirmed gap: Article 113** — stored text dropped its paragraph
  numbers (`1./2./3.`) and the final "binding in its entirety" clause.
  Cross-referenced elsewhere as "Article 113(3), point (a)". Needs repair.
* Groq Stage-0 path already wired (R52) but defaults OFF — flip the default,
  keep wrapper/Haiku as fallback.
* Wire format is "Article N" (R92), not "Art. N".

## Workstreams

* **WS1 — Verbatim data integrity** (me): systematic paragraph-drop audit
  (extracted paragraphs vs `Article N(M)` xref targets); repair Article 113
  + any other confirmed drops; add corruption-gate test.
* **WS2 — Provision extractor** (me): `app/data/provision_text.py` —
  `get_provision_text("Article 111(2)" | "Article 6" | "Annex IV(2)" | ...)`
  → verbatim text, with title-strip + robust paragraph/subpoint resolution.
* **WS3 — Verbatim answer mode** (me): route + normaliser path that, when
  refs resolve, emits verbatim provision text; relax caps for verbatim;
  env-gated `REGENOLD_VERBATIM_ANSWER` (default ON), reversible.
* **WS4 — Groq Stage-0 default** (me): config/env/railway flip + tests.
* **WS5 — Per-article eval set** (agent): 126 questions (1/article+annex) +
  MedTech use-case questions; runner + coverage test.
* **WS6 — Reevaluate** (me): full gate suite + intent A/B + live rep_100+judge.

## Gates (must hold)

* pytest green; davidath bench rubric axes reported (verbatim mode WILL move
  conciseness — measured + reported honestly, env-reversible).
* OOS probe 21/21; 276-runner 276/276 (or documented).
* Every emitted citation resolves in `ARTICLE_EXISTENCE` (hard rule #5).
* Intent A/B: Groq vs Haiku agreement reported.
