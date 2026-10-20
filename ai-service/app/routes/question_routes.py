from fastapi import APIRouter, HTTPException, UploadFile, File
import tempfile
import os
from app.models.schemas import (
    QuestionGenerationRequest,
    FollowUpRequest,
    QuestionResponse,
    AnswerEvaluationRequest,
    EvaluationResponse
)
from app.models.llama_provider import AIGenerationUnavailableError
from app.services.question_generator import question_generator
from app.services.followup_generator import followup_generator
from app.services.speech_service import speech_to_text
from app.services.speech_analyzer import analyze_speech
from app.services.answer_evaluator import answer_evaluator

router = APIRouter(prefix="/api/ai", tags=["Question Engine"])


@router.post("/generate-question", response_model=QuestionResponse)
def generate_question(req: QuestionGenerationRequest):
    try:
        return question_generator.generate(req)
    except AIGenerationUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/generate-followup", response_model=QuestionResponse)
def generate_followup(req: FollowUpRequest):
    try:
        return followup_generator.generate(req)
    except AIGenerationUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/evaluate-answer", response_model=EvaluationResponse)
def evaluate_answer(req: AnswerEvaluationRequest):
    try:
        return answer_evaluator.evaluate(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/speech-to-text", tags=["Speech"])
async def speech_to_text_api(file: UploadFile = File(...)):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")

    try:
        temp.write(await file.read())
        temp.close()

        speech = speech_to_text(temp.name)

        # English only: a non-English recording is rejected, never evaluated.
        if speech.get("error"):
            return {
                "text": "",
                "segments": [],
                "analysis": None,
                "error": speech["error"],
                "message": speech["error"],
            }

        analysis = analyze_speech(speech["text"], speech["segments"])

        return {
            "text": speech["text"],
            "segments": speech["segments"],
            "analysis": analysis
        }
    

    finally:
        if os.path.exists(temp.name):
            os.unlink(temp.name)