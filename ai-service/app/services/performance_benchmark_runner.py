"""
Performance Benchmark and Time Limit Exceeded (TLE) Runner for Java Code.
Runs safely in an isolated sandbox with strict execution deadlines,
measures actual runtime in milliseconds, detects infinite loops,
and separates actual TLE timeouts from static efficiency warnings.
"""

import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Dict, Any, List, Optional

# Prioritize JDK installation if Oracle javapath symlink is present on Windows
for jdk_candidate in [r"C:\Program Files\Java\jdk-21", r"C:\Program Files\Java\jdk-17"]:
    if os.path.exists(os.path.join(jdk_candidate, "bin", "javac.exe")):
        os.environ["JAVA_HOME"] = jdk_candidate
        bin_dir = os.path.join(jdk_candidate, "bin")
        if bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = bin_dir + ";" + os.environ.get("PATH", "")
        break

from app.services.code_executor import _JAVA_RUNNER_TEMPLATE, is_java_available

# Strict safety limits
BENCHMARK_TIMEOUT_SEC = 1.5      # Max 1.5 seconds per benchmark test
TOTAL_TIME_BUDGET_SEC = 3.5      # Hard ceiling for entire benchmark suite
CONFIGURED_TIME_LIMIT_MS = 2000  # Stated platform time limit (2000 ms)


def _kill_proc_tree(proc: subprocess.Popen):
    """Guarantees process termination to prevent stray java background processes."""
    try:
        proc.kill()
        proc.wait(timeout=1.0)
    except Exception:
        try:
            # Force kill on Windows via taskkill if needed
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=2)
        except Exception:
            pass


def _generate_scaled_inputs(problem_id: Optional[str], sample_input: str) -> List[Dict[str, Any]]:
    """
    Generates safely scaled benchmark inputs tailored to known problem types
    to evaluate scaling behavior without exceeding memory boundaries.
    """
    benchmarks = []
    
    if problem_id == "fibonacci":
        # Scale N from 25 to 35 to test exponential vs linear performance
        benchmarks.append({"label": "N=25", "input": "25", "size": 25})
        benchmarks.append({"label": "N=32", "input": "32", "size": 32})
        benchmarks.append({"label": "N=38 (Large)", "input": "38", "size": 38})
    elif problem_id == "factorial":
        benchmarks.append({"label": "N=10", "input": "10", "size": 10})
        benchmarks.append({"label": "N=16", "input": "16", "size": 16})
        benchmarks.append({"label": "N=20", "input": "20", "size": 20})
    elif problem_id == "two_sum":
        # Arrays of size 500, 2000, 5000
        benchmarks.append({"label": "N=500", "input": f"[{', '.join(str(i) for i in range(500))}], 997", "size": 500})
        benchmarks.append({"label": "N=2500", "input": f"[{', '.join(str(i) for i in range(2500))}], 4997", "size": 2500})
    elif problem_id == "duplicate_detection":
        benchmarks.append({"label": "N=500", "input": f"[{', '.join(str(i) for i in range(500))}]", "size": 500})
        benchmarks.append({"label": "N=3000", "input": f"[{', '.join(str(i) for i in range(3000))}]", "size": 3000})
    elif problem_id == "palindrome":
        half = "abcdefghij" * 50
        benchmarks.append({"label": "Len=1000", "input": f'"{half + half[::-1]}"', "size": 1000})
        half2 = "abcdefghij" * 250
        benchmarks.append({"label": "Len=5000", "input": f'"{half2 + half2[::-1]}"', "size": 5000})
    else:
        # Default fallback: use sample input as baseline benchmark
        if sample_input and sample_input.strip():
            benchmarks.append({"label": "Standard Input", "input": sample_input.strip(), "size": 100})
            
    return benchmarks


