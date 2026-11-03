import random
import hashlib
import logging
import concurrent.futures
import threading
from app.models.schemas import QuestionGenerationRequest, QuestionResponse
from app.models.llama_provider import get_ai_model_provider, _question_level_problem
from app.services.rag_service import rag_service

logger = logging.getLogger("ai_service")

# Background prefetch cache: sessionId -> Future or dict
_session_prefetches = {}
_prefetch_lock = threading.Lock()
_prefetch_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="prefetch_worker")


class QuestionGenerator:
    def __init__(self):
        self.provider = get_ai_model_provider()

    @staticmethod
    def _normalize_model_question(req: QuestionGenerationRequest, question: dict) -> dict:
        question = dict(question)
        question_text = question.get("questionText") or question.get("question") or ""

        if (
            (req.interviewType or "").lower() == "technical"
            and (req.questionFormat or "theory").lower() == "theory"
            and (req.subject or "").lower() == "java"
            and (req.difficulty or "").lower() == "easy"
        ):
            level_text = " ".join(
                [question_text, question.get("category") or ""]
                + [str(concept) for concept in (question.get("expectedConcepts") or [])]
            )
            problem = _question_level_problem(level_text, "easy", check_length=False)
            if problem:
                raise ValueError(f"Java easy theory question rejected: {problem}")

        if (
            (req.interviewType or "").lower() == "technical"
            and (req.questionFormat or "theory").lower() == "theory"
            and question.get("source") == "model"
            and question_text.strip()
        ):
            normalized = " ".join(question_text.strip().lower().split())
            question_id = "theory-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            question["id"] = question_id
            question["questionId"] = question_id

        return question

    def generate(self, req: QuestionGenerationRequest) -> QuestionResponse:
        excl_ids = getattr(req, "excludeQuestionIds", None) or []
        excl_texts = getattr(req, "excludeQuestionTexts", None) or []
        q_hist = getattr(req, "questionHistory", None) or []
        sess_id = getattr(req, "sessionId", None) or ""

        # FIX 2: Prefetch check: while the student was answering question N,
        # question N+1 was generated in the background with the base Llama.
        # Serve the prefetched question immediately when it is ready.
        if sess_id:
            with _prefetch_lock:
                fut = _session_prefetches.pop(sess_id, None)
            if fut is not None:
                try:
                    prefetched = fut if isinstance(fut, dict) else (fut.result() if fut.done() and not fut.cancelled() else None)
                    if prefetched:
                        prefetched = self._normalize_model_question(req, prefetched)
                        cand_text = prefetched.get("questionText") or prefetched.get("question") or ""
                        cand_id = prefetched.get("id") or prefetched.get("questionId") or ""
                        cand_sig = prefetched.get("codeSnippet") if req.questionFormat == "output_prediction" else (
                            f"{prefetched.get('title')}: {cand_text}" if req.questionFormat == "coding" else cand_text
                        )
                        is_dup = any(cand_text.lower() == (p or "").lower() for p in (req.previousQuestions or []))
                        is_excl_id = cand_id and str(cand_id).lower() in [str(x).lower() for x in excl_ids]

                        from app.services.embedding_service import embedding_service
                        is_sim = False
                        if excl_texts and cand_sig:
                            is_sim, _, _ = embedding_service.is_similar_to_any(cand_sig, excl_texts, threshold=0.88)

                        if not is_dup and not is_excl_id and not is_sim:
                            logger.info(f"[Prefetch] Serving ready prefetched question for session '{sess_id}' immediately.")
                            self._schedule_prefetch(req, prefetched)
                            return QuestionResponse(**prefetched)
                except Exception as e:
                    logger.warning(f"[Prefetch] Error checking prefetched question for session '{sess_id}': {e}")

        # Ready pool (only if filled by base LLaMA with source: 'model')
        if (req.interviewType or "").lower() != "hr":
            from app.services.question_pool import question_pool
            pooled = question_pool.pop_question(
                subject=req.subject or "java",
                question_format=req.questionFormat or "theory",
                difficulty=req.difficulty or "medium",
                previous_questions=req.previousQuestions or [],
                previous_categories=getattr(req, "previousCategories", None) or [],
                exclude_question_ids=excl_ids,
                exclude_question_texts=excl_texts,
                question_history=q_hist,
                session_id=sess_id,
            )
            if pooled and pooled.get("source") == "model":
                try:
                    pooled = self._normalize_model_question(req, pooled)
                except ValueError as error:
                    logger.warning("[QuestionPool] Discarding invalid pooled question: %s", error)
                else:
                    self._schedule_prefetch(req, pooled)
                    return QuestionResponse(**pooled)

        rotate = len(req.previousQuestions or []) + random.randint(0, 4)
        context = rag_service.retrieve_context(
            "hr" if req.interviewType.lower() == "hr" else req.subject or "general",
            f"{req.interviewType} {req.difficulty}",
            top_k=2,
            rotate=rotate,
        )

        try:
            q_data = self.provider.generate_question(
                req.subject or "java", req.difficulty, context, req.previousQuestions,
                question_format=req.questionFormat or "theory",
                interview_type=req.interviewType,
                previous_categories=getattr(req, "previousCategories", None) or [],
                exclude_question_ids=excl_ids,
                exclude_question_texts=excl_texts,
                question_history=q_hist,
                session_id=sess_id,
            )
            if (req.interviewType or "").lower() == "hr":
                q_data.setdefault("source", "bank")
                q_data.setdefault("modelUsed", "curated_hr100_benchmark")
            else:
                if q_data.get("source") == "catalogue_fallback":
                    q_data["modelUsed"] = "catalogue_fallback"
                else:
                    q_data.setdefault("source", "model")
                    q_data.setdefault("modelUsed", "llama3.2:3b")

            q_data = self._normalize_model_question(req, q_data)
            self._schedule_prefetch(req, q_data)
            return QuestionResponse(**q_data)
        except Exception as e:
            # Catalogue fallback is the LAST resort only, after model attempts fail
            if (req.interviewType or "").lower() != "hr":
                llama = getattr(self.provider, "llama", None) or self.provider
                q_format = (req.questionFormat or "theory").lower()
                fallback = None
                if q_format == "coding" and hasattr(llama, "_get_guaranteed_unique_coding_question"):
                    fallback = llama._get_guaranteed_unique_coding_question(
                        req.subject or "java", req.difficulty, req.previousQuestions or [],
                        getattr(req, "previousCategories", None) or [],
                        exclude_question_ids=excl_ids,
                        exclude_question_texts=excl_texts,
                        question_history=q_hist,
                        session_id=sess_id,
                    )
                elif q_format == "output_prediction" and hasattr(llama, "_get_guaranteed_unique_output_prediction"):
                    fallback = llama._get_guaranteed_unique_output_prediction(
                        req.subject or "java", req.difficulty, req.previousQuestions or [],
                        getattr(req, "previousCategories", None) or [],
                        exclude_question_ids=excl_ids,
                        exclude_question_texts=excl_texts,
                        question_history=q_hist,
                        session_id=sess_id,
                    )
                elif hasattr(llama, "_get_guaranteed_unique_theory_question"):
                    fallback = llama._get_guaranteed_unique_theory_question(
                        req.subject or "java", req.difficulty, req.previousQuestions or [],
                        getattr(req, "previousCategories", None) or [],
                        exclude_question_ids=excl_ids,
                        exclude_question_texts=excl_texts,
                        question_history=q_hist,
                        session_id=sess_id,
                    )
                if fallback:
                    fallback["source"] = "catalogue_fallback"
                    fallback["modelUsed"] = "catalogue_fallback"
                    self._schedule_prefetch(req, fallback)
                    return QuestionResponse(**fallback)
            raise e

    def _schedule_prefetch(self, req: QuestionGenerationRequest, current_q: dict):
        """Generates question N+1 in the background with the base Llama while candidate answers N."""
        sess_id = getattr(req, "sessionId", None) or ""
        if not sess_id or (req.interviewType or "").lower() == "hr":
            return

        cur_text = current_q.get("questionText") or current_q.get("question") or ""
        cur_id = current_q.get("id") or current_q.get("questionId") or ""
        cur_sig = current_q.get("codeSnippet") if req.questionFormat == "output_prediction" else (
            f"{current_q.get('title')}: {cur_text}" if req.questionFormat == "coding" else cur_text
        )

        next_prev = list(req.previousQuestions or [])
        if cur_text and cur_text not in next_prev:
            next_prev.append(cur_text)

        next_excl_ids = list(getattr(req, "excludeQuestionIds", None) or [])
        if cur_id and cur_id not in next_excl_ids:
            next_excl_ids.append(cur_id)

        next_excl_texts = list(getattr(req, "excludeQuestionTexts", None) or [])
        if cur_sig and cur_sig not in next_excl_texts:
            next_excl_texts.append(cur_sig)

        q_hist = list(getattr(req, "questionHistory", None) or [])

        def do_prefetch():
            try:
                rotate = len(next_prev) + random.randint(0, 4)
                context = rag_service.retrieve_context(
                    req.subject or "general",
                    f"{req.interviewType} {req.difficulty}",
                    top_k=2,
                    rotate=rotate,
                )
                pq = self.provider.generate_question(
                    req.subject or "java", req.difficulty, context, next_prev,
                    question_format=req.questionFormat or "theory",
                    interview_type=req.interviewType,
                    previous_categories=getattr(req, "previousCategories", None) or [],
                    exclude_question_ids=next_excl_ids,
                    exclude_question_texts=next_excl_texts,
                    question_history=q_hist,
                    session_id=sess_id,
                )
                if pq.get("source") == "catalogue_fallback":
                    pq["modelUsed"] = "catalogue_fallback"
                else:
                    pq.setdefault("source", "model")
                    pq.setdefault("modelUsed", "llama3.2:3b")
                return pq
            except Exception as e:
                logger.warning(f"[Prefetch] Background prefetch generation failed for session '{sess_id}': {e}")
                return None

        fut = _prefetch_executor.submit(do_prefetch)
        with _prefetch_lock:
            _session_prefetches[sess_id] = fut


question_generator = QuestionGenerator()
