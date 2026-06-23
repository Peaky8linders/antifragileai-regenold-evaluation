import json,textwrap
side=json.load(open(".worktrees/r139-opus-stage2/evals/bench/results/medtech-graphrag-v124-r139-opus-live.json",encoding="utf-8"))
rows={r["id"]:r for r in side["ground_truth"]["rows"]}
for rid in ["grb_08","grb_10","grb_17","grb_18","grb_20"]:
    r=rows[rid]
    print("="*80)
    print(f"{rid}  kw={r.get('keyword_recall')}  len={len(r.get('predicted_answer') or '')}  refL={r.get('ref_loose')}")
    print(f"Q: {r['question']}")
    print(f"EXPECTED_KW: {r['expected_keywords']}")
    print(f"ANSWER:\n{textwrap.fill(r.get('predicted_answer') or '', 100)}")
    rsn=r.get('reasoning')
    if rsn:
        s=rsn if isinstance(rsn,str) else json.dumps(rsn)
        print(f"REASONING(first 600): {s[:600]}")
