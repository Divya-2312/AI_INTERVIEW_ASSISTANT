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

# Load paraphrase items
with open("ai-service/tests/data/paraphrase_answers.json", "r", encoding="utf-8") as f:
    paraphrase_items = json.load(f)

# Load contradiction pairs
with open("ai-service/app/data/contradiction_pairs.json", "r", encoding="utf-8") as f:
    CONTRADICTION_PAIRS = json.load(f)

model = _load_model()

# Word embedding cache for soft anchor matching
WORD_EMB_CACHE = {}

def get_word_embedding(w: str):
    w_clean = w.lower().strip()
    if w_clean not in WORD_EMB_CACHE:
        emb = model.encode([w_clean], normalize_embeddings=True, show_progress_bar=False)[0]
        WORD_EMB_CACHE[w_clean] = emb
    return WORD_EMB_CACHE[w_clean]

def compute_word_sim(w1: str, w2: str) -> float:
    e1 = get_word_embedding(w1)
    e2 = get_word_embedding(w2)
    return float(np.dot(e1, e2))

def match_soft_anchors(anchors: set, ans_tokens: list, ans_stems: set) -> set:
    matched = set()
    # Filter answer content words
    ans_content_words = [w for w in ans_tokens if len(w) >= 3 and w not in STOP]
    for a in anchors:
        if a in ans_stems:
            matched.add(a)
            continue
        # Check cosine to answer content words
        for w in ans_content_words:
            if compute_word_sim(w, a) >= 0.60:
                matched.add(a)
                break
    return matched

# Pre-encode all units and KPs for fast similarity
all_texts = set()
for item in paraphrase_items:
    q_text = item["question"]
    ref_ans = item.get("referenceAnswer")
    if not ref_ans:
        cat_item = find_theory_item(q_text)
        ref_ans = cat_item["referenceAnswer"]
    all_texts.add(ref_ans)
    for kp in _split_reference_key_points(ref_ans):
        all_texts.add(kp)
    for k in ["good", "partial", "wrong", "reversed", "vague"]:
        ans = item["answers"][k]
        all_texts.add(ans)
        for u in _split_answer_units(ans):
            all_texts.add(u)

text_list = list(all_texts)
embeddings = model.encode(text_list, batch_size=256, normalize_embeddings=True, show_progress_bar=False)
emb_map = {t: embeddings[i] for i, t in enumerate(text_list)}

def fast_sim(t1, t2):
    e1 = emb_map.get(t1)
    e2 = emb_map.get(t2)
    if e1 is None:
        e1 = model.encode([t1], normalize_embeddings=True, show_progress_bar=False)[0]
        emb_map[t1] = e1
    if e2 is None:
        e2 = model.encode([t2], normalize_embeddings=True, show_progress_bar=False)[0]
        emb_map[t2] = e2
    return float(np.dot(e1, e2))

print("Pre-encoding done. Now testing soft anchors and lowest 5 good answers...", flush=True)

# Find current lowest 5 good answers
from app.models.llama_provider import _evaluate_theory_with_rubric

class FastEmbService:
    def compute_similarity(self, t1, t2):
        return fast_sim(t1, t2)

fast_emb = FastEmbService()

old_good = []
for item in paraphrase_items:
    q_text = item["question"]
    ref_ans = item.get("referenceAnswer")
    concepts = item.get("expectedConcepts")
    if not ref_ans:
        cat_item = find_theory_item(q_text)
        ref_ans = cat_item["referenceAnswer"]
        concepts = cat_item.get("expectedConcepts", [])
    ans_text = item["answers"]["good"]
    res = _evaluate_theory_with_rubric(q_text, ans_text, ref_ans, fast_emb, concepts)
    old_good.append((res["score"], item["questionId"], q_text, ans_text, res))

old_good.sort(key=lambda x: x[0])
print("\n--- Current Lowest 5 Good Answers ---", flush=True)
for s, qid, q, a, res in old_good[:5]:
    print(f"[{qid}] Old Score: {s} (cor={res['correctness']}, rel={res['relevance']}, cov={res['conceptCoverage']}, com={res['communication']})")
    print(f"  Q: {q}")
    print(f"  Ans: {a}")
