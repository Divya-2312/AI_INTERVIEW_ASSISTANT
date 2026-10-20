# MockMate AI — Interview Training Datasets

6 datasets, 100 items each (600 total), generated for use as fine-tuning /
seed training data for question generation and evaluation. Each file is
JSONL (one JSON object per line).

## Files

| File | Subject | Format | Contents |
|---|---|---|---|
| `java_theory_100.jsonl` | Java | theory | Conceptual Q&A (OOP, Collections, Exceptions, Multithreading, JVM, Strings, Generics, Streams, keywords) |
| `java_output_prediction_100.jsonl` | Java | output_prediction | Short code snippets + verified expected output + explanation |
| `java_coding_100.jsonl` | Java | coding | LeetCode-style problems: title, description, constraints, starter method signature, examples, test cases |
| `dbms_theory_100.jsonl` | DBMS | theory | Conceptual Q&A (Keys, ER model, Normalization, SQL/Joins, Transactions, Indexing, SQL vs NoSQL) |
| `sql_coding_100.jsonl` | DBMS | coding | "Write a query" problems against 3 consistent schemas (Employees/Departments, Customers/Orders/Products, Students/Courses/Enrollments), each with a sample correct solution query |
| `hr_questions_100.jsonl` | HR | theory | Commonly asked HR interview questions (India context) with answer-*approach* guidance (not scripted answers, since a real answer must be personal) |

## Schema notes

- `java_theory_100.jsonl` / `dbms_theory_100.jsonl`: `questionText`,
  `expectedConcepts` (list), `idealAnswer` (reference answer).
- `java_output_prediction_100.jsonl`: `codeSnippet`, `expectedOutput`
  (verified), `explanation` (step-by-step reasoning).
- `java_coding_100.jsonl`: matches the app's `QuestionResponse` /
  `TestCase` schema fields (`title`, `description`, `constraints`,
  `starterCode`, `examples`, `testCases` with `input`/`expectedOutput`/
  `label`). `input` in each test case is written as literal Java call
  arguments, matching how the app's real Java judge
  (`backend/services/javaJudge.js`) splices it into a method call.
- `sql_coding_100.jsonl`: `schema` (the reference table definitions the
  question is written against), `description`, `sampleSolution` (a correct
  query), `explanation`.
- `hr_questions_100.jsonl`: `questionText`, `answerGuidance` (what a strong
  answer's *approach* looks like — STAR method cues, what to include/avoid
  — deliberately not a verbatim scripted answer, since a real answer needs
  to reflect the candidate's own experience).

## Verification done

- All 600 rows validated for unique IDs and correct required fields.
- A diverse 22-item sample of the harder Java coding problems (DP,
  recursion, two-pointer, array algorithms) was independently implemented
  and run through **actual `javac`/`java` compilation and execution** to
  confirm every `expectedOutput` is genuinely correct — not just
  eyeballed. All 22 passed.
- The Java output-prediction snippets were hand-traced against real JVM
  semantics (operator precedence, overload resolution, autoboxing cache
  behavior, static vs. dynamic dispatch, etc.) — these are exactly the
  categories of subtle-but-correct-behavior questions that are easy to get
  wrong if not carefully verified.

## What this is NOT

This is a **starter/seed dataset**, not a production-scale fine-tuning
corpus. For fine-tuning to meaningfully change model behavior (per the
earlier discussion on Colab + Unsloth), you'll likely want to:

1. Review every item yourself — especially the SQL sample solutions and
   the ~78 Java coding problems that weren't individually re-verified by
   execution (only the 22 hardest ones were, as a representative spot
   check of the riskiest categories — the reference `README` recommends
   verifying the rest the same way before training on them).
2. Expand each category, especially with real interview transcripts / past
   session data from your own app if you have any (higher signal than any
   generic seed set).
3. Convert into whatever exact prompt/completion JSONL shape your chosen
   fine-tuning framework (Unsloth, Axolotl) expects — this repo's shape is
   close to the app's own API contract, not a training-framework-specific
   format, so a small conversion script will be needed at that step.
