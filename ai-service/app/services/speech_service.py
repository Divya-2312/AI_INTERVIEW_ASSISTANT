try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

_model = None


def _get_model():
    global _model
    if _model is None and WhisperModel is not None:
        _model = WhisperModel("base", device="cpu")
    return _model

# Speech answers are English-only. Anything else is rejected with this exact message
# instead of being force-decoded into English-looking text and graded.
NOT_ENGLISH_MESSAGE = "Couldn't understand the language."

# Whisper reports how sure it is of the detected language. Only reject when it is
# clearly something other than English: short or accented English is sometimes
# detected as another language with a LOW probability, and must not be rejected.
NON_ENGLISH_CONFIDENCE = 0.75


def speech_to_text(audio_path):
    model = _get_model()
    if model is None:
        return {
            "text": "",
            "segments": [],
            "duration_seconds": 0.0,
            "error": "Speech transcription model (faster-whisper) is not available.",
        }
    # No forced language on this first pass, so the spoken language is detected.
    # (Detection happens here, up front; segments are decoded lazily, so rejecting
    # a non-English recording costs nothing extra.)
    segments, info = model.transcribe(
        audio_path,
        language=None,
        beam_size=5,
        vad_filter=True,
    )

    detected = getattr(info, "language", None)
    confidence = float(getattr(info, "language_probability", 0.0) or 0.0)
    duration = float(getattr(info, "duration", 0.0) or 0.0)

    if detected and detected != "en":
        if confidence >= NON_ENGLISH_CONFIDENCE:
            return {
                "text": "",
                "segments": [],
                "duration_seconds": duration,
                "error": NOT_ENGLISH_MESSAGE,
                "detected_language": detected,
            }
        # Unsure -> treat as English, decoded exactly the way it always was.
        segments, info = model.transcribe(
            audio_path,
            language="en",
            beam_size=5,
            vad_filter=True,
        )

    text = ""

    timestamps = []

    for seg in segments:
        text += seg.text + " "
        timestamps.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text
        })

    return {
        "text": text.strip(),
        "segments": timestamps
        ,"duration_seconds": float(info.duration or (timestamps[-1]["end"] if timestamps else 0.0))
    }
