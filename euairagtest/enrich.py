"""ML enrichment: the deontic / actor / risk layer (plan §4, extraction cascade).

This is the *enrichment* tier — everything the deterministic backbone cannot derive
from structure alone. It follows the same discipline as the Phase-1 HF loader: the heavy
models are imported lazily and only the model-free *merge* step is exercised in tests.

Verified stack (2026-07-22):
* **GLiNER-Relex v0.5** (``knowledgator/gliner-relex-large-v0.5``, May 2026) — joint
  zero-shot NER + relation extraction in one encoder pass; supersedes the plan's separate
  GLiNER + ReLiK relation step. Keep ReLiK only for entity-linking to CELEX ids.
* **LlamaIndex ``SchemaLLMPathExtractor``** — schema-constrained LLM second pass; use a
  model with native JSON-Schema decoding so relations cannot be invented.

The design split that keeps this testable: an extractor (model-dependent, lazy) produces
plain :class:`DeonticExtraction` records; :func:`apply_deontic_extractions` merges those
into the graph deterministically (no models, fully unit-tested).

API source: HF model card for knowledgator/gliner-relex-large-v0.5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .model import KnowledgeGraph
from .schema import ACTOR_VOCAB, EdgeType, NodeType

__all__ = [
    "EnrichmentConfig",
    "DeonticExtraction",
    "GlinerRelexExtractor",
    "apply_deontic_extractions",
    "extract_deontic",
    "enrich_graph",
]

_DEONTIC_TYPES = {"obligation", "prohibition", "permission", "right"}

# Actor labels sent to the model: the ACTOR_VOCAB keys plus common surface aliases that
# GLiNER-Relex may predict verbatim (e.g. "provider" → "provider" key).
# NOTE [unverified]: whether these zero-shot labels reliably recall real Act actors depends
# on a live GPU run with downloaded weights; this label set is a design choice, not
# empirically validated.
_DEFAULT_ACTOR_LABELS: tuple[str, ...] = tuple(ACTOR_VOCAB.keys()) + (
    "market surveillance authority",
    "national competent authority",
    "conformity assessment body",
)

# Relation labels sent to the model — aligned with GLiNER-Relex v0.5 generic relation
# vocabulary as described in the model card.  Names are design choices; actual model
# performance against these labels is [unverified] without a live run.
_DEFAULT_RELATION_LABELS: tuple[str, ...] = (
    "has_bearer",
    "has_condition",
    "has_consequence",
)


@dataclass
class EnrichmentConfig:
    """Which models to use. Defaults track the verified 2026 SOTA."""

    ner_re_model: str = "knowledgator/gliner-relex-large-v0.5"
    entity_link_model: str = "sapienzanlp/relik-entity-linking-large"
    llm_tier: str = "opus"  # KG extraction is correctness-compounding -> Opus tier (plan §10)
    actor_labels: tuple[str, ...] = tuple(ACTOR_VOCAB)
    deontic_labels: tuple[str, ...] = tuple(sorted(_DEONTIC_TYPES))
    # --- GLiNER-Relex API thresholds (source: HF model card) ---
    relation_labels: tuple[str, ...] = _DEFAULT_RELATION_LABELS
    threshold: float = 0.3
    adjacency_threshold: float = 0.5
    relation_threshold: float = 0.8


@dataclass
class DeonticExtraction:
    """One normative statement extracted from a provision (the extractor's output unit)."""

    provision_id: str
    deontic_type: str  # obligation | prohibition | permission | right
    bearer: str | None = None  # an ACTOR_VOCAB key, e.g. "provider"
    condition_text: str | None = None
    consequence_text: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.deontic_type not in _DEONTIC_TYPES:
            raise ValueError(f"deontic_type must be one of {_DEONTIC_TYPES}, got {self.deontic_type!r}")


def _normalize_actor(text: str) -> str | None:
    """Map a raw entity text to an ACTOR_VOCAB key (case-insensitive substring match).

    Returns an ACTOR_VOCAB key if the text matches any key or the vocab label, else None.
    Design choice: exact key match > label match > None (no fuzzy match to avoid false
    positive bearer assignments).
    """
    lowered = text.lower().strip()
    # Exact key match first
    if lowered in ACTOR_VOCAB:
        return lowered
    # Match against vocab labels (e.g. "Provider" → "provider")
    for key, meta in ACTOR_VOCAB.items():
        if meta.get("label", "").lower() == lowered:
            return key
    # Substring match on key (e.g. "authorised representative" matches "authorised_representative")
    normalised_underscored = lowered.replace(" ", "_").replace("-", "_")
    if normalised_underscored in ACTOR_VOCAB:
        return normalised_underscored
    return None


def _normalize_batch(result: Any) -> tuple[list[dict], list[dict]]:
    """Handle the GLiNER-Relex batch-dimension ambiguity.

    The model card is unambiguous that inference() with texts=[single_text] returns
    (entities, relations), but whether those are nested lists (batch dim) or flat lists
    is [unverified].  We handle both defensively: if the first element of entities is
    itself a list, assume batch-wrapped and unwrap index [0].

    Args:
        result: The (entities, relations) tuple from model.inference().

    Returns:
        A (entities, relations) pair of flat lists of dicts.
    """
    entities_raw, relations_raw = result
    # Detect batch-wrapped output: if entities_raw is a list whose first item is a list
    if entities_raw and isinstance(entities_raw[0], list):
        entities: list[dict] = entities_raw[0]
    else:
        entities = list(entities_raw)
    if relations_raw and isinstance(relations_raw[0], list):
        relations: list[dict] = relations_raw[0]
    else:
        relations = list(relations_raw)
    return entities, relations


class GlinerRelexExtractor:
    """Wraps GLiNER-Relex v0.5 with an injectable model for offline testing.

    Usage (production — requires ``uv sync --extra enrich`` and downloaded weights)::

        extractor = GlinerRelexExtractor()
        extractions = extractor.extract(provisions)

    Usage (tests / CI — inject a stub)::

        extractor = GlinerRelexExtractor(model=stub_model)
        extractions = extractor.extract(provisions)

    The model is loaded lazily on first access via the ``model`` property.  This means
    ``import gliner`` is never executed in the deterministic pipeline (no ML deps needed
    for the graph backbone or unit tests).
    """

    def __init__(
        self,
        config: EnrichmentConfig | None = None,
        model: Any = None,
    ) -> None:
        self._config = config or EnrichmentConfig()
        self._model = model  # None means "lazy load on first access"

    @property
    def model(self) -> Any:
        """Return the injected model, or lazily load GLiNER from the optional extra."""
        if self._model is not None:
            return self._model
        try:
            from gliner import GLiNER  # type: ignore  # noqa: PLC0415
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "deontic extraction needs the ML stack. Install with `uv sync --extra enrich` "
                "(GLiNER-Relex + transformers), or supply pre-computed DeonticExtraction records "
                "to apply_deontic_extractions() / enrich_graph(extractions=...)."
            ) from e
        self._model = GLiNER.from_pretrained(self._config.ner_re_model)
        return self._model

    def extract(self, provisions: list) -> list[DeonticExtraction]:
        """Run GLiNER-Relex on each provision and map outputs to DeonticExtraction records.

        Mapping design (annotated as design choices, not empirically validated against
        real model output — [unverified] without a live GPU run):

        * For each entity whose ``label`` is in {obligation, prohibition, permission, right},
          create one :class:`DeonticExtraction`.
        * Walk ``relations`` whose ``head["entity_idx"]`` points at that deontic entity:
          - ``has_bearer`` + tail label in actor set → set ``bearer`` via :func:`_normalize_actor`
          - ``has_condition`` → set ``condition_text = tail["text"]``
          - ``has_consequence`` → set ``consequence_text = tail["text"]``
        * One DeonticExtraction per deontic entity (no duplicates).

        Args:
            provisions: Iterable of Provision objects (must have .provision_id and .text).

        Returns:
            List of :class:`DeonticExtraction` records ready for :func:`apply_deontic_extractions`.
        """
        cfg = self._config
        entity_labels = list(cfg.deontic_labels) + list(cfg.actor_labels)
        results: list[DeonticExtraction] = []
        # Probe model upfront so the missing-dep RuntimeError fires even for empty
        # provision lists — preserves the contract of the original extract_deontic stub.
        model = self.model

        for prov in provisions:
            raw = model.inference(
                texts=[prov.text],
                labels=entity_labels,
                relations=list(cfg.relation_labels),
                threshold=cfg.threshold,
                adjacency_threshold=cfg.adjacency_threshold,
                relation_threshold=cfg.relation_threshold,
                return_relations=True,
                flat_ner=False,
            )
            entities, relations = _normalize_batch(raw)

            # Build entity-index → entity dict for relation resolution
            idx_to_entity: dict[int, dict] = {i: e for i, e in enumerate(entities)}

            # Collect deontic entities first
            deontic_entities: list[tuple[int, dict]] = [
                (i, e) for i, e in enumerate(entities)
                if e.get("label") in _DEONTIC_TYPES
            ]

            for ent_idx, deontic_ent in deontic_entities:
                extraction = DeonticExtraction(
                    provision_id=prov.provision_id,
                    deontic_type=deontic_ent["label"],
                    confidence=deontic_ent.get("score"),
                )

                # Walk relations whose head points to this deontic entity
                for rel in relations:
                    head = rel.get("head", {})
                    tail = rel.get("tail", {})
                    if head.get("entity_idx") != ent_idx:
                        continue
                    relation_type = rel.get("relation", "")
                    tail_text = tail.get("text", "")

                    if relation_type == "has_bearer":
                        # Try the entity label (tail["type"]) first — that's what GLiNER
                        # predicts and is more reliable than the surface text.  Then fall
                        # back to the surface text (for models that surface-normalise actors).
                        tail_label = tail.get("type", "")
                        tail_entity = idx_to_entity.get(tail.get("entity_idx", -1), {})
                        tail_entity_label = tail_entity.get("label", "")
                        actor_key = (
                            _normalize_actor(tail_label)
                            or _normalize_actor(tail_entity_label)
                            or _normalize_actor(tail_text)
                        )
                        if actor_key is not None:
                            extraction.bearer = actor_key

                    elif relation_type == "has_condition":
                        extraction.condition_text = tail_text or None

                    elif relation_type == "has_consequence":
                        extraction.consequence_text = tail_text or None

                results.append(extraction)

        return results


