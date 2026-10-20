import hashlib
import unittest
from unittest.mock import patch, MagicMock
from app.config import settings
from app.models.llama_provider import LlamaModel, ResilientAIModel, AIGenerationUnavailableError

TEST_GGUF_HASH = "a1b2c3d4e5f60000000000000000000000000000000000000000000000000000"
BASE_BLOB_HASH = "9999999999990000000000000000000000000000000000000000000000000000"


class ModelConfigTests(unittest.TestCase):
    def test_configured_model_is_used_strictly(self):
        self.assertEqual(settings.MODEL_NAME, "llama3.2:3b")
        self.assertEqual(settings.FINE_TUNED_MODEL_NAME, "mockmate-llama-ft")
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
                {"name": "mockmate-llama-ft:latest", "digest": "digest_ft_12345"},
                {"name": "llama3.2:3b", "digest": "digest_base_99999"}
            ]
        }
        mock_get.return_value = tags_response

        def show_side_effect(url, json=None, timeout=None):
            res = MagicMock()
            res.status_code = 200
            name = (json or {}).get("name", "")
            if "mockmate-llama-ft" in name:
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
                {"name": "mockmate-llama-ft:latest", "digest": "digest_ft_12345"},
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
                {"name": "mockmate-llama-ft:latest", "digest": "digest_base_same_99999"},
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
                {"name": "mockmate-llama-ft:latest", "digest": "digest_ft_12345"},
                {"name": "qwen2.5:7b", "digest": "digest_stock_qwen"}
            ]
        }
        mock_get.return_value = tags_response

        def show_side_effect(url, json=None, timeout=None):
            res = MagicMock()
            res.status_code = 200
            name = (json or {}).get("name", "")
            if "mockmate-llama-ft" in name or "qwen2.5" in name:
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


if __name__ == "__main__":
    unittest.main()

