import argparse, csv, json, random, hashlib, re
from collections import Counter, defaultdict
from pathlib import Path

SYSTEM = (
    "You are AI Interview Assistant, an interview practice assistant. Follow the requested task. "
    "For generation and evaluation tasks, return only the requested JSON object; do not wrap it in markdown. "
    "Evaluate meaning and correctness, not keyword presence alone. Never invent evidence from the student's answer. "
    "Grading Rules: Relevance measures if the answer addresses the topic and is separate from correctness. "
    "Short answers are not auto-irrelevant if on-topic. "
    "Keyword lists earn little credit without explanation."
)


def read_records(path):
    p = Path(path)
    if p.suffix.lower() == '.jsonl':
        rows = []
        for i, line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(), 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception as e:
                    raise ValueError(f'Invalid JSON on line {i}: {e}')
        return rows
    if p.suffix.lower() == '.json':
        obj = json.loads(p.read_text(encoding='utf-8-sig'))
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            for key in ('data', 'examples', 'records'):
                if key in obj and isinstance(obj[key], list):
                    return obj[key]
            return [obj]
        raise ValueError(f'Unsupported JSON structure in {p}')
    if p.suffix.lower() == '.csv':
        with p.open(newline='', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))
    raise ValueError('Input must be .jsonl, .json or .csv')


def parse_maybe_json(x):
    if not isinstance(x, str):
        return x
    s = x.strip()
    if s.startswith('{') or s.startswith('['):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    return x


def _subject_from_record(row):
    if isinstance(row, dict):
        for key in ('subject', 'domain', 'category', 'language'):
            if row.get(key):
                return str(row[key]).lower()
        if isinstance(row.get('input'), dict):
            inp = row['input']
            for k in ('subject', 'domain', 'category', 'language', 'interviewType'):
                if inp.get(k):
                    return str(inp[k]).lower()
    return 'unknown'


def extract_group_key(task, inp, out=None, row=None, user_prompt=None):
    """Extract a normalized group key for group splitting."""
    if row and isinstance(row, dict) and row.get('source_id'):
        return str(row['source_id']).strip()

    parsed_inp = parse_maybe_json(inp)

    # For evaluate_answer: group all evaluation variants of the SAME question together
    if task == 'evaluate_answer' and isinstance(parsed_inp, dict):
        q_text = parsed_inp.get('question')
        if q_text:
            cleaned_q = re.sub(r'[^a-zA-Z0-9\s]', '', str(q_text).lower()).strip()
            if cleaned_q:
                return f"eval_{cleaned_q[:80]}"

    # For analyze_code_complexity: group complexity variants of the SAME problem together
    if task == 'analyze_code_complexity' and isinstance(parsed_inp, dict):
        q_text = parsed_inp.get('question') or parsed_inp.get('code')
        if q_text:
            cleaned_q = re.sub(r'[^a-zA-Z0-9\s]', '', str(q_text).lower()).strip()
            if cleaned_q:
                return f"complexity_{cleaned_q[:80]}"

    # For generation tasks: group by user prompt hash so identical user prompts stay in the same split
    if user_prompt:
        return f"prompt_{hashlib.sha256(user_prompt.encode('utf-8')).hexdigest()[:16]}"

    if isinstance(parsed_inp, dict):
        raw_text = json.dumps(parsed_inp, sort_keys=True)
    else:
        raw_text = str(inp or '')

    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', raw_text.lower()).strip()
    return f"group_{cleaned[:80]}"


