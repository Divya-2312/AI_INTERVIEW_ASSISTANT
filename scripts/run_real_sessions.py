import requests
import json
import base64
import hmac
import hashlib

def make_jwt(user_id):
    h = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b'=')
    p = base64.urlsafe_b64encode(json.dumps({"id": str(user_id), "iat": 1793100000, "exp": 1993100000}).encode()).rstrip(b'=')
    sig = base64.urlsafe_b64encode(hmac.new(b"your_jwt_secret_key_here", h + b"." + p, hashlib.sha256).digest()).rstrip(b'=')
    return f"{h.decode()}.{p.decode()}.{sig.decode()}"

uid = "6ae09d1662df44e67e5474d1"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {make_jwt(uid)}"}

def run_sess(subject, num):
    r = requests.post(
        "http://127.0.0.1:5000/api/interviews",
        json={"type": "technical", "subject": subject, "difficulty": "medium", "questionFormat": "theory"},
        headers=headers,
        timeout=30
    )
    d = r.json()
    iid = d["interview"]["_id"]
    qs = [d["firstQuestion"]]
    cur = d["firstQuestion"]
    for idx in range(1, 10):
        ans_r = requests.post(
            f"http://127.0.0.1:5000/api/interviews/{iid}/answers",
            json={
                "questionId": cur.get("id") or cur.get("questionId") or f"q-{idx}",
                "questionText": cur.get("questionText", ""),
                "answerText": "irrelevant answer",
                "questionFormat": "theory",
                "expectedConcepts": cur.get("expectedConcepts", [])
            },
            headers=headers,
            timeout=30
        )
        nxt = ans_r.json().get("nextQuestion")
        if not nxt:
            break
        qs.append(nxt)
        cur = nxt

    print(f"================================================================================")
    print(f"REAL APP: {subject.upper()} SESSION {num} (Interview ID: {iid})")
    print(f"================================================================================")
    for i, q in enumerate(qs, 1):
        print(f"  Q{i:02d} [{q.get('id')}]: {q.get('questionText')}")
    print()

if __name__ == "__main__":
    for i in range(1, 4):
        run_sess("java", i)
    for i in range(1, 4):
        run_sess("dbms", i)
