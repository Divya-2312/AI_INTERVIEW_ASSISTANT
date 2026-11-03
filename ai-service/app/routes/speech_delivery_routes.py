import io
import logging
import os
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.services.speech_delivery_analyzer import (
    _patch_av_open_once,
    analyze_delivery,
    compute_acoustic_features,
    transcribe_verbatim,
)

logger = logging.getLogger("speech_delivery_routes")

router = APIRouter(prefix="/api/ai", tags=["Speech Delivery"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/speech-delivery")
def speech_delivery(file: UploadFile = File(...)):
    """Analyze speech delivery metrics from an audio recording.

    Synchronous def route runs in FastAPI threadpool so it does NOT block the async event loop.
    Decodes audio in-memory once to a 16 kHz float32 array, avoiding redundant disk I/O.
    """
    enabled_str = os.getenv("SPEECH_DELIVERY_ENABLED", "true").strip().lower()
    if enabled_str in ("false", "0", "no", "off"):
        return JSONResponse(status_code=200, content={"error": "disabled"})

    try:
        content = file.file.read()
        if len(content) > MAX_FILE_SIZE:
            return JSONResponse(status_code=400, content={"error": "File size exceeds 10 MB limit"})
        if len(content) == 0:
            return JSONResponse(status_code=400, content={"error": "Uploaded file is empty"})

        _patch_av_open_once()
        from faster_whisper.audio import decode_audio
        bio = io.BytesIO(content)
        audio_np = decode_audio(bio, sampling_rate=16000)

        if audio_np is None or len(audio_np) == 0:
            return JSONResponse(status_code=200, content={"error": "Audio decoding produced empty signal"})

        # 1. Transcribe verbatim with greedy decoding
        transcription_result = transcribe_verbatim(audio_np)
        if transcription_result.get("error"):
            logger.warning(f"[speech_delivery_routes] Transcription error: {transcription_result['error']}")
            return JSONResponse(status_code=200, content={"error": transcription_result["error"]})

        words = transcription_result.get("words", [])
        text = transcription_result.get("text", "")
        model_name = transcription_result.get("model", "small.en")
        duration = transcription_result.get("duration", float(len(audio_np)) / 16000.0)

        # 2. Vectorized acoustic features
        frames, dur = compute_acoustic_features(audio_np)

        # 3. Analyze delivery metrics
        analysis = analyze_delivery(
            words,
            text,
            audio_path=audio_np,
            model=model_name,
            duration=duration,
            acoustic_frames=frames,
        )
        return JSONResponse(status_code=200, content=analysis)

    except Exception as e:
        logger.error(f"[speech_delivery_routes] Unexpected failure: {e}", exc_info=True)
        return JSONResponse(status_code=200, content={"error": str(e)})
