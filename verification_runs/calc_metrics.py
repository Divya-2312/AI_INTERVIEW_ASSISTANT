import json

with open('verification_runs/routing_scoring_selftest_results.json') as f:
    results = json.load(f)

print(f"Total test cases: {len(results)}")
modules = sorted(list(set(r['module'] for r in results)))
modules.append('OVERALL')

print(f"{'Module (self-test)':<24} | {'Total':<6} | {'TP':<4} {'FP':<4} {'TN':<4} {'FN':<4} | {'Precision':<10} | {'Recall':<10} | {'F1':<10} | {'Accuracy':<10}")
print('-' * 105)

for mod in modules:
    subset = results if mod == 'OVERALL' else [r for r in results if r['module'] == mod]
    total = len(subset)
    if total == 0:
        continue

    tp = sum(1 for r in subset if r['expected_pass'] and r['actual_pass'])
    fp = sum(1 for r in subset if not r['expected_pass'] and r['actual_pass'])
    tn = sum(1 for r in subset if not r['expected_pass'] and not r['actual_pass'])
    fn = sum(1 for r in subset if r['expected_pass'] and not r['actual_pass'])

    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    accuracy = ((tp + tn) / total) if total > 0 else 0.0

    print(f"{mod:<24} | {total:<6} | {tp:<4} {fp:<4} {tn:<4} {fn:<4} | {precision*100:>8.1f}%  | {recall*100:>8.1f}%  | {f1*100:>8.1f}%  | {accuracy*100:>8.1f}%")

print("\nPER-CASE SUMMARY:")
header = f"{'Module':<20} | {'Case Name':<35} | {'Acc':<4} {'Cor':<4} {'Rel':<4} {'Cov':<4} | {'Score':<5} | {'Model Used':<22} | {'Exp Band':<10} | {'OK?'}"
print(header)
print("-" * 115)
for r in results:
    mod = r['module']
    name = r['name']
    acc = r['acc']
    cor = r['cor']
    rel = r['rel']
    cov = r['cov']
    score = r['score']
    model_used = r['modelUsed']
    exp_band = r['expected_band']
    ok = "YES" if r['within_band'] else "NO"
    print(f"{mod:<20} | {name[:35]:<35} | {acc:<4} {cor:<4} {rel:<4} {cov:<4} | {score:<5} | {str(model_used)[:22]:<22} | {exp_band:<10} | {ok}")
