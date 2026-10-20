from app.services.code_executor import execute_coding_submission, is_java_available

def run_tests():
    print("Java available:", is_java_available())
    
    # 1. Java correct solution -> 100%
    sol_correct = """public class Solution {
    public static int[] twoSum(int[] nums, int target) {
        for (int i = 0; i < nums.length; i++) {
            for (int j = i + 1; j < nums.length; j++) {
                if (nums[i] + nums[j] == target) return new int[]{i, j};
            }
        }
        return new int[]{};
    }
}"""
    cases = [
        {"input": "[2, 7, 11, 15], 9", "expectedOutput": "[0, 1]"},
        {"input": "[3, 2, 4], 6", "expectedOutput": "[1, 2]"},
        {"input": "[3, 3], 6", "expectedOutput": "[0, 1]"}
    ]
    res1 = execute_coding_submission("java", sol_correct, cases)
    print("Java correct pass rate:", res1["passedCount"], "/", res1["totalCount"])
    assert res1["passedCount"] == 3

    # 2. Java wrong solution -> partial score
    sol_wrong = """public class Solution {
    public static int[] twoSum(int[] nums, int target) {
        if (target == 9) return new int[]{0, 1};
        return new int[]{0, 0}; // fails case 2 and 3
    }
}"""
    res2 = execute_coding_submission("java", sol_wrong, cases)
    print("Java wrong pass rate:", res2["passedCount"], "/", res2["totalCount"])
    assert res2["passedCount"] == 1

    # 3. Java compile error -> 0
    sol_bad = "public class Solution { public static void bad() { int x = ; } }"
    res3 = execute_coding_submission("java", sol_bad, cases)
    print("Java compile error pass rate:", res3["passedCount"], "/", res3["totalCount"], "Error:", bool(res3["compileError"]))
    assert res3["passedCount"] == 0
    assert res3["compileError"] is not None

    # 4. Java infinite loop -> timeout
    sol_inf = "public class Solution { public static int[] twoSum(int[] nums, int target) { while(true){} } }"
    from app.services.code_executor import execute_java
    res4 = execute_java(sol_inf, [{"input": "[1], 1", "expectedOutput": "[0]"}], timeout_sec=2.0)
    print("Java infinite loop status:", res4["results"][0]["status"])
    assert res4["results"][0]["status"] == "TIMEOUT"

    # 5. SQL correct and incorrect
    schema = "CREATE TABLE employees (id INT PRIMARY KEY, name VARCHAR(50), salary INT);"
    sample = "INSERT INTO employees VALUES (1, 'Alice', 80000), (2, 'Bob', 50000);"
    query_ok = "SELECT name FROM employees WHERE salary > 60000;"
    ref = "SELECT name FROM employees WHERE salary > 60000;"
    res_sql_ok = execute_coding_submission("sql", query_ok, [{"input": "", "expectedOutput": "Alice"}], schema=schema, reference_solution=ref, sample_data=sample)
    print("SQL correct pass rate:", res_sql_ok["passedCount"], "/", res_sql_ok["totalCount"])
    assert res_sql_ok["passedCount"] == 1

    query_wrong = "SELECT name FROM employees WHERE salary < 60000;"
    res_sql_bad = execute_coding_submission("sql", query_wrong, [{"input": "", "expectedOutput": "Alice"}], schema=schema, reference_solution=ref, sample_data=sample)
    print("SQL incorrect pass rate:", res_sql_bad["passedCount"], "/", res_sql_bad["totalCount"])
    assert res_sql_bad["passedCount"] == 0

    print("ALL TEST EXECUTOR CHECKS PASSED!")

if __name__ == "__main__":
    run_tests()
