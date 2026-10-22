import time
import statistics
import requests
import sys
import os

# Ensure ai-service root is in sys.path
sys.path.insert(0, os.path.abspath('ai-service'))

from app.utils.hr_gate import is_off_topic
from app.services.code_executor import execute_coding_submission

print("=== Starting 10-run Timing Measurements ===")

# 1. HR off-topic answer (gate only)
q_hr = "Tell me about a time you handled a conflict with a teammate."
a_off = "I had pizza for lunch and watched a cricket match yesterday."

times_gate = []
for _ in range(10):
    t0 = time.perf_counter()
    res = is_off_topic(q_hr, a_off)
    times_gate.append(time.perf_counter() - t0)

# 2. Java sandbox with simple solution
java_code = """
public class Solution {
    public int add(int a, int b) {
        return a + b;
    }
}
"""
java_cases = [{"input": "2, 3", "expectedOutput": "5"}]

times_java = []
for _ in range(10):
    t0 = time.perf_counter()
    res = execute_coding_submission(language="java", code=java_code, test_cases=java_cases)
    times_java.append(time.perf_counter() - t0)

# 3. SQL sandbox
sql_code = "SELECT * FROM users WHERE active = 1;"
sql_schema = "CREATE TABLE users (id INT, name VARCHAR(50), active INT);"
sql_cases = [{"input": "INSERT INTO users VALUES (1, 'Alice', 1), (2, 'Bob', 0);", "expectedOutput": "1|Alice|1"}]

times_sql = []
for _ in range(10):
    t0 = time.perf_counter()
    res = execute_coding_submission(language="sql", code=sql_code, schema=sql_schema, test_cases=sql_cases, reference_solution=sql_code)
    times_sql.append(time.perf_counter() - t0)

# 4. HR evaluation end-to-end via FastAPI
hr_payload = {
    "interviewType": "hr",
    "subject": "hr",
    "question": "Tell me about a time you handled a conflict with a teammate.",
    "answer": "In my final year project, two teammates disagreed on using MongoDB or PostgreSQL. I organized a meeting, listed pros and cons of both based on our query requirements, and we collectively decided on PostgreSQL. This resolved the conflict and we delivered on time.",
    "expectedConcepts": ["Context and situation", "Concrete action taken", "Outcome", "Reflection"],
    "questionFormat": "theory"
}

times_hr_e2e = []
for _ in range(10):
    t0 = time.perf_counter()
    resp = requests.post("http://localhost:8000/api/ai/evaluate-answer", json=hr_payload, timeout=60)
    times_hr_e2e.append(time.perf_counter() - t0)

# 5. Code complexity call via FastAPI
complex_payload = {
    "interviewType": "technical",
    "subject": "java",
    "question": "Write a function to check if array has duplicates.",
    "answer": "public boolean hasDuplicate(int[] nums) { for(int i=0; i<nums.length; i++) { for(int j=i+1; j<nums.length; j++) { if(nums[i] == nums[j]) return true; } } return false; }",
    "questionFormat": "coding",
    "language": "java",
    "testCases": [{"input": "[1, 2, 3, 1]", "expectedOutput": "true"}]
}

times_complexity = []
for _ in range(10):
    t0 = time.perf_counter()
    resp = requests.post("http://localhost:8000/api/ai/evaluate-answer", json=complex_payload, timeout=60)
    times_complexity.append(time.perf_counter() - t0)

def fmt(arr):
    return f"min={min(arr):.4f}s | median={statistics.median(arr):.4f}s | max={max(arr):.4f}s"

print("\n--- RESULTS (10 runs each) ---")
print(f"1. HR off-topic answer (gate only): {fmt(times_gate)}")
print(f"2. Java sandbox (simple solution) : {fmt(times_java)}")
print(f"3. SQL sandbox                    : {fmt(times_sql)}")
print(f"4. HR evaluation end-to-end       : {fmt(times_hr_e2e)}")
print(f"5. Code complexity / Coding eval  : {fmt(times_complexity)}")
