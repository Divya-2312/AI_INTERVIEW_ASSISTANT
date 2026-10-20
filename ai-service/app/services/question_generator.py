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
        rotate = len(req.previousQuestions or []) + random.randint(0, 4)
        context = rag_service.retrieve_context(
            "hr" if req.interviewType.lower() == "hr" else req.subject or "general",
            f"{req.interviewType} {req.difficulty}",
            top_k=2,
            rotate=rotate,
        )
        q_data = self.provider.generate_question(
            req.subject or "java", req.difficulty, context, req.previousQuestions,
            question_format=req.questionFormat or "theory",
            interview_type=req.interviewType,
        )
        return QuestionResponse(**q_data)

question_generator = QuestionGenerator()
