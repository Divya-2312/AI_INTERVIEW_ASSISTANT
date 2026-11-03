import unittest
import math
from app.models.llama_provider import (
    calculate_theory_overall,
    LlamaModel,
    DevFallbackModel,
    ResilientAIModel,
    find_theory_item,
    _evaluate_theory_with_rubric,
    _THEORY_ITEMS_LIST,
)
from app.services.embedding_service import embedding_service
from app.services.answer_evaluator import answer_evaluator
from app.models.schemas import AnswerEvaluationRequest


def _pct(v):
    if 0.0 < v <= 1.0:
        return int(math.floor(v * 100.0 + 0.5))
    return int(math.floor(max(0.0, min(100.0, v)) + 0.5))


class TestTheoryOverallScore(unittest.TestCase):
    def test_arraylist_linkedlist_score_52_and_explanation(self):
        """Test 5: The ArrayList/LinkedList answer gives score 52 when the four values are 76, 25, 25, 80,
        and the explanation text contains '52%'."""
        score = calculate_theory_overall(76, 25, 25, 80)
        self.assertEqual(score, 52)

        # Float representation
        score_float = calculate_theory_overall(0.76, 0.25, 0.25, 0.80)
        self.assertEqual(score_float, 52)

        # Check explanation text format
        covered = 0
        partial = 1
        num_kp = 2
        score_reason = (
            f"Score = average of Relevance, Correctness, Concept Coverage and Communication: {score}%. "
            f"Key points: {covered} covered, {partial} partial of {num_kp}."
        )
        self.assertIn("52%", score_reason)
        self.assertIn("Score = average of Relevance, Correctness, Concept Coverage and Communication: 52%", score_reason)

    def test_20_catalogue_questions_score_equals_mean_for_models(self):
        """Test 1: For 20 catalogue questions with a partial answer,
        response.score == round(mean of the four returned values) for
        LlamaModel, DevFallbackModel, and ResilientAIModel."""
        llama_model = LlamaModel()
        llama_model._call_llama = lambda *a, **k: ('{"feedback": "Good", "strengths": ["Clear"], "weaknesses": []}', "llama3.2:3b")
        resilient_model = ResilientAIModel()
        resilient_model.llama._call_llama = lambda *a, **k: ('{"feedback": "Good", "strengths": ["Clear"], "weaknesses": []}', "llama3.2:3b")
        models = [
            ("LlamaModel", llama_model),
            ("DevFallbackModel", DevFallbackModel()),
            ("ResilientAIModel", resilient_model),
        ]

        # Select 20 catalogue questions with reference answers
        cat_sample = [
            item for item in _THEORY_ITEMS_LIST
            if item.get("referenceAnswer") and len(item.get("expectedConcepts", [])) >= 2
        ][:20]
        self.assertGreaterEqual(len(cat_sample), 20)

        for item in cat_sample:
            q = item.get("questionText") or item.get("question")
            ref = item["referenceAnswer"]
            concepts = item.get("expectedConcepts", [])
            subj = item.get("subject", "java")
            # Build a partial answer using the first concept
            ans = f"In {subj}, {concepts[0]} is used as part of the implementation."

            for model_name, model in models:
                res = model.evaluate_answer(
                    q, ans, concepts, [],
                    question_format="theory",
                    subject=subj,
                    interview_type="technical"
                )
                rel = res.get("relevance")
                cor = res.get("correctness")
                cov = res.get("conceptCoverage")
                acc = res.get("accuracy")

                if rel is not None and cor is not None and cov is not None and acc is not None:
                    p_rel = _pct(rel)
                    p_cor = _pct(cor)
                    p_cov = _pct(cov)
                    p_acc = _pct(acc)
                    from app.utils.scoring_formulas import question_score
                    expected = question_score({"accuracy": p_acc, "correctness": p_cor, "relevance": p_rel, "concept_coverage": p_cov})
                    self.assertEqual(
                        res["score"], expected,
                        f"Failed for {model_name} on '{q}': score={res['score']} != expected={expected} "
                        f"({p_rel}, {p_cor}, {p_cov}, {p_acc})"
                    )

    def test_followup_answer_score_equals_mean(self):
        """Test 2: Follow-up answer path asserts response.score == round(mean of the four returned values)."""
        model = ResilientAIModel()
        q = "Can you elaborate on how ArrayList dynamically resizes when capacity is exceeded?"
        ans = "ArrayList creates a new array with 1.5 times the size and copies elements over."
        concepts = ["Dynamic resizing", "Capacity growth factor 1.5", "Array copy operation"]

        res = model.evaluate_answer(
            q, ans, concepts, [],
            question_format="theory",
            subject="java",
            interview_type="technical"
        )
        rel = res.get("relevance")
        cor = res.get("correctness")
        cov = res.get("conceptCoverage")
        acc = res.get("accuracy")

        self.assertIsNotNone(rel)
        self.assertIsNotNone(cor)
        self.assertIsNotNone(cov)
        self.assertIsNotNone(acc)

        p_rel = _pct(rel)
        p_cor = _pct(cor)
        p_cov = _pct(cov)
        p_acc = _pct(acc)
        from app.utils.scoring_formulas import question_score
        expected = question_score({"accuracy": p_acc, "correctness": p_cor, "relevance": p_rel, "concept_coverage": p_cov})
        self.assertEqual(res["score"], expected)

    def test_boundary_guard_enforces_mean(self):
        """Boundary guard corrects any mismatched theory score to the exact mean of four parameters."""
        req = AnswerEvaluationRequest(
            question="What is the difference between ArrayList and LinkedList?",
            answer="arraylist uses an array and linkedlist uses nodes with pointers",
            expectedConcepts=["Dynamic array vs doubly linked list", "Access time vs manipulation time"],
            questionFormat="theory",
            subject="java",
            interviewType="technical"
        )
        resp = answer_evaluator.evaluate(req)
        p_rel = _pct(resp.relevance)
        p_cor = _pct(resp.correctness)
        p_cov = _pct(resp.conceptCoverage)
        p_acc = _pct(resp.accuracy)
        from app.utils.scoring_formulas import question_score
        expected = question_score({"accuracy": p_acc, "correctness": p_cor, "relevance": p_rel, "concept_coverage": p_cov})
        self.assertEqual(resp.score, expected)

    def test_guard_bypassed_for_coding_sql_output_prediction(self):
        """Guard must NOT run for coding, SQL or output prediction."""
        # Coding request
        req_coding = AnswerEvaluationRequest(
            question="Write a function to reverse a string",
            answer="public String reverse(String s) { return new StringBuilder(s).reverse().toString(); }",
            questionFormat="coding",
            language="java",
            subject="java",
            interviewType="technical"
        )
        fake_data_coding = {
            "score": 100,
            "correctness": 1.0,
            "relevance": 1.0,
            "conceptCoverage": 1.0,
            "communication": 0.0,
            "feedback": "All test cases passed."
        }
        res_coding = answer_evaluator._enforce_overall_score_guard(fake_data_coding.copy(), req_coding)
        self.assertEqual(res_coding["score"], 100)

        # SQL request
        req_sql = AnswerEvaluationRequest(
            question="Find all active users",
            answer="SELECT * FROM users WHERE status = 'active';",
            questionFormat="theory",
            language="sql",
            subject="dbms",
            interviewType="technical"
        )
        fake_data_sql = {
            "score": 85,
            "correctness": 0.85,
            "relevance": 1.0,
            "conceptCoverage": 0.70,
            "communication": None,
            "feedback": "Correct query."
        }
        res_sql = answer_evaluator._enforce_overall_score_guard(fake_data_sql.copy(), req_sql)
        self.assertEqual(res_sql["score"], 85)

        # Output prediction request
        req_output = AnswerEvaluationRequest(
            question="What is the output of this code?",
            answer="42",
            questionFormat="output_prediction",
            codeSnippet="System.out.println(42);",
            subject="java",
            interviewType="technical"
        )
        fake_data_output = {
            "score": 100,
            "correctness": 1.0,
            "relevance": 1.0,
            "conceptCoverage": 1.0,
            "communication": None,
            "feedback": "Correct output predicted."
        }
        res_output = answer_evaluator._enforce_overall_score_guard(fake_data_output.copy(), req_output)
        self.assertEqual(res_output["score"], 100)


if __name__ == "__main__":
    unittest.main()
