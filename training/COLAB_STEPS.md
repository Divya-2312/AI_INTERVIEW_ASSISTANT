# AI Interview Assistant - 1-Click Google Colab Fine-Tuning Guide

This step-by-step guide explains how to fine-tune LLaMA 3.2 3B using Google Colab's free GPU runtime, export the GGUF model artifact, and register it locally with Ollama.

---

## Step 1: Open Google Colab and Enable GPU
1. Go to [Google Colab](https://colab.research.google.com/).
2. Click **File > Upload notebook** and select `mockmate/training/MockMate_LLaMA_Fine_Tuning.ipynb`.
3. In Colab, click **Runtime > Change runtime type**.
4. Under **Hardware accelerator**, select **T4 GPU** (or A100/V100 if available) and click **Save**.

---

## Step 2: Run Notebook Cells Sequentially
Run each cell in order by pressing `Shift + Enter` or clicking the play icon on each cell:

1. **Cell 1 (GPU & Environment Check)**: Verifies that CUDA GPU is active (`nvidia-smi`).
2. **Cell 2 (Install Dependencies)**: Installs `unsloth`, `transformers`, `trl`, `peft`, `bitsandbytes`, and `accelerate`.
3. **Cell 3 (Hugging Face Login)**: Paste your Hugging Face access token when prompted (required for gated LLaMA 3.2 weights).
4. **Cell 4 (Upload Datasets)**: Upload `train.jsonl` and `validation.jsonl` from `mockmate/training/data/processed/splits/`.
5. **Cell 5 (Model Initialization & LoRA Setup)**: Loads `unsloth/Llama-3.2-3B-Instruct` with 4-bit quantization and configures QLoRA adapters.
6. **Cell 6 (Run Fine-Tuning)**: Executes 3 full epochs of training (computing total steps automatically).
7. **Cell 7 (Export Adapter & GGUF Q4_K_M)**: Saves the LoRA adapter and exports `mockmate-llama-q4_k_m.gguf`.
8. **Cell 8 (Package & Download)**: Calculates SHA256 hashes, creates `train_run.json`, zips the artifacts into `mockmate_finetuned_artifacts.zip`, and downloads it to your computer.

---

## Step 3: Place GGUF Artifact in Repo
1. Extract `mockmate_finetuned_artifacts.zip` on your computer.
2. Copy `mockmate-llama-q4_k_m.gguf` into:
   ```text
   mockmate/ai-service/models/mockmate-llama-gguf/mockmate-llama-q4_k_m.gguf
   ```

---

## Step 4: Register Fine-Tuned Model in Ollama (Windows)
Open PowerShell in the `mockmate/` directory and run:

```powershell
cd ai-service\models\mockmate-llama-gguf
ollama create mockmate-llama-ft -f Modelfile
```

Verify registration:
```powershell
ollama list
```
You should see `mockmate-llama-ft` listed with its distinct size and SHA256 hash.

---

## Step 5: Evaluate Base Model vs Fine-Tuned Model
Run `evaluate_model.py` to compare output JSON valid rate and schema accuracy on the test set:

1. Evaluate base model:
   ```powershell
   python training/evaluate_model.py --model llama3.2:3b
   ```
2. Evaluate fine-tuned model:
   ```powershell
   python training/evaluate_model.py --model mockmate-llama-ft
   ```

---

## Step 6: Verify End-to-End Pipeline
Start the FastAPI AI service:
```powershell
cd ai-service
uvicorn app.main:app --port 8000 --reload
```

In another terminal, run the pipeline verification:
```powershell
python scripts/verify_finetuned_pipeline.py
```
If all 5 audit checks show `[PASS]`, the fine-tuned model is fully verified and active!
