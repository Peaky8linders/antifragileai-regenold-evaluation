"""Phase-4 grounded generation + citation-verification layer.

Two pieces:

1. ``CitationGuard`` -- fully deterministic, offline.  Every emitted citation
   must (a) resolve to a real graph node and (b) lie within the retrieved
   candidate set.  This structurally zeroes fabricated-citation hallucinations
   without any LLM involvement.

2. ``CitedGenerationBaseline`` -- cite-as-you-generate over a candidate set
   produced by a ``Retriever``.  The deterministic guard/retrieval parts are
   unit-testable offline; generation is API-gated (mirrors ``llm.py``'s honesty
   gate).
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

from ..graph.model import KnowledgeGraph
from ..graph.schema import EdgeType
from ..ids import ProvisionId, ProvisionIdError
from ..models import Provision
from .base import Baseline, question_text
from .retrieval import Retriever

__all__ = ["CitationGuard", "CitedGenerationBaseline"]

# Reuse the same model id as llm.py (correctness-compounding tier).
DEFAULT_MODEL = "claude-opus-4-8"

# System instructions for cite-as-you-generate.
_SYSTEM = (
    "You are a legal analyst answering questions strictly about the EU AI Act "
    "(Regulation (EU) 2024/1689).\n"
    "You will be given a set of candidate provisions.  Cite ONLY from those "
    "candidates -- do not invent citations that are not in the list.  If none "
    "applies, cite nothing.\n"
    "Respond with a JSON object of exactly this form and nothing else:\n"
    '{"answer": "<your 2-4 sentence answer>", "citations": ["<eid1>", "<eid2>"]}\n'
    "Use the exact eid strings from the candidate list, not human-form citations."
)


# ---------------------------------------------------------------------------
# 1. Deterministic structural guard
# ---------------------------------------------------------------------------


class CitationGuard:
    """Offline, deterministic gate: a citation is a join key, not a string.

    Canonicalises every citation to its eid via ``ProvisionId.parse`` before
    checking the graph, so both human-form ("Art. 6(2)") and raw eids
    ("art_6__para_2") work uniformly.
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        self._graph = graph

    # -- low-level ----------------------------------------------------------

    def _to_eid(self, citation: str) -> str | None:
        """Return the canonical eid, or None if unparseable."""
        try:
            return ProvisionId.parse(citation).eid
        except (ProvisionIdError, Exception):
            return None

    # -- public API ---------------------------------------------------------

    def is_real_node(self, citation: str) -> bool:
        """True iff *citation* (eid or human form) resolves to an existing graph node."""
        eid = self._to_eid(citation)
        if eid is None:
            return False
        return self._graph.get_node(eid) is not None

    def filter(self, citations: list[str], candidates: set[str]) -> list[str]:
        """Keep only citations that are real nodes AND in *candidates*.

        Preserves original order.  Both the emitted citation and each candidate
        string are canonicalised to eids before comparison so mixed forms work.
        """
        # Canonicalise the candidate set once.
        canon_candidates: set[str] = set()
        for c in candidates:
            eid = self._to_eid(c)
            if eid is not None:
                canon_candidates.add(eid)

        out: list[str] = []
        for cit in citations:
            eid = self._to_eid(cit)
            if eid is None:
                continue
            if self._graph.get_node(eid) is None:
                continue
            if eid not in canon_candidates:
                continue
            out.append(cit)
        return out

    # -- coherence ----------------------------------------------------------

    def _ancestors_of(self, eid: str) -> set[str]:
        """All ancestor eids (by HAS_CHILD parentage) via ProvisionId.ancestors."""
        try:
            pid = ProvisionId.parse(eid)
        except (ProvisionIdError, Exception):
            return set()
        return {a.eid for a in pid.ancestors()}

    def _cross_ref_neighbours(self, eid: str) -> set[str]:
        """Eids connected by a CROSS_REFERENCES_INTERNAL edge (either direction)."""
        g = self._graph
        out: set[str] = set()
        for edge in g.out_edges(eid, EdgeType.CROSS_REFERENCES_INTERNAL):
            out.add(edge.target)
        for edge in g.in_edges(eid, EdgeType.CROSS_REFERENCES_INTERNAL):
            out.add(edge.source)
        return out

    def coherence(self, citations: list[str]) -> float:
        """Fraction of cited nodes in the largest connected component.

        Two cited nodes are linked iff one is an ancestor/descendant of the
        other (structural containment via HAS_CHILD) OR they share a
        CROSS_REFERENCES_INTERNAL edge.  Returns 1.0 for 0 or 1 citation.
        """
        # Canonicalise and deduplicate, keeping first-seen order.
        eids: list[str] = []
        seen: set[str] = set()
        for cit in citations:
            eid = self._to_eid(cit)
            if eid and eid not in seen:
                eids.append(eid)
                seen.add(eid)

        n = len(eids)
        if n <= 1:
            return 1.0

        # Build adjacency: two nodes are linked when they are ancestor/descendant
        # relatives OR share a cross-reference edge.
        ancestor_map: dict[str, set[str]] = {e: self._ancestors_of(e) for e in eids}
        xref_map: dict[str, set[str]] = {e: self._cross_ref_neighbours(e) for e in eids}

        eid_set = set(eids)
        adj: dict[str, set[str]] = defaultdict(set)
        for i, a in enumerate(eids):
            for b in eids[i + 1 :]:
                linked = (
                    b in ancestor_map[a]
                    or a in ancestor_map[b]
                    or b in xref_map[a]
                    or a in xref_map[b]
                )
                if linked:
                    adj[a].add(b)
                    adj[b].add(a)

        # Union-Find to find connected components.
        parent: dict[str, str] = {e: e for e in eids}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            parent[find(x)] = find(y)

        for a, neighbours in adj.items():
            for b in neighbours:
                union(a, b)

        component_sizes: dict[str, int] = defaultdict(int)
        for e in eids:
            component_sizes[find(e)] += 1

        largest = max(component_sizes.values())
        return largest / n

    def incoherent(self, citations: list[str]) -> list[str]:
        """Return the cited eids NOT in the largest connected component.

        Uses the same connectivity definition as :meth:`coherence`.  Returns
        canonical eids (not the original citation strings).
        """
        eids: list[str] = []
        seen: set[str] = set()
        for cit in citations:
            eid = self._to_eid(cit)
            if eid and eid not in seen:
                eids.append(eid)
                seen.add(eid)

        n = len(eids)
        if n <= 1:
            return []

        ancestor_map: dict[str, set[str]] = {e: self._ancestors_of(e) for e in eids}
        xref_map: dict[str, set[str]] = {e: self._cross_ref_neighbours(e) for e in eids}

        adj: dict[str, set[str]] = defaultdict(set)
        for i, a in enumerate(eids):
            for b in eids[i + 1 :]:
                linked = (
                    b in ancestor_map[a]
                    or a in ancestor_map[b]
                    or b in xref_map[a]
                    or a in xref_map[b]
                )
                if linked:
                    adj[a].add(b)
                    adj[b].add(a)

        parent: dict[str, str] = {e: e for e in eids}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            parent[find(x)] = find(y)

        for a, neighbours in adj.items():
            for b in neighbours:
                union(a, b)

        component_sizes: dict[str, int] = defaultdict(int)
        for e in eids:
            component_sizes[find(e)] += 1

        largest_root = max(component_sizes, key=lambda r: component_sizes[r])
        return [e for e in eids if find(e) != largest_root]


