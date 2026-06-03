import httpx
import json

URL = "https://regenold-eu-ai-act-rag-production.up.railway.app/api/v1/regenold/eu-ai-act/ask"

def ask(q):
    print(f"Q: {q}")
    try:
        resp = httpx.post(URL, json={"messages": [{"role": "user", "content": q}]}, timeout=120)
        if resp.status_code == 200:
            print("A:", resp.json()["answer"])
            print("Refs:", resp.json().get("references", []))
        else:
            print(f"Error {resp.status_code}:", resp.text)
    except Exception as e:
        print("Exception:", e)
    print("-" * 40)

ask("When do high-risk AI obligations apply...?")
ask("What is a GPAI model...?")
