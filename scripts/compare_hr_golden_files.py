def clean_file(path):
    with open(path, 'rb') as f:
        raw = f.read()
    # Decode handling BOM or UTF-16 or UTF-8
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        text = raw.decode('utf-16')
    elif raw.startswith(b'\xef\xbb\xbf'):
        text = raw.decode('utf-8-sig')
    else:
        text = raw.decode('utf-8', errors='replace')
    # Normalize newlines
    lines = [l.strip('\r') for l in text.split('\n')]
    # If file has blank lines after every line (166 vs 83), strip empty lines
    non_empty = [l for l in lines if l.strip()]
    return non_empty

t1 = clean_file('verification_runs/hr_golden_before.txt')
t2 = clean_file('verification_runs/hr_golden_after.txt')

print(f"Cleaned line counts: before={len(t1)}, after={len(t2)}")
diffs = [(i+1, l1, l2) for i, (l1, l2) in enumerate(zip(t1, t2)) if l1 != l2]
print(f"Different lines count: {len(diffs)}")
for line_no, l1, l2 in diffs:
    print(f"Line {line_no}:")
    print(f"  < BEFORE: {l1}")
    print(f"  > AFTER : {l2}")

# Write both back as clean UTF-8 without BOM and with standard \n
with open('verification_runs/hr_golden_before.txt', 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(t1) + '\n')
with open('verification_runs/hr_golden_after.txt', 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(t2) + '\n')
print("Successfully normalized both files to clean UTF-8 with standard newlines.")
