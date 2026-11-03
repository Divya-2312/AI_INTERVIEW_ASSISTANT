#!/usr/bin/env python3
"""
scripts/run_3_hr_benchmarks.py

Executes scripts/check_hr_golden.py 3 times, writing the output to:
- verification_runs/hr_run1.txt
- verification_runs/hr_run2.txt
- verification_runs/hr_run3.txt

Compares the 3 runs per case (score and sub-scores) and determines whether
the model output is identical every time.
"""
import os
import sys
import subprocess
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.path.join(BASE_DIR, "verification_runs")
os.makedirs(RUNS_DIR, exist_ok=True)

def run_golden_check(run_num: int):
    out_file = os.path.join(RUNS_DIR, f"hr_run{run_num}.txt")
    print(f"\n{'='*30} Starting HR Golden Run {run_num}/3 {'='*30}", flush=True)
    
    script_path = os.path.join(BASE_DIR, "scripts", "check_hr_golden.py")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    proc = subprocess.Popen(
        [sys.executable, script_path],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    
    output_lines = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        output_lines.append(line)
        
    proc.wait()
    
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(output_lines)
        
    print(f"\n[Saved] Run {run_num} written to {out_file}", flush=True)
    return out_file

def parse_run_results(file_path):
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    # Matches: [MISS] C01 | Archetype: excellent_star  | Expected: [ 75, 100] | Actual:  68% | Sub-scores: R=80% C=60% A=55% Comm=77%
    pattern = re.compile(
        r'\[(PASS|MISS)\]\s+(C\d+)\s+\|\s+Archetype:\s+(\w+)\s+\|\s+Expected:\s+\[\s*(\d+),\s*(\d+)\]\s+\|\s+Actual:\s+(\d+)%\s+\|\s+Sub-scores:\s+R=(\d+)%\s+C=(\d+)%\s+A=(\d+)%\s+Comm=(\d+)%'
    )
    cases = {}
    for match in pattern.finditer(content):
        status, cid, arch, exp_min, exp_max, score, r, c, a, comm = match.groups()
        cases[cid] = {
            "status": status,
            "archetype": arch,
            "score": int(score),
            "R": int(r),
            "C": int(c),
            "A": int(a),
            "Comm": int(comm),
            "raw": match.group(0).strip()
        }
    return cases

def compare_runs():
    c1 = parse_run_results(os.path.join(RUNS_DIR, "hr_run1.txt"))
    c2 = parse_run_results(os.path.join(RUNS_DIR, "hr_run2.txt"))
    c3 = parse_run_results(os.path.join(RUNS_DIR, "hr_run3.txt"))
    
    print("\n" + "=" * 80)
    print("3-RUN HR BENCHMARK REPRODUCIBILITY COMPARISON")
    print("=" * 80)
    print(f"{'Case':<6} | {'Archetype':<16} | {'Run 1 Score':<12} | {'Run 2 Score':<12} | {'Run 3 Score':<12} | {'Identical?'}")
    print("-" * 80)
    
    identical_count = 0
    total_cases = len(c1)
    differences = []
    
    for cid in sorted(c1.keys(), key=lambda x: int(x[1:])):
        d1 = c1.get(cid, {})
        d2 = c2.get(cid, {})
        d3 = c3.get(cid, {})
        
        is_same = (d1 == d2 == d3)
        if is_same:
            identical_count += 1
            status_str = "YES (100% match)"
        else:
            status_str = "VARIATION"
            differences.append({
                "cid": cid,
                "arch": d1.get("archetype"),
                "r1": f"Score={d1.get('score')} R={d1.get('R')} C={d1.get('C')} A={d1.get('A')} Comm={d1.get('Comm')}",
                "r2": f"Score={d2.get('score')} R={d2.get('R')} C={d2.get('C')} A={d2.get('A')} Comm={d2.get('Comm')}",
                "r3": f"Score={d3.get('score')} R={d3.get('R')} C={d3.get('C')} A={d3.get('A')} Comm={d3.get('Comm')}",
            })
            
        print(f"{cid:<6} | {d1.get('archetype', ''):<16} | {d1.get('score', 0):>3}% (R={d1.get('R')} C={d1.get('C')} A={d1.get('A')}) | {d2.get('score', 0):>3}% (R={d2.get('R')} C={d2.get('C')} A={d2.get('A')}) | {d3.get('score', 0):>3}% (R={d3.get('R')} C={d3.get('C')} A={d3.get('A')}) | {status_str}")
        
    print("=" * 80)
    print(f"Summary: {identical_count} / {total_cases} cases are 100% IDENTICAL across all 3 runs.")
    if differences:
        print(f"Found {len(differences)} case(s) with runtime variation:")
        for diff in differences:
            print(f"  - Case {diff['cid']} ({diff['arch']}):")
            print(f"      Run 1: {diff['r1']}")
            print(f"      Run 2: {diff['r2']}")
            print(f"      Run 3: {diff['r3']}")
    else:
        print("Model output is completely deterministic across all 3 runs.")
    print("=" * 80)

def main():
    for r in range(1, 4):
        run_golden_check(r)
    compare_runs()

if __name__ == "__main__":
    main()
