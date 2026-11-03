import sys
import os
sys.path.insert(0, os.path.abspath("scripts"))
from test_v4 import tuning_items, heldout_items, paraphrase_items, evaluate_theory_v4, find_theory_item, _THEORY_ITEMS_LIST, _split_reference_key_points

print("Tuning threshold grid on Tuning Set (25 questions)...", flush=True)

grid = [
    (0.64, 0.52),
    (0.64, 0.54),
    (0.65, 0.52),
    (0.65, 0.54),
    (0.65, 0.56),
    (0.66, 0.54),
    (0.66, 0.56),
    (0.68, 0.55),
    (0.70, 0.58),
]

for tc, tp in grid:
    scores = {"good": [], "partial": [], "wrong": [], "reversed": [], "vague": []}
    for item in tuning_items:
        q = item["question"]
        ref = item.get("referenceAnswer") or find_theory_item(q)["referenceAnswer"]
        concepts = item.get("expectedConcepts", [])
        for k in scores:
            ans = item["answers"][k]
            r = evaluate_theory_v4(q, ans, ref, concepts, t_cover=tc, t_partial=tp)
            scores[k].append(r["score"])

    # Check 2-kp and 3-4-kp on catalogue
    fkp_2, fkp_34 = [], []
    for item in _THEORY_ITEMS_LIST[:50]:
        q = item['questionText']
        ref = item['referenceAnswer']
        kps = _split_reference_key_points(ref)
        if not kps: continue
        r = evaluate_theory_v4(q, kps[0], ref, item.get('expectedConcepts', []), t_cover=tc, t_partial=tp)
        if len(kps) == 2: fkp_2.append(r['score'])
        elif len(kps) in (3, 4): fkp_34.append(r['score'])

    g80 = sum(v >= 80 for v in scores["good"]) * 100 / 25
    g60 = sum(v >= 60 for v in scores["good"]) * 100 / 25
    w15 = sum(v <= 15 for v in scores["wrong"]) * 100 / 25
    r25 = sum(v <= 25 for v in scores["reversed"]) * 100 / 25
    r50 = sum(v < 50 for v in scores["reversed"]) * 100 / 25
    v25 = sum(v <= 25 for v in scores["vague"]) * 100 / 25
    max_2kp = max(fkp_2) if fkp_2 else 0
    min_34kp = min(fkp_34) if fkp_34 else 0
    max_34kp = max(fkp_34) if fkp_34 else 0

    print(f"tc={tc:.2f}, tp={tp:.2f} | Good>=80: {g80:4.1f}%, >=60: {g60:4.1f}% | Wrong<=15: {w15:4.1f}% | Rev<=25: {r25:4.1f}%, <50: {r50:4.1f}% | Vague<=25: {v25:4.1f}% | 2kpMax={max_2kp}, 34kp=[{min_34kp},{max_34kp}]", flush=True)