def apply_deontic_extractions(
    graph: KnowledgeGraph, extractions: list[DeonticExtraction]
) -> KnowledgeGraph:
    """Merge extracted normative statements into ``graph`` deterministically.

    Adds ``DeonticStatement`` nodes wired ``Actor —BEARER_OF→ DeonticStatement —GROUNDED_IN→
    Provision``, plus typed ``Condition`` / ``Sanction`` nodes — the exact path the
    compliance query "what must a Provider do?" walks. Model-free and unit-tested.
    """
    per_provision: dict[str, int] = {}
    for ext in extractions:
        idx = per_provision.get(ext.provision_id, 0)
        per_provision[ext.provision_id] = idx + 1
        ds_id = f"deontic_{ext.provision_id}_{idx}"

        props = {"deontic_type": ext.deontic_type}
        if ext.confidence is not None:
            props["confidence"] = ext.confidence
        graph.add_node(
            ds_id,
            NodeType.DEONTIC_STATEMENT,
            label=f"{ext.deontic_type} @ {ext.provision_id}",
            props=props,
        )
        graph.add_edge(EdgeType.GROUNDED_IN, ds_id, ext.provision_id)

        if ext.bearer:
            actor_id = f"actor_{ext.bearer}"
            if graph.get_node(actor_id) is None:
                label = ACTOR_VOCAB.get(ext.bearer, {}).get("label", ext.bearer.title())
                graph.add_node(actor_id, NodeType.ACTOR, label=label, props={"key": ext.bearer})
            graph.add_edge(EdgeType.BEARER_OF, actor_id, ds_id)

        if ext.condition_text:
            cond_id = f"cond_{ds_id}"
            graph.add_node(cond_id, NodeType.CONDITION, label=ext.condition_text[:80], props={"text": ext.condition_text})
            graph.add_edge(EdgeType.HAS_CONDITION, ds_id, cond_id)

        if ext.consequence_text:
            sanc_id = f"sanction_{ds_id}"
            graph.add_node(sanc_id, NodeType.SANCTION, label=ext.consequence_text[:80], props={"text": ext.consequence_text})
            graph.add_edge(EdgeType.HAS_CONSEQUENCE, ds_id, sanc_id)

    return graph


