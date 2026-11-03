import sys
import os
sys.path.insert(0, os.path.abspath("scripts"))
from test_v4 import tuning_items, evaluate_theory_v4, find_theory_item

print("=== Tuning Set Good Answers with Score < 80 ===")
for item in tuning_items:
    q = item['question']
    ref = item.get('referenceAnswer') or find_theory_item(q)['referenceAnswer']
    ans = item['answers']['good']
    res = evaluate_theory_v4(q, ans, ref, item.get('expectedConcepts', []))
    if res['score'] < 80:
        print(f"[{item['questionId']}] Score={res['score']} (cor={res['correctness']}, rel={res['relevance']}, cov={res['conceptCoverage']}, com={res['communication']})")
        print(f"  decisions={res['point_decisions']}")
        print(f"  covered={res['covered']}, partial={res['partial']}, num_kp={res['num_kp']}")
