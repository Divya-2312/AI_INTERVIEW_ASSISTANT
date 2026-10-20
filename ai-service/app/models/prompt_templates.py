import json

TRAINING_SYSTEM_PROMPT = (
    "You are AI Interview Assistant, an interview practice assistant. Follow the requested task. "
    "For generation and evaluation tasks, return only the requested JSON object; do not wrap it in markdown. "
    "Evaluate meaning and correctness, not keyword presence alone. Never invent evidence from the student's answer. "
    "Grading Rules: Relevance measures if the answer addresses the topic and is separate from correctness. "
    "Short answers are not auto-irrelevant if on-topic. "
    "Keyword lists earn little credit without explanation."
)

def build_training_style_prompt(task: str, input_dict: dict) -> str:
    """
    Reproduces EXACTLY the user-message prompt format used in training data:
    
    TASK: <task>
    INPUT:
    <json_dumps_indent_2>

    Return the required result. For JSON tasks, output valid JSON only.
    """
    formatted_json = json.dumps(input_dict, indent=2)
    return (
        f"TASK: {task}\n"
        f"INPUT:\n{formatted_json}\n\n"
        f"Return the required result. For JSON tasks, output valid JSON only."
    )