def normalize(row, index):
    if not isinstance(row, dict):
        raise ValueError(f'Row {index}: each record must be an object')

    source = row.get('source', 'source_dataset')

    if isinstance(row.get('messages'), list):
        msgs = row['messages']
        if not any(m.get('role') == 'assistant' for m in msgs):
            raise ValueError(f'Row {index}: messages needs an assistant target')
        if not any(m.get('role') == 'user' for m in msgs):
            raise ValueError(f'Row {index}: messages needs a user message')
        user_msg = next((m['content'] for m in msgs if m.get('role') == 'user'), '')
        group_key = extract_group_key('custom', user_msg, row=row, user_prompt=user_msg)
        return {
            'messages': msgs,
            'source': source,
            'source_id': row.get('source_id', ''),
            'case_type': row.get('case_type', ''),
            'task': str(row.get('task', 'custom')),
            'subject': _subject_from_record(row),
            'group_key': group_key
        }

    task = str(row.get('task') or row.get('task_type') or 'interview').strip()
    inp = parse_maybe_json(row.get('input', row.get('prompt', row.get('instruction', ''))))
    out = parse_maybe_json(row.get('output', row.get('completion', row.get('target', ''))))

    if isinstance(inp, dict):
        inp_str = json.dumps(inp, ensure_ascii=False, indent=2)
    else:
        inp_str = str(inp)

    if isinstance(out, (dict, list)):
        out_str = json.dumps(out, ensure_ascii=False)
    else:
        out_str = str(out)

    if not inp_str.strip() or not out_str.strip():
        raise ValueError(f'Row {index}: expected non-empty input/prompt/instruction and output/completion/target')

    user = f'TASK: {task}\nINPUT:\n{inp_str}\n\nReturn the required result. For JSON tasks, output valid JSON only.'
    group_key = extract_group_key(task, inp, out=out, row=row, user_prompt=user)

    return {
        'messages': [
            {'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': user},
            {'role': 'assistant', 'content': out_str}
        ],
        'task': task,
        'subject': _subject_from_record(row),
        'source': source,
        'source_id': row.get('source_id', ''),
        'case_type': row.get('case_type', ''),
        'group_key': group_key
    }


def fingerprint(ex):
    user_msg = next((m['content'] for m in ex['messages'] if m['role'] == 'user'), '')
    assistant_msg = next((m['content'] for m in ex['messages'] if m['role'] == 'assistant'), '')
    fp_text = f"{user_msg}|||{assistant_msg}"
    return hashlib.sha256(fp_text.encode()).hexdigest()


