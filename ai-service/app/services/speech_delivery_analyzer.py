import os
import re
import logging
from collections import Counter
import numpy as np

logger = logging.getLogger("speech_delivery_analyzer")

CONJUNCTIONS_PREPOSITIONS = {
    "and", "but", "because", "to", "of", "for", "with", "that", "which", "when",
    "if", "is", "are", "was", "were", "am", "be", "been", "have", "has", "can", "will",
    "or", "as", "at", "by", "from", "in", "into", "on", "onto", "than", "so"
}

ABSOLUTE_FILLERS = {"um", "umm", "uh", "uhh", "er", "erm", "ah", "ahh", "hmm", "mm"}

CONTEXTUAL_MULTI_FILLERS = [
    ("okay", "so"),
    ("you", "know"),
    ("you", "see"),
    ("i", "mean"),
    ("kind", "of"),
    ("sort", "of"),
]

CONTEXTUAL_SINGLE_FILLERS = {
    "like", "so", "right", "well", "basically", "actually", "literally"
}

_av_open_patched = False
_cached_model = None
_cached_model_name = None


def _patch_av_open_once():
    global _av_open_patched
    if not _av_open_patched:
        try:
            import av
            if hasattr(av, "open"):
                _orig_av_open = av.open
                def _safe_av_open(*args, **kwargs):
                    kwargs.pop("metadata_errors", None)
                    return _orig_av_open(*args, **kwargs)
                av.open = _safe_av_open
                _av_open_patched = True
        except Exception:
            pass


def get_delivery_whisper_model():
    global _cached_model, _cached_model_name
    if _cached_model is not None:
        return _cached_model, _cached_model_name

    model_name = os.getenv("SPEECH_DELIVERY_MODEL", "small.en").strip()
    try:
        cpu_cores = os.cpu_count() or 4
        from faster_whisper import WhisperModel
        # Use physical CPU threads for optimum inference speed
        model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=cpu_cores, local_files_only=True)
        _cached_model = model
        _cached_model_name = model_name
        logger.info(f"[SpeechDelivery] Loaded faster-whisper model '{model_name}' (local, threads={cpu_cores})")
        return _cached_model, _cached_model_name
    except Exception as e:
        logger.warning(f"[SpeechDelivery] Could not load '{model_name}' locally ({e}), falling back to speech_service model")

    try:
        from app.services.speech_service import _get_model
        fallback = _get_model()
        if fallback is not None:
            _cached_model = fallback
            _cached_model_name = "base"
            return _cached_model, _cached_model_name
    except Exception as e2:
        logger.error(f"[SpeechDelivery] Fallback model loader error: {e2}")

    return None, None


def warmup_speech_model():
    """Preload model and transcribe 1 s of silence at startup to avoid cold start latency."""
    try:
        model, model_name = get_delivery_whisper_model()
        if model is not None:
            silence = np.zeros(16000, dtype=np.float32)
            _ = list(model.transcribe(silence, language="en", beam_size=1, best_of=1)[0])
            logger.info(f"[SpeechDelivery] Startup warm-up complete for model '{model_name}'")
    except Exception as e:
        logger.warning(f"[SpeechDelivery] Startup warm-up notice: {e}")


HALLUCINATION_PATTERN = re.compile(
    r"(?:thank you for watching|thanks for watching|see you next time|see you in the next|subscribe to my channel|please subscribe|subtitles by|translated by|like and subscribe)",
    re.IGNORECASE,
)


