import unittest
from unittest.mock import MagicMock, patch
import time
from app.models.llama_provider import (
    get_ai_model_provider,
    MAX_CODING_GENERATION_ATTEMPTS,
    MAX_CODING_GENERATION_TIMEOUT_SEC,
)
from app.models.schemas import QuestionGenerationRequest
from app.services.question_generator import QuestionGenerator, _session_prefetches, _prefetch_lock


class TestFix2BoundedLabels(unittest.TestCase):
    def setUp(self):
        self.provider = get_ai_model_provider()
        self.llama = getattr(self.provider, "llama", None) or self.provider
        self.generator = QuestionGenerator()
        with _prefetch_lock:
            _session_prefetches.clear()

    def test_constants_defined(self):
        """Test that named constants are defined exactly as required."""
        self.assertEqual(MAX_CODING_GENERATION_ATTEMPTS, 2)
        self.assertEqual(MAX_CODING_GENERATION_TIMEOUT_SEC, 25)

    def test_label_correct_for_catalogue_fallback(self):
        """When a question comes from catalogue fallback, source and modelUsed must be catalogue_fallback."""
        fallback_q = self.llama._get_guaranteed_unique_coding_question(
            "java", "medium", previous=[], session_id="test_sess_labels"
        )
        self.assertEqual(fallback_q.get("source"), "catalogue_fallback")
        self.assertEqual(fallback_q.get("modelUsed"), "catalogue_fallback")

        fallback_sql = self.llama._get_guaranteed_unique_coding_question(
            "dbms", "medium", previous=[], session_id="test_sess_labels_sql"
        )
        self.assertEqual(fallback_sql.get("source"), "catalogue_fallback")
        self.assertEqual(fallback_sql.get("modelUsed"), "catalogue_fallback")

    def test_label_correct_for_model(self):
        """Only a question actually written by the base Llama may have source: model."""
        mock_question = {
            "id": "q-mock-llama-1",
            "title": "Model Generated Sum",
            "questionText": "Write a method to calculate sum",
            "starterCode": "class Solution { public static int sum(int a, int b) { return 0; } }",
            "testCases": [{"input": "1, 2", "expectedOutput": "3"}],
            "difficulty": "medium",
            "subject": "java",
            "category": "arithmetic",
            "expectedConcepts": ["arithmetic"],
            "language": "java",
            "questionFormat": "coding",
            "source": "model",
            "modelUsed": "llama3.2:3b",
        }
        with patch.object(self.llama, "_generate_coding_question", return_value=mock_question):
            res = self.provider.generate_question(
                "java", "medium", context=[], previous=[], question_format="coding", session_id="test_mock_model"
            )
            self.assertEqual(res["source"], "model")
            self.assertEqual(res["modelUsed"], "llama3.2:3b")

    def test_time_limit_and_attempts_enforced_with_mocked_slow_model(self):
        """With a slow or failing model, at most 2 attempts and 25s timeout must be enforced, then catalogue used."""
        call_count = [0]

        def slow_fail(*args, **kwargs):
            call_count[0] += 1
            # Simulate slow attempt
            time.sleep(0.01)
            raise ValueError("Model generation error")

        with patch.object(self.llama, "_generate_coding_question", side_effect=slow_fail):
            start = time.time()
            res = self.provider.generate_question(
                "java", "medium", context=[], previous=[], question_format="coding", session_id="test_slow"
            )
            elapsed = time.time() - start

            # Assert attempts were bounded to MAX_CODING_GENERATION_ATTEMPTS (2)
            self.assertEqual(call_count[0], MAX_CODING_GENERATION_ATTEMPTS)
            # Response must be from catalogue fallback
            self.assertEqual(res.get("source"), "catalogue_fallback")
            self.assertEqual(res.get("modelUsed"), "catalogue_fallback")

    def test_repeat_history_exclusion_holds(self):
        """Excluded questions and history are never repeated."""
        catalog_first = self.llama._get_guaranteed_unique_coding_question(
            "java", "medium", previous=[], session_id="sess_excl_1"
        )
        first_title = catalog_first.get("title")
        first_sig = f"{first_title}: {catalog_first.get('questionText')}"

        # Exclude the first question
        second = self.llama._get_guaranteed_unique_coding_question(
            "java", "medium", previous=[first_title],
            exclude_question_ids=[first_title],
            exclude_question_texts=[first_sig, first_title],
            session_id="sess_excl_2"
        )
        self.assertNotEqual(second.get("title"), first_title)

        # Theory repeat history exclusion
        theory_first = self.llama._get_guaranteed_unique_theory_question(
            "java", "medium", previous=[], session_id="sess_excl_t1"
        )
        t_id = theory_first.get("id")
        t_text = theory_first.get("questionText")
        theory_second = self.llama._get_guaranteed_unique_theory_question(
            "java", "medium", previous=[t_text],
            exclude_question_ids=[t_id],
            exclude_question_texts=[t_text],
            session_id="sess_excl_t2"
        )
        self.assertNotEqual(theory_second.get("id"), t_id)

    def test_prefetch_and_serve_prefetched(self):
        """Test background prefetch generation and immediate serving."""
        mock_initial = {
            "id": "q-init-100",
            "title": "Initial Problem",
            "questionText": "Implement an initial question",
            "starterCode": "class Solution {}",
            "testCases": [{"input": "1", "expectedOutput": "1"}],
            "difficulty": "medium",
            "subject": "java",
            "category": "arrays",
            "expectedConcepts": ["arrays"],
            "language": "java",
            "questionFormat": "coding",
            "source": "model",
            "modelUsed": "llama3.2:3b",
        }
        with patch.object(self.llama, "_generate_coding_question", return_value=mock_initial):
            req1 = QuestionGenerationRequest(
                interviewType="technical",
                subject="java",
                difficulty="medium",
                questionFormat="coding",
                previousQuestions=[],
                sessionId="sess_prefetch_test_100",
            )
            res1 = self.generator.generate(req1)
            self.assertIsNotNone(res1)

        # Pre-seed a ready prefetched question in the prefetch cache
        mock_prefetched = {
            "id": "q-prefetched-unique-42",
            "title": "Prefetched Problem",
            "questionText": "Implement an algorithm in Java",
            "starterCode": "class Solution {}",
            "testCases": [{"input": "1", "expectedOutput": "1"}],
            "difficulty": "medium",
            "subject": "java",
            "category": "trees",
            "expectedConcepts": ["trees"],
            "language": "java",
            "questionFormat": "coding",
            "source": "model",
            "modelUsed": "llama3.2:3b",
        }
        with _prefetch_lock:
            _session_prefetches["sess_prefetch_test_100"] = mock_prefetched

        # When student submits answer and requests next question:
        req2 = QuestionGenerationRequest(
            interviewType="technical",
            subject="java",
            difficulty="medium",
            questionFormat="coding",
            previousQuestions=[res1.questionText or res1.question],
            sessionId="sess_prefetch_test_100",
        )
        res2 = self.generator.generate(req2)
        # Must serve the ready prefetched question immediately
        self.assertEqual(res2.id, "q-prefetched-unique-42")
        self.assertEqual(res2.title, "Prefetched Problem")
        self.assertEqual(res2.source, "model")
        self.assertEqual(res2.modelUsed, "llama3.2:3b")


if __name__ == "__main__":
    unittest.main()
