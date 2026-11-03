# Final Verification

## AI test files

| Test file | Passed | Failed |
|---|---:|---:|
| `test_catalog_verification.py` | 2 | 0 |
| `test_code_executor.py` | 8 | 0 |
| `test_evaluation_rules.py` | 48 | 0 |
| `test_fix2_bounded_labels.py` | 6 | 0 |
| `test_hr_bigo_isolation.py` | 4 | 0 |
| `test_hr_evaluation.py` | 7 | 0 |
| `test_hr_generation_model.py` | 5 | 0 |
| `test_model_config.py` | 8 | 0 |
| `test_non_theory_unaffected.py` | 4 | 0 |
| `test_prompt_alignment.py` | 3 | 0 |
| `test_question_quality.py` | 44 | 0 |
| `test_question_repetition.py` | 10 | 3 |
| `test_requested_regressions.py` | 9 | 0 |
| `test_session_fixes.py` | 7 | 0 |
| `test_theory_overall_score.py` | 5 | 0 |
| **Total** | **170** | **3** |

`test_question_repetition.py` ran all 13 test methods using a deterministic provider for model-written theory questions. Its 3 failing assertions were the `test_ranking_prefers_least_asked`, `test_ranking_prefers_never_asked`, and `test_ranking_prefers_oldest` cases.

## Backend test files

| Test file | Passed | Failed |
|---|---:|---:|
| `auth.test.js` | 176 | 0 |
| `client_result_tags.test.js` | 1 | 0 |
| `failed_eval_handling.test.js` | 20 | 0 |
| `hr_session_limits.test.js` | 47 | 0 |
| `reference_answer_handling.test.js` | 3 | 0 |
| `solution_lock.test.js` | 53 | 0 |
| `theory_score_preservation.test.js` | 5 | 0 |
| **Total** | **305** | **0** |

## Frozen validation

`run_validation_cases.py` completed all 60 cases in 691.46 seconds.

| Cases | Accuracy | TP | FP | TN | FN |
|---:|---:|---:|---:|---:|---:|
| 60 | 88.3% | 22 | 6 | 31 | 1 |

| Module | Cases | Accuracy | TP | FP | TN | FN |
|---|---:|---:|---:|---:|---:|---:|
| `dbms_theory` | 15 | 73.3% | 4 | 3 | 7 | 1 |
| `hr` | 15 | 100.0% | 5 | 0 | 10 | 0 |
| `java_coding` | 5 | 100.0% | 3 | 0 | 2 | 0 |
| `java_theory` | 15 | 80.0% | 5 | 3 | 7 | 0 |
| `output_prediction` | 5 | 100.0% | 2 | 0 | 3 | 0 |
| `sql` | 5 | 100.0% | 3 | 0 | 2 | 0 |

### Wrong cases

| Case | Module | Expected pass | Score | Actual pass |
|---|---|---:|---:|---:|
| `JAVA_TH_06` | `java_theory` | No | 62 | Yes |
| `JAVA_TH_09` | `java_theory` | No | 53 | Yes |
| `JAVA_TH_12` | `java_theory` | No | 85 | Yes |
| `DBMS_TH_02` | `dbms_theory` | No | 70 | Yes |
| `DBMS_TH_06` | `dbms_theory` | No | 70 | Yes |
| `DBMS_TH_09` | `dbms_theory` | No | 70 | Yes |
| `DBMS_TH_11` | `dbms_theory` | Yes | 35 | No |

`validation_cases.json` was not edited. The validation runner was invoked once.
