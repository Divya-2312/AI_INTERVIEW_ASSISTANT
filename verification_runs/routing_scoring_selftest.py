"""
Self-Test Script: Routing and Scoring Verification
Evaluates fixed cases across all modules:
- 5 Java theory (good, good, half-correct, different-topic, empty)
- 5 DBMS theory (good, good, half-correct, different-topic, empty)
- 5 HR (good, good, half-correct, different-topic, empty)
- Output prediction (3 correct, 3 wrong)
- Java coding (2 correct, 2 wrong, 1 partial: checks 0 of N => 0, 2 of 3 => 67)
- SQL (2 correct, 2 wrong, 1 partial: checks 0 of N => 0, 2 of 3 => 67)
- 5 contradiction guard examples for theory/HR

Prints per-case table with parameters, question score, modelUsed, expected band, within-band check.
Computes confusion matrix (TP, FP, TN, FN) at pass mark 50, precision, recall, F1, accuracy per module and overall (labelled 'self-test').
"""

import sys
import json
import requests

BASE_URL = "http://localhost:8000/api/ai"
PASS_MARK = 50

# Define test cases
TEST_CASES = [
    # ------------------ 1. JAVA THEORY ------------------
    {
        "module": "java_theory",
        "name": "Java Theory: Good (OOP principles)",
        "expected_band": (75, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "Explain the four fundamental principles of Object-Oriented Programming in Java.",
            "answer": "The four OOP principles in Java are Encapsulation (hiding internal state with private fields and public getters/setters), Abstraction (hiding implementation details using interfaces and abstract classes), Inheritance (reusing code across parent and child classes using extends), and Polymorphism (method overloading at compile time and method overriding at runtime).",
            "expectedConcepts": ["Encapsulation", "Abstraction", "Inheritance", "Polymorphism"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "java_theory",
        "name": "Java Theory: Good (HashMap vs ConcurrentHashMap)",
        "expected_band": (75, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is the difference between HashMap and ConcurrentHashMap in Java?",
            "answer": "HashMap is not thread-safe and allows null keys/values. ConcurrentHashMap is thread-safe using lock striping (Java 7 segments, Java 8 CAS and synchronized bucket nodes) without locking the whole map, and does not allow null keys or values.",
            "expectedConcepts": ["Thread safety difference", "Locking mechanism: lock striping / synchronized node vs unsynchronized", "Handling of null keys and values"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "java_theory",
        "name": "Java Theory: Half-Correct (Garbage Collection)",
        "expected_band": (40, 65),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "How does Garbage Collection work in Java and what are Young and Old generations?",
            "answer": "Garbage collection in Java removes unused objects from memory automatically. There is a young generation where new objects go, but I am not entirely sure about the rest of the generations or collectors.",
            "expectedConcepts": ["Automatic memory management via mark-and-sweep", "Young generation: Eden and Survivor spaces for short-lived objects", "Old generation for long-lived objects", "Minor GC vs Major GC"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "java_theory",
        "name": "Java Theory: Different-Topic (Irrelevant answer)",
        "expected_band": (0, 35),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "Explain the difference between checked and unchecked exceptions in Java.",
            "answer": "Photosynthesis is the process by which green plants use sunlight, water, and carbon dioxide to create oxygen and energy in the form of sugar.",
            "expectedConcepts": ["Checked exceptions inherit Exception and are checked at compile time", "Unchecked exceptions inherit RuntimeException", "Mandatory try-catch or throws clause"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "java_theory",
        "name": "Java Theory: Empty Answer",
        "expected_band": (0, 0),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is the Java Memory Model and happens-before relationship?",
            "answer": "",
            "expectedConcepts": ["Java Memory Model specification", "Happens-before visibility guarantees", "Volatile keyword and synchronization"],
            "questionFormat": "theory"
        }
    },

    # ------------------ 2. DBMS THEORY ------------------
    {
        "module": "dbms_theory",
        "name": "DBMS Theory: Good (ACID properties)",
        "expected_band": (75, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "Explain ACID properties in Database Management Systems.",
            "answer": "ACID stands for Atomicity (all operations succeed or entire transaction is rolled back), Consistency (database transitions from one valid state to another satisfying all constraints), Isolation (concurrent transactions execute without interfering with each other), and Durability (once committed, updates persist even across system failure).",
            "expectedConcepts": ["Atomicity: all-or-nothing", "Consistency: constraints preserved", "Isolation: concurrent transaction separation", "Durability: persistent committed changes"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "dbms_theory",
        "name": "DBMS Theory: Good (Indexing & B-Trees)",
        "expected_band": (75, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "How does B+ Tree indexing improve database query performance?",
            "answer": "B+ Tree indexes keep data sorted with all data stored in leaf nodes, linked sequentially for efficient range scans. Internal nodes store only keys and pointers, enabling high fan-out, shallow height, and minimal disk I/O operations.",
            "expectedConcepts": ["Balanced tree structure", "Keys stored in internal nodes with data in linked leaf nodes", "Fast range queries via leaf node pointers", "Logarithmic search time O(log N)"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "dbms_theory",
        "name": "DBMS Theory: Half-Correct (Normalization)",
        "expected_band": (40, 65),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "What is Database Normalization and explain 1NF, 2NF, and 3NF?",
            "answer": "Normalization organizes database tables to reduce data redundancy. 1NF means each cell has only single atomic values. I know 2NF and 3NF remove partial and transitive dependencies, but I do not remember the exact definitions.",
            "expectedConcepts": ["Eliminate data redundancy and anomalies", "1NF: Atomic values and unique rows", "2NF: 1NF plus no partial dependencies on composite keys", "3NF: 2NF plus no transitive dependencies"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "dbms_theory",
        "name": "DBMS Theory: Different-Topic (Irrelevant answer)",
        "expected_band": (0, 35),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "What is the difference between clustered and non-clustered indexes?",
            "answer": "To make French toast, whisk eggs, milk, cinnamon, and vanilla extract in a shallow bowl. Dip bread slices and fry in a buttered skillet until golden brown on both sides.",
            "expectedConcepts": ["Clustered index defines physical order of data rows", "Only one clustered index per table", "Non-clustered index stores index entries pointing to data rows", "Multiple non-clustered indexes allowed"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "dbms_theory",
        "name": "DBMS Theory: Empty Answer",
        "expected_band": (0, 0),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "Explain optimistic versus pessimistic concurrency control.",
            "answer": "",
            "expectedConcepts": ["Optimistic concurrency control assumes few conflicts and checks on commit", "Pessimistic locking locks data rows before modification", "Trade-offs in high write vs high read systems"],
            "questionFormat": "theory"
        }
    },

    # ------------------ 3. HR EVALUATION ------------------
    {
        "module": "hr",
        "name": "HR: Excellent STAR (hr001 Tell me about yourself)",
        "expected_band": (75, 100),
        "payload": {
            "interviewType": "hr",
            "subject": "hr",
            "question": "Tell me about yourself.",
            "answer": "I graduated with a Computer Science degree from ABC University where I maintained an 8.5 GPA. During my final year, I led a 4-person team to build an e-commerce platform using React, Node.js, and MongoDB, handling over 1,000 mock transactions with 99% uptime. I completed an internship at XYZ Tech where I automated API testing, reducing regression cycle times by 30%. I am looking forward to applying my full-stack and problem-solving skills in this software engineering role.",
            "expectedConcepts": [
                "Context and situation for introduction",
                "Concrete personal actions taken",
                "Quantifiable or tangible outcome",
                "Professional self-reflection and ownership"
            ],
            "questionFormat": "theory"
        }
    },
    {
        "module": "hr",
        "name": "HR: Good (hr001 Tell me about yourself)",
        "expected_band": (60, 85),
        "payload": {
            "interviewType": "hr",
            "subject": "hr",
            "question": "Tell me about yourself.",
            "answer": "I am a software engineer with background in web development. In college, I worked on web applications and learned React and Node.js. In my internship, I helped build customer features and worked with senior engineers to deliver our sprint goals on time.",
            "expectedConcepts": [
                "Context and situation for introduction",
                "Concrete personal actions taken",
                "Quantifiable or tangible outcome",
                "Professional self-reflection and ownership"
            ],
            "questionFormat": "theory"
        }
    },
    {
        "module": "hr",
        "name": "HR: Average (hr001 Tell me about yourself)",
        "expected_band": (40, 65),
        "payload": {
            "interviewType": "hr",
            "subject": "hr",
            "question": "Tell me about yourself.",
            "answer": "I am a student from an engineering college. I have learned programming and web basics. I did my project and now I am looking for a job to start my career.",
            "expectedConcepts": [
                "Context and situation for introduction",
                "Concrete personal actions taken",
                "Quantifiable or tangible outcome",
                "Professional self-reflection and ownership"
            ],
            "questionFormat": "theory"
        }
    },
    {
        "module": "hr",
        "name": "HR: Different-Topic (Irrelevant answer)",
        "expected_band": (0, 35),
        "payload": {
            "interviewType": "hr",
            "subject": "hr",
            "question": "Tell me about yourself.",
            "answer": "Mount Everest is Earth's highest mountain above sea level, located in the Mahalangur Himal sub-range of the Himalayas. The current official elevation is 8,848.86 meters.",
            "expectedConcepts": [
                "Context and situation for introduction",
                "Concrete personal actions taken",
                "Quantifiable or tangible outcome",
                "Professional self-reflection and ownership"
            ],
            "questionFormat": "theory"
        }
    },
    {
        "module": "hr",
        "name": "HR: Empty Answer",
        "expected_band": (0, 0),
        "payload": {
            "interviewType": "hr",
            "subject": "hr",
            "question": "Tell me about yourself.",
            "answer": "",
            "expectedConcepts": [
                "Context and situation for introduction",
                "Concrete personal actions taken",
                "Quantifiable or tangible outcome",
                "Professional self-reflection and ownership"
            ],
            "questionFormat": "theory"
        }
    },

    # ------------------ 4. OUTPUT PREDICTION ------------------
    {
        "module": "output_prediction",
        "name": "Output Prediction: Correct (Exact match)",
        "expected_band": (100, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is the exact output of the following code?",
            "answer": "15",
            "expectedConcepts": ["Loop iteration and summation"],
            "questionFormat": "output_prediction",
            "codeSnippet": "public class Sum { public static void main(String[] args) { int s = 0; for(int i=1; i<=5; i++) s+=i; System.out.println(s); } }",
            "expectedOutput": "15"
        }
    },
    {
        "module": "output_prediction",
        "name": "Output Prediction: Correct (With reasoning)",
        "expected_band": (100, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is the exact output of the following code?",
            "answer": "Output is 20 because x is multiplied by 2",
            "expectedConcepts": ["Variable multiplication"],
            "questionFormat": "output_prediction",
            "codeSnippet": "public class Test { public static void main(String[] args) { int x = 10; System.out.println(x * 2); } }",
            "expectedOutput": "20"
        }
    },
    {
        "module": "output_prediction",
        "name": "Output Prediction: Correct (Multi-line exact match)",
        "expected_band": (100, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is the exact output of the following code?",
            "answer": "Hello\nWorld",
            "expectedConcepts": ["Print statements"],
            "questionFormat": "output_prediction",
            "codeSnippet": "public class Test { public static void main(String[] args) { System.out.println(\"Hello\"); System.out.println(\"World\"); } }",
            "expectedOutput": "Hello\nWorld"
        }
    },
    {
        "module": "output_prediction",
        "name": "Output Prediction: Wrong without explanation",
        "expected_band": (0, 0),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is the exact output of the following code?",
            "answer": "999",
            "expectedConcepts": ["Loop summation"],
            "questionFormat": "output_prediction",
            "codeSnippet": "public class Sum { public static void main(String[] args) { int s = 0; for(int i=1; i<=5; i++) s+=i; System.out.println(s); } }",
            "expectedOutput": "15"
        }
    },
    {
        "module": "output_prediction",
        "name": "Output Prediction: Wrong (Off-by-one with flawed logic)",
        "expected_band": (0, 35),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is the exact output of the following code?",
            "answer": "10 because the loop stops early",
            "expectedConcepts": ["Loop summation"],
            "questionFormat": "output_prediction",
            "codeSnippet": "public class Sum { public static void main(String[] args) { int s = 0; for(int i=1; i<=5; i++) s+=i; System.out.println(s); } }",
            "expectedOutput": "15"
        }
    },
    {
        "module": "output_prediction",
        "name": "Output Prediction: Empty Answer",
        "expected_band": (0, 0),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is the exact output of the following code?",
            "answer": "",
            "expectedConcepts": ["Loop summation"],
            "questionFormat": "output_prediction",
            "codeSnippet": "public class Sum { public static void main(String[] args) { int s = 0; for(int i=1; i<=5; i++) s+=i; System.out.println(s); } }",
            "expectedOutput": "15"
        }
    },

    # ------------------ 5. JAVA CODING ------------------
    {
        "module": "java_coding",
        "name": "Java Coding: All Test Cases Pass (3 of 3)",
        "expected_band": (100, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "Write a method to calculate the sum of two integers.",
            "answer": "public class Solution { public static int add(int a, int b) { return a + b; } }",
            "questionFormat": "coding",
            "language": "java",
            "testCases": [
                {"input": "1, 2", "expectedOutput": "3"},
                {"input": "10, 20", "expectedOutput": "30"},
                {"input": "-5, 5", "expectedOutput": "0"}
            ]
        }
    },
    {
        "module": "java_coding",
        "name": "Java Coding: All Test Cases Pass (2 of 2)",
        "expected_band": (100, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "Write a method to check if a number is positive.",
            "answer": "public class Solution { public static boolean isPositive(int n) { return n > 0; } }",
            "questionFormat": "coding",
            "language": "java",
            "testCases": [
                {"input": "5", "expectedOutput": "true"},
                {"input": "-3", "expectedOutput": "false"}
            ]
        }
    },
    {
        "module": "java_coding",
        "name": "Java Coding: 0 of N Pass (Wrong Output)",
        "expected_band": (0, 0),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "Write a method to calculate the sum of two integers.",
            "answer": "public class Solution { public static int add(int a, int b) { return 99999; } }",
            "questionFormat": "coding",
            "language": "java",
            "testCases": [
                {"input": "1, 2", "expectedOutput": "3"},
                {"input": "10, 20", "expectedOutput": "30"}
            ]
        }
    },
    {
        "module": "java_coding",
        "name": "Java Coding: Compilation Error (Syntax Error)",
        "expected_band": (0, 0),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "Write a method to calculate the sum of two integers.",
            "answer": "public class Solution { this is completely broken syntax }",
            "questionFormat": "coding",
            "language": "java",
            "testCases": [
                {"input": "1, 2", "expectedOutput": "3"},
                {"input": "10, 20", "expectedOutput": "30"}
            ]
        }
    },
    {
        "module": "java_coding",
        "name": "Java Coding: Partial (2 of 3 Pass => Exactly 67%)",
        "expected_band": (67, 67),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "Write a method to return absolute value of integer.",
            "answer": "public class Solution { public static int abs(int n) { return n >= 0 ? n : (n == -10 ? 10 : 0); } }",
            "questionFormat": "coding",
            "language": "java",
            "testCases": [
                {"input": "5", "expectedOutput": "5"},
                {"input": "-10", "expectedOutput": "10"},
                {"input": "-7", "expectedOutput": "7"}
            ]
        }
    },

    # ------------------ 6. SQL CODING ------------------
    {
        "module": "sql",
        "name": "SQL: All Test Cases Pass (2 of 2)",
        "expected_band": (100, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "Write an SQL query to select all active users.",
            "answer": "SELECT id, name FROM users WHERE status = 'active';",
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE users (id INT, name VARCHAR(50), status VARCHAR(20));",
            "sampleData": "INSERT INTO users VALUES (1, 'Alice', 'active'), (2, 'Bob', 'inactive');",
            "testCases": [
                {"input": "active", "expectedOutput": "1|Alice"}
            ]
        }
    },
    {
        "module": "sql",
        "name": "SQL: All Test Cases Pass (Count Query)",
        "expected_band": (100, 100),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "Count total active employees.",
            "answer": "SELECT COUNT(*) FROM employees WHERE active = 1;",
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE employees (id INT, active INT);",
            "sampleData": "INSERT INTO employees VALUES (1, 1), (2, 0), (3, 1);",
            "testCases": [
                {"input": "count", "expectedOutput": "2"}
            ]
        }
    },
    {
        "module": "sql",
        "name": "SQL: 0 of N Pass (Wrong Query)",
        "expected_band": (0, 0),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "Select all active users.",
            "answer": "SELECT * FROM users WHERE 1 = 0;",
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE users (id INT, name VARCHAR(50), status VARCHAR(20));",
            "sampleData": "INSERT INTO users VALUES (1, 'Alice', 'active');",
            "testCases": [
                {"input": "active", "expectedOutput": "1|Alice"}
            ]
        }
    },
    {
        "module": "sql",
        "name": "SQL: Syntax Error",
        "expected_band": (0, 0),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "Select all active users.",
            "answer": "SELEECT WRONG SYNTAX FROM WHERE;",
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE users (id INT, name VARCHAR(50));",
            "sampleData": "INSERT INTO users VALUES (1, 'Alice');",
            "testCases": [
                {"input": "1", "expectedOutput": "1"}
            ]
        }
    },
    {
        "module": "sql",
        "name": "SQL: Partial (2 of 3 Pass => Exactly 67%)",
        "expected_band": (67, 67),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "Filter users by status.",
            "answer": "SELECT id FROM users WHERE status = 'active';",
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE users (id INT, status VARCHAR(20));",
            "sampleData": "INSERT INTO users VALUES (1, 'active'), (2, 'active'), (3, 'pending');",
            "testCases": [
                {"input": "t1", "expectedOutput": "1\n2"},
                {"input": "t2", "expectedOutput": "1\n2"},
                {"input": "t3", "expectedOutput": "3"}
            ]
        }
    },

    # ------------------ 7. CONTRADICTION GUARD (5 EXAMPLES) ------------------
    {
        "module": "contradiction_guard",
        "name": "Contradiction 1: Java pass-by-reference myth",
        "expected_band": (0, 35),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "Is Java pass-by-value or pass-by-reference?",
            "answer": "Java is completely pass by reference for all objects and never passes anything by value.",
            "expectedConcepts": ["Java is strictly pass-by-value", "Object references are passed by value", "Primitives passed by value"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "contradiction_guard",
        "name": "Contradiction 2: String mutable in-place myth",
        "expected_band": (0, 35),
        "payload": {
            "interviewType": "technical",
            "subject": "java",
            "question": "Are Strings mutable or immutable in Java?",
            "answer": "Strings in Java are completely mutable and you can modify their internal characters in place without creating new objects.",
            "expectedConcepts": ["Strings are immutable", "String pool sharing", "Security and thread safety"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "contradiction_guard",
        "name": "Contradiction 3: Primary key allows null and duplicates",
        "expected_band": (0, 35),
        "payload": {
            "interviewType": "technical",
            "subject": "dbms",
            "question": "Can a primary key in a database contain NULL values or duplicates?",
            "answer": "Yes, primary keys can contain multiple duplicate values and can have NULL values freely.",
            "expectedConcepts": ["Primary key uniquely identifies each record", "Must be UNIQUE and NOT NULL", "Only one primary key per table"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "contradiction_guard",
        "name": "Contradiction 4: HR anti-teamwork response",
        "expected_band": (0, 35),
        "payload": {
            "interviewType": "hr",
            "subject": "hr",
            "question": "How do you handle working with difficult teammates?",
            "answer": "I refuse to speak to anyone on my team. I ignore all feedback and do whatever I feel like doing regardless of team goals.",
            "expectedConcepts": ["Constructive communication", "Empathy and listening", "Professionalism", "Alignment with team"],
            "questionFormat": "theory"
        }
    },
    {
        "module": "contradiction_guard",
        "name": "Contradiction 5: HR deadline abandonment response",
        "expected_band": (0, 35),
        "payload": {
            "interviewType": "hr",
            "subject": "hr",
            "question": "What do you do when a project deadline is approaching and work is incomplete?",
            "answer": "Whenever a deadline approaches I turn off my phone, leave the office, and abandon the project completely so someone else handles it.",
            "expectedConcepts": ["Accountability and ownership", "Early escalation to manager", "Reprioritization of deliverables", "Delivering core scope"],
            "questionFormat": "theory"
        }
    }
]

def run_selftest():
    print("=" * 105)
    print("MOCKMATE AI: ROUTING & COMMON FORMULA SCORING SELF-TEST (PASS MARK = 50)")
    print("=" * 105)

    results = []
    module_metrics = {}

    header = f"{'Module':<20} | {'Case Name':<35} | {'Acc':<4} {'Cor':<4} {'Rel':<4} {'Cov':<4} | {'Score':<5} | {'Model Used':<22} | {'Exp Band':<10} | {'OK?'}"
    print(header)
    print("-" * 105)

    for case in TEST_CASES:
        mod = case["module"]
        name = case["name"]
        exp_min, exp_max = case["expected_band"]

        try:
            r = requests.post(f"{BASE_URL}/evaluate-answer", json=case["payload"], timeout=60)
            res = r.json()
            score = res.get("score", 0)
            model_used = res.get("modelUsed", "unknown")
            formula = res.get("formula") or {}
            params = formula.get("parameters") or {}

            acc = params.get("accuracy", res.get("accuracy", 0))
            cor = params.get("correctness", res.get("correctness", 0))
            rel = params.get("relevance", res.get("relevance", 0))
            cov = params.get("concept_coverage", res.get("conceptCoverage", 0))

            # Normalize floats to ints if needed
            acc_i = int(round(acc * 100)) if isinstance(acc, float) and acc <= 1.0 else int(round(acc))
            cor_i = int(round(cor * 100)) if isinstance(cor, float) and cor <= 1.0 else int(round(cor))
            rel_i = int(round(rel * 100)) if isinstance(rel, float) and rel <= 1.0 else int(round(rel))
            cov_i = int(round(cov * 100)) if isinstance(cov, float) and cov <= 1.0 else int(round(cov))

            within_band = (exp_min <= score <= exp_max)
            ok_str = "YES" if within_band else "NO"

            # Check if expected pass/fail at 50
            expected_pass = (exp_min >= PASS_MARK)
            actual_pass = (score >= PASS_MARK)

            results.append({
                "module": mod,
                "name": name,
                "score": score,
                "acc": acc_i,
                "cor": cor_i,
                "rel": rel_i,
                "cov": cov_i,
                "modelUsed": model_used,
                "expected_band": f"[{exp_min}-{exp_max}]",
                "within_band": within_band,
                "expected_pass": expected_pass,
                "actual_pass": actual_pass,
                "formula": formula
            })

            row = f"{mod:<20} | {name[:35]:<35} | {acc_i:<4} {cor_i:<4} {rel_i:<4} {cov_i:<4} | {score:<5} | {str(model_used)[:22]:<22} | {f'[{exp_min}-{exp_max}]':<10} | {ok_str}"
            print(row)

        except Exception as e:
            print(f"{mod:<20} | {name[:35]:<35} | ERROR: {e}")

    # Compute Confusion Matrix and Metrics
    print("\n" + "=" * 105)
    print("CONFUSION MATRIX & METRICS (LABELLED 'self-test') AT PASS MARK 50:")
    print("=" * 105)

    modules = sorted(list(set(r["module"] for r in results)))
    modules.append("OVERALL")

    metrics_table_header = f"{'Module (self-test)':<24} | {'Total':<6} | {'TP':<4} {'FP':<4} {'TN':<4} {'FN':<4} | {'Precision':<10} | {'Recall':<10} | {'F1':<10} | {'Accuracy':<10}"
    print(metrics_table_header)
    print("-" * 105)

    for mod in modules:
        subset = results if mod == "OVERALL" else [r for r in results if r["module"] == mod]
        total = len(subset)
        if total == 0:
            continue

        tp = sum(1 for r in subset if r["expected_pass"] and r["actual_pass"])
        fp = sum(1 for r in subset if not r["expected_pass"] and r["actual_pass"])
        tn = sum(1 for r in subset if not r["expected_pass"] and not r["actual_pass"])
        fn = sum(1 for r in subset if r["expected_pass"] and not r["actual_pass"])

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        accuracy = ((tp + tn) / total) if total > 0 else 0.0

        print(f"{mod:<24} | {total:<6} | {tp:<4} {fp:<4} {tn:<4} {fn:<4} | {precision*100:>8.1f}%  | {recall*100:>8.1f}%  | {f1*100:>8.1f}%  | {accuracy*100:>8.1f}%")

    with open("verification_runs/routing_scoring_selftest_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_selftest()
