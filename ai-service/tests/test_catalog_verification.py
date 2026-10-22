"""
Test Suite: Catalog Verification for Fallback Catalogues.
Verifies every entry in _GUARANTEED_UNIQUE_CODING_QUESTIONS and
_GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS:
- All coding reference solutions compile and pass 100% of their test cases.
- All coding starter codes pass strict leak guards (no loops, no conditionals, no ternaries, 1 statement).
- All coding question texts contain no leaked reference solution lines.
- All output prediction snippets are deterministic, compile, and execute in sandbox.
- All output prediction expected outputs match canonical stdout ground truth.
"""

import unittest
from app.models.llama_provider import (
    _GUARANTEED_UNIQUE_CODING_QUESTIONS,
    _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS,
    _load_raw_output_predictions,
)
from app.services.code_executor import (
    is_java_available,
    execute_coding_submission,
    is_snippet_deterministic,
    verify_predict_output_snippet,
    check_starter_code_leak,
    check_question_text_leak,
    normalize_value_str,
)


class TestCatalogVerification(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _load_raw_output_predictions()

    def test_guaranteed_unique_coding_catalog(self):
        """Verify all Java entries in _GUARANTEED_UNIQUE_CODING_QUESTIONS."""
        if not is_java_available():
            self.skipTest("JDK not available")

        total_checked = 0
        for (subj, diff), items in _GUARANTEED_UNIQUE_CODING_QUESTIONS.items():
            if subj != "java":
                continue
            for q in items:
                title = q.get("title", "Untitled")
                starter = q.get("starterCode", "")
                ref = q.get("referenceSolution", "")
                q_text = q.get("questionText", "")
                cases = q.get("testCases", [])

                with self.subTest(title=title, diff=diff):
                    # 1. Starter code leak guard
                    ok_starter, reason_starter = check_starter_code_leak(starter, ref)
                    self.assertTrue(ok_starter, f"Starter leak on '{title}': {reason_starter}")

                    # 2. Question text leak guard
                    ok_qtext, reason_qtext = check_question_text_leak(q_text, ref)
                    self.assertTrue(ok_qtext, f"Question text leak on '{title}': {reason_qtext}")

                    # 3. Test cases present and non-placeholder
                    self.assertGreaterEqual(len(cases), 2, f"Too few test cases on '{title}'")
                    for tc in cases:
                        self.assertNotIn("standard input sample", str(tc.get("input", "")).lower())
                        self.assertNotIn("valid expected result", str(tc.get("expectedOutput", "")).lower())

                    # 4. Sandbox execution of reference solution against all test cases
                    res = execute_coding_submission("java", ref, cases)
                    self.assertIsNone(res.get("compileError"), f"Compile error on '{title}': {res.get('compileError')}")
                    self.assertEqual(
                        res.get("passedCount"),
                        len(cases),
                        f"Not all test cases passed on '{title}': {res.get('passedCount')}/{len(cases)}",
                    )
                    total_checked += 1

        self.assertGreater(total_checked, 0, "No coding catalog questions were tested")

    def test_guaranteed_unique_output_predictions_catalog(self):
        """Verify all Java entries in _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS."""
        if not is_java_available():
            self.skipTest("JDK not available")

        total_checked = 0
        for (subj, diff), items in _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS.items():
            if subj != "java":
                continue
            for q in items:
                snip = q.get("codeSnippet", "")
                exp = q.get("expectedOutput", "")

                with self.subTest(snippet=snip[:40]):
                    # 1. Determinism check
                    ok_det, det_reason = is_snippet_deterministic(snip)
                    self.assertTrue(ok_det, f"Non-deterministic snippet: {det_reason}")

                    # 2. Sandbox execution & verification
                    ok_exec, canon_out, err = verify_predict_output_snippet(snip)
                    self.assertTrue(ok_exec, f"Execution failed: {err}")

                    # 3. Expected output matches ground truth
                    self.assertEqual(
                        normalize_value_str(exp),
                        normalize_value_str(canon_out),
                        f"Expected output mismatch for snippet:\n{snip}\nExp: {exp}\nGot: {canon_out}",
                    )
                    total_checked += 1

        self.assertGreater(total_checked, 0, "No output prediction catalog questions were tested")


if __name__ == "__main__":
    unittest.main()
