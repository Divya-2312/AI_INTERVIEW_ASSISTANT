"""
Acceptance tests for the evaluation rules. Run from the ai-service folder:

    python -m unittest discover -s tests -v

No Ollama / internet needed: only the LLaMA call and the embedding model are
replaced by small fakes; all of AI Interview Assistant's own grading logic runs for real.
"""
import json
import os
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

    def is_similar_to_any(self, text, target_texts, threshold=0.88):
        for t in (target_texts or []):
            sim = self.compute_similarity(text, t)
            if sim >= threshold:
                return True, sim, t
        return False, 0.0, None


_emb_mod = types.ModuleType("app.services.embedding_service")
_emb_mod.embedding_service = FakeEmbedding()
_emb_mod.SYNONYM_MAP = {}
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
        res = self.grade("10")
        self.assertEqual(res["score"], 100)
        self.assertIsNone(res["communication"])

    def test_close_but_different_is_0(self):
        res = self.grade("10.0")
        self.assertEqual(res["score"], 0)
        self.assertIsNone(res["communication"])
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
                       "Inheritance supports method overriding"):
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
        acid_concepts = ["Atomicity", "Consistency", "Isolation", "Durability"]
        model = make_llama(JAVA_REPLY)
        res = model.evaluate_answer("What are the ACID properties?",
                                    "Atomicity, Consistency, Isolation, Durability",
                                    acid_concepts, [], interview_type="technical")
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
        self.assertIn("Evaluate the candidate's answer across 4 criteria", model.last_prompt)
        self.assertIn("correctness (0-100)", model.last_prompt)
        self.assertIn("relevance (0-100)", model.last_prompt)
        self.assertIn("completeness (0-100)", model.last_prompt)
        self.assertIn("clarity (0-100)", model.last_prompt)

    def test_java_uses_rounded_mean_of_four_parameters(self):
        _, res = self.grade("Inheritance allows a class to reuse code from a parent class.")
        # Java/DBMS theory score is the exact rounded mean of the four theory parameter percentages:
        # relevance, correctness, conceptCoverage, communication
        expected = lp.calculate_theory_overall(res["relevance"], res["correctness"],
                                               res["conceptCoverage"], res["communication"])
        self.assertEqual(res["score"], expected)
        percents = [round(res[k] * 100) for k in ("relevance", "correctness", "conceptCoverage", "communication")]
        self.assertEqual(res["score"], int(sum(percents) / 4 + 0.5))
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


