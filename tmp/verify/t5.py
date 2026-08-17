import ast, os
os.environ["P2P_GRAPH_RAG_PROVIDER"]="cli"
p=r"D:/Claude Projects/antifragileai-regenold-evaluation/app/engines/_graph_rag_impl.py"
tree=ast.parse(open(p,encoding="utf-8").read())
verdicts=[]
for node in ast.walk(tree):
    if isinstance(node, ast.Dict):
        keys=[k.value for k in node.keys if isinstance(k, ast.Constant)]
        if "name" in keys and "answer" in keys and "refs" in keys:
            d={}
            for k,v in zip(node.keys,node.values):
                if isinstance(k,ast.Constant) and k.value in("name","answer"):
                    try: d[k.value]=ast.literal_eval(v)
                    except Exception: pass
            if "answer" in d and "name" in d: verdicts.append((d["name"],d["answer"],node.lineno))
print("verdicts found:",len(verdicts))
from app.integrations.regenold.models import normalise_answer_for_regenold
cut=[]
for name,ans,ln in verdicts:
    n=normalise_answer_for_regenold(ans, question="")
    if len(n.strip())<len(ans.strip())-5:
        cut.append((name,ln,len(ans),len(n)))
print("cut:",len(cut))
for c in cut: print("  ",c)
