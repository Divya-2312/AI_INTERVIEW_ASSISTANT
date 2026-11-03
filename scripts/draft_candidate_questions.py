"""
Draft Candidate Questions Script for MockMate AI.
Asks the base model llama3.2:3b to draft new technical interview questions
with a referenceAnswer and expectedConcepts, filters them through quality
and Sentence-BERT near-duplicate checks (cosine similarity >= 0.88 against catalogue),
and writes candidates to:
    ai-service/app/data/question_bank/candidates_<subject>_<difficulty>.json
with "needsHumanReview": true.

NOTE: These candidate files are strictly for human review and are NOT loaded
by the runtime question pool or catalogue.
"""

import os
import sys
import json
import time
import urllib.request
import argparse
from datetime import datetime

# Setup path to import ai-service modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_SERVICE_DIR = os.path.join(BASE_DIR, "ai-service")
if AI_SERVICE_DIR not in sys.path:
    sys.path.insert(0, AI_SERVICE_DIR)

from app.models.llama_provider import _GUARANTEED_UNIQUE_THEORY_QUESTIONS
from app.services.embedding_service import embedding_service

OLLAMA_API_URL = "http://localhost:11434/api/generate"
BASE_MODEL_NAME = "llama3.2:3b"


def call_ollama(prompt: str, model_name: str = BASE_MODEL_NAME, temperature: float = 0.7) -> str:
    """Calls Ollama base model directly via standard HTTP request."""
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_predict": 512,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_API_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("response", "")


