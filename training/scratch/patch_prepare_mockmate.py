import re
from pathlib import Path

target_file = Path(r"c:\Users\kavin\Downloads\MockMateAI-fresh\MockMateAI-Clean-Source\training\prepare_mockmate_datasets.py")
text = target_file.read_text(encoding="utf-8")

# Find from "def generate_hr_evaluations" to right before "def summarize_conversion"
start_marker = "def generate_hr_evaluations(hr_records):"
end_marker = "def summarize_conversion(rows):"

idx_start = text.find(start_marker)
idx_end = text.find(end_marker)

if idx_start == -1 or idx_end == -1:
    raise ValueError(f"Markers not found: start={idx_start}, end={idx_end}")

replacement = (
    "# Note: generate_hr_evaluations and generate_complexity_analysis_records are imported\n"
    "# from generate_extra_training_tasks above to guarantee zero data leakage and O(N^3)/O(2^N) support.\n\n\n"
)

new_text = text[:idx_start] + replacement + text[idx_end:]
target_file.write_text(new_text, encoding="utf-8")
print(f"Successfully patched {target_file}")
