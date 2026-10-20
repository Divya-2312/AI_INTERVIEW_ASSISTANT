import re
from collections import Counter

LONG_PAUSE_THRESHOLD = 2.0
_FILLER_PATTERN = re.compile(
    r"\b(?:you\s+know|i\s+mean|basically|literally|actually|hmm|erm|um|uh)\b",
    flags=re.IGNORECASE,
)
_WORD_PATTERN = re.compile(r"\b[\w']+\b")


def analyze_speech(text, segments, duration_seconds=None):
    transcript = text or ""
    filler_matches = [re.sub(r"\s+", " ", match.group(0).lower()) for match in _FILLER_PATTERN.finditer(transcript)]
    filler_counts = dict(Counter(filler_matches))
    word_count = len(_WORD_PATTERN.findall(transcript))

    normalized_segments = [segment for segment in (segments or []) if isinstance(segment, dict)]
    try:
        duration = float(duration_seconds or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0 and normalized_segments:
        try:
            duration = max(float(segment.get("end", 0) or 0) for segment in normalized_segments)
        except (TypeError, ValueError):
            duration = 0.0

    wpm = round(word_count * 60 / duration) if duration > 0 else 0
    long_pauses = []
    short_gap_count = 0
    for previous, current in zip(normalized_segments, normalized_segments[1:]):
        try:
            gap_start = float(previous.get("end", 0) or 0)
            gap_end = float(current.get("start", 0) or 0)
        except (TypeError, ValueError):
            continue
        gap_duration = gap_end - gap_start
        if 0 < gap_duration <= LONG_PAUSE_THRESHOLD:
            short_gap_count += 1
        elif gap_duration > LONG_PAUSE_THRESHOLD:
            long_pauses.append({
                "start": round(gap_start, 2),
                "end": round(gap_end, 2),
                "duration": round(gap_duration, 2),
            })

    longest_pause = max((pause["duration"] for pause in long_pauses), default=0.0)
    filler_count = len(filler_matches)
    pause_durations = [pause["duration"] for pause in long_pauses]
    return {
        # Legacy keys retained for the existing /speech-to-text response.
        "fillers": filler_matches,
        "fillerCount": filler_count,
        "wordsPerMinute": wpm,
        "pauseCount": len(long_pauses),
        "pauses": pause_durations,
        # Structured metrics used by the HR analysis flow.
        "duration_seconds": round(duration, 2),
        "word_count": word_count,
        "wpm": wpm,
        "filler_count": filler_count,
        "filler_breakdown": filler_counts,
        "long_pause_count": len(long_pauses),
        "longest_pause_seconds": longest_pause,
        "long_pauses": long_pauses,
        "short_gap_count": short_gap_count,
    }