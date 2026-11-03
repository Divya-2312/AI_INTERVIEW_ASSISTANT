# Confirmed Facts & Technical Specifications

**Document:** Verification Evidence Pack  
**Last Verified:** 2026-10-30T04:47:00+05:30  
**Repository:** AI Interview Assistant (MockMate AI)

---

## 1. Environment & Software Versions

All versions below are directly inspected from the host execution environment:

| Component | Verified Version | Environment Path / Tool |
|-----------|:----------------:|-------------------------|
| **Operating System** | Windows 11 Home (x86_64) | PowerShell 5.1 / Windows Host |
| **Node.js** | `v24.19.0` | `node -v` |
| **npm** | `11.1.0` | `npm -v` |
| **Python** | `3.13.15` | `python --version` |
| **Ollama** | `0.40.12` | `ollama --version` |
| **PyTorch** | `2.14.0+cpu` | `python -c "import torch; print(torch.__version__)"` |
| **Sentence-Transformers** | `6.0.1` | `python -c "import sentence_transformers; print(sentence_transformers.__version__)"` |
| **FastAPI** | `0.141.1` | `python -c "import fastapi; print(fastapi.__version__)"` |
| **Pydantic** | `2.13.4` | `python -c "import pydantic; print(pydantic.__version__)"` |
| **Express** | `^4.18.2` | `backend/package.json` |
| **Mongoose** | `^7.4.2` | `backend/package.json` |
| **React** | `^18.2.0` | `frontend/package.json` |
| **Vite** | `^4.4.5` | `frontend/package.json` |
| **JDK (Java Sandbox)** | Java 17+ (Temurin / Oracle) | `javac -version`, `java -version` |
| **Database** | MongoDB 6.0+ | `localhost:27017` |

---

## 2. Models & Routing Specifications

| Model Identifier | Purpose / Assigned Track | Runtime Provider | Ollama Manifest Status |
|------------------|--------------------------|------------------|------------------------|
| `llama3.2:3b` | Base Model: Java Theory, DBMS Theory, Output Prediction, Java Coding, SQL Coding | Ollama (Local) | Pulled & Active |
| `mockmate-hr100:latest` | Fine-Tuned Model: HR Behavioral Evaluation & Big-O Code Complexity Analysis | Ollama (Local) | Pulled & Active |
| `all-MiniLM-L6-v2` | Sentence Embedding Model: Semantic deduplication (0.88 SBERT threshold) & concept coverage matching | Local HuggingFace / PyTorch CPU | Loaded in memory |

### Strict Model Routing Rules
1. **HR Evaluation:** Evaluated strictly via `mockmate-hr100:latest` (or offline fallback heuristic if Ollama is unavailable). Never uses base LLaMA.
2. **Big-O Complexity:** Evaluated strictly via `mockmate-hr100:latest` with a static heuristic regex fallback (`_estimate_code_complexity_heuristic`).
3. **Technical Tracks (Java / DBMS):** Evaluated strictly via `llama3.2:3b` + execution sandbox + BERT embeddings.
4. **Catalogue Fallback:** Used strictly as the LAST resort when model generation fails or exceeds bounded limits. Labeled honestly with `source: "catalogue_fallback"`, `modelUsed: "catalogue_fallback"`.

---

## 3. Training & Evaluation Datasets

| Dataset / Asset | Sample Count | Format | Primary Objective |
|-----------------|:------------:|:------:|-------------------|
| **Fine-Tuning Dataset** | 1,488 samples (1,490 prior to exact dedup) | JSONL / GGUF | HR behavioral question evaluation (STAR rubric) and code Big-O analysis |
| **Train / Validation Split** | ~80% Train (1,190), ~20% Eval (298) | Split JSONL | Model loss convergence and generalization validation |
| **Curated HR Question Bank** | 100 questions | JSON | Benchmark behavioral questions across 6 categories (Introduction, Behavioral, Leadership, Problem Solving, Adaptability, Culture Fit) |
| **Java Theory Catalogue** | 100 questions | JSON | Curated conceptual questions with reference answers and concept anchors |
| **DBMS Theory Catalogue** | 100 questions | JSON | Curated relational database questions with reference answers |
| **Java Output Prediction Bank** | 100 snippets | JSONL | Self-contained, deterministic Java snippets with pre-verified stdout outputs |
| **Java Coding Problem Bank** | 12 problems | Python Dict | Hand-curated algorithmic problems (easy, medium, hard) with starter code, leak guards, and reference solutions |
| **SQL Problem Bank** | 9 problems | Python Dict | Hand-curated relational schemas, sample rows, and canonical SELECT queries |
| **Self-Test Validation Set** | 60 cases | JSON | Developer-created balanced test cases covering theory, coding, SQL, and HR |

---

## 4. Scoring Formulas & Named Constants

### Question-Level Scoring Formula
$$\text{Score} = \text{round}\left(\frac{\text{Accuracy} + \text{Correctness} + \text{Relevance} + \text{Concept Coverage}}{4}\right)$$

- Each dimension is bounded between $0$ and $100$.
- Rounding rule: Symmetric half-up rounding (`round_half_up(val) = math.floor(val + 0.5)`).
- Subscores:
  - **Concept Coverage:** Ratio of required concept anchors found in candidate answer via keyword matching and SBERT semantic embeddings.
  - **Correctness:** Factual accuracy measured against reference answer / model rubric. Contradiction cues immediately force Correctness to $0$.
  - **Relevance:** Semantic alignment between the question and candidate answer.
  - **Accuracy:** Overall precision of the response.

### Interview Session Overall Score
$$\text{Session Score} = \text{round}\left(\frac{\sum_{i=1}^{N} \text{Score}_i}{10}\right)$$

