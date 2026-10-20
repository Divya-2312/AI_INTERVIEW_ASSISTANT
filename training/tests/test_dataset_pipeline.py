import json
import os
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from prepare_dataset import summarize_records, normalize, read_records


class DatasetPipelineTests(unittest.TestCase):
    def test_summary_counts_subject_distribution_and_duplicates(self):
        data = [
            {"task": "generate_question", "input": {"subject": "java", "difficulty": "easy"}, "output": {"answer": "A"}},
            {"task": "generate_question", "input": {"subject": "java", "difficulty": "easy"}, "output": {"answer": "A"}},
            {"task": "generate_question", "input": {"subject": "dbms", "difficulty": "easy"}, "output": {"answer": "B"}},
            {"task": "generate_question", "input": {"subject": "hr", "difficulty": "easy"}, "output": {"answer": "C"}},
            {"task": "generate_question", "input": {"subject": "java", "difficulty": "easy"}, "output": {"answer": "D"}},
        ]
        summary = summarize_records(data)
        self.assertEqual(summary["input_records"], 5)
        self.assertEqual(summary["valid_records"], 5)
        self.assertEqual(summary["duplicate_records"], 1)
        self.assertEqual(summary["rejected_records"], 0)
        self.assertEqual(summary["subject_distribution"]["java"], 3)
        self.assertEqual(summary["subject_distribution"]["dbms"], 1)

    def test_invalid_record_is_rejected_with_reason(self):
        with self.assertRaises(ValueError):
            normalize({"task": "generate_question", "input": {"subject": "java"}}, 1)

    def test_read_records_supports_jsonl_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.jsonl"
            p.write_text(json.dumps({"task": "generate_question", "input": {"subject": "java"}, "output": {"answer": "x"}}) + "\n", encoding="utf-8")
            rows = read_records(p)
            self.assertEqual(len(rows), 1)

            q = Path(tmp) / "sample.json"
            q.write_text(json.dumps({"data": [{"task": "generate_question", "input": {"subject": "java"}, "output": {"answer": "y"}}]}), encoding="utf-8")
            rows2 = read_records(q)
            self.assertEqual(rows2[0]["output"]["answer"], "y")

    def test_zero_overlap_between_splits(self):
        splits_dir = Path(__file__).resolve().parents[1] / "data" / "processed" / "splits"
        if not (splits_dir / "train.jsonl").exists():
            self.skipTest("Splits missing")
        
        train_prompts = {json.loads(line)['messages'][1]['content'] for line in (splits_dir / "train.jsonl").read_text(encoding='utf-8').splitlines() if line.strip()}
        val_prompts = {json.loads(line)['messages'][1]['content'] for line in (splits_dir / "validation.jsonl").read_text(encoding='utf-8').splitlines() if line.strip()}
        test_prompts = {json.loads(line)['messages'][1]['content'] for line in (splits_dir / "test.jsonl").read_text(encoding='utf-8').splitlines() if line.strip()}

        self.assertEqual(len(train_prompts.intersection(val_prompts)), 0, "Train and Validation share prompts!")
        self.assertEqual(len(train_prompts.intersection(test_prompts)), 0, "Train and Test share prompts!")
        self.assertEqual(len(val_prompts.intersection(test_prompts)), 0, "Validation and Test share prompts!")

    def test_all_four_evaluation_variants_land_in_same_split(self):
        splits_dir = Path(__file__).resolve().parents[1] / "data" / "processed" / "splits"
        if not (splits_dir / "train.jsonl").exists():
            self.skipTest("Splits missing")

        question_splits = {}
        for split_name in ("train", "validation", "test"):
            file_path = splits_dir / f"{split_name}.jsonl"
            lines = [l.strip() for l in file_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            for line in lines:
                obj = json.loads(line)
                if obj.get("task") == "evaluate_answer":
                    user_msg = next((m["content"] for m in obj["messages"] if m["role"] == "user"), "")
                    # Extract question from prompt JSON
                    if "INPUT:\n" in user_msg:
                        json_str = user_msg.split("INPUT:\n", 1)[1].rsplit("\n\nReturn", 1)[0]
                        try:
                            parsed_inp = json.loads(json_str)
                            q_text = parsed_inp.get("question", "")
                            if q_text:
                                question_splits.setdefault(q_text, set()).add(split_name)
                        except Exception:
                            pass

        for q_text, split_set in question_splits.items():
            self.assertEqual(len(split_set), 1, f"Question '{q_text}' variants scattered across multiple splits: {split_set}")


if __name__ == "__main__":
    unittest.main()
