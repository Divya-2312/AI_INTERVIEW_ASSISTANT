# ai-service/app/services/code_executor.py:530-560
def execute_sql_submission(candidate_query: str, schema: str, sample_data: str = None, test_cases: List[Dict[str, Any]] = None, reference_solution: str = None) -> Dict[str, Any]:
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    try:
        # 1. Execute DDL Schema
        if schema:
            cursor.executescript(schema)
        # 2. Execute sample DML data if provided
        if sample_data:
            cursor.executescript(sample_data)

        # 3. Execute reference solution to obtain expected rows and column structure
        ref_rows, ref_cols = [], []
        if reference_solution:
            cursor.execute(reference_solution)
            ref_rows = cursor.fetchall()
            ref_cols = [desc[0] for desc in cursor.description] if cursor.description else []

        # 4. Execute candidate SQL query
        cursor.execute(candidate_query)
        cand_rows = cursor.fetchall()
        cand_cols = [desc[0] for desc in cursor.description] if cursor.description else []

        passed = (cand_rows == ref_rows)
        return {
            "score": 100 if passed else 0,
            "passedCount": 1 if passed else 0,
            "totalCount": 1,
            "testCaseResults": [{"id": 1, "passed": passed, "expected": str(ref_rows), "actual": str(cand_rows)}],
            "judgeMode": "deterministic-sqlite",
        }
    except Exception as e:
        return {"score": 0, "compileError": str(e), "judgeMode": "deterministic-sqlite"}
    finally:
        conn.close()
