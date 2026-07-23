"""CRAG-style corrective verification + NLI citation grounding (plan §6/§8).

Two ideas from the literature, one module:

  * **CRAG** -- Corrective Retrieval-Augmented Generation (Yan, Gu, Zhu, Ling,
    arXiv:2401.15884, 2024). Don't trust retrieval blindly. A lightweight
    *evaluator* -- in the paper a fine-tuned T5-large, **separate** from the
    generator -- grades each retrieved document's relevance to the query, then a
    controller takes a corrective action: **Correct** (something clears the upper
    threshold -> keep/refine), **Incorrect** (everything is below the lower
    threshold -> discard and fall back), **Ambiguous** (in between -> combine).
    Our corpus is the *closed, authoritative* EU AI Act, so there is no external
    source to fall back to: the "Incorrect" branch becomes **abstention** (cite
    nothing -- the honest action when the Act does not cover the question).

  * **ALCE / citation grounding** (Gao, Yen, Yu, Chen, arXiv:2305.14627, EMNLP
    2023). A citation is only valid if the cited passage **entails** the claim:
    ``phi(premise, hypothesis) = 1`` iff the premise (provision text) entails the
    hypothesis (the claim). ALCE scores citation *precision* per-citation -- a
    citation is irrelevant if it alone does not entail the claim -- which is
    exactly the per-citation keep/drop signal we want here (as opposed to ALCE's
    *recall*, which entails against the concatenation of all citations).

In the retrieval baselines the "claim" is the question itself, so both ideas
collapse to one operation: **grade each emitted citation's (question, provision)
support, then keep / drop / abstain on it.** The grader is an
:class:`EntailmentScorer`:

  * :class:`LexicalEntailmentScorer` -- runnable NOW, no extra deps: idf-weighted
    *coverage* of the claim's content terms by the provision text. **Honest label:
    this is a lexical coverage proxy, NOT neural NLI.** Exactly the discipline of
    TF-IDF ("lexical not dense") and LSA ("classical not neural") elsewhere in the
    harness -- it stands in so the whole corrective control-flow runs, tests, and
    produces real offline numbers with zero models. It is directional (how much of
    the *claim* the provision covers), which is a different signal from the
    symmetric query<->provision cosine the retriever already used.

  * :class:`NLIEntailmentScorer` -- the real thing: a sentence-pair NLI
    cross-encoder (default ``cross-encoder/nli-deberta-v3-large``), P(entailment)
    as the support score. Behind a lazy optional-dep gate: if
    ``sentence-transformers`` / the model is missing it raises a clear
    ``RuntimeError`` -- it never fabricates a score. A model can be injected for
    offline unit-testing. Same honesty gating as the frontier-LLM baseline.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass

from ..ids import ProvisionId
from ..models import Provision
from .base import Baseline, question_text
from .retrieval import tokenize

__all__ = [
    "EntailmentScorer",
    "LexicalEntailmentScorer",
    "NLIEntailmentScorer",
    "CragThresholds",
    "VerifiedBaseline",
    "DEFAULT_NLI_MODEL",
]

# The default NLI cross-encoder. Its entailment logit is index 1 -- verified from
# the model's own config.json: id2label = {0: contradiction, 1: entailment,
# 2: neutral}. This is NOT universal (many DeBERTa-MNLI checkpoints put entailment
# at index 2), so :class:`NLIEntailmentScorer` resolves the index from the model's
# label map at runtime and only falls back to this default.
DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-large"
_DEFAULT_ENTAIL_INDEX = 1


def _softmax(xs: list[float]) -> list[float]:
    """Numerically stable softmax over a short logit vector (pure Python -- no
    numpy dependency in the hot path; NLI rows are length 3)."""
    if not xs:
        return []
    m = max(xs)
    exps = [math.exp(x - m) for x in xs]
    total = sum(exps)
    if total == 0.0:  # pragma: no cover - defensive; exp is never all-zero
        return [1.0 / len(xs)] * len(xs)
    return [e / total for e in exps]


class EntailmentScorer(ABC):
    """Scores how strongly a ``premise`` (provision text) supports a ``claim``
    (the question, or an answer sentence). Returns a support score in ``[0, 1]``:
    the NLI/ALCE entailment signal -- does the cited provision actually back the
    claim -- as opposed to mere topical similarity (which cosine already gives)."""

    name: str = "entailment"

    @abstractmethod
    def score(self, claim: str, premise: str) -> float:
        raise NotImplementedError

    def score_batch(self, claim: str, premises: list[str]) -> list[float]:
        """One claim vs many premises. Default: loop :meth:`score`. Neural
        implementations override this to batch the forward pass."""
        return [self.score(claim, p) for p in premises]


class LexicalEntailmentScorer(EntailmentScorer):
    """Idf-weighted coverage of the claim by the premise -- a runnable, model-free
    proxy for entailment (NOT neural NLI; see module docstring).

    ``score = (sum of idf of claim content-terms that also occur in the premise)
    / (sum of idf of all claim content-terms)`` -- the fraction of the claim's
    information mass that the provision text covers. Directional and asymmetric
    (unlike the retriever's symmetric cosine): a long provision is not penalised
    for containing terms the short question lacks, and rare (high-idf) claim terms
    dominate. A claim with no in-vocabulary content term scores 0 (nothing to
    ground)."""

    def __init__(self, provisions: list[Provision]) -> None:
        docs = [tokenize(p.text) for p in provisions]
        n = len(docs)
        df: Counter[str] = Counter()
        for toks in docs:
            df.update(set(toks))
        # smoothed idf, always positive -- identical formula to TfidfRetriever
        self._idf: dict[str, float] = {
            t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()
        }
        self.name = "lexical-coverage"

    def score(self, claim: str, premise: str) -> float:
        claim_terms = set(tokenize(claim))
        if not claim_terms:
            return 0.0
        # weight by idf; unseen terms (not in any provision) get a floor idf of 1.0
        # so an out-of-vocabulary claim term still counts against coverage.
        weights = {t: self._idf.get(t, 1.0) for t in claim_terms}
        total = sum(weights.values())
        if total == 0.0:  # pragma: no cover - weights are >= 1.0 each
            return 0.0
        premise_terms = set(tokenize(premise))
        covered = sum(w for t, w in weights.items() if t in premise_terms)
        return covered / total


class NLIEntailmentScorer(EntailmentScorer):
    """Sentence-pair NLI entailment via a cross-encoder. ``score`` = P(entailment)
    for the pair (premise=provision text, hypothesis=claim).

    The model (default ``cross-encoder/nli-deberta-v3-large``) is loaded lazily and
    gated: a missing ``sentence-transformers``/model raises a clear
    ``RuntimeError`` rather than fabricating scores. Inject ``model`` (anything
    exposing ``.predict(pairs) -> rows of 3 logits`` and, ideally, a
    ``.config.id2label``/``label2id``) to unit-test the logic with no package,
    download, or GPU."""

    def __init__(
        self,
        model_name: str = DEFAULT_NLI_MODEL,
        *,
        model=None,
        batch_size: int = 16,
        entail_index: int | None = None,
        apply_softmax: bool = True,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        # ``predict`` must return raw logits (apply_softmax=True, the default and
        # correct for cross-encoder/nli-deberta-v3-large). Set apply_softmax=False
        # only for a model that already returns a normalised probability row, so we
        # never double-transform it.
        self.apply_softmax = apply_softmax
        self._model = model if model is not None else self._load(model_name)
        self._entail_index = (
            entail_index
            if entail_index is not None
            else self._resolve_entail_index(self._model, _DEFAULT_ENTAIL_INDEX)
        )
        self.name = f"nli:{model_name}"

    @staticmethod
    def _load(model_name: str):
        """Construct a real CrossEncoder, or raise a clear error. Never degrades
        silently."""
        try:
            from sentence_transformers import CrossEncoder
        except ModuleNotFoundError as e:  # optional dep not installed
            raise RuntimeError(
                "NLIEntailmentScorer needs `sentence-transformers` (and torch) -- "
                "install with `uv sync --extra verify` (or inject a model). The "
                "lexical scorer runs with no extra deps."
            ) from e
        return CrossEncoder(model_name)

    @staticmethod
    def _resolve_entail_index(model, default: int) -> int:
        """Find the 'entailment' output index from the model's label map. The index
        is model-specific (deberta-v3-large NLI puts it at 1, but many MNLI
        checkpoints use 2), so never assume -- read it, and only fall back to
        ``default`` if no unambiguous label is found.

        Guards against the ``not_entailment`` / ``non-entailment`` labels used by
        some binary-NLI checkpoints: a naive ``'entail' in label`` substring test
        would match those and silently select the *negation* class. So we prefer an
        exact ``entailment`` label, then an unambiguous substring match that
        excludes negations, and only then the caller-supplied default."""
        cfg = getattr(model, "config", None)
        label2id = getattr(cfg, "label2id", None)
        id2label = getattr(cfg, "id2label", None)
        mapping: dict[str, int] = {}
        if isinstance(label2id, dict):
            mapping = {str(lbl).lower(): int(i) for lbl, i in label2id.items()}
        elif isinstance(id2label, dict):
            mapping = {str(lbl).lower(): int(i) for i, lbl in id2label.items()}
        if mapping:
            if "entailment" in mapping:  # exact label wins
                return mapping["entailment"]
            candidates = [
                i for lbl, i in mapping.items()
                if "entail" in lbl and "not" not in lbl and "non" not in lbl
            ]
            if len(candidates) == 1:  # unambiguous substring match
                return candidates[0]
        return default

    def score(self, claim: str, premise: str) -> float:
        return self.score_batch(claim, [premise])[0]

    def score_batch(self, claim: str, premises: list[str]) -> list[float]:
        if not premises:
            return []
        # NLI direction: premise (provision) entails hypothesis (claim). The
        # CrossEncoder takes (text_a, text_b) pairs.
        pairs = [(premise, claim) for premise in premises]
        raw = self._model.predict(pairs, batch_size=self.batch_size)
        out: list[float] = []
        for row in raw:
            vals = [float(x) for x in row]
            if self._entail_index >= len(vals):  # misconfigured model -> fail clean
                raise RuntimeError(
                    f"NLI model returned {len(vals)} scores per pair; no index "
                    f"{self._entail_index} for entailment. Check the model or pass "
                    f"entail_index explicitly."
                )
            probs = _softmax(vals) if self.apply_softmax else vals
            out.append(probs[self._entail_index])
        return out


@dataclass(frozen=True)
class CragThresholds:
    """The two CRAG thresholds, adapted to a closed authoritative corpus.

    ``keep`` -- drop any individual citation whose support is below this (the
    per-citation ALCE precision filter). ``abstain`` -- if the *best* surviving
    citation's support is below this, the query is judged out-of-scope and the
    whole prediction becomes ``[]`` (CRAG's "Incorrect" action, with abstention
    replacing web-search fallback). Both default to 0 -> a pass-through that only
    re-ranks nothing and never abstains, so the wrapper is a no-op until tuned."""

    keep: float = 0.0
    abstain: float = 0.0


class VerifiedBaseline(Baseline):
    """Wrap any :class:`Baseline` with a CRAG corrective verification pass.

    Runs the wrapped baseline, then for each emitted citation grades the
    (question, provision-text) support with an :class:`EntailmentScorer` and
    applies the corrective action: keep citations at/above ``keep``, abstain
    entirely (return ``[]``) if the best support is below ``abstain``. Emission
    order from the base baseline is preserved (verification filters, it does not
    re-rank); the surviving list is capped at ``k`` if given."""

    def __init__(
        self,
        base: Baseline,
        scorer: EntailmentScorer,
        provisions: list[Provision],
        *,
        thresholds: CragThresholds | None = None,
        keep: float | None = None,
        abstain: float | None = None,
        k: int | None = None,
        drop_unresolvable: bool = False,
    ) -> None:
        self.base = base
        self.scorer = scorer
        self._text: dict[str, str] = {p.provision_id: p.text for p in provisions}
        if thresholds is None:
            thresholds = CragThresholds(
                keep=keep if keep is not None else 0.0,
                abstain=abstain if abstain is not None else 0.0,
            )
        self.thresholds = thresholds
        self.k = k
        self.drop_unresolvable = drop_unresolvable
        self.name = (
            f"{base.name}+verify({scorer.name},"
            f"keep={thresholds.keep},abstain={thresholds.abstain})"
        )

    def _resolve_text(self, citation: str) -> str | None:
        """Provision text for an emitted citation. Tries the raw eid first, then
        parses a human-form citation (e.g. 'Article 6(2)') to its eid. Returns
        ``None`` when the citation names nothing in the corpus -- which for our
        full-Act corpus is itself a signal the citation is suspect."""
        text = self._text.get(citation)
        if text is not None:
            return text
        try:
            return self._text.get(ProvisionId.parse(citation).eid)
        except Exception:
            return None

    def predict(self, item: dict) -> list[str]:
        claim = question_text(item)
        cites = list(self.base.predict(item))
        if not cites:
            return []

        texts = [self._resolve_text(c) for c in cites]
        resolvable = [(c, t) for c, t in zip(cites, texts) if t is not None]
        supports = (
            self.scorer.score_batch(claim, [t for _, t in resolvable])
            if resolvable
            else []
        )
        support_by_cite = {c: s for (c, _), s in zip(resolvable, supports)}

        # CRAG "Incorrect" -> abstain: judged only on citations we could ground.
        # If nothing resolved, we have no entailment evidence either way, so we do
        # not abstain on that basis (the retriever's own emission stands).
        if support_by_cite and max(support_by_cite.values()) < self.thresholds.abstain:
            return []

        kept: list[str] = []
        for c, t in zip(cites, texts):
            if t is None:
                if not self.drop_unresolvable:
                    kept.append(c)  # can't verify -> keep unless told to prune
                continue
            if support_by_cite[c] >= self.thresholds.keep:
                kept.append(c)

        return kept[: self.k] if self.k is not None else kept
