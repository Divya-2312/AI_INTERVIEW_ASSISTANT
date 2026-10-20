"""
hr_gate.py - Deterministic topic check for the curated 100 HR interview questions.
An answer that contains none of a question's topic keywords is off-topic (irrelevant => score 0).
"""
import json
import os
import re

STOP = set("""a an the and or but if then so of to in on at for with without from by as is are was were be been being am do does did
have has had i me my mine we our us you your he she it its they them their this that these those there here what which who whom
when where why how not no yes can could would should will shall may might must just very really also too than about into over
under up down out off again more most some any each other such only own same s t don""".split())

def stem(w: str) -> str:
    w = (w or "").lower()
    if w.endswith("ies") and len(w) > 5:
        w = w[:-3] + "y"
    elif w.endswith("sses"):
        w = w[:-2]
    else:
        for suf in ("ing", "ed", "ly", "es", "s"):
            if len(w) > len(suf) + 3 and w.endswith(suf) and not (suf == "s" and w.endswith("ss")):
                w = w[: -len(suf)]
                break
    if len(w) > 4 and w.endswith("e"):
        w = w[:-1]
    return w

def toks(s: str) -> list:
    return re.findall(r"[a-z']+", (s or "").lower())

def content(s: str) -> set:
    return {stem(w) for w in toks(s) if w not in STOP and len(w) > 2}

_GENERIC_Q = content("tell describe time think would like know give example anything else please way")
_FILLER = content("work job hard calm teamwork dedication important thing best try stay face situation whenever believe always")

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_PATH = os.path.abspath(os.path.join(_HERE, "..", "data", "hr_india_100.json"))
_ITEMS = None
_ITEMS_LIST = None

def items_list():
    global _ITEMS_LIST
    if _ITEMS_LIST is None:
        if os.path.exists(_DATA_PATH):
            with open(_DATA_PATH, "r", encoding="utf-8") as f:
                _ITEMS_LIST = json.load(f)
        else:
            _ITEMS_LIST = []
    return _ITEMS_LIST

def items_map():
    global _ITEMS
    if _ITEMS is None:
        _ITEMS = {x["question"].strip().lower(): x for x in items_list()}
        for x in items_list():
            if "id" in x:
                _ITEMS[x["id"].strip().lower()] = x
    return _ITEMS

def find_hr_item(question_or_id: str):
    if not question_or_id:
        return None
    key = str(question_or_id).strip().lower()
    m = items_map()
    if key in m:
        return m[key]
    # Check normalized substring match
    for q_text, item in m.items():
        if key in q_text or q_text in key:
            return item
    return None

def topic_hits(question: str, answer: str) -> int:
    """Number of this question's topic keywords found in the answer."""
    it = find_hr_item(question)
    if not it:
        # If question is not in the 100 curated set, fallback to question content tokens
        q_content = content(question) - _GENERIC_Q
        return len(content(answer) & q_content)
    
    topic = ((content(it["question"]) - _GENERIC_Q) | content(" ".join(it.get("keywords", [])))) - _FILLER
    return len(content(answer) & topic)

def is_off_topic(question: str, answer: str) -> bool:
    """Return True if answer does not contain any relevant topic tokens."""
    if not (answer or "").strip():
        return True
    return topic_hits(question, answer) == 0
