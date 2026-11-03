import sys
import os
sys.path.insert(0, os.path.abspath("scripts"))
from test_all_rules import _THEORY_ITEMS_LIST, _split_reference_key_points, evaluate_theory_v2

print("=== 2-key-point questions with score > 65 ===")
for item in _THEORY_ITEMS_LIST:
    q = item['questionText']
    ref = item['referenceAnswer']
    kps = _split_reference_key_points(ref)
    if len(kps) == 2:
        res = evaluate_theory_v2(q, kps[0], ref, item.get('expectedConcepts', []))
        if res['score'] > 65:
            print(f"[{item['id']}] Score: {res['score']} (cor={res['correctness']}, rel={res['relevance']}, cov={res['conceptCoverage']}, com={res['communication']})")
            print(f"  Q: {q}")
            print(f"  KP1: {kps[0]}")
            print(f"  KP2: {kps[1]}")
            print(f"  Decisions: {res['point_decisions']}")

print("\n=== 3-4-key-point questions with score < 30 or > 70 ===")
outliers = []
for item in _THEORY_ITEMS_LIST:
    q = item['questionText']
    ref = item['referenceAnswer']
    kps = _split_reference_key_points(ref)
    if len(kps) in (3, 4):
        res = evaluate_theory_v2(q, kps[0], ref, item.get('expectedConcepts', []))
        if res['score'] < 30 or res['score'] > 70:
            outliers.append((res['score'], item['id'], q, kps, res))

outliers.sort(key=lambda x: x[0])
for s, qid, q, kps, res in outliers:
    print(f"[{qid}] Score: {s} (kps={len(kps)}, cor={res['correctness']}, rel={res['relevance']}, cov={res['conceptCoverage']}, com={res['communication']})")
    print(f"  Q: {q}")
    print(f"  KP1: {kps[0][:60]}...")
    print(f"  Decisions: {res['point_decisions']}")
