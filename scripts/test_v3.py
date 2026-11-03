import sys
import os
import re
import json
import math
import numpy as np
sys.path.insert(0, os.path.abspath("ai-service"))

from app.models.llama_provider import (
    _THEORY_ITEMS_LIST,
    _split_reference_key_points,
    _get_key_point_anchors,
    _split_answer_units,
    calculate_theory_overall,
    count_contradiction_cues,
    compute_theory_communication,
    THEORY_T_COVER,
    THEORY_T_PARTIAL,
    THEORY_SIDE_CAP_MARGIN,
    find_theory_item,
    stem, STOP
)
from app.services.embedding_service import _load_model

# 1. Load Data
with open("ai-service/tests/data/paraphrase_answers.json", "r", encoding="utf-8") as f:
    paraphrase_items = json.load(f)

with open("ai-service/app/data/contradiction_pairs.json", "r", encoding="utf-8") as f:
    CONTRADICTION_PAIRS = json.load(f)

model = _load_model()

# 2. Word Embedding Cache for Soft Anchors
WORD_EMB_CACHE = {}

def get_word_emb(w: str):
    w_clean = w.lower().strip()
    if w_clean not in WORD_EMB_CACHE:
        WORD_EMB_CACHE[w_clean] = model.encode([w_clean], normalize_embeddings=True, show_progress_bar=False)[0]
    return WORD_EMB_CACHE[w_clean]

def compute_word_sim(w1: str, w2: str) -> float:
    e1 = get_word_emb(w1)
    e2 = get_word_emb(w2)
    return float(np.dot(e1, e2))

def match_soft_anchors(anchors: set, ans_tokens: list, ans_stems: set) -> dict:
    """
    Returns map of anchor -> matched_word (or stem) for soft anchor matching.
    Cosine >= 0.60.
    """
    matched = {}
    ans_content = [w for w in ans_tokens if len(w) >= 3 and w not in STOP]
    for a in anchors:
        if a in ans_stems:
            matched[a] = a
            continue
        for w in ans_content:
            if compute_word_sim(w, a) >= 0.60:
                matched[a] = w
                break
    return matched

# 3. Swapped Property Check
KNOWN_ENTITY_PAIRS = [
    ("arraylist", "linkedlist"),
    ("throw", "throws"),
    ("checked", "unchecked"),
    ("stack", "heap"),
    ("process", "thread"),
    ("hashmap", "hashtable"),
    ("hashset", "treeset"),
    ("abstract class", "interface"),
    ("overloading", "overriding"),
    ("static", "instance"),
    ("this", "super"),
    ("dirty read", "non-repeatable read"),
    ("optimistic", "pessimistic"),
    ("vertical scaling", "horizontal scaling"),
    ("primary key", "unique key"),
    ("entity set", "entity"),
    ("comparable", "comparator"),
    ("superclass", "subclass"),
    ("union all", "union"),
    ("inner join", "left join"),
    ("left join", "right join"),
    ("truncate", "delete"),
    ("where", "having"),
    ("oltp", "olap"),
    ("equal", "equals"),
    ("extends", "implements"),
    ("final", "finally"),
    ("composition", "inheritance"),
    ("commit", "rollback"),
    ("drop", "truncate"),
    ("drop", "delete"),
    ("string", "stringbuilder"),
    ("stringbuffer", "stringbuilder"),
]

def split_clauses(text: str) -> list:
    parts = re.split(r';|\s+while\s+|\s+whereas\s+|\s+whilst\s+|,\s+but\s+|,\s+and\s+|\s+--\s+|\.\s+', text, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]

def find_entity_in_text(entity: str, text: str) -> bool:
    pat = r'\b' + re.escape(entity) + r'(?:s|es)?\b'
    return bool(re.search(pat, text, re.IGNORECASE))

def get_clause_for_entity(clauses: list, entity: str) -> str:
    matching = [c for c in clauses if find_entity_in_text(entity, c)]
    return " ".join(matching) if matching else ""

