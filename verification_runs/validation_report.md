# MockMate AI — Comprehensive Validation Report

> **Validation Report Metadata**  
> **Timestamp:** 2026-10-29T23:42:00+05:30  
> **Environment:** Windows (Local Dev Daemons: FastAPI port 8000, Node Express port 5000, Ollama port 11434)  
> **Constraint Verification:** Validation ONLY. Zero application code, zero threshold values, zero system prompts, and zero test files were modified. Zero `.env` files or secrets were read or printed. All data reported below originates strictly from executed measurements.

---

## 1. Test Suite Diff and Execution Audit

### 1.1 Git Diff Analysis on Test Files
A comprehensive `git diff` was executed across all test files in `ai-service/tests/` and `backend/tests/`. Every changed assertion is catalogued below with file, line, previous assertion, new assertion, and technical rationale:

| File | Line(s) | Old Assertion | New Assertion | Rationale | Weakened / Removed? |
|---|---|---|---|---|---|
| `ai-service/tests/test_model_config.py` | Line 17 | `self.assertEqual(settings.FINE_TUNED_MODEL_NAME, os.getenv("FINE_TUNED_MODEL_NAME", "mockmate-llama-ft").strip())` | `self.assertEqual(settings.FINE_TUNED_MODEL_NAME, os.getenv("FINE_TUNED_MODEL_NAME", "mockmate-hr100").strip())` | Aligns test expectation with deployed Ollama fine-tuned model name (`mockmate-hr100`). | **No.** Remains strict equality. |
| `ai-service/tests/test_hr_evaluation.py` | Line 59 | `calculate_hr_overall(..., res.communication or 0.0)` | `calculate_hr_overall(..., res.conceptCoverage or 0.0)` | Reflects canonical 4-component HR scoring contract (correctness, relevance, accuracy, conceptCoverage) where communication is preserved as candidate feedback. | **No.** Verifies canonical formula. |
| `ai-service/tests/test_hr_evaluation.py` | Line 88 | `calculate_hr_overall(..., res.communication or 0.0)` | `calculate_hr_overall(..., res.conceptCoverage or 0.0)` | Same as line 59. | **No.** Verifies canonical formula. |
| `ai-service/tests/test_evaluation_rules.py` | Line 144 | `self.assertNotIn("accuracy", res)` | `self.assertIn("accuracy", res)` | Aligns with unified 4-metric contract; theory questions now explicitly calculate and expose `accuracy`. | **No.** Strengthened (checks existence and type). |
| `ai-service/tests/test_evaluation_rules.py` | Line 207 | `self.assertNotIn("accuracy", res)` | `self.assertEqual(res["score"], int(sum(percents) / 4 + 0.5)); self.assertIn("accuracy", res)` | Enforces exact 4-metric arithmetic mean invariant. | **No.** Strengthened. |
| `ai-service/tests/test_evaluation_rules.py` | Line 233 | `self.assertIn("average", res["scoreReason"])` | *(Removed)* | Score explanation text was refactored for natural candidate feedback, eliminating internal implementation wording ("average"). Arithmetic score correctness is asserted numerically on lines 207 & 210. | **Removed assertion on internal string keyword.** Numeric assertions remain intact. |
| `ai-service/tests/test_evaluation_rules.py` | Lines 284–285 | `self.assertLess(res.score, baseline["score"])` | `self.assertEqual(res.score, baseline["score"])` and `calculate_hr_overall(..., res.conceptCoverage)` | Speech delivery penalty is applied to qualitative communication feedback rather than deducting raw points from candidate's semantic content score. | **Modified.** Asserts score preservation under delivery penalty. |
| `ai-service/tests/test_evaluation_rules.py` | Line 303 | `self.assertIsNone(res.accuracy)` | `self.assertIsNotNone(res.accuracy)` | Verifies that HR evaluation computes and returns canonical accuracy. | **No.** Strengthened. |
| `backend/tests/auth.test.js` | N/A | *(None modified)* | Purely additive: Section 15 (1-min verification TTL, 5-attempt lockout, 60s cooldown, generic reset response, 10-min password reset TTL) & Section 10 (account deletion and cascade purge). | **No.** Zero assertions removed or weakened. |

---

### 1.2 Test Execution Results

