from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models.schemas import AnswerEvaluationRequest, EvaluationResponse
from app.services.answer_evaluator import answer_evaluator

router = APIRouter(prefix="/api/ai", tags=["Evaluation Engine"])

@router.post("/evaluate-answer", response_model=EvaluationResponse)
def evaluate_answer(req: AnswerEvaluationRequest):
    result = answer_evaluator.evaluate(req)
    if result.source == "error":
        return JSONResponse(content=result.model_dump(exclude_none=True))
    return result
