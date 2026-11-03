import json
import os
import sys
import re
import numpy as np

sys.path.insert(0, os.path.abspath("ai-service"))

from app.models.llama_provider import (
    _THEORY_ITEMS_LIST,
    _split_reference_key_points,
    _get_key_point_anchors,
    calculate_theory_overall,
    find_theory_item,
    stem, STOP
)
from app.services.embedding_service import embedding_service, _load_model

# Load contradiction pairs
with open("ai-service/app/data/contradiction_pairs.json", "r", encoding="utf-8") as f:
    CONTRADICTION_PAIRS = json.load(f)

# Load paraphrase items
with open("ai-service/tests/data/paraphrase_answers.json", "r", encoding="utf-8") as f:
    paraphrase_items = json.load(f)

print(f"Loaded {len(paraphrase_items)} paraphrase items.")

NEGATION_WORDS = {"not", "no", "never", "cannot", "can't", "cant", "only", "none", "without"}

def count_contradiction_cues(kp: str, u: str, anchors: set) -> int:
    kp_l = kp.lower()
    u_l = u.lower()
    cues = 0
    
    # Check antonym pairs
    for term_a, term_b in CONTRADICTION_PAIRS:
        a_in_kp = bool(re.search(r'\b' + re.escape(term_a) + r'\b', kp_l))
        b_in_kp = bool(re.search(r'\b' + re.escape(term_b) + r'\b', kp_l))
        a_in_u = bool(re.search(r'\b' + re.escape(term_a) + r'\b', u_l))
        b_in_u = bool(re.search(r'\b' + re.escape(term_b) + r'\b', u_l))
        
        if a_in_kp and not b_in_kp and b_in_u and not a_in_u:
            cues += 1
        elif b_in_kp and not a_in_kp and a_in_u and not b_in_u:
            cues += 1

    # Check negation mismatch on matched anchors
    kp_words = re.findall(r"[A-Za-z][A-Za-z'-]*", kp_l)
    u_words = re.findall(r"[A-Za-z][A-Za-z'-]*", u_l)
    
    for a in anchors:
        a_in_kp = any(stem(w) == a for w in kp_words)
        a_in_u = any(stem(w) == a for w in u_words)
        if a_in_kp and a_in_u:
            neg_pattern = r'\b(?:not|no|never|cannot|can\'t|cant|without|none|only)\s+(?:\w+\s+){0,2}\b'
            neg_kp = False
            for m in re.finditer(r'\b[A-Za-z]+\b', kp_l):
                if stem(m.group(0)) == a:
                    start_idx = max(0, m.start() - 25)
                    prefix = kp_l[start_idx:m.start()]
                    if re.search(neg_pattern + r'$', prefix):
                        neg_kp = True
                        break
            neg_u = False
            for m in re.finditer(r'\b[A-Za-z]+\b', u_l):
                if stem(m.group(0)) == a:
                    start_idx = max(0, m.start() - 25)
                    prefix = u_l[start_idx:m.start()]
                    if re.search(neg_pattern + r'$', prefix):
                        neg_u = True
                        break
            if neg_kp != neg_u:
                cues += 1
                break
                
    return cues

def compute_communication(answer: str, key_points: list, question: str, ans_stems: set) -> int:
    comm = 40
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", (answer or "").lower())
    total_words = len(words)
    if total_words >= 12:
        comm += 20
        
    connectors = {"because", "becoz", "so", "while", "whereas", "therefore", "which", "since", "but"}
    if any(c in words for c in connectors):
        comm += 15
        
    all_anchors = set()
    for kp in key_points:
        all_anchors.update(_get_key_point_anchors(kp, question))
    matched_anchors = {a for a in all_anchors if a in ans_stems}
    if len(matched_anchors) >= 2:
        comm += 15
        
    filler_count = 0
    i = 0
    while i < total_words:
        w = words[i]
        if w in {"umm", "um", "like", "maybe"}:
            filler_count += 1
        elif w == "kind" and i + 1 < total_words and words[i + 1] == "of":
            filler_count += 2
            i += 1
        elif w == "i" and i + 1 < total_words and words[i + 1] in {"think", "guess"}:
            filler_count += 2
            i += 1
        i += 1
        
    if total_words > 0 and (filler_count / total_words) > 0.15:
        comm -= 15
        
    return max(0, min(100, comm))

def split_answer_units(answer: str) -> list:
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
    kps = _split_reference_key_points(clean_ans)
    
    units = []
    # 1. Whole answer
    units.append(clean_ans)
    # 2. 2-sentence windows
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

# Gather all texts to precompute embeddings
print("Pre-gathering texts for batch embedding...")
unique_texts = set()

