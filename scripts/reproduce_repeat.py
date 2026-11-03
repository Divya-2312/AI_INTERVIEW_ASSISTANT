import base64
import hashlib
import hmac
import json
import os
import sys
import requests

BACKEND_URL = "http://127.0.0.1:5000"
JWT_SECRET = "your_jwt_secret_key_here"


def make_jwt(user_id: str, secret: str = JWT_SECRET) -> str:
    h = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b'=')
    p = base64.urlsafe_b64encode(json.dumps({"id": str(user_id), "iat": 1793100000, "exp": 1993100000}).encode()).rstrip(b'=')
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), h + b'.' + p, hashlib.sha256).digest()).rstrip(b'=')
    return f"{h.decode()}.{p.decode()}.{sig.decode()}"


def run_session(user_id: str, subject: str, difficulty: str = "medium", question_format: str = "theory", num_questions: int = 10):
    token = make_jwt(user_id)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 1. Start session
    payload = {
        "type": "technical",
        "subject": subject,
        "difficulty": difficulty,
        "questionFormat": question_format
    }
    r = requests.post(f"{BACKEND_URL}/api/interviews", json=payload, headers=headers, timeout=30)
    if r.status_code != 201:
        raise RuntimeError(f"Failed to start interview: {r.status_code} {r.text}")

    data = r.json()
    interview_id = data["interview"]["_id"]
    first_q = data["firstQuestion"]

    questions = [{
        "id": first_q.get("id") or first_q.get("questionId") or "q-1",
        "text": first_q.get("questionText", ""),
        "category": first_q.get("category", ""),
    }]

    current_q = first_q

    # 2. Advance through remaining questions
    for idx in range(1, num_questions):
        q_id = current_q.get("id") or current_q.get("questionId") or f"q-{idx}"
        q_text = current_q.get("questionText", "")

        answer_payload = {
            "questionId": q_id,
            "questionText": q_text,
            "answerText": "irrelevant",
            "questionFormat": question_format,
            "expectedConcepts": current_q.get("expectedConcepts") or [],
            "referenceAnswer": current_q.get("referenceAnswer") or "",
        }

        r2 = requests.post(f"{BACKEND_URL}/api/interviews/{interview_id}/answers", json=answer_payload, headers=headers, timeout=30)
        if r2.status_code != 200:
            raise RuntimeError(f"Failed to submit answer for q {idx}: {r2.status_code} {r2.text}")

        res_data = r2.json()
        next_q = res_data.get("nextQuestion")
        if not next_q:
            break

        questions.append({
            "id": next_q.get("id") or next_q.get("questionId") or f"q-{idx+1}",
            "text": next_q.get("questionText", ""),
            "category": next_q.get("category", ""),
        })
        current_q = next_q

    return {
        "interview_id": interview_id,
        "user_id": user_id,
        "subject": subject,
        "difficulty": difficulty,
        "questions": questions
    }


