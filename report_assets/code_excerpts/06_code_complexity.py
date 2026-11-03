# ai-service/app/models/llama_provider.py:3273-3310
    def _analyze_code_complexity(self, question: str, code: str, lang: str = "java") -> dict:
        heuristic = _estimate_code_complexity_heuristic(code)
        if not code or not code.strip():
            return heuristic

        input_dict = {
            "language": (lang or "java").lower().strip(),
            "question": question or "Coding problem implementation",
            "code": code
        }
        prompt = build_training_style_prompt("analyze_code_complexity", input_dict)
        chosen_model = getattr(self, "ft_model_name", settings.FINE_TUNED_MODEL_NAME) if getattr(settings, "USE_FT_COMPLEXITY", True) else getattr(self, "model_name", settings.MODEL_NAME)
        try:
            raw_text, model_used = self._call_llama(
                prompt,
                timeout=45,
                num_predict=256,
                temperature=0.0,
                response_format="json",
                system=TRAINING_SYSTEM_PROMPT,
                model_override=chosen_model
            )
            data = _extract_json(raw_text)
            tc = _safe_str(data.get("timeComplexity"))
            sc = _safe_str(data.get("spaceComplexity"))
            exp = _safe_str(data.get("explanation"))
            if tc and ("O(" in tc or "o(" in tc):
                return {
                    "timeComplexity": tc,
                    "spaceComplexity": sc or heuristic["spaceComplexity"],
                    "explanation": exp or heuristic["explanation"],
                    "modelUsed": model_used,
                    "scoringSource": "fine_tuned_llama"
                }
            return heuristic
        except Exception as e:
            return heuristic
