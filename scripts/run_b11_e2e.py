import json
import os
import sys

sys.path.insert(0, os.path.abspath("ai-service"))

from app.models.llama_provider import get_ai_model_provider, find_theory_item
from app.models.schemas import AnswerEvaluationRequest
from app.services.answer_evaluator import AnswerEvaluator
from app.services.rag_service import rag_service

def run_e2e():
    evaluator = AnswerEvaluator()
    output_lines = []

    def log(msg=""):
        print(msg)
        output_lines.append(msg)

    log("# End-to-End Interview Evaluation Results (Task B11)")
    log("Generated via automated end-to-end evaluation script across all interview types.\n")

    sessions = [
        {
            "name": "1. Java Theory",
            "type": "technical",
            "subject": "java",
            "format": "theory",
            "question": "What is the difference between ArrayList and LinkedList?",
            "expectedConcepts": ["ArrayList uses dynamic array", "LinkedList uses doubly-linked list", "index-based access", "insertion/deletion efficiency"],
            "cases": [
                ("Good", "ArrayList is backed by a dynamic resizable array which offers fast O(1) random access by index. LinkedList is implemented as a doubly-linked list where nodes store data and references to next/previous nodes, providing efficient O(1) insertions or deletions at ends but slower O(n) random search."),
                ("Partial", "ArrayList uses an array inside so searching by index is very fast. LinkedList uses nodes pointing to each other which makes adding elements faster without resizing arrays."),
                ("Wrong", "ArrayList stores primitive numbers in stack memory while LinkedList is only for saving images and files on disk."),
            ]
        },
        {
            "name": "2. DBMS Theory",
            "type": "technical",
            "subject": "dbms",
            "format": "theory",
            "question": "What is a foreign key?",
            "expectedConcepts": ["references primary key", "referential integrity", "parent-child relationship"],
            "cases": [
                ("Good", "A foreign key is a column or set of columns in a table that references the primary key of another table, establishing a relationship between them and enforcing referential integrity to prevent orphaned rows."),
                ("Partial", "A foreign key connects two database tables together by pointing to the id of another table so they stay linked."),
                ("Wrong", "A foreign key is an encryption password imported from a foreign computer server to unlock the database."),
            ]
        },
        {
            "name": "3. Output Prediction",
            "type": "technical",
            "subject": "java",
            "format": "output_prediction",
            "question": "What does this code print?\n```java\nint x = 5;\nSystem.out.println(x++ + ++x);\n```",
            "expectedOutput": "12",
            "expectedConcepts": ["pre-increment", "post-increment"],
            "cases": [
                ("Good", "12"),
                ("Partial (Close Misconception)", "11"),
                ("Wrong", "Error"),
            ]
        },
        {
            "name": "4. Java Coding",
            "type": "technical",
            "subject": "java",
            "format": "coding",
            "question": "Implement a method add(int a, int b) that returns the sum of two integers.",
            "expectedConcepts": ["methods", "addition"],
            "testCases": [
                {"input": "2, 3", "expectedOutput": "5", "label": "Case 1: positive"},
                {"input": "-1, 5", "expectedOutput": "4", "label": "Case 2: negative"},
                {"input": "10, -5", "expectedOutput": "5", "label": "Case 3: mixed"},
            ],
            "cases": [
                ("Good (Correct Logic)", "public class Solution { public static int add(int a, int b) { return a + b; } }"),
                ("Partial (Passes 2 of 3)", "public class Solution { public static int add(int a, int b) { if (a > 0) return a + b; return 0; } }"),
                ("Wrong (Syntax Error)", "public class Solution { public static int add(int a, int b) { return a + ; } }"),
            ]
        },
        {
            "name": "5. SQL Coding",
            "type": "technical",
            "subject": "dbms",
            "language": "sql",
            "format": "coding",
            "question": "Find the names and salaries of employees earning strictly more than 60,000.",
            "schema": "CREATE TABLE employees (id INT PRIMARY KEY, name TEXT, salary INT);",
            "sampleData": "INSERT INTO employees VALUES (1, 'Alice', 70000);\nINSERT INTO employees VALUES (2, 'Bob', 50000);\nINSERT INTO employees VALUES (3, 'Charlie', 80000);",
            "testCases": [
                {"input": "", "expectedOutput": "Alice|70000\nCharlie|80000", "label": "Salary > 60000"}
            ],
            "expectedConcepts": ["SELECT", "WHERE clause"],
            "cases": [
                ("Good", "SELECT name, salary FROM employees WHERE salary > 60000 ORDER BY salary ASC;"),
                ("Partial (Wrong Salary Threshold)", "SELECT name, salary FROM employees WHERE salary >= 50000 ORDER BY salary ASC;"),
                ("Wrong (Syntax Error)", "SELECT FROM employees WHERE"),
            ]
        },
        {
            "name": "6. HR Behavioral Round",
            "type": "hr",
            "subject": "hr",
            "format": "theory",
            "question": "Tell me about a time you worked in a team.",
            "expectedConcepts": ["teamwork", "communication", "role and collaboration", "resolution and outcome"],
            "cases": [
                ("Good (STAR)", "During my final year engineering project, I worked in a 4-person team building a campus portal. When our backend integration faced delays due to schema mismatch, I organized a daily 15-minute sync, defined standard JSON schemas, and we successfully delivered the portal on time with zero production bugs."),
                ("Partial (Average)", "In college I worked with classmates on a group assignment. We divided the sections among ourselves, worked together, and submitted the presentation on the due date."),
                ("Wrong (Irrelevant)", "Java supports object oriented programming and uses garbage collection to free memory from the heap."),
            ]
        }
    ]

    for s in sessions:
        log(f"## {s['name']}")
        log(f"**Question:** `{s['question'].splitlines()[0]}`\n")
        log("| Answer Archetype | Answer Text | Relevance | Correctness / Accuracy | Coverage | Communication | Overall Score | Result |")
        log("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        for label, ans in s["cases"]:
            req = AnswerEvaluationRequest(
                interviewType=s["type"],
                subject=s.get("subject"),
                question=s["question"],
                answer=ans,
                expectedConcepts=s.get("expectedConcepts", []),
                questionFormat=s.get("format", "theory"),
                expectedOutput=s.get("expectedOutput"),
                testCases=s.get("testCases"),
                language=s.get("language") or ("java" if s["subject"] == "java" else None),
                schema_=s.get("schema"),
                sampleData=s.get("sampleData"),
            )
            res = evaluator.evaluate(req)

            rel = f"{int(round(res.relevance * 100))}%" if res.relevance is not None else "-"
            # For HR: accuracy is present; for theory: correctness
            if s["type"] == "hr":
                cor_acc = f"{int(round((res.correctness or 0) * 100))}% / {int(round((res.accuracy or 0) * 100))}%"
                cov = "-"
            else:
                cor_acc = f"{int(round(res.correctness * 100))}%" if res.correctness is not None else "-"
                cov = f"{int(round(res.conceptCoverage * 100))}%" if res.conceptCoverage is not None else "-"
            comm = f"{int(round(res.communication * 100))}%" if res.communication is not None else "-"
            score = f"**{res.score}%**"
            status = "PASS" if res.score >= 50 else ("PARTIAL" if res.score >= 30 else "FAIL")

            clean_ans = ans.replace("\n", " ")[:65] + ("..." if len(ans) > 65 else "")
            clean_ans = clean_ans.replace("|", "/")
            log(f"| {label} | {clean_ans} | {rel} | {cor_acc} | {cov} | {comm} | {score} | {status} |")
        log("\n---\n")

    with open("verification_runs/e2e_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print("Saved E2E results to verification_runs/e2e_results.md")

if __name__ == "__main__":
    run_e2e()
