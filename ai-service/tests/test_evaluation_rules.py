"""
Acceptance tests for the evaluation rules. Run from the ai-service folder:

    python -m unittest discover -s tests -v

No Ollama / internet needed: only the LLaMA call and the embedding model are
replaced by small fakes; all of AI Interview Assistant's own grading logic runs for real.
"""
import json
import re
import sys
import types
import unittest

# ---- fakes injected before the app modules import them -----------------------
_STOP = {"a", "an", "the", "of", "to", "in", "and", "or", "is", "are", "i", "me", "you", "your", "about", "with"}


def _tokens(text):
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if w not in _STOP}


class FakeEmbedding:
    """Word-overlap stand-in for the BERT similarity model (0..1)."""

    def compute_similarity(self, a, b):
        x, y = _tokens(a), _tokens(b)
        if not x or not y:
            return 0.0
        return min(1.0, len(x & y) / min(len(x), len(y)))

    def best_sentence_similarity(self, concept, text):
        return self.compute_similarity(concept, text)


_emb_mod = types.ModuleType("app.services.embedding_service")
_emb_mod.embedding_service = FakeEmbedding()
sys.modules["app.services.embedding_service"] = _emb_mod

_rag_mod = types.ModuleType("app.services.rag_service")
_rag_mod.rag_service = types.SimpleNamespace(retrieve_context=lambda *a, **k: [])
sys.modules["app.services.rag_service"] = _rag_mod

from app.models import llama_provider as lp  # noqa: E402
from app.models.schemas import AnswerEvaluationRequest, EvaluationResponse  # noqa: E402
from app.services.answer_evaluator import AnswerEvaluator  # noqa: E402
from app.utils.hr_scoring import calculate_hr_overall  # noqa: E402


class StubProvider(lp.DevFallbackModel):
    """Real grading logic (LlamaModel code path), with the LLM call stubbed."""


def make_llama(reply):
    """LlamaModel whose LLM call returns `reply` (dict) and counts calls."""
    model = lp.LlamaModel.__new__(lp.LlamaModel)
    model.model_name = lp.settings.MODEL_NAME
    model.calls = 0

    def fake_call(prompt, **kwargs):
        model.calls += 1
        model.last_prompt = prompt
        return json.dumps(reply), lp.settings.MODEL_NAME

    model._call_llama = fake_call
    return model


JAVA_REPLY = {
    "relevance": 0.9, "correctness": 0.8, "conceptCoverage": 0.7, "communication": 0.8,
    "isIrrelevant": False, "demonstratesUnderstanding": True, "feedback": "ok",
    "strengths": [], "weaknesses": [], "coveredConcepts": [], "partiallyCoveredConcepts": [],
    "missingConcepts": [], "deeperConcepts": [], "improvementSuggestion": "", "scoreReason": "ok",
}
HR_REPLY = {
    "relevance": 0.8, "correctness": 0.9, "accuracy": 0.6, "communication": 0.7,
    "isIrrelevant": False, "addressesQuestion": True, "feedback": "Good example.",
    "strengths": ["specific"], "weaknesses": [], "missingConcepts": [], "improvementSuggestion": "",
    "scoreReason": "Decent.",
}
HR_Q = "Tell me about a time you resolved a conflict with a teammate."
JAVA_Q = "Explain inheritance in Java."


