# End-to-End Interview Evaluation Results (Task B11)
Generated via automated end-to-end evaluation script across all interview types.

## 1. Java Theory
**Question:** `What is the difference between ArrayList and LinkedList?`

| Answer Archetype | Answer Text | Relevance | Correctness / Accuracy | Coverage | Communication | Overall Score | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Good | ArrayList is backed by a dynamic resizable array which offers fas... | 100% | 88% | 50% | 90% | **82%** | PASS |
| Partial | ArrayList uses an array inside so searching by index is very fast... | 27% | 12% | 0% | 27% | **17%** | FAIL |
| Wrong | ArrayList stores primitive numbers in stack memory while LinkedLi... | 0% | 0% | 0% | 0% | **0%** | FAIL |

---

## 2. DBMS Theory
**Question:** `What is a foreign key?`

| Answer Archetype | Answer Text | Relevance | Correctness / Accuracy | Coverage | Communication | Overall Score | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Good | A foreign key is a column or set of columns in a table that refer... | 100% | 100% | 100% | 75% | **94%** | PASS |
| Partial | A foreign key connects two database tables together by pointing t... | 90% | 75% | 50% | 90% | **76%** | PASS |
| Wrong | A foreign key is an encryption password imported from a foreign c... | 0% | 0% | 0% | 0% | **0%** | FAIL |

---

## 3. Output Prediction
**Question:** `What does this code print?`

| Answer Archetype | Answer Text | Relevance | Correctness / Accuracy | Coverage | Communication | Overall Score | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Good | 12 | 100% | 100% | 100% | - | **100%** | PASS |
| Partial (Close Misconception) | 11 | 100% | 0% | 0% | - | **0%** | FAIL |
| Wrong | Error | 100% | 0% | 0% | - | **0%** | FAIL |

---

## 4. Java Coding
**Question:** `Implement a method add(int a, int b) that returns the sum of two integers.`

| Answer Archetype | Answer Text | Relevance | Correctness / Accuracy | Coverage | Communication | Overall Score | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Good (Correct Logic) | public class Solution { public static int add(int a, int b) { ret... | - | - | - | - | **100%** | PASS |
| Partial (Passes 2 of 3) | public class Solution { public static int add(int a, int b) { if ... | - | - | - | - | **90%** | PASS |
| Wrong (Syntax Error) | public class Solution { public static int add(int a, int b) { ret... | - | - | - | - | **0%** | FAIL |

---

## 5. SQL Coding
**Question:** `Find the names and salaries of employees earning strictly more than 60,000.`

| Answer Archetype | Answer Text | Relevance | Correctness / Accuracy | Coverage | Communication | Overall Score | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Good | SELECT name, salary FROM employees WHERE salary > 60000 ORDER BY ... | - | - | - | - | **100%** | PASS |
| Partial (Wrong Salary Threshold) | SELECT name, salary FROM employees WHERE salary >= 50000 ORDER BY... | - | - | - | - | **15%** | FAIL |
| Wrong (Syntax Error) | SELECT FROM employees WHERE | - | - | - | - | **0%** | FAIL |

---

## 6. HR Behavioral Round
**Question:** `Tell me about a time you worked in a team.`

| Answer Archetype | Answer Text | Relevance | Correctness / Accuracy | Coverage | Communication | Overall Score | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Good (STAR) | During my final year engineering project, I worked in a 4-person ... | 82% | 90% / 82% | - | 77% | **83%** | PASS |
| Partial (Average) | In college I worked with classmates on a group assignment. We div... | 83% | 0% / 0% | - | 59% | **36%** | PARTIAL |
| Wrong (Irrelevant) | Java supports object oriented programming and uses garbage collec... | 0% | 0% / 0% | - | 0% | **0%** | FAIL |

---