def draft_questions_for(subject: str, difficulty: str, target_count: int = 5):
    """
    Drafts questions using llama3.2:3b, validates schema and quality,
    enforces SBERT >= 0.88 duplicate check against the catalogue,
    and saves to candidates file.
    """
    subject = subject.lower()
    difficulty = difficulty.lower()
    print(f"\n========================================================")
    print(f" DRAFTING CANDIDATE QUESTIONS: {subject.upper()} ({difficulty.upper()})")
    print(f" Target count: {target_count} | Base Model: {BASE_MODEL_NAME}")
    print(f"========================================================")

    # 1. Load existing catalogue questions for reference and deduplication
    existing_items = list(_GUARANTEED_UNIQUE_THEORY_QUESTIONS.get((subject, difficulty), []))
    catalogue_texts = [q.get("questionText", "").strip() for q in existing_items if q.get("questionText")]
    print(f"Loaded {len(catalogue_texts)} existing catalogue questions for {subject} ({difficulty}).")

    # Output file path
    output_dir = os.path.join(AI_SERVICE_DIR, "app", "data", "question_bank")
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"candidates_{subject}_{difficulty}.json"
    output_filepath = os.path.join(output_dir, output_filename)

    # Load existing candidates if present
    existing_candidates = []
    if os.path.exists(output_filepath):
        try:
            with open(output_filepath, "r", encoding="utf-8") as f:
                existing_candidates = json.load(f)
            print(f"Found {len(existing_candidates)} existing candidate(s) in {output_filename}.")
        except Exception as e:
            print(f"Warning reading existing candidates: {e}")

    existing_candidate_texts = [c.get("questionText", "").strip() for c in existing_candidates if c.get("questionText")]

    accepted_candidates = []
    attempts = 0
    max_attempts = target_count * 5

    topic_hints = {
        "java": ["OOP design", "Memory management", "Multithreading", "Collections", "Generics", "JVM internals", "Exception handling"],
        "dbms": ["ACID transactions", "Indexing & B-trees", "Normalization & Normal forms", "Relational algebra & joins", "Concurrency control", "Locking & Isolation"]
    }
    hints = topic_hints.get(subject, ["General architecture", "Performance", "Core principles"])

    while len(accepted_candidates) < target_count and attempts < max_attempts:
        attempts += 1
        hint = hints[(attempts - 1) % len(hints)]

        prompt = f"""You are a senior technical interviewer designing a {difficulty} level {subject} interview question.
Focus topic hint: {hint}.
Create ONE new, high-quality interview question.
Requirements:
1. "questionText": Clear, concise, standard interview question (ends with '?').
2. "category": Concise topic name.
3. "referenceAnswer": Accurate 2 to 4 sentence model answer stating key facts and mechanisms.
4. "expectedConcepts": Array of 2 to 5 essential technical terms/concepts the candidate must mention.

Respond ONLY with valid JSON in this exact structure:
{{
  "questionText": "What is ...?",
  "category": "...",
  "referenceAnswer": "Sentence 1. Sentence 2. Sentence 3.",
  "expectedConcepts": ["concept1", "concept2", "concept3"]
}}"""

        try:
            print(f"Attempt {attempts}: Calling {BASE_MODEL_NAME} for topic '{hint}'...", end=" ", flush=True)
            raw = call_ollama(prompt, model_name=BASE_MODEL_NAME, temperature=0.7)
            data = json.loads(raw)
        except Exception as e:
            print(f"FAIL (API/Parse error: {e})")
            continue

        qtext = str(data.get("questionText") or "").strip()
        ref_ans = str(data.get("referenceAnswer") or "").strip()
        concepts = data.get("expectedConcepts") or []
        cat = str(data.get("category") or hint).strip()

        # Quality Check 1: Length and structure
        if len(qtext) < 15 or not qtext.endswith("?"):
            print(f"REJECT (Invalid questionText: '{qtext[:40]}...')")
            continue

        if len(ref_ans) < 25 or len(ref_ans.split(".")) < 2:
            print(f"REJECT (referenceAnswer too short or lacking sentences)")
            continue

        if not isinstance(concepts, list) or len(concepts) < 2:
            print(f"REJECT (expectedConcepts must be list with >= 2 items)")
            continue

        # Quality Check 2: Deduplication against existing candidates
        all_check_texts = catalogue_texts + existing_candidate_texts + [c["questionText"] for c in accepted_candidates]
        is_dup, max_sim, closest_text = embedding_service.is_similar_to_any(qtext, all_check_texts, threshold=0.88)
        if is_dup:
            print(f"REJECT (SBERT duplicate: sim={max_sim:.3f} >= 0.88 with '{closest_text[:40]}...')")
            continue

        # Construct Candidate Object
        candidate_id = f"candidate-{subject[:3]}-{difficulty[:3]}-{int(time.time())}-{len(accepted_candidates)+1}"
        candidate_entry = {
            "id": candidate_id,
            "subject": subject,
            "difficulty": difficulty,
            "category": cat,
            "questionText": qtext,
            "referenceAnswer": ref_ans,
            "expectedConcepts": [str(c).strip() for c in concepts if str(c).strip()],
            "needsHumanReview": True,
            "draftedAt": datetime.utcnow().isoformat() + "Z",
            "modelUsed": BASE_MODEL_NAME,
            "maxCatalogueSimilarity": round(float(max_sim), 4),
            "closestCatalogueQuestion": closest_text
        }
        accepted_candidates.append(candidate_entry)
        print(f"ACCEPTED! (sim={max_sim:.3f}) '{qtext[:50]}...'")

    # Combine with existing candidates and save
    final_candidates = existing_candidates + accepted_candidates
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(final_candidates, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f" DRAFTING COMPLETE")
    print(f" Drafted {len(accepted_candidates)} new candidate(s) (Total in file: {len(final_candidates)}).")
    print(f" Target File: {output_filepath}")
    print(f" IMPORTANT NOTICE FOR TEAM:")
    print(f"   These candidate questions are tagged with 'needsHumanReview': true.")
    print(f"   They are NOT loaded by the active interview service or runtime catalogue.")
    print(f"   The team MUST manually review and approve the following file before adding to catalogue:")
    print(f"   -> {output_filepath}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Draft new candidate questions using base model llama3.2:3b.")
    parser.add_argument("--subject", choices=["java", "dbms"], default="java", help="Subject (java or dbms)")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="easy", help="Difficulty level")
    parser.add_argument("--count", type=int, default=3, help="Number of candidate questions to draft")
    args = parser.parse_args()

    draft_questions_for(args.subject, args.difficulty, args.count)
