import json
import os
import sys

sys.path.insert(0, os.path.abspath("scripts"))
from test_rubric_tuning import evaluate_theory_answer, paraphrase_items, find_theory_item

print("Inspecting Reversed answers with score > 25 (t_cover=0.70, t_partial=0.58, margin=15):")
for item in paraphrase_items:
    qid = item["questionId"]
    q_text = item["question"]
    ref_ans = item.get("referenceAnswer")
    concepts = item.get("expectedConcepts")
    if not ref_ans:
        cat_item = find_theory_item(q_text)
        ref_ans = cat_item["referenceAnswer"]
        concepts = cat_item.get("expectedConcepts", [])
        
    ans_text = item["answers"]["reversed"]
    res = evaluate_theory_answer(q_text, ans_text, ref_ans, concepts, 0.70, 0.58, 15)
    if res["score"] > 25:
        print(f"[{qid}] Score: {res['score']} (Cor={res['correctness']}, Rel={res['relevance']}, Cov={res['conceptCoverage']}, Com={res['communication']})")
        print(f"  Q: {q_text}")
        print(f"  A: {ans_text}")
        print(f"  Decisions: {res['point_decisions']}")
