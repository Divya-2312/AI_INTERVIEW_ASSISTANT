#!/usr/bin/env python3
"""
Evaluate any Ollama model on:
1. Synthetic Test Dataset Split (training/data/processed/splits/test.jsonl)
2. Real-World Isolated Test Set (training/data/real_eval/) with human ground truth labels:
   - Java Code Complexity (30 programs): exact accuracy, per-class accuracy,
     within-one-class accuracy (O(1) < O(log N) < O(N) < O(N log N) < O(N^2) < O(N^3) < O(2^N)),
     JSON validity, average latency.
   - HR Answer Evaluation (30 hand-written answers): MAE against human scores,
     Spearman rank correlation, JSON validity, average latency.

Outputs saved to:
- training/metadata/results.json
- training/metadata/eval_<model_slug>_<timestamp>.json
"""

import sys
import os
import json
import argparse
import time
import random
import statistics
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

ROOT_DIR = Path(__file__).resolve().parent.parent
TEST_FILE = ROOT_DIR / "training" / "data" / "processed" / "splits" / "test.jsonl"
REAL_EVAL_DIR = ROOT_DIR / "training" / "data" / "real_eval"
METADATA_DIR = ROOT_DIR / "training" / "metadata"
RESULTS_JSON_PATH = METADATA_DIR / "results.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

TRAINING_SYSTEM_PROMPT = (
    "You are AI Interview Assistant, an interview practice assistant. Follow the requested task. "
    "For generation and evaluation tasks, return only the requested JSON object; do not wrap it in markdown. "
    "Evaluate meaning and correctness, not keyword presence alone. Never invent evidence from the student's answer. "
    "Grading Rules: Relevance measures if the answer addresses the topic and is separate from correctness. "
    "Short answers are not auto-irrelevant if on-topic. "
    "Keyword lists earn little credit without explanation."
)

TRAINING_SCHEMA_KEYS = {
    "evaluate_answer": [
        "score", "correctness", "relevance", "communication",
        "isIrrelevant", "feedback", "strengths", "weaknesses",
        "missingConcepts", "improvementSuggestion", "scoreReason"
    ],
    "analyze_code_complexity": [
        "timeComplexity", "spaceComplexity", "explanation"
    ],
    "generate_question": [
        "question", "difficulty", "questionFormat"
    ],
    "generate_coding_problem": [
        "title", "description", "constraints", "starterCode", "testCases", "difficulty", "questionFormat"
    ],
    "generate_followup": [
        "followupQuestion"
    ]
}

SCORE_BANDS = {
    "reference": (70, 100),
    "partial": (30, 70),
    "wrong": (0, 30),
}

COMPLEXITY_ORDER = ["O(1)", "O(log N)", "O(N)", "O(N log N)", "O(N^2)", "O(N^3)", "O(2^N)"]


def normalize_complexity(tc: str) -> str:
    if not tc:
        return "UNKNOWN"
    s = tc.strip().upper().replace(" ", "")
    if "O(1)" in s:
        return "O(1)"
    if "O(LOGN)" in s or "O(LOG(N))" in s:
        return "O(log N)"
    if "O(NLOGN)" in s or "O(NLOG(N))" in s:
        return "O(N log N)"
    if "O(N^3)" in s or "O(N3)" in s:
        return "O(N^3)"
    if "O(N^2)" in s or "O(N2)" in s:
        return "O(N^2)"
    if "O(2^N)" in s or "O(2N)" in s:
        return "O(2^N)"
    if "O(N)" in s:
        return "O(N)"
    return tc.strip()


def compute_ranks(values):
    """Computes fractional ranks for a sequence of numeric values."""
    sorted_pairs = sorted((val, idx) for idx, val in enumerate(values))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(sorted_pairs):
        j = i
        while j < len(sorted_pairs) and sorted_pairs[j][0] == sorted_pairs[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[sorted_pairs[k][1]] = avg_rank
        i = j
    return ranks


def compute_spearman_correlation(x, y):
    """Computes Spearman rank correlation coefficient between two lists."""
    if len(x) < 2 or len(x) != len(y):
        return 0.0
    rx = compute_ranks(x)
    ry = compute_ranks(y)
    mean_rx = statistics.mean(rx)
    mean_ry = statistics.mean(ry)
    num = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(len(x)))
    den_x = sum((rx[i] - mean_rx) ** 2 for i in range(len(x)))
    den_y = sum((ry[i] - mean_ry) ** 2 for i in range(len(y)))
    if den_x == 0 or den_y == 0:
        return 0.0
    return round(num / ((den_x * den_y) ** 0.5), 4)


