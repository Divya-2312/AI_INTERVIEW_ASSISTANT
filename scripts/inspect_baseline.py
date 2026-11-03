import json

with open('verification_runs/repeat_baseline.json') as f:
    data = json.load(f)

same_sessions = data.get('same_user_sessions', [])
diff_sessions = data.get('different_user_sessions', [])

print(f"Same user sessions: {len(same_sessions)}")
print(f"Different user sessions: {len(diff_sessions)}")

for idx, s in enumerate(same_sessions):
    q_diffs = [q.get('difficulty', s.get('difficulty', 'medium')) for q in s.get('questions', [])]
    print(f"Session {idx+1:02d} ({s.get('subject')}, {s.get('difficulty')}): {len(s.get('questions', []))} questions, question difficulties: {q_diffs}")
