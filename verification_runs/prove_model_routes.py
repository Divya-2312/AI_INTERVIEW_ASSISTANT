"""
Proof of real model routing across all modules and functions.
Verifies that:
- mockmate-hr100 is used for: HR answer evaluation, Java complexity
- llama3.2:3b is used for: Java theory Q+eval, DBMS theory Q+eval, Output prediction Q, Java coding Q, SQL Q
"""

import json
import requests
import sys

BASE_URL = "http://localhost:8000/api/ai"

def test_routes():
    results = {}
    print("=" * 60)
    print("RUNNING REAL MODEL ROUTING PROOFS AGAINST RUNNING OLLAMA")
    print("=" * 60)

    # 1. HR Answer Evaluation -> mockmate-hr100
    print("\n[1/7] Testing HR Answer Evaluation...")
    hr_payload = {
        "interviewType": "hr",
        "subject": "hr",
        "question": "Tell me about a time you faced a tight deadline. How did you handle it?",
        "answer": "In my previous internship, we had a critical release with 2 days left. I prioritized core features using the MoSCoW method, communicated with my team lead, and delivered on time.",
        "expectedConcepts": ["Prioritization and time management", "Clear communication with stakeholders", "Execution under pressure", "Successful outcome"],
        "questionFormat": "theory"
    }
    try:
        r = requests.post(f"{BASE_URL}/evaluate-answer", json=hr_payload, timeout=60)
        res = r.json()
        model_used = res.get("modelUsed")
        print(f"  Result: modelUsed = '{model_used}', score = {res.get('score')}, formula = {res.get('formula')}")
        results["hr_eval"] = {
            "status": "PASS" if "mockmate-hr100" in str(model_used) else "FAIL",
            "modelUsed": model_used,
            "score": res.get("score"),
            "formula": res.get("formula")
        }
    except Exception as e:
        print(f"  Error: {e}")
        results["hr_eval"] = {"status": "ERROR", "error": str(e)}

    # 2. Java Time & Space Complexity -> mockmate-hr100
    print("\n[2/7] Testing Java Complexity Analysis...")
    try:
        # Import directly to test complexity routing
        sys.path.insert(0, "ai-service")
        from app.models.llama_provider import LlamaModel
        model = LlamaModel()
        code = "public int findMax(int[] arr) { int max = arr[0]; for(int i=1; i<arr.length; i++) { if(arr[i] > max) max = arr[i]; } return max; }"
        cx_res = model._analyze_code_complexity("Find Max", code)
        model_used = cx_res.get("modelUsed")
        print(f"  Result: modelUsed = '{model_used}', time = {cx_res.get('timeComplexity')}, space = {cx_res.get('spaceComplexity')}")
        results["java_complexity"] = {
            "status": "PASS" if "mockmate-hr100" in str(model_used) else "FAIL",
            "modelUsed": model_used,
            "timeComplexity": cx_res.get("timeComplexity"),
            "spaceComplexity": cx_res.get("spaceComplexity")
        }
    except Exception as e:
        print(f"  Error: {e}")
        results["java_complexity"] = {"status": "ERROR", "error": str(e)}

    # 3. Java Theory Question + Evaluation -> llama3.2:3b
    print("\n[3/7] Testing Java Theory Q & Eval...")
    q_payload = {
        "interviewType": "technical",
        "subject": "java",
        "difficulty": "medium",
        "questionFormat": "theory",
        "sessionId": "proof-session-1"
    }
    try:
        r = requests.post(f"{BASE_URL}/generate-question", json=q_payload, timeout=60)
        q_res = r.json()
        q_model = q_res.get("modelUsed") or (q_res.get("_generation_meta") or {}).get("modelUsed")
        q_source = q_res.get("source")
        print(f"  Generated Q: '{q_res.get('questionText', '')[:60]}...' | modelUsed = '{q_model}', source = '{q_source}'")

        eval_payload = {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is the difference between Comparable and Comparator in Java?",
            "answer": "Comparable is implemented by the class itself via compareTo, providing a natural ordering. Comparator is a separate class defining compare for custom ordering.",
            "expectedConcepts": ["Comparable defines natural ordering via compareTo", "Comparator is external via compare", "Multiple comparator strategies"],
            "questionFormat": "theory"
        }
        r_eval = requests.post(f"{BASE_URL}/evaluate-answer", json=eval_payload, timeout=60)
        eval_res = r_eval.json()
        eval_model = eval_res.get("modelUsed")
        print(f"  Eval Result: modelUsed = '{eval_model}', score = {eval_res.get('score')}")
        results["java_theory"] = {
            "q_model": q_model,
            "q_source": q_source,
            "eval_model": eval_model,
            "eval_score": eval_res.get("score"),
            "status": "PASS" if "llama3.2:3b" in str(q_model) and "llama3.2:3b" in str(eval_model) else "FAIL"
        }
    except Exception as e:
        print(f"  Error: {e}")
        results["java_theory"] = {"status": "ERROR", "error": str(e)}

    # 4. DBMS Theory Question + Evaluation -> llama3.2:3b
    print("\n[4/7] Testing DBMS Theory Q & Eval...")
    q_payload = {
        "interviewType": "technical",
        "subject": "dbms",
        "difficulty": "medium",
        "questionFormat": "theory",
        "sessionId": "proof-session-2"
    }
    try:
        r = requests.post(f"{BASE_URL}/generate-question", json=q_payload, timeout=60)
        q_res = r.json()
        q_model = q_res.get("modelUsed") or (q_res.get("_generation_meta") or {}).get("modelUsed")
        print(f"  Generated Q: '{q_res.get('questionText', '')[:60]}...' | modelUsed = '{q_model}'")

        eval_payload = {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "Explain ACID properties in DBMS.",
            "answer": "Atomicity guarantees all or nothing, Consistency ensures valid state transitions, Isolation prevents concurrent transaction interference, and Durability ensures committed changes survive crashes.",
            "expectedConcepts": ["Atomicity: all or nothing", "Consistency: DB constraints preserved", "Isolation: concurrent safety", "Durability: persistent commits"],
            "questionFormat": "theory"
        }
        r_eval = requests.post(f"{BASE_URL}/evaluate-answer", json=eval_payload, timeout=60)
        eval_res = r_eval.json()
        eval_model = eval_res.get("modelUsed")
        print(f"  Eval Result: modelUsed = '{eval_model}', score = {eval_res.get('score')}")
        results["dbms_theory"] = {
            "q_model": q_model,
            "eval_model": eval_model,
            "status": "PASS" if "llama3.2:3b" in str(q_model) and "llama3.2:3b" in str(eval_model) else "FAIL"
        }
    except Exception as e:
        print(f"  Error: {e}")
        results["dbms_theory"] = {"status": "ERROR", "error": str(e)}

    # 5. Output Prediction Question -> llama3.2:3b
    print("\n[5/7] Testing Output Prediction Q...")
    q_payload = {
        "interviewType": "technical",
        "subject": "java",
        "difficulty": "medium",
        "questionFormat": "output_prediction",
        "sessionId": "proof-session-3"
    }
    try:
        r = requests.post(f"{BASE_URL}/generate-question", json=q_payload, timeout=60)
        q_res = r.json()
        q_model = q_res.get("modelUsed") or (q_res.get("_generation_meta") or {}).get("modelUsed")
        print(f"  Generated Q snippet: '{str(q_res.get('codeSnippet'))[:40]}...' | modelUsed = '{q_model}'")
        results["output_prediction_q"] = {
            "q_model": q_model,
            "status": "PASS" if "llama3.2:3b" in str(q_model) else "FAIL"
        }
    except Exception as e:
        print(f"  Error: {e}")
        results["output_prediction_q"] = {"status": "ERROR", "error": str(e)}

    # 6. Java Coding Question -> llama3.2:3b
    print("\n[6/7] Testing Java Coding Q...")
    q_payload = {
        "interviewType": "technical",
        "subject": "java",
        "difficulty": "medium",
        "questionFormat": "coding",
        "language": "java",
        "sessionId": "proof-session-4"
    }
    try:
        r = requests.post(f"{BASE_URL}/generate-question", json=q_payload, timeout=120)
        q_res = r.json()
        q_model = q_res.get("modelUsed") or (q_res.get("_generation_meta") or {}).get("modelUsed")
        print(f"  Generated Q: '{q_res.get('title')}' | modelUsed = '{q_model}'")
        results["java_coding_q"] = {
            "q_model": q_model,
            "status": "PASS" if "llama3.2:3b" in str(q_model) else "FAIL"
        }
    except Exception as e:
        print(f"  Error: {e}")
        results["java_coding_q"] = {"status": "ERROR", "error": str(e)}

    # 7. SQL Coding Question -> llama3.2:3b
    print("\n[7/7] Testing SQL Question...")
    q_payload = {
        "interviewType": "technical",
        "subject": "dbms",
        "difficulty": "medium",
        "questionFormat": "coding",
        "language": "sql",
        "sessionId": "proof-session-5"
    }
    try:
        r = requests.post(f"{BASE_URL}/generate-question", json=q_payload, timeout=120)
        q_res = r.json()
        q_model = q_res.get("modelUsed") or (q_res.get("_generation_meta") or {}).get("modelUsed")
        print(f"  Generated Q: '{q_res.get('title')}' | modelUsed = '{q_model}'")
        results["sql_q"] = {
            "q_model": q_model,
            "status": "PASS" if "llama3.2:3b" in str(q_model) else "FAIL"
        }
    except Exception as e:
        print(f"  Error: {e}")
        results["sql_q"] = {"status": "ERROR", "error": str(e)}

    print("\n" + "=" * 60)
    print("PROOFS SUMMARY:")
    print(json.dumps(results, indent=2))
    print("=" * 60)

    with open("verification_runs/model_routing_proofs.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    test_routes()