#### AI-Service Tests (`unittest` / Python 3.11)
All 11 test suites under `ai-service/tests/` were executed cleanly:

| Test File | Total Tests | Passed | Failed | Errors | Duration |
|---|---|---|---|---|---|
| `test_evaluation_rules.py` | 48 | 48 | 0 | 0 | 18.06s |
| `test_hr_bigo_isolation.py` | 8 | 8 | 0 | 0 | 1.95s |
| `test_hr_evaluation.py` | 3 | 3 | 0 | 0 | 4.10s |
| `test_model_config.py` | 10 | 10 | 0 | 0 | 18.15s |
| `test_non_theory_unaffected.py` | 4 | 4 | 0 | 0 | 25.43s |
| `test_theory_overall_score.py` | 3 | 3 | 0 | 0 | 22.75s |
| `test_code_executor.py` | 13 | 13 | 0 | 0 | 11.23s |
| `test_catalog_verification.py` | 9 | 9 | 0 | 0 | 0.45s |
| `test_prompt_alignment.py` | 10 | 10 | 0 | 0 | 0.02s |
| `test_question_repetition.py` | 14 | 14 | 0 | 0 | 60.40s |
| `test_question_quality.py` | 45 | 45 | 0 | 0 | 75.14s |
| **Total AI-Service Tests** | **167** | **167** | **0** | **0** | **237.68s** |

#### Backend Tests (`npm test` / Mocha & Node.js)
All backend test suites were executed cleanly:

| Test File | Total Tests | Passed | Failed | Errors | Duration |
|---|---|---|---|---|---|
| `tests/auth.test.js` | 152 | 152 | 0 | 0 | ~16s |
| `tests/client_result_tags.test.js` | 1 | 1 | 0 | 0 | ~1s |
| `tests/reference_answer_handling.test.js` | 1 | 1 | 0 | 0 | ~1s |
| `tests/theory_score_preservation.test.js` | 2 | 2 | 0 | 0 | ~1s |
| **Total Backend Tests** | **156** | **156** | **0** | **0** | **~19s** |

---

## 2. HR Failure Path Analysis (`mockmate-hr100` Unreachable)

When the fine-tuned HR model `mockmate-hr100` or the Ollama daemon is unreachable, the system executes the following failure sequence:

### 2.1 Exact AI Service Response Payload
In `ai-service/app/models/llama_provider.py` (lines 4924–4950 and 4955–4980), all network/daemon exceptions during HR evaluation are caught in an explicit `try...except` block. The AI service responds with HTTP status 200 and the following JSON:

```json
{
  "score": 0,
  "relevance": 0.0,
  "correctness": 0.0,
  "conceptCoverage": 0.0,
  "concept_coverage": 0.0,
  "accuracy": 0.0,
  "communication": 0.0,
  "feedback": "evaluation engine unavailable, please retry",
  "scoreReason": "evaluation engine unavailable, please retry",
  "error": "evaluation engine unavailable, please retry",
  "source": "error",
  "modelUsed": "mockmate-hr100",
  "strengths": [],
  "weaknesses": [
    "evaluation engine unavailable, please retry"
  ]
}
```

### 2.2 Backend Handling in `interviewEngine.js` & `interviewController.js`

1. **Invocation (`backend/services/interviewEngine.js:364–388`)**:
   `evaluateCandidateAnswer(session, currentQuestion, answerText, durationSeconds)` calls `aiService.evaluateAnswer(...)`.
2. **Result Reception (`backend/services/interviewEngine.js:424–485`)**:
   The response returns HTTP 200, so `aiService.evaluateAnswer` resolves successfully without throwing an exception.
   The backend reads:
   ```javascript
   const score = typeof evalResult.score === 'number' ? evalResult.score : 0;
   ```
   **Crucial Finding**: Neither `interviewEngine.js` nor `interviewController.js` inspects `evalResult.source === "error"` or `evalResult.error`.
3. **Storage as an Answer (`backend/services/interviewEngine.js:489`)**:
   ```javascript
   const answer = await Answer.create({
     interviewId: session._id,
     questionId: currentQuestion.id,
     userId: session.userId,
     questionText: currentQuestion.question,
     answerText,
     score, // <-- Saved into MongoDB with score: 0
     feedback: evalResult.feedback,
     ...
   });
   ```
   **The failed evaluation is permanently saved in the database as an Answer record with `score: 0`.**
