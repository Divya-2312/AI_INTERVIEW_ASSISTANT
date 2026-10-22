import unittest
from app.utils.hr_gate import is_off_topic, find_hr_item, topic_hits
from app.models.llama_provider import get_ai_model_provider, _estimate_code_complexity_heuristic

class TestHrAndBigOIsolation(unittest.TestCase):
    """
    Regression suite ensuring HR evaluation, HR off-topic gating,
    and Big-O complexity analysis paths remain completely unchanged and isolated.
    """

    def setUp(self):
        self.provider = get_ai_model_provider()
        self.llama = getattr(self.provider, "llama", getattr(self.provider, "primary", self.provider))

    def test_hr_gate_deterministic_topic_hits(self):
        # Curated question lookup
        q = "Tell me about yourself."
        item = find_hr_item(q)
        self.assertIsNotNone(item)
        self.assertEqual(item["id"], "hr001")

        # Relevant answer must hit topics
        ans_rel = "I am a computer science graduate who completed a software engineering degree and an internship."
        self.assertFalse(is_off_topic(q, ans_rel))
        self.assertGreater(topic_hits(q, ans_rel), 0)

        # Off-topic answer must be flagged
        ans_irrel = "I enjoy playing tennis on sunny weekends with my golden retriever."
        self.assertTrue(is_off_topic(q, ans_irrel))
        self.assertEqual(topic_hits(q, ans_irrel), 0)

        # Empty answer is off-topic
        self.assertTrue(is_off_topic(q, ""))
        self.assertTrue(is_off_topic(q, "   "))

    def test_evaluate_hr_answer_off_topic_behavior(self):
        q = "Tell me about yourself."
        ans = "The weather today is very pleasant in Mumbai."
        res = self.llama._evaluate_hr_answer(q, ans, ["background", "projects"], [])
        self.assertEqual(res["score"], 0)
        self.assertTrue(res["isIrrelevant"])
        self.assertEqual(res["relevance"], 0.0)
        self.assertEqual(res["accuracy"], 0.0)
        self.assertEqual(res["communication"], 0.0)
        self.assertIn("not related", res["feedback"].lower())

    def test_evaluate_hr_answer_empty_behavior(self):
        q = "Tell me about yourself."
        res = self.llama._evaluate_hr_answer(q, "", ["background"], [])
        self.assertEqual(res["score"], 0)
        self.assertTrue(res["isIrrelevant"])

    def test_code_complexity_heuristic_isolation(self):
        # Pure heuristic baseline test (independent of external model call)
        linear_code = "for (int i = 0; i < n; i++) { sum += arr[i]; }"
        res1 = _estimate_code_complexity_heuristic(linear_code)
        self.assertIn("o(n)", res1["timeComplexity"].lower())
        self.assertIn("o(1)", res1["spaceComplexity"].lower())

        quadratic_code = "for (int i = 0; i < n; i++) { for (int j = 0; j < n; j++) { c++; } }"
        res2 = _estimate_code_complexity_heuristic(quadratic_code)
        self.assertIn("o(n^2)", res2["timeComplexity"].lower())

        sort_code = "Arrays.sort(arr); return arr[0];"
        res3 = _estimate_code_complexity_heuristic(sort_code)
        self.assertIn("o(n log n)", res3["timeComplexity"].lower())

if __name__ == "__main__":
    unittest.main()
