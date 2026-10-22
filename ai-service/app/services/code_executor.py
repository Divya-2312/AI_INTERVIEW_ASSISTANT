"""
Deterministic Code Execution Engine for AI Interview Assistant.
Handles local sandbox execution for Java (via javac/java subprocess) and SQL (via in-memory SQLite).
Provides 100% reproducible, deterministic test case evaluation without LLM hallucination.
"""

import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from typing import List, Dict, Any, Tuple, Optional

# Limit standard output from user programs to prevent memory exhaustion
MAX_OUTPUT_BYTES = 64 * 1024  # 64 KB
DEFAULT_TIMEOUT_SEC = 5.0

_JAVA_AVAILABLE: Optional[bool] = None


def is_java_available() -> bool:
    """Check if JDK (javac and java) is installed and accessible on PATH."""
    global _JAVA_AVAILABLE
    if _JAVA_AVAILABLE is not None:
        return _JAVA_AVAILABLE

    javac_path = shutil.which("javac")
    java_path = shutil.which("java")
    if not javac_path or not java_path:
        _JAVA_AVAILABLE = False
        return False

    try:
        j_ver = subprocess.run([javac_path, "-version"], capture_output=True, text=True, timeout=3)
        _JAVA_AVAILABLE = (j_ver.returncode == 0)
    except Exception:
        _JAVA_AVAILABLE = False

    return _JAVA_AVAILABLE


