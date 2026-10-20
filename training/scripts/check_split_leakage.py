#!/usr/bin/env python3
"""
Verification Script: Split Leakage and Class Distribution Audit
Proves:
1. Zero overlap by canonical source_id across train, validation, and test splits (group split proof).
2. Counts per split (total records, task distribution, unique source IDs).
3. Counts per complexity class across all splits, proving >= 30 examples of O(N^3) and O(2^N).
4. Verifies every complexity record contains an explicit, verifiable explanation for the label.
"""

import sys
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SPLITS_DIR = ROOT_DIR / "training" / "data" / "processed" / "splits"

EXPECTED_COMPLEXITY_CLASSES = ["O(1)", "O(log N)", "O(N)", "O(N log N)", "O(N^2)", "O(N^3)", "O(2^N)"]


def normalize_complexity_label(tc: str) -> str:
    if not tc:
        return "UNKNOWN"
    s = tc.strip()
    s_upper = s.upper().replace(" ", "")
    if "O(1)" in s_upper:
        return "O(1)"
    if "O(LOGN)" in s_upper or "O(LOG(N))" in s_upper:
        return "O(log N)"
    if "O(NLOGN)" in s_upper or "O(NLOG(N))" in s_upper:
        return "O(N log N)"
    if "O(N^3)" in s_upper or "O(N3)" in s_upper:
        return "O(N^3)"
    if "O(N^2)" in s_upper or "O(N2)" in s_upper:
        return "O(N^2)"
    if "O(2^N)" in s_upper or "O(2N)" in s_upper:
        return "O(2^N)"
    if "O(N)" in s_upper:
        return "O(N)"
    return s


def load_split(split_name: str):
    file_path = SPLITS_DIR / f"{split_name}.jsonl"
    if not file_path.exists():
        print(f"[ERROR] Split file does not exist: {file_path}")
        sys.exit(1)

    rows = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line.strip()))
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Malformed JSON in {split_name}.jsonl line {line_num}: {e}")
                    sys.exit(1)
    return rows


