import os
from fastapi.testclient import TestClient
from app.main import app

os.environ.pop("OPENAI_API_BASE", None)
os.environ.pop("OPENAI_API_KEY", None)

client = TestClient(app)
r = client.get("/healthz/llm")
print(r.json())
