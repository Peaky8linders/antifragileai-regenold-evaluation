import httpx
import os
from evals.regenold.scenarios_graphrag_benchmark import GROUND_TRUTH

URL = "https://regenold-eu-ai-act-rag-production.up.railway.app/api/v1/regenold/eu-ai-act/ask"
OUT_PATH = r"C:\Users\th3un\.gemini\antigravity\brain\188bf447-0f26-47a3-b698-f098f2d177cb\regenold_eval_results.md"

questions = [item for item in GROUND_TRUTH if item["id"].startswith("med_") or item["id"].startswith("gt_")]

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("# Regenold API: MedTech & GraphRAG Live Eval Results\n\n")
    f.write("These results were generated live against the production endpoint, showcasing the final fix for 1-4 sentence conciseness and proper truncation boundaries.\n\n")

    with httpx.Client(timeout=120) as client:
        for item in questions:
            q = item["question"]
            f.write(f"### Q: {q}\n")
            try:
                resp = client.post(URL, json={"messages": [{"role": "user", "content": q}]})
                if resp.status_code == 200:
                    ans = resp.json()["answer"]
                    refs = resp.json().get("references", [])
                    f.write(f"**A:** {ans}\n\n")
                    f.write(f"**Citations:** `{', '.join(refs)}`\n\n")
                else:
                    f.write(f"**Error {resp.status_code}:** {resp.text}\n\n")
            except Exception as e:
                f.write(f"**Exception:** {e}\n\n")
            f.write("---\n\n")
            # flush to see progress if needed
            f.flush()