def main():
    out_file = sys.argv[1] if len(sys.argv) > 1 else "verification_runs/repeat_baseline.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    # Fetch users from MongoDB via mongo or direct ids
    # Test user for "same user"
    same_user_id = "6ae09d1662df44e67e5474d1"

    # 20 distinct user ids
    different_user_ids = [
        "6a7b41fd664c3c2e9efd6adc",
        "6a7c3c7d61b50a57b14eb1d8",
        "6aabbce347fbbdcbafeb3811",
        "6aabbf1e47fbbdcbafeb381b",
        "6aabc18a47fbbdcbafeb3824",
        "6ac775d84f23ff495584036e",
        "6ace822da3109abacfbba0d1",
        "6ace822da3109abacfbba0d2",
        "6aced2f0361c49f4f36e1bd4",
        "6acf8f42b62fb9987cbc665f",
        "6ad658e1bedacfbb9df3bbb5",
        "6ad6b67e100ddb9032bacd5c",
        "6ad6b6a3100ddb9032bacd62",
        "6ad6b736b96edbd17fdf82ff",
        "6ad6baa784a51a618c77a51d",
        "6ad6bc81b5b6f8fee1e3383c",
        "6ad70c29764f31d6cc07d091",
        "6ad70c7b764f31d6cc07d094",
        "6ad70cac764f31d6cc07d09d",
        "6ad73dbb764f31d6cc07d0a6",
    ]

    print("=================================================================")
    print(f"Running 20 sessions for SAME user ({same_user_id})...")
    same_user_sessions = []
    # 10 Java + 10 DBMS
    for i in range(10):
        print(f"  [Same User] Session {i+1}/20: Java...", flush=True)
        s = run_session(same_user_id, "java")
        same_user_sessions.append(s)

    for i in range(10):
        print(f"  [Same User] Session {i+11}/20: DBMS...", flush=True)
        s = run_session(same_user_id, "dbms")
        same_user_sessions.append(s)

    print("\nRunning 20 sessions for DIFFERENT users...")
    diff_user_sessions = []
    for i, uid in enumerate(different_user_ids[:10]):
        print(f"  [Diff User] Session {i+1}/20 (User {uid[:8]}): Java...", flush=True)
        s = run_session(uid, "java")
        diff_user_sessions.append(s)

    for i, uid in enumerate(different_user_ids[10:20]):
        print(f"  [Diff User] Session {i+11}/20 (User {uid[:8]}): DBMS...", flush=True)
        s = run_session(uid, "dbms")
        diff_user_sessions.append(s)

    results = {
        "same_user_sessions": same_user_sessions,
        "different_user_sessions": diff_user_sessions
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved raw data to {out_file}")

    # Compute Statistics
    def analyze_sessions(name, sessions):
        print(f"\n--- Analysis for {name} ---")
        total_q = sum(len(s["questions"]) for s in sessions)
        all_ids = [q["id"] for s in sessions for q in s["questions"]]
        all_texts = [q["text"] for s in sessions for q in s["questions"]]
        distinct_ids = len(set(all_ids))
        distinct_texts = len(set(all_texts))

        print(f"Total questions generated across {len(sessions)} sessions: {total_q}")
        print(f"Distinct question IDs: {distinct_ids}")
        print(f"Distinct question Texts: {distinct_texts}")

        # Overlap between consecutive sessions of same subject
        overlaps = []
        for i in range(len(sessions) - 1):
            if sessions[i]["subject"] == sessions[i+1]["subject"]:
                q_set_a = set(q["text"] for q in sessions[i]["questions"])
                q_set_b = set(q["text"] for q in sessions[i+1]["questions"])
                intersection = q_set_a.intersection(q_set_b)
                overlap_pct = (len(intersection) / max(len(q_set_a), 1)) * 100.0
                overlaps.append(overlap_pct)

        avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
        print(f"Average overlap between consecutive same-subject sessions: {avg_overlap:.2f}%")
        if overlaps:
            print(f"Per-step consecutive overlaps: {[round(x, 1) for x in overlaps]}")

        # First question variety
        first_questions = [s["questions"][0]["text"] for s in sessions]
        distinct_first = len(set(first_questions))
        print(f"First-question distinct count: {distinct_first} / {len(sessions)}")

    analyze_sessions("Same User (20 sessions)", same_user_sessions)
    analyze_sessions("Different Users (20 sessions)", diff_user_sessions)

    # Print first 5 questions of 5 sessions
    print("\n=================================================================")
    print("FIRST 5 QUESTIONS OF 5 SESSIONS (Same User Java):")
    print("=================================================================")
    for s_idx in range(min(5, len(same_user_sessions))):
        sess = same_user_sessions[s_idx]
        print(f"\nSession {s_idx + 1} ({sess['subject']}):")
        for q_idx in range(min(5, len(sess["questions"]))):
            q = sess["questions"][q_idx]
            print(f"  Q{q_idx + 1} [{q['id']}]: {q['text']}")


if __name__ == "__main__":
    main()
