import json
import glob

files = [
    'evals/bench/results/paper-v4-paper-v4-local.json',
    'evals/bench/results/medtech-lifesci-r136-r136-medls-local.json',
    'evals/bench/results/medtech-graphrag-v124-r124-medgrb-local.json'
]

def find_results(data):
    results = []
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                results.extend(v)
            elif isinstance(v, dict):
                results.extend(find_results(v))
    elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        results.extend(data)
    return results

report = ""

for fpath in files:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = find_results(data)
        
        report += f"# Analysis for {fpath}\n"
        report += f"Total scenarios: {len(results)}\n\n"
        
        metrics = {'ref_loose': [], 'ref_strict': [], 'keyword_recall': [], 'regulatory_tone': []}
        errors = []
        refusals = 0
        mistakes = []
        
        for r in results:
            # Collect metrics
            for m in metrics.keys():
                if m in r and r[m] is not None:
                    try:
                        metrics[m].append(float(r[m]))
                    except: pass
            
            err = r.get('error')
            if err:
                errors.append((r.get('id', 'unk'), err))
                
            if r.get('is_refusal') is True:
                refusals += 1
                
            # Mistakes: poor recall or loose ref
            loose = float(r.get('ref_loose', 1.0) or 0.0)
            recall = float(r.get('keyword_recall', 1.0) or 0.0)
            if loose < 1.0 or recall < 0.5 or err:
                mistakes.append({
                    'id': r.get('id', 'unk'),
                    'question': r.get('question', ''),
                    'reasoning': r.get('reasoning', ''),
                    'predicted': r.get('predicted_answer', ''),
                    'error': err,
                    'loose': loose,
                    'recall': recall
                })
        
        report += "### Metrics (Averages)\n"
        for m, vals in metrics.items():
            avg = sum(vals)/len(vals) if vals else 0
            report += f"- {m}: {avg:.2f} (from {len(vals)})\n"
            
        report += f"- Refusals: {refusals}\n"
        report += f"- Errors: {len(errors)}\n"
        for e in errors[:10]:
            report += f"  - [{e[0]}] {e[1]}\n"
            
        report += f"\n### Mistakes / Low Score Examples ({len(mistakes)})\n"
        for m in mistakes[:10]: # show up to 10
            report += f"**ID**: {m['id']}\n"
            report += f"**Q**: {m['question']}\n"
            report += f"**Error**: {m['error']}\n"
            report += f"**Scores**: Loose={m['loose']}, Recall={m['recall']}\n"
            report += f"**Reasoning**: {str(m['reasoning'])[:200]}...\n"
            report += f"**Predicted**: {str(m['predicted'])[:200]}...\n"
            report += "---\n"
            
        report += "\n\n"
            
    except Exception as e:
        report += f"Failed to process {fpath}: {e}\n\n"

with open('eval_analysis_report.md', 'w', encoding='utf-8') as f:
    f.write(report)
