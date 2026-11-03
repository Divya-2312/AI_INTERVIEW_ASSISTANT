import os
import re
import unittest
from app.models.schemas import AnswerEvaluationRequest
from app.services.answer_evaluator import AnswerEvaluator
from app.utils.hr_scoring import calculate_hr_overall, build_hr_evaluation_summary


class TestHREvaluationSuite(unittest.TestCase):
    """
    Comprehensive test suite for HR Evaluation accuracy, consistency,
    sub-score averaging, idempotency caching, and summary clarity.
    """

    @classmethod
    def setUpClass(cls):
        cls.evaluator = AnswerEvaluator()

    def test_off_topic_answer_scores_zero(self):
        """Off-topic answer must strictly score 0 with 0 relevance."""
        req = AnswerEvaluationRequest(
            interviewType="hr",
            subject="hr",
            question="Tell me about yourself.",
            answer="I love eating pepperoni pizza on Friday nights and watching superhero movies.",
            expectedConcepts=["Context and situation", "Actions taken", "Measurable outcome", "Reflection"],
        )
        res = self.evaluator.evaluate(req)
        self.assertEqual(res.score, 0, f"Expected 0 for completely off-topic answer, got {res.score}")
        self.assertEqual(res.relevance, 0.0)

    def test_relevant_answer_scores_at_least_one(self):
        """Any answer addressing the question must score at least 1%."""
        req = AnswerEvaluationRequest(
            interviewType="hr",
            subject="hr",
            question="Tell me about yourself.",
            answer="I am a fresh graduate who studied computer science and completed a web development project.",
            expectedConcepts=["Context and situation", "Actions taken", "Measurable outcome", "Reflection"],
        )
        res = self.evaluator.evaluate(req)
        self.assertGreaterEqual(res.score, 1, f"Relevant answer must score >= 1, got {res.score}")
        self.assertGreater(res.relevance, 0.0)

    def test_displayed_overall_equals_mean_of_four_subscores_typed(self):
        """The overall score must equal the rounded mean of the 4 displayed subscores for typed answers."""
        req = AnswerEvaluationRequest(
            interviewType="hr",
            subject="hr",
            question="What are your greatest strengths?",
            answer="My strengths are structured problem solving and persistence. In my project I fixed a blocking bug in 6 hours.",
            expectedConcepts=["Context and situation", "Actions taken", "Measurable outcome", "Reflection"],
        )
        res = self.evaluator.evaluate(req)
        expected_overall = calculate_hr_overall(
            res.correctness or 0.0,
            res.relevance or 0.0,
            res.accuracy or 0.0,
            res.conceptCoverage or 0.0,
        )
        self.assertEqual(
            res.score,
            expected_overall,
            f"Overall score {res.score} does not match expected mean of sub-scores {expected_overall}"
        )

    def test_displayed_overall_equals_mean_of_four_subscores_spoken(self):
        """For spoken answers, delivery penalty applies to communication before computing the mean."""
        req = AnswerEvaluationRequest(
            interviewType="hr",
            subject="hr",
            question="Tell me about a time you handled conflict.",
            answer="Um, like, well, I had a disagreement with a teammate, you know, and um, we talked it out, like, calmly.",
            expectedConcepts=["Context and situation", "Actions taken", "Measurable outcome", "Reflection"],
            hrDeliveryMetrics={
                "fillerWords": ["um", "like", "you know", "well"],
                "fillerWordCount": 5,
                "pauseCount": 3,
                "pacing": "slow",
                "fluencyScore": 0.5,
            },
        )
        res = self.evaluator.evaluate(req)
        expected_overall = calculate_hr_overall(
            res.correctness or 0.0,
            res.relevance or 0.0,
            res.accuracy or 0.0,
            res.conceptCoverage or 0.0,
        )
        self.assertEqual(
            res.score,
            expected_overall,
            f"Spoken answer overall score {res.score} does not match rounded mean {expected_overall}"
        )

    def test_identical_answer_idempotent_cached_score(self):
        """Submitting the exact same question and answer must hit cache and return identical score."""
        req = AnswerEvaluationRequest(
            interviewType="hr",
            subject="hr",
            question="Why do you want to work at our company?",
            answer="I respect your engineering culture and commitment to open source developer tools.",
            expectedConcepts=["Context and situation", "Actions taken", "Measurable outcome", "Reflection"],
        )
        res1 = self.evaluator.evaluate(req)
        res2 = self.evaluator.evaluate(req)

        self.assertEqual(res1.score, res2.score)
        self.assertEqual(res1.correctness, res2.correctness)
        self.assertEqual(res1.relevance, res2.relevance)
        self.assertEqual(res1.accuracy, res2.accuracy)
        self.assertEqual(res1.communication, res2.communication)
        self.assertEqual(res1.whyNot100, res2.whyNot100)

    def test_summary_never_contains_raw_decimals_or_weighted_score(self):
        """HR evaluation summary must never contain raw decimals (e.g., 0.50) or 'weighted score'."""
        req = AnswerEvaluationRequest(
            interviewType="hr",
            subject="hr",
            question="Where do you see yourself in five years?",
            answer="In five years I hope to lead a team of junior engineers.",
            expectedConcepts=["Context and situation", "Actions taken", "Measurable outcome", "Reflection"],
        )
        res = self.evaluator.evaluate(req)

        text_to_check = []
        if res.whyNot100:
            text_to_check.append(res.whyNot100)
        if res.scoreReason:
            text_to_check.append(res.scoreReason)

        decimal_pattern = re.compile(r'\b\d+\.\d+\b')
        for text in text_to_check:
            self.assertNotIn("weighted score", text.lower())
            raw_decimals = decimal_pattern.findall(text)
            self.assertEqual(
                raw_decimals,
                [],
                f"Found raw decimals in evaluation text: {raw_decimals} in '{text}'"
            )

    def test_score_at_or_above_95_has_no_why_not_100(self):
        """For scores >= 95%, whyNot100 must be None and the summary must be positive."""
        summary, why_not_100 = build_hr_evaluation_summary(
            score=98,
            correctness=0.98,
            relevance=1.0,
            accuracy=0.97,
            communication=0.97,
            answer="Comprehensive STAR method answer with clear metrics and outcomes.",
            weaknesses=[],
            improvement_suggestion="",
            delivery_metrics=None,
        )
        self.assertIsNone(why_not_100)
        self.assertIn("response", summary.lower())
        self.assertIn("98%", summary)
        self.assertNotIn("weighted score", summary.lower())
        self.assertFalse(re.search(r'\b\d+\.\d+\b', summary))


if __name__ == "__main__":
    unittest.main()
