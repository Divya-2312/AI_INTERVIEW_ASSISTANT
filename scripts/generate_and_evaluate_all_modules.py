#!/usr/bin/env python3
"""
AI Interview Assistant - 600-Record End-to-End Batch Generation & Evaluation Pipeline Script
Processes all 6 dataset modules (100 records each = 600 total records):
1. Java Theory (100)
2. Java Output Prediction (100)
3. Java Coding (100)
4. DBMS Theory (100)
5. SQL Coding (100)
6. HR Questions (100)

For EVERY record:
- Generates a question via configured model
- Evaluates 3 answer cases for the generated question: 'reference', 'wrong', 'keyword_dump'
- Records real response metadata from API: modelUsed, is_fine_tuned_verified, usedFallback, scoringSources
- Calculates mean score per case_type per module and flags modules with insufficient discrimination (<30 pt difference)
"""

import sys
import os
import json
import time
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "training" / "data" / "raw"
OUTPUTS_DIR = ROOT_DIR / "outputs"

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")

MODULE_SPECS = [
    {
        "key": "java_theory",
        "file": "java_theory_100.jsonl",
        "subject": "java",
        "questionFormat": "theory",
        "interviewType": "technical",
    },
    {
        "key": "java_output_prediction",
        "file": "java_output_prediction_100.jsonl",
        "subject": "java",
        "questionFormat": "output_prediction",
        "interviewType": "technical",
    },
    {
        "key": "java_coding",
        "file": "java_coding_100.jsonl",
        "subject": "java",
        "questionFormat": "coding",
        "interviewType": "technical",
    },
    {
        "key": "dbms_theory",
        "file": "dbms_theory_100.jsonl",
        "subject": "dbms",
        "questionFormat": "theory",
        "interviewType": "technical",
    },
    {
        "key": "sql_coding",
        "file": "sql_coding_100.jsonl",
        "subject": "dbms",
        "questionFormat": "coding",
        "interviewType": "technical",
    },
    {
        "key": "hr_questions",
        "file": "hr_questions_100.jsonl",
        "subject": "hr",
        "questionFormat": "theory",
        "interviewType": "hr",
    },
]


def print_banner(title):
    print("\n=======================================================")
    print(f" {title}")
    print("=======================================================")


def check_ai_service_health(allow_unverified=False):
    url = f"{AI_SERVICE_URL}/health"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            is_verified = data.get("is_fine_tuned_verified", False)
            model_id = data.get("model_identity", {})
            print(f"[HEALTH OK] Connected to AI Service at {url}")
            print(f"  - Configured Model: {data.get('configured_model')}")
            print(f"  - Verified Fine-Tuned: {is_verified}")
            print(f"  - Reason: {data.get('verification_reason')}")
            
            if not is_verified and not allow_unverified:
                print("\n[ABORT] Model is NOT verified as a distinct fine-tuned artifact.")
                print("Pass --allow-unverified to run evaluation with base/unverified model.")
                return False, data
            return True, data
    except Exception as exc:
        print(f"[HEALTH ERROR] Could not reach AI service at {url}: {exc}")
    return False, None


def evaluate_case(spec, question_text, expected_concepts, gen_result, candidate_answer, case_type):
    eval_payload = {
        "question": question_text,
        "answer": str(candidate_answer),
        "expectedConcepts": expected_concepts,
        "context": [f"Standard {spec['subject']} principles"],
        "questionFormat": spec["questionFormat"],
        "interviewType": spec["interviewType"],
        "expectedOutput": gen_result.get("expectedOutput"),
        "explanation": gen_result.get("explanation"),
        "language": gen_result.get("language") or "java",
    }
    try:
        res = requests.post(f"{AI_SERVICE_URL}/api/ai/evaluate-answer", json=eval_payload, timeout=60)
        if res.status_code == 200:
            eval_data = res.json()
            eval_data["case_type"] = case_type
            return eval_data, True, None
        return None, False, f"HTTP {res.status_code}: {res.text[:200]}"
    except Exception as exc:
        return None, False, str(exc)


