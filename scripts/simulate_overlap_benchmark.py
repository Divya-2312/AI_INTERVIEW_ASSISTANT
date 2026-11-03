"""
Simulation and Benchmark Script for Question Overlap & Repetition.
Measures shared catalogue questions for:
  Subject (java, dbms) x Difficulty (easy, medium, hard)
Simulating 20 sessions for one user across:
  - First 6 sessions
  - First 10 sessions
  - First 20 sessions
Comparing:
  1. Old Algorithm (hard 5-session exclusion without full-history ranking)
  2. New Algorithm (ranking over full 30-session history: never asked, least asked, oldest)
Reports max and average shared questions for consecutive sessions and any two sessions.
"""

import os
import sys
import json
import random
from typing import List, Dict, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_SERVICE_DIR = os.path.join(BASE_DIR, "ai-service")
if AI_SERVICE_DIR not in sys.path:
    sys.path.insert(0, AI_SERVICE_DIR)

from app.models.llama_provider import _GUARANTEED_UNIQUE_THEORY_QUESTIONS
from app.services.embedding_service import embedding_service


def simulate_old_algorithm(subject: str, difficulty: str, num_sessions: int = 20, session_len: int = 10) -> List[List[str]]:
    """
    Simulates the OLD algorithm:
    - Maintains exclusion list of question IDs and texts from the last 5 sessions.
    - No compact history / ranking across 30 sessions.
    - When catalogue candidates are filtered by last 5 sessions, if exhausted, picks randomly or loops.
    """
    catalog = list(_GUARANTEED_UNIQUE_THEORY_QUESTIONS.get((subject, difficulty), []))
    sessions = []

    for s_idx in range(num_sessions):
        # Exclusions from last 5 sessions
        recent_5 = sessions[-5:] if sessions else []
        exclude_ids = {qid for sess in recent_5 for qid in sess}
        
        session_qs = []
        for q_idx in range(session_len):
            # Filter candidates not in current session and not in last 5 sessions
            curr_exclude = exclude_ids | set(session_qs)
            candidates = [q["id"] for q in catalog if q["id"] not in curr_exclude]
            
            if not candidates:
                # Old fallback: bank exhausted, relax last 5 sessions check, only exclude current session
                candidates = [q["id"] for q in catalog if q["id"] not in set(session_qs)]
            
            if not candidates:
                candidates = [q["id"] for q in catalog]
            
            # Deterministic/seeded pseudo-random pick
            rng = random.Random(f"old:{subject}:{difficulty}:{s_idx}:{q_idx}")
            chosen = rng.choice(candidates)
            session_qs.append(chosen)

        sessions.append(session_qs)

    return sessions


def simulate_new_algorithm(subject: str, difficulty: str, num_sessions: int = 20, session_len: int = 10) -> List[List[str]]:
    """
    Simulates the NEW algorithm:
    - Tracks user history across up to 30 sessions: { questionId, timesAsked, lastAskedSessionIndex }
    - Ranks candidates by:
        1. Never asked by this user (timesAsked == 0)
        2. Asked fewest times (timesAsked ascending)
        3. Asked longest ago (lastAskedSessionIndex ascending)
      Random tie-break with per-session seed.
    - Excludes questions asked in the current session.
    """
    catalog = list(_GUARANTEED_UNIQUE_THEORY_QUESTIONS.get((subject, difficulty), []))
    sessions = []

    for s_idx in range(num_sessions):
        # Build compact history from up to last 30 sessions
        history_slice = sessions[-30:] if sessions else []
        hist_map = {}
        for past_idx, sess in enumerate(history_slice):
            for qid in sess:
                if qid not in hist_map:
                    hist_map[qid] = {"timesAsked": 0, "lastAskedSessionIndex": past_idx}
                hist_map[qid]["timesAsked"] += 1
                hist_map[qid]["lastAskedSessionIndex"] = past_idx

        session_qs = []
        for q_idx in range(session_len):
            # Candidates must not repeat in current session
            candidates = [q for q in catalog if q["id"] not in set(session_qs)]
            if not candidates:
                candidates = list(catalog)

            def rank_key(q):
                qid = q["id"]
                h = hist_map.get(qid)
                if h:
                    times = h["timesAsked"]
                    last_i = h["lastAskedSessionIndex"]
                else:
                    times = 0
                    last_i = -1
                seed_str = f"new:{subject}:{difficulty}:{s_idx}:{q_idx}:{qid}"
                tie = random.Random(seed_str).random()
                return (times, last_i, tie)

            candidates.sort(key=rank_key)
            chosen = candidates[0]["id"]
            session_qs.append(chosen)

        sessions.append(session_qs)

    return sessions


def compute_metrics(sessions: List[List[str]], limit: int) -> Dict[str, float]:
    """Computes max and avg shared questions for consecutive and any two sessions up to limit."""
    sub_sessions = sessions[:limit]
    n = len(sub_sessions)

    # 1. Consecutive sessions
    consec_shared = []
    for i in range(n - 1):
        s1 = set(sub_sessions[i])
        s2 = set(sub_sessions[i + 1])
        consec_shared.append(len(s1 & s2))

    max_consec = max(consec_shared) if consec_shared else 0
    avg_consec = (sum(consec_shared) / len(consec_shared)) if consec_shared else 0.0

    # 2. Any two sessions (pairwise)
    pair_shared = []
    for i in range(n):
        for j in range(i + 1, n):
            s1 = set(sub_sessions[i])
            s2 = set(sub_sessions[j])
            pair_shared.append(len(s1 & s2))

    max_pair = max(pair_shared) if pair_shared else 0
    avg_pair = (sum(pair_shared) / len(pair_shared)) if pair_shared else 0.0

    return {
        "max_consec": max_consec,
        "avg_consec": round(avg_consec, 2),
        "max_pair": max_pair,
        "avg_pair": round(avg_pair, 2),
    }


def run_benchmark():
    subjects = ["java", "dbms"]
    difficulties = ["easy", "medium", "hard"]
    limits = [6, 10, 20]

    results = {}

    for subj in subjects:
        results[subj] = {}
        for diff in difficulties:
            bank_size = len(_GUARANTEED_UNIQUE_THEORY_QUESTIONS.get((subj, diff), []))
            old_sess = simulate_old_algorithm(subj, diff, num_sessions=20, session_len=10)
            new_sess = simulate_new_algorithm(subj, diff, num_sessions=20, session_len=10)

            results[subj][diff] = {
                "bank_size": bank_size,
                "old": {},
                "new": {}
            }

            for lim in limits:
                results[subj][diff]["old"][lim] = compute_metrics(old_sess, lim)
                results[subj][diff]["new"][lim] = compute_metrics(new_sess, lim)

    # Output formatted JSON and Markdown tables
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run_benchmark()
