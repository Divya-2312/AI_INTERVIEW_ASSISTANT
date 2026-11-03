with open('verification_runs/hr_golden_before.log', 'r', encoding='utf-8') as f:
    before_lines = [l.strip() for l in f if l.startswith('[PASS]') or l.startswith('[MISS]')]

for enc in ['utf-16', 'utf-16-le', 'utf-8']:
    try:
        with open('verification_runs/hr_golden_after.log', 'r', encoding=enc) as f:
            after_lines = [l.strip() for l in f if l.startswith('[PASS]') or l.startswith('[MISS]')]
        if after_lines:
            break
    except:
        pass

print(f"Before cases: {len(before_lines)}, After cases: {len(after_lines)}")
print(f"{'Case':<6} | {'Archetype':<16} | {'Expected':<12} | {'Before Score':<14} | {'After Score':<14} | {'Before':<6} | {'After':<6}")
print("-" * 85)
for b, a in zip(before_lines, after_lines):
    b_id = b.split('|')[0].split()[1]
    arch = b.split('|')[1].split(':')[1].strip()
    exp = b.split('|')[2].split(':')[1].strip()
    b_score = b.split('|')[3].split(':')[1].strip()
    a_score = a.split('|')[3].split(':')[1].strip()
    b_stat = 'PASS' if b.startswith('[PASS]') else 'MISS'
    a_stat = 'PASS' if a.startswith('[PASS]') else 'MISS'
    print(f"{b_id:<6} | {arch:<16} | {exp:<12} | {b_score:<14} | {a_score:<14} | {b_stat:<6} | {a_stat:<6}")
