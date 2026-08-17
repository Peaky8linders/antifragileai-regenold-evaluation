import os
os.environ["P2P_GRAPH_RAG_PROVIDER"]="cli"
os.environ["REGENOLD_EXTERNAL_EMBEDDINGS"]="0"
from app.engines import graph_rag as g
tests = [
 ("_detect_robotic_surgery_inquiry", "Our hospital is deploying an AI system that assists in robotic surgery. What are our obligations?"),
 ("_detect_robotic_surgery_inquiry", "What are the obligations for an AI system used in robotic surgery?"),
 ("_detect_robotic_surgery_inquiry", "We are a hospital. Is our robotic surgery AI high-risk?"),
 ("_detect_robotic_surgery_inquiry", "Is a surgical robot high-risk?"),
 ("_detect_risk_framework_inquiry", "What are the risk categories under the EU AI Act?"),
 ("_detect_risk_framework_inquiry", "What are the risk categories of AI systems under the EU AI Act?"),
 ("_detect_risk_framework_inquiry", "What risk categories does the EU AI Act define?"),
 ("_detect_prohibited_practices_inquiry", "Which AI systems are banned?"),
]
for fn, q in tests:
    f = getattr(g, fn, None)
    print(fn, "->", (f(q) if f else "MISSING"), "|", q)
