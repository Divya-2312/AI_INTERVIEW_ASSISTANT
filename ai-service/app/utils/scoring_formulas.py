"""
ai-service/app/utils/scoring_formulas.py

Pure evaluation formula functions (no model calls, no side effects).
Used across all interview modules:
- Java Theory
- DBMS Theory
- HR / Behavioral
- Predict the Output
- Java Coding
- SQL
"""
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional

# One constant: every average uses this set, so the set can be changed in one place
PARAMETERS: List[str] = ["accuracy", "correctness", "relevance", "concept_coverage"]


def round_half_up(val: float) -> int:
    """
    Standard round-half-up (e.g. 2.5 -> 3, 2.4 -> 2, 66.666... -> 67).
    Uses Decimal quantize to avoid floating-point binary representation anomalies.
    """
    if math.isnan(val) or math.isinf(val):
        return 0
    # Format with 10 decimal digits to prevent float representation imprecision
    d = Decimal(f"{val:.10f}")
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def percent(matched: float, total: float) -> int:
    """
    percent(matched, total) = round-half-up(100 * matched / total),
    clamped 0..100, and 0 when total = 0.
    """
    if total <= 0:
        return 0
    if matched <= 0:
        return 0
    raw = (100.0 * float(matched)) / float(total)
    return max(0, min(100, round_half_up(raw)))


def question_score(params: Dict[str, Any]) -> int:
    """
    question_score(params) = round-half-up(mean of the PARAMETERS values),
    equal weights, no other terms.
    """
    if not params:
        return 0
    vals = [float(params.get(p, 0) or 0) for p in PARAMETERS]
    mean_val = sum(vals) / float(len(PARAMETERS))
    return max(0, min(100, round_half_up(mean_val)))


def session_score(question_scores: List[int], questions_count: int = 10) -> int:
    """
    session_score(question_scores, questions_count) = round-half-up(sum of question scores / questions_count),
    unanswered question = 0 (questions_count is 10 by default).
    """
    if questions_count <= 0:
        return 0
    total = sum(question_scores or [])
    return max(0, min(100, round_half_up(total / float(questions_count))))


def build_formula_object(module: str, accuracy: int, correctness: int, relevance: int, concept_coverage: int) -> Dict[str, Any]:
    """
    Constructs the canonical formula metadata object returned in evaluation responses:
    {
      "module": "theory",
      "parameters": {
        "accuracy": 70,
        "correctness": 75,
        "relevance": 90,
        "concept_coverage": 80
      },
      "rule": "mean of 4",
      "score": 79
    }
    """
    params = {
        "accuracy": max(0, min(100, round_half_up(accuracy))),
        "correctness": max(0, min(100, round_half_up(correctness))),
        "relevance": max(0, min(100, round_half_up(relevance))),
        "concept_coverage": max(0, min(100, round_half_up(concept_coverage))),
    }
    score = question_score(params)
    return {
        "module": module,
        "parameters": params,
        "rule": "mean of 4",
        "score": score,
    }
