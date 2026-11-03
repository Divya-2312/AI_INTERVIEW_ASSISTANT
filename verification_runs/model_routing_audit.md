# Model Routing Audit Report

**Date**: 2026-10-29  
**Service**: MockMate AI Service (`ai-service` on port 8000)  
**Endpoint**: `http://localhost:11434/api/generate` (Ollama local runner)  

---

## 1. Executive Summary & Runtime Model Inventory

### 1.1 Ollama Installed Models (Verified via `ollama list`)
| Model Name | Model ID | Parameter Size / Quant | Primary Purpose | Status in Ollama |
|---|---|---|---|---|
| `mockmate-hr100:latest` | `377c3b5ed931` | 3.2B / Q8_0 | Fine-tuned HR evaluation & Java code complexity (Big-O) | **Installed & Available** |
| `llama3.2:3b` | `a80c4f17acd5` | 3.2B / Q4_K_M | Predefined Base LLaMA for writing & grading technical modules | **Installed & Available** |
| `mockmate:latest` | `fc49d4f5b709` | 3.4 GB | General fine-tuned artifact | Installed |
| `mockmate-llama-ft:latest` | `174faa587450` | 2.0 GB | Legacy fine-tuned alias | Installed |
| `llama3:8b` | `365c0bd3c000` | 4.7 GB | 8B base model | Installed |

### 1.2 AI Service Effective Runtime Configuration (from `/health` and `config.py`)
- **Base Model (`BASE_MODEL_NAME` / `BASE_MODEL_OLLAMA_NAME` / `MODEL_NAME`)**: `llama3.2:3b`
- **Fine-Tuned Model (`FINE_TUNED_MODEL_NAME`)**: Configured at runtime via env to `mockmate-hr100:latest`; code default in `app/config.py` previously pointed to `mockmate-llama-ft` (must be fixed to `mockmate-hr100`).
- **Complexity Model (`COMPLEXITY_MODEL_NAME`)**: Evaluates to `mockmate-hr100`; code default in `app/config.py` was `mockmate-llama-ft` (must be fixed to `mockmate-hr100`).
- **Sentence Transformer (`EMBEDDING_MODEL`)**: `all-MiniLM-L6-v2` (BERT-derived similarity tool).

---

## 2. Call Site Audit Table

