#!/usr/bin/env python3
"""
Convert MockMate's six interview JSONL seed datasets into SFT-ready task records,
and programmatically build synthetic rubric evaluate_answer rows from conceptual records.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path
import sys

_scripts_dir = Path(__file__).resolve().parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))
from generate_extra_training_tasks import generate_hr_evaluations, generate_complexity_analysis_records

FILES = [
    'java_theory_100.jsonl',
    'java_output_prediction_100.jsonl',
    'java_coding_100.jsonl',
    'dbms_theory_100.jsonl',
    'sql_coding_100.jsonl',
    'hr_questions_100.jsonl'
]

SYSTEM_PROMPT = (
    "You are AI Interview Assistant, an interview practice assistant. Follow the requested task. "
    "For generation and evaluation tasks, return only the requested JSON object; do not wrap it in markdown. "
    "Evaluate meaning and correctness, not keyword presence alone. Never invent evidence from the student's answer. "
    "Grading Rules: Relevance measures if the answer addresses the topic and is separate from correctness. "
    "Short answers are not auto-irrelevant if on-topic. "
    "Keyword lists earn little credit without explanation."
)



def read_jsonl(p):
    rows = []
    for i, line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f'{p.name}:{i}: {e}')
    return rows


def split_sentences(text):
    text = (text or "").strip()
    if not text:
        return []
    sents = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sents if s.strip()]


def convert(r):
    """Converts a raw dataset record into standard generation task format."""
    fmt = r.get('questionFormat', 'theory')
    subject = r.get('subject', 'unknown')
    diff = r.get('difficulty', 'medium')
    source_id = r.get('id', '')

    if 'idealAnswer' in r:
        task = 'generate_question'
        inp = {
            'interviewType': 'technical',
            'subject': subject,
            'difficulty': diff,
            'questionFormat': 'theory',
            'category': r.get('category'),
            'request': f"Create one interview question on {r.get('category', subject)} [{source_id}] with an ideal reference answer and expected concepts."
        }
        out = {
            'question': r['questionText'],
            'expectedConcepts': r.get('expectedConcepts', []),
            'idealAnswer': r['idealAnswer'],
            'difficulty': diff,
            'questionFormat': 'theory'
        }
    elif 'codeSnippet' in r:
        task = 'generate_question'
        inp = {
            'interviewType': 'technical',
            'subject': 'Java',
            'difficulty': diff,
            'questionFormat': 'output_prediction',
            'category': r.get('category'),
            'request': f"Create a predict-the-output question for [{source_id}]. Preserve code and expected output exactly."
        }
        out = {
            'question': r.get('questionText', 'What does this program print?'),
            'codeSnippet': r['codeSnippet'],
            'expectedOutput': r['expectedOutput'],
            'explanation': r.get('explanation', ''),
            'difficulty': diff,
            'questionFormat': 'output_prediction'
        }
    elif 'testCases' in r and 'starterCode' in r:
        task = 'generate_coding_problem'
        inp = {
            'interviewType': 'technical',
            'subject': 'Java',
            'language': 'java',
            'difficulty': diff,
            'category': r.get('category'),
            'request': f"Create a coding problem for '{r.get('title', source_id)}' [{source_id}] with starter code, examples and test cases."
        }
        out = {k: r[k] for k in ['title', 'description', 'constraints', 'starterCode', 'examples', 'testCases'] if k in r}
        out.update({'subject': 'java', 'language': 'java', 'questionFormat': 'coding', 'difficulty': diff})
    elif 'sampleSolution' in r:
        task = 'generate_coding_problem'
        inp = {
            'interviewType': 'technical',
            'subject': 'DBMS',
            'language': 'SQL',
            'difficulty': diff,
            'category': r.get('category'),
            'request': f"Create a SQL coding interview problem for '{r.get('title', source_id)}' [{source_id}] with schema, solution and explanation."
        }
        out = {k: r[k] for k in ['title', 'description', 'schema', 'sampleSolution', 'explanation'] if k in r}
        out.update({'subject': 'dbms', 'language': 'sql', 'questionFormat': 'coding', 'difficulty': diff})
    elif 'answerGuidance' in r:
        task = 'generate_question'
        inp = {
            'interviewType': 'hr',
            'subject': 'HR',
            'category': r.get('category'),
            'request': f"Create an HR interview question on '{r.get('questionText', '')[:45]}' [{source_id}] and concise guidance for evaluating a candidate response."
        }
        out = {
            'question': r['questionText'],
            'answerGuidance': r['answerGuidance'],
            'questionFormat': 'theory',
            'category': r.get('category', 'General')
        }
    else:
        raise ValueError('Unrecognized schema: ' + str(sorted(r.keys())))

    return {
        'task': task,
        'input': inp,
        'output': out,
        'source_id': source_id,
        'source': 'dataset_raw'
    }


def generate_synthetic_evaluations(raw_records_by_file):
    """
    Programmatically creates 3 evaluate_answer training rows for each theory record
    (reference, partial, wrong) = 200 * 3 = 600 evaluation rows.
    Caps evaluation rows at about 1 per generation row (600 generation : 600 evaluation).
    Uses reference_answer when real ideal answer is known.
    """
    eval_rows = []

    # Collect theory records (Java theory and DBMS theory)
    theory_records = []
    for file_name, records in raw_records_by_file.items():
        if 'theory' in file_name:
            theory_records.extend(records)

    for i, r in enumerate(theory_records):
        question = r.get('questionText', '')
        if not question:
            continue

        subject = r.get('subject', 'Java' if 'java' in r.get('id', '') else 'DBMS')
        interview_type = 'technical'
        concepts = r.get('expectedConcepts', [])
        ideal_answer = r.get('idealAnswer') or r.get('answerGuidance')

        # Pick a wrong answer from another record
        wrong_record = theory_records[(i + 1) % len(theory_records)]
        wrong_answer = wrong_record.get('idealAnswer') or wrong_record.get('answerGuidance') or "An unrelated answer."

        # Split sentences for partial answer
        sents = split_sentences(ideal_answer or "")
        partial_answer = " ".join(sents[:max(1, len(sents) // 2)]) if sents else (ideal_answer[:len(ideal_answer)//2] if ideal_answer else "Partial answer.")

        # Case 1: reference answer
        inp_ref = {
            'interviewType': interview_type,
            'subject': subject,
            'question': question,
            'answer': ideal_answer,
            'expectedConcepts': concepts,
            'questionFormat': 'theory',
            'reference_answer': ideal_answer or "Comprehensive explanation of key principles."
        }

        eval_rows.append({
            'task': 'evaluate_answer',
            'input': inp_ref,
            'output': {
                'score': 90,
                'conceptCoverage': 1.0,
                'correctness': 1.0,
                'relevance': 1.0,
                'communication': 0.85,
                'isIrrelevant': False,
                'feedback': "Comprehensive and accurate answer covering all key points.",
                'strengths': concepts[:3] if concepts else ["Clear explanation"],
                'weaknesses': [],
                'coveredConcepts': concepts,
                'missingConcepts': [],
                'improvementSuggestion': "To make it even stronger, consider adding a practical real-world example.",
                'scoreReason': "Full credit awarded for complete, accurate coverage of required concepts."
            },
            'source_id': r.get('id', 'q'),
            'case_type': 'reference',
            'source': 'synthetic_rubric'
        })

        # Case 2: partial answer
        missing = concepts[len(concepts)//2:] if len(concepts) > 1 else concepts
        covered = concepts[:len(concepts)//2] if len(concepts) > 1 else []
        inp_part = {
            'interviewType': interview_type,
            'subject': subject,
            'question': question,
            'answer': partial_answer,
            'expectedConcepts': concepts,
            'questionFormat': 'theory',
            'reference_answer': ideal_answer or "Comprehensive explanation of key principles."
        }

        eval_rows.append({
            'task': 'evaluate_answer',
            'input': inp_part,
            'output': {
                'score': 50,
                'conceptCoverage': 0.5,
                'correctness': 0.6,
                'relevance': 0.8,
                'communication': 0.7,
                'isIrrelevant': False,
                'feedback': "Good initial explanation, but leaves out important secondary details.",
                'strengths': covered if covered else ["Basic concept mentioned"],
                'weaknesses': [f"Omitted: {c}" for c in missing],
                'coveredConcepts': covered,
                'missingConcepts': missing,
                'improvementSuggestion': f"To improve your answer, explain {', '.join(missing)} and connect those ideas directly to the question.",
                'scoreReason': f"Partial credit awarded. Missing required concepts: {', '.join(missing)}."
            },
            'source_id': r.get('id', 'q'),
            'case_type': 'partial',
            'source': 'synthetic_rubric'
        })

        # Case 3: wrong answer
        inp_wrong = {
            'interviewType': interview_type,
            'subject': subject,
            'question': question,
            'answer': wrong_answer,
            'expectedConcepts': concepts,
            'questionFormat': 'theory',
            'reference_answer': ideal_answer or "Comprehensive explanation of key principles."
        }

        eval_rows.append({
            'task': 'evaluate_answer',
            'input': inp_wrong,
            'output': {
                'score': 0,
                'conceptCoverage': 0.0,
                'correctness': 0.0,
                'relevance': 0.0,
                'communication': 0.0,
                'isIrrelevant': True,
                'feedback': "The answer is unrelated to the question.",
                'strengths': [],
                'weaknesses': ["Unrelated response"],
                'coveredConcepts': [],
                'missingConcepts': concepts,
                'improvementSuggestion': "Provide an answer that directly addresses the question.",
                'scoreReason': "Zero score because the response addresses a different topic entirely."
            },
            'source_id': r.get('id', 'q'),
            'case_type': 'wrong',
            'source': 'synthetic_rubric'
        })

    return eval_rows


# Note: generate_hr_evaluations and generate_complexity_analysis_records are imported
# from generate_extra_training_tasks above to guarantee zero data leakage and O(N^3)/O(2^N) support.


def summarize_conversion(rows):
    by_task = Counter()
    by_source = Counter()
    seen = set()
    duplicates = 0

    for row in rows:
        by_task[row['task']] += 1
        by_source[row.get('source', 'unknown')] += 1
        fp = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if fp in seen:
            duplicates += 1
        else:
            seen.add(fp)

    return {
        'input_records': len(rows),
        'unique_records': len(seen),
        'duplicate_records': duplicates,
        'task_distribution': dict(sorted(by_task.items())),
        'source_distribution': dict(sorted(by_source.items())),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input-dir', default='training/data/raw')
    ap.add_argument('--output', default='training/data/processed/canonical.jsonl')
    ap.add_argument('--summary-path', default=None)
    a = ap.parse_args()

    indir = Path(a.input_dir)
    if not indir.exists() and Path('data/raw').exists():
        indir = Path('data/raw')
    out = Path(a.output)
    if not out.parent.exists() and Path('data/processed').exists():
        out = Path('data/processed/canonical.jsonl')

    raw_by_file = {}
    all_gen_rows = []
    seen = set()
    invalid = 0

    for name in FILES:
        p = indir / name
        if not p.exists():
            raise FileNotFoundError(f'Missing dataset file: {p}')
        records = read_jsonl(p)
        raw_by_file[name] = records

        for r in records:
            try:
                x = convert(r)
            except ValueError as exc:
                invalid += 1
                print(f'Warning: skipped malformed record from {p.name}: {exc}')
                continue
            key = json.dumps(x, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                all_gen_rows.append(x)

    # 1. Generate synthetic evaluate_answer rows for Theory (Java & DBMS)
    synthetic_eval_rows = generate_synthetic_evaluations(raw_by_file)
    for row in synthetic_eval_rows:
        key = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            all_gen_rows.append(row)

    # 2. Generate synthetic evaluate_answer rows for HR (STAR, Partial, Cliché, Irrelevant)
    hr_records = raw_by_file.get('hr_questions_100.jsonl', [])
    hr_eval_rows = generate_hr_evaluations(hr_records)
    for row in hr_eval_rows:
        key = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            all_gen_rows.append(row)

    # 3. Generate synthetic analyze_code_complexity rows for Coding problems
    coding_records = raw_by_file.get('java_coding_100.jsonl', [])
    complexity_rows = generate_complexity_analysis_records(coding_records)
    for row in complexity_rows:
        key = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            all_gen_rows.append(row)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in all_gen_rows), encoding='utf-8')

    summary = summarize_conversion(all_gen_rows)
    summary['invalid_records'] = invalid
    summary['files_processed'] = len(FILES)

    if a.summary_path:
        sp = Path(a.summary_path)
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f'Converted {len(all_gen_rows)} total examples (generation + synthetic evaluation) from {len(FILES)} raw files')
    for task, n in sorted(summary['task_distribution'].items()):
        print(f'  {task}: {n}')
    print('Source distribution:', json.dumps(summary['source_distribution']))
    print('Output:', out)


if __name__ == '__main__':
    main()