def process_single_record(spec, idx, record, all_records):
    source_id = record.get("id") or f"{spec['key']}_{idx:03d}"
    difficulty = record.get("difficulty", "easy")
    category = record.get("category", spec["subject"].upper())

    gen_payload = {
        "subject": spec["subject"],
        "difficulty": difficulty,
        "questionFormat": spec["questionFormat"],
        "interviewType": spec["interviewType"],
        "category": category,
        "previousQuestions": [],
    }

    gen_result = None
    gen_failed = False
    gen_error_msg = None

    try:
        res = requests.post(f"{AI_SERVICE_URL}/api/ai/generate-question", json=gen_payload, timeout=60)
        if res.status_code == 200:
            gen_result = res.json()
        else:
            gen_failed = True
            gen_error_msg = f"HTTP {res.status_code}: {res.text[:200]}"
    except Exception as exc:
        gen_failed = True
        gen_error_msg = str(exc)

    if gen_failed or not gen_result:
        question_record = {
            "module": spec["key"],
            "source_id": source_id,
            "status": "FAILED",
            "error": gen_error_msg,
            "model_used": "unknown",
            "is_fine_tuned_verified": False,
            "usedFallback": True,
        }
        eval_records = [{
            "module": spec["key"],
            "source_id": source_id,
            "status": "FAILED",
            "error": "Skipped evaluation due to generation failure",
            "case_type": "reference",
        }]
        return question_record, eval_records, False, False

    question_text = gen_result.get("questionText") or gen_result.get("title") or "Interview Question"
    expected_concepts = gen_result.get("expectedConcepts") or record.get("expectedConcepts") or [category]

    question_record = {
        "module": spec["key"],
        "source_id": source_id,
        "generated_question": gen_result,
        "model_used": gen_result.get("modelUsed", "unknown"),
        "used_fallback": gen_result.get("usedFallback", False),
        "status": "SUCCESS",
    }

    # Answer cases
    ref_answer = (gen_result.get("sampleSolution") or
                  gen_result.get("expectedOutput") or
                  gen_result.get("explanation") or
                  record.get("idealAnswer") or
                  record.get("answerGuidance") or
                  f"Standard answer for {category}.")
    if isinstance(ref_answer, dict):
        ref_answer = json.dumps(ref_answer)

    # Wrong answer: pick from another record in the same module
    wrong_record = all_records[(idx % len(all_records))]
    wrong_answer = (wrong_record.get("idealAnswer") or
                    wrong_record.get("answerGuidance") or
                    wrong_record.get("explanation") or
                    "Unrelated answer concept.")
    if isinstance(wrong_answer, dict):
        wrong_answer = json.dumps(wrong_answer)

    # Keyword dump
    keyword_dump_answer = ", ".join(expected_concepts)

    eval_records = []
    eval_ok_count = 0

    for c_type, c_ans in [("reference", ref_answer), ("wrong", wrong_answer), ("keyword_dump", keyword_dump_answer)]:
        e_res, e_ok, e_err = evaluate_case(spec, question_text, expected_concepts, gen_result, c_ans, c_type)
        rec = {
            "module": spec["key"],
            "source_id": source_id,
            "case_type": c_type,
            "question_text": question_text,
            "candidate_answer": str(c_ans),
            "evaluation": e_res,
            "status": "SUCCESS" if e_ok else "FAILED",
            "error": e_err,
            "model_used": e_res.get("modelUsed") if e_res else "unknown",
            "usedFallback": e_res.get("usedFallback") if e_res else True,
            "scoringSources": e_res.get("scoringSources") if e_res else [],
        }
        eval_records.append(rec)
        if e_ok:
            eval_ok_count += 1

    return question_record, eval_records, not gen_failed, (eval_ok_count == 3)


