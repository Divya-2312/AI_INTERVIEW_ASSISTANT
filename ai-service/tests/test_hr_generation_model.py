"""
HR question generation must be done by the fine-tuned model (mockmate-hr100) from the India HR dataset.
- the model chooses the next question from a short list taken from the dataset;
- the question text always comes from the dataset;
- the base model is never used; a model failure falls back to a dataset question labelled honestly.
Run:  python -m unittest tests/test_hr_generation_model.py
"""
import re
import unittest
from unittest import mock

from app.config import settings
from app.models.llama_provider import LlamaModel
from app.utils.hr_gate import items_list


def _provider():
    # No network: the model call is always mocked in these tests.
    return object.__new__(LlamaModel)


def _first_listed_id(prompt):
    return re.search(r"- id: (\S+) \|", prompt).group(1)


class TestHrGenerationByFineTunedModel(unittest.TestCase):
    def setUp(self):
        self.bank = {q["id"]: q for q in items_list()}
        self.assertGreaterEqual(len(self.bank), 100)

    def test_model_pick_is_used_and_labelled(self):
        p = _provider()
        calls = []

        def fake_call(prompt, **kw):
            calls.append(kw)
            return '{"id": "%s"}' % _first_listed_id(prompt), kw.get("model_override")

        with mock.patch.object(LlamaModel, "_call_llama", side_effect=fake_call):
            q = p._generate_hr_question("medium", [], [], previous_categories=[])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["model_override"], settings.FINE_TUNED_MODEL_NAME)
        self.assertNotEqual(calls[0]["model_override"], settings.MODEL_NAME)
        self.assertEqual(q["source"], "model")
        self.assertEqual(q["modelUsed"], settings.FINE_TUNED_MODEL_NAME)
        self.assertEqual(q["questionText"], self.bank[q["id"]]["question"])

    def test_model_failure_falls_back_with_honest_label(self):
        p = _provider()
        with mock.patch.object(LlamaModel, "_call_llama", side_effect=RuntimeError("ollama down")):
            q = p._generate_hr_question("medium", [], [], previous_categories=[])
        self.assertEqual(q["source"], "bank_fallback")
        self.assertNotEqual(q["modelUsed"], settings.FINE_TUNED_MODEL_NAME)
        self.assertEqual(q["questionText"], self.bank[q["id"]]["question"])

    def test_invented_id_is_not_accepted(self):
        p = _provider()
        with mock.patch.object(LlamaModel, "_call_llama", return_value=('{"id": "hr99999"}', "x")):
            q = p._generate_hr_question("medium", [], [], previous_categories=[])
        self.assertEqual(q["source"], "bank_fallback")
        self.assertIn(q["id"], self.bank)

    def test_garbage_reply_falls_back(self):
        p = _provider()
        with mock.patch.object(LlamaModel, "_call_llama", return_value=("I think you should ask about teamwork.", "x")):
            q = p._generate_hr_question("medium", [], [], previous_categories=[])
        self.assertEqual(q["source"], "bank_fallback")

    def test_previous_questions_are_not_offered_again(self):
        p = _provider()
        prompts = []

        def fake_call(prompt, **kw):
            prompts.append(prompt)
            return '{"id": "%s"}' % _first_listed_id(prompt), "x"

        some = list(self.bank.values())[:30]
        previous = [q["question"] for q in some]
        with mock.patch.object(LlamaModel, "_call_llama", side_effect=fake_call):
            q = p._generate_hr_question("medium", [], previous, previous_categories=[])
        self.assertNotIn(q["questionText"], previous)


if __name__ == "__main__":
    unittest.main()