def transcribe_verbatim(audio_input):
    _patch_av_open_once()

    model, model_name = get_delivery_whisper_model()
    if model is None:
        return {"error": "Speech transcription model (faster-whisper) is not available.", "words": [], "text": "", "model": "none"}

    try:
        # Greedy decoding (beam_size=1, best_of=1) for 3-5x faster inference
        segments_gen, info = model.transcribe(
            audio_input,
            language="en",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            vad_filter=False,
            word_timestamps=True,
            condition_on_previous_text=False,
            compression_ratio_threshold=None,
            log_prob_threshold=None,
            no_speech_threshold=None,
            hallucination_silence_threshold=None,
            suppress_blank=False,
            initial_prompt="So, um, I I think, uh, the the main thing is, like, you know, uhh, basically, th-th-the, hmm, okay so, I mean, it's it's, uh, kind of, like, a a way to, um, to do it.",
        )

        segments = list(segments_gen)

        # Drop known Whisper hallucination tail if the last segment appears after a gap or matches pattern
        if segments:
            last_seg = segments[-1]
            last_text = last_seg.text.strip()
            if HALLUCINATION_PATTERN.search(last_text):
                is_tail_drop = False
                if len(segments) > 1:
                    gap = last_seg.start - segments[-2].end
                    if gap >= 1.0 or getattr(last_seg, "no_speech_prob", 0.0) > 0.4:
                        is_tail_drop = True
                else:
                    if getattr(last_seg, "no_speech_prob", 0.0) > 0.4:
                        is_tail_drop = True
                if is_tail_drop:
                    logger.info(f"[SpeechDelivery] Dropped hallucinated tail: '{last_text}'")
                    segments = segments[:-1]

        words = []
        full_text_parts = []
        for segment in segments:
            full_text_parts.append(segment.text)
            if hasattr(segment, "words") and segment.words:
                for w in segment.words:
                    words.append({
                        "word": w.word,
                        "start": float(w.start),
                        "end": float(w.end),
                        "probability": getattr(w, "probability", None),
                    })

        full_text = " ".join(full_text_parts).strip()
        duration = float(getattr(info, "duration", 0.0) or 0.0)
        return {"words": words, "text": full_text, "duration": duration, "model": model_name}
    except Exception as e:
        logger.error(f"[speech_delivery_analyzer] Transcription failed: {e}")
        return {"error": str(e), "words": [], "text": "", "model": model_name or "unknown"}


def compute_acoustic_features(audio_input):
    _patch_av_open_once()
    if isinstance(audio_input, np.ndarray):
        audio = audio_input
    else:
        try:
            from faster_whisper.audio import decode_audio
            audio = decode_audio(audio_input, sampling_rate=16000)
        except Exception as e:
            logger.warning(f"[SpeechDelivery] decode_audio failed: {e}")
            return None, 0.0

    if audio is None or len(audio) == 0:
        return None, 0.0

    sr = 16000
    duration = float(len(audio)) / sr
    frame_len = int(0.025 * sr)  # 400
    hop_len = int(0.010 * sr)    # 160
    min_lag = int(sr / 400)      # 40
    max_lag = int(sr / 70)       # 228

    num_frames = (len(audio) - frame_len) // hop_len + 1
    if num_frames <= 0:
        return None, duration

    # Vectorized computation via numpy sliding_window_view (70x faster)
    from numpy.lib.stride_tricks import sliding_window_view
    valid_len = (num_frames - 1) * hop_len + frame_len
    frames = sliding_window_view(audio[:valid_len], frame_len)[::hop_len]

    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    all_dbs_arr = 20.0 * np.log10(rms + 1e-12)
    all_dbs = all_dbs_arr.tolist()
    zcrs = np.mean(np.abs(np.diff(np.signbit(frames), axis=1)), axis=1)

    lags = np.arange(min_lag, max_lag + 1)
    n_lags = len(lags)
    corrs_matrix = np.zeros((num_frames, n_lags), dtype=np.float32)

    for idx, lag in enumerate(lags):
        A = frames[:, :frame_len - lag]
        B = frames[:, lag:]
        dot = np.sum(A * B, axis=1)
        norm = np.sqrt(np.sum(A**2, axis=1) * np.sum(B**2, axis=1)) + 1e-12
        corrs_matrix[:, idx] = dot / norm

    best_indices = np.argmax(corrs_matrix, axis=1)
    periodicities = np.maximum(0.0, corrs_matrix[np.arange(num_frames), best_indices])
    peak_lags = lags[best_indices]
    f0s = np.where(peak_lags > 0, sr / peak_lags, 0.0)

    e0 = np.sum(frames**2, axis=1)
    periodicities = np.where(e0 < 1e-8, 0.0, periodicities)
    peak_lags = np.where(e0 < 1e-8, min_lag, peak_lags)
    f0s = np.where(e0 < 1e-8, 0.0, f0s)

    center_ts = (np.arange(num_frames) * hop_len + frame_len / 2.0) / sr

    frames_data = [
        {
            "t": float(center_ts[i]),
            "db": float(all_dbs_arr[i]),
            "zcr": float(zcrs[i]),
            "periodicity": float(periodicities[i]),
            "f0": float(f0s[i]),
        }
        for i in range(num_frames)
    ]

    noise_floor = float(np.percentile(all_dbs, 10))
    p95 = float(np.percentile(all_dbs, 95))
    active_thresh = max(noise_floor + 10.0, p95 - 35.0)

    for fd in frames_data:
        fd["active"] = bool(fd["db"] > active_thresh)
        fd["voiced"] = bool(fd["active"] and (fd["periodicity"] >= 0.5) and (fd["zcr"] < 0.2))

    return frames_data, duration


