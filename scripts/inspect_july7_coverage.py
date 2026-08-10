"""Inspect the July 7 batch of questions for complete vector, embedding, knowledge graph, ontology, and semantic layer coverage.

Performs a step-by-step audit:
1. Questions & Gold References Inventory in July 7 Batch.
2. Vector Index Coverage (Article, Annex, Paragraph, Point, SubPoint, Definition, Recital).
3. Knowledge Graph & Ontology Coverage (Cypher patterns, relations, node labels).
4. Semantic Layer & Extractor Coverage (Entity extractions, intent classification, BM25 + Vector fusion).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["NEO4J_AUTO_SEED"] = "0"
os.environ["REGENOLD_GRAPH_VECTOR_RECALL"] = "1"

from app.data import article_existence  # noqa: E402
from app.data.kb_search import top_articles_by_relevance  # noqa: E402
from app.engines import (  # noqa: E402
    embeddings_index,
    kg_context,
    semantic_layer,
    turboquant_index,
    vector_recall,
)


def run_inspection() -> int:
    failures: list[str] = []
    batch_file = Path("evals/regenold/_official_batch_20260707.json")
    if not batch_file.exists():
        batch_file = Path("evals/bench/results/official-r318-july7-easy-easy.ckpt.jsonl")
    if not batch_file.exists():
        print("FAILED: neither July 7 batch input exists", file=sys.stderr)
        return 2

    print("=" * 80)
    print("STEP-BY-STEP INSPECTION: JULY 7 BATCH COVERAGE AUDIT")
    print("=" * 80)

    # ----------------------------------------------------
    # STEP 1: Load Questions & Analyze Target Provisions
    # ----------------------------------------------------
    rows = []
    if batch_file.name.endswith(".json"):
        with open(batch_file, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = data.get("questions") or data.get("rows") or []
    else:
        with open(batch_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))

    print(f"\n[Step 1] Analyzed {len(rows)} questions from July 7 batch ({batch_file.name}).")
    if not rows:
        failures.append("July 7 input parsed to zero rows")

    all_articles_targeted = set()
    all_annexes_targeted = set()
    category_counts = {}

    for r in rows:
        cat = r.get("category") or r.get("difficulty_category") or "general"
        category_counts[cat] = category_counts.get(cat, 0) + 1

        refs = (
            r.get("pred_refs")
            or r.get("expected_references")
            or r.get("jul07_refs")
            or []
        )
        for ref in refs:
            ref_str = str(ref).strip()
            if ref_str.startswith("Article") or ref_str.startswith("Art"):
                all_articles_targeted.add(ref_str)
            elif ref_str.startswith("Annex"):
                all_annexes_targeted.add(ref_str)

    print(f"  Categories represented: {dict(sorted(category_counts.items()))}")
    print(f"  Target Articles identified: {len(all_articles_targeted)} unique articles")
    print(f"  Target Annexes identified: {len(all_annexes_targeted)} unique annexes: {sorted(all_annexes_targeted)}")

    # ----------------------------------------------------
    # STEP 2: Vector & Embedding Coverage Audit
    # ----------------------------------------------------
    print("\n[Step 2] Vector & Embedding Layer Audit")
    emb_ok = embeddings_index.is_available()
    print(f"  - Local TF-IDF+SVD 128-d sentence embedding index available: {emb_ok}")
    if not emb_ok:
        failures.append("local sentence embedding assets unavailable")

    manifest_file = Path("app/engines/_assets/embeddings_manifest.json")
    if manifest_file.exists():
        with open(manifest_file, encoding="utf-8") as f:
            m_data = json.load(f)
            print(f"  - Embedding Index Metadata: SVD dim={m_data.get('vector_dim')}, sents={m_data.get('total_sentences')}, vocab={m_data.get('vocab_size')}")
            if not m_data.get("vector_dim") or not m_data.get("total_sentences"):
                failures.append("embedding manifest has zero/missing dimensions or sentences")
    else:
        failures.append("embedding manifest missing")

    tq_diag = turboquant_index.index_diagnostics()
    print(f"  - TurboQuant index diagnostics: {tq_diag}")
    if not tq_diag.get("loaded") or not tq_diag.get("num_docs"):
        failures.append("TurboQuant/precomputed dense index did not load")
    if not tq_diag.get("compression_active"):
        failures.append("TurboQuant 4-bit compression is inactive")

    # Test query embedding on sample July 7 questions
    sample_qs = [
        "What are all the prohibited AI practices under Article 5?",
        "Which AI systems fall under high-risk Annex III category 4 employment?",
        "What are the obligations for deployers of high-risk AI under Article 26?",
        "How are general purpose AI models with systemic risk classified under Annex XIII?"
    ]

    print("\n  Sample Embedding Vector Retrieval Test:")
    native_hit_count = 0
    fallback_hit_count = 0
    for q in sample_qs:
        vec = embeddings_index._embed_query(q)
        v_hits = (
            vector_recall.recall_articles_with_provenance(q, top_k=3)
            if emb_ok else []
        )
        native_hit_count += sum(h.source.startswith("neo4j:") for h in v_hits)
        fallback_hit_count += sum(h.source.startswith("local:") for h in v_hits)
        print(
            f"    Q: '{q[:60]}...' -> Vec dim: "
            f"{len(vec) if vec is not None else 'None'} | Vector hits: "
            f"{[(h.ref, round(h.score, 3), h.source) for h in v_hits]}"
        )
    if not native_hit_count:
        failures.append("native Neo4j vector indexes produced no valid sample hit")
    if not native_hit_count and not fallback_hit_count:
        failures.append("neither native nor local vector recall produced a sample hit")

    # ----------------------------------------------------
    # STEP 3: Knowledge Graph & Ontology Schema Audit
    # ----------------------------------------------------
    print("\n[Step 3] Knowledge Graph & Ontology Schema Audit")
    from app.graph import schema as graph_schema
    all_node_labels = [
        getattr(graph_schema, attr) for attr in dir(graph_schema)
        if attr.startswith("NODE_") and isinstance(getattr(graph_schema, attr), str)
    ]
    all_rel_types = [
        getattr(graph_schema, attr) for attr in dir(graph_schema)
        if attr.startswith("REL_") and isinstance(getattr(graph_schema, attr), str)
    ]
    print(f"  - Ontology Node Labels ({len(all_node_labels)}): {sorted(all_node_labels)}")
    print(f"  - Ontology Relations ({len(all_rel_types)}): {sorted(all_rel_types)}")
    required_labels = {"Practice", "OperatorRole", "AnnexIIICategory", "LifecyclePhase", "SubPoint"}
    if not required_labels.issubset(set(all_node_labels)):
        failures.append(
            "schema is missing R326 labels: "
            + ", ".join(sorted(required_labels - set(all_node_labels)))
        )

    from app.graph.client import get_graph_client
    graph_client = get_graph_client()
    if not getattr(graph_client, "enabled", False):
        failures.append("Neo4j Aura client is disabled")
    else:
        try:
            index_rows = graph_client.execute_read_strict(
                "SHOW INDEXES YIELD name, type, state "
                "WHERE name IN $names RETURN name, type, state",
                {"names": [
                    "v_article_embedding",
                    "v_annex_embedding",
                    "ft_provision_prose",
                ]},
            )
            online = {
                str(row.get("name")) for row in index_rows
                if str(row.get("state", "")).upper() == "ONLINE"
            }
            print(f"  - Online required native indexes: {sorted(online)}")
            missing_indexes = {
                "v_article_embedding",
                "v_annex_embedding",
                "ft_provision_prose",
            } - online
            if missing_indexes:
                failures.append(
                    "required native vector/full-text indexes absent/offline: "
                    + ", ".join(sorted(missing_indexes))
                )

            metadata = graph_client.execute_read_strict(
                "MATCH (m:KBMetadata) "
                "RETURN m.seed_version AS seed_version, "
                "m.kb_version AS kb_version LIMIT 1"
            )
            if not metadata or not metadata[0].get("seed_version"):
                failures.append("Aura KBMetadata has no seed version")
            else:
                print(f"  - Aura KB metadata: {metadata[0]}")

            label_counts = graph_client.execute_read_strict(
                "MATCH (n) UNWIND labels(n) AS label "
                "WITH label, count(n) AS count WHERE label IN $labels "
                "RETURN label, count",
                {"labels": sorted(required_labels)},
            )
            counts = {str(row.get("label")): int(row.get("count") or 0) for row in label_counts}
            missing_data = {label for label in required_labels if counts.get(label, 0) <= 0}
            print(f"  - Aura R326 label counts: {counts}")
            if missing_data:
                failures.append(
                    "Aura has no nodes for R326 labels: "
                    + ", ".join(sorted(missing_data))
                )
        except Exception as exc:
            failures.append(f"Aura index audit failed closed: {exc}")

    # Audit kg_context Cypher shapes against target provisions
    sample_refs = ["Article 5", "Article 6", "Article 26", "Annex III", "Annex I"]
    rendered_kg = kg_context.render_kg_context(sample_refs)
    print(f"  - Rendered KG Context Parts for {sample_refs}: {len(rendered_kg)} blocks rendered")
    rendered_text = "\n".join(rendered_kg)
    if "KNOWLEDGE-GRAPH PROVISION STRUCTURE" not in rendered_text:
        failures.append("Aura hierarchy returned no rendered provision structure")
    annex_rows = kg_context.fetch_deontic_context(["Annex III"])
    if not any(any(row.get("annex_iii") or []) for row in annex_rows):
        failures.append("direct Annex III category path returned no categories")

    # ----------------------------------------------------
    # STEP 4: Semantic Layer & Hybrid Retrieval Audit
    # ----------------------------------------------------
    print("\n[Step 4] Semantic Layer & Entity Extractor Audit")
    valid_count = len(article_existence.ARTICLE_EXISTENCE)
    print(f"  - Article Existence Corpus size: {valid_count} provisions")
    if valid_count != 126:
        failures.append(f"official provision catalog size changed unexpectedly: {valid_count}")
    semantic_probe = semantic_layer.cross_reference_context(["Art. 16"])
    print(f"  - Semantic cross-reference probe items: {len(semantic_probe)}")
    if not semantic_layer.is_cross_ref_context_enabled() or not semantic_probe:
        failures.append("semantic cross-reference layer produced no Article 16 context")

    # Test top_articles_by_relevance hybrid retrieval on July 7 sample questions
    print("\n  Hybrid BM25 + Vector Retrieval Test on July 7 Questions:")
    for r in rows[:5]:
        q = r.get("question") or r.get("text") or ""
        bm25_hits = top_articles_by_relevance(q, k=3, min_score=1.0)
        vec_hits = vector_recall.recall_articles_with_provenance(q, top_k=3)
        print(
            f"    [{r.get('id', 'N/A')}] BM25: {bm25_hits} | Vector Hits: "
            f"{[(h.ref, h.source) for h in vec_hits]}"
        )

    print("\n" + "=" * 80)
    if failures:
        print("FULL COVERAGE AUDIT FAILED CLOSED")
        for failure in failures:
            print(f"  - FAIL: {failure}")
    else:
        print("FULL COVERAGE AUDIT COMPLETE: ALL CHECKED LAYERS OPERATING CLEANLY")
    print("=" * 80)
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(run_inspection())