- Every interview session enforces exactly $10$ questions.
- If a candidate attends $K < 10$ questions, the remaining $10 - K$ questions contribute $0$ points.
- Example: 1 question attended with $100\%$ score yields a session score of $10\%$.

### Specific Coding & Prediction Rules
- **Java Coding & SQL:** 100% deterministic execution in sandbox.
  - All test cases pass $\rightarrow$ Score $= 100$.
  - 0 test cases pass $\rightarrow$ Score $= 0$.
  - Compile / syntax error $\rightarrow$ Score $= 0$.
- **Output Prediction:**
  - Exact match against stdout $\rightarrow$ Score $= 100$ (`source: "exact_match"`).
  - Wrong output without valid reasoning explanation $\rightarrow$ Score $= 0$ (`source: "rule"`).

### System Timeouts & Bounded Waiting Constants
- `MAX_CODING_GENERATION_ATTEMPTS = 2`
- `MAX_CODING_GENERATION_TIMEOUT_SEC = 25`
- `VERIFICATION_CODE_TTL_SEC = 60` (1 minute)
- `VERIFICATION_COOLDOWN_SEC = 30`
- `VERIFICATION_MAX_ATTEMPTS = 5`
- `PASSWORD_RESET_CODE_TTL_SEC = 600` (10 minutes)
- `JWT_EXPIRY_MINUTES = 15`
- `ACCOUNT_LOCKOUT_MINUTES = 15` (after 5 failed logins)

---

## 5. Test Counts Summary

| Suite / Component | Total Tests | Passed | Failures | Pass Rate |
|-------------------|:-----------:|:------:|:--------:|:---------:|
| **Backend Suite (`npm test`)** | 176 | 176 | 0 | **100.0%** |
| **Frontend Production Build** | 1 | 1 | 0 | **100.0%** |
| **AI Service Unit Tests** | 149 | 138 | 11 | **92.6%** |
| *Total All Tests* | **326** | **315** | **11** | **96.6%** |

*Note on AI Service Failures:*
- 4 failures in `test_question_quality.py` are legacy prototype assertions expecting an old 80/20 rubric instead of the agreed 100/0 deterministic rule.
- 7 failures in `test_question_repetition.py` occur because live model-generated theory questions return `id: None`, triggering duplicate ID checks in the test script.

---

## 6. 60-Case Self-Test Confusion Matrix & Accuracy

Results from executing `verification_runs/run_validation_cases.py` on `validation_cases.json`:

| Metric | Measured Value | Formula / Definition |
|--------|:--------------:|----------------------|
| **Total Labeled Cases** | 60 | Defined in `validation_cases.json` |
| **Correct Decisions** | 50 | Model score $\ge 50$ matches expected pass, or $< 50$ matches expected fail |
| **Overall Accuracy** | **83.3%** | $50 / 60$ |
| **True Positives (TP)** | 32 | Correctly predicted as satisfactory ($\ge 50$) |
| **True Negatives (TN)** | 18 | Correctly predicted as unsatisfactory ($< 50$) |
| **False Positives (FP)** | 4 | Unsatisfactory answers scored $\ge 50$ |
| **False Negatives (FN)** | 6 | Satisfactory answers scored $< 50$ |
| **Precision** | **88.9%** | $32 / (32 + 4)$ |
| **Recall** | **84.2%** | $32 / (32 + 6)$ |
| **F1 Score** | **86.5%** | $2 \times (0.889 \times 0.842) / (0.889 + 0.842)$ |

---

## 7. Timing & Benchmark Measurements

| Operation / Benchmark | Measured Time | Conditions / Notes |
|-----------------------|:-------------:|-------------------|
| **Frontend Production Build** | 2.42s | `npm run build` with Vite |
| **Backend Test Suite (176 tests)** | 11.8s | In-memory MongoDB + supertest |
| **AI Evaluation (Offline Rule / Sandbox)** | 45ms – 120ms | Deterministic sandbox execution |
| **AI Evaluation (SentenceTransformer)** | 180ms – 350ms | `all-MiniLM-L6-v2` PyTorch CPU |
| **Catalogue Reference Solution Batch** | 134.3s | 12 Java solutions + 100 output prediction snippets |
| **Live Ollama Inference (Base LLaMA)** | 1.8s – 4.5s | `llama3.2:3b` on local host |
| **Live Ollama Inference (Fine-Tuned HR)** | 2.2s – 4.8s | `mockmate-hr100:latest` without VRAM contention |
| **Live Ollama Model Hot-Swap Delay** | 8s – 25s | Windows GPU single-model swap overhead |

---

## 8. Non-Existent Features (Clear Anti-Claims)

The following capabilities are explicitly NOT implemented in this platform:

1. **Computer Vision / Facial Tracking:** The platform does NOT perform real-time gaze tracking, emotion detection, or webcam facial analysis. The interview evaluates typed code/text and audio speech transcripts.
2. **Native Mobile Applications:** There are no standalone native iOS (.ipa) or Android (.apk) client apps. The system is a web application accessible via modern desktop and mobile browsers.
3. **Enterprise SAML / OAuth SSO:** Single Sign-On (e.g. Google Sign-In, Okta, Active Directory) is not enabled. Authentication is handled natively through verified email and bcrypt-hashed passwords.
4. **Dynamic SQL Schema Generation by Model:** The model does not generate arbitrary arbitrary database schemas at runtime; SQL questions utilize pre-verified relational schemas and sample datasets.
5. **Prefetch for HR Interviews:** Background prefetch generation is explicitly disabled for HR sessions; HR questions are instantly selected from the pre-verified 100-question benchmark bank.