# Java test harness template that dynamically loads candidate classes and runs test cases.
_JAVA_RUNNER_TEMPLATE = r'''
import java.lang.reflect.*;
import java.util.*;

public class MockMateRunner {
    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: MockMateRunner <TargetClassName> [InputString]");
            System.exit(1);
        }
        String targetClassName = args[0];
        String rawInput = args.length > 1 ? args[1] : "";

        try {
            Class<?> targetClass = Class.forName(targetClassName);
            Method[] methods = targetClass.getDeclaredMethods();
            Method targetMethod = null;

            // Prioritize non-main solver methods
            for (Method m : methods) {
                if (!m.getName().equals("main") && !Modifier.isPrivate(m.getModifiers()) && !m.isSynthetic()) {
                    targetMethod = m;
                    break;
                }
            }
            if (targetMethod == null) {
                for (Method m : methods) {
                    if (m.getName().equals("main") && !m.isSynthetic()) {
                        targetMethod = m;
                        break;
                    }
                }
            }

            if (targetMethod == null) {
                System.err.println("No executable method found in class " + targetClassName);
                System.exit(2);
            }

            targetMethod.setAccessible(true);
            Object targetInstance = Modifier.isStatic(targetMethod.getModifiers())
                ? null
                : targetClass.getDeclaredConstructor().newInstance();

            Class<?>[] paramTypes = targetMethod.getParameterTypes();
            Object[] invokedArgs = parseArguments(rawInput, paramTypes);

            Object result = targetMethod.invoke(targetInstance, invokedArgs);
            System.out.print(formatOutput(result));
        } catch (InvocationTargetException ite) {
            Throwable cause = ite.getCause() != null ? ite.getCause() : ite;
            System.err.println("RUNTIME_ERROR: " + cause.toString());
            System.exit(3);
        } catch (Exception e) {
            System.err.println("RUNTIME_ERROR: " + e.toString());
            System.exit(3);
        }
    }

    public static Object[] parseArguments(String rawInput, Class<?>[] paramTypes) {
        if (paramTypes.length == 0) return new Object[0];

        List<String> rawTokens = splitArgs(rawInput, paramTypes.length);
        Object[] args = new Object[paramTypes.length];
        for (int i = 0; i < paramTypes.length; i++) {
            String token = i < rawTokens.size() ? rawTokens.get(i).trim() : "";
            args[i] = parseSingleArg(token, paramTypes[i]);
        }
        return args;
    }

    private static List<String> splitArgs(String input, int expectedCount) {
        List<String> list = new ArrayList<>();
        if (expectedCount <= 1) {
            list.add(input.trim());
            return list;
        }

        int depth = 0;
        boolean inQuotes = false;
        StringBuilder current = new StringBuilder();
        for (int i = 0; i < input.length(); i++) {
            char c = input.charAt(i);
            if (c == '"' && (i == 0 || input.charAt(i - 1) != '\\')) {
                inQuotes = !inQuotes;
                current.append(c);
            } else if (!inQuotes && (c == '[' || c == '{' || c == '(')) {
                depth++;
                current.append(c);
            } else if (!inQuotes && (c == ']' || c == '}' || c == ')')) {
                depth--;
                current.append(c);
            } else if (!inQuotes && c == ',' && depth == 0) {
                list.add(current.toString().trim());
                current.setLength(0);
            } else {
                current.append(c);
            }
        }
        if (current.length() > 0) {
            list.add(current.toString().trim());
        }
        return list;
    }

    private static Object parseSingleArg(String s, Class<?> type) {
        String clean = s.trim();
        if (type == int.class || type == Integer.class) {
            clean = clean.replaceAll("[^0-9-]", "");
            return clean.isEmpty() ? 0 : Integer.parseInt(clean);
        }
        if (type == long.class || type == Long.class) {
            clean = clean.replaceAll("[^0-9-]", "");
            return clean.isEmpty() ? 0L : Long.parseLong(clean);
        }
        if (type == double.class || type == Double.class) {
            return clean.isEmpty() ? 0.0 : Double.parseDouble(clean);
        }
        if (type == float.class || type == Float.class) {
            return clean.isEmpty() ? 0.0f : Float.parseFloat(clean);
        }
        if (type == boolean.class || type == Boolean.class) {
            return Boolean.parseBoolean(clean);
        }
        if (type == char.class || type == Character.class) {
            clean = clean.replaceAll("^'|'$", "");
            return clean.isEmpty() ? ' ' : clean.charAt(0);
        }
        if (type == String.class) {
            if (clean.startsWith("\"") && clean.endsWith("\"") && clean.length() >= 2) {
                return clean.substring(1, clean.length() - 1);
            }
            return clean;
        }
        if (type == int[].class) {
            String inner = clean.replaceAll("^[^{\\[]*[{\\[]", "").replaceAll("[}\\]][^}\\]]*$", "");
            if (inner.trim().isEmpty()) return new int[0];
            String[] parts = inner.split(",");
            int[] arr = new int[parts.length];
            for (int i = 0; i < parts.length; i++) {
                String p = parts[i].trim().replaceAll("[^0-9-]", "");
                arr[i] = p.isEmpty() ? 0 : Integer.parseInt(p);
            }
            return arr;
        }
        if (type == long[].class) {
            String inner = clean.replaceAll("^[^{\\[]*[{\\[]", "").replaceAll("[}\\]][^}\\]]*$", "");
            if (inner.trim().isEmpty()) return new long[0];
            String[] parts = inner.split(",");
            long[] arr = new long[parts.length];
            for (int i = 0; i < parts.length; i++) {
                String p = parts[i].trim().replaceAll("[^0-9-]", "");
                arr[i] = p.isEmpty() ? 0L : Long.parseLong(p);
            }
            return arr;
        }
        if (type == String[].class) {
            String inner = clean.replaceAll("^[^{\\[]*[{\\[]", "").replaceAll("[}\\]][^}\\]]*$", "");
            if (inner.trim().isEmpty()) return new String[0];
            String[] parts = inner.split(",");
            String[] arr = new String[parts.length];
            for (int i = 0; i < parts.length; i++) {
                String p = parts[i].trim();
                if (p.startsWith("\"") && p.endsWith("\"") && p.length() >= 2) {
                    p = p.substring(1, p.length() - 1);
                }
                arr[i] = p;
            }
            return arr;
        }
        if (type == char[].class) {
            String inner = clean.replaceAll("^[^{\\[]*[{\\[]", "").replaceAll("[}\\]][^}\\]]*$", "");
            if (inner.trim().isEmpty()) return new char[0];
            String[] parts = inner.split(",");
            char[] arr = new char[parts.length];
            for (int i = 0; i < parts.length; i++) {
                String p = parts[i].trim().replaceAll("^'|'$", "");
                arr[i] = p.isEmpty() ? ' ' : p.charAt(0);
            }
            return arr;
        }
        return clean;
    }

    public static String formatOutput(Object result) {
        if (result == null) return "null";
        if (result instanceof int[]) return Arrays.toString((int[]) result);
        if (result instanceof long[]) return Arrays.toString((long[]) result);
        if (result instanceof double[]) return Arrays.toString((double[]) result);
        if (result instanceof boolean[]) return String.valueOf(result);
        if (result instanceof char[]) return String.valueOf((char[]) result);
        if (result instanceof Object[]) return Arrays.deepToString((Object[]) result);
        if (result instanceof List) return result.toString();
        return String.valueOf(result);
    }
}
'''


def normalize_value_str(val: Any) -> str:
    """Normalize string representation of output for robust comparison."""
    if val is None:
        return ""
    text = str(val).strip()
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Normalize outer quotes if present
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        if len(text) >= 2:
            text = text[1:-1].strip()

    # Normalize booleans
    if text.lower() in ("true", "1"):
        return "true"
    if text.lower() in ("false", "0"):
        return "false"

    # Normalize brackets/whitespace: "[ 0,  1 ]" -> "[0, 1]"
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
        items = [i.strip() for i in inner.split(",") if i.strip()]
        return "[" + ", ".join(items) + "]"

    # Normalize decimal trailing zeros: "5.0" vs "5.00" -> "5" or numeric float
    try:
        f = float(text)
        if f.is_integer():
            return str(int(f))
        return str(round(f, 6))
    except (ValueError, TypeError):
        pass

    return text


def values_match(actual: Any, expected: Any) -> bool:
    """Compare actual and expected outputs with normalization."""
    act_norm = normalize_value_str(actual)
    exp_norm = normalize_value_str(expected)
    if act_norm == exp_norm:
        return True

    # Case-insensitive check
    if act_norm.lower() == exp_norm.lower():
        return True

    # Check without spaces
    if re.sub(r"\s+", "", act_norm) == re.sub(r"\s+", "", exp_norm):
        return True

    return False