def extract_deontic(
    provisions,
    config: EnrichmentConfig | None = None,
    *,
    extractor: GlinerRelexExtractor | None = None,
) -> list[DeonticExtraction]:
    """Run the GLiNER-Relex + schema-constrained LLM cascade. Lazily imports heavy deps.

    Args:
        provisions: Iterable of Provision objects.
        config: Optional :class:`EnrichmentConfig`. Ignored when ``extractor`` is given.
        extractor: Optional pre-built :class:`GlinerRelexExtractor` (for DI / testing).
            If None, a new extractor is constructed from ``config``.

    Raises a clear RuntimeError if the optional ``enrich`` extra is not installed and no
    ``extractor`` is injected, so the deterministic pipeline never hard-depends on the ML
    stack (mirrors the Phase-1 loader).
    """
    if extractor is not None:
        return extractor.extract(list(provisions))
    # Construct a fresh extractor — the lazy .model property handles the import gate
    return GlinerRelexExtractor(config).extract(list(provisions))


def enrich_graph(
    graph: KnowledgeGraph,
    provisions=None,
    *,
    config: EnrichmentConfig | None = None,
    extractions: list[DeonticExtraction] | None = None,
) -> KnowledgeGraph:
    """Add the deontic layer to ``graph``. Uses ``extractions`` if given, else runs the cascade."""
    if extractions is None:
        extractions = extract_deontic(provisions or [], config)
    return apply_deontic_extractions(graph, extractions)