class NoNewContentGateAndPredefinedRubricTests(unittest.TestCase):
    def test_theory_question_words_repeats_score_zero(self):
        # "im sopna i know a thread and process difference" -> 0
        # "i know the difference" -> 0
        model = make_llama(JAVA_REPLY)
        q = "What is the difference between a process and a thread?"
        concepts = ["process", "thread", "memory space", "execution"]
        for ans in ("im sopna i know a thread and process difference", "i know the difference"):
            res = model.evaluate_answer(q, ans, concepts, [], interview_type="technical")
            self.assertEqual(res["score"], 0, ans)
            self.assertEqual(res["conceptCoverage"], 0.0)
            self.assertFalse(res["isIrrelevant"])
            self.assertEqual(res["feedback"], "The answer only repeats words from the question and does not explain anything.")
            self.assertIn("Answer repeats the question without explaining", res["weaknesses"])

    def test_theory_real_explanation_scores_greater_than_zero(self):
        # "A process has its own memory space, while threads of the same process share..." -> > 0
        model = make_llama(JAVA_REPLY)
        q = "What is the difference between a process and a thread?"
        ans = "A process has its own memory space, while threads of the same process share memory and heap space."
        concepts = ["process", "thread", "memory space", "threads of the same process"]
        res = model.evaluate_answer(q, ans, concepts, [], interview_type="technical")
        self.assertGreater(res["score"], 0)

    def test_hr_no_new_content_scores_zero(self):
        # "I know tell me about yourself" -> 0
        model = make_llama(HR_REPLY)
        q = "Tell me about yourself."
        concepts = ["background", "experience", "skills", "projects"]
        res = model.evaluate_answer(q, "I know tell me about yourself", concepts, [], interview_type="hr")
        self.assertEqual(res["score"], 0)
        self.assertEqual(res["relevance"], 0.0)
        self.assertEqual(res["accuracy"], 0.0)
        self.assertEqual(res["communication"], 0.0)
        self.assertFalse(res["isIrrelevant"])
        self.assertEqual(res["feedback"], "The answer only repeats words from the question and does not explain anything.")

    def test_hr_short_real_answer_scores_partial(self):
        # "Yes, I am open to relocating" -> partial score > 0
        model = make_llama(HR_REPLY)
        q = "Are you willing to relocate for this role?"
        concepts = ["relocation", "flexibility", "timeline"]
        res = model.evaluate_answer(q, "Yes, I am open to relocating", concepts, [], interview_type="hr")
        self.assertGreater(res["score"], 0)

    def test_theory_followup_no_new_content_scores_zero(self):
        model = make_llama(JAVA_REPLY)
        q = "Can you explain why immutability is important for String in Java?"
        ans = "I know why immutability is important for string in java"
        res = model.evaluate_answer(q, ans, ["thread safety", "string pool"], [], interview_type="technical")
        self.assertEqual(res["score"], 0)

    def test_hr_followup_no_new_content_scores_zero(self):
        model = make_llama(HR_REPLY)
        q = "How did you measure the outcome of that conflict resolution?"
        ans = "I know how we measured the outcome of the conflict resolution"
        res = model.evaluate_answer(q, ans, ["metrics", "team harmony"], [], interview_type="hr")
        self.assertEqual(res["score"], 0)

    def test_deterministic_offline_fallback_no_new_content(self):
        fb = lp.DevFallbackModel()
        q_tech = "What is the difference between a process and a thread?"
        res_tech = fb.evaluate_answer(q_tech, "im sopna i know a thread and process difference",
                                      ["process", "thread"], [], interview_type="technical")
        self.assertEqual(res_tech["score"], 0)

        q_hr = "Tell me about yourself."
        res_hr = fb.evaluate_answer(q_hr, "I know tell me about yourself",
                                    ["background", "experience"], [], interview_type="hr")
        self.assertEqual(res_hr["score"], 0)

    def test_resilient_ai_model_no_new_content(self):
        resilient = lp.ResilientAIModel()
        q_tech = "What is the difference between a process and a thread?"
        res_tech = resilient.evaluate_answer(q_tech, "im sopna i know a thread and process difference",
                                             ["process", "thread"], [], interview_type="technical")
        self.assertEqual(res_tech["score"], 0)

        q_hr = "Tell me about yourself."
        res_hr = resilient.evaluate_answer(q_hr, "I know tell me about yourself",
                                           ["background", "experience"], [], interview_type="hr")
        self.assertEqual(res_hr["score"], 0)

    def test_output_prediction_non_answer_scores_zero(self):
        fb = lp.DevFallbackModel()
        res = fb.evaluate_answer("What does this code print?", "I don't know the output",
                                 ["loops"], [], question_format="output_prediction", expected_output="10")
        self.assertEqual(res["score"], 0)

    def test_coding_plain_english_non_code_scores_zero(self):
        # Plain-English non-code answer fails to compile and scores 0
        model = make_llama({})
        tc = [{"input": "5", "expectedOutput": "10", "label": "Test 1"}]
        res = model.evaluate_answer("Write a Java method to double an integer.",
                                   "I don't know how to write this in Java code",
                                   ["methods"], [], question_format="coding", language="java", test_cases=tc)
        self.assertEqual(res["score"], 0)

    def test_sql_plain_english_non_code_scores_zero(self):
        # Plain-English non-code answer fails SQL execution and scores 0
        model = make_llama({})
        tc = [{"input": "test", "expectedOutput": "rows", "label": "Test 1"}]
        schema = "CREATE TABLE employees (id INT, name TEXT);"
        res = model.evaluate_answer("Find all employees",
                                   "I think we need to select everyone from the employee table",
                                   ["SELECT"], [], question_format="coding", language="sql",
                                   test_cases=tc, schema=schema)
        self.assertEqual(res["score"], 0)

    def test_catalogue_rubric_java_theory_032(self):
        # Question (java-theory-032): "What is the difference between checked and unchecked exceptions?"
        # Answer: "checked exception is a tick mark ✓ and unchecked is a cross X, you draw them in notebook" -> score <= 10
        model = make_llama(JAVA_REPLY)
        q = "What is the difference between checked and unchecked exceptions?"
        ans_bogus = "checked exception is a tick mark ✓ and unchecked is a cross X, you draw them in notebook"
        res = model.evaluate_answer(q, ans_bogus, ["checked exceptions", "unchecked exceptions"], [],
                                   interview_type="technical", subject="java")
        self.assertLessEqual(res["score"], 10)
        self.assertEqual(res["conceptCoverage"], 0.0)
        self.assertEqual(res["correctness"], 0.0)
        self.assertIn("0 covered, 0 partial", res["scoreReason"])

        # 1st key point partial answer -> score between 30 and 70
        cat_item = lp.find_theory_item(q, subject="java")
        self.assertIsNotNone(cat_item)
        ref_ans = cat_item["referenceAnswer"]
        kps = lp._split_reference_key_points(ref_ans)
        ans_partial = kps[0]
        res_part = model.evaluate_answer(q, ans_partial, cat_item["expectedConcepts"], [],
                                         interview_type="technical", subject="java")
        self.assertTrue(30 <= res_part["score"] <= 70)
        self.assertEqual(res_part["score"], lp.calculate_theory_overall(res_part["relevance"], res_part["correctness"], res_part["conceptCoverage"], res_part["communication"]))

        # Positive test: referenceAnswer against itself -> score >= 90
        ref_ans = cat_item["referenceAnswer"]
        res_pos = model.evaluate_answer(q, ref_ans, cat_item["expectedConcepts"], [],
                                        interview_type="technical", subject="java")
        self.assertGreaterEqual(res_pos["score"], 90)
        self.assertEqual(res_pos["score"], lp.calculate_theory_overall(res_pos["relevance"], res_pos["correctness"], res_pos["conceptCoverage"], res_pos["communication"]))