class PredictOutputExactMatch(unittest.TestCase):
    def grade(self, answer, expected="10", provider=None):
        provider = provider or make_llama({})
        return provider.evaluate_answer(
            "What does this print?", answer, ["variables"], [],
            question_format="output_prediction", expected_output=expected,
        )

    def test_exact_is_100(self):
        self.assertEqual(self.grade("10")["score"], 100)

    def test_close_but_different_is_0(self):
        self.assertEqual(self.grade("10.0")["score"], 0)
        self.assertEqual(self.grade("The output is 10")["score"], 0)
        self.assertEqual(self.grade("100")["score"], 0)

    def test_case_and_inner_spacing_matter(self):
        self.assertEqual(self.grade("Hello World", "Hello World")["score"], 100)
        self.assertEqual(self.grade("hello world", "Hello World")["score"], 0)
        self.assertEqual(self.grade("Hello  World", "Hello World")["score"], 0)

    def test_only_outer_whitespace_and_line_endings_are_ignored(self):
        self.assertEqual(self.grade("10\n")["score"], 100)
        self.assertEqual(self.grade("1\r\n2", "1\n2")["score"], 100)

    def test_no_llm_or_semantic_scoring_is_used(self):
        provider = make_llama({})
        self.grade("10.0", provider=provider)
        self.assertEqual(provider.calls, 0)

    def test_offline_grader_is_also_exact(self):
        fb = lp.DevFallbackModel()
        for answer, expected_score in (("10", 100), ("10.0", 0), ("The output is 10", 0), ("Hello", 0)):
            res = fb.evaluate_answer("q", answer, [], [], question_format="output_prediction",
                                     expected_output="10" if answer != "Hello" else "hello")
            self.assertEqual(res["score"], expected_score, answer)


class JavaDbmsTheoryMeaningBased(unittest.TestCase):
    CONCEPTS = ["inheritance", "code reuse", "method overriding"]

    def grade(self, answer, question=JAVA_Q, reply=None, model=None):
        model = model or make_llama(reply or JAVA_REPLY)
        return model, model.evaluate_answer(question, answer, self.CONCEPTS, [], interview_type="technical")

    def test_keyword_list_from_the_spec_scores_zero_without_asking_the_llm(self):
        model, res = self.grade("class, interface, abstract, polymorphism")
        self.assertEqual(res["score"], 0)
        self.assertEqual(model.calls, 0)
        self.assertNotIn("accuracy", res)

    def test_other_bare_lists_also_score_zero(self):
        for answer in ("class interface abstract polymorphism", "SELECT, FROM, WHERE, GROUP BY",
                       "inheritance\nencapsulation\nabstraction"):
            _, res = self.grade(answer)
            self.assertEqual(res["score"], 0, answer)

    def test_real_explanations_are_not_flagged(self):
        for answer in ("Inheritance allows a class to reuse code from a parent class.",
                       "Inheritance allows code reuse",
                       "Method overriding"):
            model, res = self.grade(answer)
            self.assertGreater(model.calls, 0, answer)
            self.assertGreater(res["score"], 0, answer)

    def test_terse_but_real_answers_are_never_zeroed_by_the_list_gate(self):
        for answer in ("A primary key uniquely identifies each row in a table.",
                       "Normalization reduces redundancy by splitting tables.",
                       "Interfaces support multiple inheritance",
                       "Garbage collector frees unused objects",
                       "Triggers execute automatically on events",
                       "JOIN combines rows from two tables based on a related column.",
                       "Inheritance: reusing code, Polymorphism: many forms, Abstraction: hiding details"):
            self.assertFalse(lp._is_bare_term_list(answer), answer)

    def test_gaming_attempts_are_caught(self):
        for answer in ("class, interface, abstract, polymorphism", "class; interface; abstract; polymorphism",
                       "joins indexes keys normalization transactions", "SELECT, FROM, WHERE, GROUP BY",
                       "teamwork leadership communication adaptability passion"):
            self.assertTrue(lp._is_bare_term_list(answer), answer)

    def test_list_questions_may_have_list_answers(self):
        model, res = self.grade("Atomicity, Consistency, Isolation, Durability",
                                question="What are the ACID properties?")
        self.assertGreater(model.calls, 0)
        self.assertGreater(res["score"], 0)

    def test_code_in_an_answer_is_not_treated_as_a_term_list(self):
        model, _ = self.grade("class B extends A { void f() { } }")
        self.assertGreater(model.calls, 0)

    def test_model_saying_no_understanding_caps_the_score(self):
        reply = dict(JAVA_REPLY, demonstratesUnderstanding=False, correctness=0.9, conceptCoverage=0.9)
        _, res = self.grade("Inheritance is good and class interface abstract polymorphism are used.", reply=reply)
        self.assertLessEqual(res["correctness"], 0.30)
        self.assertLess(res["score"], 45)

    def test_prompt_tells_the_model_to_judge_meaning_not_keywords(self):
        model, _ = self.grade("Inheritance allows a class to reuse code from a parent class.")
        self.assertIn("TASK: evaluate_answer", model.last_prompt)
        self.assertIn("Evaluate meaning and correctness", lp.TRAINING_SYSTEM_PROMPT)
        self.assertIn("separate from correctness", lp.TRAINING_SYSTEM_PROMPT)
        self.assertIn("Short answers are not auto-irrelevant", lp.TRAINING_SYSTEM_PROMPT)
        self.assertIn("Keyword lists earn little credit", lp.TRAINING_SYSTEM_PROMPT)

    def test_java_uses_weighted_formula_not_the_hr_average(self):
        _, res = self.grade("Inheritance allows a class to reuse code from a parent class.")
        # relevance blend, correctness .8, coverage, communication .8 -> weighted .25/.30/.30/.15
        expected = lp._calculate_text_score(res["relevance"], res["correctness"], res["conceptCoverage"], res["communication"])
        self.assertEqual(res["score"], expected)
        self.assertNotIn("accuracy", res)

    def test_offline_grader_rejects_term_lists_too(self):
        res = lp.DevFallbackModel().evaluate_answer(JAVA_Q, "class, interface, abstract, polymorphism",
                                                    self.CONCEPTS, [], interview_type="technical")
        self.assertEqual(res["score"], 0)