def check_ollama_model(model_name):
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if res.status_code == 200:
            models = [m.get("name") for m in res.json().get("models", [])]
            if model_name in models or any(m.startswith(model_name) or model_name.startswith(m.split(":")[0]) for m in models):
                return True
            print(f"[WARN] Model '{model_name}' is not present in local Ollama storage ({models}).")
            return False
    except Exception as exc:
        print(f"[ERROR] Could not connect to Ollama at {OLLAMA_URL}: {exc}")
        return False
    return False


def query_ollama(model_name, system_prompt, user_prompt, temperature=0.2, seed=None):
    options = {"temperature": temperature}
    if seed is not None:
        options["seed"] = seed

    payload = {
        "model": model_name,
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False,
        "options": options
    }
    try:
        res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=90)
        if res.status_code == 200:
            return res.json().get("response", "").strip()
    except Exception:
        pass
    return ""


def parse_json_response(response_text):
    if not response_text:
        return None
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        try:
            parsed = json.loads(cleaned[start:end+1])
            if isinstance(parsed, dict) and "evaluation" in parsed and isinstance(parsed["evaluation"], dict):
                merged = dict(parsed["evaluation"])
                for k, v in parsed.items():
                    if k != "evaluation" and k not in merged:
                        merged[k] = v
                return merged
            return parsed
        except Exception:
            pass
    return None


def extract_score(response_text):
    data = parse_json_response(response_text)
    if not data or not isinstance(data, dict):
        return None
    for k in ["score", "score_overall", "overall_score"]:
        if k in data and data[k] is not None:
            try:
                import re
                val = str(data[k]).replace("%", "").strip()
                match = re.search(r'\d+(?:\.\d+)?', val)
                if match:
                    return float(match.group(0))
            except (ValueError, TypeError):
                pass
    if "result" in data:
        res_str = str(data["result"]).lower()
        if "pass" in res_str or "strong" in res_str or "hire" in res_str:
            return 85.0
        elif "fail" in res_str or "poor" in res_str or "no" in res_str:
            return 35.0
        elif "borderline" in res_str:
            return 60.0
    if "relevance" in data or "correctness" in data:
        try:
            rel = float(data.get("relevance", 5.0 if "correctness" in data else 0.5))
            corr = float(data.get("correctness", rel))
            cov = float(data.get("conceptCoverage", corr) if not isinstance(data.get("conceptCoverage"), list) else corr)
            comm = float(data.get("communication", 7.5 if rel > 1.0 else 0.75))
            if max(rel, corr, cov) <= 1.0:
                return float(round((rel * 0.25 + corr * 0.30 + cov * 0.30 + comm * 0.15) * 100))
            elif max(rel, corr, cov) <= 10.0:
                return float(round((rel * 0.25 + corr * 0.30 + cov * 0.30 + (comm if comm <= 10.0 else comm / 10.0) * 0.15) * 10))
            else:
                return float(round(rel * 0.25 + corr * 0.30 + cov * 0.30 + comm * 0.15))
        except (ValueError, TypeError):
            pass
    return None


# ==============================================================================
# REAL EVALUATION SUITE (30 HR answers + 30 Java Complexity programs)
# ==============================================================================

