# FINAL MODEL & PIPELINE AUDIT REPORT: AI INTERVIEW ASSISTANT

---

## 1. Measured Current State & Phase 0 Findings

An empirical audit of the repository model files, Ollama registration, and runtime probe endpoints yielded the following measured findings:

| Probe Check | Command / Endpoint | Measured Result | Status |
| :--- | :--- | :--- | :---: |
| **GGUF File Existence** | `Test-Path mockmate\ai-service\models\mockmate-llama-gguf\mockmate-llama-q4_k_m.gguf` | `False` (No GGUF file or adapter binary present in repository) | **MISSING** |
| **Ollama Model Registration** | `ollama list` | `mockmate-llama-ft:latest` registered (`digest: 6a0746a100f7...`) | **PRESENT** |
| **Model Blob Alignment** | `ollama show mockmate-llama-ft --modelfile` vs `llama3:8b` | `FROM sha256-6a0746a1...` (Identical blob to stock `llama3:8b`) | **UNFINE-TUNED ALIAS** |
| **10x JSON Behavior Test** | `generate_question` prompt x 10 runs | 0/10 outputs returned bare valid JSON without text wrapping | **FAILED** |
| **Health Probe** | `GET /health` | `is_fine_tuned_verified: false`, `demo_ready: false` | **UNVERIFIED** |

### Phase 0 One-Paragraph Verdict
> **Fine-tuned artifact present and distinct: NO.**
> The Ollama model `mockmate-llama-ft` points to `sha256-6a0746a100f7...`, which is the exact same blob as the stock base model `llama3:8b`. The expected GGUF file `mockmate-llama-q4_k_m.gguf` does not exist on disk, and 0/10 test prompts returned bare valid JSON. Therefore, `mockmate-llama-ft` is currently the stock base model under a new name. To activate a real fine-tuned model, follow the Colab training steps in `training/COLAB_STEPS.md`.

---

## 2. Dataset Verification & Group-Based Splitting

The project contains 6 raw dataset files (100 records each = 600 total source records):

| Module Name | File Path | Record Count | Malformed | Duplicates |
| :--- | :--- | :---: | :---: | :---: |
| **Java Theory** | `training/data/raw/java_theory_100.jsonl` | 100 | 0 | 0 |
| **Java Output Prediction** | `training/data/raw/java_output_prediction_100.jsonl` | 100 | 0 | 0 |
| **Java Coding** | `training/data/raw/java_coding_100.jsonl` | 100 | 0 | 0 |
| **DBMS Theory** | `training/data/raw/dbms_theory_100.jsonl` | 100 | 0 | 0 |
| **SQL Coding** | `training/data/raw/sql_coding_100.jsonl` | 100 | 0 | 0 |
| **HR Questions** | `training/data/raw/hr_questions_100.jsonl` | 100 | 0 | 0 |
| **TOTAL** | **6 Modules** | **600** | **0** | **0** |

### Data Pipeline Processing (`training/data/processed/`)
- **Canonical Dataset (`canonical.jsonl`)**: 1,800 records total (600 generation records with `"source": "dataset_raw"` + 1,200 synthetic evaluation records with `"source": "synthetic_rubric"` covering `reference`, `partial`, `wrong`, and `keyword_dump` answer cases).
- **Group-Based Splits (`splits/`)**: Split by question group key to guarantee **0 prompt overlap** and **0 question overlap** across splits:
  - **Train**: 1,348 records (840 distinct prompts)
  - **Validation**: 180 records (158 distinct prompts)
  - **Test**: 272 records (213 distinct prompts)

---

## 3. Measured Identity Architecture (No Hardcoded Booleans)

The hardcoded constants (`IS_FINE_TUNED = True`, `FALLBACK_ENABLED = False`) have been replaced with live runtime measurement:

1. **Measured `/health` Identity**:
   - `is_fine_tuned_verified` is computed dynamically via Ollama API inspect (`/api/tags` and `/api/show`) and GGUF file presence.
   - `base_model_used_for_inference` is `True` when the active model shares the base model digest/blob.
   - `demo_ready` is `False` when the model is unverified.
2. **Response Metadata**:
   - Every API generation and evaluation response includes additive metadata fields: `modelUsed`, `usedFallback`, and `scoringSources` (e.g. `["llm", "bert", "rules"]` or `["exact_match"]`).
3. **Strict Control Flow**:
   - Silent fallback to base model or dummy fallbacks is disabled in strict mode. If the LLM call fails, the AI service returns `AIGenerationUnavailableError` (HTTP 503).

---

## 4. How to Verify

Run the following commands to audit the codebase and verify system state:

### 1. Run All Unit Test Suites (42 Tests)
```powershell
# Run AI Service unit tests (35 tests)
cd mockmate/ai-service
python -m unittest discover -s tests -v

# Run Training unit tests (7 tests)
cd mockmate
python -m unittest discover -s training/tests -v
```

### 2. Verify Live Health & Model Verification
```powershell
# Start AI service
cd mockmate/ai-service
uvicorn app.main:app --port 8000

# Probe health endpoint
curl http://localhost:8000/health
```

### 3. Run Pipeline Verification Script
```powershell
cd mockmate
python scripts/verify_finetuned_pipeline.py
```

### 4. Run Batch Evaluation (Requires `--allow-unverified` when unverified)
```powershell
python scripts/generate_and_evaluate_all_modules.py --allow-unverified
```

---

## 5. Known Limitations & Truthful Status Disclosure

1. **Ollama Model Status**: `mockmate-llama-ft` is currently an un-finetuned alias pointing to the stock `llama3:8b` base model blob because no GGUF artifact was supplied.
2. **Fine-Tuned Tasks**: Only `generate_question` and `generate_coding_problem` tasks have raw source training data. `evaluate_answer` tasks use programmatically generated synthetic rubric examples (`"source": "synthetic_rubric"`). `generate_followup` has 0 training examples (`# UNTRAINED TASK`).
3. **Evaluation Scoring Methods**:
   - Output prediction tasks use exact string matching (`"scoringSources": ["exact_match"]`).
   - Technical/Theory answers blend LLM score, BERT embedding similarity, and term-list heuristics.
   - Coding and SQL scores use an LLM-estimated test case pass rate (code is not executed in a sandbox).
4. **Dataset Scale**: The 600-record raw dataset is small and repetitive. Group-based splitting was implemented to eliminate test set contamination.
