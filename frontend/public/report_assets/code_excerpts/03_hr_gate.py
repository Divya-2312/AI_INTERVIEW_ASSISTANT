# ai-service/app/utils/hr_gate.py:75-91
def topic_hits(question: str, answer: str) -> int:
    """Number of this question's topic keywords found in the answer."""
    it = find_hr_item(question)
    if not it:
        # Fallback to question content tokens if not in 100 curated set
        q_content = content(question) - _GENERIC_Q
        return len(content(answer) & q_content)
    
    topic = ((content(it["question"]) - _GENERIC_Q) | content(" ".join(it.get("keywords", [])))) - _FILLER
    return len(content(answer) & topic)

def is_off_topic(question: str, answer: str) -> bool:
    """Return True if answer does not contain any relevant topic tokens."""
    if not (answer or "").strip():
        return True
    return topic_hits(question, answer) == 0
