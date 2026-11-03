import json
import os
import sys

# Ensure app is in path
sys.path.insert(0, os.path.abspath("ai-service"))

from app.models.llama_provider import _THEORY_ITEMS_LIST, find_theory_item

with open("ai-service/tests/data/paraphrase_answers.json", "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Loaded {len(items)} items")

# Check java-theory-081 reference
cat_081 = find_theory_item("What is the benefit of using generics instead of raw Object types in collections?")
if not cat_081:
    for x in _THEORY_ITEMS_LIST:
        if "generics" in x.get("questionText", "").lower() and "raw" in x.get("questionText", "").lower():
            cat_081 = x
            break

print("Generics item:", cat_081.get("id"), cat_081.get("questionText"))
print("Generics ref:", cat_081.get("referenceAnswer"))
