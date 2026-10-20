import os
import unittest

from prepare_dataset import read_records
from train_qlora import validate_training_config


class TrainingConfigTests(unittest.TestCase):
    def test_config_rejects_invalid_batch_or_learning_rate(self):
        with self.assertRaises(ValueError):
            validate_training_config({"batch_size": 0, "learning_rate": 1e-4, "max_steps": 50})

        with self.assertRaises(ValueError):
            validate_training_config({"batch_size": 2, "learning_rate": 0, "max_steps": 50})

    def test_config_accepts_smoke_test_defaults(self):
        cfg = validate_training_config({
            "model": "meta-llama/Llama-3.2-3B-Instruct",
            "max_steps": 10,
            "batch_size": 1,
            "learning_rate": 2e-4,
            "max_seq_length": 1024,
            "gradient_accumulation_steps": 2,
            "smoke_test": True,
        })
        self.assertTrue(cfg["smoke_test"])
        self.assertEqual(cfg["max_steps"], 10)
        self.assertEqual(cfg["batch_size"], 1)

    def test_training_data_files_are_readable(self):
        p = "training/data/processed/splits/train.jsonl"
        if not os.path.exists(p):
            p = "data/processed/splits/train.jsonl"
        rows = read_records(p)
        self.assertGreater(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