def detect_acoustic_hesitations_and_pauses(audio_path, words, acoustic_frames=None, audio_dur=None):
    if acoustic_frames is not None:
        frames_data = acoustic_frames
        if audio_dur is None:
            audio_dur = frames_data[-1]["t"] if frames_data else 0.0
    else:
        if isinstance(audio_path, np.ndarray):
            frames_data, audio_dur = compute_acoustic_features(audio_path)
        elif not audio_path or not os.path.exists(audio_path):
            return 0, 0, []
        else:
            frames_data, audio_dur = compute_acoustic_features(audio_path)
    if not frames_data:
        return 0, 0, []

    # Build candidate spans (inter-word gaps + prolonged words where Whisper absorbs silence or buzz)
    candidates = []
    if words:
        first_start = float(words[0].get("start", 0.0))
        if first_start > 0.0:
            candidates.append((0.0, first_start))
        for i in range(len(words) - 1):
            g_start = float(words[i].get("end", 0.0))
            g_end = float(words[i + 1].get("start", 0.0))
            if g_end > g_start:
                candidates.append((g_start, g_end))
        last_end = float(words[-1].get("end", 0.0))
        if audio_dur > last_end:
            candidates.append((last_end, audio_dur))

        # Check prolonged words (where Whisper absorbed hesitation buzz or pause into the word token)
        for w in words:
            w_start = float(w.get("start", 0.0))
            w_end = float(w.get("end", 0.0))
            if w_end - w_start >= 0.40:
                candidates.append((w_start, w_end))
    else:
        candidates.append((0.0, audio_dur))

    hesitation_count = 0
    silent_pause_count = 0
    hesitation_spans = []

    for g_start, g_end in candidates:
        span_frames = [f for f in frames_data if g_start <= f["t"] <= g_end]
        if not span_frames:
            continue

        # Check silent pause: duration >= 1.0s and active fraction < 0.2
        if (g_end - g_start) >= 1.0:
            active_frames = [f for f in span_frames if f["active"]]
            if len(active_frames) / float(len(span_frames)) < 0.2:
                silent_pause_count += 1
                continue

        # Check hesitation sound: shrink by 0.04s at both ends
        shrunk_start = g_start + 0.04
        shrunk_end = g_end - 0.04
        if (shrunk_end - shrunk_start) >= 0.25:
            s_frames = [f for f in span_frames if shrunk_start <= f["t"] <= shrunk_end]
            if s_frames:
                voiced_frames = [f for f in s_frames if f["voiced"]]
                if len(voiced_frames) / float(len(s_frames)) >= 0.6:
                    f0_list = [f["f0"] for f in voiced_frames if f["f0"] > 0]
                    if f0_list:
                        f0_mean = float(np.mean(f0_list))
                        f0_std = float(np.std(f0_list))
                        f0_cov = (f0_std / f0_mean) if f0_mean > 0 else 1.0
                        if f0_cov < 0.15:
                            hesitation_count += 1
                            hesitation_spans.append({"start": round(shrunk_start, 2), "end": round(shrunk_end, 2)})

    return hesitation_count, silent_pause_count, hesitation_spans


def detect_stretched_words(words):
    stretched_count = 0
    for w in words:
        raw_word = str(w.get("word", ""))
        clean_letters = re.sub(r"[^a-zA-Z]", "", raw_word)
        n_letters = len(clean_letters)
        if 0 < n_letters < 7:
            start_t = float(w.get("start", 0.0))
            end_t = float(w.get("end", 0.0))
            dur = end_t - start_t
            expected_baseline = 0.09 * n_letters + 0.10
            if dur > 0.9 and dur > 3.0 * expected_baseline:
                stretched_count += 1
    return stretched_count


PHRASE_STOPWORDS = {"the", "a", "an", "of", "to", "in", "is", "are", "it", "and", "or"}
FILLER_TOKENS_FOR_REPETITIONS = {"um", "umm", "uh", "uhh", "er", "erm", "ah", "ahh", "hmm", "mm"}