def process_module(spec):
    file_path = RAW_DIR / spec["file"]
    print(f"\nProcessing module: {spec['key']} ({spec['file']})...")

    if not file_path.exists():
        print(f"[ERROR] Missing dataset file: {file_path}")
        return None

    raw_lines = [line.strip() for line in file_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    records = [json.loads(line) for line in raw_lines]

    module_dir = OUTPUTS_DIR / spec["key"]
    module_dir.mkdir(parents=True, exist_ok=True)

    gen_out_file = module_dir / "generated_questions.jsonl"
    eval_out_file = module_dir / "evaluation_results.jsonl"

    gen_results = []
    eval_results = []
    gen_success = 0
    eval_success = 0

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(process_single_record, spec, idx, record, records): (idx, record)
            for idx, record in enumerate(records, 1)
        }
        for future in as_completed(futures):
            q_rec, e_recs, g_ok, e_ok = future.result()
            gen_results.append(q_rec)
            eval_results.extend(e_recs)
            if g_ok:
                gen_success += 1
            if e_ok:
                eval_success += 1

    gen_out_file.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in gen_results), encoding="utf-8")
    eval_out_file.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in eval_results), encoding="utf-8")

    # Compute mean scores per case_type
    case_scores = {"reference": [], "wrong": [], "keyword_dump": []}
    for e in eval_results:
        if e.get("status") == "SUCCESS" and e.get("evaluation"):
            c_type = e.get("case_type")
            score = e["evaluation"].get("score", 0)
            if c_type in case_scores:
                case_scores[c_type].append(score)

    mean_ref = sum(case_scores["reference"]) / len(case_scores["reference"]) if case_scores["reference"] else 0.0
    mean_wrong = sum(case_scores["wrong"]) / len(case_scores["wrong"]) if case_scores["wrong"] else 0.0
    mean_kd = sum(case_scores["keyword_dump"]) / len(case_scores["keyword_dump"]) if case_scores["keyword_dump"] else 0.0

    delta = mean_ref - mean_wrong
    flagged = delta < 30.0

    print(f"  [{spec['key']}] Mean Scores -> Reference: {mean_ref:.1f}, Wrong: {mean_wrong:.1f}, KeywordDump: {mean_kd:.1f}")
    print(f"  [{spec['key']}] Discrimination Delta: {delta:.1f} pts | Flagged (<30pt delta): {flagged}")

    return {
        "module": spec["key"],
        "input_records": len(records),
        "generated_questions": len(gen_results),
        "generation_success": gen_success,
        "generation_failures": len(records) - gen_success,
        "evaluated_cases": len(eval_results),
        "mean_scores": {
            "reference": round(mean_ref, 2),
            "wrong": round(mean_wrong, 2),
            "keyword_dump": round(mean_kd, 2),
            "delta_ref_vs_wrong": round(delta, 2),
        },
        "flagged_insufficient_discrimination": flagged,
    }


def main():
    parser = argparse.ArgumentParser(description="Run AI Interview Assistant evaluation pipeline")
    parser.add_argument("--allow-unverified", action="store_true", help="Allow running when fine-tuned model is not verified")
    args = parser.parse_args()

    start_time = time.time()
    print_banner("AI INTERVIEW ASSISTANT - BATCH GENERATION & EVALUATION PIPELINE")

    ok, health_data = check_ai_service_health(allow_unverified=args.allow_unverified)
    if not ok:
        sys.exit(1)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    summary_modules = {}
    total_input = 0
    total_generated = 0

    for spec in MODULE_SPECS:
        res = process_module(spec)
        if res:
            summary_modules[spec["key"]] = res
            total_input += res["input_records"]
            total_generated += res["generation_success"]

    duration = round(time.time() - start_time, 2)

    overall_summary = {
        "total_modules": len(MODULE_SPECS),
        "total_source_records": total_input,
        "total_questions_generated": total_generated,
        "is_fine_tuned_verified": health_data.get("is_fine_tuned_verified", False) if health_data else False,
        "allow_unverified": args.allow_unverified,
        "configured_model": health_data.get("configured_model") if health_data else "unknown",
        "execution_duration_seconds": duration,
        "module_breakdown": summary_modules,
    }

    summary_file = OUTPUTS_DIR / "overall_evaluation_summary.json"
    summary_file.write_text(json.dumps(overall_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print_banner("BATCH PIPELINE EXECUTION SUMMARY")
    print(f"Summary Saved To: {summary_file}")


if __name__ == "__main__":
    main()
