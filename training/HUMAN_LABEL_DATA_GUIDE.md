# Human-Reviewed Evaluation & Follow-Up Label Data Guide

## Overview
Currently, `evaluate_answer` rows in the training dataset are programmatically generated synthetic rubric examples (`"source": "synthetic_rubric"`). To transition from synthetic labels to real human expert annotations, follow the guide below to create, validate, and merge human-reviewed datasets.

## File Format
Save human-reviewed records in JSONL format. Each line must be a valid JSON object with `"source": "human_reviewed"`.

### Example `evaluate_answer` Record
```json
{
  "task": "evaluate_answer",
  "source": "human_reviewed",
  "input": {
    "interviewType": "technical",
    "subject": "Java",
    "question": "What is encapsulation in Java?",
    "answer": "Encapsulation is hiding implementation details and exposing public getter and setter methods.",
    "reference_answer": "Encapsulation is bundling data and methods that operate on that data within a single unit and restricting access using private fields and public methods.",
    "expectedConcepts": ["data hiding", "private fields", "getters and setters"]
  },
  "output": {
    "score": 90,
    "correctness": 95,
    "conceptCoverage": 90,
    "relevance": 100,
    "communication": 90,
    "isIrrelevant": false,
    "feedback": "Excellent explanation of encapsulation focusing on data hiding and accessors.",
    "strengths": ["Accurately describes data hiding", "Mentions getters and setters"],
    "weaknesses": ["Could mention bundling fields and methods"],
    "missingConcepts": [],
    "improvementSuggestion": "Mention that encapsulation also bundles fields and methods into a single class unit.",
    "scoreReason": "Human expert rating based on coverage of core concepts."
  }
}
```

## How Human Data Replaces Synthetic Data
1. Add your reviewed lines to `training/data/raw/human_evaluations.jsonl`.
2. Run `python training/prepare_mockmate_datasets.py` to convert raw files into `canonical.jsonl`.
3. Run `python training/prepare_dataset.py --input training/data/processed/canonical.jsonl --output-dir training/data/processed/splits --summary-path training/data/processed/summary.json`.
4. Inspect `summary.json` to verify `source_distribution` counts reflect the addition of `"human_reviewed"` examples.
