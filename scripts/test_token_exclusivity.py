import sys
import os
import re
import json
import numpy as np
sys.path.insert(0, os.path.abspath("scripts"))
from test_v4 import _THEORY_ITEMS_LIST, _split_reference_key_points, evaluate_theory_v4

# Let's test modifying the exclusivity check in evaluate_theory_v4 to use token allocation
def check_exclusivity(kp_info):
    credited = [k for k in kp_info if k["decision"] in ("covered", "partial")]
    if len(credited) > 1:
        credited.sort(key=lambda k: k["best_sim"], reverse=True)
        allocated_tokens = set()
        allocated_anchors = set()
        for k in credited:
            # Map of anchor -> matched_word
            matched_dict = k["matched_dict"]
            # Words in the answer that this KP uses and hasn't been claimed yet
            own_words = {w for a, w in matched_dict.items() if w not in allocated_tokens}
            own_anchors = {a for a, w in matched_dict.items() if a not in allocated_anchors and w not in allocated_tokens}
            
            if len(own_words) == 0 or len(own_anchors) == 0:
                k["decision"] = "missed"
            elif k["min_anchors"] >= 2 and len(own_anchors) < 2 and len(own_words) < 2:
                k["decision"] = "missed"
            else:
                allocated_tokens.update(matched_dict.values())
                allocated_anchors.update(matched_dict.keys())

print("Testing token-based exclusivity on the 4 outlier questions...", flush=True)
# Let's test directly
from test_v4 import evaluate_theory_v4

# We'll import evaluate_theory_v4 and test on dbms-theory-083, java-theory-053, dbms-theory-065, dbms-theory-070