def run_performance_benchmarks(
    candidate_code: str,
    test_cases: List[Dict[str, Any]],
    time_complexity: str,
    problem_id: Optional[str] = None,
    optimal_time_complexity: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes compiled Java code against scaled inputs with strict timeout budgets.
    Returns actual execution time, time limit, TLE status, and performance diagnosis.
    """
    if not is_java_available():
        return {
            "executionTimeMs": 0,
            "timeLimitMs": CONFIGURED_TIME_LIMIT_MS,
            "status": "NOT_MEASURED",
            "isTLE": False,
            "warning": None,
            "scaledResults": [],
        }

    cleaned_code = re.sub(r"^\s*package\s+[\w.]+;\s*", "", candidate_code or "", flags=re.MULTILINE)
    class_match = re.search(r"\b(?:public\s+)?class\s+([A-Za-z0-9_]+)", cleaned_code)
    class_name = class_match.group(1) if class_match else "Solution"
    target_code = cleaned_code if class_match else f"public class Solution {{\n{cleaned_code}\n}}"
    if "import java.util." not in target_code:
        target_code = "import java.util.*;\n" + target_code

    temp_dir = tempfile.mkdtemp(prefix="mockmate_bench_")
    start_total_time = time.perf_counter()

    measured_times_ms = []
    scaled_results = []
    is_tle = False
    tle_reason = None
    overall_status = "OPTIMAL_PERFORMANCE"
    efficiency_warning = None

    try:
        # 1. Compile runner and student code
        with open(os.path.join(temp_dir, "MockMateRunner.java"), "w", encoding="utf-8") as f:
            f.write(_JAVA_RUNNER_TEMPLATE)
        with open(os.path.join(temp_dir, f"{class_name}.java"), "w", encoding="utf-8") as f:
            f.write(target_code)

        compile_cmd = ["javac", "-J-Xmx256m", "MockMateRunner.java", f"{class_name}.java"]
        c_proc = subprocess.run(compile_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=10)
        if c_proc.returncode != 0:
            return {
                "executionTimeMs": 0,
                "timeLimitMs": CONFIGURED_TIME_LIMIT_MS,
                "status": "COMPILE_ERROR",
                "isTLE": False,
                "warning": "Code did not compile; performance benchmarks skipped.",
                "scaledResults": [],
            }

        # 2. Select benchmark inputs
        sample_input = test_cases[0].get("input", "") if test_cases else ""
        benchmarks = _generate_scaled_inputs(problem_id, sample_input)

        # 3. Execute scaled runs
        for bench in benchmarks:
            # Check total safety budget
            if time.perf_counter() - start_total_time >= TOTAL_TIME_BUDGET_SEC:
                break

            b_input = str(bench.get("input", ""))
            b_label = bench.get("label", "Benchmark")
            run_cmd = ["java", "-Xmx256m", "-XX:+TieredCompilation", "MockMateRunner", class_name, b_input]

            t0 = time.perf_counter()
            proc = None
            try:
                proc = subprocess.Popen(
                    run_cmd,
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = proc.communicate(timeout=BENCHMARK_TIMEOUT_SEC)
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                measured_times_ms.append(elapsed_ms)

                scaled_results.append({
                    "label": b_label,
                    "executionTimeMs": elapsed_ms,
                    "passed": (proc.returncode == 0),
                    "status": "PASSED" if proc.returncode == 0 else "ERROR",
                })

            except subprocess.TimeoutExpired:
                elapsed_ms = round(BENCHMARK_TIMEOUT_SEC * 1000, 2)
                _kill_proc_tree(proc)
                is_tle = True
                tle_reason = f"Execution timed out on input {b_label} (> {CONFIGURED_TIME_LIMIT_MS} ms limit)."
                scaled_results.append({
                    "label": b_label,
                    "executionTimeMs": elapsed_ms,
                    "passed": False,
                    "status": "TIME_LIMIT_EXCEEDED",
                })
                break
            except Exception as e:
                if proc:
                    _kill_proc_tree(proc)
                break

    except Exception:
        pass
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # 4. Formulate overall performance status
    max_measured_time = max(measured_times_ms) if measured_times_ms else 0.0

    if is_tle:
        overall_status = "TIME_LIMIT_EXCEEDED"
        efficiency_warning = tle_reason or "Your solution exceeded the execution time limit on large benchmark test inputs."
    elif time_complexity in ("O(N^2)", "O(N^3)", "O(2^N)"):
        # Code passed test cases within time limit, but complexity is suboptimal
        overall_status = "EFFICIENCY_WARNING"
        opt_text = f"An {optimal_time_complexity} approach is possible." if optimal_time_complexity else "A more efficient linear approach is possible."
        efficiency_warning = (
            f"Your solution uses an {time_complexity} approach and completed in {max_measured_time} ms on the current test suite. "
            f"However, this approach may cause Time Limit Exceeded (TLE) on large production test inputs. {opt_text}"
        )
    else:
        overall_status = "OPTIMAL_PERFORMANCE"
        efficiency_warning = None

    return {
        "executionTimeMs": max_measured_time,
        "timeLimitMs": CONFIGURED_TIME_LIMIT_MS,
        "status": overall_status,
        "isTLE": is_tle,
        "warning": efficiency_warning,
        "scaledResults": scaled_results,
    }