class HRAnswerEvaluation(unittest.TestCase):
    CONCEPTS = ["communication", "teamwork", "conflict resolution"]

    def grade(self, answer, reply=None, question=HR_Q, model=None):
        model = model or make_llama(reply or HR_REPLY)
        return model, model.evaluate_answer(question, answer, self.CONCEPTS, [], interview_type="hr")

    def test_score_is_average_of_four_factors(self):
        _, res = self.grade("I resolved a conflict with a teammate by talking to him and agreeing a plan.")
        self.assertEqual(res["score"], calculate_hr_overall(res["correctness"], res["relevance"],
                                                            res["accuracy"], res["communication"]))
        percents = [round(res[k] * 100) for k in ("correctness", "relevance", "accuracy", "communication")]
        self.assertEqual(res["score"], int(sum(percents) / 4 + 0.5))
        self.assertIn("average", res["scoreReason"])

    def test_unrelated_answer_is_not_related_to_the_question(self):
        reply = dict(HR_REPLY, relevance=0.05, isIrrelevant=True, addressesQuestion=False)
        _, res = self.grade("I like pizza and football on weekends.", reply=reply)
        self.assertEqual(res["feedback"], "Not related to the question.")
        self.assertEqual(res["scoreReason"], "Not related to the question.")
        self.assertEqual(res["score"], 0)
        self.assertTrue(res["isIrrelevant"])

    def test_generic_hr_keywords_are_not_related_and_skip_the_llm(self):
        model, res = self.grade("teamwork, leadership, communication, hard work, passion")
        self.assertEqual(res["scoreReason"], "Not related to the question.")
        self.assertEqual(res["score"], 0)
        self.assertEqual(model.calls, 0)

    def test_generic_buzzword_sentences_cannot_score_high(self):
        reply = dict(HR_REPLY, relevance=0.25, correctness=0.9, accuracy=0.9, communication=0.9,
                     isIrrelevant=False, addressesQuestion=False)
        # embedding overlap with the question is high enough that it is NOT "unrelated",
        # but the model says it does not address the question
        _, res = self.grade("I am a great team player with leadership and conflict resolution and teamwork skills.",
                            reply=reply)
        self.assertLess(res["score"], 50)

    def test_hr_result_exposes_accuracy_and_validates_against_the_schema(self):
        _, res = self.grade("I resolved a conflict with a teammate by talking to him and agreeing a plan.")
        parsed = EvaluationResponse(**res)
        self.assertIsNotNone(parsed.accuracy)

    def test_offline_hr_grader_uses_the_same_average(self):
        fb = lp.DevFallbackModel()
        res = fb.evaluate_answer(HR_Q, "I resolved a conflict with a teammate by talking to him.",
                                 self.CONCEPTS, [], interview_type="hr")
        self.assertEqual(res["score"], calculate_hr_overall(res["correctness"], res["relevance"],
                                                            res["accuracy"], res["communication"]))
        unrelated = fb.evaluate_answer(HR_Q, "I like pizza and football on weekends.", self.CONCEPTS, [],
                                       interview_type="hr")
        self.assertEqual(unrelated["scoreReason"], "Not related to the question.")


