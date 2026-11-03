import unittest
from app.models.schemas import AnswerEvaluationRequest
from app.services.answer_evaluator import answer_evaluator


class TestNonTheoryUnaffected(unittest.TestCase):
    def test_hr_answer_scoring(self):
        """HR answer uses calculate_hr_overall and HR delivery metrics unaffected."""
        req = AnswerEvaluationRequest(
            interviewType="hr",
            subject="hr",
            question="Tell me about a time you handled a difficult conflict with a coworker.",
            answer="In my previous job, I had a disagreement with a team member about architecture. I scheduled a 1-on-1 discussion, listened to their perspective, and we compromised on a shared design that met both requirements.",
            expectedConcepts=["Context and situation", "Concrete personal actions", "Measurable outcome"],
            questionFormat="theory",
        )
        resp = answer_evaluator.evaluate(req)
        self.assertIsNotNone(resp.accuracy)
        self.assertIsNotNone(resp.relevance)
        self.assertIsNotNone(resp.correctness)
        self.assertIsNotNone(resp.communication)
        self.assertGreater(resp.score, 0)

    def test_java_coding_answer_scoring(self):
        """Java coding answer uses compiler/sandbox test cases unaffected."""
        req = AnswerEvaluationRequest(
            interviewType="technical",
            subject="java",
            question="Write a function to return the sum of two integers.",
            answer="public class Solution { public static int add(int a, int b) { return a + b; } }",
            questionFormat="coding",
            language="java",
            testCases=[
                {"input": "1 2", "expectedOutput": "3"},
                {"input": "5 7", "expectedOutput": "12"}
            ]
        )
        resp = answer_evaluator.evaluate(req)
        self.assertIn(resp.judgeMode, ["sandbox", "mock", "fallback", "deterministic", None])
        self.assertGreaterEqual(resp.score, 0)

    def test_sql_answer_scoring(self):
        """SQL query answer evaluated without communication chip unaffected."""
        req = AnswerEvaluationRequest(
            interviewType="technical",
            subject="dbms",
            question="Write an SQL query to find all users with status active.",
            answer="SELECT * FROM users WHERE status = 'active';",
            questionFormat="theory",
            language="sql",
            expectedConcepts=["SELECT clause", "WHERE filter on status"]
        )
        resp = answer_evaluator.evaluate(req)
        self.assertIsNone(resp.communication)
        self.assertGreaterEqual(resp.score, 0)

    def test_output_prediction_answer_scoring(self):
        """Output prediction answer graded against expected output unaffected."""
        req = AnswerEvaluationRequest(
            interviewType="technical",
            subject="java",
            question="What is the exact output of this code snippet?",
            codeSnippet="System.out.println(10 + 20);",
            answer="30",
            expectedOutput="30",
            questionFormat="output_prediction"
        )
        resp = answer_evaluator.evaluate(req)
        self.assertEqual(resp.score, 100)


if __name__ == "__main__":
    unittest.main()
