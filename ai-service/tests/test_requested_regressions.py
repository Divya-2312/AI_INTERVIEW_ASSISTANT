import hashlib
import json
import unittest
from unittest.mock import Mock, patch

import requests

from app.models.llama_provider import LlamaModel
from app.models.schemas import EvaluationResponse, QuestionGenerationRequest
from app.services.question_generator import QuestionGenerator
from app.services.followup_generator import FollowUpGenerator


class TestRequestedRegressions(unittest.TestCase):
    def test_model_theory_question_id_is_a_stable_text_hash(self):
        req = QuestionGenerationRequest(
            interviewType="technical",
            subject="java",
            difficulty="medium",
            questionFormat="theory",
        )
        question = {
            "questionText": "Explain polymorphism with a simple example.",
            "source": "model",
        }

        first = QuestionGenerator._normalize_model_question(req, question)
        second = QuestionGenerator._normalize_model_question(req, question)
        expected = "theory-" + hashlib.sha256(
            "explain polymorphism with a simple example.".encode("utf-8")
        ).hexdigest()

        self.assertEqual(first["id"], expected)
        self.assertEqual(first["questionId"], expected)
        self.assertEqual(second["id"], first["id"])

    def test_followup_question_has_a_stable_id(self):
        request = Mock()
        request.previousQuestion = "Explain a cache invalidation strategy."
        request.studentAnswer = "Use versioned cache keys."
        request.expectedConcepts = ["cache keys"]
        request.previousQuestions = []
        request.interviewType = "technical"
        request.subject = "java"
        request.previousScore = 70

        generator = FollowUpGenerator()
        generator.provider.generate_followup = Mock(return_value={
            "questionText": "What trade-off does versioning introduce?",
            "subject": "java",
            "difficulty": "medium",
            "category": "Adaptive Follow-Up",
            "expectedConcepts": ["cache invalidation"],
        })

        result = generator.generate(request)

        self.assertTrue(result.id.startswith("followup-"))
        self.assertEqual(result.id, result.questionId)

    def test_java_easy_questions_reject_all_requested_advanced_topics(self):
        req = QuestionGenerationRequest(
            interviewType="technical",
            subject="java",
            difficulty="easy",
            questionFormat="theory",
        )
        forbidden_questions = [
            "Explain Java virtual threads.",
            "Explain garbage collectors in the JVM.",
            "Explain the Java memory model.",
            "Explain bounded generics in Java.",
            "Explain custom annotations in Java.",
            "Explain Java reflection.",
        ]

        for text in forbidden_questions:
            with self.subTest(question=text):
                with self.assertRaises(ValueError):
                    QuestionGenerator._normalize_model_question(
                        req, {"questionText": text, "source": "model"}
                    )

    def test_model_switch_unloads_the_previous_ollama_model(self):
        provider = LlamaModel.__new__(LlamaModel)
        provider.endpoint = "http://localhost:11434/api/generate"
        provider.model_name = "llama3.2:3b"
        provider.ft_model_name = "mockmate-hr100"
        provider.complexity_model_name = "mockmate-hr100"

        ps = Mock(status_code=200)
        ps.json.return_value = {"models": [{"model": "llama3.2:3b"}]}
        unloaded = Mock(status_code=200)
        generated = Mock(status_code=200)
        generated.json.return_value = {"model": "mockmate-hr100:latest", "response": "{}"}

        with patch("app.models.llama_provider.requests.get", return_value=ps), patch(
            "app.models.llama_provider.requests.post", side_effect=[unloaded, generated]
        ) as post:
            response, model = provider._call_llama(
                "{}", model_override="mockmate-hr100", timeout=90
            )

        self.assertEqual(response, "{}")
        self.assertEqual(model, "mockmate-hr100:latest")
        self.assertEqual(post.call_args_list[0].kwargs["json"], {
            "model": "llama3.2:3b",
            "keep_alive": 0,
        })
        self.assertEqual(post.call_args_list[1].kwargs["json"]["keep_alive"], "30m")

    def test_hr_timeout_has_error_source_and_no_score(self):
        provider = LlamaModel.__new__(LlamaModel)
        provider.ft_model_name = "mockmate-hr100"
        provider._eval_cache = {}

        with patch.object(
            provider,
            "_call_llama",
            side_effect=requests.exceptions.Timeout("model request timed out"),
        ):
            result = provider._evaluate_hr_answer(
                "Tell me about yourself.",
                "I studied computer science and completed a web development project.",
                ["education", "project"],
                [],
            )

        self.assertEqual(result["source"], "error")
        self.assertNotIn("score", result)

    def test_complexity_timeout_has_error_source_and_no_score(self):
        provider = LlamaModel.__new__(LlamaModel)
        provider.complexity_model_name = "mockmate-hr100"

        with patch.object(
            provider,
            "_call_llama",
            side_effect=requests.exceptions.Timeout("model request timed out"),
        ):
            result = provider._analyze_code_complexity(
                "Count items", "for (int i = 0; i < n; i++) {}", "java"
            )

        self.assertEqual(result["source"], "error")
        self.assertNotIn("score", result)

    def test_output_prediction_timeout_has_error_source_and_no_score(self):
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}

        with patch.object(
            provider,
            "_call_llama",
            side_effect=requests.exceptions.Timeout("model request timed out"),
        ):
            result = provider._evaluate_output_prediction(
                question="What is the exact output?",
                answer="The output is 9 because the loop ends before 10.",
                concepts=["loop"],
                expected_output="10",
                subject="java",
            )

        self.assertEqual(result["source"], "error")
        self.assertNotIn("score", result)

    def test_evaluation_error_response_omits_score(self):
        from app.routes import evaluation_routes

        request = Mock()
        result = EvaluationResponse(
            feedback="Evaluation engine timed out.",
            source="error",
            error="Evaluation engine timed out.",
        )

        with patch.object(evaluation_routes.answer_evaluator, "evaluate", return_value=result):
            response = evaluation_routes.evaluate_answer(request)

        body = json.loads(response.body)
        self.assertEqual(body["source"], "error")
        self.assertNotIn("score", body)

    def test_model_theory_accuracy_uses_completeness_not_correctness(self):
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        rubric = json.dumps({
            "correctness": 91,
            "relevance": 84,
            "completeness": 62,
            "clarity": 80,
            "feedback": "The response is accurate but omits important details.",
            "strengths": [],
            "weaknesses": [],
        })

        with patch.object(
            provider, "_call_llama", return_value=(rubric, "llama3.2:3b")
        ), patch(
            "app.services.embedding_service.embedding_service.compute_similarity",
            return_value=0.6,
        ), patch(
            "app.models.llama_provider._classify_expected_concepts",
            return_value=(["cache invalidation"], [], []),
        ):
            result = provider.evaluate_answer(
                question="For the Zorblax cache protocol, explain refresh-token synchronization.",
                answer=(
                    "Refresh-token synchronization ensures each cache client sees the latest "
                    "token value before it reuses a stored response."
                ),
                concepts=["cache invalidation", "refresh-token synchronization"],
                context=[],
                subject="java",
            )

        self.assertEqual(result["correctness"], 0.91)
        self.assertEqual(result["accuracy"], 0.62)


if __name__ == "__main__":
    unittest.main()
