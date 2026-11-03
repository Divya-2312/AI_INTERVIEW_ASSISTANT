import json
import os
import sys

sys.path.insert(0, os.path.abspath("ai-service"))

from app.models.llama_provider import (
    DevFallbackModel,
    LlamaModel,
    find_theory_item,
    _evaluate_theory_with_rubric,
    THEORY_T_COVER,
    THEORY_T_PARTIAL,
    THEORY_SIDE_CAP_MARGIN,
)
from app.services.embedding_service import embedding_service

def run_all_b6():
    fb = DevFallbackModel()
    results = {}

    # 1. Java / DBMS Theory (5 examples)
    print("=== 1. Java / DBMS Theory ===")
    theory_ex = [
        ("java-001-good", "What is encapsulation in Java and why is it useful?", 
         "Encapsulation means wrapping fields and methods together in a single class while keeping fields private with getters and setters to protect internal state."),
        ("java-001-partial", "What is encapsulation in Java and why is it useful?",
         "Encapsulation means keeping data inside a class using getters and setters so other classes don't mess with it directly."),
        ("java-081-reversed", "What is the benefit of using generics instead of raw Object types in collections?",
         "generics let you store any type in one list together like int and String mixed, raw objects only allow one type"),
        ("java-001-wrong", "What is encapsulation in Java and why is it useful?",
         "encapsulation means making a class inside another class so it is hidden, it is useful becoz then you dont need constructors"),
        ("dbms-001-vague", "What is a primary key?",
         "primary key is a database key used in sql tables"),
    ]
    theory_res = []
    for cid, q, ans in theory_ex:
        cat = find_theory_item(q)
        r = _evaluate_theory_with_rubric(q, ans, cat["referenceAnswer"], embedding_service, cat.get("expectedConcepts", []))
        theory_res.append({
            "id": cid, "question": q, "answer": ans,
            "score": r["score"], "relevance": r["relevance"],
            "correctness": r["correctness"], "conceptCoverage": r["conceptCoverage"],
            "communication": r["communication"], "scoreReason": r["scoreReason"]
        })
        print(f"[{cid}] Score={r['score']}% (Rel={r['relevance']}, Cor={r['correctness']}, Cov={r['conceptCoverage']}, Com={r['communication']})")
    results["theory"] = theory_res

    # 2. Output Prediction (5 examples)
    print("\n=== 2. Output Prediction ===")
    op_cases = [
        ("op-right-1", "10", "10"),
        ("op-right-2", "true", "true"),
        ("op-wrong-val", "15", "10"),
        ("op-wrong-type", "Error", "10"),
        ("op-empty", "", "10"),
    ]
    op_res = []
    for cid, ans, expected in op_cases:
        r = fb.evaluate_answer("What does this code snippet print?", ans, ["variables"], [],
                                question_format="output_prediction", expected_output=expected)
        op_res.append({"id": cid, "answer": ans, "expected": expected, "score": r["score"], "isCorrect": r["score"] == 100})
        print(f"[{cid}] Answer='{ans}' Expected='{expected}' -> Score={r['score']}%")
    results["output_prediction"] = op_res

    # 3. Java Coding (5 examples)
    print("\n=== 3. Java Coding ===")
    java_tc = [
        {"input": "2 3", "expectedOutput": "5", "label": "Sample 1"},
        {"input": "-1 5", "expectedOutput": "4", "label": "Sample 2"},
        {"input": "0 0", "expectedOutput": "0", "label": "Sample 3"},
    ]
    java_cases = [
        ("code-perfect", "public class Solution { public static int solve(int a, int b) { return a + b; } }"),
        ("code-partial", "public class Solution { public static int solve(int a, int b) { if (a > 0) return a + b; return 0; } }"),
        ("code-compile-err", "public class Solution { public static int solve(int a, int b) { return a + ; } }"),
        ("code-wrong-logic", "public class Solution { public static int solve(int a, int b) { return a * b; } }"),
        ("code-empty", ""),
    ]
    java_res = []
    for cid, code in java_cases:
        r = fb.evaluate_answer("Write a Java method solve(int a, int b) to return sum.", code, ["methods"], [],
                                question_format="coding", language="java", test_cases=java_tc)
        java_res.append({"id": cid, "score": r["score"], "passedTests": r.get("passedTests"), "totalTests": r.get("totalTests"), "feedback": r.get("feedback")[:80]})
        print(f"[{cid}] Score={r['score']}% passed={r.get('passedTests')}/{r.get('totalTests')}")
    results["java_coding"] = java_res

    # 4. SQL Coding (5 examples)
    print("\n=== 4. SQL Coding ===")
    sql_schema = "CREATE TABLE employees (id INT PRIMARY KEY, name TEXT, salary INT, dept TEXT);"
    sql_sample = (
        "INSERT INTO employees VALUES (1, 'Alice', 70000, 'Eng');\n"
        "INSERT INTO employees VALUES (2, 'Bob', 50000, 'HR');\n"
        "INSERT INTO employees VALUES (3, 'Charlie', 80000, 'Eng');"
    )
    sql_tc = [
        {"input": "", "expectedOutput": "Charlie|80000", "label": "Highest Eng salary"}
    ]
    sql_cases = [
        ("sql-perfect", "SELECT name, salary FROM employees WHERE dept = 'Eng' ORDER BY salary DESC LIMIT 1;"),
        ("sql-wrong-where", "SELECT name, salary FROM employees WHERE dept = 'HR' ORDER BY salary DESC LIMIT 1;"),
        ("sql-syntax-err", "SELECT name salary FROM employees WHERE"),
        ("sql-missing-limit", "SELECT name, salary FROM employees WHERE dept = 'Eng' ORDER BY salary DESC;"),
        ("sql-empty", ""),
    ]
    sql_res = []
    for cid, query in sql_cases:
        r = fb.evaluate_answer("Find highest paid engineer.", query, ["SELECT"], [],
                                question_format="coding", language="sql",
                                schema=sql_schema, sample_data=sql_sample, test_cases=sql_tc)
        sql_res.append({"id": cid, "score": r["score"], "feedback": r.get("feedback")[:80]})
        print(f"[{cid}] Score={r['score']}% feedback={r.get('feedback')[:60]}")
    results["sql_coding"] = sql_res

    # 5. Big-O Complexity (5 examples)
    print("\n=== 5. Big-O Complexity ===")
    llama = LlamaModel()
    bigo_cases = [
        ("bigo-linear", "public int find(int[] arr) { for(int x : arr) if(x == 5) return 1; return 0; }"),
        ("bigo-quadratic", "public void bubble(int[] a) { for(int i=0;i<a.length;i++) for(int j=0;j<a.length;j++) {} }"),
        ("bigo-constant", "public int first(int[] a) { return a[0]; }"),
        ("bigo-logarithmic", "public int binSearch(int[] a, int k) { int l=0, r=a.length-1; while(l<=r) { int m=(l+r)/2; if(a[m]==k) return m; else if(a[m]<k) l=m+1; else r=m-1; } return -1; }"),
        ("bigo-nlogn", "public void sort(int[] a) { java.util.Arrays.sort(a); }"),
    ]
    bigo_res = []
    for cid, code in bigo_cases:
        r = llama._analyze_code_complexity("Coding problem", code, "java")
        bigo_res.append({
            "id": cid, "time": r.get("timeComplexity"), "space": r.get("spaceComplexity"),
            "usedFallback": r.get("scoringSource") != "fine_tuned_llama", "modelUsed": r.get("modelUsed")
        })
        print(f"[{cid}] Time={r.get('timeComplexity')} Space={r.get('spaceComplexity')} (model={r.get('modelUsed')})")
    results["bigo"] = bigo_res

    with open("verification_runs/b6_predefined_scoring_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nSuccessfully saved results to verification_runs/b6_predefined_scoring_results.json")

if __name__ == "__main__":
    run_all_b6()
