import json
import re
import os
import sys

# Ensure app is in path
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("ai-service"))

from app.utils.hr_gate import STOP, stem
from app.services.embedding_service import embedding_service

# Calibrated thresholds
THEORY_T_COVER = 0.70
THEORY_T_PARTIAL = 0.58
THEORY_SIDE_CAP_MARGIN = 26  # Documented: Test 3 (1st point 30..70) on questions with 5-6 key points requires margin 26 to pass score >= 30

def split_reference_key_points(reference_answer: str) -> list:
    """
    Split referenceAnswer into 2-6 points:
    Sentences, then split on ';', ' while ', ' whereas ', and clause boundaries;
    drop points under 4 words. Guarantees 2-6 points.
    """
    if not reference_answer or not reference_answer.strip():
        return []
    protected = re.sub(
        r'\b(e\.g\.|i\.e\.|etc\.|vs\.)',
        lambda m: m.group(0).replace('.', '__DOT__'),
        reference_answer.strip(),
        flags=re.IGNORECASE
    )
    # Protect commas inside parentheses
    protected = re.sub(
        r'\([^)]*\)',
        lambda m: m.group(0).replace(',', '__COMMA__'),
        protected
    )
    sents = [s.replace('__DOT__', '.').strip() for s in re.split(r'(?<=[.!?])\s+|\n+', protected) if s.strip()]
    points = []
    split_regex = r';|\s+while\s+|\s+whereas\s+|,\s+and\s+|,\s+but\s+|\s+--\s+|:\s+|,\s+which\s+|,\s+so\s+|,\s+since\s+|,\s+where\s+|,\s+meaning\s+|,\s+without\s+|,\s+allowing\s+|,\s+enabling\s+|,\s+or\s+'
    for s in sents:
        for pt in re.split(split_regex, s, flags=re.IGNORECASE):
            clean = pt.replace('__COMMA__', ',').strip().rstrip('.!?')
            w_count = len(re.findall(r"[A-Za-z][A-Za-z'-]*", clean))
            if w_count >= 4:
                points.append(clean)
    if len(points) < 3:
        new_pts = []
        for p in (points or [reference_answer.strip()]):
            for pt in re.split(r',\s+', p):
                clean = pt.replace('__COMMA__', ',').strip().rstrip('.!?')
                if len(re.findall(r"[A-Za-z][A-Za-z'-]*", clean)) >= 4:
                    new_pts.append(clean)
        if len(new_pts) >= len(points):
            points = new_pts
    if not points and reference_answer.strip():
        points = [reference_answer.strip()]
    if len(points) > 6:
        points = points[:6]
    return points

def split_answer_units(answer: str) -> list:
    """
    Split answer into comparison units: whole answer, 2-sentence sliding windows,
    single sentences, and clause-level key points.
    """
    if not answer or not answer.strip():
        return []
    clean_ans = answer.strip()
    protected = re.sub(
        r'\b(e\.g\.|i\.e\.|etc\.|vs\.)',
        lambda m: m.group(0).replace('.', '__DOT__'),
        clean_ans,
        flags=re.IGNORECASE
    )
    sents = [s.replace('__DOT__', '.').strip() for s in re.split(r'(?<=[.!?])\s+|\n+', protected) if s.strip()]
    kps = split_reference_key_points(clean_ans)

    units = []
    # 1. Whole answer
    units.append(clean_ans)
    # 2. 2-sentence sliding windows
    if len(sents) >= 2:
        for i in range(len(sents) - 1):
            w = f"{sents[i]} {sents[i+1]}"
            if w not in units:
                units.append(w)
    # 3. Single sentences
    for s in sents:
        if s not in units:
            units.append(s)
    # 4. Clauses
    for kp in kps:
        if kp not in units:
            units.append(kp)
    return units or [clean_ans]

def get_key_point_anchors(point: str, question: str) -> set:
    """
    Anchors = distinct content words (stemmed) after removing stop words
    AND every word whose stem occurs in the QUESTION text.
    """
    q_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", (question or "").lower())
    q_stems = {stem(w) for w in q_tokens}
    pt_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", (point or "").lower())
    anchors = set()
    for w in pt_tokens:
        if len(w) < 3 or w in STOP:
            continue
        s = stem(w)
        if s not in q_stems and w not in q_stems:
            anchors.add(s)
    return anchors