def main():
    print("================================================================================")
    print(" MOCKMATE AI - DATASET SPLIT LEAKAGE & COMPLEXITY AUDIT")
    print("================================================================================")

    splits = {
        "train": load_split("train"),
        "validation": load_split("validation"),
        "test": load_split("test")
    }

    # 1. Collect source IDs per split
    split_source_ids = {}
    split_task_counts = {}
    split_complexity_counts = defaultdict(Counter)
    complexity_missing_reasons = 0
    total_complexity_records = 0

    for split_name, rows in splits.items():
        source_ids = set()
        task_counts = Counter()

        for r in rows:
            sid = r.get("source_id")
            if not sid:
                # Fallback: inspect assistant message or user prompt
                sid = r.get("group_key", "unknown")
            source_ids.add(sid)
            task = r.get("task", "unknown")
            task_counts[task] += 1

            if task == "analyze_code_complexity":
                total_complexity_records += 1
                assistant_content = next((m["content"] for m in r.get("messages", []) if m["role"] == "assistant"), "")
                try:
                    data = json.loads(assistant_content)
                    tc = data.get("timeComplexity", "")
                    norm_tc = normalize_complexity_label(tc)
                    split_complexity_counts[split_name][norm_tc] += 1
                    explanation = data.get("explanation", "").strip()
                    if not explanation:
                        complexity_missing_reasons += 1
                except Exception:
                    split_complexity_counts[split_name]["PARSE_ERROR"] += 1
                    complexity_missing_reasons += 1

        split_source_ids[split_name] = source_ids
        split_task_counts[split_name] = task_counts

    # 2. Check Overlaps
    train_ids = split_source_ids["train"]
    val_ids = split_source_ids["validation"]
    test_ids = split_source_ids["test"]

    train_val_overlap = train_ids.intersection(val_ids)
    train_test_overlap = train_ids.intersection(test_ids)
    val_test_overlap = val_ids.intersection(test_ids)

    print("\n--- 1. ZERO-LEAKAGE SOURCE ID OVERLAP PROOF ---")
    print(f"  Train distinct source IDs      : {len(train_ids):4d}")
    print(f"  Validation distinct source IDs : {len(val_ids):4d}")
    print(f"  Test distinct source IDs       : {len(test_ids):4d}")
    print(f"  Total unique source problems   : {len(train_ids | val_ids | test_ids):4d}")
    print("  ------------------------------------------------")
    print(f"  Train  INTERSECT  Validation   : {len(train_val_overlap):4d} overlap {list(train_val_overlap)[:5] if train_val_overlap else '[ZERO]'}")
    print(f"  Train  INTERSECT  Test         : {len(train_test_overlap):4d} overlap {list(train_test_overlap)[:5] if train_test_overlap else '[ZERO]'}")
    print(f"  Validation INTERSECT Test      : {len(val_test_overlap):4d} overlap {list(val_test_overlap)[:5] if val_test_overlap else '[ZERO]'}")

    has_leakage = bool(train_val_overlap or train_test_overlap or val_test_overlap)
    if has_leakage:
        print("\n[FAIL] DATA LEAKAGE DETECTED! Some source IDs appear in multiple splits.")
    else:
        print("\n[PASS] ZERO LEAKAGE CONFIRMED! All examples derived from the same source problem")
        print("       or HR question stay strictly within ONE split (100% group isolation).")

    # 3. Print counts per split
    print("\n--- 2. RECORD COUNTS PER SPLIT ---")
    print(f"{'Task Name':<28} | {'Train':>7} | {'Val':>7} | {'Test':>7} | {'Total':>7}")
    print("-" * 65)
    all_tasks = sorted(set().union(*(tc.keys() for tc in split_task_counts.values())))
    for task in all_tasks:
        tr_c = split_task_counts["train"].get(task, 0)
        va_c = split_task_counts["validation"].get(task, 0)
        te_c = split_task_counts["test"].get(task, 0)
        tot = tr_c + va_c + te_c
        print(f"{task:<28} | {tr_c:>7d} | {va_c:>7d} | {te_c:>7d} | {tot:>7d}")
    print("-" * 65)
    tr_tot = len(splits["train"])
    va_tot = len(splits["validation"])
    te_tot = len(splits["test"])
    print(f"{'TOTAL RECORDS':<28} | {tr_tot:>7d} | {va_tot:>7d} | {te_tot:>7d} | {tr_tot + va_tot + te_tot:>7d}")

    # 4. Print counts per complexity class
    print("\n--- 3. COMPLEXITY CLASS DISTRIBUTION AUDIT ---")
    print(f"{'Complexity Class':<20} | {'Train':>7} | {'Val':>7} | {'Test':>7} | {'Total':>7} | {'Target Requirement'}")
    print("-" * 80)

    overall_complexity = Counter()
    for s_name in ["train", "validation", "test"]:
        overall_complexity.update(split_complexity_counts[s_name])

    cubic_count = overall_complexity.get("O(N^3)", 0)
    exp_count = overall_complexity.get("O(2^N)", 0)

    for c_class in EXPECTED_COMPLEXITY_CLASSES:
        tr_c = split_complexity_counts["train"].get(c_class, 0)
        va_c = split_complexity_counts["validation"].get(c_class, 0)
        te_c = split_complexity_counts["test"].get(c_class, 0)
        tot = tr_c + va_c + te_c
        req = ">= 30 (REQUIRED)" if c_class in ["O(N^3)", "O(2^N)"] else "balanced"
        print(f"{c_class:<20} | {tr_c:>7d} | {va_c:>7d} | {te_c:>7d} | {tot:>7d} | {req}")

    print("-" * 80)
    print(f"{'TOTAL COMPLEXITY':<20} | {sum(split_complexity_counts['train'].values()):>7d} | {sum(split_complexity_counts['validation'].values()):>7d} | {sum(split_complexity_counts['test'].values()):>7d} | {total_complexity_records:>7d} |")

    # 5. Verifiable Reason Check
    print("\n--- 4. VERIFIABLE EXPLANATION REASON CHECK ---")
    print(f"  Total complexity records checked : {total_complexity_records}")
    print(f"  Records missing stored reason    : {complexity_missing_reasons}")
    if complexity_missing_reasons == 0:
        print("  [PASS] 100% of complexity records contain an explicit, verifiable reasoning field.")
    else:
        print(f"  [FAIL] {complexity_missing_reasons} complexity records missing verifiable explanations.")

    # 6. Requirement Sanity Checks
    print("\n--- AUDIT SUMMARY & VERIFICATION ---")
    errors = []
    if has_leakage:
        errors.append("Source ID data leakage detected across splits.")
    if cubic_count < 30:
        errors.append(f"O(N^3) complexity count ({cubic_count}) is less than required 30.")
    if exp_count < 30:
        errors.append(f"O(2^N) complexity count ({exp_count}) is less than required 30.")
    if complexity_missing_reasons > 0:
        errors.append(f"Missing verifiable reasoning on {complexity_missing_reasons} complexity records.")

    if errors:
        print("[FAILED AUDIT]")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("[SUCCESS] ALL AUDIT CHECKS PASSED!")
        print(f"  - Zero leakage by source ID confirmed.")
        print(f"  - O(N^3) count: {cubic_count} >= 30 confirmed.")
        print(f"  - O(2^N) count: {exp_count} >= 30 confirmed.")
        print(f"  - Verifiable stored explanations confirmed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
