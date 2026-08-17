import os
os.environ["P2P_GRAPH_RAG_PROVIDER"]="cli"
os.environ["REGENOLD_EXTERNAL_EMBEDDINGS"]="0"
os.environ["OPENAI_API_BASE"]="http://127.0.0.1:1/v1"
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
qs = [
 "Is an AI system for robotic surgery high-risk under the EU AI Act?",
 "Under Article 50, how should users be informed when interacting with an AI system?",
]
for q in qs:
    r = c.post("/api/v1/regenold/eu-ai-act/ask", json={"messages":[{"role":"user","content":q}]})
    j = r.json()
    a = j.get("answer","")
    print("="*30, q)
    print("len", len(a))
    print(a)
    print("refs", j.get("references"))