# Paraphrase texts
for item in paraphrase_items:
    q_text = item["question"]
    ref_ans = item.get("referenceAnswer")
    if not ref_ans:
        cat_item = find_theory_item(q_text)
        ref_ans = cat_item["referenceAnswer"]
    unique_texts.add(ref_ans)
    for kp in _split_reference_key_points(ref_ans):
        unique_texts.add(kp)
    for k in ["good", "partial", "wrong", "reversed", "vague"]:
        ans = item["answers"][k]
        unique_texts.add(ans)
        for u in split_answer_units(ans):
            unique_texts.add(u)

# Catalogue sample texts
for i, item in enumerate(_THEORY_ITEMS_LIST[:50]):
    ref = item["referenceAnswer"]
    unique_texts.add(ref)
    for kp in _split_reference_key_points(ref):
        unique_texts.add(kp)
    diff_ref = _THEORY_ITEMS_LIST[(i + 101) % len(_THEORY_ITEMS_LIST)]["referenceAnswer"]
    unique_texts.add(diff_ref)
    for u in split_answer_units(diff_ref):
        unique_texts.add(u)
    kps = _split_reference_key_points(ref)
    if kps:
        first_kp = kps[0]
        unique_texts.add(first_kp)
        for u in split_answer_units(first_kp):
            unique_texts.add(u)

unique_texts = list(unique_texts)
print(f"Encoding {len(unique_texts)} unique texts in batch...")
model = _load_model()
embeddings = model.encode(unique_texts, batch_size=128, normalize_embeddings=True, show_progress_bar=False)
emb_dict = {text: embeddings[i] for i, text in enumerate(unique_texts)}
print("Pre-encoding complete!")

def fast_sim(t1, t2):
    e1 = emb_dict.get(t1)
    e2 = emb_dict.get(t2)
    if e1 is None or e2 is None:
        return embedding_service.compute_similarity(t1, t2)
    return float(np.dot(e1, e2))

def evaluate_theory_answer(q_text, ans_text, ref_ans, concepts, t_cover, t_partial, side_cap_margin):
    key_points = _split_reference_key_points(ref_ans)
    units = split_answer_units(ans_text)
    ans_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", (ans_text or "").lower())
    ans_stems = {stem(w) for w in ans_tokens}
    q_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", (q_text or "").lower())
    q_stems = {stem(w) for w in q_tokens}
    
    num_kp = len(key_points) or 1
    covered = 0
    partial = 0
    covered_key_points = []
    partial_key_points = []
    point_decisions = []
    
    for kp in key_points:
        anchors = _get_key_point_anchors(kp, q_text)
        matched_anchors = {a for a in anchors if a in ans_stems}
        best_sim = 0.0
        best_unit = ""
        for u in units:
            sim = fast_sim(kp, u)
            if sim > best_sim:
                best_sim = sim
                best_unit = u
                
        min_anchors = 2 if len(anchors) >= 4 else 1
        has_min = (len(matched_anchors) >= min_anchors) if anchors else True
        is_cov = has_min and (best_sim >= t_cover)
        is_part = not is_cov and (has_min and (best_sim >= t_partial))
        
        decision = "missed"
        if is_cov:
            decision = "covered"
        elif is_part:
            decision = "partial"
            
        if decision != "missed":
            cues = count_contradiction_cues(kp, best_unit, matched_anchors)
            if cues >= 2:
                decision = "missed"
            elif cues >= 1:
                if decision == "covered":
                    decision = "partial"
                else:
                    decision = "missed"
                
        if decision == "covered":
            covered += 1
            covered_key_points.append(kp)
            point_decisions.append("covered")
        elif decision == "partial":
            partial += 1
            partial_key_points.append(kp)
            point_decisions.append("partial")
        else:
            point_decisions.append("missed")
            
    correctness = round(100.0 * (covered + 0.5 * partial) / num_kp)
    
    def _kp_matches_concept(c_str: str, kp: str) -> bool:
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
        for c in (concepts or []):
            cstr = str(c).strip()
            c_words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", cstr.lower()) if len(w) >= 3 and w not in STOP]
            c_non_q = [w for w in c_words if stem(w) not in q_stems and w not in q_stems and w not in q_tokens]
            if not c_non_q:
                if covered >= 1:
                    cov_c += float(covered) / num_kp
            else:
                if any(_kp_matches_concept(cstr, kp) for kp in covered_key_points):
                    cov_c += 1.0
                elif any(_kp_matches_concept(cstr, kp) for kp in partial_key_points):
                    part_c += 1.0
        if concepts:
            concept_coverage = round(100.0 * (cov_c + 0.5 * part_c) / len(concepts))
        else:
            concept_coverage = correctness
            
    concept_coverage = min(concept_coverage, correctness)
    
    # Relevance
    cos_sim = fast_sim(ans_text, ref_ans)
    relevance = round(max(0.0, min(1.0, (cos_sim - 0.20) / 0.50)) * 100.0)
    
    # Communication
    communication = compute_communication(ans_text, key_points, q_text, ans_stems)
    
    if correctness == 0:
        relevance = 0
        correctness = 0
        concept_coverage = 0
        communication = 0
        score = 0
    else:
        relevance = min(relevance, correctness + side_cap_margin)
        communication = min(communication, correctness + side_cap_margin)
        score = calculate_theory_overall(relevance, correctness, concept_coverage, communication)
        
    return {
        "score": score,
        "correctness": correctness,
        "relevance": relevance,
        "conceptCoverage": concept_coverage,
        "communication": communication,
        "point_decisions": point_decisions
    }

