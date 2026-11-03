"""
prove_generation_routes.py
Executes the real route proof for Java coding question, SQL question,
output-prediction question, and DBMS question generation against the running AI microservice,
recording and printing the exact modelUsed and source of each.
"""

import time
import json
import requests
import sys

BASE_URL = "http://localhost:8000/api/ai"


def prove_generation_routes():
    print("=" * 70)
    print("PROVING QUESTION GENERATION ROUTES (REAL RUN AGAINST AI SERVICE)")
    print("=" * 70)

    routes = [
        {
            "name": "DBMS Theory Question",
            "payload": {
                "interviewType": "technical",
                "subject": "dbms",
                "difficulty": "medium",
                "questionFormat": "theory",
                "sessionId": "route-proof-dbms-th",
            },
        },
        {
            "name": "Output Prediction Question",
            "payload": {
                "interviewType": "technical",
                "subject": "java",
                "difficulty": "medium",
                "questionFormat": "output_prediction",
                "sessionId": "route-proof-output-pred",
            },
        },
        {
            "name": "Java Coding Question",
            "payload": {
                "interviewType": "technical",
                "subject": "java",
                "difficulty": "medium",
                "questionFormat": "coding",
                "language": "java",
                "sessionId": "route-proof-java-coding",
            },
        },
        {
            "name": "SQL Question",
            "payload": {
                "interviewType": "technical",
                "subject": "dbms",
                "difficulty": "medium",
                "questionFormat": "coding",
                "language": "sql",
                "sessionId": "route-proof-sql-coding",
            },
        },
    ]

    results = []

    for route in routes:
        print(f"\nTesting {route['name']}...")
        t0 = time.time()
        try:
            r = requests.post(f"{BASE_URL}/generate-question", json=route["payload"], timeout=120)
            elapsed = time.time() - t0
            data = r.json()
            source = data.get("source")
            model_used = data.get("modelUsed")
            title = data.get("title") or (data.get("questionText") or "")[:50]
            print(f"  Status: HTTP {r.status_code} in {elapsed:.2f}s")
            print(f"  source: '{source}'")
            print(f"  modelUsed: '{model_used}'")
            print(f"  Question/Title: '{title}'")

            results.append({
                "route": route["name"],
                "http_status": r.status_code,
                "elapsed_sec": round(elapsed, 2),
                "source": source,
                "modelUsed": model_used,
                "title": title,
            })
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  Error after {elapsed:.2f}s: {e}")
            results.append({
                "route": route["name"],
                "error": str(e),
                "elapsed_sec": round(elapsed, 2),
            })

    print("\n" + "=" * 70)
    print("ROUTING PROOF SUMMARY:")
    print(json.dumps(results, indent=2))
    print("=" * 70)

    with open("verification_runs/route_proof_results.json", "w") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    prove_generation_routes()