class TheoryScoreDeterministicAndMeanOfFourTests(unittest.TestCase):
    def test_im_sopna_all_four_parameters_zero_and_score_zero(self):
        model = make_llama(JAVA_REPLY)
        q = "What is the difference between a process and a thread?"
        ans = "im sopna i know a thread and process difference"
        res = model.evaluate_answer(q, ans, ["process", "thread"], [], interview_type="technical")
        self.assertEqual(res["score"], 0)
        self.assertEqual(res["relevance"], 0.0)
        self.assertEqual(res["correctness"], 0.0)
        self.assertEqual(res["conceptCoverage"], 0.0)
        self.assertEqual(res["communication"], 0.0)

    def test_theory_score_equals_mean_of_four_parameters(self):
        # Verify for both catalogue and non-catalogue theory questions
        cat_item = lp.find_theory_item("What is the difference between checked and unchecked exceptions?", subject="java")
        self.assertIsNotNone(cat_item)
        model = make_llama(JAVA_REPLY)
        res = model.evaluate_answer(
            cat_item["questionText"],
            cat_item["referenceAnswer"],
            cat_item["expectedConcepts"],
            [],
            interview_type="technical",
            subject="java"
        )
        self.assertGreaterEqual(res["score"], 90)
        expected = lp.calculate_theory_overall(
            res["relevance"], res["correctness"], res["conceptCoverage"], res["communication"]
        )
        self.assertEqual(res["score"], expected)
        percents = [round(res[k] * 100) for k in ("relevance", "correctness", "conceptCoverage", "communication")]
        self.assertEqual(res["score"], int(sum(percents) / 4 + 0.5))

    def test_hr_score_equals_mean_of_four_parameters(self):
        model = make_llama(HR_REPLY)
        res = model.evaluate_answer(
            "Tell me about a time you worked in a team.",
            "I worked in a team of 4 engineers to deliver an e-commerce platform on time.",
            ["teamwork", "communication"],
            [],
            interview_type="hr"
        )
        expected = calculate_hr_overall(res["correctness"], res["relevance"], res["accuracy"], res["communication"])
        self.assertEqual(res["score"], expected)
        percents = [round(res[k] * 100) for k in ("correctness", "relevance", "accuracy", "communication")]
        self.assertEqual(res["score"], int(sum(percents) / 4 + 0.5))

    def test_coding_sql_output_prediction_non_regression(self):
        # 1. Output prediction
        fb = lp.DevFallbackModel()
        res_op = fb.evaluate_answer("What does this print?", "42", ["variables"], [],
                                   question_format="output_prediction", expected_output="42")
        self.assertEqual(res_op["score"], 100)
        self.assertIsNone(res_op["communication"])

        # 2. Java coding
        model = make_llama({})
        tc = [{"input": "5", "expectedOutput": "10", "label": "Test 1"}]
        res_code = model.evaluate_answer(
            "Write a Java method to double an integer.",
            "public class Solution { public static int solve(int n) { return n * 2; } }",
            ["methods"], [], question_format="coding", language="java", test_cases=tc
        )
        self.assertIn("score", res_code)
        self.assertIsNone(res_code.get("communication"))

        # 3. SQL query
        schema = "CREATE TABLE employees (id INT, name TEXT);"
        tc_sql = [{"input": "", "expectedOutput": "Alice", "label": "Test 1"}]
        sample_data = "INSERT INTO employees VALUES (1, 'Alice');"
        res_sql = model.evaluate_answer(
            "Find all employee names",
            "SELECT name FROM employees;",
            ["SELECT"], [], question_format="coding", language="sql",
            test_cases=tc_sql, schema=schema, sample_data=sample_data
        )
        self.assertIn("score", res_sql)
        self.assertIsNone(res_sql.get("communication"))


class TheoryFourParametersInvariantsAndFollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalogue_path_java = os.path.join(
            os.path.dirname(__file__), "..", "app", "data", "question_bank", "java_theory_catalogue.json"
        )
        catalogue_path_dbms = os.path.join(
            os.path.dirname(__file__), "..", "app", "data", "question_bank", "dbms_theory_catalogue.json"
        )
        with open(catalogue_path_java, "r", encoding="utf-8") as f:
            cls.java_q = json.load(f)
        with open(catalogue_path_dbms, "r", encoding="utf-8") as f:
            cls.dbms_q = json.load(f)
        cls.all_200 = cls.java_q + cls.dbms_q
        cls.model = lp.DevFallbackModel()

    def test_200_catalogue_questions_invariants_across_four_answer_types(self):
        """
        For 200 catalogue questions x 4 answer types:
        - conceptCoverage <= correctness always
        - correctness == 0 -> score == 0 always
        - score == round(mean of the four) always
        """
        for i, item in enumerate(self.all_200):
            q_text = item["questionText"]
            ref_ans = item["referenceAnswer"]
            concepts = item.get("expectedConcepts", [])
            kps = lp._split_reference_key_points(ref_ans)
            first_kp = kps[0] if kps else ref_ans
            diff_item = self.all_200[(i + 101) % len(self.all_200)]
            diff_ref = diff_item["referenceAnswer"]
            vague_ans = "it is used for programming in computers and databases"

            answer_types = [
                ("reference", ref_ans),
                ("diff_reference", diff_ref),
                ("first_key_point", first_kp),
                ("vague_one_liner", vague_ans),
            ]

            for ans_type, ans in answer_types:
                res = self.model.evaluate_answer(
                    q_text, ans, concepts, [],
                    interview_type="technical", subject=item.get("subject", "java")
                )
                score = res["score"]
                cov = res["conceptCoverage"]
                cor = res["correctness"]
                rel = res["relevance"]
                com = res["communication"]

                # Invariant 1: conceptCoverage <= correctness always
                self.assertLessEqual(
                    cov, cor,
                    f"Invariant violated (coverage > correctness): {cov} > {cor} on {item['id']} ({ans_type})"
                )

                # Invariant 2: correctness == 0 -> score == 0 always
                if cor == 0:
                    self.assertEqual(
                        score, 0,
                        f"Invariant violated (correctness 0 but score != 0): score={score} on {item['id']} ({ans_type})"
                    )
                    self.assertEqual(rel, 0.0)
                    self.assertEqual(cov, 0.0)
                    self.assertEqual(com, 0.0)

                # Invariant 3: score == round(mean of the four) always
                expected_score = lp.calculate_theory_overall(rel, cor, cov, com)
                self.assertEqual(
                    score, expected_score,
                    f"Invariant violated (score != round(mean)): {score} != {expected_score} on {item['id']} ({ans_type})"
                )

    def test_followup_fake_reference_and_no_zero_dropout(self):
        """
        Follow-up test with a fake reference:
        - wrong answer -> <= 10
        - correct answer -> >= 70
        - relevance and communication are never 0 only because reference is missing.
        """
        q = "Can you provide an example of a checked exception?"
        fake_ref = (
            "A standard example of a checked exception is IOException. "
            "It requires a try-catch block or a throws clause because it is checked at compile time."
        )
        concepts = ["IOException", "compile time", "try-catch"]

        # Wrong answer
        wrong_ans = "umm like ArithmeticException when you do 6 + 5 and get 13"
        res_wrong = self.model.evaluate_answer(
            q, wrong_ans, concepts, [],
            reference_answer=fake_ref, subject="java"
        )
        self.assertLessEqual(res_wrong["score"], 10)
        self.assertLessEqual(res_wrong["conceptCoverage"], res_wrong["correctness"])

        # Correct answer in student's own words (paraphrased, different structure)
        correct_ans = (
            "IOException is a clear example of a checked exception. "
            "At compile time, code requires a try-catch block or a throws clause."
        )
        res_correct = self.model.evaluate_answer(
            q, correct_ans, concepts, [],
            reference_answer=fake_ref, subject="java"
        )
        self.assertGreaterEqual(res_correct["score"], 70)
        self.assertGreater(res_correct["relevance"], 0.0)
        self.assertGreater(res_correct["communication"], 0.0)

        # Missing reference: should fall back to parent reference and not drop relevance/communication to 0 solely due to missing ref
        q_fu = "Can you explain how a class is instantiated into an object?"
        fu_ans = (
            "You instantiate a class into an object at runtime by invoking new with the constructor, "
            "creating an instance that occupies its own memory."
        )
        res_missing_ref = self.model.evaluate_answer(
            q_fu, fu_ans, ["class", "object", "instantiation"], [],
            reference_answer=None, subject="follow_up"
        )
        self.assertGreater(res_missing_ref["relevance"], 0.0)
        self.assertGreater(res_missing_ref["communication"], 0.0)
        self.assertGreater(res_missing_ref["correctness"], 0.0)

    def test_problems_a_b_c_real_strings(self):
        """
        Tests for observed problems A, B, and C with the exact real strings:
        A: Follow-up checked exception with fake reference -> all four <= 10 and score <= 10, no coverage above correctness.
        B: Catalogue Q String immutability with stack answer -> score <= 20, coverage <= correctness.
        C: Nonsense encapsulation answer -> all four 0, score 0.
        """
        # Problem A
        q_a = "Can you provide an example of a checked exception that would require a try-catch block, and explain why it's necessary?"
        ans_a = "umm like ArithmeticException when you do 6 + 5 and get 13, you need try catch becoz otherwise the computer cant add properly"
        ref_a = (
            "An example of a checked exception is IOException or SQLException, which represents recoverable conditions outside program control. "
            "The compiler forces either handling it with a try-catch block or declaring it with throws to ensure application robustness."
        )
        res_a = self.model.evaluate_answer(
            q_a, ans_a, ["IOException", "compile time", "try-catch block"], [],
            reference_answer=ref_a, subject="java"
        )
        self.assertLessEqual(res_a["score"], 10)
        self.assertLessEqual(res_a["relevance"], 0.10)
        self.assertLessEqual(res_a["correctness"], 0.10)
        self.assertLessEqual(res_a["conceptCoverage"], 0.10)
        self.assertLessEqual(res_a["communication"], 0.10)
        self.assertLessEqual(res_a["conceptCoverage"], res_a["correctness"])

        # Problem B
        q_b = "Why are Strings immutable in Java?"
        ans_b = "strings are immutable becoz they are stored in the stack and stack cant be changed once the program starts"
        res_b = self.model.evaluate_answer(
            q_b, ans_b, ["String constant pool", "security", "thread safety"], [],
            subject="java"
        )
        self.assertLessEqual(res_b["score"], 20)
        self.assertLessEqual(res_b["conceptCoverage"], res_b["correctness"])

        # Problem C
        q_c = "What is encapsulation in Java and why is it useful?"
        ans_c = "encapsulation is when you put all the code in one capsule file so nobody can open it without scissors"
        res_c = self.model.evaluate_answer(
            q_c, ans_c, ["data hiding", "private fields", "getters and setters"], [],
            subject="java"
        )
        self.assertEqual(res_c["score"], 0)
        self.assertEqual(res_c["relevance"], 0.0)
        self.assertEqual(res_c["correctness"], 0.0)
        self.assertEqual(res_c["conceptCoverage"], 0.0)
        self.assertEqual(res_c["communication"], 0.0)
        self.assertIn("No correct key point found in the answer.", res_c["scoreReason"])

    def test_coding_sql_output_prediction_and_hr_non_regression(self):
        """
        Verify that coding, SQL, output prediction, and HR evaluations continue
        to function identically.
        """
        # Output prediction
        res_op = self.model.evaluate_answer(
            "What does this print?", "42", ["variables"], [],
            question_format="output_prediction", expected_output="42"
        )
        self.assertEqual(res_op["score"], 100)
        self.assertIsNone(res_op["communication"])

        # Java Coding
        tc = [{"input": "5", "expectedOutput": "10", "label": "Test 1"}]
        res_code = self.model.evaluate_answer(
            "Write a Java method to double an integer.",
            "public class Solution { public static int solve(int n) { return n * 2; } }",
            ["methods"], [], question_format="coding", language="java", test_cases=tc
        )
        self.assertIn("score", res_code)
        self.assertIsNone(res_code.get("communication"))

        # SQL
        schema = "CREATE TABLE employees (id INT, name TEXT);"
        tc_sql = [{"input": "", "expectedOutput": "Alice", "label": "Test 1"}]
        sample_data = "INSERT INTO employees VALUES (1, 'Alice');"
        res_sql = self.model.evaluate_answer(
            "Find all employee names",
            "SELECT name FROM employees;",
            ["SELECT"], [], question_format="coding", language="sql",
            test_cases=tc_sql, schema=schema, sample_data=sample_data
        )
        self.assertIn("score", res_sql)
        self.assertIsNone(res_sql.get("communication"))

        # HR evaluation
        res_hr = self.model.evaluate_answer(
            "Tell me about a time you worked in a team.",
            "I worked in a team of 4 engineers to deliver an e-commerce platform on time.",
            ["teamwork", "communication"], [],
            interview_type="hr"
        )
        self.assertGreater(res_hr["score"], 0)
        self.assertIn("accuracy", res_hr)
        self.assertEqual(
            res_hr["score"],
            calculate_hr_overall(res_hr["correctness"], res_hr["relevance"], res_hr["accuracy"], res_hr["communication"])
        )


if __name__ == "__main__":
    unittest.main()
