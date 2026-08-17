import os
os.environ.setdefault("P2P_GRAPH_RAG_PROVIDER","cli")
os.environ.setdefault("REGENOLD_EXTERNAL_EMBEDDINGS","0")
os.environ.setdefault("OPENAI_API_BASE","http://127.0.0.1:1/v1")
from app.integrations.regenold.models import normalise_answer_for_regenold
from app.engines import graph_rag as g
qs = [
 "Is an AI system for robotic surgery high-risk under the EU AI Act?",
 "Under Article 50, how should users be informed when interacting with an AI system?",
]
for q in qs:
    print("="*20, q)
    print("curated?", g._is_curated_authoritative_intercept(q))
    import inspect
    sig = inspect.signature(g._deterministic_answer)
    print("sig", sig)
