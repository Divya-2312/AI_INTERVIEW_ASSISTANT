from collections import defaultdict
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

from app.services.embedding_service import embedding_service

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
        self._pool: Dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
        self._lock = threading.Lock()
        self._refilling_keys = set()

    def init_from_catalogues(self):
        """Immediately loads diverse pre-verified catalog questions into the pool on startup."""
        try:
            import random
            with self._lock:
                # 1. Java coding
                for diff in ("easy", "medium", "hard"):
                    key = ("java", "coding", diff)
                    self._pool.setdefault(key, [])
                    items = list(_GUARANTEED_UNIQUE_CODING_QUESTIONS.get(("java", diff), []))
                    random.shuffle(items)
                    seen_cats = set()
                    for q in items:
                        cat = (q.get("category") or "").lower()
                        if cat not in seen_cats and not any(x.get("title") == q.get("title") for x in self._pool[key]):
                            seen_cats.add(cat)
                            item = dict(q)
                            item["source"] = "catalogue_fallback"
                            item["modelUsed"] = "catalogue_fallback"
                            self._pool[key].append(item)
                            if len(self._pool[key]) >= self.target_per_bucket:
                                break

                # 2. DBMS coding (SQL)
                for diff in ("easy", "medium", "hard"):
                    key = ("dbms", "coding", diff)
                    self._pool.setdefault(key, [])
                    items = list(_GUARANTEED_UNIQUE_CODING_QUESTIONS.get(("dbms", diff), []))
                    random.shuffle(items)
                    seen_cats = set()
                    for q in items:
                        cat = (q.get("category") or "").lower()
                        if cat not in seen_cats and not any(x.get("title") == q.get("title") for x in self._pool[key]):
                            seen_cats.add(cat)
                            item = dict(q)
                            item["source"] = "catalogue_fallback"
                            item["modelUsed"] = "catalogue_fallback"
                            self._pool[key].append(item)
                            if len(self._pool[key]) >= self.target_per_bucket:
                                break

                # 3. Java output_prediction
                for diff in ("easy", "medium", "hard"):
                    key = ("java", "output_prediction", diff)
                    self._pool.setdefault(key, [])
                    items = list(_GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS.get(("java", diff), []))
                    random.shuffle(items)
                    seen_cats = set()
                    for q in items:
                        cat = (q.get("category") or "").lower()
                        if cat not in seen_cats and not any(x.get("codeSnippet") == q.get("codeSnippet") for x in self._pool[key]):
                            seen_cats.add(cat)
                            item = dict(q)
                            item["source"] = "catalogue_fallback"
                            item["modelUsed"] = "catalogue_fallback"
                            self._pool[key].append(item)
                            if len(self._pool[key]) >= self.target_per_bucket:
                                break

                # 4. Java & DBMS theory
                for subj in ("java", "dbms"):
                    for diff in ("easy", "medium", "hard"):
                        key = (subj, "theory", diff)
                        self._pool.setdefault(key, [])
                        items = list(_GUARANTEED_UNIQUE_THEORY_QUESTIONS.get((subj, diff), []))
                        random.shuffle(items)
                        seen_cats = set()
                        for q in items:
                            cat = (q.get("category") or "").lower()
                            if cat not in seen_cats and not any(x.get("questionText") == q.get("questionText") for x in self._pool[key]):
                                seen_cats.add(cat)
                                item = dict(q)
                                item["source"] = "catalogue_fallback"
                                item["modelUsed"] = "catalogue_fallback"
                                self._pool[key].append(item)
                                if len(self._pool[key]) >= self.target_per_bucket:
                                    break
            logger.info("[QuestionPool] Pre-verified question pool successfully initialized.")
        except Exception as e:
            logger.warning(f"[QuestionPool] init_from_catalogues encountered error: {e}")

    def pop_question(self, subject: str, question_format: str, difficulty: str,
                     previous_questions: List[str] = None,
                     previous_categories: List[str] = None,
                     exclude_question_ids: List[str] = None,
                     exclude_question_texts: List[str] = None,
                     question_history: List[dict] = None,
                     session_id: str = None) -> Optional[dict]:
        """
        Pops a pre-verified question matching (subject, format, difficulty).
        First checks pool; if empty or if pool contains only repeats while catalogue has never-asked items, falls back to the bank.
        Enforces session rules:
        - At most 2 questions per category/topic.
        - In a 5-question session, at least 4 distinct topics.
        - Deduplication by question signature.
        - Excludes questions by Sentence-BERT cosine similarity >= 0.88 to exclude_question_texts (last 5 sessions).
        - Ranks candidates by: (1) never asked, (2) asked fewest times, (3) asked longest ago; seeded random tie-break.
        """
        import random
        from app.services.embedding_service import embedding_service

        s = (subject or "java").lower()
        f = (question_format or "theory").lower()
        d = (difficulty or "medium").lower()
        key = (s, f, d)

        prev_q = previous_questions or []
        prev_cats = [c.lower() for c in (previous_categories or []) if c]
        exclude_ids_set = {str(x).strip().lower() for x in (exclude_question_ids or []) if x}
        exclude_texts = [str(x).strip() for x in (exclude_question_texts or []) if x]

        has_pair = any(prev_cats.count(c) >= 2 for c in set(prev_cats))
        distinct_cats = len(set(prev_cats))
        must_choose_new_cat = has_pair or (len(prev_cats) >= 3 and distinct_cats < 3) or (len(prev_cats) == 4 and distinct_cats < 4)

        hist_by_id = {}
        hist_by_text = {}
        if question_history:
            for h in question_history:
                qid = str(h.get("questionId") or "").strip().lower()
                if qid:
                    hist_by_id[qid] = h
                txt = str(h.get("text") or "").strip().lower()
                if txt:
                    hist_by_text[txt] = h

        def _get_rank_key(q_dict):
            qid = str(q_dict.get("id") or q_dict.get("title") or "").strip().lower()
            qtext = str(q_dict.get("questionText") or q_dict.get("codeSnippet") or "").strip().lower()
            h = hist_by_id.get(qid) or hist_by_text.get(qtext)
            if h:
                times_asked = int(h.get("timesAsked", 1))
                last_idx = int(h.get("lastAskedSessionIndex", 0))
            elif not question_history and exclude_ids_set and qid in exclude_ids_set:
                times_asked = 1
                last_idx = 999999
            else:
                times_asked = 0
                last_idx = -1

            seed_str = f"{session_id}:{len(prev_q)}:{qid}:{qtext[:20]}"
            tie_break = random.Random(seed_str).random()
            return (times_asked, last_idx, tie_break)

        chosen = None
        with self._lock:
            bucket = self._pool.get(key, [])
            candidates = []
            for i, q in enumerate(bucket):
                # 1. Old client ID exclusion if question_history not provided
                q_id = str(q.get("id") or q.get("title") or "").strip().lower()
                if not question_history and q_id and q_id in exclude_ids_set:
                    continue

                # 2. Current session duplicate check (never repeat within current session)
                sig = q.get("codeSnippet") if f == "output_prediction" else (
                    f"{q.get('title')}: {q.get('questionText')}" if f == "coding" else q.get("questionText")
                )
                if _is_duplicate_question(sig, prev_q):
                    continue

                # 3. Cross-session semantic similarity check (>= 0.88 against last 5 sessions)
                text_to_check = q.get("questionText") or sig
                if exclude_texts:
                    is_sim, _, _ = embedding_service.is_similar_to_any(text_to_check, exclude_texts, threshold=0.88)
                    if is_sim:
                        continue

                # 4. Category / topic constraints
                cat = (q.get("category") or "").lower()
                if cat and prev_cats.count(cat) >= 2:
                    continue

                if must_choose_new_cat and cat and cat in prev_cats:
                    continue

                candidates.append((i, q))

            if candidates:
                # Rank candidates by: (1) never asked, (2) fewest times, (3) oldest session
                candidates.sort(key=lambda item: _get_rank_key(item[1]))
                best_rank = _get_rank_key(candidates[0][1])
                if best_rank[0] == 0:
                    best_pair = candidates[0]
                    chosen = bucket.pop(best_pair[0])
                    chosen["_served_from_pool"] = True

        # Trigger background refill if bucket is below target
        self._trigger_refill(s, f, d)

        if chosen:
            return chosen

        return self._fallback_to_bank(
            subject, question_format, difficulty,
            previous_questions, previous_categories,
            exclude_question_ids=exclude_question_ids,
            exclude_question_texts=exclude_question_texts,
            question_history=question_history,
            session_id=session_id
        )

    def _fallback_to_bank(self, subject: str, question_format: str, difficulty: str,
                          previous_questions: List[str], previous_categories: List[str],
                          exclude_question_ids: List[str] = None,
                          exclude_question_texts: List[str] = None,
                          question_history: List[dict] = None,
                          session_id: str = None) -> Optional[dict]:
        """Falls back to curated guaranteed-unique catalogues when pool is exhausted."""
        try:
            provider = get_ai_model_provider()
            llama = getattr(provider, "llama", None) or provider
            res = None
            if question_format == "coding":
                res = llama._get_guaranteed_unique_coding_question(
                    subject, difficulty, previous_questions, previous_categories,
                    exclude_question_ids=exclude_question_ids,
                    exclude_question_texts=exclude_question_texts,
                    question_history=question_history,
                    session_id=session_id
                )
            elif question_format == "output_prediction":
                res = llama._get_guaranteed_unique_output_prediction(
                    subject, difficulty, previous_questions, previous_categories,
                    exclude_question_ids=exclude_question_ids,
                    exclude_question_texts=exclude_question_texts,
                    question_history=question_history,
                    session_id=session_id
                )
            else:
                res = llama._get_guaranteed_unique_theory_question(
                    subject, difficulty, previous_questions, previous_categories,
                    exclude_question_ids=exclude_question_ids,
                    exclude_question_texts=exclude_question_texts,
                    question_history=question_history,
                    session_id=session_id
                )
            if res:
                res["source"] = "catalogue_fallback"
                res["modelUsed"] = "catalogue_fallback"
            return res
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
        import random
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

        shuffled_items = list(items)
        random.shuffle(shuffled_items)

        for item in shuffled_items:
            sig = item.get("codeSnippet") if question_format == "output_prediction" else (
                f"{item.get('title')}: {item.get('questionText')}" if question_format == "coding" else item.get("questionText")
            )
            with self._lock:
                if len(self._pool[key]) >= self.target_per_bucket:
                    break
                if not _is_duplicate_question(sig, current_sigs):
                    entry = dict(item)
                    entry["source"] = "catalogue_fallback"
                    entry["modelUsed"] = "catalogue_fallback"
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
