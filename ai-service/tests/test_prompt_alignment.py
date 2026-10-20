import unittest
import json
from pathlib import Path
from app.models.prompt_templates import build_training_style_prompt, TRAINING_SYSTEM_PROMPT

class TestPromptAlignment(unittest.TestCase):
    def test_runtime_prompt_matches_training_format(self):
        root_dir = Path(__file__).resolve().parent.parent.parent
        train_file = root_dir / "training" / "data" / "processed" / "splits" / "train.jsonl"
        
        self.assertTrue(train_file.exists(), f"Missing training file {train_file}")
        
        with open(train_file, "r", encoding="utf-8") as f:
            sample_line = f.readline().strip()
            
        data = json.loads(sample_line)
        messages = data.get("messages", [])
        
        system_msg = messages[0]["content"]
        user_msg = messages[1]["content"]
        
        # Verify system prompt matches
        self.assertEqual(system_msg, TRAINING_SYSTEM_PROMPT)
        
        # Verify structure of user prompt
        sample_input = {
            "interviewType": "technical",
            "subject": "Java",
            "language": "java",
            "difficulty": "medium",
            "category": "Strings",
            "request": "Create a coding problem with starter code, examples and test cases."
        }
        
        generated_user_msg = build_training_style_prompt("generate_coding_problem", sample_input)
        
        self.assertTrue(generated_user_msg.startswith("TASK: generate_coding_problem\nINPUT:\n"))
        self.assertTrue(generated_user_msg.endswith("\n\nReturn the required result. For JSON tasks, output valid JSON only."))
        self.assertIn('"interviewType": "technical"', generated_user_msg)

    def test_evaluate_answer_prompt_matches_sampled_training_row(self):
        root_dir = Path(__file__).resolve().parent.parent.parent
        train_file = root_dir / "training" / "data" / "processed" / "splits" / "train.jsonl"
        
        self.assertTrue(train_file.exists(), f"Missing training file {train_file}")
        
        eval_row = None
        with open(train_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    if obj.get("task") == "evaluate_answer":
                        eval_row = obj
                        break

        self.assertIsNotNone(eval_row, "No evaluate_answer row found in train.jsonl")

        messages = eval_row["messages"]
        system_msg = messages[0]["content"]
        user_msg = messages[1]["content"]

        self.assertEqual(system_msg, TRAINING_SYSTEM_PROMPT)
        self.assertTrue(user_msg.startswith("TASK: evaluate_answer\nINPUT:\n"))
        self.assertTrue(user_msg.endswith("\n\nReturn the required result. For JSON tasks, output valid JSON only."))

        # Verify build_training_style_prompt produces identical structure for runtime inputs
        sample_eval_input = {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is encapsulation?",
            "answer": "It hides data.",
            "reference_answer": "Encapsulation bundles data and restricts access.",
            "expectedConcepts": ["data hiding", "access restriction"],
            "questionFormat": "theory"
        }
        runtime_prompt = build_training_style_prompt("evaluate_answer", sample_eval_input)
        self.assertTrue(runtime_prompt.startswith("TASK: evaluate_answer\nINPUT:\n"))
        self.assertIn('"question": "What is encapsulation?"', runtime_prompt)

    def test_runtime_and_training_evaluate_answer_keys_match(self):
        root_dir = Path(__file__).resolve().parent.parent.parent
        train_file = root_dir / "training" / "data" / "processed" / "splits" / "train.jsonl"
        self.assertTrue(train_file.exists(), f"Missing training file {train_file}")

        eval_row = None
        with open(train_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    if obj.get("task") == "evaluate_answer":
                        eval_row = obj
                        break

        self.assertIsNotNone(eval_row)
        user_msg = eval_row["messages"][1]["content"]
        # Extract JSON blob inside user message
        json_start = user_msg.find("INPUT:\n") + len("INPUT:\n")
        json_end = user_msg.rfind("\n\nReturn the required result.")
        training_input_json = json.loads(user_msg[json_start:json_end])

        training_keys = set(training_input_json.keys())

        # Runtime keys when ideal answer is known
        runtime_input_known = {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is encapsulation?",
            "answer": "It hides data.",
            "expectedConcepts": ["data hiding"],
            "questionFormat": "theory",
            "reference_answer": "Encapsulation bundles data."
        }
        self.assertEqual(training_keys, set(runtime_input_known.keys()))

        # Runtime keys when ideal answer is unknown (reference_answer omitted, context present)
        runtime_input_unknown = {
            "interviewType": "technical",
            "subject": "java",
            "question": "What is encapsulation?",
            "answer": "It hides data.",
            "expectedConcepts": ["data hiding"],
            "questionFormat": "theory",
            "context": ["Java encapsulation principles."]
        }
        self.assertNotIn("reference_answer", runtime_input_unknown)
        self.assertIn("context", runtime_input_unknown)


if __name__ == "__main__":
    unittest.main()

