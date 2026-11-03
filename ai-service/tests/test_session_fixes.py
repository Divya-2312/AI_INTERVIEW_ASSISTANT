"""
Regression tests from a real Easy Java-theory session:
- Easy questions must be easy (level filter, catalogue tags).
- A correct answer must not be zeroed only because no anchor word matched.
- The shown score must equal the round-half-up mean of the four shown parameters.
Run:  python -m unittest tests/test_session_fixes.py
"""
import json
import os
import random
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "..", "app")
PROVIDER_SRC = os.path.join(APP, "models", "llama_provider.py")
BANK = os.path.join(APP, "data", "question_bank")

# Questions asked in the Easy session that were NOT easy.
HARD_ASKED_AS_EASY = [
    "What is the primary difference between the generational CMS (Concurrent Mark-and-Sweep) garbage "
    "collectors in the JVM, such as G1 and ZGC, and how does it relate to the traditional CMS collector?",
    "Consider a scenario where two threads, T1 and T2, access shared variables through a lock, but T1 "
    "performs a volatile read before T2 writes to it. How does the happens-before relationship affect "
    "the visibility of the write?",
]
EASY_ASKED_OK = [
    "What is the purpose of the String pool in Java?",
    "What is a constructor in Java?",
    "What is a List in Java?",
]


def _level_checker():
    from app.models.llama_provider import _question_level_problem
    return _question_level_problem


class TestDifficultyFilter(unittest.TestCase):
    def test_advanced_topics_rejected_for_easy(self):
        check = _level_checker()
        for q in HARD_ASKED_AS_EASY:
            self.assertTrue(check(q, "easy"), q)
        self.assertTrue(check(
            "What is the purpose of the transient keyword in Java when serializing objects?",
            "easy",
        ))

    def test_easy_questions_accepted(self):
        check = _level_checker()
        for q in EASY_ASKED_OK:
            self.assertEqual(check(q, "easy"), "", q)

    def test_hard_level_has_no_limit(self):
        check = _level_checker()
        for q in HARD_ASKED_AS_EASY:
            self.assertEqual(check(q, "hard"), "")

    def test_long_or_double_questions_rejected_for_easy(self):
        check = _level_checker()
        self.assertTrue(check("What is a class? What is an object?", "easy"))
        self.assertTrue(check(
            "What is the purpose of the String pool in Java, and how does it relate to String immutability?",
            "easy",
        ))
        self.assertTrue(check(" ".join(["word"] * 40) + "?", "easy"))

    def test_catalogue_easy_and_medium_questions_pass_their_own_level(self):
        check = _level_checker()
        for name in ("java_theory_catalogue.json", "dbms_theory_catalogue.json"):
            with open(os.path.join(BANK, name), encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else next(v for v in data.values() if isinstance(v, list))
            easy = [i for i in items if i.get("difficulty") == "easy"]
            self.assertGreaterEqual(len(easy), 10, name)
            for i in easy:
                self.assertEqual(check(i["questionText"], "easy"), "", i.get("id"))


class TestNoWordMatchZeroGate(unittest.TestCase):
    def test_gate_removed_from_both_evaluators(self):
        with open(PROVIDER_SRC, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("not has_any_concept_anchor and concept_anchors", src)


class TestShownScoreEqualsMeanOfShownParameters(unittest.TestCase):
    def test_formula_object_for_every_module(self):
        from app.utils.scoring_formulas import build_formula_object, round_half_up
        rnd = random.Random(7)
        for module in ("theory", "hr", "output_prediction", "coding", "sql"):
            for _ in range(200):
                a, c, r, k = (rnd.randint(0, 100) for _ in range(4))
                f = build_formula_object(module, a, c, r, k)
                p = f["parameters"]
                self.assertEqual(f["score"], round_half_up((p["accuracy"] + p["correctness"] + p["relevance"] + p["concept_coverage"]) / 4.0))


if __name__ == "__main__":
    unittest.main()
