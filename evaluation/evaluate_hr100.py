"""Evaluates the model ONLY on the 100 India HR questions, with validation answers it never trained on.
Also checks the scoring RULE: irrelevant answer => score 0, any relevant (even partial) answer => score >= 1.
Run in the folder that has the NEW validation.jsonl, hr_india_100.json (and mockmate_client.py is NOT needed)."""
import json, re, urllib.request
from collections import defaultdict

MODEL, URL = "mockmate-hr100", "http://localhost:11434/api/chat"      # change MODEL if you named the new model differently
TASK_RE = re.compile(r"TASK:\s*(\S+)\s*\nINPUT:\s*(\{.*\})\s*\n\s*\nReturn", re.S)
india = {x["question"]: x for x in json.load(open("hr_india_100.json", encoding="utf-8"))}

def ask(messages):
    body = json.dumps({"model": MODEL, "messages": messages, "stream": False,
                       "options": {"temperature": 0, "num_predict": 700}}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=300))["message"]["content"]
def jl(s):
    try: return json.loads(s)
    except Exception: return None

rows = []
for line in open("validation.jsonl", encoding="utf-8"):
    e = json.loads(line); u = next(m["content"] for m in e["messages"] if m["role"] == "user")
    m = TASK_RE.search(u)
    if m and m.group(1) == "evaluate_answer" and json.loads(m.group(2)).get("question") in india:
        rows.append((e, json.loads(m.group(2))["question"]))
import sys, random
if len(sys.argv) > 1:                      # optional: python evaluate_hr100.py 50   -> random sample of 50 rows
    random.seed(0); rows = random.sample(rows, min(int(sys.argv[1]), len(rows)))
    print("using a random sample of", len(rows), "rows")
print(f"{len(rows)} validation rows covering {len({q for _, q in rows})} of 100 questions")
assert rows, "No rows matched the 100 questions - you probably used the OLD validation.jsonl. Download the NEW one from Drive: mockmate-data-hr100"

bad = n = 0; sc = []; per_q = defaultdict(list)
ref_irr = irr_caught = ref_rel = false_zero = 0          # irrelevant detection
rule_a = rule_b = 0                                      # the model's own outputs breaking the rule
for i, (e, q) in enumerate(rows):
    ref, pr = jl(e["messages"][-1]["content"]), jl(ask(e["messages"][:-1]))
    print(f"{i+1}/{len(rows)}", end="\r")
    try:
        err = abs(ref["score"] - pr["score"]); sc.append(err); per_q[q].append(err); n += 1
        if ref["isIrrelevant"]:
            ref_irr += 1; irr_caught += (bool(pr["isIrrelevant"]) and pr["score"] == 0)
        else:
            ref_rel += 1; false_zero += (pr["score"] == 0 or bool(pr["isIrrelevant"]))
        rule_a += (bool(pr["isIrrelevant"]) and pr["score"] != 0)
        rule_b += ((not pr["isIrrelevant"]) and pr["score"] < 1)
    except Exception:
        bad += 1
mean = lambda v: sum(v) / len(v) if v else float("nan")
print(f"\nparsed {n}, invalid JSON {bad}")
print(f"score MAE: {mean(sc):.1f} points")
print(f"irrelevant answers correctly scored 0 : {irr_caught}/{ref_irr}")
print(f"relevant answers wrongly scored 0     : {false_zero}/{ref_rel}   (should be 0 or close)")
print(f"model output breaking the rule        : irrelevant but score>0 = {rule_a}, relevant but score<1 = {rule_b}")
worst = sorted(per_q.items(), key=lambda kv: -mean(kv[1]))[:5]
print("5 questions with the largest score error:")
for q, v in worst: print(f"  {mean(v):5.1f}  {q}")
