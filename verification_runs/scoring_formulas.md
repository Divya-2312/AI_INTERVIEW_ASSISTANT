# Common Evaluation Scoring Formulas & Module Adapters

## 1. Core Mathematical Definitions (`ai-service/app/utils/scoring_formulas.py`)

All evaluations across every interview module (Java Theory, DBMS Theory, HR / Behavioral, Predict the Output, Java Coding, SQL) strictly share a single parameter set and common formula set:

```python
PARAMETERS = ["accuracy", "correctness", "relevance", "concept_coverage"]
```

### 1.1 Pure Helper Functions
- **Rounding Rule**: Round-half-up (`round_half_up(val)`) using Decimal quantization. `val = 2.5 -> 3`, `val = 66.666... -> 67`.
- **Percentage**:
  $$\text{percent}(matched, total) = \text{clamp}\left(0, 100, \text{round\_half\_up}\left(\frac{100 \times matched}{total}\right)\right)$$
  (returns $0$ when $total \le 0$).
- **Question Score**:
  $$\text{question\_score}(params) = \text{round\_half\_up}\left(\frac{\sum_{p \in \text{PARAMETERS}} params[p]}{4}\right)$$
  Equal weights of 25% each; no other terms, caps, or side margins.
- **Session Score (Interview Total)**:
  $$\text{session\_score}(question\_scores, questions\_count) = \text{round\_half\_up}\left(\frac{\sum question\_scores}{questions\_count}\right)$$
  Unanswered questions contribute 0. Default $questions\_count = 10$.

---

## 2. Common Parameter Semantics

For every module:
- **Required items ($R$)**: What a complete answer must contain.
- **Answer items ($A$)**: What the candidate actually stated or produced.
- **`concept_coverage`**: $\text{percent}(\text{number of } R \text{ items covered by } A, |R|)$
- **`correctness`**: $\text{percent}(\text{number of } A \text{ items that are correct}, |A|)$ (empty answer = 0)
- **`relevance`**: $\text{percent}(\text{number of } A \text{ items that are on-topic}, |A|)$
- **`accuracy`**: $\text{percent}(R \text{ items matched precisely with strict threshold}, |R|)$

---

## 3. Module Adapters & Existing Thresholds

### 3.1 Java Theory & DBMS Theory
- **$R$ (Required Items)**: Key points and expected technical concepts extracted from question and reference answer ($|R| \in [2, 6]$).
- **$A$ (Answer Items)**: Candidate sentences / assertion units ($|A| \ge 1$).
- **Signals & Thresholds**:
  - Semantic Matching: Sentence-BERT cosine similarity (`all-MiniLM-L6-v2`).
  - Standard Coverage Threshold: `THEORY_T_COVER = 0.70`.
  - Partial Threshold: `THEORY_T_PARTIAL = 0.50`.
  - Strict Accuracy Threshold: `THEORY_T_STRICT = 0.82` with anchor match.
- **Parameter Formulas**:
  - `concept_coverage`: $\text{percent}(\text{key points covered with } \text{sim} \ge 0.70, |R|)$
  - `accuracy`: $\text{percent}(\text{key points matched with strict } \text{sim} \ge 0.82 \text{ and anchors}, |R|)$
  - `correctness`: $\text{percent}(\text{sentences correct and free of contradiction cues}, |A|)$
  - `relevance`: $\text{percent}(\text{sentences semantically relevant to question domain}, |A|)$
- **Guards**:
  - Zero Rule: If no key point covered or partial ($\text{correctness} = 0$), all parameters = 0 and score = 0.
  - Contradiction Guard: If contradiction cues fire for an item, sentence is marked incorrect / keypoint downgraded.
  - Side caps on communication and relevance are removed. Communication is displayed for feedback only and is NOT in the 4-factor average.

### 3.2 HR / Behavioral
- **Signals & Routing**:
  - Fine-Tuned Model: `mockmate-hr100` ONLY (temperature 0).
  - Output sub-scores from fine-tuned model: `correctness`, `relevance`, `accuracy` ($0..100$ whole percentages).
- **Concept Coverage**:
  - $R$: 4 rubric concepts from `hr_india_100.json` (Context & Situation, Concrete Personal Actions, Tangible Outcome, Professional Reflection).
  - Evaluated via Sentence-BERT cosine similarity against candidate answer (threshold $\ge 0.65$).
  - `concept_coverage`: $\text{percent}(\text{rubric concepts covered}, 4)$.
- **Guards**:
  - Topic Gate: Zero semantic hits or off-topic flag $\implies 0\%$ across all parameters.
  - Copy of question / bare keyword list $\implies 0\%$.
  - Communication: Retained as qualitative speech delivery feedback text only; NOT included in average.

### 3.3 Predict the Output
- **$R$ (Required Items)**: Expected stdout lines from deterministic JVM execution ($|R| \ge 1$).
- **$A$ (Answer Items)**: Candidate output lines produced ($|A| \ge 1$).
- **Formulas**:
  - Exact match of full stdout after whitespace/quote normalization $\implies 100\%$ on all 4 parameters (`score = 100`).
  - `concept_coverage`: $\text{percent}(\text{expected lines covered by candidate lines}, |R|)$.
  - `correctness`: $\text{percent}(\text{candidate lines that match an expected line}, |A|)$.
  - `relevance`: $\text{percent}(\text{produced lines that contain valid program output tokens}, |A|)$.
  - `accuracy`: $\text{percent}(\text{exact line matches in identical sequence}, |R|)$.
  - If output is wrong and no reasoning explanation is given: score = 0.

### 3.4 Java Coding
- **$R$ (Required Items)**: Test cases specified for the problem ($|R| \ge 3$).
- **$A$ (Answer Items)**: Test cases executed in deterministic JVM sandbox.
- **Formulas**:
  - Compilation error or syntax failure $\implies$ all 4 parameters = 0, score = 0.
  - `passed` = number of passing test cases in sandbox execution.
  - `concept_coverage`: $\text{percent}(passed, |R|)$.
  - `correctness`: $\text{percent}(passed, |R|)$.
  - `accuracy`: $\text{percent}(passed, |R|)$.
  - `relevance`: $\text{percent}(passed, |R|)$.
  - Result: All 4 parameters are strictly consistent.
    - $0 \text{ of } N \text{ pass} \implies 0\%$ score.
    - $2 \text{ of } 3 \text{ pass} \implies 67\%$ score.
    - $3 \text{ of } 3 \text{ pass} \implies 100\%$ score.
  - LLaMA rubric criteria (logic, approach, edge case, readability) and Big-O complexity analysis provide qualitative comments ONLY and NEVER add or subtract points from the score.

### 3.5 SQL
- **$R$ (Required Items)**: Test queries and expected rows in SQLite database ($|R| \ge 1$).
- **$A$ (Answer Items)**: Queries executed against SQLite test schema.
- **Formulas**: Identical to Java Coding.
  - Query syntax error / runtime error $\implies$ all 4 parameters = 0, score = 0.
  - Row-by-row result comparison determines passed test cases.
  - All 4 parameters equal $\text{percent}(passed, |R|)$.
