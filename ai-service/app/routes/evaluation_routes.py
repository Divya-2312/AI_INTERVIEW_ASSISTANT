from fastapi import APIRouter
from app.models.schemas import AnswerEvaluationRequest, EvaluationResponse
from app.services.answer_evaluator import answer_evaluator

router = APIRouter(prefix="/api/ai", tags=["Evaluation Engine"])

@router.post("/evaluate-answer", response_model=EvaluationResponse)
def evaluate_answer(req: AnswerEvaluationRequest):
    return answer_evaluator.evaluate(req)
