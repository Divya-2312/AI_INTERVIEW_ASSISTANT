import time
import json
import os
import sys

# Add ai-service to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai-service")))

from app.models.schemas import QuestionGenerationRequest
from app.services.question_generator import question_generator


def measure_generation():
    print("==================================================================")
    print("Measuring Generation Times and Sources for Java Coding & SQL (DBMS)")
    print("==================================================================")

    results = {"java_coding": [], "sql_coding": []}

    # 1. Measure 5 Java Coding Questions
    print("\n--- Generating 5 Java Coding Questions ---")
    java_prev = []
    sess_id = f"benchmark_java_{int(time.time())}"
    for i in range(1, 6):
        req = QuestionGenerationRequest(
            interviewType="technical",
            subject="java",
            difficulty="medium",
            questionFormat="coding",
            previousQuestions=list(java_prev),
            sessionId=sess_id,
        )
        t0 = time.time()
        res = question_generator.generate(req)
        elapsed = time.time() - t0
        q_dict = res.dict() if hasattr(res, "dict") else res.model_dump()
        source = q_dict.get("source")
        model_used = q_dict.get("modelUsed")
        title = q_dict.get("title") or q_dict.get("questionText", "")[:40]

        java_prev.append(q_dict.get("questionText") or q_dict.get("title"))
        entry = {
            "index": i,
            "subject": "java",
            "time_sec": round(elapsed, 2),
            "source": source,
            "modelUsed": model_used,
            "title": title,
        }
        results["java_coding"].append(entry)
        print(f"  Java Q{i}: {elapsed:.2f}s | source: '{source}' | modelUsed: '{model_used}' | title: '{title}'")

    # 2. Measure 5 SQL (DBMS) Questions
    print("\n--- Generating 5 SQL (DBMS) Coding Questions ---")
    sql_prev = []
    sess_id_sql = f"benchmark_sql_{int(time.time())}"
    for i in range(1, 6):
        req = QuestionGenerationRequest(
            interviewType="technical",
            subject="dbms",
            difficulty="medium",
            questionFormat="coding",
            previousQuestions=list(sql_prev),
            sessionId=sess_id_sql,
        )
        t0 = time.time()
        res = question_generator.generate(req)
        elapsed = time.time() - t0
        q_dict = res.dict() if hasattr(res, "dict") else res.model_dump()
        source = q_dict.get("source")
        model_used = q_dict.get("modelUsed")
        title = q_dict.get("title") or q_dict.get("questionText", "")[:40]

        sql_prev.append(q_dict.get("questionText") or q_dict.get("title"))
        entry = {
            "index": i,
            "subject": "dbms (sql)",
            "time_sec": round(elapsed, 2),
            "source": source,
            "modelUsed": model_used,
            "title": title,
        }
        results["sql_coding"].append(entry)
        print(f"  SQL Q{i}: {elapsed:.2f}s | source: '{source}' | modelUsed: '{model_used}' | title: '{title}'")

    out_file = os.path.join(os.path.dirname(__file__), "timing_benchmark_results.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved benchmark results to {out_file}")
    return results


if __name__ == "__main__":
    measure_generation()
