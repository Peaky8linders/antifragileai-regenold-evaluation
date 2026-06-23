import json
from collections import Counter
from evals.regenold.scenarios_medtech_graphrag_v124 import GROUND_TRUTH

def recall(answer, kws):
    low = (answer or "").lower()
    miss = [k for k in kws if k.lower() not in low]
    hit = len(kws) - len(miss)
    return hit/len(kws), miss

# 1) gold_answer self-recall (the achievable ceiling with the ideal concise reference)
print("=== GOLD_ANSWER SELF-RECALL (ceiling) ===")
self_scores=[]
self_miss=Counter()
for r in GROUND_TRUTH:
    sc,miss=recall(r["gold_answer"], r["expected_keywords"])
    self_scores.append(sc)
    for m in miss: self_miss[m]+=1
    if miss:
        print(f"{r['id']} self={sc:.2f} MISS={miss}")
print(f"\nGOLD self-recall MEAN = {sum(self_scores)/len(self_scores):.4f}")
print(f"keywords the gold_answer ITSELF misses: {dict(self_miss)}")

# 2) R139 Opus sidecar
print("\n=== R139 OPUS LIVE per-row ===")
side=json.load(open(".worktrees/r139-opus-stage2/evals/bench/results/medtech-graphrag-v124-r139-opus-live.json",encoding="utf-8"))
rows=side["ground_truth"]["rows"]
opus_miss=Counter()
opus_scores=[]
for r in rows:
    ans=r.get("predicted_answer") or r.get("answer_preview") or ""
    kws=r["expected_keywords"]
    sc,miss=recall(ans,kws)
    opus_scores.append(r.get("keyword_recall"))
    for m in miss: opus_miss[m]+=1
    print(f"{r['id']} kw_stored={r.get('keyword_recall')} recomputed={sc:.2f} len={len(ans)} MISS={miss}")
print(f"\nR139 Opus kw MEAN (stored) = {sum(x for x in opus_scores if x is not None)/len(opus_scores):.4f}")
print(f"most-missed keywords by Opus: {opus_miss.most_common(20)}")
