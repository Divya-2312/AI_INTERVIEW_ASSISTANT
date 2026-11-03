import sys
import os
sys.path.insert(0, os.path.abspath("scripts"))
from test_v4 import tuning_items, evaluate_theory_v4, find_theory_item, _split_reference_key_points, _split_answer_units, sim

for qid in ['java-theory-001', 'java-theory-003', 'java-theory-011', 'java-theory-013', 'dbms-theory-002']:
    item = [x for x in tuning_items if x['questionId'] == qid][0]
    q = item['question']
    ref = item.get('referenceAnswer') or find_theory_item(q)['referenceAnswer']
    ans = item['answers']['good']
    kps = _split_reference_key_points(ref)
    units = _split_answer_units(ans)
    print(f"\n[{qid}] Ans: {ans}")
    for idx, kp in enumerate(kps):
        best_u = max(units, key=lambda u: sim(kp, u))
        best_s = sim(kp, best_u)
        print(f"  KP{idx+1} ({best_s:.3f}): {kp[:60]}... | best_u: {best_u[:60]}...")
