import hashlib
import os
import unittest
from unittest.mock import patch, MagicMock
from app.config import settings
from app.models.llama_provider import LlamaModel, ResilientAIModel, AIGenerationUnavailableError

TEST_GGUF_HASH = "a1b2c3d4e5f60000000000000000000000000000000000000000000000000000"
BASE_BLOB_HASH = "9999999999990000000000000000000000000000000000000000000000000000"
FT_TAG = settings.FINE_TUNED_MODEL_NAME if ":" in settings.FINE_TUNED_MODEL_NAME else f"{settings.FINE_TUNED_MODEL_NAME}:latest"
FT_BASE = settings.FINE_TUNED_MODEL_NAME.split(":")[0]


class ModelConfigTests(unittest.TestCase):
    def test_configured_model_is_used_strictly(self):
        self.assertEqual(settings.MODEL_NAME, os.getenv("MODEL_NAME", "llama3.2:3b").strip())
        self.assertEqual(settings.FINE_TUNED_MODEL_NAME, os.getenv("FINE_TUNED_MODEL_NAME", "mockmate-hr100").strip())
        self.assertTrue(settings.USE_FT_HR)
        self.assertTrue(settings.USE_FT_COMPLEXITY)

    def test_unreachable_model_raises_unavailable_error(self):
        model = ResilientAIModel()
        with patch.object(LlamaModel, "_call_llama", side_effect=Exception("Connection refused")):
            with self.assertRaises(AIGenerationUnavailableError):
                model.generate_question("java", "easy", [], [])

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.open")
    @patch("requests.get")
    @patch("requests.post")
    def test_is_fine_tuned_verified_true_when_distinct_and_modelfile_sha256_matches(self, mock_post, mock_get, mock_open, mock_exists):
        content = b"sample gguf binary content for unit test"
        expected_hash = hashlib.sha256(content).hexdigest().lower()

        mock_file = MagicMock()
        mock_file.read.side_effect = [content, b""]
        mock_open.return_value.__enter__.return_value = mock_file

        tags_response = MagicMock()
        tags_response.status_code = 200
        tags_response.json.return_value = {
            "models": [
                {"name": FT_TAG, "digest": "digest_ft_12345"},
                {"name": "llama3.2:3b", "digest": "digest_base_99999"}
            ]
        }
        mock_get.return_value = tags_response

        def show_side_effect(url, json=None, timeout=None):
            res = MagicMock()
            res.status_code = 200
            name = (json or {}).get("name", "")
            if FT_BASE in name:
                res.json.return_value = {
                    "modelfile": f"FROM C:\\Users\\user\\.ollama\\models\\blobs\\sha256-{expected_hash}\nSYSTEM You are MockMate AI.",
                    "details": {"family": "llama", "parameter_size": "3B", "quantization_level": "Q4_K_M"}
                }
            else:
                res.json.return_value = {
                    "modelfile": f"FROM C:\\Users\\user\\.ollama\\models\\blobs\\sha256-{BASE_BLOB_HASH}\nSYSTEM Base model.",
                    "details": {"family": "llama", "parameter_size": "3B", "digest": "digest_base_99999"}
                }
            return res

        mock_post.side_effect = show_side_effect

        model = LlamaModel()
        status = model.check_connection()

        self.assertTrue(status["is_fine_tuned_verified"])
        self.assertFalse(status["base_model_used_for_inference"])
        self.assertIn("verified", status["verification_reason"].lower())

    @patch("pathlib.Path.exists", return_value=False)
    @patch("requests.get")
    @patch("requests.post")
    def test_is_fine_tuned_verified_false_when_modelfile_wrong_gguf(self, mock_post, mock_get, mock_exists):
        tags_response = MagicMock()
        tags_response.status_code = 200
        tags_response.json.return_value = {
            "models": [
                {"name": FT_TAG, "digest": "digest_ft_12345"},
                {"name": "llama3.2:3b", "digest": "digest_base_99999"}
            ]
        }
        mock_get.return_value = tags_response

        def show_side_effect(url, json=None, timeout=None):
            res = MagicMock()
            res.status_code = 200
            res.json.return_value = {
                "modelfile": f"FROM C:\\Users\\user\\.ollama\\models\\blobs\\sha256-{BASE_BLOB_HASH}\nSYSTEM Base model.",
                "details": {"family": "llama", "parameter_size": "3B", "digest": "digest_base_99999"}
            }
            return res

        mock_post.side_effect = show_side_effect

        model = LlamaModel()
        status = model.check_connection()

        self.assertFalse(status["is_fine_tuned_verified"])
        self.assertIn("Local GGUF file not found", status["verification_reason"])

    @patch("requests.get")
    @patch("requests.post")
    def test_is_fine_tuned_verified_false_when_same_digest_as_base(self, mock_post, mock_get):
        tags_response = MagicMock()
        tags_response.status_code = 200
        tags_response.json.return_value = {
            "models": [
                {"name": FT_TAG, "digest": "digest_base_same_99999"},
                {"name": "llama3.2:3b", "digest": "digest_base_same_99999"}
            ]
        }
        mock_get.return_value = tags_response

        def show_side_effect(url, json=None, timeout=None):
            res = MagicMock()
            res.status_code = 200
            res.json.return_value = {
                "modelfile": f"FROM C:\\Users\\user\\.ollama\\models\\blobs\\sha256-{BASE_BLOB_HASH}",
                "details": {"digest": "digest_base_same_99999"}
            }
            return res

        mock_post.side_effect = show_side_effect

        model = LlamaModel()
        status = model.check_connection()

        self.assertFalse(status["is_fine_tuned_verified"])
        self.assertTrue(status["base_model_used_for_inference"])

    @patch("requests.get")
    @patch("requests.post")
    def test_is_fine_tuned_verified_false_when_matches_any_stock_model(self, mock_post, mock_get):
        stock_blob_hash = "8888888888880000000000000000000000000000000000000000000000000000"
        tags_response = MagicMock()
        tags_response.status_code = 200
        tags_response.json.return_value = {
            "models": [
                {"name": FT_TAG, "digest": "digest_ft_12345"},
                {"name": "qwen2.5:7b", "digest": "digest_stock_qwen"}
            ]
        }
        mock_get.return_value = tags_response

        def show_side_effect(url, json=None, timeout=None):
            res = MagicMock()
            res.status_code = 200
            name = (json or {}).get("name", "")
            if FT_BASE in name or "qwen2.5" in name:
                res.json.return_value = {
                    "modelfile": f"FROM C:\\Users\\user\\.ollama\\models\\blobs\\sha256-{stock_blob_hash}",
                    "details": {"digest": "digest_stock_qwen"}
                }
            return res

        mock_post.side_effect = show_side_effect

        model = LlamaModel()
        status = model.check_connection()

        self.assertFalse(status["is_fine_tuned_verified"])
        self.assertTrue(status["base_model_used_for_inference"])
        self.assertIn("qwen2.5:7b", status["verification_reason"])

    @patch("requests.get", side_effect=Exception("Connection refused"))
    def test_is_fine_tuned_verified_false_when_ollama_unreachable(self, mock_get):
        model = LlamaModel()
        status = model.check_connection()

        self.assertFalse(status["is_fine_tuned_verified"])
        self.assertEqual(status["status"], "unreachable")
        self.assertIn("could not reach ollama", status["verification_reason"].lower())

    def test_non_hr_evaluation_and_generation_strictly_use_base_model(self):
        """
        Architectural Enforcement: Non-HR evaluation and generation calls NEVER use
        FINE_TUNED_MODEL_NAME or COMPLEXITY_MODEL_NAME, but strictly use BASE_MODEL_NAME.
        Only HR evaluation and Big-O code complexity analysis route to the fine-tuned model.
        """
        import json
        model = LlamaModel()
        base_expected = settings.BASE_MODEL_NAME
        ft_expected = settings.FINE_TUNED_MODEL_NAME
        complexity_expected = getattr(settings, "COMPLEXITY_MODEL_NAME", settings.FINE_TUNED_MODEL_NAME)

        # 1. Java Coding Evaluation routes to base model
        with patch.object(model, "_call_llama") as mock_call:
            mock_call.return_value = (json.dumps({
                "logicScore": 90, "approachScore": 90, "edgeCaseScore": 90, "readabilityScore": 90,
                "summary": "Great job", "strengths": [], "weaknesses": []
            }), base_expected)
            model.evaluate_answer(
                question="Implement binary search",
                answer="class Solution { public int search(int[] nums, int target) { return 0; } }",
                concepts=["binary search"],
                context=[],
                question_format="coding",
                test_cases=[{"input": "[1], 1", "expected": "0"}],
                language="java"
            )
            rubric_call = [c for c in mock_call.call_args_list if "logicScore" in c.kwargs.get("prompt", "") or (len(c.args) > 0 and "logicScore" in c.args[0])]
            self.assertTrue(len(rubric_call) > 0, "Coding evaluation must call LLaMA for rubric")
            self.assertEqual(rubric_call[0].kwargs.get("model_override"), base_expected)
            self.assertNotEqual(rubric_call[0].kwargs.get("model_override"), ft_expected)

        # 2. Output Prediction Evaluation routes to base model
        with patch.object(model, "_call_llama") as mock_call:
            mock_call.return_value = (json.dumps({
                "reasoningScore": 50, "misconception": "None", "explanation": "Ok"
            }), base_expected)
            model.evaluate_answer(
                question="What is output?",
                answer="The output is 5 because of loop incrementing.",
                concepts=["loops"],
                context=[],
                question_format="output_prediction",
                expected_output="10",
                code_snippet="int x = 10;"
            )
            self.assertTrue(mock_call.called, "Output prediction evaluation must call LLaMA for misconception diagnosis")
            self.assertEqual(mock_call.call_args.kwargs.get("model_override"), base_expected)
            self.assertNotEqual(mock_call.call_args.kwargs.get("model_override"), ft_expected)

        # 3. Theory Evaluation routes to base model
        with patch.object(model, "_call_llama") as mock_call:
            mock_call.return_value = (json.dumps({
                "correctness": 80, "relevance": 80, "completeness": 80, "clarity": 80,
                "feedback": "Good", "strengths": [], "weaknesses": []
            }), base_expected)
            model.evaluate_answer(
                question="Explain encapsulation.",
                answer="Encapsulation is data hiding through private fields and public methods.",
                concepts=["encapsulation", "data hiding"],
                context=[],
                question_format="theory"
            )
            self.assertTrue(mock_call.called, "Theory evaluation must call LLaMA for 4-criterion rubric")
            self.assertEqual(mock_call.call_args.kwargs.get("model_override"), base_expected)
            self.assertNotEqual(mock_call.call_args.kwargs.get("model_override"), ft_expected)

        # 4. Big-O Complexity Analysis routes to COMPLEXITY_MODEL_NAME / FINE_TUNED_MODEL_NAME
        with patch.object(model, "_call_llama") as mock_call:
            mock_call.return_value = (json.dumps({
                "timeComplexity": "O(N)", "spaceComplexity": "O(1)", "explanation": "Linear scan"
            }), complexity_expected)
            model._analyze_code_complexity("Search", "for (int i=0; i<n; i++) {}")
            self.assertTrue(mock_call.called, "Complexity analysis must invoke model")
            self.assertEqual(mock_call.call_args.kwargs.get("model_override"), complexity_expected)

        # 5. HR Evaluation routes to FINE_TUNED_MODEL_NAME
        with patch.object(model, "_call_llama") as mock_call:
            mock_call.return_value = (json.dumps({
                "score": 85, "correctness": 85, "relevance": 85, "communication": 85,
                "feedback": "Strong response using STAR format."
            }), ft_expected)
            model._evaluate_hr_answer(
                question="Tell me about yourself.",
                answer="I am a software engineer with 2 years experience building distributed web applications.",
                concepts=["background", "experience"],
                context=[]
            )
            self.assertTrue(mock_call.called, "HR evaluation must invoke model")
            self.assertEqual(mock_call.call_args.kwargs.get("model_override"), ft_expected)


if __name__ == "__main__":
    unittest.main()


