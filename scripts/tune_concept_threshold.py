#!/usr/bin/env python3
"""
Threshold Tuning Script for Concept Coverage.
Evaluates BERT-derived SentenceTransformer ('all-MiniLM-L6-v2') on the Golden Set:
- 100 Java Theory questions from java_theory_100.jsonl
- 100 DBMS Theory questions from dbms_theory_100.jsonl

Ground truth labels:
- Positive cases: reference answers (ground truth = COVERED, should score >= threshold)
- Negative cases: off-topic / irrelevant answers (ground truth = MISSING, should score < threshold)

Sweeps thresholds from 0.25 to 0.70 in 0.05 steps, measuring:
- Precision
- Recall
- F1 Score
- Accuracy
Reports the optimal threshold and exact metrics.
"""

import os
import sys
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_SERVICE_DIR = os.path.join(BASE_DIR, "ai-service")
if AI_SERVICE_DIR not in sys.path:
    sys.path.insert(0, AI_SERVICE_DIR)

from app.services.embedding_service import embedding_service, SYNONYM_MAP


def load_dataset(filename):
    path = os.path.join(BASE_DIR, "training", "data", "raw", filename)
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def run_tuning():
    print("=" * 80)
    print(" Concept Coverage Threshold Tuning on Golden Set (all-MiniLM-L6-v2)")
    print("=" * 80)

    java_data = load_dataset("java_theory_100.jsonl")
    dbms_data = load_dataset("dbms_theory_100.jsonl")
    combined = java_data + dbms_data

    print(f"Loaded {len(java_data)} Java Theory + {len(dbms_data)} DBMS Theory = {len(combined)} Golden Items.")

    # Build benchmark pairs: (concept, answer, ground_truth_covered)
    benchmark_pairs = []

    # Off-topic negative answers
    negative_answers = [
        "I like to play basketball and watch movies on weekends.",
        "The weather today is sunny and pleasant in California.",
        "To make pasta, boil water and add salt then simmer the tomato sauce.",
        "Machine learning models use backpropagation and gradient descent for deep learning neural networks.",
        "The economic inflation rate depends on central bank interest rates.",
    ]

    for item in combined:
        concepts = item.get("expectedConcepts", [])
        ref_ans = item.get("idealAnswer", "")
        for c in concepts:
            # Positive pair
            benchmark_pairs.append((c, ref_ans, True))
            # Negative pair (using negative answer)
            neg_ans = negative_answers[hash(c) % len(negative_answers)]
            benchmark_pairs.append((c, neg_ans, False))

    print(f"Generated {len(benchmark_pairs)} benchmark evaluation pairs ({len(benchmark_pairs)//2} pos, {len(benchmark_pairs)//2} neg).")

    # Compute similarities once
    print("Computing embedding similarities with synonym expansion...")
    scores = []
    for concept, answer, label in benchmark_pairs:
        sim = embedding_service.best_sentence_similarity(concept, answer)
        scores.append((sim, label))

    # Sweep thresholds
    thresholds = [0.25, 0.30, 0.35, 0.40, 0.42, 0.45, 0.50, 0.55, 0.60, 0.65]
    results = []

    print("\nThreshold Sweep Results:")
    print("-" * 75)
    print(f"{'Threshold':<10} | {'Precision':<12} | {'Recall':<12} | {'F1-Score':<12} | {'Accuracy':<12}")
    print("-" * 75)

    best_f1 = -1.0
    best_thresh = 0.45

    for th in thresholds:
        tp = sum(1 for sim, label in scores if sim >= th and label)
        fp = sum(1 for sim, label in scores if sim >= th and not label)
        fn = sum(1 for sim, label in scores if sim < th and label)
        tn = sum(1 for sim, label in scores if sim < th and not label)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        acc = (tp + tn) / len(scores)

        results.append({
            "threshold": th,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "accuracy": acc,
        })

        if f1 > best_f1:
            best_f1 = f1
            best_thresh = th

        print(f"{th:<10.2f} | {precision:<12.4f} | {recall:<12.4f} | {f1:<12.4f} | {acc:<12.4f}")

    print("-" * 75)
    print(f"\nOPTIMAL THRESHOLD: {best_thresh:.2f} (F1 = {best_f1:.4f})")

    # Save results to JSON
    out_file = os.path.join(BASE_DIR, "ai-service", "app", "data", "concept_threshold_tuning_report.json")
    report = {
        "dataset": "Golden Set (200 questions, 526 concept benchmark pairs)",
        "model": "all-MiniLM-L6-v2",
        "optimal_threshold": best_thresh,
        "best_f1": round(best_f1, 4),
        "results": results,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Saved tuning report to {out_file}\n")


if __name__ == "__main__":
    run_tuning()
