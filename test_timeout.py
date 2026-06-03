import httpx
import time

URL = "https://regenold-eu-ai-act-rag-production.up.railway.app/api/v1/regenold/eu-ai-act/ask"
q = "Can a hospital use an AI system to sort patients based on their biometric data to determine priority for an experimental clinical trial?"

print(f"Testing Q: {q}")
start = time.time()
try:
    # Use timeout=None to completely disable httpx client-side timeouts
    with httpx.Client(timeout=None) as client:
        resp = client.post(URL, json={"messages": [{"role": "user", "content": q}]})
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Success!")
        else:
            print(f"Error Body: {resp.text}")
except Exception as e:
    print(f"Exception Type: {type(e)}")
    print(f"Exception: {e}")

print(f"Total time elapsed: {time.time() - start:.2f} seconds")
