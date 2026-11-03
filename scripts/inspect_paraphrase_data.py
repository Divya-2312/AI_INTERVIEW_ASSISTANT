import json
import os
import sys

with open("ai-service/tests/data/paraphrase_answers.json", "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Total items: {len(items)}")
for i, item in enumerate(items):
    qid = item.get("questionId")
    qtext = item.get("question", "")[:60]
    keys = list(item.get("answers", {}).keys())
    print(f"[{i:02d}] {qid}: {qtext} | keys: {keys}")