def calculate_theory_overall(relevance, correctness, concept_coverage, communication) -> int:
    """Exact rounded mean of the four theory parameter integer percentages."""
    def _pct(v):
        try:
            val = float(v)
        except (TypeError, ValueError):
            return 0
        if isinstance(v, float) and 0.0 < v <= 1.0:
            return int(round(v * 100.0))
        return int(round(max(0.0, min(100.0, val))))

    p_rel = _pct(relevance)
    p_cor = _pct(correctness)
    p_cov = _pct(concept_coverage)
    p_com = _pct(communication)
    return int(round((p_rel + p_cor + p_cov + p_com) / 4.0))

def evaluate_theory_answer(question: str, answer: str, reference_answer: str,
                           expected_concepts: list, t_cover: float = THEORY_T_COVER,
                           t_partial: float = THEORY_T_PARTIAL,
                           margin: int = THEORY_SIDE_CAP_MARGIN) -> dict:
    key_points = split_reference_key_points(reference_answer)
    units = split_answer_units(answer)
    ans_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", (answer or "").lower())
    ans_stems = {stem(w) for w in ans_tokens}
    q_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", (question or "").lower())
    q_stems = {stem(w) for w in q_tokens}

    covered = 0
    partial = 0
    covered_key_points = []
    partial_key_points = []
    point_decisions = []

    for kp in key_points:
        anchors = get_key_point_anchors(kp, question)
        matched_anchors = {a for a in anchors if a in ans_stems}
        best_sim = 0.0
        for u in units:
            sim = embedding_service.compute_similarity(kp, u)
            if sim > best_sim:
                best_sim = sim

        min_anchors = 2 if len(anchors) >= 4 else 1
        has_min = (len(matched_anchors) >= min_anchors) if anchors else True
        is_cov = has_min and (best_sim >= t_cover)
        is_part = not is_cov and (has_min and (best_sim >= t_partial))

        if is_cov:
            covered += 1
            covered_key_points.append(kp)
            point_decisions.append("covered")
        elif is_part:
            partial += 1
            partial_key_points.append(kp)
            point_decisions.append("partial")
        else:
            point_decisions.append("missed")

    num_kp = len(key_points) or 1
    correctness = round(100.0 * (covered + 0.5 * partial) / num_kp)

    def kp_matches_concept(c_str: str, kp: str) -> bool:
        kp_l = kp.lower()
        if c_str.lower() in kp_l:
            return True
        c_words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", c_str.lower()) if len(w) >= 3 and w not in STOP]
        c_non_q = [w for w in c_words if stem(w) not in q_stems and w not in q_stems and w not in q_tokens]
        target = c_non_q if c_non_q else c_words
        if not target:
            target = [w for w in re.findall(r"[A-Za-z0-9]+", c_str.lower()) if w not in STOP]
        if not target:
            return False
        tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", kp_l)
        stems = {stem(t) for t in tokens}
        def w_in(w):
            wl = w.lower()
            return wl in tokens or stem(wl) in stems or wl in kp_l
        return all(w_in(w) for w in target)

    if covered == num_kp and partial == 0:
        concept_coverage = 100
    elif correctness == 0:
        concept_coverage = 0
    else:
        cov_c, part_c = 0.0, 0.0
        for c in (expected_concepts or []):
            cstr = str(c).strip()
            c_words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", cstr.lower()) if len(w) >= 3 and w not in STOP]
            c_non_q = [w for w in c_words if stem(w) not in q_stems and w not in q_stems and w not in q_tokens]
            if not c_non_q:
                if covered >= 1:
                    cov_c += float(covered) / num_kp
            else:
                if any(kp_matches_concept(cstr, kp) for kp in covered_key_points):
                    cov_c += 1.0
                elif any(kp_matches_concept(cstr, kp) for kp in partial_key_points):
                    part_c += 1.0
        if expected_concepts:
            concept_coverage = round(100.0 * (cov_c + 0.5 * part_c) / len(expected_concepts))
        else:
            concept_coverage = correctness

    concept_coverage = min(concept_coverage, correctness)

    cos_sim = embedding_service.compute_similarity(answer, reference_answer)
    relevance = round(max(0.0, min(1.0, (cos_sim - 0.20) / 0.50)) * 100.0)

    communication = 80 if (covered == num_kp and partial == 0) else 60

    if correctness == 0:
        relevance = 0
        correctness = 0
        concept_coverage = 0
        communication = 0
        score = 0
    else:
        relevance = min(relevance, correctness + margin)
        communication = min(communication, correctness + margin)
        score = calculate_theory_overall(relevance, correctness, concept_coverage, communication)

    return {
        "score": score,
        "correctness": correctness,
        "conceptCoverage": concept_coverage,
        "relevance": relevance,
        "communication": communication,
        "point_decisions": point_decisions,
        "covered": covered,
        "partial": partial,
        "total_points": num_kp
    }

