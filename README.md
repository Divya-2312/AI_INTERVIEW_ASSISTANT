# AI Interview Assistant (MockMate AI)

An AI-powered technical and behavioral interview preparation platform featuring real-time evaluation, deterministic code execution sandboxes, adaptive follow-ups, and interactive feedback.

---

## 🌟 Core Features

- **Technical Tracks**:
  - **Java Coding & DBMS SQL Coding**: Self-contained coding problems with deterministic in-memory SQLite sandbox (for SQL) and reflection-based JVM runner (for Java).
  - **Output Prediction**: Dynamic code snippet tracing and execution simulation.
  - **Theory Evaluation**: Semantic concept coverage, correctness, communication, and relevance grading.
- **HR & Behavioral Simulation**:
  - Fine-tuned evaluation on behavioral questions with automatic relevance gating (off-topic detection).
- **Enterprise-Grade Authentication**:
  - Secure signup with email verification.
  - Access token + rotating `httpOnly` refresh tokens.
  - 6-digit verification code for password resets.
  - Rate limiting and brute-force lockout protection.

---

## 🏗️ Repository Architecture

```
AI_INTERVIEW_ASSISTANT/
├── ai-service/             # FastAPI AI Engine (Python)
│   ├── app/                # LLaMA provider, RAG, evaluators, code executor
│   ├── knowledge/          # Domain knowledge base for RAG retrieval
│   └── requirements.txt    # Python dependencies
├── backend/                # REST API & Orchestration (Node.js / Express)
│   ├── controllers/        # Interview, Auth, Question, and Result controllers
│   ├── models/             # Mongoose schemas (User, Interview, Answer, Result)
│   ├── services/           # Interview engine, AI service client, email service
│   └── package.json        # Backend dependencies
├── frontend/               # Single Page Application (React / Vite)
│   ├── src/                # UI components, pages, state context, styles
│   └── package.json        # Frontend dependencies
├── training/               # LLaMA QLoRA fine-tuning datasets and scripts
│   ├── data/               # Raw & processed JSONL datasets
│   └── MockMate_LLaMA_Fine_Tuning.ipynb # Google Colab fine-tuning notebook
├── HOW_TO_RUN.md           # Operational guide & verification steps
└── FINAL_MODEL_AUDIT.md    # Model architecture & evaluation report
```

---

## 📋 Prerequisites

Before running the project locally, ensure you have:
1. **Node.js** (v18 or higher) & **npm**
2. **Python** (v3.10 to v3.13)
3. **MongoDB** (running locally on port `27017`)
4. **Ollama** (running locally on port `11434`)
   ```bash
   ollama pull llama3.2:3b
   ```
5. *(Optional)* **Java JDK** (`javac` and `java` on system PATH for executing Java coding sandboxes).

---

## 🚀 Step-by-Step Setup & Execution

### 1. Configure Environment Files

Create the local `.env` files for backend and frontend:

#### Backend: `backend/.env`
```env
PORT=5000
MONGODB_URI=mongodb://localhost:27017/ai_interview_assistant
CLIENT_URL=http://localhost:3000
AI_SERVICE_URL=http://localhost:8000/api/ai

# JWT Secrets
JWT_SECRET=super_secret_jwt_access_key_12345
JWT_REFRESH_SECRET=super_secret_jwt_refresh_key_67890

# SMTP Email Configuration (Optional in Dev Mode: prints reset codes to terminal)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=
SMTP_PASS=
MAIL_FROM="AI Interview Assistant" <no-reply@ai-interview-assistant.com>
```

#### Frontend: `frontend/.env`
```env
VITE_API_URL=http://localhost:5000/api
```

---

### 2. Start the AI Service (FastAPI)

```bash
cd ai-service
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
*Health check:* `http://localhost:8000/health`

---

### 3. Start the Backend API (Node / Express)

Open a new terminal:
```bash
cd backend
npm install
npm run dev
```
*Health check:* `http://localhost:5000/api/health`

---

### 4. Start the Frontend (React / Vite)

Open a new terminal:
```bash
cd frontend
npm install
npm run dev
```
*Application URL:* `http://localhost:3000`

---

## 🧪 Running Automated Tests

- **Backend Tests (40 assertions)**:
  ```bash
  cd backend
  npm test
  ```
- **AI Service Sandbox & Evaluation Tests (45 tests)**:
  ```bash
  cd ai-service
  python -m unittest discover -s tests -v
  ```
- **Frontend Production Build**:
  ```bash
  cd frontend
  npm run build
  ```

---

## 🔒 Security & Privacy Notice
All `.env` files, production secrets, and large model binary weights (`*.gguf`) are strictly excluded via `.gitignore` to protect credentials and maintain repository performance.