4. **Session Score Accumulation (`backend/services/interviewEngine.js:532–560`)**:
   ```javascript
   session.attemptedCount += 1;
   session.scores.push(score); // pushes 0 into array
   session.overallScore = Math.round(
     session.scores.reduce((a, b) => a + b, 0) / session.scores.length
   );
   ```
   **The 0 is counted in the overall session average score, dragging the candidate's average down.**
5. **Session Progression (`backend/services/interviewEngine.js:570–620` & `backend/controllers/interviewController.js:195–320`)**:
   The controller returns HTTP 200 with the next question or interview completion summary.

**Conclusion**: The failure path is **saved as an Answer with score 0**, is **counted in the candidate's session score average**, and is **NOT surfaced as a client-retryable error**. The candidate is penalized 0 points and advanced to the next question.

---

## 3. Question Generation Routing Proof

The 4 question generation routes were executed against the live AI service endpoint (`http://localhost:8000/api/ai/generate-question`):

| Question Type | Request Parameters | HTTP Status | Response `modelUsed` | Response `source` | Time | Generated Question Title / Snippet |
|---|---|---|---|---|---|---|
| **DBMS Theory** | `subject: "dbms"`, `questionFormat: "theory"`, `difficulty: "medium"` | 200 OK | `"llama3.2:3b"` | `"model"` | 18.32s | *"Explain the concepts of candidate keys, primary keys, and foreign keys in relational databases..."* |
| **Output-Prediction** | `subject: "java"`, `questionFormat: "output_prediction"`, `difficulty: "medium"` | 200 OK | `"llama3.2:3b"` | `"model"` | 11.72s | *"Consider the following Java code: ... What is the exact output?"* |
| **Java Coding** | `subject: "java"`, `questionFormat: "coding"`, `difficulty: "medium"` | 200 OK | `"verified_adaptive_catalog"` | `"model"` | 74.69s | *"Two Sum Problem"* (Dual-solution verification caught non-deterministic LLaMA output and routed to guaranteed verified problem) |
| **SQL Coding** | `subject: "dbms"`, `questionFormat: "coding"`, `difficulty: "medium"`, `language: "sql"` | 200 OK | `"verified_adaptive_catalog"` | `"model"` | 50.29s | *"Customers with No Placed Orders"* (Dual-solution verification caught empty row generation and routed to guaranteed verified schema) |

---

## 4. Independent Measurement (60 Fixed Cases)

### 4.1 Methodology & Integrity Verification
- **Cases File**: `verification_runs/validation_cases.json`
- **Pre-Run Recorded SHA-256**: `2650a47826e906cfab0098492f57c06155b936522d76654477c3f9fe0a8dc5cd`
- **Post-Run Verified SHA-256**: `2650A47826E906CFAB0098492F57C06155B936522D76654477C3F9FE0A8DC5CD` *(Zero alterations after recording)*
- **Composition**:
  - 15 Java Theory cases
  - 15 DBMS Theory cases
  - 15 HR Behavioral cases
  - 15 Mixed Coding / SQL / Output-Prediction cases (5 Java code, 5 SQL, 5 output prediction)
- **Answer Diversity**: Catalogue reference answers (good), half-correct answers, wrong-topic/unrelated answers, and empty answers spread across cases.
- **Pass Mark Threshold**: 50 / 100.
- **Label**: `self-test, 60 cases, written by the development agent` *(not candidate accuracy)*.

---

### 4.2 Confusion Matrix and Evaluation Metrics

| Module (self-test) | Cases | TP | FP | TN | FN | Precision | Recall | F1 Score | Accuracy |
|---|---|---|---|---|---|---|---|---|---|
| **DBMS Theory** | 15 | 4 | 2 | 8 | 1 | 66.7% | 80.0% | 72.7% | **80.0%** |
| **Java Theory** | 15 | 5 | 2 | 8 | 0 | 71.4% | 100.0% | 83.3% | **86.7%** |
| **HR Behavioral** | 15 | 5 | 0 | 10 | 0 | 100.0% | 100.0% | 100.0% | **100.0%** |
| **Java Coding** | 5 | 3 | 0 | 2 | 0 | 100.0% | 100.0% | 100.0% | **100.0%** |
| **SQL** | 5 | 3 | 0 | 2 | 0 | 100.0% | 100.0% | 100.0% | **100.0%** |
| **Output-Prediction** | 5 | 2 | 0 | 3 | 0 | 100.0% | 100.0% | 100.0% | **100.0%** |
| *Mixed Subtotal (Code/SQL/Output)* | *15* | *8* | *0* | *7* | *0* | *100.0%* | *100.0%* | *100.0%* | ***100.0%*** |
| **OVERALL SYSTEM** | **60** | **22** | **4** | **33** | **1** | **84.6%** | **95.7%** | **89.8%** | **91.7%** |

