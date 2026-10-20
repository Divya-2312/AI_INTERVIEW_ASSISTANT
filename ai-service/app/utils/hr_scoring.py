"""
HR-only overall score.

HR answers are scored as the plain average of four factors:
    correctness, relevance, accuracy, communication

This is deliberately NOT used for Java theory, DBMS theory, predict-the-output
or coding questions -- those keep their own scoring.
"""

HR_SCORE_FACTORS = ("correctness", "relevance", "accuracy", "communication")


def _percent(value) -> int:
    """0..1 float -> whole percent, matching what the UI displays (Math.round(v * 100))."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    numeric = max(0.0, min(1.0, numeric))
    return int(numeric * 100 + 0.5)


def calculate_hr_overall(correctness, relevance, accuracy, communication) -> int:
    """
    Average of the four factors as shown to the candidate, so the overall score
    always equals the average of the four displayed percentages.
    """
    percents = [_percent(v) for v in (correctness, relevance, accuracy, communication)]
    return int(sum(percents) / len(percents) + 0.5)
