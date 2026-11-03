"""
run_validation_cases.py
Executes the 60 validation cases from verification_runs/validation_cases.json
against the running AI evaluation service (http://localhost:8000/api/ai/evaluate-answer).
Evaluates pass/fail decisions against pass mark = 50, computes the confusion matrix,
precision, recall, F1, and accuracy per module and overall, and saves results to
verification_runs/validation_results.json.
"""

import os
import sys
import json
import time
import requests

EVAL_URL = "http://localhost:8000/api/ai/evaluate-answer"
PASS_MARK = 50
CASES_FILE = os.path.join(os.path.dirname(__file__), "validation_cases.json")
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "validation_results.json")


def run_validation():
    print("=" * 80)
    print("RUNNING 60 VALIDATION CASES (SELF-TEST)")
    print("=" * 80)

    if not os.path.exists(CASES_FILE):
        print(f"Error: Cases file not found: {CASES_FILE}")
        sys.exit(1)

    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"Loaded {len(cases)} cases from {CASES_FILE}")

    results = []
    start_all = time.time()

    for idx, case in enumerate(cases, 1):
        cid = case["id"]
        mod = case["module"]
        name = case.get("name", cid)
        exp_pass = case["expected_pass"]
        payload = case["payload"]

        t0 = time.time()
        try:
            r = requests.post(EVAL_URL, json=payload, timeout=60)
            elapsed = time.time() - t0
            data = r.json()
            score = data.get("score")
            if score is None:
                score = 0
            model_used = data.get("modelUsed")
            actual_pass = (score >= PASS_MARK)
            decision_match = (actual_pass == exp_pass)

            res_entry = {
                "id": cid,
                "module": mod,
                "name": name,
                "expected_pass": exp_pass,
                "actual_pass": actual_pass,
                "score": score,
                "modelUsed": model_used,
                "time_sec": round(elapsed, 2),
                "isIrrelevant": data.get("isIrrelevant"),
                "formula": data.get("formula"),
                "conceptCoverage": data.get("conceptCoverage"),
                "correctness": data.get("correctness"),
                "relevance": data.get("relevance"),
                "accuracy": data.get("accuracy"),
                "communication": data.get("communication"),
                "decision_match": decision_match,
            }
            results.append(res_entry)

            status_str = "MATCH" if decision_match else "MISMATCH"
            print(f"[{idx:02d}/60] {cid:<14} | {mod:<18} | Exp: {str(exp_pass):<5} | Score: {score:>3} ({str(actual_pass):<5}) | {status_str} in {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"[{idx:02d}/60] {cid:<14} | ERROR in {elapsed:.2f}s: {e}")
            results.append({
                "id": cid,
                "module": mod,
                "name": name,
                "expected_pass": exp_pass,
                "actual_pass": False,
                "score": 0,
                "error": str(e),
                "decision_match": False,
                "time_sec": round(elapsed, 2),
            })

    total_time = time.time() - start_all
    print(f"\nAll 60 cases completed in {total_time:.2f}s.")

    # Save validation results
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved results to {RESULTS_FILE}")

    # Compute Confusion Matrix per Module and Overall
    modules = [
        "dbms_theory",
        "java_theory",
        "hr",
        "java_coding",
        "sql",
        "output_prediction",
        "mixed_subtotal",
        "OVERALL SYSTEM",
    ]

    print("\n" + "=" * 115)
    print(f"{'Module (self-test)':<22} | {'Cases':<5} | {'TP':<4} {'FP':<4} {'TN':<4} {'FN':<4} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10} | {'Accuracy':<10}")
    print("-" * 115)

    summary_table = {}

    for mod in modules:
        if mod == "OVERALL SYSTEM":
            subset = results
        elif mod == "mixed_subtotal":
            subset = [r for r in results if r["module"] in ("java_coding", "sql", "output_prediction")]
        else:
            subset = [r for r in results if r["module"] == mod]

        total = len(subset)
        if total == 0:
            continue

        tp = sum(1 for r in subset if r["expected_pass"] and r["actual_pass"])
        fp = sum(1 for r in subset if not r["expected_pass"] and r["actual_pass"])
        tn = sum(1 for r in subset if not r["expected_pass"] and not r["actual_pass"])
        fn = sum(1 for r in subset if r["expected_pass"] and not r["actual_pass"])

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        accuracy = ((tp + tn) / total) if total > 0 else 0.0

        label = mod.replace("_", " ").title() if mod not in ("OVERALL SYSTEM", "mixed_subtotal") else (
            "Mixed Subtotal" if mod == "mixed_subtotal" else "OVERALL SYSTEM"
        )
        print(f"{label:<22} | {total:<5} | {tp:<4} {fp:<4} {tn:<4} {fn:<4} | {precision*100:>8.1f}%  | {recall*100:>8.1f}%  | {f1*100:>8.1f}%  | {accuracy*100:>8.1f}%")

        summary_table[mod] = {
            "total": total,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "precision": round(precision * 100, 1),
            "recall": round(recall * 100, 1),
            "f1": round(f1 * 100, 1),
            "accuracy": round(accuracy * 100, 1),
        }

    print("=" * 115)

    # Detailed Wrong Decisions
    mismatches = [r for r in results if not r["decision_match"]]
    print(f"\nTotal Wrong Decisions (Mismatches against pass mark 50): {len(mismatches)}")
    for m in mismatches:
        print(f"  - {m['id']} ({m['module']}): Exp Pass={m['expected_pass']}, Actual Score={m['score']} (Pass={m['actual_pass']}), Model={m.get('modelUsed')}")

    return results, summary_table


if __name__ == "__main__":
    run_validation()