---

### 4.3 Detailed Audit of Every Wrong Decision (5 Total)

Out of 60 test cases, exactly 5 decisions diverged from the expected pass/fail boundary (at pass mark = 50):

1. **`JAVA_TH_06`** — *Java Theory: HashMap vs ConcurrentHashMap (Half-Correct)*
   - **Expected:** FAIL (`expected_pass: false`)
   - **Actual Score:** **67** (`actual_pass: true`)
   - **Evaluated By:** `llama3.2:3b`
   - **Diagnostic:** Candidate stated that HashMap is non-synchronized while ConcurrentHashMap is thread-safe using locking, but omitted segment locking/CAS. LLaMA 3.2 3B awarded partial credit across accuracy and relevance that summed above the 50 pass threshold.

2. **`JAVA_TH_12`** — *Java Theory: Pass by Value (Myth Claim / Half-Correct)*
   - **Expected:** FAIL (`expected_pass: false`)
   - **Actual Score:** **88** (`actual_pass: true`)
   - **Evaluated By:** `llama3.2:3b`
   - **Diagnostic:** Common misconception test. Candidate claimed *"Java passes primitives by value, but objects are passed by reference"*. While technically false (Java is strictly pass-by-value of object references), LLaMA 3.2 3B treated the explanation favorably due to keyword similarity with textbook references.

3. **`DBMS_TH_02`** — *DBMS Theory: ACID Properties (Half-Correct)*
   - **Expected:** FAIL (`expected_pass: false`)
   - **Actual Score:** **72** (`actual_pass: true`)
   - **Evaluated By:** `llama3.2:3b`
   - **Diagnostic:** Candidate accurately described Atomicity and Consistency, but completely omitted Isolation and Durability. The evaluator awarded 72%, passing an incomplete definition.

4. **`DBMS_TH_06`** — *DBMS Theory: Clustered vs Non-Clustered Indexes (Half-Correct)*
   - **Expected:** FAIL (`expected_pass: false`)
   - **Actual Score:** **75** (`actual_pass: true`)
   - **Evaluated By:** `llama3.2:3b`
   - **Diagnostic:** Candidate gave an intuitive high-level explanation without mentioning physical row sorting on disk or non-clustered row pointer mechanics. The model scored it generously at 75%.

5. **`DBMS_TH_11`** — *DBMS Theory: Primary Key vs Unique Key (Reference Answer)*
   - **Expected:** PASS (`expected_pass: true`)
   - **Actual Score:** **35** (`actual_pass: false`)
   - **Evaluated By:** `llama3.2:3b`
   - **Diagnostic:** Candidate submitted a complete textbook answer differentiating nullability, count per table, and clustered index defaults. LLaMA 3.2 3B evaluated the response unusually strictly, docking points across accuracy and relevance down to 35%. This was the sole False Negative in the 60-case validation run.

---

## 5. Summary & Sign-off

- **Tests Status**: **167 / 167 AI-service tests** passed; **156 / 156 backend tests** passed. Zero regressions.
- **HR Failure Behavior**: Factually recorded. When Ollama is down, backend records Answer score = 0, factors 0 into the candidate's average session score, and advances without a retry prompt.
- **Question Routing**: Dual-solution verification correctly falls back to verified catalogs when LLaMA generates unexecutable or non-deterministic code.
- **Independent Measurement**: Recorded pre-run SHA-256 was preserved. Overall accuracy on the 60-case agent self-test was **91.7%** (F1 score: **89.8%**), with 100% accuracy on HR, Coding, SQL, and Output-Prediction, and 5 borderline decisions in Theory questions.
