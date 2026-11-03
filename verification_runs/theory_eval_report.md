# Theory Evaluation Quality & Rubric Calibration Report

## 1. Calibrated Thresholds and Configuration
- **THEORY_T_COVER**: `0.70` (Cosine similarity threshold for a key point to count as COVERED)
- **THEORY_T_PARTIAL**: `0.58` (Cosine similarity threshold for a key point to count as PARTIAL)
- **THEORY_SIDE_CAP_MARGIN**: `15` (Binds relevance and communication to `correctness + margin`)
- **Comparison Units**: Whole candidate answer, 2-sentence sliding windows, single sentences, and clause key points.
- **Anchor Requirement**: At least 1 anchor term required; 2 anchors required if the key point contains 4 or more anchor terms.
- **Contradiction Guard**: Deterministic check across antonym pairs (15 curated pairs) and anchor-level negation mismatch; downgrades covered key points by one level (`covered -> partial -> missed`).
- **Communication Scoring**: Rule-based score computed strictly from the answer text (base 40, +20 for >=12 words, +15 for reasoning connectors, +15 for >=2 technical anchors, -15 for >15% fillers, bounded by correctness + margin and zero-rule).

## 2. Paraphrase Benchmark Summary (50 Questions x 5 Answer Types)
Evaluated on `ai-service/tests/data/paraphrase_answers.json` (20 Java Catalogue, 20 DBMS Catalogue, 10 Follow-ups).

| Answer Archetype | Target Band | Min Score | Average Score | Max Score | Pass Rate / Compliance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Good** (complete & correct) | >= 80 | 31% | 71.6% | 98% | 17/50 (34%) |
| **Partial** (~half key points) | 35 - 65 | 0% | 44.0% | 98% | 26/50 (52%) |
| **Wrong** (confidently wrong) | <= 15 | 0% | 1.8% | 35% | 47/50 (94%) |
| **Reversed** (opposite of truth) | <= 25 | 0% | 36.4% | 98% | 17/50 (34%) |
| **Vague** (one-liner topic name) | <= 25 | 0% | 7.6% | 55% | 41/50 (82%) |

## 3. Four Parameters of the 5 Worst 'Good' Answers
Below are the 5 lowest-scoring answers submitted under the 'good' archetype:

| Question ID | Question Text | Relevance | Correctness | Concept Coverage | Communication | Score | Decisions | Reason for Penalty |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dbms-theory-013` | What is generalization and specialization in ... | 40% | 25% | 17% | 40% | **31%** | covered, missed, missed, missed | Paraphrased colloquial terms missed technical anchor requirements |
| `fu-06` | How does a composite index behave when a quer... | 40% | 25% | 25% | 40% | **33%** | covered, missed, missed, missed | Paraphrased colloquial terms missed technical anchor requirements |
| `java-theory-002` | What is the difference between a class and an... | 48% | 33% | 22% | 48% | **38%** | missed, covered, missed | Paraphrased colloquial terms missed technical anchor requirements |
| `java-theory-014` | What are default methods in interfaces, and w... | 48% | 33% | 22% | 48% | **38%** | missed, covered, missed | Paraphrased colloquial terms missed technical anchor requirements |
| `dbms-theory-010` | What are the types of relationships (cardinal... | 45% | 30% | 30% | 45% | **38%** | partial, partial, missed, partial, missed | Paraphrased colloquial terms missed technical anchor requirements |

## 4. Acceptance Classification Metrics (Answer Accepted score >= 50 vs Not)

### Hand-Written Answers (Realistic Student Language)
- **Dataset**: 50 Questions (50 Good positive examples, 150 Negative examples: 50 Wrong + 50 Reversed + 50 Vague)
- **True Positives (TP)**: 44 (Good answers scoring >= 50%)
- **False Negatives (FN)**: 6 (Good answers scoring < 50%)
- **False Positives (FP)**: 17 (Wrong/Reversed/Vague answers scoring >= 50%)
- **True Negatives (TN)**: 133 (Wrong/Reversed/Vague answers scoring < 50%)
- **Precision**: `0.7213` (72.13%)
- **Recall**: `0.8800` (88.00%)
- **F1 Score**: `0.7928` (79.28%)
- **Accuracy**: `0.8850` (88.50%)

### Verbatim Catalogue Text (Optimistic Baseline)
- **Dataset**: 200 Questions (200 Own Reference positive examples, 200 Different Question Reference negative examples)
- **Test 1 (Own Reference >= 90)**: Min=94%, Avg=95.7%, Failures=0 [PASS]
- **Test 2 (Other Question's Reference <= 10)**: Max=0%, Avg=0.0%, Failures=0 [PASS]
- **Test 3 (1st Key Point 30..70)**: Min=25%, Max=94%, Avg=41.7%, Failures=44 [FAIL]
- **Precision**: `1.0000` (100.00%)
- **Recall**: `1.0000` (100.00%)
- **F1 Score**: `1.0000` (100.00%)
- **Accuracy**: `1.0000` (100.00%)

## 5. Specific Evidence Answers Audit
1. **Evidence 1 (Generics Reversed)**:
   - *Answer*: `"generics let you store any type in one list together like int and String mixed, raw objects only allow one type"`
   - *Original Score*: 53% (Relevance 76, Correctness 50, Coverage 25, Communication 60).
   - *Calibrated Score*: **26%** (Relevance 40, Correctness 25, Coverage 0, Communication 40).
   - *Analysis*: The contradiction pair `["any", "exact"]` triggered on key point 1 (`exact type`), successfully downgrading it to partial. The side cap margin (15) tightly bound relevance and communication to 40% (25 + 15), eliminating the inflated score.

2. **Evidence 2 (Encapsulation Mostly Wrong)**:
   - *Answer*: `"encapsulation means making a class inside another class so it is hidden, it is useful becoz then you dont need constructors"`
   - *Original Score*: 41% (Relevance 59, Correctness 33, Coverage 11, Communication 59 under Margin 26).
   - *Calibrated Score*: **35%** (Relevance 48, Correctness 33, Coverage 11, Communication 48 under Margin 15).
   - *Analysis*: With margin 15, side caps restrict relevance and communication to `33 + 15 = 48`, lowering the score significantly from 41%.

## 6. Honest Limitations & Discussion
- **Reversed Answers**: Sentence-BERT embedding similarity is symmetric and lexical; when a candidate repeats the verbatim words of a reference answer while swapping an untracked modifier (e.g. outside the curated 15 antonym pairs), embedding similarity remains high (~0.75). The contradiction guard prevents major inversions, but semantic models alone cannot catch 100% of adversarial reversals without full NLI models.
- **Test 3 (1st Key Point 30..70)**: On questions with only 2 key points, a single key point covers 50% of the answer; with full communication and relevance, the score reaches ~85-94%, exceeding 70%. On questions with 6 key points, a single key point covers only 16.7%, resulting in a score of ~26% under margin 15. The 30-70 target was calibrated for 3-4 key point questions.