def execute_java(candidate_code: str, test_cases: List[Dict[str, Any]], timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> Dict[str, Any]:
    """
    Deterministically compile and execute candidate Java code in a temp directory.
    Returns per-testcase results and summary stats.
    """
    if not is_java_available():
        raise RuntimeError("Java Development Kit (javac/java) is not available.")

    test_cases = test_cases or []
    cleaned_code = re.sub(r"^\s*package\s+[\w.]+;\s*", "", candidate_code or "", flags=re.MULTILINE)

    # Determine class name
    class_match = re.search(r"\b(?:public\s+)?class\s+([A-Za-z0-9_]+)", cleaned_code)
    if class_match:
        class_name = class_match.group(1)
        target_code = cleaned_code
    else:
        class_name = "Solution"
        target_code = f"public class Solution {{\n{cleaned_code}\n}}"

    if "import java.util." not in target_code:
        target_code = "import java.util.*;\n" + target_code

    temp_dir = tempfile.mkdtemp(prefix="mockmate_java_")
    try:
        runner_path = os.path.join(temp_dir, "MockMateRunner.java")
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(_JAVA_RUNNER_TEMPLATE)

        solution_path = os.path.join(temp_dir, f"{class_name}.java")
        with open(solution_path, "w", encoding="utf-8") as f:
            f.write(target_code)

        # 1. Compile
        compile_cmd = ["javac", "-J-Xmx256m", "MockMateRunner.java", f"{class_name}.java"]
        c_proc = subprocess.run(compile_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=15)

        if c_proc.returncode != 0:
            err_output = (c_proc.stderr or c_proc.stdout or "Compilation failed").strip()
            # Clean directory paths from compiler output for candidate readability
            cleaned_err = re.sub(r"^[A-Za-z]:\\[^\n]*mockmate_java_[^\n\\]+\\", "", err_output, flags=re.MULTILINE)
            # Take the first 6 lines of javac output
            summary_err = "\n".join(cleaned_err.splitlines()[:6])

            results = []
            for i, tc in enumerate(test_cases):
                expected = tc.get("expectedOutput", tc.get("expected", ""))
                results.append({
                    "id": i + 1,
                    "input": tc.get("input", ""),
                    "expected": expected,
                    "actual": "",
                    "status": "COMPILE_ERROR",
                    "error": summary_err,
                    "passed": False,
                    "expectedOutput": expected,
                    "actualOutput": "",
                    "failureReason": summary_err,
                    "label": tc.get("label"),
                })
            return {
                "judgeMode": "deterministic",
                "compileError": summary_err,
                "passedCount": 0,
                "totalCount": len(test_cases),
                "results": results,
            }

        # 2. Execute each test case
        results = []
        passed_count = 0

        for i, tc in enumerate(test_cases):
            tc_input = str(tc.get("input", "")).strip()
            tc_expected = str(tc.get("expectedOutput", tc.get("expected", ""))).strip()

            run_cmd = ["java", "-Xmx256m", "MockMateRunner", class_name, tc_input]
            out_file = os.path.join(temp_dir, f"out_{i}.txt")
            err_file = os.path.join(temp_dir, f"err_{i}.txt")

            timed_out = False
            actual_out = ""
            err_out = ""
            ret_code = 0

            with open(out_file, "w", encoding="utf-8") as out_f, open(err_file, "w", encoding="utf-8") as err_f:
                p = subprocess.Popen(run_cmd, cwd=temp_dir, stdout=out_f, stderr=err_f)
                try:
                    ret_code = p.wait(timeout=timeout_sec)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                    else:
                        p.kill()
                    try:
                        p.wait(timeout=1)
                    except Exception:
                        pass

            if timed_out:
                passed = False
                status = "TIMEOUT"
                actual_out = ""
                err_msg = f"Execution timed out after {timeout_sec:.1f} seconds"
            else:
                if os.path.exists(out_file):
                    with open(out_file, "r", encoding="utf-8", errors="replace") as f:
                        actual_out = f.read(MAX_OUTPUT_BYTES).strip()
                if os.path.exists(err_file):
                    with open(err_file, "r", encoding="utf-8", errors="replace") as f:
                        err_out = f.read(MAX_OUTPUT_BYTES).strip()

                if ret_code == 0:
                    passed = values_match(actual_out, tc_expected)
                    status = "PASSED" if passed else "FAILED"
                    err_msg = None if passed else f"Expected: {tc_expected}, Got: {actual_out}"
                else:
                    passed = False
                    status = "RUNTIME_ERROR"
                    err_msg = err_out or f"Process exited with code {ret_code}"

            if passed:
                passed_count += 1

            results.append({
                "id": i + 1,
                "input": tc_input,
                "expected": tc_expected,
                "actual": actual_out,
                "status": status,
                "error": err_msg,
                "passed": passed,
                "expectedOutput": tc_expected,
                "actualOutput": actual_out,
                "failureReason": err_msg if not passed else "",
                "label": tc.get("label"),
            })

        return {
            "judgeMode": "deterministic",
            "compileError": None,
            "passedCount": passed_count,
            "totalCount": len(test_cases),
            "results": results,
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def execute_java_snippet(code: str, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> Tuple[bool, str, Optional[str]]:
    """
    Deterministically compiles and executes a standalone Java code snippet (e.g. for predict-the-output).
    Returns (success, actual_output, error_message).
    - If compilation fails, returns (False, "", compile_error).
    - If execution fails or times out, returns (False, "", error_message).
    - If succeeds, returns (True, stdout, None).
    """
    if not is_java_available():
        return False, "", "Java Development Kit (javac/java) is not available."

    if not code or not code.strip():
        return False, "", "Empty code snippet."

    cleaned = re.sub(r"^\s*package\s+[\w.]+;\s*", "", code or "", flags=re.MULTILINE).strip()

    # Reject snippets with multiple main() methods (e.g. glued distinct questions)
    main_matches = re.findall(r"\bpublic\s+static\s+void\s+main\s*\(", cleaned)
    if len(main_matches) > 1:
        return False, "", "Snippet contains multiple main() methods."

    # If no class at all, wrap inside class Main with main method
    if not re.search(r"\bclass\s+[A-Za-z0-9_]+", cleaned):
        cleaned = f"public class Main {{\n    public static void main(String[] args) {{\n        {cleaned}\n    }}\n}}"
    elif not re.search(r"\bpublic\s+static\s+void\s+main\s*\(", cleaned):
        return False, "", "No public static void main method found in snippet."

    # Find the class that contains the main method
    class_blocks = re.findall(r"(?:public\s+)?class\s+([A-Za-z0-9_]+)[^{]*\{([\s\S]*?)(?=\n\s*(?:public\s+)?class|\Z)", cleaned)
    main_class_name = None
    for cname, cbody in class_blocks:
        if "public static void main" in cbody:
            main_class_name = cname
            break

    if not main_class_name:
        m = re.search(r"\bclass\s+([A-Za-z0-9_]+)", cleaned)
        main_class_name = m.group(1) if m else "Main"

    # In a single .java file, only the class with main should be public; others must be package-private
    def make_single_public(match):
        cname = match.group(1)
        if cname == main_class_name:
            return f"public class {cname}"
        return f"class {cname}"

    target_code = re.sub(r"\bpublic\s+class\s+([A-Za-z0-9_]+)", make_single_public, cleaned)

    temp_dir = tempfile.mkdtemp(prefix="mockmate_java_snippet_")
    try:
        java_file = os.path.join(temp_dir, f"{main_class_name}.java")
        with open(java_file, "w", encoding="utf-8") as f:
            f.write(target_code)

        # 1. Compile
        c = subprocess.run(
            ["javac", "-J-Xmx256m", f"{main_class_name}.java"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if c.returncode != 0:
            cleaned_err = re.sub(
                r"^[A-Za-z]:\\[^\n]*mockmate_java_snippet_[^\n\\]+\\",
                "",
                c.stderr or c.stdout or "",
                flags=re.MULTILINE,
            )
            summary_err = "\n".join(cleaned_err.strip().splitlines()[:5])
            return False, "", summary_err

        # 2. Run with robust Windows timeout cleanup
        out_file = os.path.join(temp_dir, "stdout.txt")
        err_file = os.path.join(temp_dir, "stderr.txt")
        timed_out = False
        ret_code = 0
        with open(out_file, "w", encoding="utf-8") as out_f, open(err_file, "w", encoding="utf-8") as err_f:
            p = subprocess.Popen(["java", "-Xmx256m", main_class_name], cwd=temp_dir, stdout=out_f, stderr=err_f)
            try:
                ret_code = p.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                else:
                    p.kill()
                try:
                    p.wait(timeout=1)
                except Exception:
                    pass

        if timed_out:
            return False, "", "Execution timed out (possible infinite loop)"

        stdout_data = ""
        stderr_data = ""
        if os.path.exists(out_file):
            with open(out_file, "r", encoding="utf-8", errors="replace") as f:
                stdout_data = f.read(MAX_OUTPUT_BYTES)
        if os.path.exists(err_file):
            with open(err_file, "r", encoding="utf-8", errors="replace") as f:
                stderr_data = f.read(MAX_OUTPUT_BYTES)

        if ret_code != 0:
            err_msg = (stderr_data or stdout_data or "").strip()
            exc_m = re.search(r'Exception in thread "[^"]*"\s+([\w.$]+(?:Exception|Error))', err_msg)
            if exc_m:
                short_exc = exc_m.group(1).split(".")[-1]
                return True, short_exc, None
            return False, "", f"Runtime error (exit code {ret_code}): {err_msg[:200]}"

        out = stdout_data.replace("\r\n", "\n").replace("\r", "\n").strip()
        return True, out, None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def is_snippet_deterministic(code: str) -> Tuple[bool, str]:
    """
    Checks if a Java snippet contains non-deterministic or side-effect constructs.
    Reject:
    - Random, Math.random
    - System.currentTimeMillis, nanoTime
    - threads (Thread, Runnable, Executor, ForkJoin)
    - hashCode printing / identityHashCode
    - HashMap/HashSet iteration order
    - Input reading (Scanner, System.in, BufferedReader, InputStreamReader, Console)
    """
    if not code:
        return False, "Code is empty"

    forbidden_patterns = [
        (r"\bRandom\b", "Uses Random class"),
        (r"Math\.random\s*\(", "Uses Math.random()"),
        (r"System\.(currentTimeMillis|nanoTime)\s*\(", "Uses system clock"),
        (r"\bnanoTime\s*\(", "Uses nanoTime"),
        (r"\b(Thread|Runnable|ExecutorService|Executors|ForkJoinPool)\b", "Uses threads or concurrency"),
        (r"\.(hashCode|identityHashCode)\s*\(", "Prints or uses object hash codes"),
        (r"System\.identityHashCode\s*\(", "Uses System.identityHashCode"),
        (r"\b(Scanner|BufferedReader|InputStreamReader|Console)\b", "Reads user/system input"),
        (r"System\.in\b", "Reads from System.in"),
    ]

    for pat, desc in forbidden_patterns:
        if re.search(pat, code):
            return False, desc

    # Disallow HashMap / HashSet iteration which has undefined order in JVM
    if re.search(r"\b(HashMap|HashSet)\b", code):
        if re.search(r"\b(for\s*\(|\.forEach|\.iterator|\.keySet|\.values|\.entrySet)", code):
            return False, "Iterates non-deterministic HashMap/HashSet order"

    return True, ""


def verify_predict_output_snippet(code: str, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> Tuple[bool, str, Optional[str]]:
    """
    Verification pipeline for Predict-the-Output questions.
    Compiles and executes the snippet twice in the Java sandbox.
    Requires:
    - Code compiles cleanly
    - Deterministic across 2 runs (identical stdout)
    - Non-empty stdout
    - At most 15 lines of output
    - No non-deterministic or input-reading constructs
    Returns (True, canonical_stdout, None) or (False, "", error_reason).
    """
    ok_det, det_reason = is_snippet_deterministic(code)
    if not ok_det:
        return False, "", f"Non-deterministic construct detected: {det_reason}"

    # Run 1
    ok1, out1, err1 = execute_java_snippet(code, timeout_sec=timeout_sec)
    if not ok1:
        return False, "", f"Run 1 failed: {err1}"

    if not out1 or not out1.strip():
        return False, "", "Snippet prints nothing"

    lines = [l for l in out1.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    if len(lines) > 15:
        return False, "", f"Output exceeds 15 lines ({len(lines)} lines)"

    # Run 2
    ok2, out2, err2 = execute_java_snippet(code, timeout_sec=timeout_sec)
    if not ok2:
        return False, "", f"Run 2 failed: {err2}"

    if out1.strip() != out2.strip():
        return False, "", f"Non-deterministic output between run 1 ('{out1}') and run 2 ('{out2}')"

    # Canonical normalization
    norm_lines = [line.rstrip() for line in out1.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")]
    canon_out = "\n".join(norm_lines)
    return True, canon_out, None


def generate_deterministic_starter_code(method_signature: str, class_name: str = "Solution") -> str:
    """
    Builds starterCode deterministically from the parsed method signature only.
    Class wrapper, signature, '// Write your code here', and default return statement.
    Does NOT derive from model-written code.
    """
    clean_sig = re.sub(r"//[^\n]*", "", method_signature or "").strip()
    clean_sig = re.sub(r"/\*[\s\S]*?\*/", "", clean_sig).strip()
    clean_sig = clean_sig.rstrip("{;").strip()

    sig_m = re.search(
        r"\b(?:public|protected|private)?\s*(static\s+)?"
        r"([A-Za-z0-9_]+(?:<[A-Za-z0-9_,\s<>]+>)?(?:\[\s*\])*)\s+"
        r"([A-Za-z0-9_]+)\s*\(([^)]*)\)",
        clean_sig,
    )
    if not sig_m:
        return (
            f"public class {class_name} {{\n"
            "    public static int solve() {\n"
            "        // Write your code here\n"
            "        return 0;\n"
            "    }\n"
            "}"
        )

    is_static = bool(sig_m.group(1))
    return_type = sig_m.group(2).strip()
    method_name = sig_m.group(3).strip()
    params = sig_m.group(4).strip()

    full_sig = f"public static {return_type} {method_name}({params})"

    ret_clean = re.sub(r"\s+", "", return_type)
    if ret_clean == "void":
        default_ret = ""
    elif ret_clean in ("int", "long", "short", "byte"):
        default_ret = "        return 0;\n"
    elif ret_clean in ("double", "float"):
        default_ret = "        return 0.0;\n"
    elif ret_clean == "boolean":
        default_ret = "        return false;\n"
    elif ret_clean == "char":
        default_ret = "        return ' ';\n"
    elif ret_clean in ("String", "java.lang.String"):
        default_ret = '        return "";\n'
    elif ret_clean == "int[]":
        default_ret = "        return new int[0];\n"
    elif ret_clean == "String[]":
        default_ret = "        return new String[0];\n"
    elif ret_clean.endswith("[]"):
        base_t = ret_clean[:-2]
        default_ret = f"        return new {base_t}[0];\n"
    elif "List" in ret_clean:
        default_ret = "        return new java.util.ArrayList<>();\n"
    elif "Map" in ret_clean:
        default_ret = "        return new java.util.HashMap<>();\n"
    elif "Set" in ret_clean:
        default_ret = "        return new java.util.HashSet<>();\n"
    else:
        default_ret = "        return null;\n"

    return (
        f"public class {class_name} {{\n"
        f"    {full_sig} {{\n"
        "        // Write your code here\n"
        f"{default_ret}"
        "    }\n"
        "}"
    )


def check_starter_code_leak(starter_code: str, reference_solution: str = None) -> Tuple[bool, str]:
    """
    Strict leak guard for starterCode:
    - Fails if it contains any loop (for, while, do)
    - Fails if it contains if, switch, or ternary (? ... :)
    - Fails if it has more than one statement besides the default return
    - Fails if token similarity to referenceSolution is above 0.6
    """
    if not starter_code or not starter_code.strip():
        return False, "Starter code is empty"

    clean = re.sub(r"//[^\n]*", "", starter_code)
    clean = re.sub(r"/\*[\s\S]*?\*/", "", clean)
    clean_no_strings = re.sub(r'"(?:\\.|[^"\\])*"', '""', clean)

    # 1. Check for loops
    if re.search(r"\b(for|while)\s*\(", clean_no_strings) or re.search(r"\bdo\s*[\(\{]", clean_no_strings):
        return False, "Starter code contains a loop (for/while/do)"

    # 2. Check for if, switch, ternary
    if re.search(r"\b(if|switch)\s*\(", clean_no_strings):
        return False, "Starter code contains conditional logic (if/switch)"
    if re.search(r"\?[^:;\n]+:", clean_no_strings):
        return False, "Starter code contains ternary operator"

    # 3. Check number of statements inside method body
    body_m = re.search(r"\b[A-Za-z0-9_]+\s*\([^)]*\)\s*\{([\s\S]*)\}\s*\}", clean_no_strings)
    if body_m:
        body = body_m.group(1).strip()
        stmts = [s.strip() for s in body.split(";") if s.strip()]
        non_return_stmts = [s for s in stmts if not re.match(r"^return\b", s)]
        if len(stmts) > 1 or len(non_return_stmts) > 0:
            return False, f"Starter code contains extra statements in method body: {stmts}"

    # 4. Token similarity to referenceSolution
    if reference_solution and reference_solution.strip():
        ref_clean = re.sub(r"//[^\n]*", "", reference_solution)
        ref_clean = re.sub(r"/\*[\s\S]*?\*/", "", ref_clean)
        ref_no_strings = re.sub(r'"(?:\\.|[^"\\])*"', '""', ref_clean)

        starter_tokens = set(re.findall(r"\b[A-Za-z0-9_]+\b", clean_no_strings))
        ref_tokens = set(re.findall(r"\b[A-Za-z0-9_]+\b", ref_no_strings))

        common_boilerplate = {"public", "class", "static", "void", "Solution", "solve", "return", "new"}
        s_meaningful = starter_tokens - common_boilerplate
        r_meaningful = ref_tokens - common_boilerplate

        if s_meaningful and r_meaningful:
            jaccard = len(s_meaningful & r_meaningful) / len(s_meaningful | r_meaningful)
            if jaccard > 0.6:
                return False, f"Starter code has high token similarity ({jaccard:.2f} > 0.6) to reference solution"

    return True, ""


def check_question_text_leak(question_text: str, reference_solution: str) -> Tuple[bool, str]:
    """
    Checks that questionText does not leak substantive code lines from referenceSolution.
    """
    if not question_text or not reference_solution:
        return True, ""

    q_lower = question_text.lower()
    ref_lines = [l.strip() for l in reference_solution.splitlines() if l.strip()]
    for line in ref_lines:
        if len(line) < 15:
            continue
        if re.match(r"^(public|private|protected|class|\{|\}|\/\/|\/\*|\*|\bimport\b)", line):
            continue
        line_clean = re.sub(r"\s+", " ", line).strip()
        if line_clean.lower() in q_lower:
            return False, f"Question text contains substantive reference solution line: '{line}'"

    return True, ""


def verify_dual_coding_solutions(
    ref_solution: str,
    alt_solution: str,
    test_inputs: List[str],
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """
    Runs referenceSolution on all test_inputs in the Java sandbox twice to verify compilation,
    timeout, and determinism.
    Computes expected outputs from the reference solution.
    Runs alternativeSolution (brute-force or alternative approach) on the same test_inputs.
    Requires alternativeSolution to produce identical outputs for all test_inputs.
    Returns (True, verified_test_cases, None) or (False, [], error_reason).
    """
    if not is_java_available():
        return False, [], "Java runtime (JDK) not available"

    if not test_inputs or len(test_inputs) < 2:
        return False, [], f"Insufficient test inputs: {len(test_inputs)} (need at least 2, ideally 3-5)"

    # 0. Static determinism checks on both solutions
    ok_det_ref, det_ref_err = is_snippet_deterministic(ref_solution)
    if not ok_det_ref:
        return False, [], f"Reference solution contains non-deterministic construct: {det_ref_err}"

    if not alt_solution or not alt_solution.strip():
        return False, [], "Missing alternative solution for independent dual-solution verification"

    ok_det_alt, det_alt_err = is_snippet_deterministic(alt_solution)
    if not ok_det_alt:
        return False, [], f"Alternative solution contains non-deterministic construct: {det_alt_err}"

    mock_cases = [
        {"id": i + 1, "input": str(inp).strip(), "expectedOutput": "__COMPUTE__", "label": f"Test {i + 1}"}
        for i, inp in enumerate(test_inputs)
    ]

    # 1. Run reference solution (Run 1)
    res_ref_1 = execute_coding_submission("java", ref_solution, mock_cases, timeout_sec=timeout_sec)
    if res_ref_1.get("compileError"):
        return False, [], f"Reference solution compilation error: {res_ref_1['compileError']}"

    computed_outputs_1 = []
    for tc_res in res_ref_1["results"]:
        if tc_res["status"] in ("TIMEOUT", "RUNTIME_ERROR", "COMPILE_ERROR"):
            return False, [], f"Reference solution run 1 failed on input '{tc_res['input']}': {tc_res['error']}"
        computed_outputs_1.append(tc_res["actual"])

    # 2. Run reference solution (Run 2) for determinism
    res_ref_2 = execute_coding_submission("java", ref_solution, mock_cases, timeout_sec=timeout_sec)
    if res_ref_2.get("compileError"):
        return False, [], f"Reference solution compilation error on run 2: {res_ref_2['compileError']}"

    for i, tc_res in enumerate(res_ref_2["results"]):
        if tc_res["actual"] != computed_outputs_1[i]:
            return False, [], f"Reference solution is non-deterministic on input '{tc_res['input']}'"

    # 3. Independent verification with alternative solution (brute-force or alternative approach)
    res_alt = execute_coding_submission("java", alt_solution, mock_cases, timeout_sec=timeout_sec)
    if res_alt.get("compileError"):
        return False, [], f"Alternative solution compilation error: {res_alt['compileError']}"

    for i, tc_res in enumerate(res_alt["results"]):
        if tc_res["status"] in ("TIMEOUT", "RUNTIME_ERROR", "COMPILE_ERROR"):
            return False, [], f"Alternative solution failed on input '{tc_res['input']}': {tc_res['error']}"
        if not values_match(tc_res["actual"], computed_outputs_1[i]):
            return False, [], (
                f"Disagreement on input '{tc_res['input']}': "
                f"reference solution gave '{computed_outputs_1[i]}', "
                f"alternative solution gave '{tc_res['actual']}'"
            )

    # Build verified test cases with true executed outputs
    verified_test_cases = [
        {
            "id": i + 1,
            "input": str(inp).strip(),
            "expectedOutput": computed_outputs_1[i],
            "label": f"Test {i + 1}",
        }
        for i, inp in enumerate(test_inputs)
    ]
    return True, verified_test_cases, None


def clean_sqlite_schema(ddl: str) -> str:
    """Transform common MySQL/PostgreSQL schema quirks into SQLite-compatible DDL."""
    if not ddl:
        return ""
    cleaned = ddl
    cleaned = re.sub(r"\bAUTO_INCREMENT\b", "AUTOINCREMENT", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bSERIAL\b", "INTEGER PRIMARY KEY AUTOINCREMENT", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bENGINE\s*=\s*\w+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bDEFAULT\s+CHARSET\s*=\s*\w+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bON\s+UPDATE\s+CURRENT_TIMESTAMP\b", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def normalize_sql_rows(rows: List[Tuple]) -> List[Tuple]:
    """Normalize row values for order-independent or ordered comparison."""
    norm_rows = []
    for r in rows:
        norm_row = tuple(normalize_value_str(v) for v in r)
        norm_rows.append(norm_row)
    return norm_rows


def execute_sql(candidate_query: str, schema: str, test_cases: List[Dict[str, Any]],
                reference_query: str = None, sample_data: str = None) -> Dict[str, Any]:
    """
    Deterministically execute candidate SQL queries against an in-memory SQLite database.
    Builds the database from schema and sample data, comparing candidate query rows against
    the reference query rows.
    """
    test_cases = test_cases or []
    cleaned_cand_query = (candidate_query or "").strip().rstrip(";") + ";"
    cleaned_ref_query = (reference_query or "").strip().rstrip(";") + ";" if reference_query else ""
    cleaned_schema = clean_sqlite_schema(schema or "")
    has_order_by = bool(re.search(r"\border\s+by\b", cleaned_ref_query or cleaned_cand_query, re.IGNORECASE))

    # Detect obvious non-SQLite dialect features for feedback notes
    dialect_notes = []
    if re.search(r"\bTOP\s+\d+\b", candidate_query or "", re.IGNORECASE):
        dialect_notes.append("The query uses T-SQL 'TOP' syntax instead of standard SQL 'LIMIT'.")
    if re.search(r"\bNVL\b", candidate_query or "", re.IGNORECASE):
        dialect_notes.append("The query uses Oracle 'NVL' instead of standard 'COALESCE' or 'IFNULL'.")
    if re.search(r"\bCONCAT_WS\b", candidate_query or "", re.IGNORECASE):
        dialect_notes.append("The query uses MySQL 'CONCAT_WS' function.")

    results = []
    passed_count = 0

    for i, tc in enumerate(test_cases):
        tc_input = str(tc.get("input", "")).strip()
        tc_expected = str(tc.get("expectedOutput", tc.get("expected", ""))).strip()

        # Build fresh in-memory SQLite database for this test case
        conn_cand = sqlite3.connect(":memory:")
        conn_ref = sqlite3.connect(":memory:") if cleaned_ref_query else None

        cand_error = None
        cand_rows = []
        expected_rows = []

        try:
            # 1. Execute schema DDL
            for stmt in cleaned_schema.split(";"):
                stmt = stmt.strip()
                if stmt:
                    conn_cand.execute(stmt)
                    if conn_ref:
                        conn_ref.execute(stmt)

            # 2. Execute sampleData DML if present
            if sample_data:
                for stmt in sample_data.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        conn_cand.execute(stmt)
                        if conn_ref:
                            conn_ref.execute(stmt)

            # 3. Execute test case input if it contains SQL insert statements
            if tc_input and ("insert into" in tc_input.lower() or "create table" in tc_input.lower()):
                for stmt in tc_input.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        conn_cand.execute(stmt)
                        if conn_ref:
                            conn_ref.execute(stmt)

            # 4. Run candidate query
            cur_cand = conn_cand.cursor()
            cur_cand.execute(cleaned_cand_query)
            cand_rows = cur_cand.fetchall()

            # 5. Determine expected rows
            if conn_ref:
                cur_ref = conn_ref.cursor()
                cur_ref.execute(cleaned_ref_query)
                expected_rows = cur_ref.fetchall()
        except sqlite3.Error as e:
            cand_error = str(e)
        except Exception as e:
            cand_error = str(e)
        finally:
            conn_cand.close()
            if conn_ref:
                conn_ref.close()

        # Format rows for display
        actual_str = "\n".join(" | ".join(str(v) for v in r) for r in cand_rows) if cand_rows else ""
        if not actual_str and not cand_error:
            actual_str = "(0 rows returned)"

        if expected_rows:
            expected_str = "\n".join(" | ".join(str(v) for v in r) for r in expected_rows)
        else:
            expected_str = tc_expected

        if cand_error:
            passed = False
            status = "RUNTIME_ERROR"
            err_msg = f"SQL error: {cand_error}"
        else:
            if expected_rows:
                norm_cand = normalize_sql_rows(cand_rows)
                norm_exp = normalize_sql_rows(expected_rows)
                if has_order_by:
                    passed = (norm_cand == norm_exp)
                else:
                    passed = (sorted(norm_cand) == sorted(norm_exp))
            else:
                passed = values_match(actual_str, expected_str)

            status = "PASSED" if passed else "FAILED"
            err_msg = None if passed else f"Expected: {expected_str}, Got: {actual_str}"

        if passed:
            passed_count += 1

        results.append({
            "id": i + 1,
            "input": tc_input or "Standard database state",
            "expected": expected_str,
            "actual": actual_str,
            "status": status,
            "error": err_msg,
            "passed": passed,
            "expectedOutput": expected_str,
            "actualOutput": actual_str,
            "failureReason": err_msg if not passed else "",
            "label": tc.get("label"),
        })

    return {
        "judgeMode": "deterministic",
        "compileError": None,
        "dialectNotes": " ".join(dialect_notes) if dialect_notes else None,
        "passedCount": passed_count,
        "totalCount": len(test_cases),
        "results": results,
    }


def execute_coding_submission(language: str, code: str, test_cases: List[Dict[str, Any]],
                              schema: str = None, reference_solution: str = None,
                              sample_data: str = None, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> Dict[str, Any]:
    """Top-level dispatcher for deterministic code grading."""
    lang = (language or "java").lower().strip()
    if lang == "sql":
        return execute_sql(
            candidate_query=code,
            schema=schema,
            test_cases=test_cases,
            reference_query=reference_solution,
            sample_data=sample_data,
        )
    return execute_java(candidate_code=code, test_cases=test_cases, timeout_sec=timeout_sec)
