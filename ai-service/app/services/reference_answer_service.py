import os
import time
import re
import logging
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import List, Optional, Dict, Any, Tuple
import requests

from app.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger("ai_service")

_REFUSAL_PATTERN = re.compile(
    r"\b(i am sorry|i apologize|as an ai|i cannot|i do not know|as a language model|i'm sorry|not_covered)\b",
    re.IGNORECASE,
)


class ReferenceAnswerService:
    """
    In-memory background reference answer service.
    Prepares reference answers using base model (llama3.2:3b) in the background
    for Java and DBMS theory questions only.
    Answers come ONLY from generation.
    Results are kept in an in-memory cache only (TTL: 2 hours, max 500 entries).
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ref_ans_worker")
        self._ttl_seconds = 7200  # 2 hours
        self._max_cache_entries = 500

    def _is_enabled(self) -> bool:
        val = os.getenv("REFERENCE_ANSWER_ENABLED", "true").strip().lower()
        return val in ("true", "1", "yes", "on")

    def _cache_key(self, question: str, subject: str) -> str:
        norm_text = " ".join(str(question or "").strip().lower().split())
        norm_subj = str(subject or "").strip().lower()
        return hashlib.sha256(f"{norm_subj}:{norm_text}".encode("utf-8")).hexdigest()

    def _prune_cache_locked(self):
        now = time.time()
        expired = [k for k, v in self._cache.items() if now - v.get("timestamp", 0) > self._ttl_seconds]
        for k in expired:
            self._cache.pop(k, None)

        if len(self._cache) > self._max_cache_entries:
            sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k].get("timestamp", 0))
            remove_count = len(self._cache) - self._max_cache_entries
            for k in sorted_keys[:remove_count]:
                self._cache.pop(k, None)

    def schedule_generation(
        self,
        question: str,
        subject: str,
        interview_type: str = "technical",
        question_format: str = "theory",
        difficulty: str = "medium",
        expected_concepts: Optional[Any] = None,
        guidance: Optional[str] = None,
        reference_answer: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """
        Schedules background generation for technical + theory + subject java or dbms ONLY.
        HR, coding, SQL, and output prediction do nothing.
        """
        if not self._is_enabled():
            return

        itype = str(interview_type or "").strip().lower()
        qformat = str(question_format or "theory").strip().lower()
        subj = str(subject or "").strip().lower()

        # Acts ONLY for technical + theory + (java or dbms). HR, coding, SQL, output_prediction do nothing.
        if not (itype == "technical" and qformat == "theory" and subj in ("java", "dbms")):
            return

        if not question or not str(question).strip():
            return

        key = self._cache_key(question, subj)

        with self._lock:
            self._prune_cache_locked()
            entry = self._cache.get(key)
            if entry and (entry.get("status") in ("ready", "in_flight")):
                return

            future = self._executor.submit(
                self._generate_and_validate,
                question=question,
                subject=subj,
                expected_concepts=expected_concepts,
                cache_key=key,
                timeout=40,
            )

            self._cache[key] = {
                "status": "in_flight",
                "referenceAnswer": None,
                "timestamp": time.time(),
                "future": future,
            }

    def _call_base_llama(
        self,
        prompt: str,
        model: str,
        endpoint: str,
        timeout: int = 40,
    ) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 200,
                "temperature": 0.2,
            },
        }

        resp = requests.post(endpoint, json=payload, timeout=timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama base model call failed with HTTP {resp.status_code}")
        data = resp.json()
        return data.get("response", "").strip()

    def _clean_model_output(self, raw: str) -> str:
        text = raw.strip()
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()

        prefixes = [
            r"^reference answer:\s*",
            r"^model answer:\s*",
            r"^answer:\s*",
            r"^here is (the|a) (reference )?answer:\s*",
            r"^sure, here is (the|a) (reference )?answer:\s*",
        ]
        for p in prefixes:
            text = re.sub(p, "", text, flags=re.IGNORECASE).strip()

        return text

    def _sanity_check_and_trim(self, question: str, text: str) -> Tuple[bool, Optional[str]]:
        cleaned = self._clean_model_output(text)
        if not cleaned:
            return False, None

        if _REFUSAL_PATTERN.search(cleaned):
            return False, None

        norm_ans = " ".join(re.findall(r"\w+", cleaned.lower()))
        norm_q = " ".join(re.findall(r"\w+", question.lower()))
        if norm_ans == norm_q:
            return False, None

        words = cleaned.split()
        if len(words) < 15:
            return False, None

        if len(words) > 160:
            # Cut at the last full sentence within 160 words
            sub_text = " ".join(words[:160])
            match = list(re.finditer(r"[.!?](?:\s|$)", sub_text))
            if match:
                last_end = match[-1].end()
                trimmed = sub_text[:last_end].strip()
                trimmed_words = trimmed.split()
                if len(trimmed_words) >= 15:
                    cleaned = trimmed
                else:
                    return False, None
            else:
                return False, None

        return True, cleaned

    def _generate_and_validate(
        self,
        question: str,
        subject: str,
        expected_concepts: Optional[Any],
        cache_key: str,
        timeout: int = 40,
    ) -> Optional[str]:
        # Top 2 RAG chunks
        top2_chunks = rag_service.retrieve_context(subject, question, top_k=2)
        context_str = " ".join(" ".join(c.split()) for c in top2_chunks) if top2_chunks else "None"

        # Expected concepts formatting
        concepts_list: List[str] = []
        if isinstance(expected_concepts, list):
            concepts_list = [str(c).strip() for c in expected_concepts if str(c).strip()]
        elif isinstance(expected_concepts, str):
            concepts_list = [c.strip() for c in expected_concepts.split(",") if c.strip()]

        concepts_str = ", ".join(concepts_list) if concepts_list else "core definitions and key principles"

        prompt = (
            f"Write a clear model answer to this interview question in 3 to 5 sentences (60 to 110 words). "
            f"Cover these key points: {concepts_str}. "
            f"Notes that may help (use only if relevant): {context_str}. "
            f"Answer the question directly and do not repeat the question.\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )

        model = os.getenv("REFERENCE_ANSWER_MODEL", getattr(settings, "BASE_MODEL_OLLAMA_NAME", getattr(settings, "BASE_MODEL_NAME", "llama3.2:3b")))
        endpoint = getattr(settings, "MODEL_ENDPOINT", "http://localhost:11434/api/generate")

        final_answer = None
        # Single generation run with 1 retry on sanity check failure
        for attempt in range(2):
            try:
                raw = self._call_base_llama(prompt, model=model, endpoint=endpoint, timeout=timeout)
                passed, cleaned = self._sanity_check_and_trim(question, raw)
                if passed and cleaned:
                    final_answer = cleaned
                    logger.info(f"[ReferenceAnswer] Generated answer accepted (attempt {attempt+1}/2, {len(cleaned.split())} words)")
                    break
                else:
                    logger.warning(f"[ReferenceAnswer] Sanity check failed (attempt {attempt+1}/2)")
            except Exception as e:
                logger.warning(f"[ReferenceAnswer] Generation error (attempt {attempt+1}/2): {e}")

        with self._lock:
            if final_answer:
                self._cache[cache_key] = {
                    "status": "ready",
                    "referenceAnswer": final_answer,
                    "timestamp": time.time(),
                    "future": None,
                }
            else:
                self._cache[cache_key] = {
                    "status": "failed",
                    "referenceAnswer": None,
                    "timestamp": time.time(),
                    "future": None,
                }

        return final_answer

    def get_reference_answer(
        self,
        question: str,
        subject: str,
        interview_type: str = "technical",
        difficulty: str = "medium",
        expected_concepts: Optional[Any] = None,
        guidance: Optional[str] = None,
        wait_timeout: float = 40.0,
    ) -> Dict[str, Any]:
        """
        Retrieves reference answer from cache or waits up to wait_timeout.
        If cached status is failed, retries once on demand within 25 s.
        Generates on-demand if not found in cache.
        """
        if not self._is_enabled():
            return {"status": "failed", "referenceAnswer": None}

        itype = str(interview_type or "").strip().lower()
        subj = str(subject or "").strip().lower()

        # Acts ONLY for technical theory java/dbms
        if itype != "technical" or subj not in ("java", "dbms"):
            return {"status": "failed", "referenceAnswer": None}

        key = self._cache_key(question, subj)

        entry = None
        with self._lock:
            entry = self._cache.get(key)

        if entry and entry.get("status") == "in_flight":
            fut = entry.get("future")
            if isinstance(fut, Future):
                try:
                    fut.result(timeout=wait_timeout)
                except Exception:
                    pass
            with self._lock:
                entry = self._cache.get(key)

        if entry and entry.get("status") == "ready":
            return {"status": "ready", "referenceAnswer": entry.get("referenceAnswer")}

        # If the endpoint is called for a question whose cached status is "failed", retry once on demand within 25 s.
        if entry and entry.get("status") == "failed":
            try:
                answer = self._generate_and_validate(
                    question=question,
                    subject=subj,
                    expected_concepts=expected_concepts,
                    cache_key=key,
                    timeout=25,
                )
                if answer:
                    return {"status": "ready", "referenceAnswer": answer}
            except Exception as e:
                logger.warning(f"[ReferenceAnswer] On-demand retry failed: {e}")
            return {"status": "failed", "referenceAnswer": None}

        # Not in cache yet: generate on demand
        try:
            answer = self._generate_and_validate(
                question=question,
                subject=subj,
                expected_concepts=expected_concepts,
                cache_key=key,
                timeout=int(min(wait_timeout, 40.0)),
            )
            if answer:
                return {"status": "ready", "referenceAnswer": answer}
        except Exception as e:
            logger.warning(f"[ReferenceAnswer] On-demand generation failed: {e}")

        return {"status": "failed", "referenceAnswer": None}


reference_answer_service = ReferenceAnswerService()
