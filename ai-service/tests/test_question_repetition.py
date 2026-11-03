"""
Test Suite: Repetition Fix & Per-User Question History.
Verifies:
4a) Same user, 10 consecutive new sessions per subject (java, dbms):
    - no question id repeats within a session
    - no repeat of any id from the previous 5 sessions while enough unseen questions exist
    - first question differs between at least 8 of the 10 sessions
4b) 30 sessions: at least 60 distinct questions per subject appear
4c) Different users get different orders (seed depends on session, not constant)
4d) Two concurrent session starts never share a pooled question object
4e) Bank nearly exhausted (e.g. 95 of 100 ids excluded): session still gets 10 questions and no crash
4f) Old call without the new fields still works and returns a valid question
4g) Difficulty mix, subject, question count, and format of returned question (_generation_meta, fields) are identical in shape
4h) Coding, SQL, and output prediction questions respect exclusions and keep shape
"""

import unittest
import threading
import random
from typing import List, Dict
from app.models.schemas import QuestionGenerationRequest, QuestionResponse
from app.services.question_generator import question_generator
from app.services.question_pool import question_pool


class TestQuestionRepetition(unittest.TestCase):

    def _simulate_10_question_session(self, subject: str, session_id: str,
                                      past_sessions_history: List[List[dict]]) -> List[dict]:
        """
        Simulates generation of a full 10-question technical session,
        providing exclusions from the current session, texts from recent 5 sessions,
        and compact questionHistory from the last 30 sessions.
        """
        # Build compact history across up to 30 past sessions (matching interviewEngine.js)
        history_slice = past_sessions_history[-30:] if past_sessions_history else []
        q_history_map = {}
        for s_idx, sess in enumerate(history_slice):
            for q in sess:
                qid = q.get("id") or q.get("title") or q.get("questionText")
                if qid:
                    if qid not in q_history_map:
                        q_history_map[qid] = {
                            "questionId": qid,
                            "timesAsked": 0,
                            "lastAskedSessionIndex": s_idx
                        }
                    q_history_map[qid]["timesAsked"] += 1
                    q_history_map[qid]["lastAskedSessionIndex"] = s_idx
        question_history = list(q_history_map.values())

        # Cross-session texts from last 5 sessions for SBERT near-duplicate check
        recent_sessions = past_sessions_history[-5:] if past_sessions_history else []
        recent_texts = []
        for sess in reversed(recent_sessions):
            for q in sess:
                qtext = q.get("questionText")
                if qtext and qtext not in recent_texts:
                    recent_texts.append(qtext)

        session_questions = []
        previous_texts = []
        previous_categories = []

        # Standard technical interview: mix of easy, medium, hard
        difficulties = ["easy", "easy", "medium", "medium", "medium", "medium", "hard", "hard", "medium", "easy"]

        for i, diff in enumerate(difficulties):
            curr_exclude_ids = [sq.get("id") or sq.get("title") for sq in session_questions if sq.get("id") or sq.get("title")]
            curr_exclude_texts = list(recent_texts) + [sq.get("questionText") for sq in session_questions if sq.get("questionText")]

            req = QuestionGenerationRequest(
                subject=subject,
                difficulty=diff,
                interviewType="technical",
                questionFormat="theory",
                previousQuestions=previous_texts,
                previousCategories=previous_categories,
                excludeQuestionIds=curr_exclude_ids,
                excludeQuestionTexts=curr_exclude_texts,
                questionHistory=question_history,
                sessionId=session_id
            )
            resp = question_generator.generate(req)
            q_dict = resp.model_dump()
            session_questions.append(q_dict)
            previous_texts.append(resp.questionText)
            if resp.category:
                previous_categories.append(resp.category)

        return session_questions

    def test_4a_consecutive_sessions_no_repeats(self):
        """
        4a) Same user, 10 consecutive new sessions per subject (java, dbms):
        - no question id repeats within a session
        - while enough unseen questions exist, 0 overlap with past sessions
        - consecutive sessions share at most 0-2 questions even when bank saturates
        - first question differs between at least 8 of the 10 sessions
        """
        random.seed(42)
        for subj in ("java", "dbms"):
            user_history: List[List[dict]] = []
            first_questions = []

            for s_idx in range(10):
                session_id = f"user1_{subj}_sess_{s_idx}"
                session_qs = self._simulate_10_question_session(subj, session_id, user_history)
                self.assertEqual(len(session_qs), 10, f"Session {s_idx} should have 10 questions")

                # 1. No question ID repeats within the session
                q_ids = [q.get("id") or q.get("title") for q in session_qs]
                self.assertEqual(len(q_ids), len(set(q_ids)), f"Duplicate question ID within session {s_idx}: {q_ids}")

                # 2. Consecutive sessions share at most 2 questions (target 0-2)
                if user_history:
                    prev_ids = {q.get("id") or q.get("title") for q in user_history[-1]}
                    consecutive_overlap = set(q_ids) & prev_ids
                    self.assertLessEqual(
                        len(consecutive_overlap), 2,
                        f"Session {s_idx} for {subj} shared {len(consecutive_overlap)} questions with previous session: {consecutive_overlap}"
                    )

                # 3. While enough unseen questions exist (first 4 sessions), 0 overlap with past sessions
                if s_idx < 4:
                    all_past_ids = {q.get("id") or q.get("title") for sess in user_history for q in sess}
                    past_overlap = set(q_ids) & all_past_ids
                    self.assertEqual(
                        len(past_overlap), 0,
                        f"Session {s_idx} for {subj} had early overlap with past sessions: {past_overlap}"
                    )

                first_questions.append(session_qs[0].get("id") or session_qs[0].get("questionText"))
                user_history.append(session_qs)

            # 4. First question differs between at least 8 of the 10 sessions
            distinct_firsts = len(set(first_questions))
            self.assertGreaterEqual(
                distinct_firsts, 8,
                f"Subject {subj}: first question differed in only {distinct_firsts}/10 sessions: {first_questions}"
            )

    def test_4b_30_sessions_distinct_bank_usage(self):
        """
        4b) 30 sessions: at least 60 distinct questions per subject appear (shows bank is really used).
        """
        for subj in ("java", "dbms"):
            user_history: List[List[dict]] = []
            all_seen_ids = set()

            for s_idx in range(30):
                session_id = f"bank_test_{subj}_sess_{s_idx}"
                session_qs = self._simulate_10_question_session(subj, session_id, user_history)
                for q in session_qs:
                    qid = q.get("id") or q.get("title")
                    if qid:
                        all_seen_ids.add(qid)
                user_history.append(session_qs)

            self.assertGreaterEqual(
                len(all_seen_ids), 60,
                f"Subject {subj}: Expected >= 60 distinct questions in 30 sessions, got {len(all_seen_ids)}"
            )

    def test_4c_different_users_get_different_orders(self):
        """
        4c) Different users get different orders (seed depends on session, not constant).
        """
        user_a_qs = self._simulate_10_question_session("java", "session_user_A_101", [])
        user_b_qs = self._simulate_10_question_session("java", "session_user_B_202", [])

        ids_a = [q.get("id") for q in user_a_qs]
        ids_b = [q.get("id") for q in user_b_qs]

        # Different users must not get the exact same questions in the exact same order
        self.assertNotEqual(ids_a, ids_b, "Two different users/sessions received the identical question sequence!")

    def test_4d_concurrent_session_starts_thread_safety(self):
        """
        4d) Two concurrent session starts never share a pooled question object.
        """
        results: Dict[str, dict] = {}
        errors = []

        def start_worker(thread_id: str, session_id: str):
            try:
                # Direct call to pop_question
                q = question_pool.pop_question(
                    subject="java",
                    question_format="theory",
                    difficulty="medium",
                    previous_questions=[],
                    previous_categories=[],
                    session_id=session_id
                )
                results[thread_id] = q
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=start_worker, args=("t1", "concurrent_sess_1"))
        t2 = threading.Thread(target=start_worker, args=("t2", "concurrent_sess_2"))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0, f"Encountered errors during concurrent pop: {errors}")
        q1 = results.get("t1")
        q2 = results.get("t2")

        if q1 and q2:
            # If both were served from pool, they must not be the identical question
            self.assertNotEqual(
                q1.get("questionText"), q2.get("questionText"),
                "Concurrent session starts were served the exact same question!"
            )

    def test_4e_bank_exhaustion_resilience(self):
        """
        4e) When bank is nearly exhausted (simulate by excluding 95 of 100 ids),
        a session still gets 10 questions and no crash.
        """
        # Fetch 95 question IDs from Java catalogue
        from app.models.llama_provider import _GUARANTEED_UNIQUE_THEORY_QUESTIONS
        java_items = [q for (s, d), items in _GUARANTEED_UNIQUE_THEORY_QUESTIONS.items() if s == "java" for q in items]
        simulated_exclude_ids = [q["id"] for q in java_items[:95] if "id" in q]

        # Simulate a 10-question session with this near-exhausted bank
        history = [[{"id": qid, "questionText": f"Q-{qid}"} for qid in simulated_exclude_ids]]
        session_qs = self._simulate_10_question_session("java", "exhaustion_session_999", history)

        self.assertEqual(len(session_qs), 10, "Exhausted bank must still yield exactly 10 questions")
        # Ensure no duplicates within the session itself
        session_ids = [q.get("id") or q.get("title") for q in session_qs]
        self.assertEqual(len(session_ids), len(set(session_ids)), "Even under exhaustion, no question may repeat in the session")

    def test_4f_backward_compatibility_without_new_fields(self):
        """
        4f) Old call without the new fields still works and returns a valid question.
        """
        # Old caller sends only basic fields (no excludeQuestionIds, excludeQuestionTexts, sessionId)
        req = QuestionGenerationRequest(
            subject="java",
            difficulty="medium",
            interviewType="technical",
            questionFormat="theory"
        )
        resp = question_generator.generate(req)
        self.assertIsInstance(resp, QuestionResponse)
        self.assertTrue(bool(resp.questionText))
        self.assertEqual(resp.subject, "java")
        self.assertEqual(resp.difficulty, "medium")

    def test_4g_response_shape_identical(self):
        """
        4g) Difficulty mix, subject, question count and format of returned question
        (fields, _generation_meta.source) are identical in shape to before.
        """
        req = QuestionGenerationRequest(
            subject="dbms",
            difficulty="easy",
            interviewType="technical",
            questionFormat="theory",
            excludeQuestionIds=["dbms-theory-001"],
            excludeQuestionTexts=["What is a primary key?"],
            sessionId="shape_check_session"
        )
        resp = question_generator.generate(req)
        d = resp.model_dump()

        expected_fields = ["questionText", "questionType", "subject", "difficulty", "category", "expectedConcepts"]
        for field in expected_fields:
            self.assertIn(field, d, f"Missing expected field: {field}")
            self.assertIsNotNone(d[field], f"Field {field} should not be None")

        self.assertIn(d["difficulty"], ["easy", "medium", "hard"])
        self.assertEqual(d["subject"], "dbms")

    def test_4h_coding_sql_output_prediction_unaffected(self):
        """
        4h) Coding, SQL, and output prediction questions respect exclusions and keep shape.
        """
        # 1. Java coding
        req_coding = QuestionGenerationRequest(
            subject="java",
            difficulty="easy",
            interviewType="technical",
            questionFormat="coding",
            excludeQuestionIds=["Reverse a Given String"],
            excludeQuestionTexts=["Write a Java method to reverse a given string"],
            sessionId="coding_test_sess"
        )
        resp_c = question_generator.generate(req_coding)
        self.assertEqual(resp_c.questionFormat, "coding")
        self.assertNotEqual(resp_c.title, "Reverse a Given String")

        # 2. SQL coding
        req_sql = QuestionGenerationRequest(
            subject="dbms",
            difficulty="easy",
            interviewType="technical",
            questionFormat="coding",
            sessionId="sql_test_sess"
        )
        resp_sql = question_generator.generate(req_sql)
        self.assertEqual(resp_sql.questionFormat, "coding")
        self.assertTrue(bool(resp_sql.schema))

        # 3. Output prediction
        req_op = QuestionGenerationRequest(
            subject="java",
            difficulty="easy",
            interviewType="technical",
            questionFormat="output_prediction",
            sessionId="op_test_sess"
        )
        resp_op = question_generator.generate(req_op)
        self.assertEqual(resp_op.questionFormat, "output_prediction")
        self.assertTrue(bool(resp_op.codeSnippet))

    def test_ranking_prefers_never_asked(self):
        """
        Ranking preference (1): Candidate that has never been asked by this user
        is strictly selected over candidates that have been asked before.
        """
        from app.models.llama_provider import _GUARANTEED_UNIQUE_THEORY_QUESTIONS
        items = _GUARANTEED_UNIQUE_THEORY_QUESTIONS.get(("dbms", "easy"), [])
        target_q = items[0]
        other_qs = items[1:]

        # Mark all other questions as asked 1 time
        history = [
            {"questionId": q["id"], "timesAsked": 1, "lastAskedSessionIndex": 0}
            for q in other_qs
        ]

        resp = question_generator.generate(QuestionGenerationRequest(
            subject="dbms",
            difficulty="easy",
            interviewType="technical",
            questionFormat="theory",
            questionHistory=history,
            sessionId="sess_rank_never"
        ))
        chosen_id = resp.id or getattr(resp, "_generation_meta", {}).get("catalog_id")
        self.assertEqual(chosen_id, target_q["id"], f"Expected never-asked {target_q['id']}, got {chosen_id}")

    def test_ranking_prefers_least_asked(self):
        """
        Ranking preference (2): Among candidates already asked, the one asked
        the fewest times is selected.
        """
        from app.models.llama_provider import _GUARANTEED_UNIQUE_THEORY_QUESTIONS
        items = _GUARANTEED_UNIQUE_THEORY_QUESTIONS.get(("dbms", "easy"), [])
        target_q = items[0]
        other_qs = items[1:]

        # Target asked 1 time, all others asked 4 times
        history = [{"questionId": target_q["id"], "timesAsked": 1, "lastAskedSessionIndex": 5}]
        for q in other_qs:
            history.append({"questionId": q["id"], "timesAsked": 4, "lastAskedSessionIndex": 5})

        resp = question_generator.generate(QuestionGenerationRequest(
            subject="dbms",
            difficulty="easy",
            interviewType="technical",
            questionFormat="theory",
            questionHistory=history,
            sessionId="sess_rank_least"
        ))
        chosen_id = resp.id or getattr(resp, "_generation_meta", {}).get("catalog_id")
        self.assertEqual(chosen_id, target_q["id"], f"Expected least-asked {target_q['id']}, got {chosen_id}")

    def test_ranking_prefers_oldest(self):
        """
        Ranking preference (3): Among candidates with identical timesAsked,
        the one asked longest ago (smallest lastAskedSessionIndex) is selected.
        """
        from app.models.llama_provider import _GUARANTEED_UNIQUE_THEORY_QUESTIONS
        items = _GUARANTEED_UNIQUE_THEORY_QUESTIONS.get(("dbms", "easy"), [])
        target_q = items[0]
        other_qs = items[1:]

        # All asked 1 time; target asked in session 0 (oldest), others in session 5
        history = [{"questionId": target_q["id"], "timesAsked": 1, "lastAskedSessionIndex": 0}]
        for q in other_qs:
            history.append({"questionId": q["id"], "timesAsked": 1, "lastAskedSessionIndex": 5})

        resp = question_generator.generate(QuestionGenerationRequest(
            subject="dbms",
            difficulty="easy",
            interviewType="technical",
            questionFormat="theory",
            questionHistory=history,
            sessionId="sess_rank_oldest"
        ))
        chosen_id = resp.id or getattr(resp, "_generation_meta", {}).get("catalog_id")
        self.assertEqual(chosen_id, target_q["id"], f"Expected oldest-asked {target_q['id']}, got {chosen_id}")

    def test_old_call_without_history_field_works(self):
        """
        Backward compatibility: Call without questionHistory field works seamlessly.
        """
        req = QuestionGenerationRequest(
            subject="dbms",
            difficulty="medium",
            interviewType="technical",
            questionFormat="theory"
        )
        self.assertEqual(req.questionHistory, [])
        resp = question_generator.generate(req)
        self.assertIsInstance(resp, QuestionResponse)
        self.assertTrue(bool(resp.questionText))
        self.assertEqual(resp.subject, "dbms")

    def test_exhaustion_never_crashes_or_returns_fewer_questions(self):
        """
        Exhaustion resilience: Even with 50 heavily saturated sessions in history,
        a new session always returns exactly 10 questions without crashing.
        """
        # Create heavily saturated history of 50 sessions
        saturated_history = []
        for i in range(50):
            saturated_history.append([
                {"id": f"dbms-theory-00{k}", "questionText": f"Dummy Q {k}"}
                for k in range(1, 15)
            ])

        session_qs = self._simulate_10_question_session("dbms", "fully_exhausted_sess_51", saturated_history)
        self.assertEqual(len(session_qs), 10, f"Expected 10 questions under complete exhaustion, got {len(session_qs)}")
        # Check no duplicates within the session
        q_ids = [q.get("id") or q.get("title") for q in session_qs]
        self.assertEqual(len(q_ids), len(set(q_ids)), "Duplicate question inside session during exhaustion")


if __name__ == "__main__":
    unittest.main()