class HRDeliveryStaysConsistentWithTheAverage(unittest.TestCase):
    def test_delivery_penalty_lowers_communication_and_overall_stays_the_average(self):
        evaluator = AnswerEvaluator.__new__(AnswerEvaluator)
        evaluator.provider = make_llama(HR_REPLY)
        req = AnswerEvaluationRequest(
            interviewType="hr", question=HR_Q,
            answer="I resolved a conflict with a teammate by talking to him and agreeing a plan.",
            expectedConcepts=["communication"],
            hrDeliveryMetrics={"fillerWordCount": 4, "fillerFrequencyPer100Words": 9.0,
                               "noticeablePauseCount": 3, "repetitionCount": 2,
                               "sentenceCompleteness": "likely_complete"},
        )
        res = evaluator.evaluate(req)
        baseline = make_llama(HR_REPLY).evaluate_answer(req.question, req.answer, req.expectedConcepts, [],
                                                        interview_type="hr")
        self.assertLess(res.communication, baseline["communication"])
        self.assertLess(res.score, baseline["score"])
        self.assertEqual(res.score, calculate_hr_overall(res.correctness, res.relevance, res.accuracy, res.communication))

    def test_technical_requests_never_get_the_hr_adjustment(self):
        evaluator = AnswerEvaluator.__new__(AnswerEvaluator)
        evaluator.provider = make_llama(JAVA_REPLY)
        req = AnswerEvaluationRequest(interviewType="technical", subject="java", question=JAVA_Q,
                                      answer="Inheritance allows a class to reuse code from a parent class.",
                                      expectedConcepts=["inheritance"],
                                      hrDeliveryMetrics={"fillerWordCount": 9, "noticeablePauseCount": 9})
        res = evaluator.evaluate(req)
        self.assertIsNone(res.accuracy)
        self.assertIsNone(res.deliveryMetrics)


class SpeechIsEnglishOnly(unittest.TestCase):
    def _load(self, language, probability):
        fake = types.ModuleType("faster_whisper")
        calls = []

        class Seg:
            start, end, text = 0.0, 1.0, "hello there"

        class Model:
            def __init__(self, *a, **k):
                pass

            def transcribe(self, path, language=None, **kw):
                calls.append(language)
                info = types.SimpleNamespace(language="en" if language == "en" else self_lang[0],
                                             language_probability=self_prob[0], duration=1.0)
                return iter([Seg()]), info

        self_lang, self_prob = [language], [probability]
        fake.WhisperModel = Model
        sys.modules["faster_whisper"] = fake
        sys.modules.pop("app.services.speech_service", None)
        import app.services.speech_service as svc
        return svc, calls

    def test_english_is_transcribed_as_before(self):
        svc, _ = self._load("en", 0.99)
        out = svc.speech_to_text("x.wav")
        self.assertEqual(out["text"], "hello there")
        self.assertNotIn("error", out)

    def test_clear_non_english_is_rejected_with_the_exact_message(self):
        for lang in ("hi", "ta", "es", "fr"):
            svc, _ = self._load(lang, 0.97)
            out = svc.speech_to_text("x.wav")
            self.assertEqual(out["error"], "Couldn't understand the language.")
            self.assertEqual(out["text"], "")
            self.assertEqual(out["segments"], [])

    def test_unsure_detection_is_treated_as_english_not_rejected(self):
        svc, calls = self._load("hi", 0.40)
        out = svc.speech_to_text("x.wav")
        self.assertEqual(out["text"], "hello there")
        self.assertEqual(calls[-1], "en")


if __name__ == "__main__":
    unittest.main()
