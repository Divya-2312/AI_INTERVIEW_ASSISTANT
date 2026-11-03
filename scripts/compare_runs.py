import re
import sys

def parse_run(filepath):
    cases = {}
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.search(r'\[(PASS|MISS)\]\s+(C\d+)\s+\|\s+Archetype:\s+(\w+)\s+\|\s+Expected:\s+\[\s*(\d+),\s*(\d+)\]\s+\|\s+Actual:\s+(\d+)%\s+\|\s+Sub-scores:\s+R=(\d+)%\s+C=(\d+)%\s+A=(\d+)%\s+Comm=(\d+)%', line)
            if m:
                status, cid, arch, exp_low, exp_high, score, r, c, a, comm = m.groups()
                cases[cid] = {
                    'status': status,
                    'score': int(score),
                    'arch': arch,
                    'expected': f"[{exp_low}, {exp_high}]",
                    'R': int(r), 'C': int(c), 'A': int(a), 'Comm': int(comm)
                }
    return cases

if __name__ == "__main__":
    file1 = sys.argv[1] if len(sys.argv) > 1 else 'verification_runs/hr_run1.txt'
    file2 = sys.argv[2] if len(sys.argv) > 2 else 'verification_runs/hr_run2.txt'
    r1 = parse_run(file1)
    r2 = parse_run(file2)
    print(f"File 1: {file1} ({len(r1)} cases)")
    print(f"File 2: {file2} ({len(r2)} cases)")
    diffs = []
    for cid in sorted(r1.keys()):
        c1 = r1[cid]
        c2 = r2.get(cid, {})
        if c1 != c2:
            diffs.append((cid, c1, c2))
    print(f"Differences: {len(diffs)} cases")
    for cid, c1, c2 in diffs:
        print(f"  {cid} ({c1['arch']} exp={c1['expected']}):")
        print(f"    {file1}: {c1['status']} Score={c1['score']}% (R={c1['R']}% C={c1['C']}% A={c1['A']}% Comm={c1['Comm']}%)")
        print(f"    {file2}: {c2['status']} Score={c2['score']}% (R={c2['R']}% C={c2['C']}% A={c2['A']}% Comm={c2['Comm']}%)")
