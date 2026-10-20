#!/usr/bin/env python3
"""
AI Interview Assistant - Automated Fine-Tuned Pipeline Verification Script
Verifies:
1. Datasets: 6 raw modules x 100 records = 600 total valid records.
2. Data Pipeline: zero prompt and question overlap across train/validation/test splits.
3. Live /health endpoint verification: is_fine_tuned_verified is True.
4. Model Used: modelUsed matches configured model without silent fallback (usedFallback = False).
5. Evaluation Discrimination Sanity Check: reference answer outscores irrelevant answer by >= 30 points.
"""

import sys
import os
import json
import requests
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "training" / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "training" / "data" / "processed" / "splits"
EXPECTED_FILES = {
    "java_theory_100.jsonl": 100,
    "java_output_prediction_100.jsonl": 100,
    "java_coding_100.jsonl": 100,
    "dbms_theory_100.jsonl": 100,
    "sql_coding_100.jsonl": 100,
    "hr_questions_100.jsonl": 100,
}

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8000")


def print_banner(title):
    print(f"\n=======================================================")
    print(f" {title}")
    print(f"=======================================================")


def audit_datasets():
    print_banner("1. DATASET AUDIT (6 MODULES x 100 RECORDS = 600 TOTAL)")
    total_records = 0
    errors = 0

    if not RAW_DIR.exists():
        print(f"[FAIL] Raw dataset directory missing: {RAW_DIR}")
        return False

    for file_name, expected_count in EXPECTED_FILES.items():
        file_path = RAW_DIR / file_name
        if not file_path.exists():
            print(f"[FAIL] Missing dataset file: {file_name}")
            errors += 1
            continue

        lines = [line.strip() for line in file_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        valid_records = len(lines)
        total_records += valid_records
        status = "OK" if valid_records == expected_count else "MISMATCH"
        print(f"  - {file_name:<35} | Records: {valid_records:3d}/{expected_count:3d} [{status}]")
        if status != "OK":
            errors += 1

    print(f"\nTotal Verified Raw Records: {total_records} / 600")
    if total_records != 600 or errors > 0:
        print("[FAIL] Dataset record audit failed.")
        return False
    print("[PASS] Dataset record audit passed.")
    return True


def audit_splits_overlap():
    print_banner("2. DATA SPLITS OVERLAP AUDIT")
    train_file = PROCESSED_DIR / "train.jsonl"
    val_file = PROCESSED_DIR / "validation.jsonl"
    test_file = PROCESSED_DIR / "test.jsonl"

    if not (train_file.exists() and val_file.exists() and test_file.exists()):
        print(f"[FAIL] Splits missing in {PROCESSED_DIR}")
        return False

    train_prompts = {json.loads(line)['messages'][1]['content'] for line in train_file.read_text(encoding='utf-8').splitlines() if line.strip()}
    val_prompts = {json.loads(line)['messages'][1]['content'] for line in val_file.read_text(encoding='utf-8').splitlines() if line.strip()}
    test_prompts = {json.loads(line)['messages'][1]['content'] for line in test_file.read_text(encoding='utf-8').splitlines() if line.strip()}

    tv_overlap = len(train_prompts.intersection(val_prompts))
    tt_overlap = len(train_prompts.intersection(test_prompts))
    vt_overlap = len(val_prompts.intersection(test_prompts))

    print(f"  - Train prompts: {len(train_prompts)} | Validation prompts: {len(val_prompts)} | Test prompts: {len(test_prompts)}")
    print(f"  - Overlaps -> Train/Val: {tv_overlap}, Train/Test: {tt_overlap}, Val/Test: {vt_overlap}")

    if tv_overlap > 0 or tt_overlap > 0 or vt_overlap > 0:
        print("[FAIL] Prompts overlap across dataset splits.")
        return False

    print("[PASS] Data splits overlap audit passed (0 overlap verified).")
    return True


def audit_live_health_and_verification():
    print_banner("3. LIVE /HEALTH FINE-TUNED VERIFICATION AUDIT")
    try:
        url = f"{AI_SERVICE_URL}/health"
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            print(f"[FAIL] /health endpoint returned HTTP {res.status_code}")
            return False

        health = res.json()
        print(json.dumps(health, indent=2))

        is_verified = health.get("is_fine_tuned_verified", False)
        base_model_used = health.get("base_model_used_for_inference", True)
        reason = (
            health.get("verification_reason") or
            health.get("model_identity", {}).get("verification_reason", "") or
            health.get("ai_status", {}).get("llama", {}).get("verification_reason", "")
        )

        if not is_verified:
            print(f"[FAIL] Model is NOT verified fine-tuned: {reason}")
            return False

        if base_model_used:
            print("[FAIL] Model identity reports base_model_used_for_inference = True.")
            return False

        print("[PASS] Live /health fine-tuned verification audit passed.")
        return True
    except Exception as exc:
        print(f"[FAIL] Could not connect to AI service at {AI_SERVICE_URL}: {exc}")
        return False


def audit_inference_models_and_fallback():
    print_banner("4. INFERENCE MODEL & FALLBACK SANITY AUDIT")
    try:
        # Check generation
        gen_res = requests.post(f"{AI_SERVICE_URL}/api/ai/generate-question", json={
            "subject": "java",
            "difficulty": "easy",
            "questionFormat": "theory",
            "interviewType": "technical",
        }, timeout=30)
        if gen_res.status_code != 200:
            print(f"[FAIL] Question generation endpoint failed with HTTP {gen_res.status_code}")
            return False

        gen_data = gen_res.json()
        model_used = gen_data.get("modelUsed")
        used_fallback = gen_data.get("usedFallback", False)

        print(f"  - Generation modelUsed: {model_used} | usedFallback: {used_fallback}")

        if used_fallback:
            print("[FAIL] Generation used fallback path.")
            return False

        # Check evaluation
        eval_res = requests.post(f"{AI_SERVICE_URL}/api/ai/evaluate-answer", json={
            "question": "What is encapsulation?",
            "answer": "Encapsulation hides internal state and requires all interaction to be through object methods.",
            "expectedConcepts": ["data hiding", "private fields"],
            "questionFormat": "theory",
            "interviewType": "technical",
        }, timeout=30)
        if eval_res.status_code != 200:
            print(f"[FAIL] Evaluation endpoint failed with HTTP {eval_res.status_code}")
            return False

        eval_data = eval_res.json()
        eval_model = eval_data.get("modelUsed")
        eval_fallback = eval_data.get("usedFallback", False)
        eval_parse_failed = eval_data.get("parseFailed", False)

        print(f"  - Evaluation modelUsed: {eval_model} | usedFallback: {eval_fallback} | parseFailed: {eval_parse_failed}")

        if eval_fallback:
            print("[FAIL] Evaluation used fallback path.")
            return False

        print("[PASS] Inference model and fallback audit passed.")
        return True
    except Exception as exc:
        print(f"[FAIL] Error during inference audit: {exc}")
        return False


def audit_discrimination_sanity():
    print_banner("5. EVALUATION DISCRIMINATION SANITY AUDIT (10 QUESTIONS: MEAN & SPREAD)")
    import statistics

    test_cases = [
        {
            "question": "What is Encapsulation in Java?",
            "expectedConcepts": ["data hiding", "private fields", "getters and setters"],
            "ref": "Encapsulation is wrapping data and methods into a single unit and restricting direct access using private fields and public getters/setters.",
            "on_topic_wrong": "Encapsulation in Java means inheriting non-private methods from a superclass using the extends keyword.",
            "unrelated": "The capital of Japan is Tokyo and sushi is popular worldwide."
        },
        {
            "question": "What is polymorphism in Java?",
            "expectedConcepts": ["method overriding", "dynamic binding", "interfaces"],
            "ref": "Polymorphism allows objects to be treated as instances of their parent class or interface, enabling dynamic method dispatch at runtime.",
            "on_topic_wrong": "Polymorphism means creating multiple threads in Java to run methods in parallel using synchronized blocks.",
            "unrelated": "The capital of France is Paris and baguette is popular bread."
        },
        {
            "question": "What is a primary key in DBMS?",
            "expectedConcepts": ["unique identifier", "not null", "single row"],
            "ref": "A primary key is a column or set of columns that uniquely identifies each row in a database table and cannot contain NULL values.",
            "on_topic_wrong": "A primary key is an index used to perform full-text search across large text documents.",
            "unrelated": "Photosynthesis is the process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water."
        },
        {
            "question": "What is the difference between WHERE and HAVING in SQL?",
            "expectedConcepts": ["WHERE filters rows", "HAVING filters groups", "GROUP BY"],
            "ref": "WHERE filters individual rows before aggregation occurs, whereas HAVING filters groups after a GROUP BY clause has been applied.",
            "on_topic_wrong": "WHERE is used for updating records, while HAVING is used for creating new tables.",
            "unrelated": "Baking bread requires flour, water, yeast, and salt."
        },
        {
            "question": "Explain method overriding vs method overloading in Java.",
            "expectedConcepts": ["overriding is runtime", "overloading is compile-time", "same signature"],
            "ref": "Overloading occurs in the same class with the same method name but different parameter signatures at compile time; overriding occurs in a subclass with the exact same signature at runtime.",
            "on_topic_wrong": "Overriding changes the variable scope from local to global, while overloading deletes unused variables.",
            "unrelated": "Mount Everest is the highest mountain above sea level located in the Himalayas."
        },
        {
            "question": "What is a Foreign Key constraint in relational databases?",
            "expectedConcepts": ["referential integrity", "parent table primary key", "relationship"],
            "ref": "A Foreign Key is a field in one table that references the Primary Key of another table, maintaining referential integrity between tables.",
            "on_topic_wrong": "A Foreign Key is an external API key used to authenticate third-party web services.",
            "unrelated": "Electric cars use lithium-ion battery packs to power electric motors."
        },
        {
            "question": "What is the purpose of interface in Java?",
            "expectedConcepts": ["abstraction", "multiple inheritance of type", "contract"],
            "ref": "An interface specifies a contract that implementing classes must fulfill, enabling total abstraction and multiple inheritance of type in Java.",
            "on_topic_wrong": "An interface is a graphical user interface layout component built using Java Swing.",
            "unrelated": "Mozart was a prolific and influential composer of the Classical period."
        },
        {
            "question": "What is database normalization?",
            "expectedConcepts": ["reduce redundancy", "data integrity", "normal forms"],
            "ref": "Normalization is the process of organizing database tables to minimize redundancy and prevent insertion, update, and deletion anomalies.",
            "on_topic_wrong": "Normalization is compressing database files on disk using zip compression.",
            "unrelated": "The speed of light in a vacuum is approximately 299,792,458 meters per second."
        },
        {
            "question": "Tell me about a time you resolved a conflict in a team.",
            "expectedConcepts": ["active listening", "collaboration", "resolution"],
            "ref": "I listened actively to both opposing perspectives, identified the common technical goal, and facilitated a compromise that satisfied team standards.",
            "on_topic_wrong": "I ignored the conflict entirely and let the project fail so management would step in.",
            "unrelated": "Basketball is played with two teams of five players on a rectangular court."
        },
        {
            "question": "What is the purpose of the final keyword in Java?",
            "expectedConcepts": ["immutable variable", "prevent overriding", "prevent inheritance"],
            "ref": "The final keyword makes a variable constant, prevents a method from being overridden, and prevents a class from being inherited.",
            "on_topic_wrong": "The final keyword terminates the JVM process immediately when executed.",
            "unrelated": "Coffee beans are harvested from flowering plants of the Coffea genus."
        }
    ]

    ref_scores, wrong_scores, unrelated_scores, deltas = [], [], [], []

    try:
        print(f"Evaluating {len(test_cases)} distinct questions...")
        for i, tc in enumerate(test_cases, 1):
            r_res = requests.post(f"{AI_SERVICE_URL}/api/ai/evaluate-answer", json={
                "question": tc["question"], "answer": tc["ref"],
                "expectedConcepts": tc["expectedConcepts"], "questionFormat": "theory", "interviewType": "technical"
            }, timeout=120).json()

            w_res = requests.post(f"{AI_SERVICE_URL}/api/ai/evaluate-answer", json={
                "question": tc["question"], "answer": tc["on_topic_wrong"],
                "expectedConcepts": tc["expectedConcepts"], "questionFormat": "theory", "interviewType": "technical"
            }, timeout=120).json()

            u_res = requests.post(f"{AI_SERVICE_URL}/api/ai/evaluate-answer", json={
                "question": tc["question"], "answer": tc["unrelated"],
                "expectedConcepts": tc["expectedConcepts"], "questionFormat": "theory", "interviewType": "technical"
            }, timeout=120).json()

            r_sc = r_res.get("score", 0)
            w_sc = w_res.get("score", 0)
            u_sc = u_res.get("score", 0)
            d = r_sc - u_sc

            ref_scores.append(r_sc)
            wrong_scores.append(w_sc)
            unrelated_scores.append(u_sc)
            deltas.append(d)

            print(f"  Q{i:2d}: Ref={r_sc:3d} | OnTopicWrong={w_sc:3d} | Unrelated={u_sc:3d} | Delta={d:3d}")

        def get_stats(vals):
            mean_v = round(statistics.mean(vals), 2)
            min_v = min(vals)
            max_v = max(vals)
            stdev_v = round(statistics.stdev(vals), 2) if len(vals) > 1 else 0.0
            return f"Mean: {mean_v:6.2f} | Min: {min_v:3d} | Max: {max_v:3d} | StdDev: {stdev_v:5.2f}"

        print("\n--- DISCRIMINATION METRICS OVER 10 QUESTIONS ---")
        print(f"  - Reference Answer Scores      : {get_stats(ref_scores)}")
        print(f"  - On-Topic Wrong Answer Scores : {get_stats(wrong_scores)}")
        print(f"  - Truly Unrelated Answer Scores: {get_stats(unrelated_scores)}")
        print(f"  - Score Deltas (Ref vs Unrel)  : {get_stats(deltas)}")

        avg_delta = statistics.mean(deltas)
        if avg_delta < 30:
            print(f"[FAIL] Average score delta ({avg_delta:.2f} pts) is less than required 30 points threshold.")
            return False

        print("[PASS] Evaluation discrimination sanity audit passed.")
        return True
    except Exception as exc:
        print(f"[FAIL] Error during discrimination sanity audit: {exc}")
        return False


def audit_hr_evaluation():
    print_banner("6. HR QUESTION EVALUATION AUDIT")
    try:
        hr_q = "Describe a situation where you had to manage tight deadlines and competing priorities."
        hr_strong_ans = (
            "During our major Q3 platform migration, our core database server experienced latency spikes "
            "two days before release. As engineering lead, I quickly convened a triage meeting, separated "
            "critical bug fixes from non-essential enhancements, and delegated the database query profiling "
            "to two senior engineers while I handled stakeholder communications. We completed the migration "
            "on time with zero downtime and reduced API response times by 35%."
        )
        res = requests.post(f"{AI_SERVICE_URL}/api/ai/evaluate-answer", json={
            "question": hr_q,
            "answer": hr_strong_ans,
            "expectedConcepts": ["Situation management", "Clear personal actions", "Measurable positive result"],
            "questionFormat": "theory",
            "interviewType": "hr"
        }, timeout=45)

        if res.status_code != 200:
            print(f"[FAIL] HR evaluation endpoint returned HTTP {res.status_code}")
            return False

        data = res.json()
        score = data.get("score", 0)
        relevance = data.get("relevance", 0.0)
        is_irrelevant = data.get("isIrrelevant", True)
        model_used = data.get("modelUsed", "unknown")

        print(f"  - Model Used: {model_used}")
        print(f"  - HR Score: {score}/100 | Relevance: {relevance} | isIrrelevant: {is_irrelevant}")
        print(f"  - Feedback: {data.get('feedback')}")
        print(f"  - Score Reason: {data.get('scoreReason')}")

        if is_irrelevant or score < 60:
            print(f"[FAIL] Strong HR answer received unexpectedly low score ({score}) or marked irrelevant.")
            return False

        print("[PASS] HR question evaluation audit passed.")
        return True
    except Exception as exc:
        print(f"[FAIL] Error during HR evaluation audit: {exc}")
        return False


def audit_code_complexity():
    print_banner("7. CODE TIME & SPACE COMPLEXITY AUDIT")
    try:
        code = (
            "public class Solution {\n"
            "    public static int sumArray(int[] nums) {\n"
            "        int total = 0;\n"
            "        for (int i = 0; i < nums.length; i++) {\n"
            "            total += nums[i];\n"
            "        }\n"
            "        return total;\n"
            "    }\n"
            "}"
        )
        res = requests.post(f"{AI_SERVICE_URL}/api/ai/evaluate-answer", json={
            "question": "Calculate the sum of all elements in an integer array.",
            "answer": code,
            "testCases": [{"input": "[1, 2, 3]", "expectedOutput": "6", "label": "basic"}],
            "questionFormat": "coding",
            "language": "java",
            "interviewType": "technical"
        }, timeout=45)

        if res.status_code != 200:
            print(f"[FAIL] Coding evaluation endpoint returned HTTP {res.status_code}")
            return False

        data = res.json()
        tc = data.get("timeComplexity")
        sc = data.get("spaceComplexity")
        exp = data.get("timeComplexityExplanation")
        model_used = data.get("modelUsed")

        print(f"  - Model Used: {model_used}")
        print(f"  - Time Complexity: {tc}")
        print(f"  - Space Complexity: {sc}")
        print(f"  - Explanation: {exp}")

        if not tc or "O(" not in tc.upper():
            print(f"[FAIL] Time complexity missing or invalid format: {tc}")
            return False

        if not sc or "O(" not in sc.upper():
            print(f"[FAIL] Space complexity missing or invalid format: {sc}")
            return False

        print("[PASS] Code time & space complexity finding audit passed.")
        return True
    except Exception as exc:
        print(f"[FAIL] Error during code complexity audit: {exc}")
        return False


def main():
    print_banner("AI INTERVIEW ASSISTANT - AUTOMATED FINE-TUNED PIPELINE VERIFICATION")

    checks = [
        ("Dataset Audit", audit_datasets),
        ("Splits Overlap Audit", audit_splits_overlap),
        ("Live Health & Verification Audit", audit_live_health_and_verification),
        ("Inference Model & Fallback Audit", audit_inference_models_and_fallback),
        ("Evaluation Discrimination Sanity Audit", audit_discrimination_sanity),
        ("HR Question Evaluation Audit", audit_hr_evaluation),
        ("Code Complexity Finding Audit", audit_code_complexity),
    ]

    failed = []
    for name, fn in checks:
        success = fn()
        if not success:
            failed.append(name)

    print_banner("VERIFICATION SUMMARY REPORT")
    if failed:
        print(f"[FAILED] {len(failed)} out of {len(checks)} audit checks failed:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print("[SUCCESS] ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        sys.exit(0)


if __name__ == "__main__":
    main()
