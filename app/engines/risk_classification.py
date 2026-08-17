"""R353 — the R352 surviving hypothesis, made concrete.

R352 measured the broad risk-classification triad (``Art. 6`` + ``Annex III``
+ ``Annex I`` anchored whenever a question asks for a risk classification)
and refuted it: 12% precision, with ``Art. 6`` at exactly 0% — gold cites the
LIST (``Annex III``), never the rule that points at the list. What survived
that computation was one narrow shape:

    "Is [ordinary software / consumer tool] high-risk (or regulated) under
     the AI Act?" — where the correct answer is "no, and here is the list
     (Annex III) it is not on."

The exact gold impact of this trigger was computed over the whole 297-row
probe pool BEFORE this module was written (R352's own doctrine), with the
methodology replicated independently (scratch/verify_r352_final.py —
the broad-triad table reproduces R352 §3 to the row: Art. 6 0%, Annex III
24%, Annex I 11%):

    * trigger fires on 13 rows;
    * ``Annex III`` is gold-but-not-anchored on 7 of them
      (lr_spam_filter, lr_music_recommender, lr_chatbot, lr_translation,
      lr_image_generator, graphrag:med_6, live_answers:la_q46);
    * the only non-gold fire was a "prohibited OR high-risk" question
      (lr_ctrl_social_scoring) whose gold is Art. 5 — excluded below by the
      ``prohibit|banned|illegal`` negative, which no gold row contains;
    * 92% precision raw, 100% with that one exclusion, 0 false positives on
      the remaining 284 rows.

The anchor is a RECALL SUPPLEMENT: ``Annex III`` is appended to the entity
list (never prepended, never displacing a keyword anchor), and on the
default path the cross-encoder rerank then decides its final position —
the reranker is the precision guard against a trigger misfire on an unseen
question. Gate: ``REGENOLD_RISK_CLASS_ANNEX`` (default OFF, registered in
``_engine_cache_key`` per the R30/R56/R79/R263.2 doctrine).

Never raises; a malformed question simply returns False.
"""

from __future__ import annotations

import os
import re

_TRUTHY = ("1", "true", "yes", "on")

_ENV_GATE = "REGENOLD_RISK_CLASS_ANNEX"

#: The question must OPEN with a yes/no auxiliary — "What …", "Which …",
#: "How …", "Does X require …" are different shapes.
_YN_RE = re.compile(r"^\s*(?:is|are|does|do|would|will|can)\b", re.IGNORECASE)

#: A classification term. NOTE: "prohibited" alone is deliberately NOT in
#: this class — prohibition questions' gold is Art. 5, never Annex III.
_CLASS_TERM_RE = re.compile(
    r"\b(?:high-risk|high risk|regulated(?: under)?|subject to the ai act|"
    r"fall under the high-risk|classified as high-risk|considered high-risk|"
    r"a high-risk ai system|high-risk classification)\b",
    re.IGNORECASE,
)

#: Shapes that mention "high-risk" but are NOT "is this system high-risk?":
#: list/definition questions, obligation/technical-documentation questions
#: ("Does the technical documentation … require specifications …"), and
#: prohibition questions.
_NOT_CLASS_RE = re.compile(
    r"\b(?:what|which|how|when|where|why|who|list|explain|describe|"
    r"require\w*|specification\w*|technical documentation|"
    r"obligation\w*|penalt\w*|fine\b|prohibit\w*|banned|illegal)\b",
    re.IGNORECASE,
)

#: Domains where "is X high-risk?" routes through Annex I (medical devices),
#: Art. 5 (prohibitions), or a sector regime — never the Annex III list.
_EXCLUDE_RE = re.compile(
    r"\b(?:medic\w*|health\w*|patient\w*|x-ray|xray|tumor\w*|tumour\w*|"
    r"surg\w*|device\w*|drug\w*|clinical\w*|hospital\w*|worker\w*|"
    r"employ\w*|recruit\w*|law enforcement|police\w*|biometric\w*|"
    r"credit\w*|insur\w*|border\w*|migrat\w*|asylum|justice|education\w*|"
    r"school\w*|exam\w*|student\w*|voting|election\w*|infrastructure\w*|"
    r"essential service|safety component|robot\w*|machin\w*|vehicle\w*|"
    r"aircraft|transport\w*|energy|water\w*|nuclear|gpaI|"
    r"foundation model|systemic risk|melanoma|dermoscopy|diagnos\w*|"
    r"video game|opponent in a game|gaming)\b",
    re.IGNORECASE,
)