class RepetitionResult(int):
    def __new__(cls, count, examples=None):
        obj = super().__new__(cls, count)
        obj.count = int(count)
        obj.examples = list(examples or [])
        return obj

    def __iter__(self):
        yield self.count
        yield self.examples


def detect_repetitions(words_input, filler_indices=None):
    if isinstance(words_input, str):
        raw_list = words_input.split()
    elif isinstance(words_input, list):
        raw_list = words_input
    else:
        raw_list = []

    tokens_info = []
    for idx, item in enumerate(raw_list):
        if isinstance(item, dict):
            raw_w = item.get("word", "")
        else:
            raw_w = str(item)
        clean_w = re.sub(r"^[^\w]+|[^\w]+$", "", raw_w).lower()
        if clean_w:
            tokens_info.append((idx, clean_w, raw_w))

    if filler_indices is None:
        filler_indices = set()
        for idx, clean_w, _ in tokens_info:
            if clean_w in FILLER_TOKENS_FOR_REPETITIONS:
                filler_indices.add(idx)
        for i, (idx, clean_w, _) in enumerate(tokens_info):
            if clean_w in {"like", "so", "right", "well", "basically", "actually", "literally"}:
                prev_w = tokens_info[i - 1][1] if i > 0 else ""
                next_w = tokens_info[i + 1][1] if i < len(tokens_info) - 1 else ""
                if (
                    i == 0
                    or prev_w in FILLER_TOKENS_FOR_REPETITIONS
                    or next_w in FILLER_TOKENS_FOR_REPETITIONS
                    or (i > 0 and tokens_info[i - 1][0] in filler_indices)
                ):
                    filler_indices.add(idx)

    # Filter out fillers
    filtered = []
    for idx, clean_w, raw_w in tokens_info:
        if idx in filler_indices or clean_w in FILLER_TOKENS_FOR_REPETITIONS:
            continue
        filtered.append((clean_w, raw_w))

    if not filtered:
        return RepetitionResult(0, [])

    filtered_clean = [f[0] for f in filtered]
    filtered_raw = [f[1] for f in filtered]

    events = []
    examples = []
    single_rep_indices = set()

    # 1. Single-word repetitions (adjacent identical words)
    i = 0
    while i < len(filtered_clean):
        j = i + 1
        while j < len(filtered_clean) and filtered_clean[j] == filtered_clean[i]:
            j += 1
        run_len = j - i
        if run_len >= 2:
            word = filtered_clean[i]
            if run_len == 2 and word in {"that", "had"}:
                i = j
                continue
            for k in range(i, j):
                single_rep_indices.add(k)
            ex = " ".join(filtered_raw[i:j])
            examples.append(ex)
            events.append(("single", ex))
            i = j
        else:
            i += 1

    # 2. Phrase repetitions (2-4 word phrases, gap <= 2)
    i = 0
    while i < len(filtered_clean):
        if i in single_rep_indices:
            i += 1
            continue
        matched = False
        for length in (4, 3, 2):
            if i + length > len(filtered_clean):
                continue
            phrase = filtered_clean[i : i + length]
            if all(w in PHRASE_STOPWORDS for w in phrase):
                continue
            for gap in (0, 1, 2):
                next_start = i + length + gap
                if next_start + length <= len(filtered_clean):
                    cand = filtered_clean[next_start : next_start + length]
                    if cand == phrase:
                        ex = " ".join(filtered_raw[i : next_start + length])
                        examples.append(ex)
                        events.append(("phrase", ex))
                        matched = True
                        i = next_start + length
                        break
            if matched:
                break
        if not matched:
            i += 1

    return RepetitionResult(len(events), examples[:3])


