import sys
import os
import json
sys.path.insert(0, os.path.abspath("ai-service"))
sys.path.insert(0, os.path.abspath("scripts"))

from test_v4 import (
    tuning_items,
    heldout_items,
    paraphrase_items,
    evaluate_theory_v4,
    find_theory_item,
    _THEORY_ITEMS_LIST,
    _split_reference_key_points
)

def run_evaluation(tc=0.65, tp=0.54):
    print(f"\n=======================================================")
    print(f"EVALUATION REPORT WITH t_cover={tc:.2f}, t_partial={tp:.2f}")
    print(f"=======================================================")

    # First-key-point check across catalogue
    fkp_2, fkp_34 = [], []
    for item in _THEORY_ITEMS_LIST:
        q = item['questionText']
        ref = item['referenceAnswer']
        kps = _split_reference_key_points(ref)
        if not kps: continue
        res = evaluate_theory_v4(q, kps[0], ref, item.get('expectedConcepts', []), t_cover=tc, t_partial=tp)
        if len(kps) == 2:
            fkp_2.append((res['score'], item['id'], q, res))
        elif len(kps) in (3, 4):
            fkp_34.append((res['score'], item['id'], q, res))

    max_2 = max(x[0] for x in fkp_2)
    min_34 = min(x[0] for x in fkp_34)
    max_34 = max(x[0] for x in fkp_34)
    print(f"\nCatalogue First-Key-Point-Only Checks:")
    print(f"  2-KP (26 questions): min={min(x[0] for x in fkp_2)}, avg={sum(x[0] for x in fkp_2)/len(fkp_2):.1f}, max={max_2} -> Target <= 65: {'PASS' if max_2 <= 65 else 'FAIL'}")
    print(f"  3-4-KP (157 questions): min={min_34}, avg={sum(x[0] for x in fkp_34)/len(fkp_34):.1f}, max={max_34} -> Target in [30, 70]: {'PASS' if all(30 <= x[0] <= 70 for x in fkp_34) else 'FAIL'}")

    subsets = [
        ("Tuning Set (25 questions)", tuning_items),
        ("Held-out Set (25 questions)", heldout_items),
        ("Combined Paraphrase Set (50 questions)", paraphrase_items),
    ]

    # Check for team set
    team_path = "ai-service/tests/data/heldout_team_answers.json"
    if os.path.exists(team_path):
        with open(team_path, "r", encoding="utf-8") as f:
            team_items = json.load(f)
        subsets.append(("Team Held-out Set (20 questions)", team_items))
    else:
        print(f"\nNotice: {team_path} does not exist in workspace yet.")

    for name, items in subsets:
        scores = {"good": [], "partial": [], "wrong": [], "reversed": [], "vague": []}
        for item in items:
            q_text = item["question"]
            ref_ans = item.get("referenceAnswer") or find_theory_item(q_text)["referenceAnswer"]
            concepts = item.get("expectedConcepts", [])
            for k in scores:
                if k in item["answers"]:
                    ans_text = item["answers"][k]
                    res = evaluate_theory_v4(q_text, ans_text, ref_ans, concepts, t_cover=tc, t_partial=tp)
                    scores[k].append(res["score"])

        n_good = len(scores["good"]) or 1
        n_wrong = len(scores["wrong"]) or 1
        n_rev = len(scores["reversed"]) or 1
        n_vague = len(scores["vague"]) or 1

        g_ge_80 = sum(v >= 80 for v in scores["good"]) * 100 / n_good
        g_ge_60 = sum(v >= 60 for v in scores["good"]) * 100 / n_good
        w_le_15 = sum(v <= 15 for v in scores["wrong"]) * 100 / n_wrong
        r_le_25 = sum(v <= 25 for v in scores["reversed"]) * 100 / n_rev
        r_lt_50 = sum(v < 50 for v in scores["reversed"]) * 100 / n_rev
        v_le_25 = sum(v <= 25 for v in scores["vague"]) * 100 / n_vague

        tp = sum(v >= 50 for v in scores["good"])
        fn = sum(v < 50 for v in scores["good"])
        fp = sum(v >= 50 for v in (scores["wrong"] + scores["reversed"] + scores["vague"]))
        tn = sum(v < 50 for v in (scores["wrong"] + scores["reversed"] + scores["vague"]))

        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        acc = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) else 0.0

        print(f"\n---------------- {name} ----------------")
        print(f"  Target Check:")
        print(f"    Good >= 80 (Target >= 70%): {g_ge_80:.1f}% -> {'PASS' if g_ge_80 >= 70 else 'MISSED'}")
        print(f"    Good >= 60 (Target >= 90%): {g_ge_60:.1f}% -> {'PASS' if g_ge_60 >= 90 else 'MISSED'}")
        print(f"    Wrong <= 15 (Target >= 90%): {w_le_15:.1f}% -> {'PASS' if w_le_15 >= 90 else 'MISSED'}")
        print(f"    Reversed <= 25 (Target >= 70%): {r_le_25:.1f}% -> {'PASS' if r_le_25 >= 70 else 'MISSED'}")
        print(f"    Reversed < 50 (Target >= 90%): {r_lt_50:.1f}% -> {'PASS' if r_lt_50 >= 90 else 'MISSED'}")
        print(f"    Vague <= 25 (Target >= 85%): {v_le_25:.1f}% -> {'PASS' if v_le_25 >= 85 else 'MISSED'}")
        print(f"  Score >= 50 Metrics (Good vs Wrong/Rev/Vague):")
        print(f"    TP={tp}, FP={fp}, TN={tn}, FN={fn}")
        print(f"    Precision={prec:.4f}, Recall={rec:.4f}, F1={f1:.4f}, Accuracy={acc:.4f}")

if __name__ == "__main__":
    run_evaluation(0.65, 0.54)
