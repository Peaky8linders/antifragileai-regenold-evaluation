import httpx
import json

URL = "https://regenold-eu-ai-act-rag-production.up.railway.app/api/v1/regenold/eu-ai-act/ask"
questions = [
    "We are developing a generative AI chatbot that will be deployed on a hospital website to answer general patient queries. What transparency obligations apply?",
    "A pharmaceutical company wants to use an AI system to monitor the emotions and stress levels of their manufacturing line workers to improve efficiency. Is this allowed?",
    "How should users be informed when interacting with AI systems?",
    "Can a hospital use an AI system to sort patients based on their biometric data to determine priority for an experimental clinical trial?"
]

for q in questions:
    print(f"### Q: {q}")
    try:
        # httpx.post inherently creates a new connection each time, bypassing Keep-Alive drops
        resp = httpx.post(URL, json={"messages": [{"role": "user", "content": q}]}, timeout=120)
        if resp.status_code == 200:
            print(f"**A:** {resp.json()['answer']}\n")
            print(f"**Refs:** {', '.join(resp.json().get('references', []))}\n")
        else:
            print(f"**Error:** {resp.text}\n")
    except Exception as e:
        print(f"**Exception:** {e}\n")
    print("---\n")
