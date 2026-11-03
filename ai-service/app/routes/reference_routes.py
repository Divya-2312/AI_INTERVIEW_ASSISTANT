from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Any
from app.services.reference_answer_service import reference_answer_service

router = APIRouter(prefix="/api/ai", tags=["Reference Answer"])


class ReferenceAnswerRequest(BaseModel):
    question: str
    subject: Optional[str] = "N/A"
    interviewType: Optional[str] = "technical"
    questionFormat: Optional[str] = "theory"
    difficulty: Optional[str] = "medium"
    expectedConcepts: Optional[Any] = None
    guidance: Optional[str] = None
    referenceSolution: Optional[str] = None
    referenceAnswer: Optional[str] = None


class ReferenceAnswerResponse(BaseModel):
    status: str
    referenceAnswer: Optional[str] = None


@router.post("/reference-answer", response_model=ReferenceAnswerResponse)
def get_reference_answer(req: ReferenceAnswerRequest):
    guidance = req.guidance or req.referenceSolution or req.referenceAnswer or ""
    res = reference_answer_service.get_reference_answer(
        question=req.question,
        subject=req.subject or "N/A",
        interview_type=req.interviewType or "technical",
        difficulty=req.difficulty or "medium",
        expected_concepts=req.expectedConcepts,
        guidance=guidance,
        wait_timeout=40.0,
    )
    return ReferenceAnswerResponse(
        status=res.get("status", "failed"),
        referenceAnswer=res.get("referenceAnswer"),
    )
