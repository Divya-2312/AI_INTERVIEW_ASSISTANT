import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_DIR = os.path.join(BASE_DIR, "ai-service")
if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)

from app.models.llama_provider import (
    _GUARANTEED_UNIQUE_THEORY_QUESTIONS,
    _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS,
    _GUARANTEED_UNIQUE_CODING_QUESTIONS,
)

print("=" * 80)
print("CATALOGUE QUESTION BANK SIZES (Subject x Difficulty x Format)")
print("=" * 80)

# 1. Theory bank
print("\n--- FORMAT: Theory ---")
for subj in ["java", "dbms"]:
    for diff in ["easy", "medium", "hard"]:
        items = _GUARANTEED_UNIQUE_THEORY_QUESTIONS.get((subj, diff), [])
        unique_ids = set(q.get("id") for q in items if q.get("id"))
        unique_texts = set(q.get("questionText") for q in items if q.get("questionText"))
        print(f"  {subj.upper():<6} | {diff:<6} | Total items: {len(items):>3} | Unique IDs: {len(unique_ids):>3} | Unique Texts: {len(unique_texts):>3}")

# 2. Output Prediction
print("\n--- FORMAT: Output Prediction ---")
for subj in ["java"]:
    for diff in ["easy", "medium", "hard"]:
        items = _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS.get((subj, diff), [])
        unique_snippets = set(q.get("codeSnippet") for q in items if q.get("codeSnippet"))
        print(f"  {subj.upper():<6} | {diff:<6} | Total items: {len(items):>3} | Unique Snippets: {len(unique_snippets):>3}")

# 3. Coding / SQL
print("\n--- FORMAT: Coding / SQL ---")
for subj in ["java", "dbms"]:
    for diff in ["easy", "medium", "hard"]:
        items = _GUARANTEED_UNIQUE_CODING_QUESTIONS.get((subj, diff), [])
        unique_titles = set(q.get("title") for q in items if q.get("title"))
        print(f"  {subj.upper():<6} | {diff:<6} | Total items: {len(items):>3} | Unique Titles: {len(unique_titles):>3}")

print("=" * 80)
