"""§8 baseline runner -- emit predictions for eu-ai-act-benchmark/scorer.py.

    # naive lexical retrieval (runs anywhere, no API):
    uv run euaiact-baseline ../eu-ai-act-benchmark/eu_ai_act_bench_easy.json \
        --baseline retrieval --k 5 --out data/preds_easy_retrieval.json

    # graph-expansion retrieval (uses the Phase-2 KG; runs anywhere, no API):
    uv run euaiact-baseline ../eu-ai-act-benchmark/eu_ai_act_bench_easy.json \
        --baseline graphrag --graph data/graph.json --k 5 --out data/preds_easy_graphrag.json

    # frontier LLM with the full Act in context (needs the `baselines` extra +
    # ANTHROPIC_API_KEY; see llm.py):
    uv run euaiact-baseline ../eu-ai-act-benchmark/eu_ai_act_bench_hard.json \
        --baseline llm --full-act --out data/preds_hard_llm.json

Then score:  python3 ../eu-ai-act-benchmark/scorer.py <benchmark> --predictions <out>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..models import Provision
from .base import run_baseline, write_predictions
from .naive_rag import NaiveRetrievalBaseline
from .retrieval import TfidfRetriever


def _load_items(path: Path) -> list[dict]:
    return json.loads(path.read_text())["items"]


def _load_provisions(path: Path) -> list[Provision]:
    if not path.exists():
        raise SystemExit(
            f"error: provision corpus not found at {path}. Run `euaiact-ingest` first "
            f"(Phase-1) or pass --provisions."
        )
    return [Provision.model_validate(r) for r in json.loads(path.read_text())]


def _load_graph(path: Path):
    if not path.exists():
        raise SystemExit(
            f"error: knowledge graph not found at {path}. Run `euaiact-graph` first "
            f"(Phase-2) or pass --graph."
        )
    from ..graph.model import KnowledgeGraph

    return KnowledgeGraph.from_dict(json.loads(path.read_text()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a §8 baseline and write scorer-ready predictions")
    ap.add_argument("benchmark", type=Path, help="benchmark JSON (eu_ai_act_bench_{easy,hard}.json)")
    ap.add_argument(
        "--baseline",
        choices=["retrieval", "lsa", "graphrag", "llm", "bm25", "dense", "cited-gen"],
        default="retrieval",
    )
    ap.add_argument("--out", type=Path, required=True, help="predictions JSON to write")
    ap.add_argument("--provisions", type=Path, default=Path("data/provisions.json"))
    ap.add_argument("--k", type=int, default=5, help="retrieval/lsa/graphrag: top-k provisions to cite")
    ap.add_argument("--seeder", choices=["tfidf", "lsa"], default="tfidf",
                    help="graphrag: seed retriever -- lexical TF-IDF or offline latent-semantic LSA")
    ap.add_argument("--lsa-components", type=int, default=200, help="lsa/seeder=lsa: truncated-SVD rank")
    ap.add_argument("--lsa-min-df", type=int, default=2, help="lsa/seeder=lsa: document-frequency floor for the vocabulary")
    ap.add_argument("--graph", type=Path, default=Path("data/graph.json"), help="graphrag: Phase-2 graph.json")
    ap.add_argument("--seed-k", type=int, default=10, help="graphrag: lexical seeds before graph expansion")
    ap.add_argument("--max-hops", type=int, default=1, help="graphrag: expansion hops from each seed")
    ap.add_argument("--min-seed-score", type=float, default=0.0,
                    help="graphrag: abstain (cite nothing) if the best seed cosine is below this")
    ap.add_argument("--model", default=None, help="llm: model id (default: tiering default, Opus)")
    ap.add_argument("--full-act", action="store_true", help="llm: put the provision corpus in context")
    ap.add_argument("--max-tokens", type=int, default=1024, help="llm: max output tokens")
    ap.add_argument("--verify", choices=["none", "lexical", "nli", "llm"], default="none",
                    help="CRAG post-retrieval verification: drop/abstain on (question,provision) "
                         "entailment. 'lexical' runs anywhere; 'nli' needs the `verify` extra; "
                         "'llm' needs the `baselines` extra + ANTHROPIC_API_KEY (LLM-as-NLI judge).")
    ap.add_argument("--verify-keep", type=float, default=0.0,
                    help="verify: drop a citation whose entailment support is below this")
    ap.add_argument("--verify-abstain", type=float, default=0.0,
                    help="verify: cite nothing if the best surviving support is below this")
    ap.add_argument("--nli-model", default=None, help="verify=nli: NLI cross-encoder id")
    ap.add_argument("--structural-abstain", type=float, default=0.0,
                    help="deterministic structural-cohesion gate (runs offline): abstain "
                         "(cite nothing) when the top --seed-k lexical seeds are too "
                         "scattered -- cohesion (largest article/cross-ref cluster / N) "
                         "below this [0,1] threshold. 0 = off (passthrough). Uses --graph.")
    args = ap.parse_args(argv)

    items = _load_items(args.benchmark)
    provisions = _load_provisions(args.provisions)

    if args.baseline == "retrieval":
        baseline = NaiveRetrievalBaseline(provisions, k=args.k)
    elif args.baseline == "lsa":
        from .lsa import LsaRetriever

        baseline = NaiveRetrievalBaseline(
            provisions,
            k=args.k,
            retriever=LsaRetriever(provisions, n_components=args.lsa_components, min_df=args.lsa_min_df),
        )
        baseline.name = f"naive-retrieval-lsa(k={args.lsa_components})"
    elif args.baseline == "graphrag":
        from .graph_rag import GraphRAGBaseline

        seeder = None
        if args.seeder == "lsa":
            from .lsa import LsaRetriever

            seeder = LsaRetriever(provisions, n_components=args.lsa_components, min_df=args.lsa_min_df)

        baseline = GraphRAGBaseline(
            provisions,
            _load_graph(args.graph),
            k=args.k,
            seed_k=args.seed_k,
            max_hops=args.max_hops,
            min_seed_score=args.min_seed_score,
            seeder=seeder,
            seeder_name=args.seeder,
        )
    elif args.baseline == "bm25":
        from .bm25 import Bm25Retriever

        baseline = NaiveRetrievalBaseline(provisions, k=args.k, retriever=Bm25Retriever(provisions))
        baseline.name = "naive-retrieval-bm25f"
    elif args.baseline == "dense":
        # The DenseRetriever needs an injected embedder (voyage-law-2 / Qwen3 / any
        # object with `.embed(texts) -> list[list[float]]`). No embedder client is
        # wired for CLI use here (no local torch; embedding APIs unreachable in this
        # environment), so fail clean rather than fabricate vectors.
        raise SystemExit(
            "error: --baseline dense needs an embeddings client, which is not wired "
            "for CLI use. Construct DenseRetriever(provisions, embedder=...) "
            "programmatically with a voyage-law-2 / Qwen3-Embedding / OpenAI-compatible "
            "shim, then pass it to NaiveRetrievalBaseline(retriever=...)."
        )
    elif args.baseline == "cited-gen":
        from .generate import CitedGenerationBaseline

        try:
            baseline = CitedGenerationBaseline(
                provisions,
                _load_graph(args.graph),
                TfidfRetriever(provisions),
                k=args.k,
                model=args.model,
                max_tokens=args.max_tokens,
            )
        except RuntimeError as e:  # missing package / API key -- fail clean, don't fabricate
            raise SystemExit(f"error: {e}")
    else:  # llm -- imported lazily so the anthropic dep is only needed on this path
        from .llm import FrontierLLMBaseline

        try:
            baseline = FrontierLLMBaseline(
                provisions=provisions if args.full_act else None,
                model=args.model,
                max_tokens=args.max_tokens,
            )
        except RuntimeError as e:  # missing package / API key -- fail clean, don't fabricate
            raise SystemExit(f"error: {e}")

    if args.verify != "none":
        if args.verify_keep <= 0.0 and args.verify_abstain <= 0.0:
            print(
                f"warning: --verify {args.verify} is a no-op with --verify-keep 0 and "
                f"--verify-abstain 0 -- nothing is dropped or abstained. Set "
                f"--verify-keep and/or --verify-abstain > 0 to actually gate citations.",
                file=sys.stderr,
            )
        from .verify import LexicalEntailmentScorer, VerifiedBaseline

        if args.verify == "lexical":
            scorer = LexicalEntailmentScorer(provisions)
        elif args.verify == "nli":  # lazy import so the ML deps are only needed on this path
            from .verify import NLIEntailmentScorer

            try:
                scorer = NLIEntailmentScorer(model_name=args.nli_model) if args.nli_model \
                    else NLIEntailmentScorer()
            except RuntimeError as e:  # missing package / model -- fail clean
                raise SystemExit(f"error: {e}")
        else:  # llm -- LLM-as-NLI judge; lazy import so anthropic is only needed here
            from .llm_entail import LLMEntailmentScorer

            try:
                scorer = LLMEntailmentScorer(model=args.model)
            except RuntimeError as e:  # missing package / API key -- fail clean
                raise SystemExit(f"error: {e}")

        baseline = VerifiedBaseline(
            baseline, scorer, provisions,
            keep=args.verify_keep, abstain=args.verify_abstain,
        )

    if args.structural_abstain > 0.0:
        from .structural_abstain import StructuralAbstentionBaseline

        baseline = StructuralAbstentionBaseline(
            baseline,
            provisions,
            _load_graph(args.graph),
            seed_n=args.seed_k,
            min_cohesion=args.structural_abstain,
        )

    preds = run_baseline(baseline, items)
    write_predictions(args.out, preds)

    n_cited = sum(1 for v in preds.values() if v)
    print(f"{baseline.name}: {len(preds)} predictions ({n_cited} non-empty) over {len(provisions)} provisions -> {args.out}", file=sys.stderr)
    print(f"score:  python3 {args.benchmark.parent}/scorer.py {args.benchmark} --predictions {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
