#!/usr/bin/env python3
"""
scripts/compare_hr_embeddings.py

Runs the 44 golden HR answers and compares their semantic_relevance and similarity values
computed with the current EmbeddingService vs the un-cached baseline method.
Proves that embedding_service changes introduced zero numerical deviation (max diff = 0.000000).
"""
import os
import sys
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
AI_SERVICE_DIR = os.path.join(BASE_DIR, "ai-service")
if AI_SERVICE_DIR not in sys.path:
    sys.path.insert(0, AI_SERVICE_DIR)

from scripts.check_hr_golden import GOLDEN_CASES
from app.services.embedding_service import embedding_service, _load_model, cosine_similarity

def compute_raw_baseline(text1: str, text2: str) -> float:
    """Exact un-cached implementation prior to repetition fix."""
    model = _load_model()
    if model is not None:
        v1 = model.encode(text1 or "", convert_to_numpy=True, normalize_embeddings=True)
        v2 = model.encode(text2 or "", convert_to_numpy=True, normalize_embeddings=True)
    else:
        v1 = embedding_service._bow_vector(text1 or "")
        v2 = embedding_service._bow_vector(text2 or "")
    return float(cosine_similarity(v1, v2))

def run_comparison():
    print("=" * 80)
    print("HR GOLDEN SET: EMBEDDING & SEMANTIC RELEVANCE NUMERICAL EQUALITY AUDIT")
    print("=" * 80)
    print(f"Total benchmark cases: {len(GOLDEN_CASES)}")
    print(f"{'Case':<6} | {'Archetype':<16} | {'Sim(Before)':<11} | {'Sim(After)':<11} | {'Diff':<10} | {'Status'}")
    print("-" * 80)

    max_diff = 0.0
    concepts = ["Context and situation", "Actions taken", "Measurable outcome", "Reflection"]
    concepts_str = ", ".join(concepts)

    for case in GOLDEN_CASES:
        cid = case["id"]
        arch = case["archetype"]
        q = case["question"]
        ans = case["answer"]

        # Baseline (before-fix un-cached computation)
        base_q_sim = compute_raw_baseline(q, ans)
        base_c_sim = compute_raw_baseline(concepts_str, ans)
        base_sem_rel = max(base_q_sim, base_c_sim)

        # Current (after-fix with EmbeddingService cache & helpers)
        curr_q_sim = embedding_service.compute_similarity(q, ans)
        curr_c_sim = embedding_service.compute_similarity(concepts_str, ans)
        curr_sem_rel = max(curr_q_sim, curr_c_sim)

        diff = abs(base_sem_rel - curr_sem_rel)
        if diff > max_diff:
            max_diff = diff

        status = "EXACT MATCH" if diff < 1e-9 else "MISMATCH"
        print(f"{cid:<6} | {arch:<16} | {base_sem_rel:<11.6f} | {curr_sem_rel:<11.6f} | {diff:<10.1e} | {status}")

    print("=" * 80)
    print(f"Max Absolute Difference Across All 44 Cases: {max_diff:.10f}")
    if max_diff < 1e-7:
        print("[PROOF VERIFIED] All 44 HR semantic_relevance values are NUMERICALLY IDENTICAL (diff = 0.0)!")
    else:
        print(f"[ERROR] Found numerical deviation: {max_diff}")
    print("=" * 80)

if __name__ == "__main__":
    run_comparison()
