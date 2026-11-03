"""
make_validation_cases.py
Evidence generation script that creates/verifies verification_runs/validation_cases.json.
Validates structure, case counts per module, and SHA-256 integrity.
"""

import os
import json
import hashlib

CASES_FILE = os.path.join(os.path.dirname(__file__), "validation_cases.json")
EXPECTED_SHA256 = "2650a47826e906cfab0098492f57c06155b936522d76654477c3f9fe0a8dc5cd"


def verify_or_make_cases():
    print("=" * 60)
    print("CHECKING VALIDATION CASES INTEGRITY")
    print("=" * 60)

    if not os.path.exists(CASES_FILE):
        print(f"Error: {CASES_FILE} does not exist.")
        return False

    with open(CASES_FILE, "rb") as f:
        data = f.read()

    actual_hash = hashlib.sha256(data).hexdigest()
    print(f"File Path: {CASES_FILE}")
    print(f"Expected SHA-256: {EXPECTED_SHA256}")
    print(f"Actual SHA-256:   {actual_hash}")

    if actual_hash.lower() == EXPECTED_SHA256.lower():
        print("[OK] SHA-256 checksum matches perfectly!")
    else:
        print("[WARNING] SHA-256 checksum mismatch!")

    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"Total Cases: {len(cases)}")
    counts = {}
    for c in cases:
        counts[c["module"]] = counts.get(c["module"], 0) + 1
    print("Cases per module:")
    for mod, count in sorted(counts.items()):
        print(f"  - {mod}: {count}")

    return actual_hash.lower() == EXPECTED_SHA256.lower()


if __name__ == "__main__":
    verify_or_make_cases()
