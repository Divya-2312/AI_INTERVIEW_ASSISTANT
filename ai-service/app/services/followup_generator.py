from app.models.schemas import FollowUpRequest, QuestionResponse
from app.models.llama_provider import get_ai_model_provider

class FollowUpGenerator:
    def __init__(self):
        self.provider = get_ai_model_provider()

    def generate(self, req: FollowUpRequest) -> QuestionResponse:
        q_data = self.provider.generate_followup(
            req.previousQuestion,
            req.studentAnswer,
            req.expectedConcepts or [],
            previous=req.previousQuestions or [],
            interview_type=req.interviewType,
        )
        return QuestionResponse(**q_data)

followup_generator = FollowUpGenerator()
