# ai-service/app/models/llama_provider.py:3087-3110
        # 1. Deterministic Off-Topic Gate (0 score for completely irrelevant answers)
        if is_off_topic(question, answer):
            missing = list(hr_item["concepts"]) if hr_item and "concepts" in hr_item else (concepts or ["Context and situation", "Concrete personal actions", "Quantifiable outcome", "Professional ownership"])
            return {
                "score": 0,
                "conceptCoverage": 0.0,
                "correctness": 0.0,
                "relevance": 0.0,
                "accuracy": 0.0,
                "communication": 0.0,
                "isIrrelevant": True,
                "feedback": "The response does not address the question asked, so no credit can be given.",
                "strengths": [],
                "weaknesses": ["The answer does not relate to the question that was asked"],
                "coveredConcepts": [],
                "partiallyCoveredConcepts": [],
                "missingConcepts": missing,
                "deeperConcepts": [],
                "improvementSuggestion": "Answer the question that was asked, using a specific example from your own experience.",
                "scoreReason": "The answer is not about this question; score 0.",
                "modelUsed": "hr_gate_filter",
                "usedFallback": False,
                "scoringSources": ["hr_gate", "rubric"],
            }
