import hashlib
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
            subject=req.subject,
            previous_score=req.previousScore,
        )
        question_text = (q_data.get("questionText") or "").strip()
        if question_text:
            normalized = " ".join(question_text.lower().split())
            question_id = "followup-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            q_data["id"] = question_id
            q_data["questionId"] = question_id
        return QuestionResponse(**q_data)

followup_generator = FollowUpGenerator()
