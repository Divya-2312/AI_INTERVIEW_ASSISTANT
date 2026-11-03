import re

def parse_run(filepath):
    cases = {}
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.match(r'\[(PASS|MISS)\]\s+(C\d+)\s+\|\s+Archetype:\s+(\w+)\s+\|\s+Expected:\s+\[\s*(\d+),\s*(\d+)\]\s+\|\s+Actual:\s+(\d+)%', line)
            if m:
                status, cid, arch, exp_low, exp_high, actual = m.groups()
                cases[cid] = {
                    "status": status,
                    "archetype": arch,
                    "expected": (int(exp_low), int(exp_high)),
                    "actual": int(actual),
                    "raw": line.strip()
                }
    return cases

before = parse_run("verification_runs/hr_golden_before.txt")
run1 = parse_run("verification_runs/hr_run1.txt")
run2 = parse_run("verification_runs/hr_run2.txt")
run3 = parse_run("verification_runs/hr_run3.txt")

print(f"Total parsed: before={len(before)}, run1={len(run1)}, run2={len(run2)}, run3={len(run3)}")
print(f"Pass count: before={sum(1 for c in before.values() if c['status']=='PASS')}, "
      f"run1={sum(1 for c in run1.values() if c['status']=='PASS')}, "
      f"run2={sum(1 for c in run2.values() if c['status']=='PASS')}, "
      f"run3={sum(1 for c in run3.values() if c['status']=='PASS')}")

print("\n--- CASE-BY-CASE COMPARISON (ONLY FLIPS / DIFFERENCES) ---")
all_cids = sorted(before.keys())
for cid in all_cids:
    s_b = before.get(cid, {}).get("status")
    s_1 = run1.get(cid, {}).get("status")
    s_2 = run2.get(cid, {}).get("status")
    s_3 = run3.get(cid, {}).get("status")
    a_b = before.get(cid, {}).get("actual")
    a_1 = run1.get(cid, {}).get("actual")
    a_2 = run2.get(cid, {}).get("actual")
    a_3 = run3.get(cid, {}).get("actual")
    arch = before.get(cid, {}).get("archetype")
    exp = before.get(cid, {}).get("expected")

    if not (s_b == s_1 == s_2 == s_3 and a_b == a_1 == a_2 == a_3):
        print(f"{cid} ({arch}, Exp: {exp}):")
        print(f"  Before: {s_b} ({a_b}%)")
        print(f"  Run 1 : {s_1} ({a_1}%)")
        print(f"  Run 2 : {s_2} ({a_2}%)")
        print(f"  Run 3 : {s_3} ({a_3}%)")
