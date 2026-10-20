# AI Interview Assistant — Fine-tuning kit (LLaMA + QLoRA)

This kit adds a training workflow without replacing the existing React frontend, Node/Express backend, FastAPI AI service, RAG knowledge files, or BERT-derived sentence embeddings.

## Important hardware note

This computer has no NVIDIA GPU, so **do not try to fine-tune LLaMA locally**. Train in a GPU runtime such as Google Colab (T4, if available), then export a quantized GGUF model and run it locally through Ollama. CPU-only inference may be slow, depending on RAM and CPU. Start with `meta-llama/Llama-3.2-3B-Instruct`; it requires accepting Meta's license and Hugging Face access. Never upload your Hugging Face token to GitHub or include it in project files.

## 1. Dataset contract

Put your source data in `data/raw/`. Supported input types: `.jsonl`, `.json`, `.csv`.

Recommended canonical input is JSONL, one record per line:

```json
{"task":"evaluate_answer","input":{"question":"What is normalization?","answer":"It reduces duplicate data.","reference_answer":"Normalization organizes relations to reduce redundancy and anomalies.","rubric":{"correctness":0.4,"coverage":0.3,"relevance":0.2,"clarity":0.1}},"output":{"score":45,"correctness":0.5,"conceptCoverage":0.4,"relevance":0.9,"communication":0.6,"isIrrelevant":false,"feedback":"You identified redundancy, but did not explain normal forms or anomalies.","strengths":["Recognized redundancy"],"weaknesses":["No explanation of normal forms"],"missingConcepts":["update anomalies","normal forms"],"improvementSuggestion":"Explain how decomposition reduces insert, update and delete anomalies.","scoreReason":"The answer covers one key idea but omits important details."}}
{"task":"generate_question","input":{"interviewType":"technical","subject":"Java","difficulty":"intermediate","questionFormat":"theory","topic":"generics and type erasure"},"output":{"question":"Why does Java use type erasure for generics, and what runtime limitation follows from it?","expectedConcepts":["compile-time type checking","erasure to bounds or Object","runtime type information limitation"],"difficulty":"intermediate","questionFormat":"theory"}}
{"task":"generate_followup","input":{"previousQuestion":"What is normalization?","studentAnswer":"It reduces duplicate data.","expectedConcepts":["redundancy","normal forms","anomalies"]},"output":{"question":"How can normalization help prevent update anomalies?","expectedConcepts":["update anomalies","consistent data"],"difficulty":"intermediate","questionFormat":"theory"}}
```

Each example must have a **target output**. A list of questions alone teaches question style but does not teach answer grading. For evaluation examples, include human-reviewed scores, feedback, missing concepts and reference answers. For code-output questions, include the exact expected output and preferably verified test results. Do not use model-generated labels as ground truth without reviewing them.

The converter also accepts records with `messages` (chat format), `instruction` + `output`, or `prompt` + `completion`. CSV should have `task`, `input`, `output` columns; `input` and `output` may contain JSON strings. See `data/template.jsonl`.


## 1A. Use the bundled 600-example dataset

The archive includes six seed files under `data/raw/` (100 records each): Java theory, Java output prediction, Java coding, DBMS theory, SQL coding and HR questions. These are starter examples; review correctness and licensing before academic or public use.

From the `training` directory, run the schema-aware converter first:

```powershell
python prepare_mockmate_datasets.py --input-dir data/raw --output data/processed/canonical.jsonl
python prepare_dataset.py --input data/processed/canonical.jsonl --output-dir data/processed/splits
```

Then upload `data/processed/splits/train.jsonl` and `data/processed/splits/validation.jsonl` to Colab as `/content/data/train.jsonl` and `/content/data/validation.jsonl`. Upload the `train_qlora.py` script too.

**Coverage limitation:** these 600 examples primarily teach question/problem generation and reference-answer formats. They do not contain verified student answer + numeric score + feedback labels, and they do not contain real previous-answer/follow-up pairs. They are therefore not sufficient on their own to train reliable answer scoring or adaptive follow-ups. Add a human-reviewed dataset for `evaluate_answer` and `generate_followup` before training those behaviors; never use fabricated scores as ground truth.

## 2. Prepare data on Windows

From the `mockmate` folder in PowerShell:

```powershell
# Put your dataset file in mockmate\training\data\raw\
cd training
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-data.txt
python prepare_dataset.py --input data/raw/interview_dataset.jsonl --output-dir data/processed
```

