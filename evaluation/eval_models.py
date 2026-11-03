"""Evaluate ANY Ollama model on the HR task or the code-complexity task, with identical prompts, and save the numbers.
Usage (run in C:\\mockmate_eval, which has validation.jsonl and hr_india_100.json):
    python eval_models.py mockmate-hr100 cx            # code complexity, all validation rows (about 50)
    python eval_models.py mockmate-hr100 hr 100        # HR, random sample of 100 rows
    python eval_models.py llama3.2:3b cx               # the same tests on the base model, for comparison
    python eval_models.py llama3.2:3b hr 100
Results are printed and saved to results_<model>_<task>.json (upload these files)."""
import json, random, re, sys, time, urllib.request
from collections import Counter

model, task = sys.argv[1], sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
URL = "http://localhost:11434/api/chat"
TASK_RE = re.compile(r"TASK:\s*(\S+)\s*\nINPUT:\s*(\{.*\})\s*\n\s*\nReturn", re.S)
india = {x["question"] for x in json.load(open("hr_india_100.json", encoding="utf-8"))}

def ask(messages):
    body = json.dumps({"model": model, "messages": messages, "stream": False,
                       "options": {"temperature": 0, "num_predict": 700}}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=600))["message"]["content"]

def parse(s):
    try: return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s or "", re.S)          # tolerate text around the JSON
        try: return json.loads(m.group(0)) if m else None
        except Exception: return None

rows = []
for line in open("validation.jsonl", encoding="utf-8"):
    e = json.loads(line); u = next(m["content"] for m in e["messages"] if m["role"] == "user")
    m = TASK_RE.search(u)
    if not m: continue
    inp = json.loads(m.group(2))
    if task == "hr" and m.group(1) == "evaluate_answer" and inp.get("question") in india: rows.append(e)
    if task == "cx" and m.group(1) == "analyze_code_complexity": rows.append(e)
assert rows, "no matching rows - use the NEW validation.jsonl"
if limit and limit < len(rows):
    random.seed(0); rows = random.sample(rows, limit)
print(f"model={model} task={task} rows={len(rows)}")

norm = lambda s: re.sub(r"[\s^*]", "", str(s or "").lower())
n = valid = 0; t0 = time.time(); secs = []
hr_err = []; irr_ref = irr_ok = rel_ref = false_zero = 0; t_hit = s_hit = 0
for i, e in enumerate(rows):
    ref = json.loads(e["messages"][-1]["content"]); t1 = time.time()
    try: out = ask(e["messages"][:-1])
    except Exception as ex: print("ERROR", ex); out = ""
    secs.append(time.time() - t1); pr = parse(out); n += 1
    print(f"{i+1}/{len(rows)}", end="\r")
    if not isinstance(pr, dict): continue
    if task == "cx":
        if "timeComplexity" in pr and "spaceComplexity" in pr:
            valid += 1; t_hit += norm(ref["timeComplexity"]) == norm(pr["timeComplexity"]); s_hit += norm(ref["spaceComplexity"]) == norm(pr["spaceComplexity"])
    else:
        try:
            sc = float(pr["score"]); valid += 1; hr_err.append(abs(ref["score"] - sc))
            if ref["isIrrelevant"]: irr_ref += 1; irr_ok += (sc == 0)
            else: rel_ref += 1; false_zero += (sc == 0)
        except Exception: pass
res = {"model": model, "task": task, "rows": n, "valid_json": valid, "seconds_per_row_median": sorted(secs)[len(secs)//2], "total_minutes": round((time.time()-t0)/60, 1)}
if task == "cx": res.update({"time_exact": t_hit, "space_exact": s_hit})
else: res.update({"score_mae": round(sum(hr_err)/len(hr_err), 2) if hr_err else None, "irrelevant_scored_0": f"{irr_ok}/{irr_ref}", "relevant_wrongly_0": f"{false_zero}/{rel_ref}"})
print("\n" + json.dumps(res, indent=2))
open(f"results_{model.replace(':','_').replace('/','_')}_{task}.json", "w").write(json.dumps(res, indent=2))