def check_swapped_properties(question: str, answer: str, reference_answer: str, kp: str) -> bool:
    ans_clauses = split_clauses(answer)
    ref_clauses = split_clauses(reference_answer)

    pairs_to_check = []
    for e1, e2 in KNOWN_ENTITY_PAIRS:
        in_ref = find_entity_in_text(e1, reference_answer) and find_entity_in_text(e2, reference_answer)
        in_ans = find_entity_in_text(e1, answer) and find_entity_in_text(e2, answer)
        if in_ref and in_ans:
            pairs_to_check.append((e1, e2))

    m = re.search(r'\b([A-Za-z0-9_`\'-]+(?:\s+[A-Za-z0-9_`\'-]+)?)\s+(?:while|whereas|whilst)\s+([A-Za-z0-9_`\'-]+(?:\s+[A-Za-z0-9_`\'-]+)?)\b', kp, re.IGNORECASE)
    if m:
        e1, e2 = m.group(1).strip().lower(), m.group(2).strip().lower()
        if len(e1) >= 3 and len(e2) >= 3 and e1 not in STOP and e2 not in STOP:
            if find_entity_in_text(e1, answer) and find_entity_in_text(e2, answer):
                pairs_to_check.append((e1, e2))

    m_q = re.search(r'difference between\s+(?:a |an |the )?([A-Za-z0-9_`\'-]+(?:\s+[A-Za-z0-9_`\'-]+)?)\s+and\s+(?:a |an |the )?([A-Za-z0-9_`\'-]+(?:\s+[A-Za-z0-9_`\'-]+)?)\b', question, re.IGNORECASE)
    if m_q:
        e1, e2 = m_q.group(1).strip().lower(), m_q.group(2).strip().lower()
        if len(e1) >= 3 and len(e2) >= 3 and e1 not in STOP and e2 not in STOP:
            if find_entity_in_text(e1, answer) and find_entity_in_text(e2, answer):
                pairs_to_check.append((e1, e2))

    if not pairs_to_check:
        return False

    q_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", question.lower())
    q_stems = {stem(w) for w in q_tokens}

    for e1, e2 in pairs_to_check:
        ref_c1 = get_clause_for_entity(ref_clauses, e1)
        ref_c2 = get_clause_for_entity(ref_clauses, e2)
        if not ref_c1 or not ref_c2:
            continue

        anchors_e1 = {stem(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]*", ref_c1.lower()) if len(w) >= 3 and w not in STOP and stem(w) not in q_stems}
        anchors_e2 = {stem(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]*", ref_c2.lower()) if len(w) >= 3 and w not in STOP and stem(w) not in q_stems}

        distinct_ref_e1 = anchors_e1 - anchors_e2
        distinct_ref_e2 = anchors_e2 - anchors_e1

        e1_words = {stem(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]*", e1.lower())}
        e2_words = {stem(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]*", e2.lower())}
        distinct_ref_e1 -= (e1_words | e2_words)
        distinct_ref_e2 -= (e1_words | e2_words)

        if not distinct_ref_e1 or not distinct_ref_e2:
            continue

        ans_c1 = get_clause_for_entity(ans_clauses, e1)
        ans_c2 = get_clause_for_entity(ans_clauses, e2)
        if not ans_c1 or not ans_c2:
            continue

        ans_stems_e1 = {stem(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]*", ans_c1.lower())}
        ans_stems_e2 = {stem(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]*", ans_c2.lower())}

        e1_matches_e2 = len(ans_stems_e1 & distinct_ref_e2)
        e1_matches_e1 = len(ans_stems_e1 & distinct_ref_e1)

        e2_matches_e1 = len(ans_stems_e2 & distinct_ref_e1)
        e2_matches_e2 = len(ans_stems_e2 & distinct_ref_e2)

        if (e1_matches_e2 >= 1 and e1_matches_e1 == 0) or (e2_matches_e1 >= 1 and e2_matches_e2 == 0):
            return True

    return False

# Pre-encoding texts
all_needed_texts = set()
for item in paraphrase_items:
    q_text = item["question"]
    ref_ans = item.get("referenceAnswer") or find_theory_item(q_text)["referenceAnswer"]
    all_needed_texts.add(ref_ans)
    for kp in _split_reference_key_points(ref_ans):
        all_needed_texts.add(kp)
    for k in ["good", "partial", "wrong", "reversed", "vague"]:
        ans = item["answers"][k]
        all_needed_texts.add(ans)
        for u in _split_answer_units(ans):
            all_needed_texts.add(u)

for item in _THEORY_ITEMS_LIST:
    ref = item["referenceAnswer"]
    all_needed_texts.add(ref)
    kps = _split_reference_key_points(ref)
    for kp in kps:
        all_needed_texts.add(kp)
    if kps:
        all_needed_texts.add(kps[0])
        for u in _split_answer_units(kps[0]):
            all_needed_texts.add(u)

text_list = list(all_needed_texts)
print(f"Pre-encoding {len(text_list)} texts...", flush=True)
embeddings = model.encode(text_list, batch_size=256, normalize_embeddings=True, show_progress_bar=False)
emb_map = {t: embeddings[i] for i, t in enumerate(text_list)}

def sim(t1, t2):
    e1 = emb_map.get(t1)
    e2 = emb_map.get(t2)
    if e1 is None:
        e1 = model.encode([t1], normalize_embeddings=True, show_progress_bar=False)[0]
        emb_map[t1] = e1
    if e2 is None:
        e2 = model.encode([t2], normalize_embeddings=True, show_progress_bar=False)[0]
        emb_map[t2] = e2
    return float(np.dot(e1, e2))

def evaluate_theory_v3(question: str, answer: str, reference_answer: str,
                       expected_concepts: list = None,
                       t_cover: float = THEORY_T_COVER,
                       t_partial: float = THEORY_T_PARTIAL,
                       side_cap_margin: int = THEORY_SIDE_CAP_MARGIN) -> dict:
    key_points = _split_reference_key_points(reference_answer)
    units = _split_answer_units(answer)
    clean_ans = (answer or "").strip()
    ans_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", clean_ans.lower())
    ans_stems = {stem(w) for w in ans_tokens}
    q_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", (question or "").lower())
    q_stems = {stem(w) for w in q_tokens}

    num_kp = len(key_points) or 1

    # Protected sentence split to know sentence count
    protected = re.sub(r'\b(e\.g\.|i\.e\.|etc\.|vs\.)', lambda m: m.group(0).replace('.', '__DOT__'), clean_ans, flags=re.IGNORECASE)
    ans_sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', protected) if s.strip()]
    has_multiple_sentences = len(ans_sents) >= 2

    # Preliminary per-key-point evaluation
    kp_info = []
    for kp_idx, kp in enumerate(key_points):
        anchors = _get_key_point_anchors(kp, question)
        matched_dict = match_soft_anchors(anchors, ans_tokens, ans_stems)
        matched_anchors = set(matched_dict.keys())

        best_sim = 0.0
        best_u = ""
        for u in units:
            s = sim(kp, u)
            if s > best_sim:
                best_sim = s
                best_u = u

        min_anchors = 2 if len(anchors) >= 4 else 1
        has_min = (len(matched_anchors) >= min_anchors) if anchors else True

        # Rule 1a: Whole-answer comparison may only support PARTIAL, never COVERED
        # When answer has multiple sentences, unit 0 (whole answer) can only support PARTIAL
        is_whole_answer_unit = has_multiple_sentences and (best_u == clean_ans)

        is_cov = has_min and (best_sim >= t_cover) and not is_whole_answer_unit
        is_part = not is_cov and (has_min and (best_sim >= t_partial))

        decision = "missed"
        if is_cov:
            decision = "covered"
        elif is_part:
            decision = "partial"

        # Contradiction cues (antonym + negation)
        if decision != "missed":
            cues = count_contradiction_cues(kp, best_u, matched_anchors)
            if cues >= 2:
                decision = "missed"
            elif cues >= 1:
                decision = "partial" if decision == "covered" else "missed"

        # Swapped-property check (1b)
        if decision != "missed":
            if check_swapped_properties(question, answer, reference_answer, kp):
                decision = "partial" if decision == "covered" else "missed"

        kp_info.append({
            "idx": kp_idx,
            "kp": kp,
            "anchors": anchors,
            "matched_anchors": matched_anchors,
            "matched_dict": matched_dict,
            "min_anchors": min_anchors,
            "best_sim": best_sim,
            "best_unit": best_u,
            "decision": decision
        })

    # Rule 1a: Anchor Exclusivity and Comparison Unit Constraint
    # "every key point must be supported by its OWN matched anchors;
    #  an answer sentence or window may credit at most one key point unless each credited key point
    #  has at least one distinct matched anchor not used by another credited key point."
    credited = [k for k in kp_info if k["decision"] in ("covered", "partial")]

    if len(credited) > 1:
        # Check distinct anchors for each credited key point
        # A key point's matched anchors must not be entirely shared/consumed by others
        # Prioritize key point with higher similarity
        credited.sort(key=lambda k: k["best_sim"], reverse=True)
        allocated_matched_anchors = set()
        allocated_ans_words = set()

        for k in credited:
            # Check distinct anchors not in other credited key points
            other_matched = set()
            for other in credited:
                if other is not k:
                    other_matched.update(other["matched_anchors"])
            
            own_anchors = k["matched_anchors"] - other_matched
            own_words = {w for a, w in k["matched_dict"].items() if a in own_anchors}

            # If all matched anchors are shared with other key points and has no distinct anchor of its own:
            if len(own_anchors) == 0:
                k["decision"] = "missed"
            elif len(k["matched_anchors"]) >= 4 and len(own_anchors) < 2 and len(k["matched_anchors"] - allocated_matched_anchors) < 1:
                k["decision"] = "missed"
            else:
                allocated_matched_anchors.update(k["matched_anchors"])
                allocated_ans_words.update(own_words)

    # Tally final covered and partial
    covered = 0
    partial = 0
    covered_key_points = []
    partial_key_points = []
    point_decisions = []

    for k in kp_info:
        dec = k["decision"]
        point_decisions.append(dec)
        if dec == "covered":
            covered += 1
            covered_key_points.append(k["kp"])
        elif dec == "partial":
            partial += 1
            partial_key_points.append(k["kp"])

    # 1. Correctness
    correctness = round(100.0 * (covered + 0.5 * partial) / num_kp)

    # 2. Concept coverage
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
        for c in (expected_concepts or []):
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
        if expected_concepts:
            concept_coverage = round(100.0 * (cov_c + 0.5 * part_c) / len(expected_concepts))
        else:
            concept_coverage = correctness

    concept_coverage = min(concept_coverage, correctness)

    # 3. Relevance
    cos_sim = sim(answer, reference_answer)
    relevance = round(max(0.0, min(1.0, (cos_sim - 0.20) / 0.50)) * 100.0)

    # 4. Communication
    raw_comm = compute_theory_communication(answer, key_points, question, ans_stems)

    if correctness == 0:
        relevance = 0
        correctness = 0
        concept_coverage = 0
        communication = 0
        score = 0
    else:
        relevance = min(relevance, correctness + side_cap_margin)
        communication = min(raw_comm, correctness + side_cap_margin)
        score = calculate_theory_overall(relevance, correctness, concept_coverage, communication)

    return {
        "score": score,
        "correctness": correctness,
        "relevance": relevance,
        "conceptCoverage": concept_coverage,
        "communication": communication,
        "point_decisions": point_decisions,
        "covered": covered,
        "partial": partial,
        "num_kp": num_kp
    }

print("Running test v3 on First-KP-Only across catalogue...", flush=True)
fkp_2 = []
fkp_34 = []
for item in _THEORY_ITEMS_LIST:
    q = item['questionText']
    ref = item['referenceAnswer']
    kps = _split_reference_key_points(ref)
    if not kps: continue
    res = evaluate_theory_v3(q, kps[0], ref, item.get('expectedConcepts', []))
    if len(kps) == 2:
        fkp_2.append((res['score'], item['id'], q, res))
    elif len(kps) in (3, 4):
        fkp_34.append((res['score'], item['id'], q, res))

print(f"\n2-key-point questions ({len(fkp_2)} total):")
print(f"  Min={min(x[0] for x in fkp_2)}, Avg={sum(x[0] for x in fkp_2)/len(fkp_2):.1f}, Max={max(x[0] for x in fkp_2)}")
print(f"  Target: never above 65 -> Max <= 65? {'PASS' if max(x[0] for x in fkp_2) <= 65 else 'FAIL'}")

print(f"\n3-4-key-point questions ({len(fkp_34)} total):")
print(f"  Min={min(x[0] for x in fkp_34)}, Avg={sum(x[0] for x in fkp_34)/len(fkp_34):.1f}, Max={max(x[0] for x in fkp_34)}")
print(f"  Target: back in 30-70 -> All in 30-70? {'PASS' if all(30 <= x[0] <= 70 for x in fkp_34) else 'FAIL'}")
if not all(30 <= x[0] <= 70 for x in fkp_34):
    outliers = [x for x in fkp_34 if x[0] < 30 or x[0] > 70]
    print(f"  Outliers count: {len(outliers)}")
    for s, qid, q, r in outliers[:5]:
        print(f"    [{qid}] Score={s}, cor={r['correctness']}, rel={r['relevance']}, cov={r['conceptCoverage']}, com={r['communication']}, decisions={r['point_decisions']}")
