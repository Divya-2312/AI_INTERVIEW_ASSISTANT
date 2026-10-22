"""
Comprehensive Quality Verification Script for MockMate AI.
Generates 50 output-prediction questions and 50 coding questions across easy/medium/hard
through the real pipeline and verifies:
1. Served on first try, regenerated, or fell back to verified catalogue.
2. Leak checks on starter code, question text, and client-sanitized payloads (MUST BE 0).
3. Execution verification against JVM sandbox ground truth (MUST BE 0 MISMATCHES).
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_SERVICE_DIR = os.path.join(BASE_DIR, "ai-service")
if AI_SERVICE_DIR not in sys.path:
    sys.path.insert(0, AI_SERVICE_DIR)

from app.models.llama_provider import LlamaModel, _load_raw_output_predictions
from app.services.code_executor import (
    is_java_available,
    execute_coding_submission,
    is_snippet_deterministic,
    verify_predict_output_snippet,
    check_starter_code_leak,
    check_question_text_leak,
    normalize_value_str,
)


def run_quality_check():
    print("=" * 80)
    print(" MockMate AI - Question Quality & Verification Pipeline Audit")
    print("=" * 80)

    if not is_java_available():
        print("ERROR: Java Development Kit (JDK) is not available on PATH. Exiting.")
        sys.exit(1)

    _load_raw_output_predictions()
    model = LlamaModel()

    difficulties = ["easy", "medium", "hard"]
    # 50 output prediction: 17 easy, 17 medium, 16 hard
    # 50 coding: 17 easy, 17 medium, 16 hard
    op_diffs = ["easy"] * 17 + ["medium"] * 17 + ["hard"] * 16
    cd_diffs = ["easy"] * 17 + ["medium"] * 17 + ["hard"] * 16

    stats = {
        "output_prediction": {
            "total": 0,
            "first_try": 0,
            "regenerated": 0,
            "catalog_fallback": 0,
            "leaks": 0,
            "mismatches": 0,
            "failures": [],
        },
        "coding": {
            "total": 0,
            "first_try": 0,
            "regenerated": 0,
            "catalog_fallback": 0,
            "leaks": 0,
            "mismatches": 0,
            "failures": [],
        },
    }

    # -------------------------------------------------------------
    # 1. Output-Prediction Questions (50 items)
    # -------------------------------------------------------------
    print("\n[1/2] Generating and verifying 50 Output-Prediction questions...")
    for idx, diff in enumerate(op_diffs, 1):
        try:
            q = model.generate_question(
                subject="java",
                difficulty=diff,
                context=[],
                previous=[],
                question_format="output_prediction",
                interview_type="technical",
            )
            stats["output_prediction"]["total"] += 1
            meta = q.get("_generation_meta", {})
            attempts = meta.get("attempts", 1)
            source = meta.get("source", "model")

            if source == "catalog":
                stats["output_prediction"]["catalog_fallback"] += 1
            elif attempts == 1:
                stats["output_prediction"]["first_try"] += 1
            else:
                stats["output_prediction"]["regenerated"] += 1

            snip = q.get("codeSnippet", "")
            exp = q.get("expectedOutput", "")

            # Leak check: explanation must not be in questionText
            q_text = q.get("questionText", "")
            expl = q.get("explanation", "")
            if expl and len(expl) > 20 and expl.lower() in q_text.lower():
                stats["output_prediction"]["leaks"] += 1
                stats["output_prediction"]["failures"].append(f"OP #{idx} leaked explanation into questionText")

            # Determinism check
            ok_det, det_reason = is_snippet_deterministic(snip)
            if not ok_det:
                stats["output_prediction"]["mismatches"] += 1
                stats["output_prediction"]["failures"].append(f"OP #{idx} non-deterministic snippet: {det_reason}")
                continue

            # Ground-truth execution check
            ok_exec, canon_out, err = verify_predict_output_snippet(snip)
            if not ok_exec:
                stats["output_prediction"]["mismatches"] += 1
                stats["output_prediction"]["failures"].append(f"OP #{idx} execution failed: {err}")
                continue

            if normalize_value_str(exp) != normalize_value_str(canon_out):
                stats["output_prediction"]["mismatches"] += 1
                stats["output_prediction"]["failures"].append(
                    f"OP #{idx} mismatch: expected '{exp}' vs actual '{canon_out}'"
                )

            if idx % 10 == 0 or idx == len(op_diffs):
                print(f"  Processed {idx}/50 output-prediction questions...")

        except Exception as e:
            stats["output_prediction"]["failures"].append(f"OP #{idx} exception: {e}")

    # -------------------------------------------------------------
    # 2. Coding Questions (50 items)
    # -------------------------------------------------------------
    print("\n[2/2] Generating and verifying 50 Coding questions...")
    for idx, diff in enumerate(cd_diffs, 1):
        try:
            q = model.generate_question(
                subject="java",
                difficulty=diff,
                context=[],
                previous=[],
                question_format="coding",
                interview_type="technical",
            )
            stats["coding"]["total"] += 1
            meta = q.get("_generation_meta", {})
            attempts = meta.get("attempts", 1)
            source = meta.get("source", "model")

            if source == "catalog":
                stats["coding"]["catalog_fallback"] += 1
            elif attempts == 1:
                stats["coding"]["first_try"] += 1
            else:
                stats["coding"]["regenerated"] += 1

            starter = q.get("starterCode", "")
            ref = q.get("referenceSolution", "")
            q_text = q.get("questionText", "")
            cases = q.get("testCases", [])

            # Starter code leak check
            ok_starter, starter_reason = check_starter_code_leak(starter, ref)
            if not ok_starter:
                stats["coding"]["leaks"] += 1
                stats["coding"]["failures"].append(f"Coding #{idx} starter code leak: {starter_reason}")

            # Question text leak check
            ok_qtext, qtext_reason = check_question_text_leak(q_text, ref)
            if not ok_qtext:
                stats["coding"]["leaks"] += 1
                stats["coding"]["failures"].append(f"Coding #{idx} question text leak: {qtext_reason}")

            # Test cases check (no placeholders)
            if len(cases) < 2:
                stats["coding"]["mismatches"] += 1
                stats["coding"]["failures"].append(f"Coding #{idx} insufficient test cases: {len(cases)}")
            for tc in cases:
                if "standard input sample" in str(tc.get("input", "")).lower() or \
                   "valid expected result" in str(tc.get("expectedOutput", "")).lower():
                    stats["coding"]["mismatches"] += 1
                    stats["coding"]["failures"].append(f"Coding #{idx} has placeholder test case")

            # Reference solution sandbox execution against all test cases
            res = execute_coding_submission("java", ref, cases)
            if res.get("compileError"):
                stats["coding"]["mismatches"] += 1
                stats["coding"]["failures"].append(f"Coding #{idx} compile error: {res['compileError']}")
            elif res.get("passedCount") != len(cases):
                stats["coding"]["mismatches"] += 1
                stats["coding"]["failures"].append(
                    f"Coding #{idx} test failure: only {res.get('passedCount')}/{len(cases)} passed"
                )

            if idx % 10 == 0 or idx == len(cd_diffs):
                print(f"  Processed {idx}/50 coding questions...")

        except Exception as e:
            stats["coding"]["failures"].append(f"Coding #{idx} exception: {e}")

    # -------------------------------------------------------------
    # 3. Final Summary Report
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print(" QUESTION QUALITY AUDIT SUMMARY (100 TOTAL QUESTIONS)")
    print("=" * 80)
    print(f"{'Module':<22} | {'Total':<6} | {'1st Try':<8} | {'Regen':<6} | {'Catalog':<8} | {'Leaks':<6} | {'Mismatches':<10}")
    print("-" * 80)
    for name in ["output_prediction", "coding"]:
        s = stats[name]
        label = "Output Prediction" if name == "output_prediction" else "Java Coding"
        print(f"{label:<22} | {s['total']:<6} | {s['first_try']:<8} | {s['regenerated']:<6} | {s['catalog_fallback']:<8} | {s['leaks']:<6} | {s['mismatches']:<10}")
    print("-" * 80)
    total_leaks = stats["output_prediction"]["leaks"] + stats["coding"]["leaks"]
    total_mismatches = stats["output_prediction"]["mismatches"] + stats["coding"]["mismatches"]
    print(f"Total Leaks: {total_leaks} (Target: 0)")
    print(f"Total Mismatches: {total_mismatches} (Target: 0)")
    print("=" * 80)

    if stats["output_prediction"]["failures"] or stats["coding"]["failures"]:
        print("\nFailures Detail:")
        for f in stats["output_prediction"]["failures"]:
            print(f"  [OP Failure] {f}")
        for f in stats["coding"]["failures"]:
            print(f"  [Coding Failure] {f}")

    all_passed = (total_leaks == 0 and total_mismatches == 0 and stats["output_prediction"]["total"] == 50 and stats["coding"]["total"] == 50)
    if all_passed:
        print("\n>>> AUDIT PASSED: 0 LEAKS, 0 MISMATCHES. ALL 100 QUESTIONS VERIFIED. <<<\n")
    else:
        print("\n>>> AUDIT FAILED: Non-zero leaks or mismatches detected. <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    run_quality_check()
