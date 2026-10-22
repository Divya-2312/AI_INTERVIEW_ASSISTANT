import threading
import logging
from typing import Dict, List, Tuple, Optional
from app.models.llama_provider import (
    get_ai_model_provider,
    _is_duplicate_question,
    _GUARANTEED_UNIQUE_CODING_QUESTIONS,
    _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS,
    _GUARANTEED_UNIQUE_THEORY_QUESTIONS,
)

logger = logging.getLogger("ai_service")


class QuestionPool:
    """
    Background pre-generation and pre-verification pool.
    Pre-populates verified questions per (subject, question_format, difficulty)
    so sessions can serve pre-verified questions instantly without waiting for sandbox verification.
    Serves from the pool first, then falls back to the curated bank.
    Enforces session-level rules:
    - At most 2 questions per category/topic.
    - Session topic distribution: in 5-question sessions, at least 4 distinct topics.
    - Question signature deduplication.
    """
    def __init__(self, target_per_bucket: int = 4):
        self.target_per_bucket = target_per_bucket
        self._pool: Dict[Tuple[str, str, str], List[dict]] = {}
        self._lock = threading.Lock()
        self._refilling_keys = set()

    def init_from_catalogues(self):
        """Immediately loads diverse pre-verified catalog questions into the pool on startup."""
        try:
            with self._lock:
                # 1. Java coding
                for diff in ("easy", "medium", "hard"):
                    key = ("java", "coding", diff)
                    self._pool.setdefault(key, [])
                    items = _GUARANTEED_UNIQUE_CODING_QUESTIONS.get(("java", diff), [])
                    seen_cats = set()
                    for q in items:
                        cat = (q.get("category") or "").lower()
                        if cat not in seen_cats and not any(x.get("title") == q.get("title") for x in self._pool[key]):
                            seen_cats.add(cat)
                            item = dict(q)
                            item["modelUsed"] = "verified_adaptive_catalog"
                            self._pool[key].append(item)
                            if len(self._pool[key]) >= self.target_per_bucket:
                                break

                # 2. DBMS coding (SQL)
                for diff in ("easy", "medium", "hard"):
                    key = ("dbms", "coding", diff)
                    self._pool.setdefault(key, [])
                    items = _GUARANTEED_UNIQUE_CODING_QUESTIONS.get(("dbms", diff), [])
                    seen_cats = set()
                    for q in items:
                        cat = (q.get("category") or "").lower()
                        if cat not in seen_cats and not any(x.get("title") == q.get("title") for x in self._pool[key]):
                            seen_cats.add(cat)
                            item = dict(q)
                            item["modelUsed"] = "verified_adaptive_catalog"
                            self._pool[key].append(item)
                            if len(self._pool[key]) >= self.target_per_bucket:
                                break

                # 3. Java output_prediction
                for diff in ("easy", "medium", "hard"):
                    key = ("java", "output_prediction", diff)
                    self._pool.setdefault(key, [])
                    items = _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS.get(("java", diff), [])
                    seen_cats = set()
                    for q in items:
                        cat = (q.get("category") or "").lower()
                        if cat not in seen_cats and not any(x.get("codeSnippet") == q.get("codeSnippet") for x in self._pool[key]):
                            seen_cats.add(cat)
                            item = dict(q)
                            item["modelUsed"] = "verified_adaptive_catalog"
                            self._pool[key].append(item)
                            if len(self._pool[key]) >= self.target_per_bucket:
                                break

                # 4. Java & DBMS theory
                for subj in ("java", "dbms"):
                    for diff in ("easy", "medium", "hard"):
                        key = (subj, "theory", diff)
                        self._pool.setdefault(key, [])
                        items = _GUARANTEED_UNIQUE_THEORY_QUESTIONS.get((subj, diff), [])
                        seen_cats = set()
                        for q in items:
                            cat = (q.get("category") or "").lower()
                            if cat not in seen_cats and not any(x.get("questionText") == q.get("questionText") for x in self._pool[key]):
                                seen_cats.add(cat)
                                item = dict(q)
                                item["modelUsed"] = "verified_adaptive_catalog"
                                self._pool[key].append(item)
                                if len(self._pool[key]) >= self.target_per_bucket:
                                    break
            logger.info("[QuestionPool] Pre-verified question pool successfully initialized.")
        except Exception as e:
            logger.warning(f"[QuestionPool] init_from_catalogues encountered error: {e}")

    def pop_question(self, subject: str, question_format: str, difficulty: str,
                     previous_questions: List[str] = None,
                     previous_categories: List[str] = None) -> Optional[dict]:
        """
        Pops a pre-verified question matching (subject, format, difficulty).
        First checks pool; if empty, falls back to the bank.
        Enforces session rules:
        - At most 2 questions per category/topic.
        - In a 5-question session, at least 4 distinct topics.
        - Deduplication by question signature.
        """
        s = (subject or "java").lower()
        f = (question_format or "theory").lower()
        d = (difficulty or "medium").lower()
        key = (s, f, d)

        prev_q = previous_questions or []
        prev_cats = [c.lower() for c in (previous_categories or []) if c]

        has_pair = any(prev_cats.count(c) >= 2 for c in set(prev_cats))
        distinct_cats = len(set(prev_cats))
        must_choose_new_cat = has_pair or (len(prev_cats) >= 3 and distinct_cats < 3) or (len(prev_cats) == 4 and distinct_cats < 4)

        chosen = None
        with self._lock:
            bucket = self._pool.get(key, [])
            candidates = []
            for i, q in enumerate(bucket):
                sig = q.get("codeSnippet") if f == "output_prediction" else (
                    f"{q.get('title')}: {q.get('questionText')}" if f == "coding" else q.get("questionText")
                )
                if _is_duplicate_question(sig, prev_q):
                    continue

                cat = (q.get("category") or "").lower()
                # Rule: At most 2 per topic
                if cat and prev_cats.count(cat) >= 2:
                    continue

                if must_choose_new_cat and cat and cat in prev_cats:
                    continue

                candidates.append((i, q))

            if candidates:
                chosen_idx = candidates[0][0]
                chosen = bucket.pop(chosen_idx)
                chosen["_served_from_pool"] = True

        # Trigger background refill if bucket is below target
        self._trigger_refill(s, f, d)

        if chosen:
            return chosen

        # Fall back to curated bank
        return self._fallback_to_bank(s, f, d, prev_q, prev_cats)

    def _fallback_to_bank(self, subject: str, question_format: str, difficulty: str,
                          previous_questions: List[str], previous_categories: List[str]) -> Optional[dict]:
        """Falls back to curated guaranteed-unique catalogues when pool is exhausted."""
        try:
            provider = get_ai_model_provider()
            llama = getattr(provider, "llama", None) or provider
            if question_format == "coding":
                return llama._get_guaranteed_unique_coding_question(subject, difficulty, previous_questions, previous_categories)
            elif question_format == "output_prediction":
                return llama._get_guaranteed_unique_output_prediction(subject, difficulty, previous_questions, previous_categories)
            else:
                return llama._get_guaranteed_unique_theory_question(subject, difficulty, previous_questions, previous_categories)
        except Exception as e:
            logger.warning(f"[QuestionPool] Bank fallback error: {e}")
            return None

    def _trigger_refill(self, subject: str, question_format: str, difficulty: str):
        """Asynchronously refills the bucket in the background without blocking."""
        key = (subject, question_format, difficulty)
        with self._lock:
            if key in self._refilling_keys or len(self._pool.get(key, [])) >= self.target_per_bucket:
                return
            self._refilling_keys.add(key)

        def worker():
            try:
                self._refill_bucket(subject, question_format, difficulty)
            finally:
                with self._lock:
                    self._refilling_keys.discard(key)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _refill_bucket(self, subject: str, question_format: str, difficulty: str):
        """Background refill worker: pre-verifies questions and adds them to the pool."""
        key = (subject, question_format, difficulty)

        with self._lock:
            current_sigs = [
                q.get("codeSnippet") if question_format == "output_prediction" else (
                    f"{q.get('title')}: {q.get('questionText')}" if question_format == "coding" else q.get("questionText")
                )
                for q in self._pool.get(key, [])
            ]

        # Draw verified questions from catalog
        if question_format == "coding":
            items = _GUARANTEED_UNIQUE_CODING_QUESTIONS.get((subject, difficulty), [])
        elif question_format == "output_prediction":
            items = _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS.get((subject, difficulty), [])
        else:
            items = _GUARANTEED_UNIQUE_THEORY_QUESTIONS.get((subject, difficulty), [])

        for item in items:
            sig = item.get("codeSnippet") if question_format == "output_prediction" else (
                f"{item.get('title')}: {item.get('questionText')}" if question_format == "coding" else item.get("questionText")
            )
            with self._lock:
                if len(self._pool[key]) >= self.target_per_bucket:
                    break
                if not _is_duplicate_question(sig, current_sigs):
                    entry = dict(item)
                    entry["modelUsed"] = "verified_adaptive_catalog"
                    self._pool[key].append(entry)
                    current_sigs.append(sig)

    def add_verified_question(self, subject: str, question_format: str, difficulty: str, question: dict):
        s = (subject or "java").lower()
        f = (question_format or "theory").lower()
        d = (difficulty or "medium").lower()
        key = (s, f, d)
        with self._lock:
            self._pool.setdefault(key, [])
            if len(self._pool[key]) < 10:
                self._pool[key].append(dict(question))


question_pool = QuestionPool()
question_pool.init_from_catalogues()
