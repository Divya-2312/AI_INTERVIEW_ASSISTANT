# Manual Test Checklist & Verification Guide

**Document:** AI Interview Assistant — End-to-End Manual Verification Guide  
**Target Environment:** Local Full-Stack Deployment (Chrome, Node Backend, FastAPI AI Service, Ollama, MongoDB)  
**Test Account:** `divyae.ramachandran+mm4@gmail.com` (Password: `Test1234x`)

---

## 1. Pre-Flight System Verification

Before beginning manual tests, ensure all four system services are running and healthy:

1. **MongoDB Service:**
   ```powershell
   Get-Service -Name MongoDB
   # Ensure Status is Running on port 27017
   ```
2. **Ollama Service & Loaded Models:**
   ```powershell
   ollama list
   # Verify 'llama3.2:3b' and 'mockmate-hr100:latest' are present
   ```
3. **AI Service Health Check:**
   - Open browser or execute: `http://localhost:8000/health`
   - Verify JSON output:
     ```json
     {
       "status": "healthy",
       "ollama_connected": true,
       "models": {
         "base": "llama3.2:3b",
         "fine_tuned": "mockmate-hr100:latest",
         "embedding": "all-MiniLM-L6-v2"
       }
     }
     ```
4. **Backend Server:**
   - Active on `http://localhost:5000`
5. **Frontend Client:**
   - Active on `http://localhost:5173`

---

## 2. Test 1: Real Email Delivery & Account Verification

**Objective:** Confirm SMTP email delivery reaches a real Gmail inbox, verify 60s TTL, and test security lockout.

1. **Trigger Real Verification Code:**
   - In browser, go to `http://localhost:5173/login`.
   - Enter unverified email or trigger "Resend Verification Code".
   - Alternatively, execute the diagnostic CLI:
     ```powershell
     cd backend
     npm run test-email divyae.ramachandran+mm4@gmail.com
     ```
2. **Inbox Check:**
   - Open `divyae.ramachandran+mm4@gmail.com` in Google Mail.
   - Check that the email arrives within **10 seconds**.
   - Verify the email body contains a clear 6-digit verification code.
   - Verify the text explicitly states the code expires in **1 minute**.
3. **Acceptance Test (within 60s):**
   - On the verification screen, input the 6-digit code within 45 seconds.
   - Click **Verify Account**.
   - Confirm immediate redirect to login or dashboard with success message.
4. **Rejection Test (after 60s):**
   - Click "Resend Code" (wait 30s if cooldown active).
   - Wait **65 seconds** without submitting.
   - Enter the expired code.
   - Confirm error banner: `Verification code has expired. Please request a new one.` (HTTP 400 `CODE_EXPIRED`).
5. **Lockout Test (5 failed attempts):**
   - Request a fresh code.
   - Intentionally type an incorrect 6-digit code 5 times in a row.
   - Confirm attempts decrement: "4 attempts remaining", "3 remaining", ..., "1 remaining".
   - On 5th wrong attempt, confirm the code is invalidated with `TOO_MANY_ATTEMPTS`.

---

## 3. Test 2: Speech Answer Mode (Web Speech API)

**Objective:** Validate live microphone speech-to-text, real-time transcription, and English audio filtering.

1. **Browser Setup:**
   - Open Google Chrome (recommended for Web Speech API).
   - Navigate to `http://localhost:5173/interview/setup`.
   - Select **HR Interview** track, difficulty **Medium**.
   - Click **Start Interview**.
2. **Microphone Activation:**
   - On Question 1, click the **Microphone** icon button.
   - When Chrome prompts, click **Allow** for microphone access.
   - Verify the recording indicator turns red with a live pulsing wave animation.
3. **Dictation Test:**
   - Speak clearly into the microphone in English:
     > *"In my previous project, our team faced a tight production deadline. I organized a daily standup, prioritized critical blockers, and we delivered two days early."*
   - Verify that transcribed words appear inside the answer textarea in real-time.
   - Verify natural speech pauses do NOT inject stray periods (`.`) in the middle of sentences.
4. **Delivery Metrics Capture (HR Track):**
   - Stop recording after speaking for ~30 seconds.
   - Click **Submit Answer**.
   - Verify in the evaluation response that delivery metrics (words per minute, pause count, latency) were processed by the HR evaluator.

---

## 4. Test 3: One Full Session per Module

Execute one session in each of the 5 interview formats to verify end-to-end functionality:

### A. Java Theory Interview
1. Setup: Technical $\rightarrow$ Java $\rightarrow$ Theory $\rightarrow$ Medium.
2. Verify Question 1 is a conceptual question with no code boilerplate.
3. Type an explanation (e.g. explaining `HashMap` vs `Hashtable`).
4. Click **Submit Answer**.
5. Verify evaluation shows 4 subscores (Accuracy, Correctness, Relevance, Concept Coverage) and overall score is their mean.
6. Verify Solution Viewer expands to show expected concepts and explanation.

### B. Java Coding Interview
1. Setup: Technical $\rightarrow$ Java $\rightarrow$ Coding $\rightarrow$ Easy.
2. Verify Code Workspace loads with:
   - Problem description and parameters.
   - Non-leaked starter code stub (`public class Solution { ... }`).
   - Visible test cases with input and expected output.
3. Write Java implementation in the editor.
4. Click **Run Tests**:
   - Verify test execution output displays in the test runner panel (pass/fail status per test case).
5. Click **Submit Solution**:
   - 100% test cases passed gives Score 100.
   - Big-O analysis displays Time and Space complexity (e.g. $O(N)$ time, $O(1)$ space).