def analyze_delivery(words, full_text=None, audio_path=None, model="small.en", duration=0.0, acoustic_frames=None):
    # Guard: if audio shorter than 3 seconds or Whisper returns no words
    if not words or (duration > 0 and duration < 3.0):
        note = "too short to analyse"
        return {
            "metrics": {
                "fillerWordCount": 0,
                "spokenFillerCount": 0,
                "hesitationSoundCount": 0,
                "stretchedWordCount": 0,
                "silentPauseCount": 0,
                "noticeablePauseCount": 0,
                "repetitionCount": 0,
                "repetitionExamples": [],
                "stammerCount": 0,
                "longPauseCount": 0,
                "fillerFrequencyPer100Words": 0.0,
                "sentenceCompleteness": "possible_fragment",
                "fillerBreakdown": {},
            },
            "approximateWpm": None,
            "rating": "Clear",
            "tips": [],
            "transcript": full_text or "",
            "source": "audio",
            "model": model,
            "note": note,
        }

    tokens = [w.get("word", "").strip() for w in words]
    clean_words = [re.sub(r"[^\w'-]", "", t).lower() for t in tokens]
    n = len(clean_words)

    # 1. Lexical and Contextual Fillers
    filler_counts = Counter()
    filler_indices = set()

    # Multi-word fillers
    for i in range(n - 1):
        pair = (clean_words[i], clean_words[i + 1])
        for mf in CONTEXTUAL_MULTI_FILLERS:
            if pair == mf:
                filler_name = f"{mf[0]} {mf[1]}"
                filler_counts[filler_name] += 1
                filler_indices.add(i)
                filler_indices.add(i + 1)

    # Single-word absolute fillers and contextual fillers
    for i in range(n):
        if i in filler_indices:
            continue
        cw = clean_words[i]
        if cw in ABSOLUTE_FILLERS:
            filler_counts[cw] += 1
            filler_indices.add(i)
        elif cw in CONTEXTUAL_SINGLE_FILLERS:
            prev_w = clean_words[i - 1] if i > 0 else ""
            next_w = clean_words[i + 1] if i < n - 1 else ""
            raw_token = tokens[i]

            # Exclusion rules:
            if cw == "like":
                is_verb_or_prep = (
                    prev_w in {"i", "we", "they", "you", "would", "looks", "look", "looked", "feels", "feel", "felt", "seems", "seem", "seemed", "sounded", "sounds", "sound"}
                    or next_w in {"a", "an", "the", "this", "that", "these", "those"}
                )
                if is_verb_or_prep:
                    continue
            elif cw == "so":
                if next_w in {"that", "much", "many", "far"}:
                    continue

            # Discourse filler conditions: adjacent to comma/pause, start of sentence, or next to another filler
            has_comma = (
                raw_token.endswith(",") or raw_token.startswith(",") or
                (i > 0 and tokens[i - 1].endswith(","))
            )
            prev_gap = (float(words[i].get("start", 0)) - float(words[i - 1].get("end", 0))) if i > 0 else 0.0
            next_gap = (float(words[i + 1].get("start", 0)) - float(words[i].get("end", 0))) if i < n - 1 else 0.0
            has_pause = prev_gap > 0.20 or next_gap > 0.20
            adjacent_filler = (i - 1 in filler_indices) or (i + 1 < n and clean_words[i + 1] in ABSOLUTE_FILLERS)
            is_start_with_pause = (i == 0 and (has_comma or has_pause or n <= 2))

            if has_comma or has_pause or adjacent_filler or is_start_with_pause:
                filler_counts[cw] += 1
                filler_indices.add(i)

    spoken_filler_count = sum(filler_counts.values())

    # 2. Acoustic Detection of Hesitation Sounds and Silent Pauses
    hesitation_sound_count, acoustic_silent_pauses, _ = detect_acoustic_hesitations_and_pauses(audio_path, words, acoustic_frames=acoustic_frames, audio_dur=duration)
    if hesitation_sound_count > 0:
        filler_counts["hesitation sound"] = hesitation_sound_count

    total_filler_count = spoken_filler_count + hesitation_sound_count

    # 3. Stretched Words
    stretched_word_count = detect_stretched_words(words)

    # 4. Stammers / False Starts
    stammer_count = 0
    for i in range(n):
        token = tokens[i]
        cw = clean_words[i]
        if "-" in token:
            parts = token.split("-")
            if len(parts) >= 2:
                p0 = re.sub(r"[^\w]", "", parts[0]).lower()
                p1 = re.sub(r"[^\w]", "", parts[1]).lower()
                if p0 and p1 and (p1.startswith(p0) or p0 == p1):
                    stammer_count += 1
                    continue

        if i < n - 1 and i not in filler_indices and (i + 1) not in filler_indices:
            next_cw = clean_words[i + 1]
            if 1 <= len(cw) <= 3 and len(next_cw) > len(cw) and next_cw.startswith(cw):
                stammer_count += 1

    # 5. Repetitions
    repetition_count, repetition_examples = detect_repetitions(words, filler_indices=filler_indices)

    # 6. Pauses from timestamps
    timestamp_noticeable_pauses = 0
    long_pause_count = 0
    for i in range(len(words) - 1):
        try:
            gap = float(words[i + 1].get("start", 0)) - float(words[i].get("end", 0))
            if gap > 1.0:
                timestamp_noticeable_pauses += 1
            if gap > 2.0:
                long_pause_count += 1
        except (TypeError, ValueError):
            continue

    noticeable_pause_count = max(timestamp_noticeable_pauses, acoustic_silent_pauses)
    silent_pause_count = acoustic_silent_pauses

    # 7. Approximate WPM
    approximate_wpm = None
    try:
        if len(words) >= 2:
            first_start = float(words[0].get("start", 0))
            last_end = float(words[-1].get("end", 0))
            total_dur = last_end - first_start
            if total_dur > 0:
                raw_wpm = round((len(clean_words) / total_dur) * 60)
                if 40 <= raw_wpm <= 250:
                    approximate_wpm = raw_wpm
    except Exception:
        pass

    # 8. Rating & Frequency
    word_count = len(clean_words)
    filler_freq = round((total_filler_count * 100 / word_count), 1) if word_count > 0 else 0.0
    disfluencies = total_filler_count + repetition_count + stammer_count
    disfluency_rate = round((disfluencies * 100 / word_count), 1) if word_count > 0 else 0.0

    if disfluency_rate < 4:
        rating = "Clear"
    elif disfluency_rate < 10:
        rating = "Fair"
    else:
        rating = "Needs work"

    if rating == "Clear" and (noticeable_pause_count >= 3 or long_pause_count >= 3):
        rating = "Fair"

    # 9. Tips
    tips = []
    if total_filler_count > 0:
        fillers_preview = ", ".join([k for k in filler_counts.keys() if k != "hesitation sound"][:3])
        dur_sec = round(float(duration or (words[-1]["end"] - words[0]["start"])))
        if fillers_preview:
            tips.append(f"You used about {total_filler_count} filler sound{'s' if total_filler_count != 1 else ''} in {dur_sec}s ({fillers_preview}); pause silently instead")
        else:
            tips.append(f"You used about {total_filler_count} filler/hesitation sound{'s' if total_filler_count != 1 else ''} in {dur_sec}s; pause silently instead")

    if repetition_count >= 2:
        tips.append("Avoid repeating phrases; finish one thought before the next")
    if stammer_count >= 1:
        tips.append("Reduce false starts and stuttered words; take a steady breath before speaking")
    if stretched_word_count >= 2:
        tips.append(f"Avoid prolonging/stretching words ({stretched_word_count} detected); maintain steady vocal pace")
    if noticeable_pause_count >= 3:
        tips.append("Several noticeable pauses; prepare key concepts before speaking")
    if approximate_wpm is not None:
        if approximate_wpm < 90:
            tips.append("Pace is slow; try to speak a little faster")
        elif approximate_wpm > 180:
            tips.append("Pace is fast; slow down slightly")

    # 10. Sentence completeness
    last_word = clean_words[-1] if clean_words else ""
    sentence_completeness = (
        "likely_complete"
        if (len(clean_words) >= 4 and last_word not in CONJUNCTIONS_PREPOSITIONS)
        else "possible_fragment"
    )

    verbatim_text = full_text or " ".join(tokens)

    return {
        "metrics": {
            "fillerWordCount": total_filler_count,
            "spokenFillerCount": spoken_filler_count,
            "hesitationSoundCount": hesitation_sound_count,
            "stretchedWordCount": stretched_word_count,
            "silentPauseCount": silent_pause_count,
            "noticeablePauseCount": noticeable_pause_count,
            "repetitionCount": repetition_count,
            "repetitionExamples": repetition_examples,
            "stammerCount": stammer_count,
            "longPauseCount": long_pause_count,
            "fillerFrequencyPer100Words": filler_freq,
            "sentenceCompleteness": sentence_completeness,
            "fillerBreakdown": dict(filler_counts),
        },
        "approximateWpm": approximate_wpm,
        "rating": rating,
        "tips": tips[:6],
        "transcript": verbatim_text,
        "source": "audio",
        "model": model,
    }
