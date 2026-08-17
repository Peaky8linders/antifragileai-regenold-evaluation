from app.data.graph_rag_prompts import resolve_answer_system
s = resolve_answer_system()
for pat in ["AT MOST 4 sentences total","four-sentence cap","the 4th sentence","exceed four","AT MOST four sentences"]:
    print(repr(pat), "->", s.count(pat))