def main():
    # 1. Evaluate on 200 catalogue questions (verbatim)
    with open("ai-service/app/data/question_bank/java_theory_catalogue.json", "r", encoding="utf-8") as f:
        java_q = json.load(f)
    with open("ai-service/app/data/question_bank/dbms_theory_catalogue.json", "r", encoding="utf-8") as f:
        dbms_q = json.load(f)

    all_q = java_q + dbms_q
    print(f"Loaded {len(all_q)} catalogue questions (Java: {len(java_q)}, DBMS: {len(dbms_q)}).")

    t1_fails = 0
    t2_fails = 0
    t3_fails = 0
    t1_scores = []
    t2_scores = []
    t3_scores = []

    verb_tp, verb_fp, verb_fn, verb_tn = 0, 0, 0, 0

    for i, item in enumerate(all_q):
        q_text = item["questionText"]
        ref_ans = item["referenceAnswer"]
        concepts = item.get("expectedConcepts", [])

        # Test 1: Own referenceAnswer as answer -> score >= 90
        r1 = evaluate_theory_answer(q_text, ref_ans, ref_ans, concepts, THEORY_T_COVER, THEORY_T_PARTIAL)
        t1_scores.append(r1["score"])
        if r1["score"] < 90:
            t1_fails += 1
        for d in r1["point_decisions"]:
            if d == "covered":
                verb_tp += 1
            else:
                verb_fn += 1

        # Test 2: Different question referenceAnswer -> score <= 10
        diff_item = all_q[(i + 101) % len(all_q)]
        r2 = evaluate_theory_answer(q_text, diff_item["referenceAnswer"], ref_ans, concepts, THEORY_T_COVER, THEORY_T_PARTIAL)
        t2_scores.append(r2["score"])
        if r2["score"] > 10:
            t2_fails += 1
        for d in r2["point_decisions"]:
            if d == "covered":
                verb_fp += 1
            else:
                verb_tn += 1

        # Test 3: Only the first key point -> score 30..70
        kps = split_reference_key_points(ref_ans)
        r3 = evaluate_theory_answer(q_text, kps[0], ref_ans, concepts, THEORY_T_COVER, THEORY_T_PARTIAL)
        t3_scores.append(r3["score"])
        if r3["score"] < 30 or r3["score"] > 70:
            t3_fails += 1

    verb_precision = verb_tp / (verb_tp + verb_fp) if (verb_tp + verb_fp) else 0.0
    verb_recall = verb_tp / (verb_tp + verb_fn) if (verb_tp + verb_fn) else 0.0
    verb_f1 = (2 * verb_precision * verb_recall / (verb_precision + verb_recall)) if (verb_precision + verb_recall) else 0.0
    verb_accuracy = (verb_tp + verb_tn) / (verb_tp + verb_tn + verb_fp + verb_fn) if (verb_tp + verb_tn + verb_fp + verb_fn) else 0.0

    print(f"\n=======================================================")
    print(f"VERBATIM CALIBRATION RESULTS (T_COVER={THEORY_T_COVER:.2f}, T_PARTIAL={THEORY_T_PARTIAL:.2f}, MARGIN={THEORY_SIDE_CAP_MARGIN})")
    print(f"=======================================================")
    print(f"Test 1 (Own Ref >= 90):      Min={min(t1_scores)}, Avg={sum(t1_scores)/len(t1_scores):.1f} (Failures: {t1_fails}) [{'PASS' if t1_fails == 0 else 'FAIL'}]")
    print(f"Test 2 (Diff Ref <= 10):     Max={max(t2_scores)}, Avg={sum(t2_scores)/len(t2_scores):.1f} (Failures: {t2_fails}) [{'PASS' if t2_fails == 0 else 'FAIL'}]")
    print(f"Test 3 (1st Point 30..70):   Min={min(t3_scores)}, Max={max(t3_scores)}, Avg={sum(t3_scores)/len(t3_scores):.1f} (Failures: {t3_fails}) [{'PASS' if t3_fails == 0 else 'FAIL'}]")
    print(f"-------------------------------------------------------")
    print(f"Verbatim Precision: {verb_precision:.4f}")
    print(f"Verbatim Recall:    {verb_recall:.4f}")
    print(f"Verbatim F1 Score:  {verb_f1:.4f}")
    print(f"Verbatim Accuracy:  {verb_accuracy:.4f}")

    # 2. Evaluate on 50 paraphrase questions
    with open("ai-service/tests/data/paraphrase_answers.json", "r", encoding="utf-8") as f:
        para_q = json.load(f)
    print(f"\nLoaded {len(para_q)} paraphrase questions.")

    para_scores = {"good": [], "partial": [], "wrong": [], "vague": []}
    para_tp, para_fp, para_fn, para_tn = 0, 0, 0, 0

    cat_by_id = {q["id"]: q for q in all_q}
    cat_by_text = {q["questionText"].strip().lower(): q for q in all_q}

    for item in para_q:
        q_text = item["question"]
        qid = item.get("questionId")
        cat_item = cat_by_id.get(qid) or cat_by_text.get(q_text.strip().lower())
        ref_ans = item.get("referenceAnswer") or (cat_item.get("referenceAnswer") if cat_item else None)
        concepts = item.get("expectedConcepts") or (cat_item.get("expectedConcepts") if cat_item else [])

        # Evaluate good answer
        r_good = evaluate_theory_answer(q_text, item["answers"]["good"], ref_ans, concepts, THEORY_T_COVER, THEORY_T_PARTIAL)
        para_scores["good"].append(r_good["score"])
        for d in r_good["point_decisions"]:
            if d == "covered":
                para_tp += 1
            else:
                para_fn += 1

        # Evaluate partial answer
        r_part = evaluate_theory_answer(q_text, item["answers"]["partial"], ref_ans, concepts, THEORY_T_COVER, THEORY_T_PARTIAL)
        para_scores["partial"].append(r_part["score"])

        # Evaluate wrong answer
        r_wrong = evaluate_theory_answer(q_text, item["answers"]["wrong"], ref_ans, concepts, THEORY_T_COVER, THEORY_T_PARTIAL)
        para_scores["wrong"].append(r_wrong["score"])
        for d in r_wrong["point_decisions"]:
            if d == "covered":
                para_fp += 1
            else:
                para_tn += 1

        # Evaluate vague answer
        r_vague = evaluate_theory_answer(q_text, item["answers"]["vague"], ref_ans, concepts, THEORY_T_COVER, THEORY_T_PARTIAL)
        para_scores["vague"].append(r_vague["score"])

    para_precision = para_tp / (para_tp + para_fp) if (para_tp + para_fp) else 0.0
    para_recall = para_tp / (para_tp + para_fn) if (para_tp + para_fn) else 0.0
    para_f1 = (2 * para_precision * para_recall / (para_precision + para_recall)) if (para_precision + para_recall) else 0.0
    para_accuracy = (para_tp + para_tn) / (para_tp + para_tn + para_fp + para_fn) if (para_tp + para_tn + para_fp + para_fn) else 0.0

    print(f"\n=======================================================")
    print(f"PARAPHRASE BENCHMARK RESULTS (50 items x 4 types)")
    print(f"=======================================================")
    print(f"Good (target >= 70):     Min={min(para_scores['good'])}, Avg={sum(para_scores['good'])/len(para_scores['good']):.1f}, Max={max(para_scores['good'])}")
    print(f"Partial (target 30-65):  Min={min(para_scores['partial'])}, Avg={sum(para_scores['partial'])/len(para_scores['partial']):.1f}, Max={max(para_scores['partial'])}")
    print(f"Wrong (target <= 15):    Min={min(para_scores['wrong'])}, Avg={sum(para_scores['wrong'])/len(para_scores['wrong']):.1f}, Max={max(para_scores['wrong'])}")
    print(f"Vague (target <= 25):    Min={min(para_scores['vague'])}, Avg={sum(para_scores['vague'])/len(para_scores['vague']):.1f}, Max={max(para_scores['vague'])}")
    print(f"-------------------------------------------------------")
    print(f"Paraphrase Precision: {para_precision:.4f}")
    print(f"Paraphrase Recall:    {para_recall:.4f}")
    print(f"Paraphrase F1 Score:  {para_f1:.4f}")
    print(f"Paraphrase Accuracy:  {para_accuracy:.4f}")
    print(f"=======================================================\n")

    report = {
        "t_cover": THEORY_T_COVER,
        "t_partial": THEORY_T_PARTIAL,
        "side_cap_margin": THEORY_SIDE_CAP_MARGIN,
        "verbatim": {
            "label": "verbatim catalogue text, optimistic",
            "total_questions": len(all_q),
            "test1_own_ref": {
                "target": ">= 90",
                "passed": (t1_fails == 0),
                "fails": t1_fails,
                "min_score": min(t1_scores),
                "avg_score": round(sum(t1_scores) / len(t1_scores), 2)
            },
            "test2_diff_ref": {
                "target": "<= 10",
                "passed": (t2_fails == 0),
                "fails": t2_fails,
                "max_score": max(t2_scores),
                "avg_score": round(sum(t2_scores) / len(t2_scores), 2)
            },
            "test3_first_key_point": {
                "target": "30 .. 70",
                "passed": (t3_fails == 0),
                "fails": t3_fails,
                "min_score": min(t3_scores),
                "max_score": max(t3_scores),
                "avg_score": round(sum(t3_scores) / len(t3_scores), 2)
            },
            "metrics": {
                "precision": round(verb_precision, 4),
                "recall": round(verb_recall, 4),
                "f1": round(verb_f1, 4),
                "accuracy": round(verb_accuracy, 4)
            }
        },
        "paraphrase": {
            "label": "hand-written answers",
            "total_questions": len(para_q),
            "score_summary": {
                "good": {
                    "target": ">= 70",
                    "min": min(para_scores["good"]),
                    "avg": round(sum(para_scores["good"]) / len(para_scores["good"]), 2),
                    "max": max(para_scores["good"])
                },
                "partial": {
                    "target": "30-65",
                    "min": min(para_scores["partial"]),
                    "avg": round(sum(para_scores["partial"]) / len(para_scores["partial"]), 2),
                    "max": max(para_scores["partial"])
                },
                "wrong": {
                    "target": "<= 15",
                    "min": min(para_scores["wrong"]),
                    "avg": round(sum(para_scores["wrong"]) / len(para_scores["wrong"]), 2),
                    "max": max(para_scores["wrong"])
                },
                "vague": {
                    "target": "<= 25",
                    "min": min(para_scores["vague"]),
                    "avg": round(sum(para_scores["vague"]) / len(para_scores["vague"]), 2),
                    "max": max(para_scores["vague"])
                }
            },
            "metrics": {
                "precision": round(para_precision, 4),
                "recall": round(para_recall, 4),
                "f1": round(para_f1, 4),
                "accuracy": round(para_accuracy, 4)
            }
        }
    }
    with open("ai-service/app/data/rubric_calibration_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("Saved calibration report to ai-service/app/data/rubric_calibration_report.json")

if __name__ == "__main__":
    main()