def summarize_records(rows):
    if rows is None or not isinstance(rows, list):
        raise ValueError('Rows must be a list of records')

    valid_rows = []
    rejected = []
    seen = set()
    duplicate_count = 0
    subject_distribution = Counter()
    source_distribution = Counter()

    for index, row in enumerate(rows, 1):
        try:
            normalized = normalize(row, index)
        except ValueError as exc:
            rejected.append({'row_index': index, 'reason': str(exc)})
            continue

        valid_rows.append(normalized)
        subject_distribution[normalized['subject']] += 1
        source_distribution[normalized['source']] += 1

        fp = fingerprint(normalized)
        if fp in seen:
            duplicate_count += 1
        else:
            seen.add(fp)

    return {
        'input_records': len(rows),
        'valid_records': len(valid_rows),
        'rejected_records': len(rejected),
        'duplicate_records': duplicate_count,
        'subject_distribution': dict(sorted(subject_distribution.items())),
        'source_distribution': dict(sorted(source_distribution.items())),
        'rejected_examples': rejected,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--output-dir', default='data/processed/splits')
    ap.add_argument('--test-ratio', type=float, default=.15)
    ap.add_argument('--validation-ratio', type=float, default=.1)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--summary-path', default=None, help='Optional path for JSON summary report')
    a = ap.parse_args()

    if a.test_ratio <= 0 or a.validation_ratio <= 0 or a.test_ratio + a.validation_ratio >= .5:
        raise SystemExit('Ratios must be >0 and sum to less than 0.5')

    rows = read_records(a.input)
    summary = summarize_records(rows)

    valid_rows = []
    seen = set()
    for i, row in enumerate(rows, 1):
        try:
            ex = normalize(row, i)
        except ValueError:
            continue
        fp = fingerprint(ex)
        if fp not in seen:
            seen.add(fp)
            valid_rows.append(ex)

    if len(valid_rows) < 10:
        raise SystemExit(f'Only {len(valid_rows)} unique examples.')

    groups = defaultdict(list)
    for row in valid_rows:
        groups[row['group_key']].append(row)

    # Categorize group keys for task-stratified allocation across splits
    eval_gks, coding_gks, complexity_gks, gen_other_gks = [], [], [], []
    for gk, items in groups.items():
        tasks = {item['task'] for item in items}
        if 'evaluate_answer' in tasks:
            eval_gks.append(gk)
        elif 'analyze_code_complexity' in tasks:
            complexity_gks.append(gk)
        elif 'generate_coding_problem' in tasks:
            coding_gks.append(gk)
        else:
            gen_other_gks.append(gk)

    rng = random.Random(a.seed)
    rng.shuffle(eval_gks)
    rng.shuffle(coding_gks)
    rng.shuffle(complexity_gks)
    rng.shuffle(gen_other_gks)

    unfit_reports = []

    def allocate_category_groups(category_name, category_gks):
        cat_total_items = sum(len(groups[gk]) for gk in category_gks)
        target_test_cat = round(cat_total_items * a.test_ratio)
        target_val_cat = round(cat_total_items * a.validation_ratio)

        curr_test, curr_val, curr_train = [], [], []
        curr_test_count, curr_val_count = 0, 0

        for gk in category_gks:
            items = groups[gk]
            item_len = len(items)
            if curr_test_count < target_test_cat:
                if curr_test_count + item_len > target_test_cat * 1.5 and curr_test_count > 0:
                    unfit_reports.append(f"Category {category_name} group '{gk[:30]}' size {item_len} exceeded test target limit ({curr_test_count}/{target_test_cat}).")
                curr_test.extend(items)
                curr_test_count += item_len
            elif curr_val_count < target_val_cat:
                if curr_val_count + item_len > target_val_cat * 1.5 and curr_val_count > 0:
                    unfit_reports.append(f"Category {category_name} group '{gk[:30]}' size {item_len} exceeded val target limit ({curr_val_count}/{target_val_cat}).")
                curr_val.extend(items)
                curr_val_count += item_len
            else:
                curr_train.extend(items)

        return curr_test, curr_val, curr_train

    t1, v1, tr1 = allocate_category_groups('eval_theory', eval_gks)
    t2, v2, tr2 = allocate_category_groups('coding', coding_gks)
    t3, v3, tr3 = allocate_category_groups('complexity', complexity_gks)
    t4, v4, tr4 = allocate_category_groups('gen_other', gen_other_gks)

    test_rows = t1 + t2 + t3 + t4
    val_rows = v1 + v2 + v3 + v4
    train_rows = tr1 + tr2 + tr3 + tr4

    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    distinct_prompts = {}
    task_counts_per_split = {}
    source_counts_per_split = {}
    for name, data in [('train', train_rows), ('validation', val_rows), ('test', test_rows)]:
        export_data = []
        for d in data:
            item = {k: v for k, v in d.items() if k != 'group_key'}
            export_data.append(item)

        (out / f'{name}.jsonl').write_text(
            ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in export_data),
            encoding='utf-8'
        )

        user_prompts = {next(m['content'] for m in x['messages'] if m['role'] == 'user') for x in data}
        distinct_prompts[name] = len(user_prompts)
        task_counts_per_split[name] = dict(Counter(d['task'] for d in data))
        source_counts_per_split[name] = dict(Counter(d['source'] for d in data))

    distinct_prompts['total'] = len({next(m['content'] for m in x['messages'] if m['role'] == 'user') for x in valid_rows})

    summary['unique_valid_records'] = len(valid_rows)
    summary['split_counts'] = {'train': len(train_rows), 'validation': len(val_rows), 'test': len(test_rows)}
    summary['task_counts_per_split'] = task_counts_per_split
    summary['source_counts_per_split'] = source_counts_per_split
    summary['distinct_prompt_counts'] = distinct_prompts
    summary['unfit_reports'] = unfit_reports
    summary['random_seed'] = a.seed

    if a.summary_path:
        summary_path = Path(a.summary_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f'Input records: {summary["input_records"]} | valid: {summary["valid_records"]} | rejected: {summary["rejected_records"]} | duplicates removed: {summary["duplicate_records"]}')
    print(f'Unique valid examples: {len(valid_rows)}')
    print(f'train={len(train_rows)}, validation={len(val_rows)}, test={len(test_rows)}')
    print(f'task_counts_per_split: {json.dumps(task_counts_per_split, indent=2)}')
    print(f'source_counts_per_split: {json.dumps(source_counts_per_split, indent=2)}')
    print(f'Distinct prompt counts: {json.dumps(distinct_prompts)}')
    if unfit_reports:
        print('Group fit warnings:', json.dumps(unfit_reports, indent=2))
    else:
        print('Group fit check: All groups fit within target limits cleanly.')
    print('Wrote splits to:', out)
    if a.summary_path:
        print('Summary JSON:', summary_path)


if __name__ == '__main__':
    main()

