#!/usr/bin/env python3
"""
Script to build human-readable Topic Catalogues for Java Theory and DBMS Theory.
Generates:
- ai-service/app/data/question_bank/java_theory_catalogue.json
- ai-service/app/data/question_bank/JAVA_THEORY_CATALOGUE.md
- ai-service/app/data/question_bank/dbms_theory_catalogue.json
- ai-service/app/data/question_bank/DBMS_THEORY_CATALOGUE.md

Every entry is formatted with:
- id
- subject
- difficulty
- category
- questionText
- expectedConcepts
- referenceAnswer
- needs_human_review: True
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "training", "data", "raw")
OUT_DIR = os.path.join(BASE_DIR, "ai-service", "app", "data", "question_bank")

os.makedirs(OUT_DIR, exist_ok=True)

MODULES = [
    ("java", "java_theory_100.jsonl", "java_theory_catalogue.json", "JAVA_THEORY_CATALOGUE.md", "Java Theory Topic Catalogue"),
    ("dbms", "dbms_theory_100.jsonl", "dbms_theory_catalogue.json", "DBMS_THEORY_CATALOGUE.md", "DBMS Theory Topic Catalogue"),
]

for subject, raw_file, json_name, md_name, title in MODULES:
    raw_path = os.path.join(RAW_DIR, raw_file)
    if not os.path.exists(raw_path):
        print(f"Warning: {raw_path} not found")
        continue

    entries = []
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            entry = {
                "id": item.get("id"),
                "subject": subject,
                "difficulty": item.get("difficulty", "medium"),
                "category": item.get("category", "General"),
                "questionText": item.get("questionText", ""),
                "expectedConcepts": item.get("expectedConcepts", []),
                "referenceAnswer": item.get("idealAnswer", item.get("referenceAnswer", "")),
                "needs_human_review": True,
            }
            entries.append(entry)

    # Save readable JSON
    json_path = os.path.join(OUT_DIR, json_name)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(entries)} entries to {json_path}")

    # Save readable Markdown
    md_path = os.path.join(OUT_DIR, md_name)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"Total Topics: {len(entries)} | Status: Needs Human Review (`needs_human_review: true`)\n\n")
        f.write("| ID | Difficulty | Category | Question | Expected Concepts |\n")
        f.write("|---|---|---|---|---|\n")
        for e in entries:
            concepts = ", ".join(e["expectedConcepts"])
            q_clean = e["questionText"].replace("|", "\\|")
            f.write(f"| {e['id']} | {e['difficulty'].capitalize()} | {e['category']} | {q_clean} | {concepts} |\n")

        f.write("\n---\n\n## Detailed Reference Answers\n\n")
        for i, e in enumerate(entries, 1):
            f.write(f"### {i}. [{e['id']}] {e['questionText']}\n")
            f.write(f"- **Subject**: {e['subject'].upper()}\n")
            f.write(f"- **Difficulty**: {e['difficulty'].capitalize()}\n")
            f.write(f"- **Category**: {e['category']}\n")
            f.write(f"- **Expected Concepts**: `{', '.join(e['expectedConcepts'])}`\n")
            f.write(f"- **Needs Human Review**: `true`\n\n")
            f.write(f"**Reference Answer:**\n> {e['referenceAnswer']}\n\n")

    print(f"Saved readable Markdown to {md_path}")