| Call Site (File & Function) | Purpose | Allowed Model (Target A/B/C) | Configured Model | Failure Behavior Before Fix | Target Compliance |
|---|---|---|---|---|---|
| `llama_provider.py`:<br>`_evaluate_hr_answer` | HR answer evaluation (sub-scores: correctness, relevance, accuracy) | Fine-tuned ONLY (`mockmate-hr100`) | `ft_model_name` (`mockmate-hr100`) | **DEVIATION**: If fine-tuned call failed, `_call_llama` silently fell back to base model `self.model_name` (`llama3.2:3b`)! | **Non-Compliant** (Must fail cleanly without falling back to base model) |
| `llama_provider.py`:<br>`_analyze_code_complexity` | Java time & space complexity (Big-O) analysis | Fine-tuned ONLY (`mockmate-hr100`) | `complexity_model_name` (`mockmate-hr100`) | **DEVIATION**: `_call_llama` fell back to base model before heuristic fallback. | **Non-Compliant** (Must never call base model; fallback directly to regex rule marked `source: "rule"`) |
| `llama_provider.py`:<br>`_generate_hr_question` | HR interview questions | Bank ONLY (`hr_india_100.json`, 10 distinct per session) | None (Curated Bank) | **DEVIATION**: If bank load failed, fell back to `_call_llama` generating dynamic question via base model! | **Non-Compliant** (Must only pull from 100-question bank; no base model call) |
| `llama_provider.py`:<br>`generate_question` (theory) | Java & DBMS theory question generation | Base model ONLY (`llama3.2:3b`) | `self.model_name` (`llama3.2:3b`) | Up to 5 generation attempts, then catalogue fallback | **Compliant** |
| `llama_provider.py`:<br>`_generate_output_prediction_question` | Predict the output snippet generation | Base model ONLY (`llama3.2:3b`) | `self.model_name` (`llama3.2:3b`) | Up to 5 generation attempts, then catalogue fallback | **Compliant** |
| `llama_provider.py`:<br>`_generate_java_coding_question` | Java coding problem generation | Base model ONLY (`llama3.2:3b`) | `self.model_name` (`llama3.2:3b`) | Up to 5 generation attempts, then catalogue fallback | **Compliant** |
| `llama_provider.py`:<br>`_generate_sql_question` | SQL query problem generation | Base model ONLY (`llama3.2:3b`) | `self.model_name` (`llama3.2:3b`) | Up to 5 generation attempts, then catalogue fallback | **Compliant** |
| `llama_provider.py`:<br>`generate_followup` | Technical theory follow-up questions & reference answer | Base model ONLY (`llama3.2:3b`) | `self.model_name` (`llama3.2:3b`) | Up to 3 attempts, raises error or returns fallback | **Compliant** |
| `llama_provider.py`:<br>`_generate_question_commentary` | Technical question commentary & tips | Base model ONLY (`llama3.2:3b`) | `self.model_name` (`llama3.2:3b`) | Empty fallback string | **Compliant** |
| `llama_provider.py`:<br>`_evaluate_theory_answer` | Java/DBMS theory rubric evaluation & feedback | Base model ONLY (`llama3.2:3b`) | `self.model_name` (`llama3.2:3b`) | Falls back to SBERT concept coverage | **Compliant** |
| `llama_provider.py`:<br>`_evaluate_coding_answer` | Java/SQL coding test case judge & feedback | Base model ONLY (`llama3.2:3b`) | `self.model_name` (`llama3.2:3b`) | Execution in JVM/SQLite does ground truth; model only provides explanation | **Compliant** |
| `llama_provider.py`:<br>`_evaluate_output_prediction` | Output prediction grading & misconceptions | Base model ONLY (`llama3.2:3b`) | `self.model_name` (`llama3.2:3b`) | Normalization & execution does scoring; model explains errors | **Compliant** |
| `question_pool.py`:<br>`init_from_catalogues` & `pop_question` | Question source ordering & pool serving | Base model FIRST, Catalogue LAST | Catalogues (`_GUARANTEED_UNIQUE_*`) | **DEVIATION**: Pre-populated pool with catalogue items and served catalogue BEFORE calling base LLaMA! | **Non-Compliant** (Model must be 1st source; pool only filled by base LLaMA; catalogue is last resort fallback) |

---

## 3. Deviations Identified & Required Fixes

1. **`app/config.py` Default Model Names**:
   - `FINE_TUNED_MODEL_NAME` defaulted to `"mockmate-llama-ft"`. Must default to `"mockmate-hr100"`.
   - `COMPLEXITY_MODEL_NAME` defaulted to `"mockmate-llama-ft"`. Must default to `"mockmate-hr100"`.
2. **`llama_provider.py:_call_llama` Silent Fallback**:
   - Lines 2903–2919: Automatically caught failures for `target_model` and re-dispatched to `self.model_name` (`llama3.2:3b`).
   - Fix: For fine-tuned routes (`mockmate-hr100` for HR eval and complexity), **never** fall back to base model.
   - For HR evaluation: retry per retry policy, then return error `"evaluation engine unavailable, please retry"`.
   - For complexity: fall back directly to regex heuristic rule, marked `source: "rule"`.
3. **`llama_provider.py:_generate_hr_question` Base Model Fallback**:
   - Lines 3302–3330: If bank loading threw, fell back to `_call_llama` to dynamically generate HR questions with base LLaMA.
   - Fix: Remove base model call. HR questions must strictly come from the 100-question bank (`hr_india_100.json`).
4. **Question Source Order in `question_generator.py` and `question_pool.py`**:
   - `question_pool.init_from_catalogues()` served catalogue questions first before calling base model.
   - Fix:
     - Base LLaMA is the FIRST source for technical questions.
     - Ready pool can only be filled by the base model (not catalogues).
     - Catalogues / `_GUARANTEED_UNIQUE` lists are ONLY the last resort when all model generation attempts fail.
     - Questions from base model marked `modelUsed: "llama3.2:3b"` and `source: "model"`.
     - Questions from catalogue fallback marked `source: "catalogue_fallback"`.
     - Questions from HR bank marked `source: "bank"`.
5. **Metadata Reporting**:
   - Ensure every AI response returns `modelUsed` and (for questions) `source`.
