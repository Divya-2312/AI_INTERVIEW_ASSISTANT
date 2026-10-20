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
                              sample_data: str = None) -> Dict[str, Any]:
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
    return execute_java(candidate_code=code, test_cases=test_cases)
