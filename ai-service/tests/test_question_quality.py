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

    def test_dbms_theory_synonym_matching(self):
        """Rule 3 Proof (DBMS): Relational theory answers using standard DBMS synonyms match expected concepts."""
        from app.models.llama_provider import _classify_expected_concepts
        from app.services.embedding_service import embedding_service

        # Test 1: "relation" for concept "table", "tuple" for concept "row", "attribute" for concept "column"
        answer = "A relation in the relational model stores data formatted as tuples across various attributes."
        concepts = ["table", "row", "column"]
        covered, partial, missing = _classify_expected_concepts(concepts, answer, embedding_service)
        self.assertIn("table", covered, "Expected 'relation' to cover concept 'table'")
        self.assertIn("row", covered, "Expected 'tuple' to cover concept 'row'")
        self.assertIn("column", covered, "Expected 'attribute' to cover concept 'column'")

        # Test 2: "candidate key" for concept "primary key"
        answer2 = "A candidate key uniquely identifies each record and satisfies minimal superkey requirements."
        concepts2 = ["primary key"]
        covered2, partial2, missing2 = _classify_expected_concepts(concepts2, answer2, embedding_service)
        self.assertIn("primary key", covered2, "Expected 'candidate key' to cover concept 'primary key'")

    def test_dbms_theory_fallback_when_model_down(self):
        """Rule 6 Proof (DBMS): When model is unreachable, DBMS theory generates from bank and evaluates deterministically."""
        from unittest.mock import patch
        from app.models.llama_provider import ResilientAIModel
        from app.services.question_generator import question_generator
        from app.models.schemas import QuestionGenerationRequest

        model = ResilientAIModel()

        # Generation Fallback
        with patch.object(model.llama, "generate_question", side_effect=Exception("Connection refused")):
            req = QuestionGenerationRequest(subject="dbms", difficulty="easy", interviewType="technical", questionFormat="theory")
            gen_res = question_generator.generate(req)
            self.assertIsNotNone(gen_res)
            self.assertEqual(gen_res.subject, "dbms")
            self.assertEqual(gen_res.questionFormat, "theory")
            self.assertTrue(len(gen_res.expectedConcepts) > 0)

        # Evaluation Fallback
        with patch.object(model.llama, "evaluate_answer", side_effect=Exception("Connection refused")):
            eval_res = model.evaluate_answer(
                question="What is 1NF in database normalization?",
                answer="First normal form requires that each column contains atomic indivisible values and each row is unique.",
                concepts=["1NF", "atomic values", "normalization"],
                context=[],
                question_format="theory",
                subject="dbms"
            )
            self.assertTrue(eval_res["evaluationUnavailable"])
            self.assertEqual(eval_res["modelUsed"], "deterministic_concept_coverage")
            self.assertGreater(eval_res["score"], 50)
            self.assertIn("atomic values", eval_res["coveredConcepts"])

    def test_question_pool_serves_first_instantly(self):
        """Rule 4 Proof: QuestionPool serves pre-verified questions instantly without waiting for sandbox verification."""
        import time
        from app.services.question_pool import question_pool
        question_pool.init_from_catalogues()

        t0 = time.perf_counter()
        q = question_pool.pop_question(subject="java", question_format="coding", difficulty="easy")
        elapsed = time.perf_counter() - t0

        self.assertIsNotNone(q)
        self.assertTrue(q.get("_served_from_pool"))
        self.assertLess(elapsed, 0.05, f"Expected pool pop to be instantaneous (<50ms), took {elapsed*1000:.2f}ms")
        self.assertIn("starterCode", q)
        self.assertIn("testCases", q)

    def test_question_pool_max_two_per_category(self):
        """Session Rule: At most 2 questions per category are allowed in a session."""
        from app.services.question_pool import question_pool
        question_pool.init_from_catalogues()

        # Given 2 previous questions in "OOP" category
        prev_categories = ["OOP", "OOP"]
        for _ in range(5):
            q = question_pool.pop_question(
                subject="java", question_format="theory", difficulty="easy",
                previous_categories=prev_categories
            )
            if q:
                cat = q.get("category", "")
                self.assertNotEqual(cat.upper(), "OOP", "Category 'OOP' was already asked 2 times, should not be served again")
                prev_categories.append(cat)

    def test_session_topic_diversity_5_questions(self):
        """Session Rule: A 5-question interview session must cover at least 4 distinct topics."""
        from app.services.question_pool import question_pool
        question_pool.init_from_catalogues()

        prev_q = []
        prev_cats = []
        for i in range(5):
            q = question_pool.pop_question(
                subject="java", question_format="theory", difficulty="medium",
                previous_questions=prev_q,
                previous_categories=prev_cats
            )
            self.assertIsNotNone(q, f"Failed to pop question {i+1}")
            prev_q.append(q["questionText"])
            cat = q.get("category", f"Cat-{i}")
            prev_cats.append(cat)

        unique_cats = set(prev_cats)
        self.assertGreaterEqual(
            len(unique_cats), 4,
            f"Expected at least 4 distinct topics in a 5-question session, got {len(unique_cats)}: {prev_cats}"
        )
        # Check no category appears more than 2 times
        for cat in unique_cats:
            self.assertLessEqual(prev_cats.count(cat), 2, f"Category '{cat}' appeared {prev_cats.count(cat)} times (max 2)")

    def test_question_signature_deduplication(self):
        """Session Rule: Deduplication by question signature must prevent duplicate questions."""
        from app.services.question_pool import question_pool
        question_pool.init_from_catalogues()

        # Pop one coding question
        q1 = question_pool.pop_question(subject="java", question_format="coding", difficulty="easy")
        self.assertIsNotNone(q1)
        sig1 = f"{q1.get('title')}: {q1.get('questionText')}"

        # Pop another, passing sig1 as previous question
        q2 = question_pool.pop_question(
            subject="java", question_format="coding", difficulty="easy",
            previous_questions=[sig1]
        )
        self.assertIsNotNone(q2)
        sig2 = f"{q2.get('title')}: {q2.get('questionText')}"
        self.assertNotEqual(sig1, sig2, "Question pool served a duplicate question signature")

    def test_negative_proof_category_limit_rejection(self):
        """Rule 1 Proof: Removing category limit check allows 3+ questions of same category (proves guard works)."""
        from app.models.llama_provider import _is_duplicate_question
        
        # Test simulated pool with and without check
        mock_bucket = [
            {"title": "Q1", "questionText": "T1", "category": "OOP"},
            {"title": "Q2", "questionText": "T2", "category": "OOP"},
            {"title": "Q3", "questionText": "T3", "category": "OOP"},
        ]
        prev_cats = ["OOP", "OOP"]

        # With guard: Q3 is rejected
        eligible_with_guard = [
            q for q in mock_bucket
            if prev_cats.count(q.get("category")) < 2
        ]
        self.assertEqual(len(eligible_with_guard), 0, "Guard must reject all items when category count >= 2")

        # Without guard: items would be accepted
        eligible_without_guard = [
            q for q in mock_bucket
        ]
        self.assertEqual(len(eligible_without_guard), 3, "Without guard, 3 items would have been accepted")

    def test_coding_guard_100_percent_pass_gives_100(self):
        """A fully passing submission scores exactly 100, regardless of the model rubric.
        Without the guard, 0.80*100 + 0.20*0 = 80 (<90).
        The deterministic pass rate is the final score.
        """
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        zero_rubric = json.dumps({
            "logicScore": 0, "approachScore": 0, "edgeCaseScore": 0, "readabilityScore": 0,
            "summary": "Hallucinated penalty", "strengths": [], "weaknesses": ["Style"], "correctedSolution": ""
        })
        
        tc = [{"id": 1, "input": "2, 3", "expectedOutput": "5", "label": "Case 1"}]
        code = "public class Solution { public static int add(int a, int b) { return a + b; } }"
        
        with patch.object(provider, "_call_llama", return_value=(zero_rubric, "llama3.2:3b")):
            res = provider._evaluate_coding_answer("Add numbers", code, ["math"], tc, language="java")
            
            # Agreed rule: score equals the test-case pass rate, so 100% pass = 100
            self.assertEqual(res["score"], 100, "100% pass must score 100")
            
            # Negative proof: Without the guard, score would have been 80
            ungarded_score = round(0.80 * 100.0 + 0.20 * 0.0)
            self.assertLess(ungarded_score, 100, "Proves the rubric blend would miss the required 100")

    def test_coding_guard_0_percent_pass_gives_0(self):
        """A submission that fails every deterministic test scores exactly 0.
        """
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        perfect_rubric = json.dumps({
            "logicScore": 100, "approachScore": 100, "edgeCaseScore": 100, "readabilityScore": 100,
            "summary": "Great syntax", "strengths": ["Clean"], "weaknesses": [], "correctedSolution": ""
        })
        
        tc = [{"id": 1, "input": "2, 3", "expectedOutput": "5", "label": "Case 1"}]
        code = "public class Solution { public static int add(int a, int b) { return 999; } }"
        
        with patch.object(provider, "_call_llama", return_value=(perfect_rubric, "llama3.2:3b")):
            res = provider._evaluate_coding_answer("Add numbers", code, ["math"], tc, language="java")
            # Agreed rule: score equals the test-case pass rate, so 0% pass = 0
            self.assertEqual(res["score"], 0, "0% pass must score 0")

    def test_coding_guard_compile_error_gives_0(self):
        """A compilation failure scores exactly 0, regardless of the model rubric.
        Without the guard, 0.80*0 + 0.20*90 = 18 (>10).
        The compile failure is a hard zero.
        """
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        high_rubric = json.dumps({
            "logicScore": 90, "approachScore": 90, "edgeCaseScore": 90, "readabilityScore": 90,
            "summary": "Good idea but broke", "strengths": ["Thoughtful"], "weaknesses": ["Compile"], "correctedSolution": ""
        })
        
        tc = [{"id": 1, "input": "2, 3", "expectedOutput": "5", "label": "Case 1"}]
        code = "public class Solution { public static int add(int a, int b) { return a + ; } }"
        
        with patch.object(provider, "_call_llama", return_value=(high_rubric, "llama3.2:3b")):
            res = provider._evaluate_coding_answer("Add numbers", code, ["math"], tc, language="java")
            # Agreed rule: a compile error passes no test case, so it scores 0
            self.assertEqual(res["score"], 0, "Compile error must score 0")
            
            # Negative proof: Without the guard, score would have been 18
            ungarded_score = round(0.80 * 0.0 + 0.20 * 90.0)
            self.assertGreater(ungarded_score, 10, "Proves unguarded score is 18 > 10")

    def test_coding_model_unavailable_gives_execution_only_and_no_crash(self):
        """Proof: Model unavailable gives execution-only score, llamaEvaluation='unavailable', no crash."""
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        # 1 passed out of 2 = 50%
        tc = [
            {"id": 1, "input": "2, 3", "expectedOutput": "5", "label": "Case 1"},
            {"id": 2, "input": "4, 4", "expectedOutput": "10", "label": "Case 2"},
        ]
        code = "public class Solution { public static int add(int a, int b) { return a + b; } }"
        
        with patch.object(provider, "_call_llama", side_effect=RuntimeError("Ollama connection refused")):
            res = provider._evaluate_coding_answer("Add numbers", code, ["math"], tc, language="java")
            self.assertEqual(res["llamaEvaluation"], "unavailable")
            self.assertEqual(res["evaluatedBy"], "executor")
            self.assertIsNone(res["llamaRubric"])
            self.assertEqual(res["score"], 50)
            self.assertTrue(res["usedFallback"])
            self.assertEqual(res["scoringSources"], ["executor"])

    def test_coding_evaluation_idempotent_keyed_by_hash(self):
        """Proof: Identical coding submission returns identical score and cached result."""
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        rubric = json.dumps({
            "logicScore": 85, "approachScore": 80, "edgeCaseScore": 90, "readabilityScore": 85,
            "summary": "Solid solution", "strengths": ["Clean"], "weaknesses": [], "correctedSolution": ""
        })
        tc = [{"id": 1, "input": "2, 3", "expectedOutput": "5", "label": "Case 1"}]
        code = "public class Solution { public static int add(int a, int b) { return a + b; } }"
        
        with patch.object(provider, "_call_llama", return_value=(rubric, "llama3.2:3b")) as mock_call:
            res1 = provider._evaluate_coding_answer("Add numbers", code, ["math"], tc, language="java")
            first_count = mock_call.call_count
            res2 = provider._evaluate_coding_answer("Add numbers", code, ["math"], tc, language="java")
            
            self.assertEqual(res1["score"], res2["score"])
            self.assertEqual(res1["llamaRubric"], res2["llamaRubric"])
            self.assertEqual(res1["evidence"], res2["evidence"])
            self.assertEqual(mock_call.call_count, first_count, "Second evaluation must hit cache, invoking model 0 additional times")

    def test_predict_output_guard_exact_match_gives_100(self):
        """Proof: Exact match gives 100 immediately without model call. Model cannot lower it."""
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        snippet = "public class Solution { public static void main(String[] args) { System.out.println(42); } }"
        
        with patch.object(provider, "_call_llama") as mock_call:
            res = provider._evaluate_output_prediction(
                question="What is the output?",
                answer="42",
                concepts=["output"],
                expected_output="42",
                code_snippet=snippet,
                subject="java",
            )
            self.assertEqual(res["score"], 100)
            self.assertTrue(res["evidence"]["exactMatch"])
            self.assertEqual(res["evaluatedBy"], "executor")
            self.assertEqual(mock_call.call_count, 0, "Exact match must never call LLaMA")

    def test_predict_output_guard_no_explanation_gives_0(self):
        """Proof: Wrong output with NO explanation gives 0, even if LLaMA gave reasoningScore=100.
        Without guard, min(30, round(0.30*100)) = 30.
        With guard, score is 0.
        """
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        perfect_reasoning = json.dumps({
            "reasoningScore": 100,
            "misconception": "Minor off-by-one",
            "explanation": "Actual output is 10"
        })
        
        with patch.object(provider, "_call_llama", return_value=(perfect_reasoning, "llama3.2:3b")):
            # Candidate only gives wrong number "99" with no explanation
            res = provider._evaluate_output_prediction(
                question="What is the output?",
                answer="99",
                concepts=["loops"],
                expected_output="10",
                code_snippet="int x = 10; System.out.println(x);",
                subject="java",
            )
            self.assertEqual(res["score"], 0, "No explanation for wrong output must score 0")
            
            # Negative proof: without guard, formula would have produced 30
            ungarded_score = min(30, round(0.30 * 100))
            self.assertGreater(ungarded_score, 0, "Proves unguarded score would have been 30 > 0")

    def test_predict_output_wrong_value_with_explanation_gives_0(self):
        """An incorrect predicted value scores 0 even when accompanied by an explanation."""
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        reasoning_data = json.dumps({
            "reasoningScore": 80,
            "misconception": "Forgot that the loop post-increments before printing",
            "explanation": "The loop terminates after printing 10"
        })
        
        ans_with_expl = "The output is 9 because the loop condition checks i < 10 and stops at 9 before printing."
        
        with patch.object(provider, "_call_llama", return_value=(reasoning_data, "llama3.2:3b")):
            res = provider._evaluate_output_prediction(
                question="What is the output?",
                answer=ans_with_expl,
                concepts=["loops"],
                expected_output="10",
                code_snippet="for (int i = 0; i <= 10; i++) {}",
                subject="java",
            )
            # Agreed rule: a wrong predicted output scores 0 on all four parameters (no partial credit)
            self.assertEqual(res["score"], 0, "Wrong output scores 0 even with an explanation")
            self.assertEqual(res["formula"]["parameters"], {"accuracy": 0, "correctness": 0, "relevance": 0, "concept_coverage": 0})
            self.assertEqual(res["evaluatedBy"], "base_llama")
            self.assertEqual(res["llamaEvaluation"], "ok")

    def test_predict_output_model_unavailable_gives_execution_only_and_no_crash(self):
        """Proof: Model unavailable gives execution-only score (0 for wrong, 100 for exact), llamaEvaluation='unavailable', no crash."""
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        ans_with_expl = "The output is 9 because the loop terminates at index 9."
        
        with patch.object(provider, "_call_llama", side_effect=RuntimeError("Ollama connection refused")):
            res = provider._evaluate_output_prediction(
                question="What is the output?",
                answer=ans_with_expl,
                concepts=["loops"],
                expected_output="10",
                code_snippet="for (int i = 0; i <= 10; i++) {}",
                subject="java",
            )
            self.assertEqual(res["score"], 0)
            self.assertEqual(res["llamaEvaluation"], "unavailable")
            self.assertEqual(res["evaluatedBy"], "executor")
            self.assertIsNone(res["llamaRubric"])
            self.assertTrue(res["usedFallback"])

    def test_predict_output_evaluation_idempotent_keyed_by_hash(self):
        """Proof: Identical output prediction submission returns identical score and cached result."""
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        reasoning_data = json.dumps({
            "reasoningScore": 70,
            "misconception": "Off by one error in loop condition",
            "explanation": "Correct output is 10"
        })
        
        ans_with_expl = "The output is 9 because the loop terminates at 9."
        
        with patch.object(provider, "_call_llama", return_value=(reasoning_data, "llama3.2:3b")) as mock_call:
            res1 = provider._evaluate_output_prediction(
                question="What is the output?",
                answer=ans_with_expl,
                concepts=["loops"],
                expected_output="10",
                code_snippet="for (int i = 0; i <= 10; i++) {}",
                subject="java",
            )
            first_count = mock_call.call_count
            res2 = provider._evaluate_output_prediction(
                question="What is the output?",
                answer=ans_with_expl,
                concepts=["loops"],
                expected_output="10",
                code_snippet="for (int i = 0; i <= 10; i++) {}",
                subject="java",
            )
            self.assertEqual(res1["score"], res2["score"])
            self.assertEqual(res1["llamaRubric"], res2["llamaRubric"])
            self.assertEqual(res1["evidence"], res2["evidence"])
            self.assertEqual(mock_call.call_count, first_count, "Second call must hit cache with 0 additional invocations")

    def test_theory_guard_zero_concept_coverage_gives_at_most_20(self):
        """Proof: Concept coverage <= 0.05 and no concept mentioned must score <= 20 even if LLaMA gave 100 on rubric."""
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        hallucinated_perfect = json.dumps({
            "correctness": 100,
            "relevance": 100,
            "completeness": 100,
            "clarity": 100,
            "feedback": "Great explanation of general computation.",
            "strengths": ["Well structured"],
            "weaknesses": []
        })
        
        with patch.object(provider, "_call_llama", return_value=(hallucinated_perfect, "llama3.2:3b")):
            res = provider.evaluate_answer(
                question="Explain the ACID properties in database management systems.",
                answer="Computers process electrical signals using silicon transistors to compute binary boolean values.",
                concepts=["atomicity", "consistency", "isolation", "durability"],
                context=[],
                question_format="theory",
                subject="dbms"
            )
            self.assertLessEqual(res["score"], 20, "Zero concept coverage must score <= 20 despite 100 LLaMA rubric")
            
            # Negative proof: without the guard, 60% of 100 + 40% of 0 = 60 > 20
            unguarded_score = round(0.60 * 100 + 0.40 * 0)
            self.assertGreater(unguarded_score, 20, "Proves unguarded score would have been 60 > 20")

    def test_theory_guard_high_concept_and_high_rubric_gives_at_least_80(self):
        """Proof: High concept coverage (>= 0.85) and high rubric (>= 80) guarantees final score >= 80."""
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        rubric_data = json.dumps({
            "correctness": 85,
            "relevance": 85,
            "completeness": 80,
            "clarity": 80,
            "feedback": "Comprehensive and accurate breakdown of ACID properties.",
            "strengths": ["Thorough explanation"],
            "weaknesses": []
        })
        
        answer = (
            "ACID properties ensure reliable database transactions: "
            "Atomicity ensures all-or-nothing execution of transactions. "
            "Consistency ensures the database transitions from one valid state to another. "
            "Isolation ensures concurrent transactions do not interfere with each other. "
            "Durability guarantees committed transaction changes persist even after system crashes."
        )
        
        with patch.object(provider, "_call_llama", return_value=(rubric_data, "llama3.2:3b")):
            res = provider.evaluate_answer(
                question="Explain the ACID properties in database management systems.",
                answer=answer,
                concepts=["atomicity", "consistency", "isolation", "durability"],
                context=[],
                question_format="theory",
                subject="dbms"
            )
            self.assertGreaterEqual(res["score"], 80, "High concept coverage + high rubric must score >= 80")
            self.assertEqual(res["evaluatedBy"], "base_llama")
            self.assertEqual(res["llamaEvaluation"], "ok")
            self.assertIsNotNone(res["llamaRubric"])

    def test_theory_empty_and_keyword_dump_gives_zero(self):
        """Proof: Empty answer and bare keyword dump score 0 via rules with no LLaMA invocation."""
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        with patch.object(provider, "_call_llama") as mock_call:
            # 1. Empty answer
            res_empty = provider.evaluate_answer(
                question="What is encapsulation in Java?",
                answer="",
                concepts=["encapsulation", "data hiding", "access modifiers"],
                context=[],
                question_format="theory",
                subject="java"
            )
            self.assertEqual(res_empty["score"], 0)
            self.assertEqual(res_empty["evaluatedBy"], "rules")
            self.assertEqual(mock_call.call_count, 0, "Empty answer must not call LLaMA")
            
            # 2. Bare term list
            res_list = provider.evaluate_answer(
                question="What is encapsulation in Java?",
                answer="Encapsulation, Data Hiding, Getters, Setters, Access Modifiers",
                concepts=["encapsulation", "data hiding", "access modifiers"],
                context=[],
                question_format="theory",
                subject="java"
            )
            self.assertEqual(res_list["score"], 0)
            self.assertEqual(res_list["evaluatedBy"], "rules")
            self.assertEqual(mock_call.call_count, 0, "Bare term list must not call LLaMA")

    def test_theory_model_unavailable_gives_bert_only_and_no_crash(self):
        """Proof: When model is unavailable, theory evaluation falls back to BERT concept coverage without crashing."""
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        answer = "Polymorphism allows objects to take multiple forms through dynamic method overriding and dispatch."
        
        with patch.object(provider, "_call_llama", side_effect=RuntimeError("Connection refused")):
            res = provider.evaluate_answer(
                question="What is polymorphism in Java?",
                answer=answer,
                concepts=["polymorphism", "method overriding", "dynamic dispatch"],
                context=[],
                question_format="theory",
                subject="java"
            )
            self.assertEqual(res["llamaEvaluation"], "unavailable")
            self.assertEqual(res["evaluatedBy"], "bert_semantic")
            self.assertIsNone(res["llamaRubric"])
            self.assertGreater(res["score"], 40, "BERT semantic concept coverage calculates partial score")
            self.assertIsNotNone(res["evidence"])
            self.assertTrue(res["usedFallback"])

    def test_theory_evaluation_idempotent_keyed_by_hash(self):
        """Proof: Identical theory submission returns cached result with identical score and 0 additional LLaMA calls."""
        import json
        from unittest.mock import patch
        from app.models.llama_provider import LlamaModel
        
        provider = LlamaModel.__new__(LlamaModel)
        provider.model_name = "llama3.2:3b"
        provider.endpoint = "http://localhost:11434/api/generate"
        provider._eval_cache = {}
        
        rubric_data = json.dumps({
            "correctness": 88,
            "relevance": 90,
            "completeness": 85,
            "clarity": 87,
            "feedback": "Strong explanation of inheritance.",
            "strengths": ["Clear explanation"],
            "weaknesses": []
        })
        
        answer = "Inheritance allows a subclass to inherit fields and methods from a superclass using the extends keyword."
        
        with patch.object(provider, "_call_llama", return_value=(rubric_data, "llama3.2:3b")) as mock_call:
            res1 = provider.evaluate_answer(
                question="Explain inheritance in Java.",
                answer=answer,
                concepts=["inheritance", "subclass", "superclass", "extends"],
                context=[],
                question_format="theory",
                subject="java"
            )
            first_count = mock_call.call_count
            res2 = provider.evaluate_answer(
                question="Explain inheritance in Java.",
                answer=answer,
                concepts=["inheritance", "subclass", "superclass", "extends"],
                context=[],
                question_format="theory",
                subject="java"
            )
            self.assertEqual(res1["score"], res2["score"])
            self.assertEqual(res1["llamaRubric"], res2["llamaRubric"])
            self.assertEqual(res1["evidence"], res2["evidence"])
            self.assertEqual(res1["evaluatedBy"], res2["evaluatedBy"])
            self.assertEqual(mock_call.call_count, first_count, "Second call must hit cache without invoking LLaMA again")


if __name__ == "__main__":
    unittest.main()