Replace `interview_dataset.jsonl` with your real filename. If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for that terminal only, then activate again. The script prints counts and creates train/validation/test JSONL files. It removes exact duplicate examples and uses a fixed seed for reproducibility.

**Inspect the split files before training.** Make sure the test split was not copied into the training set and that each output is factually correct.

## 3. Train on Google Colab (GPU)

1. Open a new Google Colab notebook and set **Runtime → Change runtime type → T4 GPU** if offered.
2. Upload the prepared `train.jsonl` and `validation.jsonl` from `data/processed/` into Colab's `/content/data/` folder (create it first). Do not upload private student responses unless you have permission and have removed identifying information.
3. Run:

```python
!pip install -U unsloth datasets trl peft transformers accelerate bitsandbytes
!git clone https://github.com/unslothai/unsloth.git /content/unsloth-src
```

4. Upload this `train_qlora.py` file to `/content/` (or upload the `training` folder), then run:

```python
!python /content/train_qlora.py \
  --train /content/data/train.jsonl \
  --validation /content/data/validation.jsonl \
  --output /content/mockmate-llama-adapter \
  --gguf-output /content/mockmate-llama-gguf \
  --max-steps 100
```

The script loads `meta-llama/Llama-3.2-3B-Instruct`. If the repository is gated, accept Meta's terms on Hugging Face and log in inside Colab with `huggingface_hub.login()`; enter the token in the secure prompt, not in source code. If a T4 is not available or memory runs out, reduce `--max-seq-length` to 1024 and `--batch-size` to 1, or wait for a GPU runtime. 100 steps is a smoke-test run, not proof of model quality; tune steps/epochs based on validation and dataset size.

5. Download `/content/mockmate-llama-gguf/` (it contains a Q4_K_M GGUF file) to your computer. Use Colab's file browser or zip it first:

```python
!zip -r /content/mockmate-llama-gguf.zip /content/mockmate-llama-gguf
```

Then download `mockmate-llama-gguf.zip` from the Colab file pane. Keep the adapter and training logs too, so you can reproduce the model.

## 4. Register the fine-tuned model in Ollama (Windows)

Install/update Ollama, then create a folder such as `mockmate\ai-service\models\mockmate-llama-gguf` and place the `.gguf` file there. In PowerShell:

```powershell
cd ..\ai-service\models\mockmate-llama-gguf
@'
FROM ./mockmate-llama-q4_k_m.gguf
PARAMETER temperature 0.2
PARAMETER num_ctx 4096
'@ | Set-Content -Encoding ascii Modelfile
ollama create mockmate-llama-ft -f Modelfile
ollama run mockmate-llama-ft "Generate a Java interview question about type erasure as JSON."
```

Replace the GGUF filename with the actual exported filename. The model file is several GB; ensure disk space. For best results, preserve the Llama chat template used by the trainer/exporter; Unsloth's GGUF export includes model metadata/template.

## 5. Connect the existing AI service

The existing provider already sends `MODEL_NAME` to Ollama's `/api/generate` endpoint. You normally only need to change `ai-service/.env`:

```env
MODEL_NAME=mockmate-llama-ft
MODEL_ENDPOINT=http://localhost:11434/api/generate
STRICT_AI_MODE=true
```

Restart the FastAPI AI service. Verify `GET http://localhost:8000/health` shows the expected fine-tuned model and active BERT-derived embeddings. `STRICT_AI_MODE=true` makes provider/embedding problems more visible; switch to false only if you intentionally want development fallback behavior. Do not change frontend/backend routes just to swap the model name.

## 6. Test and compare

- Keep `data/processed/test.jsonl` held out; never train on it.
- First smoke-test Ollama with `python smoke_test_ollama.py --model mockmate-llama-ft`.
- Then start the FastAPI service and test existing `/api/ai/generate-question`, `/api/ai/generate-followup`, and `/api/ai/evaluate-answer` routes using the request schemas shown by `http://localhost:8000/docs`.
- Compare base LLaMA and fine-tuned LLaMA on the exact same held-out cases. Record question relevance, follow-up relevance, score agreement with human labels, missing-concept detection and valid JSON rate. Report sample count and do not claim improvement unless results support it.
- Run existing tests from `ai-service`: `python -m unittest discover -s tests -v`.

## 7. Limits and safety

Fine-tuning is not a substitute for retrieval or programmatic checks. Keep the current RAG knowledge base for factual context, BERT embeddings for semantic retrieval, and exact code-output/test-case checks in application logic. A model score is an estimate, not an objective ground truth; calibrate it against human-reviewed examples. Keep train/validation/test splits separate and avoid leaking the same question/answer across splits.