def evaluate_real_test_set(model_name: str, temperature: float = 0.0, seed: int = 42) -> dict:
    print(f"\n================================================================================")
    print(f" EVALUATING ON REAL-WORLD BENCHMARK (DATA/REAL_EVAL): {model_name}")
    print(f"================================================================================")

    hr_file = REAL_EVAL_DIR / "real_hr_eval_30.jsonl"
    comp_file = REAL_EVAL_DIR / "real_complexity_eval_30.jsonl"

    if not hr_file.exists() or not comp_file.exists():
        print(f"[ERROR] Real eval files missing in {REAL_EVAL_DIR}")
        return {}

    # 1. EVALUATE JAVA CODE COMPLEXITY (30 programs)
    comp_rows = [json.loads(l) for l in comp_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\nEvaluating Java Code Complexity on {len(comp_rows)} programs...")

    comp_exact_correct = 0
    comp_within_one_correct = 0
    comp_json_valid = 0
    comp_latencies = []
    comp_per_class_total = Counter()
    comp_per_class_correct = Counter()
    comp_details = []

    for idx, item in enumerate(comp_rows, 1):
        inp_dict = {
            "language": item.get("language", "java"),
            "question": item.get("question", "Algorithm Problem"),
            "code": item.get("code", "")
        }
        user_prompt = f"TASK: analyze_code_complexity\nINPUT:\n{json.dumps(inp_dict, indent=2)}\n\nReturn the required result. For JSON tasks, output valid JSON only."

        t0 = time.time()
        resp_text = query_ollama(model_name, TRAINING_SYSTEM_PROMPT, user_prompt, temperature=temperature, seed=seed)
        latency = round(time.time() - t0, 3)
        comp_latencies.append(latency)

        data = parse_json_response(resp_text)
        raw_tc = ""
        raw_sc = ""
        if isinstance(data, dict):
            raw_tc = data.get("timeComplexity") or data.get("time_complexity") or data.get("timeComplexityBigO") or data.get("time") or ""
            raw_sc = data.get("spaceComplexity") or data.get("space_complexity") or data.get("space") or ""
        is_valid = data is not None and bool(raw_tc or "time_complexity" in data or "timeComplexity" in data or "code_complexity" in data)
        if is_valid:
            comp_json_valid += 1

        pred_tc = normalize_complexity(raw_tc)
        true_tc = normalize_complexity(item.get("human_time_complexity", ""))
        comp_per_class_total[true_tc] += 1

        is_exact = (pred_tc == true_tc)
        if is_exact:
            comp_exact_correct += 1
            comp_per_class_correct[true_tc] += 1

        is_within_one = False
        if pred_tc in COMPLEXITY_ORDER and true_tc in COMPLEXITY_ORDER:
            dist = abs(COMPLEXITY_ORDER.index(pred_tc) - COMPLEXITY_ORDER.index(true_tc))
            is_within_one = (dist <= 1)
        elif is_exact:
            is_within_one = True

        if is_within_one:
            comp_within_one_correct += 1

        comp_details.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "true_time": true_tc,
            "pred_time": pred_tc,
            "exact": is_exact,
            "within_one": is_within_one,
            "latency": latency
        })

        if idx % 10 == 0 or idx == len(comp_rows):
            print(f"  Complexity: {idx}/{len(comp_rows)} | Exact Acc: {comp_exact_correct}/{idx} ({comp_exact_correct/idx*100:.1f}%) | Within-1 Acc: {comp_within_one_correct}/{idx} ({comp_within_one_correct/idx*100:.1f}%)")

    comp_exact_acc = round(comp_exact_correct / len(comp_rows) * 100, 2)
    comp_within_one_acc = round(comp_within_one_correct / len(comp_rows) * 100, 2)
    comp_json_rate = round(comp_json_valid / len(comp_rows) * 100, 2)
    comp_avg_latency = round(statistics.mean(comp_latencies), 3)

    per_class_accuracy = {}
    for c_class in COMPLEXITY_ORDER:
        tot = comp_per_class_total[c_class]
        corr = comp_per_class_correct[c_class]
        acc = round(corr / tot * 100, 1) if tot > 0 else 0.0
        per_class_accuracy[c_class] = {"correct": corr, "total": tot, "accuracy_pct": acc}

    # 2. EVALUATE HR INTERVIEW ANSWERS (30 hand-written answers)
    hr_rows = [json.loads(l) for l in hr_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\nEvaluating HR Answer Evaluation on {len(hr_rows)} hand-written answers...")

    hr_json_valid = 0
    hr_latencies = []
    pred_scores = []
    human_scores = []
    abs_errors = []
    hr_details = []

    for idx, item in enumerate(hr_rows, 1):
        inp_dict = {
            "interviewType": "hr",
            "subject": "hr",
            "question": item.get("question", ""),
            "answer": item.get("candidate_answer", ""),
            "expectedConcepts": item.get("expectedConcepts", []),
            "questionFormat": "theory"
        }
        user_prompt = f"TASK: evaluate_answer\nINPUT:\n{json.dumps(inp_dict, indent=2)}\n\nReturn the required result. For JSON tasks, output valid JSON only."

        t0 = time.time()
        resp_text = query_ollama(model_name, TRAINING_SYSTEM_PROMPT, user_prompt, temperature=temperature, seed=seed)
        latency = round(time.time() - t0, 3)
        hr_latencies.append(latency)

        data = parse_json_response(resp_text)
        is_valid = data is not None and ("score" in data or "relevance" in data)
        if is_valid:
            hr_json_valid += 1

        sc = extract_score(resp_text)
        pred_sc = sc if sc is not None else 0.0
        human_sc = float(item.get("human_score", 0.0))

        err = abs(pred_sc - human_sc)
        pred_scores.append(pred_sc)
        human_scores.append(human_sc)
        abs_errors.append(err)

        hr_details.append({
            "id": item.get("id"),
            "category": item.get("category"),
            "human_score": human_sc,
            "pred_score": pred_sc,
            "abs_error": round(err, 2),
            "latency": latency
        })

        if idx % 10 == 0 or idx == len(hr_rows):
            cur_mae = round(statistics.mean(abs_errors), 2)
            print(f"  HR Evaluation: {idx}/{len(hr_rows)} | Valid JSON: {hr_json_valid}/{idx} ({hr_json_valid/idx*100:.1f}%) | Current MAE: {cur_mae} pts")

    hr_mae = round(statistics.mean(abs_errors), 2)
    hr_spearman = compute_spearman_correlation(pred_scores, human_scores)
    hr_json_rate = round(hr_json_valid / len(hr_rows) * 100, 2)
    hr_avg_latency = round(statistics.mean(hr_latencies), 3)

    # 3. PRINT SUMMARY TABLES
    print("\n--------------------------------------------------------------------------------")
    print(f" REAL-WORLD BENCHMARK RESULTS SUMMARY: {model_name}")
    print("--------------------------------------------------------------------------------")
    print(f" Java Complexity Exact Accuracy       : {comp_exact_acc}% ({comp_exact_correct}/{len(comp_rows)})")
    print(f" Java Complexity Within-One Accuracy  : {comp_within_one_acc}% ({comp_within_one_correct}/{len(comp_rows)})")
    print(f" Java Complexity JSON Validity Rate   : {comp_json_rate}%")
    print(f" Java Complexity Average Latency      : {comp_avg_latency}s")
    print(" Per-Class Complexity Accuracy:")
    for c_class in COMPLEXITY_ORDER:
        info = per_class_accuracy[c_class]
        print(f"   - {c_class:<10}: {info['accuracy_pct']:5.1f}% ({info['correct']}/{info['total']})")
    print("--------------------------------------------------------------------------------")
    print(f" HR Score Mean Absolute Error (MAE)   : {hr_mae} pts (lower is better)")
    print(f" HR Score Spearman Rank Correlation   : {hr_spearman:+.4f} (higher is better, +1.0 ideal)")
    print(f" HR Evaluation JSON Validity Rate     : {hr_json_rate}%")
    print(f" HR Evaluation Average Latency        : {hr_avg_latency}s")
    print("--------------------------------------------------------------------------------\n")

    return {
        "model": model_name,
        "timestamp": datetime.now().isoformat(),
        "java_complexity": {
            "total_programs": len(comp_rows),
            "exact_accuracy_pct": comp_exact_acc,
            "within_one_class_accuracy_pct": comp_within_one_acc,
            "json_validity_rate_pct": comp_json_rate,
            "average_latency_sec": comp_avg_latency,
            "per_class_accuracy": per_class_accuracy,
            "details": comp_details
        },
        "hr_evaluation": {
            "total_answers": len(hr_rows),
            "score_mae_points": hr_mae,
            "spearman_correlation": hr_spearman,
            "json_validity_rate_pct": hr_json_rate,
            "average_latency_sec": hr_avg_latency,
            "details": hr_details
        }
    }


def print_real_eval_comparison(base_res: dict, ft_res: dict):
    print("\n====================================================================================================")
    print(" BASE MODEL vs. FINE-TUNED MODEL: REAL-WORLD BENCHMARK COMPARISON REPORT")
    print("====================================================================================================")
    b_name = base_res.get("model", "Base")
    f_name = ft_res.get("model", "Fine-Tuned")

    print(f"{'Benchmark Metric':<42} | {b_name:<24} | {f_name:<24} | {'Advantage'}")
    print("-" * 105)

    # Complexity
    bc = base_res.get("java_complexity", {})
    fc = ft_res.get("java_complexity", {})

    b_acc = f"{bc.get('exact_accuracy_pct', 0)}%"
    f_acc = f"{fc.get('exact_accuracy_pct', 0)}%"
    adv_acc = f"+{fc.get('exact_accuracy_pct', 0) - bc.get('exact_accuracy_pct', 0):.1f}%"
    print(f"{'Complexity Exact Accuracy':<42} | {b_acc:<24} | {f_acc:<24} | {adv_acc}")

    b_w1 = f"{bc.get('within_one_class_accuracy_pct', 0)}%"
    f_w1 = f"{fc.get('within_one_class_accuracy_pct', 0)}%"
    adv_w1 = f"+{fc.get('within_one_class_accuracy_pct', 0) - bc.get('within_one_class_accuracy_pct', 0):.1f}%"
    print(f"{'Complexity Within-One-Class Accuracy':<42} | {b_w1:<24} | {f_w1:<24} | {adv_w1}")

    b_cj = f"{bc.get('json_validity_rate_pct', 0)}%"
    f_cj = f"{fc.get('json_validity_rate_pct', 0)}%"
    print(f"{'Complexity JSON Validity Rate':<42} | {b_cj:<24} | {f_cj:<24} |")

    b_cl = f"{bc.get('average_latency_sec', 0)}s"
    f_cl = f"{fc.get('average_latency_sec', 0)}s"
    print(f"{'Complexity Average Latency':<42} | {b_cl:<24} | {f_cl:<24} |")

    print("-" * 105)

    # HR Evaluation
    bh = base_res.get("hr_evaluation", {})
    fh = ft_res.get("hr_evaluation", {})

    b_mae = f"{bh.get('score_mae_points', 0)} pts"
    f_mae = f"{fh.get('score_mae_points', 0)} pts"
    adv_mae = f"{bh.get('score_mae_points', 0) - fh.get('score_mae_points', 0):+.2f} pts"
    print(f"{'HR Score Mean Absolute Error (MAE)':<42} | {b_mae:<24} | {f_mae:<24} | {adv_mae} (lower is better)")

    b_sp = f"{bh.get('spearman_correlation', 0):+.4f}"
    f_sp = f"{fh.get('spearman_correlation', 0):+.4f}"
    adv_sp = f"{fh.get('spearman_correlation', 0) - bh.get('spearman_correlation', 0):+.4f}"
    print(f"{'HR Score Spearman Rank Correlation':<42} | {b_sp:<24} | {f_sp:<24} | {adv_sp} (higher is better)")

    b_hj = f"{bh.get('json_validity_rate_pct', 0)}%"
    f_hj = f"{fh.get('json_validity_rate_pct', 0)}%"
    print(f"{'HR Evaluation JSON Validity Rate':<42} | {b_hj:<24} | {f_hj:<24} |")

    b_hl = f"{bh.get('average_latency_sec', 0)}s"
    f_hl = f"{fh.get('average_latency_sec', 0)}s"
    print(f"{'HR Evaluation Average Latency':<42} | {b_hl:<24} | {f_hl:<24} |")

    print("====================================================================================================\n")


# ==============================================================================
# SPLIT EVALUATION (test.jsonl)
# ==============================================================================

def evaluate_model_on_rows(model_name, test_rows, temperature=0.2, seed=None):
    print(f"\nEvaluating model '{model_name}' (temp={temperature}, seed={seed}) on {len(test_rows)} test split examples...")

    task_stats = {}
    total_samples = 0
    total_json_valid = 0
    total_keys_valid = 0
    per_key_failures = defaultdict(lambda: defaultdict(int))

    eval_band_total = 0
    eval_band_correct = 0
    eval_question_variants = defaultdict(dict)
    no_score_rows = []

    for idx, row in enumerate(test_rows, 1):
        msgs = row.get("messages", [])
        system_msg = next((m["content"] for m in msgs if m.get("role") == "system"), "")
        user_msg = next((m["content"] for m in msgs if m.get("role") == "user"), "")
        task = row.get("task", "unknown")

        if task not in task_stats:
            task_stats[task] = {
                "count": 0,
                "json_valid_count": 0,
                "required_keys_valid_count": 0,
            }

        task_stats[task]["count"] += 1
        total_samples += 1

        response_text = query_ollama(model_name, system_msg, user_msg, temperature=temperature, seed=seed)
        parsed_json = parse_json_response(response_text)

        is_valid_json = parsed_json is not None
        keys_valid = False

        if is_valid_json:
            task_stats[task]["json_valid_count"] += 1
            total_json_valid += 1

            required_keys = TRAINING_SCHEMA_KEYS.get(task, [])
            missing_for_row = []
            for k in required_keys:
                if k not in parsed_json:
                    missing_for_row.append(k)
                    per_key_failures[task][k] += 1

            if not missing_for_row:
                keys_valid = True
                task_stats[task]["required_keys_valid_count"] += 1
                total_keys_valid += 1

        if task == "evaluate_answer":
            predicted_score = extract_score(response_text)
            if predicted_score is None:
                no_score_rows.append((idx, response_text[:120].replace("\n", " ")))

            case_type = row.get("case_type")
            if not case_type:
                target_score = None
                if len(msgs) >= 2 and msgs[-1].get("role") == "assistant":
                    try:
                        target_data = parse_json_response(msgs[-1]["content"])
                        if target_data and "score" in target_data:
                            target_score = float(target_data["score"])
                    except Exception:
                        pass
                if target_score is not None:
                    if target_score >= 70:
                        case_type = "reference"
                    elif target_score >= 30:
                        case_type = "partial"
                    else:
                        case_type = "wrong"
                else:
                    case_type = "reference"

            base_q_id = None
            try:
                if "INPUT:\n" in user_msg:
                    json_str = user_msg.split("INPUT:\n", 1)[1].rsplit("\n\nReturn", 1)[0].strip()
                    input_data = json.loads(json_str)
                    base_q_id = input_data.get("question")
            except Exception:
                pass
            if not base_q_id:
                source_id = row.get("source_id", "")
                base_q_id = source_id.split("_eval_")[0] if "_eval_" in source_id else source_id

            if predicted_score is not None:
                band_min, band_max = SCORE_BANDS.get(case_type, (0, 100))
                eval_band_total += 1
                if band_min <= predicted_score <= band_max:
                    eval_band_correct += 1
                if base_q_id:
                    eval_question_variants[base_q_id][case_type] = predicted_score

        if idx % 25 == 0 or idx == len(test_rows):
            print(f"  Progress: {idx}/{len(test_rows)} | Valid JSON: {total_json_valid}/{idx} ({total_json_valid/idx*100:.1f}%) | Exact Schema Keys: {total_keys_valid}/{idx} ({total_keys_valid/idx*100:.1f}%)")

    ordering_total = 0
    ordering_correct = 0
    for q_id, variants in eval_question_variants.items():
        if "reference" in variants and "partial" in variants and "wrong" in variants:
            ordering_total += 1
            if variants["reference"] > variants["partial"] > variants["wrong"]:
                ordering_correct += 1

    band_accuracy_pct = round((eval_band_correct / eval_band_total * 100) if eval_band_total > 0 else 0.0, 2)
    ordering_accuracy_pct = round((ordering_correct / ordering_total * 100) if ordering_total > 0 else 0.0, 2)

    per_task_results = {}
    for t_name, stats in task_stats.items():
        cnt = stats["count"]
        jv = stats["json_valid_count"]
        kv = stats["required_keys_valid_count"]
        per_task_results[t_name] = {
            "count": cnt,
            "json_valid_count": jv,
            "json_valid_rate": round(jv / cnt if cnt > 0 else 0.0, 4),
            "exact_keys_valid_count": kv,
            "exact_keys_valid_rate": round(kv / cnt if cnt > 0 else 0.0, 4),
            "key_failures": dict(per_key_failures[t_name])
        }

    overall_results = {
        "model": model_name,
        "timestamp": datetime.now().isoformat(),
        "total_samples": total_samples,
        "json_valid_count": total_json_valid,
        "json_valid_rate": round(total_json_valid / total_samples if total_samples > 0 else 0.0, 4),
        "exact_keys_valid_count": total_keys_valid,
        "exact_keys_valid_rate": round(total_keys_valid / total_samples if total_samples > 0 else 0.0, 4),
        "no_score_count": len(no_score_rows),
        "evaluate_answer_analysis": {
            "eval_samples_n": eval_band_total,
            "band_accuracy_pct": band_accuracy_pct,
            "ordering_questions_n": ordering_total,
            "ordering_accuracy_pct": ordering_accuracy_pct,
        },
        "per_task": per_task_results,
    }

    print("\n=======================================================")
    print(f" TEST SPLIT EVALUATION COMPLETE: {model_name}")
    print("=======================================================")
    print(f"Total Samples (n)       : {total_samples}")
    print(f"JSON Validity Rate      : {overall_results['json_valid_rate']*100:.1f}%")
    print(f"Exact Schema Keys Rate  : {overall_results['exact_keys_valid_rate']*100:.1f}%")
    print(f"Eval Band Accuracy (%)  : {band_accuracy_pct}% (n={eval_band_total})")
    print(f"Eval Monotonic Order (%) : {ordering_accuracy_pct}% (n={ordering_total})")
    print("=======================================================\n")

    return overall_results


def stratified_sample(all_rows, limit=100, seed=42):
    by_task = defaultdict(list)
    for r in all_rows:
        by_task[r.get("task", "unknown")].append(r)

    rng = random.Random(seed)
    sampled = []
    total_rows = len(all_rows)

    print(f"Stratifying sample of {limit} rows across {len(by_task)} tasks (total rows={total_rows}, seed={seed}):")
    for task_name, rows in by_task.items():
        shuffled = list(rows)
        rng.shuffle(shuffled)
        target_cnt = max(1, round(len(rows) / total_rows * limit))
        task_sampled = shuffled[:target_cnt]
        sampled.extend(task_sampled)
        print(f"  - Task '{task_name:<25}': total={len(rows):3d} -> sampled={len(task_sampled):3d}")

    rng.shuffle(sampled)
    return sampled[:limit]


def main():
    parser = argparse.ArgumentParser(description="Evaluate Ollama models on test split and real-world benchmark")
    parser.add_argument("--model", required=True, help="Primary Ollama model name (e.g., mockmate-llama-ft)")
    parser.add_argument("--compare-base", nargs="*", default=[], help="Optional additional models to compare (e.g. llama3.2:3b)")
    parser.add_argument("--eval-real", action="store_true", help="Evaluate on isolated real test benchmark (training/data/real_eval/)")
    parser.add_argument("--limit", type=int, default=100, help="Number of test split samples to evaluate (default 100)")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling and generation")
    parser.add_argument("--save-results", action="store_true", default=True, help="Save evaluation report to training/metadata/results.json")
    args = parser.parse_args()

    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    models_to_run = [args.model] + args.compare_base

    # 1. REAL BENCHMARK EVALUATION (if --eval-real or default when evaluating fine-tuned vs base)
    if args.eval_real:
        real_results = {}
        for m_name in models_to_run:
            if check_ollama_model(m_name):
                m_res = evaluate_real_test_set(m_name, temperature=0.0, seed=args.seed)
                real_results[m_name] = m_res
            else:
                print(f"[SKIP] Model '{m_name}' unavailable in local Ollama storage.")

        if len(real_results) >= 2:
            base_model_key = args.compare_base[0] if args.compare_base else list(real_results.keys())[1]
            ft_model_key = args.model
            if base_model_key in real_results and ft_model_key in real_results:
                print_real_eval_comparison(real_results[base_model_key], real_results[ft_model_key])

        if args.save_results and real_results:
            RESULTS_JSON_PATH.write_text(json.dumps(real_results, indent=2), encoding="utf-8")
            print(f"[SAVED] Real benchmark results saved to {RESULTS_JSON_PATH}")
        return

    # 2. TEST SPLIT EVALUATION
    if not TEST_FILE.exists():
        print(f"[ERROR] Test split file missing: {TEST_FILE}")
        sys.exit(1)

    all_lines = [json.loads(l.strip()) for l in TEST_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    test_rows = stratified_sample(all_lines, limit=args.limit, seed=args.seed)

    split_results = []
    for m_name in models_to_run:
        if check_ollama_model(m_name):
            res = evaluate_model_on_rows(m_name, test_rows, temperature=args.temperature, seed=args.seed)
            split_results.append(res)
            # Write individual timestamped run
            slug = m_name.replace(":", "_").replace("/", "_")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_file = METADATA_DIR / f"eval_{slug}_{ts}.json"
            run_file.write_text(json.dumps(res, indent=2), encoding="utf-8")
            print(f"[SAVED] Run results saved to {run_file}")
        else:
            print(f"\n[SKIP] Model '{m_name}' is currently unavailable in local Ollama storage.")

    if args.save_results and split_results:
        RESULTS_JSON_PATH.write_text(json.dumps(split_results, indent=2), encoding="utf-8")
        print(f"[SAVED] Test split results saved to {RESULTS_JSON_PATH}")


if __name__ == "__main__":
    main()
