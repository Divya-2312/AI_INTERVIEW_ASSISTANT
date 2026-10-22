"""
Unit Test Suite for Question Quality & Verification Pipeline.
Covers:
1. Predict-the-output: execution-verified ground truth, non-deterministic rejection.
2. Coding: dual-solution independent verification, disagreement rejection, ground truth computation.
3. Starter code & question text leak guards: rejection of loops, conditionals, ternaries, multiple statements.
4. Deterministic starter code generation from method signature.
5. Rejection of placeholder test cases.
"""

import unittest
from app.services.code_executor import (
    is_snippet_deterministic,
    verify_predict_output_snippet,
    generate_deterministic_starter_code,
    check_starter_code_leak,
    check_question_text_leak,
    verify_dual_coding_solutions,
    is_java_available,
    execute_coding_submission,
    validate_sql_query_guard,
    execute_sql,
)


class TestQuestionQualityRules(unittest.TestCase):

    def test_non_deterministic_snippets_rejected(self):
        """Rule 1: Non-deterministic constructs must be rejected."""
        non_deterministic_snippets = [
            "Random r = new Random(); System.out.println(r.nextInt());",
            "System.out.println(Math.random());",
            "System.out.println(System.currentTimeMillis());",
            "System.out.println(System.nanoTime());",
            "System.out.println(new Object().hashCode());",
            "new Thread(() -> System.out.println(1)).start();",
            "Scanner sc = new Scanner(System.in); int x = sc.nextInt();",
            "Map<String, Integer> map = new HashMap<>(); for (String k : map.keySet()) { System.out.println(k); }",
            "Set<String> set = new HashSet<>(); for (String s : set) { System.out.println(s); }",
        ]
        for snip in non_deterministic_snippets:
            with self.subTest(snip=snip):
                ok, reason = is_snippet_deterministic(snip)
                self.assertFalse(
                    ok,
                    f"Expected snippet to be detected as non-deterministic:\n{snip}",
                )

    def test_deterministic_snippet_accepted_and_executed(self):
        """Rule 1: Deterministic snippets must compile and produce verified output."""
        if not is_java_available():
            self.skipTest("JDK not available")

        valid_snippet = (
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        int a = 5;\n"
            "        int b = 10;\n"
            "        System.out.println(a + b);\n"
            "    }\n"
            "}"
        )
        ok_det, _ = is_snippet_deterministic(valid_snippet)
        self.assertTrue(ok_det)
        ok, canon_out, err = verify_predict_output_snippet(valid_snippet)
        self.assertTrue(ok, f"Snippet execution failed: {err}")
        self.assertEqual(canon_out, "15")

    def test_snippet_printing_nothing_or_too_many_lines_rejected(self):
        """Rule 1: Snippets that print nothing or >15 lines must be rejected."""
        if not is_java_available():
            self.skipTest("JDK not available")

        # Prints nothing
        no_print = (
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        int x = 42;\n"
            "    }\n"
            "}"
        )
        ok, out, err = verify_predict_output_snippet(no_print)
        self.assertFalse(ok)
        self.assertTrue("nothing" in err.lower() or "empty" in err.lower())

        # Prints >15 lines
        too_many_lines = (
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        for (int i = 0; i < 20; i++) System.out.println(i);\n"
            "    }\n"
            "}"
        )
        ok, out, err = verify_predict_output_snippet(too_many_lines)
        self.assertFalse(ok)
        self.assertIn("15", err)

    def test_starter_code_leak_guards(self):
        """Rule 3: starterCode must fail if it contains loops, conditionals, ternaries, or extra statements."""
        ref_solution = (
            "public class Solution {\n"
            "    public int maxSubArray(int[] nums) {\n"
            "        int max = nums[0];\n"
            "        int curr = nums[0];\n"
            "        for (int i = 1; i < nums.length; i++) {\n"
            "            curr = Math.max(nums[i], curr + nums[i]);\n"
            "            max = Math.max(max, curr);\n"
            "        }\n"
            "        return max;\n"
            "    }\n"
            "}"
        )

        leaked_starters = [
            # Loop (for)
            (
                "public class Solution {\n"
                "    public int maxSubArray(int[] nums) {\n"
                "        for (int i = 0; i < nums.length; i++) {}\n"
                "        return 0;\n"
                "    }\n"
                "}",
                "loop",
            ),
            # Loop (while)
            (
                "public class Solution {\n"
                "    public int maxSubArray(int[] nums) {\n"
                "        while (nums.length > 0) {}\n"
                "        return 0;\n"
                "    }\n"
                "}",
                "loop",
            ),
            # Conditional (if)
            (
                "public class Solution {\n"
                "    public int maxSubArray(int[] nums) {\n"
                "        if (nums == null) return 0;\n"
                "        return 0;\n"
                "    }\n"
                "}",
                "conditional",
            ),
            # Switch
            (
                "public class Solution {\n"
                "    public int maxSubArray(int[] nums) {\n"
                "        switch(nums.length) { case 0: return 0; }\n"
                "        return 0;\n"
                "    }\n"
                "}",
                "switch",
            ),
            # Ternary
            (
                "public class Solution {\n"
                "    public int maxSubArray(int[] nums) {\n"
                "        int x = nums.length > 0 ? 1 : 0;\n"
                "        return x;\n"
                "    }\n"
                "}",
                "ternary",
            ),
            # More than one statement
            (
                "public class Solution {\n"
                "    public int maxSubArray(int[] nums) {\n"
                "        int dummy = 42;\n"
                "        return 0;\n"
                "    }\n"
                "}",
                "statement",
            ),
        ]

        for code, expected_keyword in leaked_starters:
            with self.subTest(expected_keyword=expected_keyword):
                ok, reason = check_starter_code_leak(code, ref_solution)
                self.assertFalse(ok, f"Expected leak detection for {expected_keyword}")
                self.assertTrue(
                    any(term in reason.lower() for term in ["loop", "if", "switch", "ternary", "statement"]),
                    f"Unexpected reason: {reason}",
                )

    def test_deterministic_starter_code_generation(self):
        """Rule 3: Deterministic starter code must be built from signature only and pass leak guard."""
        signatures = [
            ("public int solve(int[] nums)", "return 0;"),
            ("public boolean isValid(String s)", "return false;"),
            ("public String reverseWords(String s)", 'return "";'),
            ("public int[] twoSum(int[] nums, int target)", "return new int[0];"),
            ("public void sortColors(int[] nums)", "// Write your code here"),
            ("public List<Integer> findDuplicates(int[] nums)", "return new java.util.ArrayList<>();"),
        ]

        for sig, expected_snippet in signatures:
            with self.subTest(sig=sig):
                starter = generate_deterministic_starter_code(sig)
                self.assertIn("public class Solution", starter)
                self.assertIn("// Write your code here", starter)
                self.assertIn(expected_snippet, starter)
                ok, reason = check_starter_code_leak(starter, "")
                self.assertTrue(ok, f"Generated starter failed leak check: {reason}")

    def test_question_text_leak_guard(self):
        """Rule 3: questionText must not contain code lines from referenceSolution."""
        ref = (
            "public class Solution {\n"
            "    public int countPrimes(int n) {\n"
            "        boolean[] isPrime = new boolean[n];\n"
            "        Arrays.fill(isPrime, true);\n"
            "        return 0;\n"
            "    }\n"
            "}"
        )
        leaked_q = "Count primes up to n. Hint: use Arrays.fill(isPrime, true); in your code."
        ok, reason = check_question_text_leak(leaked_q, ref)
        self.assertFalse(ok)
        self.assertTrue("reference solution" in reason.lower() or "leaked" in reason.lower())

        clean_q = "Count the number of prime numbers strictly less than a non-negative integer n."
        ok, reason = check_question_text_leak(clean_q, ref)
        self.assertTrue(ok)

    def test_dual_coding_solutions_disagreement_rejected(self):
        """Rule 2: If referenceSolution and alternativeSolution disagree, question is rejected."""
        if not is_java_available():
            self.skipTest("JDK not available")

        # Optimal reference solution: returns a + b
        ref = (
            "public class Solution {\n"
            "    public int add(int a, int b) {\n"
            "        return a + b;\n"
            "    }\n"
            "}"
        )
        # Buggy alternative solution: returns a - b
        alt_buggy = (
            "public class Solution {\n"
            "    public int add(int a, int b) {\n"
            "        return a - b;\n"
            "    }\n"
            "}"
        )
        test_inputs = ["1, 2", "10, 20", "5, 5"]

        ok, cases, err = verify_dual_coding_solutions(ref, alt_buggy, test_inputs)
        self.assertFalse(ok)
        self.assertIn("disagreement", err.lower())

    def test_dual_coding_solutions_agreement_computes_ground_truth(self):
        """Rule 2: Both solutions agree -> verify determinism and compute true expected outputs."""
        if not is_java_available():
            self.skipTest("JDK not available")

        ref = (
            "public class Solution {\n"
            "    public int maxElement(int[] nums) {\n"
            "        int m = nums[0];\n"
            "        for (int x : nums) if (x > m) m = x;\n"
            "        return m;\n"
            "    }\n"
            "}"
        )
        alt = (
            "public class Solution {\n"
            "    public int maxElement(int[] nums) {\n"
            "        int[] copy = nums.clone();\n"
            "        java.util.Arrays.sort(copy);\n"
            "        return copy[copy.length - 1];\n"
            "    }\n"
            "}"
        )
        test_inputs = ["[3, 1, 4, 1, 5, 9]", "[-10, -5, -20]", "[42]"]

        ok, cases, err = verify_dual_coding_solutions(ref, alt, test_inputs)
        self.assertTrue(ok, f"Expected dual solutions to pass: {err}")
        self.assertEqual(len(cases), 3)
        self.assertEqual(cases[0]["expectedOutput"], "9")
        self.assertEqual(cases[1]["expectedOutput"], "-5")
        self.assertEqual(cases[2]["expectedOutput"], "42")

    def test_missing_alternative_solution_rejected(self):
        """Rule 2: Missing alternative solution must be rejected."""
        ref = (
            "public class Solution {\n"
            "    public int solve() { return 1; }\n"
            "}"
        )
        ok, cases, err = verify_dual_coding_solutions(ref, "", ["1", "2"])
        self.assertFalse(ok)
        self.assertIn("missing alternative solution", err.lower())

    def test_dual_coding_solutions_non_deterministic_rejected(self):
        """Rule 2 Proof: If solution contains non-deterministic constructs, it must fail."""
        ref_nondet = (
            "public class Solution {\n"
            "    public int solve(int n) {\n"
            "        return new java.util.Random().nextInt(100) + n;\n"
            "    }\n"
            "}"
        )
        alt = (
            "public class Solution {\n"
            "    public int solve(int n) { return n; }\n"
            "}"
        )
        ok, cases, err = verify_dual_coding_solutions(ref_nondet, alt, ["1", "2"])
        self.assertFalse(ok)
        self.assertIn("non-deterministic", err.lower())

    def test_dual_coding_solutions_compilation_failure_rejected(self):
        """Rule 2 Proof: If alternative solution has syntax error, it must fail."""
        ref = (
            "public class Solution {\n"
            "    public int solve(int n) { return n * 2; }\n"
            "}"
        )
        alt_syntax_err = (
            "public class Solution {\n"
            "    public int solve(int n) { return n * ; }\n"
            "}"
        )
        ok, cases, err = verify_dual_coding_solutions(ref, alt_syntax_err, ["1", "2"])
        self.assertFalse(ok)
        self.assertIn("compilation error", err.lower())

    def test_sql_guard_allows_single_select(self):
        """SQL Guard: Valid single SELECT queries must be allowed."""
        queries = [
            "SELECT name, age FROM users WHERE age >= 18;",
            "select id, count(*) from orders group by id having count(*) > 5",
            "-- Comment\nSELECT * FROM customers WHERE status = 'ACTIVE' /* block */",
            "SELECT 'drop table inside string' AS title FROM articles;",
        ]
        for q in queries:
            with self.subTest(query=q):
                ok, err = validate_sql_query_guard(q)
                self.assertTrue(ok, f"Expected query to pass guard: {err}")

    def test_sql_guard_allows_with_select(self):
        """SQL Guard: CTE WITH ... SELECT queries must be allowed."""
        q = "WITH active_users AS (SELECT id, name FROM users WHERE active = 1) SELECT * FROM active_users;"
        ok, err = validate_sql_query_guard(q)
        self.assertTrue(ok, f"Expected CTE to pass guard: {err}")

    def test_sql_guard_rejects_dangerous_keywords(self):
        """SQL Guard: Non-SELECT and destructive keywords must be rejected before execution."""
        dangerous_queries = [
            ("DROP TABLE users;", "drop"),
            ("DELETE FROM employees WHERE id = 1;", "delete"),
            ("UPDATE accounts SET balance = 1000;", "update"),
            ("INSERT INTO logs VALUES ('test');", "insert"),
            ("ALTER TABLE users ADD COLUMN phone TEXT;", "alter"),
            ("ATTACH DATABASE ':memory:' AS evil;", "attach"),
            ("DETACH DATABASE evil;", "detach"),
            ("PRAGMA table_info(users);", "pragma"),
            ("VACUUM;", "vacuum"),
            ("REINDEX;", "reindex"),
            ("TRUNCATE TABLE users;", "truncate"),
            ("CREATE TABLE hacked (id INT);", "create"),
        ]
        for q, kw in dangerous_queries:
            with self.subTest(keyword=kw):
                ok, err = validate_sql_query_guard(q)
                self.assertFalse(ok, f"Expected {kw} to be rejected")
                self.assertTrue(
                    kw in err.lower() or "only select" in err.lower(),
                    f"Unexpected error reason: {err}",
                )

    def test_sql_guard_rejects_chained_multiple_statements(self):
        """SQL Guard: Chained semicolons/multiple statements must be rejected."""
        chained = "SELECT * FROM users; DROP TABLE users;"
        ok, err = validate_sql_query_guard(chained)
        self.assertFalse(ok)
        self.assertIn("multiple sql statements", err.lower())

    def test_sql_execution_blocked_by_guard(self):
        """SQL Execution: A query violating the guard must be rejected with status GUARD_VIOLATION."""
        schema = "CREATE TABLE users (id INT, name TEXT);"
        test_cases = [{"input": "standard", "expectedOutput": "1 | Alice"}]
        evil_query = "DROP TABLE users;"
        res = execute_sql(
            candidate_query=evil_query,
            schema=schema,
            test_cases=test_cases,
        )
        self.assertEqual(res["passedCount"], 0)
        self.assertIn("sql guard rejected", res["compileError"].lower())
        self.assertEqual(res["results"][0]["status"], "GUARD_VIOLATION")

    def test_predict_output_snippet_syntax_error_rejected(self):
        """Rule 1 Proof: Broken Java snippets with compile errors must be rejected."""
        if not is_java_available():
            self.skipTest("JDK not available")
        broken_snippet = (
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        int x = ;\n"
            "    }\n"
            "}"
        )
        ok, out, err = verify_predict_output_snippet(broken_snippet)
        self.assertFalse(ok)
        self.assertTrue("compilation failed" in err.lower() or "error" in err.lower())

    def test_predict_output_snippet_infinite_loop_timeout_rejected(self):
        """Rule 1 Proof: Snippets with infinite loops must time out and be rejected."""
        if not is_java_available():
            self.skipTest("JDK not available")
        infinite_loop_snippet = (
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        while (true) {}\n"
            "    }\n"
            "}"
        )
        ok, out, err = verify_predict_output_snippet(infinite_loop_snippet, timeout_sec=2.0)
        self.assertFalse(ok)
        self.assertIn("timed out", err.lower())

    def test_predict_output_crlf_lf_whitespace_normalization(self):
        """Rule 1: Line ending variations (CRLF vs LF) and surrounding whitespace must match identically."""
        from app.models.llama_provider import _canonical_output
        out_lf = "Line 1\nLine 2\nLine 3"
        out_crlf = "Line 1\r\nLine 2\r\nLine 3\r\n"
        out_trailing_spaces = "Line 1   \nLine 2 \nLine 3\n\n"
        self.assertEqual(_canonical_output(out_lf), _canonical_output(out_crlf))
        self.assertEqual(_canonical_output(out_lf), _canonical_output(out_trailing_spaces))

    def test_java_theory_synonym_matching(self):
        """Rule 3: Candidate answers using valid domain synonyms must match expected concepts."""
        from app.models.llama_provider import _classify_expected_concepts
        from app.services.embedding_service import embedding_service
        
        # Test 1: "derived class" for concept "subclass"
        answer1 = "In object-oriented programming, a derived class inherits behavior from its parent."
        concepts1 = ["subclass", "inheritance"]
        covered, partial, missing = _classify_expected_concepts(concepts1, answer1, embedding_service)
        self.assertIn("subclass", covered, "Expected 'derived class' to cover concept 'subclass'")
        self.assertIn("inheritance", covered)

        # Test 2: "instance creation" for concept "instantiation"
        answer2 = "Object creation is done using the new keyword to allocate memory on the heap."
        concepts2 = ["instantiation"]
        covered2, partial2, missing2 = _classify_expected_concepts(concepts2, answer2, embedding_service)
        self.assertIn("instantiation", covered2, "Expected 'object creation' to cover concept 'instantiation'")

        # Test 3: "member function" for concept "method"
        answer3 = "A class encapsulates data members and member functions that operate on that data."
        concepts3 = ["method", "encapsulation"]
        covered3, partial3, missing3 = _classify_expected_concepts(concepts3, answer3, embedding_service)
        self.assertIn("method", covered3, "Expected 'member function' to cover concept 'method'")

    def test_java_theory_evaluation_idempotent(self):
        """Rule 4: Evaluation must be idempotent. Evaluating the same (question, answer) returns the same score."""
        from app.models.llama_provider import DevFallbackModel, _THEORY_EVAL_CACHE
        fallback_model = DevFallbackModel()
        question = "What is polymorphism in Java?"
        answer = "Polymorphism allows objects of different classes to be treated through a common interface, using method overriding."
        concepts = ["polymorphism", "method overriding", "dynamic dispatch"]

        res1 = fallback_model.evaluate_answer(question, answer, concepts, context=[], question_format="theory")
        res2 = fallback_model.evaluate_answer(question, answer, concepts, context=[], question_format="theory")
        
        self.assertEqual(res1["score"], res2["score"])
        self.assertEqual(res1["conceptCoverage"], res2["conceptCoverage"])
        self.assertEqual(res1["coveredConcepts"], res2["coveredConcepts"])
        self.assertEqual(res1["missingConcepts"], res2["missingConcepts"])

    def test_java_theory_fallback_when_model_down(self):
        """Rule 6: If base model is down and STRICT_AI_MODE is on, theory generation falls back to curated bank, and evaluation sets evaluationUnavailable=True."""
        from unittest.mock import patch
        from app.models.llama_provider import ResilientAIModel
        from app.config import settings

        model = ResilientAIModel()
        
        # Test Generation Fallback: when provider fails, question_generator falls back to curated catalogue
        from app.services.question_generator import question_generator
        from app.models.schemas import QuestionGenerationRequest
        with patch.object(model.llama, "generate_question", side_effect=Exception("Connection refused")):
            req = QuestionGenerationRequest(subject="java", difficulty="easy", interviewType="technical", questionFormat="theory")
            gen_res = question_generator.generate(req)
            self.assertIsNotNone(gen_res)
            self.assertEqual(gen_res.subject, "java")
            self.assertEqual(gen_res.questionFormat, "theory")
            self.assertTrue(len(gen_res.expectedConcepts) > 0)

        # Test Evaluation Fallback: when llama.evaluate_answer throws, deterministic concept coverage used
        with patch.object(model.llama, "evaluate_answer", side_effect=Exception("Connection refused")):
            eval_res = model.evaluate_answer(
                question="What is encapsulation?",
                answer="Encapsulation is data hiding using private access modifiers and public getters/setters.",
                concepts=["encapsulation", "data hiding", "access modifiers"],
                context=[],
                question_format="theory"
            )
            self.assertTrue(eval_res["evaluationUnavailable"])
            self.assertEqual(eval_res["modelUsed"], "deterministic_concept_coverage")
            self.assertGreater(eval_res["score"], 50)
            self.assertIn("encapsulation", eval_res["coveredConcepts"])


if __name__ == "__main__":
    unittest.main()