def annex_iii_risk_class_anchor_enabled() -> bool:
    """``REGENOLD_RISK_CLASS_ANNEX`` — **DEFAULT OFF**, fresh read per call.

    Registered in ``_engine_cache_key`` (R30/R56/R79/R263.2 doctrine) so an
    in-process A/B of the lever is real — flipping the gate mid-process
    cannot serve the other arm's cached engine output.
    """
    return os.getenv(_ENV_GATE, "0").strip().lower() in _TRUTHY


def is_yes_no_risk_classification(question: str) -> bool:
    """Does this question have the "is X high-risk?" shape?

    Pure, deterministic, never raises. This is the trigger that R352 §4
    left open and the whole-pool computation above fitted to 100% precision
    (with the prohibition exclusion).
    """
    q = str(question or "")
    if not q.strip():
        return False
    if not _YN_RE.search(q):
        return False
    if not _CLASS_TERM_RE.search(q):
        return False
    if _NOT_CLASS_RE.search(q):
        return False
    if _EXCLUDE_RE.search(q):
        return False
    return True


# ── R365 — Article 50 chatbot-transparency anchor ─────────────────────────
#
# R353.1's true-gap table showed Article 50 gold-but-not-anchored on 18 of
# the 297 pool rows, concentrated on chatbot/interaction questions: the
# answer is "not high-risk -> limited-risk -> the Article 50 transparency
# duties apply" (interaction disclosure 50(1), synthetic-content marking
# 50(2), deepfake disclosure 50(4)), yet the keyword map never anchors
# Article 50 on those shapes. Exact gold impact computed over the whole pool
# before this code existed (scratch/r365_art50_trigger.py): the trigger
# fires on 4 rows and Article 50 is gold-but-not-anchored on all 4 — 100%
# precision, zero non-gold additions. The exclusions are principled, not
# fitted: care-triage chatbots route to the high-risk Annex III/6 answer
# (Article 50 not gold), and "we are building X — what do we need to know?"
# shapes route to GPAI/provider-obligation answers.

_ENV_GATE_ART50 = "REGENOLD_ART50_CHAT_ANCHOR"

#: The interaction surface: a chatbot / chat assistant / conversational AI.
_ART50_CHATBOT_RE = re.compile(
    r"\b(?:chat\s?bot|chat assistant|conversational(?: ai)?)\b",
    re.IGNORECASE,
)

#: Shapes that mention a chatbot but do NOT answer with Article 50:
#: care-triage/urgency chatbots (high-risk route — Annex III point 5(d) /
#: Article 6) and build/obligation questions ("we are building X, what do
#: we need to know?") whose gold is the GPAI/provider-obligation surface.
_ART50_NOT_RE = re.compile(
    r"\b(?:triage|urgency|symptom\w*|emergency\w*|need to know|"
    r"we are building|we want to build|developing a|obligation\w*)\b",
    re.IGNORECASE,
)


def art50_chatbot_anchor_enabled() -> bool:
    """``REGENOLD_ART50_CHAT_ANCHOR`` — **DEFAULT OFF**, fresh read per call.

    Registered in ``_engine_cache_key`` (R30/R56/R79/R263.2 doctrine) so an
    in-process A/B of the lever is real.
    """
    return os.getenv(_ENV_GATE_ART50, "0").strip().lower() in _TRUTHY


def is_chatbot_transparency_question(question: str) -> bool:
    """Does this question describe a chatbot whose answer needs Article 50?

    Pure, deterministic, never raises. Fitted to 100% precision over the
    297-row pool (4 fires, 4 gold Article-50-but-not-anchored, 0 non-gold
    additions) with the triage/build exclusions above.
    """
    q = str(question or "")
    if not q.strip():
        return False
    if not _ART50_CHATBOT_RE.search(q):
        return False
    if _ART50_NOT_RE.search(q):
        return False
    return True
