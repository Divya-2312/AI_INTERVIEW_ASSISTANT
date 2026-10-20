import unittest
from app.services.code_executor import execute_coding_submission, is_java_available
from app.models.schemas import AnswerEvaluationRequest
from app.services.answer_evaluator import answer_evaluator


class TestCodeExecutor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not is_java_available():
            raise unittest.SkipTest("Java runtime (JDK) not available on this system.")

    def test_java_runtime_is_detected(self):
        self.assertTrue(is_java_available())

    def test_java_correct_solution_scores_100(self):
        code = (
            "public class Solution {\n"
            "    public static int add(int a, int b) {\n"
            "        return a + b;\n"
            "    }\n"
            "}"
        )
        test_cases = [
            {"id": 1, "input": "2, 3", "expectedOutput": "5", "label": "Case 1"},
            {"id": 2, "input": "-1, 1", "expectedOutput": "0", "label": "Case 2"},
            {"id": 3, "input": "10, -5", "expectedOutput": "5", "label": "Case 3"},
        ]
        res = execute_coding_submission("java", code, test_cases)
        self.assertEqual(res["totalCount"], 3)
        self.assertEqual(res["passedCount"], 3)
        self.assertIsNone(res.get("compileError"))
        for tc in res["results"]:
            self.assertEqual(tc["status"], "PASSED")

        # Test through answer_evaluator
        req = AnswerEvaluationRequest(
            interviewType="technical",
            question="Write a method to add two integers",
            answer=code,
            questionFormat="coding",
            language="java",
            testCases=test_cases,
        )
        eval_res = answer_evaluator.evaluate(req)
        self.assertEqual(eval_res.score, 100)
        self.assertEqual(eval_res.passedCount, 3)
        self.assertEqual(eval_res.totalCount, 3)
        self.assertEqual(eval_res.judgeMode, "deterministic")
        self.assertIsNone(eval_res.whyNot100)
        self.assertIsNone(eval_res.correctedCode)
        self.assertIsNone(eval_res.conceptCoverage)
        self.assertIsNone(eval_res.correctness)
        self.assertIsNone(eval_res.relevance)
        self.assertIsNone(eval_res.communication)
        self.assertIsNotNone(eval_res.timeComplexity)
        self.assertTrue("O(" in eval_res.timeComplexity or "o(" in eval_res.timeComplexity)

    def test_java_wrong_solution_partial_score(self):
        code = (
            "public class Solution {\n"
            "    public static int add(int a, int b) {\n"
            "        if (a < 0) return 0;\n"
            "        return a + b;\n"
            "    }\n"
            "}"
        )
        test_cases = [
            {"id": 1, "input": "2, 3", "expectedOutput": "5", "label": "Case 1"},
            {"id": 2, "input": "-1, 5", "expectedOutput": "4", "label": "Case 2"},
            {"id": 3, "input": "10, 2", "expectedOutput": "12", "label": "Case 3"},
        ]
        res = execute_coding_submission("java", code, test_cases)
        self.assertEqual(res["totalCount"], 3)
        self.assertEqual(res["passedCount"], 2)

        req = AnswerEvaluationRequest(
            interviewType="technical",
            question="Write a method to add two integers",
            answer=code,
            questionFormat="coding",
            language="java",
            testCases=test_cases,
        )
        eval_res = answer_evaluator.evaluate(req)
        self.assertEqual(eval_res.score, 67)
        self.assertEqual(eval_res.passedCount, 2)
        self.assertEqual(eval_res.totalCount, 3)
        self.assertIsNotNone(eval_res.whyNot100)

    def test_java_compile_error_scores_zero(self):
        code = "public class Solution { public static int bad(int a) { return a + ; } }"
        test_cases = [
            {"id": 1, "input": "2", "expectedOutput": "2", "label": "Case 1"},
            {"id": 2, "input": "5", "expectedOutput": "5", "label": "Case 2"},
        ]
        res = execute_coding_submission("java", code, test_cases)
        self.assertIsNotNone(res.get("compileError"))
        self.assertEqual(res["passedCount"], 0)
        for tc in res["results"]:
            self.assertEqual(tc["status"], "COMPILE_ERROR")

        req = AnswerEvaluationRequest(
            interviewType="technical",
            question="Write a method that returns input",
            answer=code,
            questionFormat="coding",
            language="java",
            testCases=test_cases,
        )
        eval_res = answer_evaluator.evaluate(req)
        self.assertEqual(eval_res.score, 0)
        self.assertIsNotNone(eval_res.compileError)

    def test_java_infinite_loop_timeout(self):
        code = (
            "public class Solution {\n"
            "    public static int loop(int n) {\n"
            "        while(true) {}\n"
            "    }\n"
            "}"
        )
        test_cases = [
            {"id": 1, "input": "5", "expectedOutput": "5", "label": "Case 1"}
        ]
        res = execute_coding_submission("java", code, test_cases)
        self.assertEqual(res["passedCount"], 0)
        self.assertEqual(res["results"][0]["status"], "TIMEOUT")
        self.assertIn("timed out", res["results"][0]["error"].lower())

    def test_eval_idempotent_5_times(self):
        code = (
            "public class Solution {\n"
            "    public static int square(int n) {\n"
            "        return n * n;\n"
            "    }\n"
            "}"
        )
        test_cases = [
            {"id": 1, "input": "3", "expectedOutput": "9", "label": "Case 1"},
            {"id": 2, "input": "4", "expectedOutput": "16", "label": "Case 2"},
        ]
        scores = []
        for _ in range(5):
            res = execute_coding_submission("java", code, test_cases)
            scores.append(res["passedCount"])
        self.assertEqual(len(set(scores)), 1)
        self.assertEqual(scores[0], 2)

    def test_sql_correct_and_incorrect(self):
        schema = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(50), age INT);"
        sample = "INSERT INTO users VALUES (1, 'Alice', 25), (2, 'Bob', 17), (3, 'Charlie', 30);"
        test_cases = [
            {"id": 1, "input": "Users table with ages 25, 17, 30", "expectedOutput": "Alice, Charlie", "label": "Adults query"}
        ]
        correct_query = "SELECT name FROM users WHERE age >= 18 ORDER BY id;"
        wrong_query = "SELECT name FROM users WHERE age < 18 ORDER BY id;"

        res_ok = execute_coding_submission(
            "sql",
            correct_query,
            test_cases,
            schema=schema,
            reference_solution=correct_query,
            sample_data=sample,
        )
        self.assertEqual(res_ok["passedCount"], 1)
        self.assertEqual(res_ok["results"][0]["status"], "PASSED")

        res_bad = execute_coding_submission(
            "sql",
            wrong_query,
            test_cases,
            schema=schema,
            reference_solution=correct_query,
            sample_data=sample,
        )
        self.assertEqual(res_bad["passedCount"], 0)
        self.assertEqual(res_bad["results"][0]["status"], "FAILED")

    def test_100_percent_result_has_no_why_not_100(self):
        schema = "CREATE TABLE items (id INT, price INT);"
        sample = "INSERT INTO items VALUES (1, 10), (2, 20);"
        test_cases = [{"id": 1, "input": "", "expectedOutput": "10, 20", "label": "All items"}]
        query = "SELECT price FROM items ORDER BY id;"

        req = AnswerEvaluationRequest(
            interviewType="technical",
            question="Select all item prices",
            answer=query,
            questionFormat="coding",
            language="sql",
            testCases=test_cases,
            schema=schema,
            sampleData=sample,
            referenceSolution=query,
        )
        eval_res = answer_evaluator.evaluate(req)
        self.assertEqual(eval_res.score, 100)
        self.assertIsNone(eval_res.whyNot100)
        self.assertIsNone(eval_res.correctedCode)


if __name__ == "__main__":
    unittest.main()