# ---------------------------------------------------------------------------
# 2. Cite-as-you-generate baseline
# ---------------------------------------------------------------------------


class CitedGenerationBaseline(Baseline):
    """Phase-4 grounded generation baseline.

    The guard makes fabricated citations structurally impossible: only citations
    that resolve to a real graph node AND appear in the retrieved candidate set
    survive.  Generation is the sole API-gated part -- the guard and retrieval
    run fully offline.

    Constructor raises ``RuntimeError`` when no ``client`` is injected and
    ``ANTHROPIC_API_KEY`` is absent (mirrors ``llm.py``'s honesty gate).
    """

    name = "cited-generation"

    def __init__(
        self,
        provisions: list[Provision],
        graph: KnowledgeGraph,
        retriever: Retriever,
        k: int = 10,
        model: str | None = None,
        max_tokens: int = 1024,
        client: Any = None,
    ) -> None:
        if client is None:
            client = self._make_client()
        self.client = client
        self.model = model or DEFAULT_MODEL
        self.max_tokens = max_tokens
        self.k = k
        self._retriever = retriever
        self._guard = CitationGuard(graph)
        # Build a provision_id -> Provision lookup once.
        self._provisions: dict[str, Provision] = {p.provision_id: p for p in provisions}
        self.name = f"cited-generation:{self.model}"

    @staticmethod
    def _make_client() -> Any:
        """Construct a real Anthropic client, or raise a clear error.  Never
        silently degrades.  Mirrors the gate in ``llm.py`` exactly."""
        try:
            import anthropic
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "the cited-generation baseline needs the `anthropic` package -- "
                "install it with `uv sync --extra baselines` (or inject a client)."
            ) from e
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "the cited-generation baseline needs ANTHROPIC_API_KEY in the "
                "environment (or inject a client)."
            )
        return anthropic.Anthropic()

    def _build_user_message(self, query: str, candidate_ids: list[str]) -> str:
        """Render the cite-as-you-generate prompt.

        Candidates are listed with their eid and text so the model can cite
        only from them.  The JSON output constraint makes parsing exact.
        """
        lines: list[str] = [
            "Answer the following question using ONLY the provisions listed below.",
            "Return a JSON object with keys 'answer' (string) and 'citations' "
            "(list of eid strings from the candidates).  Do not cite anything "
            "not in this list.",
            "",
            "Candidate provisions:",
        ]
        for pid in candidate_ids:
            prov = self._provisions.get(pid)
            text_snippet = prov.text[:200] if prov else ""
            lines.append(f"  [{pid}] {text_snippet}")
        lines += ["", f"Question: {query}"]
        return "\n".join(lines)

    def predict(self, item: dict) -> list[str]:
        """Retrieve candidates, generate with citation constraint, guard output.

        Steps:
        1. Retrieve top-k candidate provision_ids.
        2. Build a cite-as-you-generate prompt with those candidates.
        3. Call the LLM at temperature 0 requesting strict JSON.
        4. Parse the emitted citations.
        5. Run ``guard.filter`` -- anything not a real node or not in the
           candidate set is dropped.  Returns the surviving list (empty = abstain).
        """
        query = question_text(item)
        candidate_ids = self._retriever.search(query, self.k)
        candidate_set: set[str] = set(candidate_ids)

        if not candidate_ids:
            return []

        user_msg = self._build_user_message(query, candidate_ids)

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )

        # Extract text from the response (duck-typed like llm.py).
        raw = "\n".join(
            b.text for b in resp.content if getattr(b, "type", None) == "text"
        ).strip()

        # Parse the strict JSON the prompt demands.
        emitted: list[str] = []
        try:
            # Strip markdown code-fence if the model wraps it.
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            emitted = [str(c) for c in data.get("citations", [])]
        except (json.JSONDecodeError, AttributeError, TypeError):
            # Malformed JSON: no citations survive -- structurally safe.
            emitted = []

        return self._guard.filter(emitted, candidate_set)
