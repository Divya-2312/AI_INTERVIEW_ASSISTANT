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


def build_hr_evaluation_summary(
    score: int,
    correctness: float,
    relevance: float,
    accuracy: float,
    communication: float,
    answer: str,
    weaknesses: list = None,
    improvement_suggestion: str = None,
    delivery_metrics: dict = None,
    is_irrelevant: bool = False,
) -> tuple:
    """
    Builds a plain-English 2-3 sentence evaluation summary for HR answers.
    Returns:
        (score_reason, why_not_100)
    For score >= 95 or 100: why_not_100 is None.
    Contains zero raw decimals or phrases like 'weighted score'.
    Uses the exact displayed percentages.
    """
    import re

    c_pct = _percent(correctness)
    r_pct = _percent(relevance)
    a_pct = _percent(accuracy)
    comm_pct = _percent(communication)

    text = (answer or "").strip()
    words = text.split()
    word_count = len(words)
    clean_weaknesses = [str(w).strip() for w in (weaknesses or []) if w]

    # Handle completely off-topic or empty
    if is_irrelevant or (r_pct == 0 and c_pct == 0):
        reason = (
            "The response scored 0% overall because it does not address the question that was asked. "
            "The answer lacks relevant situation context, personal actions, and professional outcomes. "
            "To improve, answer the question directly using a specific example from your experience."
        )
        return reason, reason

    # High score (>= 95)
    if score >= 95:
        summary = (
            f"Excellent response! Your answer scored {score}% overall, reflecting the average of "
            f"{r_pct}% relevance, {c_pct}% correctness, {a_pct}% accuracy, and {comm_pct}% communication. "
            f"You provided clear context, concrete personal actions, and a well-articulated outcome."
        )
        return summary, None

    # Sentence 1: Displayed score and average breakdown of factors (no raw decimals)
    s1 = (
        f"Your response scored {score}% overall, reflecting the average of "
        f"{r_pct}% relevance, {c_pct}% correctness, {a_pct}% accuracy, and {comm_pct}% communication."
    )

    # Identify the single weakest factor
    factors = [
        ("relevance", r_pct, "Relevance"),
        ("correctness", c_pct, "Correctness"),
        ("accuracy", a_pct, "Accuracy"),
        ("communication", comm_pct, "Communication"),
    ]
    factors.sort(key=lambda x: x[1])
    weakest_key, weakest_pct, weakest_label = factors[0]

    # Find concrete reason from signals
    concrete_reason = ""
    has_delivery_issues = False

    # Check delivery metrics first if communication is weakest or delivery had issues
    if delivery_metrics and isinstance(delivery_metrics, dict):
        filler_count = delivery_metrics.get("fillerWordCount", 0)
        pause_count = delivery_metrics.get("noticeablePauseCount", 0)
        repetition_count = delivery_metrics.get("repetitionCount", 0)
        obs = delivery_metrics.get("observations") or []
        if filler_count >= 3:
            concrete_reason = f"frequent filler words ({filler_count} detected) impacted verbal clarity"
            has_delivery_issues = True
        elif pause_count >= 3:
            concrete_reason = f"noticeable pauses ({pause_count} gaps over 1.8 seconds) interrupted delivery"
            has_delivery_issues = True
        elif repetition_count >= 2:
            concrete_reason = f"repeated phrasing ({repetition_count} repetitions) reduced fluency"
            has_delivery_issues = True
        elif obs:
            concrete_reason = obs[0].lower().rstrip(".")
            has_delivery_issues = True

    if not concrete_reason:
        if word_count < 25:
            concrete_reason = f"the response is too brief ({word_count} words) to adequately detail your actions"
        elif any("outcome" in w.lower() or "result" in w.lower() for w in clean_weaknesses):
            concrete_reason = "it omits the final measurable outcome or impact of your actions"
        elif any("example" in w.lower() or "situation" in w.lower() or "context" in w.lower() for w in clean_weaknesses):
            concrete_reason = "it remains too general without a concrete real-world example"
        elif clean_weaknesses:
            w0 = clean_weaknesses[0].rstrip(".")
            w0 = re.sub(r'\b\d+\.\d+\b', '', w0).strip()
            if w0.lower().startswith("the answer ") or w0.lower().startswith("the candidate "):
                w0 = w0[len("the answer "):] if w0.lower().startswith("the answer ") else w0[len("the candidate "):]
            concrete_reason = w0[:120].strip()
        elif improvement_suggestion and len(improvement_suggestion) > 10:
            sugg = re.sub(r'\b\d+\.\d+\b', '', improvement_suggestion).strip().rstrip(".")
            concrete_reason = sugg[:120].strip()
        else:
            if weakest_key == "communication":
                concrete_reason = "the response could be structured more clearly and concisely"
            elif weakest_key == "relevance":
                concrete_reason = "the response does not directly target the core question"
            elif weakest_key == "correctness":
                concrete_reason = "key behavioral competencies for the role were not fully covered"
            else:
                concrete_reason = "the explanation lacks sufficient depth on key competencies"

    # Ensure concrete_reason contains no raw decimals or 'weighted'
    concrete_reason = re.sub(r'\b\d+\.\d+\b', '', concrete_reason).replace("weighted score", "score").replace("weighted", "")

    # Sentence 2: Mention weakest factor and concrete reason
    s2 = f"The primary area lowering the score is {weakest_label} ({weakest_pct}%), where {concrete_reason}."

    # Sentence 3: Constructive guidance / next step
    if has_delivery_issues:
        s3 = "Focus on speaking at a steady pace and pausing briefly rather than using filler words."
    elif "star" not in text.lower():
        s3 = "Structure your response with the STAR method (Situation, Task, Action, Result) to highlight tangible achievements."
    else:
        s3 = "Provide more specific personal takeaways and quantifiable outcomes to strengthen your explanation."

    full_summary = f"{s1} {s2} {s3}"
    return full_summary, full_summary

