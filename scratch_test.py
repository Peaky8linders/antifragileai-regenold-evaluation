import os
from dotenv import load_dotenv
load_dotenv()

from app.graph.client import get_graph_client

client = get_graph_client()
print(f"Client enabled: {client.enabled}")
if client.enabled:
    print(f"Health check status: {client.health_check()}")
    res = client.execute_read("MATCH (n) RETURN labels(n) as lbl, count(n) as cnt")
    print("Graph node counts:")
    for row in res:
        print(f"  {row['lbl']}: {row['cnt']}")
else:
    print("Graph client is not enabled.")
