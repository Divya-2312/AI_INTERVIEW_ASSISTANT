import random
from app.models.schemas import QuestionGenerationRequest, QuestionResponse
from app.models.llama_provider import get_ai_model_provider
from app.services.rag_service import rag_service

class QuestionGenerator:
    def __init__(self):
        self.provider = get_ai_model_provider()

    def generate(self, req: QuestionGenerationRequest) -> QuestionResponse:
        # `rotate` = how many questions already asked this session, so later
        # questions pull different knowledge-base material instead of every
        # question converging on the same top-ranked chunk for a near-static
        # query like "technical medium" -- see retrieve_context's docstring.
        #
        # For question #1 specifically, `previousQuestions` is always empty,
        # so rotate was always 0 -- meaning every fresh interview with the
        # same subject/difficulty retrieved the exact same top RAG chunk and
        # fed LLaMA an essentially identical prompt, which is a big part of
        # why the very first question came back the same so often. A random
        # jitter here means two fresh interviews with identical settings
        # still start from different context.
        # Serve pre-verified questions from background pool first for technical interviews
        excl_ids = getattr(req, "excludeQuestionIds", None) or []
        excl_texts = getattr(req, "excludeQuestionTexts", None) or []
        q_hist = getattr(req, "questionHistory", None) or []
        sess_id = getattr(req, "sessionId", None) or ""

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
            if pooled:
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
        except Exception as e:
            if (req.questionFormat or "theory").lower() == "theory" and (req.interviewType or "").lower() != "hr":
                llama = getattr(self.provider, "llama", None)
                if llama and hasattr(llama, "_get_guaranteed_unique_theory_question"):
                    fallback = llama._get_guaranteed_unique_theory_question(
                        req.subject or "java", req.difficulty, req.previousQuestions or [],
                        getattr(req, "previousCategories", None) or [],
                        exclude_question_ids=excl_ids,
                        exclude_question_texts=excl_texts,
                        question_history=q_hist,
                        session_id=sess_id,
                    )
                    if fallback:
                        return QuestionResponse(**fallback)
            raise e
        return QuestionResponse(**q_data)

question_generator = QuestionGenerator()