if __name__ == "__main__":
    # Run test grid across candidate parameters
    grid = [
        (0.68, 0.55, 15),
        (0.68, 0.55, 20),
        (0.68, 0.55, 26),
        (0.70, 0.58, 15),
        (0.70, 0.58, 20),
        (0.70, 0.58, 26),
        (0.72, 0.58, 15),
        (0.72, 0.58, 26),
        (0.75, 0.60, 15),
        (0.75, 0.60, 26),
    ]

    for t_cover, t_partial, margin in grid:
        scores = {"good": [], "partial": [], "wrong": [], "reversed": [], "vague": []}
        for item in paraphrase_items:
            q_text = item["question"]
            ref_ans = item.get("referenceAnswer")
            concepts = item.get("expectedConcepts")
            if not ref_ans:
                cat_item = find_theory_item(q_text)
                ref_ans = cat_item["referenceAnswer"]
                concepts = cat_item.get("expectedConcepts", [])
                
            for k in ["good", "partial", "wrong", "reversed", "vague"]:
                ans_text = item["answers"][k]
                res = evaluate_theory_answer(q_text, ans_text, ref_ans, concepts, t_cover, t_partial, margin)
                scores[k].append(res["score"])
                
        # Check old tests: Test 1 (own ref >= 90), Test 2 (diff ref <= 10), Test 3 (1st kp 30-70)
        t1_scores, t2_scores, t3_scores = [], [], []
        for i, item in enumerate(_THEORY_ITEMS_LIST[:40]):
            q_text = item["questionText"]
            ref_ans = item["referenceAnswer"]
            concepts = item.get("expectedConcepts", [])
            kps = _split_reference_key_points(ref_ans)
            first_kp = kps[0] if kps else ref_ans
            diff_item = _THEORY_ITEMS_LIST[(i + 101) % len(_THEORY_ITEMS_LIST)]
            diff_ref = diff_item["referenceAnswer"]
            
            r1 = evaluate_theory_answer(q_text, ref_ans, ref_ans, concepts, t_cover, t_partial, margin)
            t1_scores.append(r1["score"])
            r2 = evaluate_theory_answer(q_text, diff_ref, ref_ans, concepts, t_cover, t_partial, margin)
            t2_scores.append(r2["score"])
            r3 = evaluate_theory_answer(q_text, first_kp, ref_ans, concepts, t_cover, t_partial, margin)
            t3_scores.append(r3["score"])
            
        t1_pass = all(s >= 90 for s in t1_scores)
        t2_pass = all(s <= 10 for s in t2_scores)
        t3_pass = all(30 <= s <= 70 for s in t3_scores)
        t3_min, t3_max = min(t3_scores), max(t3_scores)
        
        print(f"\n--- GRID: t_cover={t_cover}, t_partial={t_partial}, margin={margin} ---")
        print(f"Good (target >= 80):    min={min(scores['good'])}, avg={sum(scores['good'])/len(scores['good']):.1f}, max={max(scores['good'])}")
        print(f"Partial (target 35-65): min={min(scores['partial'])}, avg={sum(scores['partial'])/len(scores['partial']):.1f}, max={max(scores['partial'])}")
        print(f"Wrong (target <= 15):   min={min(scores['wrong'])}, avg={sum(scores['wrong'])/len(scores['wrong']):.1f}, max={max(scores['wrong'])}")
        print(f"Reversed (target <= 25):min={min(scores['reversed'])}, avg={sum(scores['reversed'])/len(scores['reversed']):.1f}, max={max(scores['reversed'])}")
        print(f"Vague (target <= 25):   min={min(scores['vague'])}, avg={sum(scores['vague'])/len(scores['vague']):.1f}, max={max(scores['vague'])}")
        print(f"Old Tests: T1(>=90)={t1_pass} (min={min(t1_scores)}), T2(<=10)={t2_pass} (max={max(t2_scores)}), T3(30-70)={t3_pass} (min={t3_min}, max={t3_max})")

