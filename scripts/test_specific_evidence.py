import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("ai-service"))
sys.path.insert(0, os.path.abspath("scripts"))

from app.models.llama_provider import (
    find_theory_item,
    _split_reference_key_points
)
from scripts.test_rubric_tuning import evaluate_theory_answer

# Evidence 1: Generics reversed
q1 = "What is the benefit of using generics instead of raw Object types in collections?"
a1 = "generics let you store any type in one list together like int and String mixed, raw objects only allow one type"
cat1 = find_theory_item(q1)
ref1 = cat1["referenceAnswer"]
c1 = cat1.get("expectedConcepts", [])

print("--- Evidence 1: Generics reversed ---")
print("Key points:", _split_reference_key_points(ref1))

# Evidence 2: Encapsulation mostly wrong
q2 = "What is encapsulation in Java and why is it useful?"
a2 = "encapsulation means making a class inside another class so it is hidden, it is useful becoz then you dont need constructors"
cat2 = find_theory_item(q2)
ref2 = cat2["referenceAnswer"]
c2 = cat2.get("expectedConcepts", [])

print("\n--- Evidence 2: Encapsulation mostly wrong ---")
print("Key points:", _split_reference_key_points(ref2))

for margin in [15, 20, 26]:
    r1 = evaluate_theory_answer(q1, a1, ref1, c1, 0.70, 0.58, margin)
    r2 = evaluate_theory_answer(q2, a2, ref2, c2, 0.70, 0.58, margin)
    print(f"\nMargin={margin}:")
    print(f"  Generics (target <= 25): score={r1['score']} (Cor={r1['correctness']}, Rel={r1['relevance']}, Cov={r1['conceptCoverage']}, Com={r1['communication']}), Decisions={r1['point_decisions']}")
    print(f"  Encapsulation (target <= 15): score={r2['score']} (Cor={r2['correctness']}, Rel={r2['relevance']}, Cov={r2['conceptCoverage']}, Com={r2['communication']}), Decisions={r2['point_decisions']}")