### C. DBMS SQL Interview
1. Setup: Technical $\rightarrow$ DBMS $\rightarrow$ Coding (SQL) $\rightarrow$ Medium.
2. Verify schema viewer displays relational tables and column data types.
3. Verify sample data preview table displays rows.
4. Type standard SQL query in the editor (e.g. `SELECT name FROM employees WHERE salary > 50000;`).
5. Click **Run Query**:
   - Verify query runs against SQLite in-memory sandbox and displays actual result rows.
6. Click **Submit**:
   - Verify deterministic evaluation against expected result dataset.

### D. Java Output Prediction Interview
1. Setup: Technical $\rightarrow$ Java $\rightarrow$ Output Prediction $\rightarrow$ Medium.
2. Verify question displays a self-contained Java code snippet (e.g. loops with arithmetic or string manipulation).
3. Type predicted stdout output into the answer box.
4. Submit answer:
   - If exact match $\rightarrow$ Score $= 100$ (`exact_match`).
   - If wrong output with reasoning explanation $\rightarrow$ Partial credit based on explanation reasoning.
   - If wrong output without explanation $\rightarrow$ Score $= 0$.

### E. HR Behavioral Interview
1. Setup: HR Track $\rightarrow$ All Difficulties.
2. Verify question is drawn from the 100-question curated HR benchmark bank.
3. Answer using STAR framework (Situation, Task, Action, Result).
4. Verify evaluation scores candidate using the fine-tuned HR model (`mockmate-hr100:latest`).

---

## 5. Test 4: Anti-Cheat & Code Workspace Protection

**Objective:** Confirm cheating prevention guards block external code pasting.

1. Navigate to any coding question in an active technical interview.
2. Copy sample code from an external notepad or website (`Ctrl+C`).
3. Click inside the CodeWorkspace Monaco/text editor.
4. Attempt to paste via keyboard shortcut: **Press `Ctrl+V`**.
   - *Expected:* Nothing is pasted into the box.
5. Attempt to paste via mouse: **Right-Click inside editor $\rightarrow$ select "Paste"**.
   - *Expected:* Context menu is blocked, or paste action is intercepted and rejected.
6. Attempt to drag-and-drop text from an external window into the editor.
   - *Expected:* Drag action rejected.
7. Verify manual keyboard typing works normally and without lag.

---

## 6. Test 5: Mid-Session Refresh & State Preservation

**Objective:** Verify that reloading the browser does not lose interview state or advance questions prematurely.

1. Start a new Technical Java session.
2. Answer Question 1 and Question 2 normally.
3. When Question 3 appears, type a partial answer into the textarea:
   > *"Polymorphism in Java is achieved through method overloading and..."*
4. **Press `F5` or click Browser Reload.**
5. Observe the restored screen:
   - *Expected:* Session reloads at **Question 3 of 10**.
   - *Expected:* Total questions count remains 10.
   - *Expected:* Answered count remains 2.
   - *Expected:* Session does NOT skip to Question 4 or reset to Question 1.
6. Complete typing answer for Question 3 and submit.
   - *Expected:* Evaluation succeeds, and session advances to Question 4.

---

## 7. Test 6: AI Evaluation Engine Failure & Retry Handling (FIX 1)

**Objective:** Confirm HTTP 503 `EVALUATION_UNAVAILABLE` does not save answers, increase attempt counts, or lose candidate input.

1. Open active interview on Question 1.
2. Type an answer in the box:
   > *"Encapsulation bundles data and methods operating on that data within a single unit."*
3. **Simulate AI service outage:**
   - In terminal, temporarily terminate the uvicorn process or disconnect Ollama:
     ```powershell
     # Stop AI service
     ```
4. Click **Submit Answer**:
   - *Expected:* Browser displays amber error banner:
     `"evaluation engine unavailable, please retry"` (HTTP 503).
   - *Expected:* A **Retry** button appears beside the message.
   - *Expected:* The candidate's typed answer is **NOT cleared** from the text box.
   - *Expected:* The question does NOT advance; Question 1 remains active.
   - *Expected:* The overall score is NOT set to 0%.
5. **Restore AI service:**
   - Restart the AI service process:
     ```powershell
     cd ai-service
     python -m uvicorn app.main:app --port 8000
     ```
6. Click the **Retry** button in the UI:
   - *Expected:* Evaluation succeeds with HTTP 200.
   - *Expected:* Answer document is saved in MongoDB with genuine score.
   - *Expected:* Session advances cleanly to Question 2.

---

## 8. Test 7: Dashboard, Results, & History Cascade Purge

**Objective:** Verify results calculation, session history display, and cascade deletion of all child records.

1. Complete all 10 questions of an interview session (or end interview).
2. Verify redirect to `/result/:id`:
   - *Expected:* Performance assessment card shows calculated score.
   - *Expected:* If candidate attended 10/10 questions, score is the direct mean.
   - *Expected:* If candidate attended $K < 10$ questions, score reflects $(total\_points / 10)$.
   - *Expected:* Strengths, weaknesses, recommendations, and question breakdown display.
3. Click **Dashboard** or navigate to `/history`:
   - Verify the completed session is listed with correct track, subject, score, and date.
4. Click the **Delete** (trash can) button on the session card:
   - Confirm deletion dialog.
   - Confirm session is immediately removed from the history view.
5. **Database Cascade Verification:**
   - Verify in MongoDB:
     ```javascript
     db.interviews.findOne({ _id: ObjectId("<deleted_id>") }); // null
     db.answers.find({ interviewId: ObjectId("<deleted_id>") }); // empty (0 records)
     db.results.findOne({ interviewId: ObjectId("<deleted_id>") }); // null
     ```
   - All child `Answer` and `Result` documents are purged along with the parent `Interview`.
