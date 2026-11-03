"""
Intelligent Time and Space Complexity Analyzer for Java Submissions.
Performs deterministic static code analysis, loop/recursion structure parsing,
data structure space auditing, and problem catalogue matching.
"""

import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple

_CATALOGUE_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_approaches_catalogue() -> List[Dict[str, Any]]:
    global _CATALOGUE_CACHE
    if _CATALOGUE_CACHE is not None:
        return _CATALOGUE_CACHE
    cat_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "question_bank",
        "coding_approaches_catalogue.json",
    )
    try:
        if os.path.exists(cat_path):
            with open(cat_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _CATALOGUE_CACHE = data.get("problems", [])
        else:
            _CATALOGUE_CACHE = []
    except Exception:
        _CATALOGUE_CACHE = []
    return _CATALOGUE_CACHE


def strip_java_comments_and_strings(code: str) -> str:
    """Removes single-line, multi-line comments and string/char literals from Java code."""
    if not code:
        return ""
    # Remove block comments
    no_block = re.sub(r"/\*[\s\S]*?\*/", " ", code)
    # Remove line comments
    no_line = re.sub(r"//[^\n]*", " ", no_block)
    # Replace string literals with empty string literal to prevent keyword confusion
    no_strings = re.sub(r'"(\\.|[^"\\])*"', '""', no_line)
    # Replace character literals
    no_chars = re.sub(r"'(\\.|[^'\\])*'", "''", no_strings)
    return no_chars


def extract_loop_header(code: str, start_idx: int) -> Tuple[str, int]:
    """Extracts balanced parenthesis content for for(...) or while(...) headers."""
    paren_start = code.find("(", start_idx)
    if paren_start == -1:
        return "", start_idx
    depth = 1
    idx = paren_start + 1
    while idx < len(code) and depth > 0:
        if code[idx] == "(":
            depth += 1
        elif code[idx] == ")":
            depth -= 1
        idx += 1
    return code[paren_start + 1 : idx - 1], idx


def _extract_constant_collections(code: str) -> set:
    """Detects local arrays/collections with constant/literal bounds in Java code."""
    const_vars = set()
    # 1. Array initialized with literal elements: e.g. char[] vowels = {'a', 'e', 'i', 'o', 'u'};
    for m in re.finditer(r"(?:[a-zA-Z_]\w*\s*\[\s*\]\s*([a-zA-Z_]\w*)|[a-zA-Z_]\w*\s+([a-zA-Z_]\w*)\s*\[\s*\])\s*=\s*(?:\{[^}]*\}|new\s+[a-zA-Z_]\w*\s*\[\s*\]\s*\{[^}]*\})", code):
        const_vars.add(m.group(1) or m.group(2))
    # 2. Fixed-size arrays: e.g. new int[26], new char[256]
    for m in re.finditer(r"(?:[a-zA-Z_]\w*\s*\[\s*\]\s*([a-zA-Z_]\w*)|[a-zA-Z_]\w*\s+([a-zA-Z_]\w*)\s*\[\s*\])\s*=\s*new\s+[a-zA-Z_]\w*\s*\[\s*(\d+)\s*\]", code):
        const_vars.add(m.group(1) or m.group(2))
    # 3. String literals: e.g. String vowels = "aeiou";
    for m in re.finditer(r"\bString\s+([a-zA-Z_]\w*)\s*=\s*\"[^\"]*\"", code):
        const_vars.add(m.group(1))
    # 4. Fixed collections: e.g. Arrays.asList('a', 'e', ...), Set.of(...), List.of(...)
    for m in re.finditer(r"\b(?:List|Set|Collection)(?:<[^>]+>)?\s+([a-zA-Z_]\w*)\s*=\s*(?:Arrays\.asList|Set\.of|List\.of)\s*\([^)]*\)", code):
        const_vars.add(m.group(1))
    return const_vars


def _is_constant_bound_loop(header: str, const_vars: set) -> bool:
    """Checks whether a loop iterates over a constant bound (O(1)) rather than input size."""
    if not header:
        return False
    h = header.strip()
    # Enhanced for loop: for (char v : vowels)
    if ":" in h:
        iterable = h.split(":", 1)[1].strip()
        if iterable in const_vars:
            return True
        for cv in const_vars:
            if re.search(rf"\b{re.escape(cv)}\b", iterable):
                return True
        if re.search(r'^\s*""', iterable) or "toCharArray()" in iterable:
            return True
        if "new " in iterable and ("{" in iterable or re.search(r"\[\s*\d+\s*\]", iterable)):
            return True
        return False
    # 3-part for loop: for (init; cond; step)
    parts = h.split(";")
    if len(parts) >= 2:
        cond = parts[1].strip()
        # Comparison with numeric integer constant (e.g. j < 5, j < 26)
        if re.search(r"(?:<|<=|>|>=|==|!=)\s*\d+\b", cond) or re.search(r"\b\d+\s*(?:<|<=|>|>=|==|!=)", cond):
            return True
        # Comparison with char literal (e.g. c <= 'z')
        if re.search(r"(?:<|<=|>|>=|==|!=)\s*''", cond) or re.search(r"''\s*(?:<|<=|>|>=|==|!=)", cond):
            return True
        # Comparison with constant collection length or size
        for cv in const_vars:
            if re.search(rf"\b{re.escape(cv)}\s*\.\s*(?:length|length\(\)|size\(\))", cond):
                return True
            if re.search(rf"\b{re.escape(cv)}\b", cond):
                return True
        if '""' in cond and "length()" in cond:
            return True
    return False


def count_loop_nesting_depth(code: str) -> Tuple[int, List[str]]:
    """
    Parses bracket nesting to measure max loop nesting depth
    and distinguish consecutive loops (O(N) + O(N)) from nested loops (O(N^2)).
    Inner loops bounded by constant collections or literal limits are O(1) and
    do not add factors of N to the nesting depth.
    """
    clean = strip_java_comments_and_strings(code)
    const_vars = _extract_constant_collections(code)

    max_depth = 0
    current_loop_depth = 0
    brace_stack = []  # tracks loop type of opening brace: 'input', 'constant', or 'other'
    loop_details = []
    
    pending_loop = None
    next_valid_pos = 0

    for m in re.finditer(r"(\bfor\b|\bwhile\b|\bdo\b|\{|\})", clean):
        if m.start() < next_valid_pos:
            continue
        tok = m.group(1)
        if tok in ("for", "while"):
            header, end_pos = extract_loop_header(clean, m.start())
            next_valid_pos = end_pos
            is_const = _is_constant_bound_loop(header, const_vars)
            pending_loop = "constant" if is_const else "input"
        elif tok == "do":
            pending_loop = "input"
        elif tok == "{":
            if pending_loop == "input":
                current_loop_depth += 1
                brace_stack.append("input")
                pending_loop = None
                if current_loop_depth > max_depth:
                    max_depth = current_loop_depth
            elif pending_loop == "constant":
                brace_stack.append("constant")
                pending_loop = None
            else:
                brace_stack.append("other")
        elif tok == "}":
            if brace_stack:
                kind = brace_stack.pop()
                if kind == "input":
                    current_loop_depth = max(0, current_loop_depth - 1)

    if max_depth >= 3:
        loop_details.append(f"Triple-nested loops detected (max loop depth: {max_depth}).")
    elif max_depth == 2:
        loop_details.append("Nested loop structure detected (outer and inner iteration).")
    elif max_depth == 1:
        # Check if there are multiple consecutive loops
        loop_count = len(re.findall(r"\b(for|while)\b", clean))
        if loop_count > 1:
            loop_details.append(f"{loop_count} consecutive sequential loops detected (O(N) + O(N) = O(N)).")
        else:
            loop_details.append("Single loop iteration detected.")
    else:
        loop_details.append("No loop structures detected.")

    return max_depth, loop_details


def analyze_recursion_patterns(code: str) -> Dict[str, Any]:
    """
    Analyzes whether code contains recursion, call-branching factor,
    and parameter progression (linear decrement vs halving).
    """
    clean = strip_java_comments_and_strings(code)
    
    # Extract method signatures: e.g., public static int fib(int n) {
    method_pattern = r"(?:public|private|protected|static|\s)+\s+[\w<>\[\]]+\s+(\w+)\s*\(([^)]*)\)\s*\{"
    methods = re.findall(method_pattern, clean)
    
    found_recursion = False
    branching_factor = 0
    is_divide_and_conquer = False
    recursive_method_name = None

    for m_name, params in methods:
        if m_name in ("main", "equals", "hashCode", "toString"):
            continue
        # Find where the method starts and slice its body
        m_match = re.search(rf"\b{re.escape(m_name)}\s*\([^)]*\)\s*\{{", clean)
        if not m_match:
            continue
        body_start = m_match.end()
        method_body = clean[body_start:]
        
        # Count actual recursive calls inside the method body
        internal_calls = len(re.findall(rf"\b{re.escape(m_name)}\s*\(", method_body))
        if internal_calls >= 1:
            found_recursion = True
            recursive_method_name = m_name
            branching_factor = 2 if internal_calls >= 2 else 1

            # Check if arguments divide: e.g., / 2, >> 1, mid - 1
            if re.search(rf"\b{re.escape(m_name)}\s*\([^)]*(?:/\s*2|>>\s*1|\bmid\b)", method_body):
                is_divide_and_conquer = True

    return {
        "hasRecursion": found_recursion,
        "methodName": recursive_method_name,
        "branchingFactor": branching_factor,
        "isDivideAndConquer": is_divide_and_conquer,
    }


def analyze_auxiliary_space(code: str, has_recursion: bool, branching: int, max_loop_depth: int) -> Tuple[str, List[str]]:
    """
    Inspects auxiliary heap and stack memory usage:
    - Distinguishes fixed constant-size arrays (int[26] -> O(1)) from dynamic arrays (int[n] -> O(N)).
    - Detects HashMaps, HashSets, Stacks, Lists.
    - Measures recursive call stack depth.
    """
    clean = strip_java_comments_and_strings(code)
    space_explanations = []
    estimated_space = "O(1)"
    
    # 1. Check fixed constant arrays: e.g. new int[26], new int[256], new int[128], new boolean[2]
    fixed_array_match = re.search(r"new\s+\w+\[\s*(\d+)\s*\]", clean)
    # Check variable arrays: e.g. new int[n], new int[nums.length], new char[s.length()]
    dynamic_array_match = re.search(r"new\s+\w+\[\s*([a-zA-Z_]\w*(?:\.\w+)?(?:\(\))?)\s*\]", clean)
    
    # 2. Check dynamic collections
    collection_matches = re.findall(
        r"new\s+(HashMap|HashSet|ArrayList|LinkedList|ArrayDeque|Stack|PriorityQueue|TreeMap|TreeSet)\b",
        clean,
    )
    
    # 3. Check string builder usage inside loops
    string_builder_in_loop = bool(re.search(r"new\s+StringBuilder\b", clean) and max_loop_depth > 0)
    
    uses_heap_memory = False
    
    if collection_matches:
        collections_used = ", ".join(sorted(set(collection_matches)))
        space_explanations.append(f"Dynamically allocates collections: {collections_used} (O(N) auxiliary space).")
        estimated_space = "O(N)"
        uses_heap_memory = True
    elif dynamic_array_match:
        dim = dynamic_array_match.group(1)
        space_explanations.append(f"Allocates dynamically-sized array based on input size '{dim}' (O(N) auxiliary space).")
        estimated_space = "O(N)"
        uses_heap_memory = True
    elif fixed_array_match:
        size = fixed_array_match.group(1)
        space_explanations.append(f"Uses fixed-size frequency array of length {size} (O(1) constant auxiliary space).")
        estimated_space = "O(1)"
    elif string_builder_in_loop:
        space_explanations.append("Repeatedly allocates StringBuilder buffers inside iterations (O(N) auxiliary space).")
        estimated_space = "O(N)"
        uses_heap_memory = True

    # 4. Recursive stack frames
    if has_recursion:
        if branching >= 2:
            space_explanations.append("Recursive call stack reaches depth of O(N) frames along the deepest recursion branch.")
            estimated_space = "O(N)"
        else:
            space_explanations.append("Recursive call stack requires O(N) stack frames for linear recursion depth.")
            estimated_space = "O(N)"
    
    if not uses_heap_memory and not has_recursion and not fixed_array_match:
        space_explanations.append("Operates in-place using only O(1) primitive local variables without heap structures or recursion.")
        estimated_space = "O(1)"

    return estimated_space, space_explanations


def estimate_time_complexity(code: str, max_loop_depth: int, recursion_info: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Calculates Time Complexity (Big-O) based on loop nesting, loop steps, sorting, and recursion.
    """
    clean = strip_java_comments_and_strings(code)
    reasons = []
    
    has_sort = bool(re.search(r"\b(Arrays\.sort|Collections\.sort|\.sort\()\b", clean))
    has_log_step = bool(re.search(r"(>>\s*1|/\s*2|\bmid\b|\bbinarySearch\b)", clean))
    
    has_recursion = recursion_info["hasRecursion"]
    branching = recursion_info["branchingFactor"]
    is_dnc = recursion_info["isDivideAndConquer"]

    # Recursion takes precedence if present
    if has_recursion:
        if branching >= 2 and not is_dnc:
            # e.g., Fibonacci fib(n-1) + fib(n-2)
            time_c = "O(2^N)"
            reasons.append("Binary tree recursion: Each recursive call branches into 2 additional calls, generating 2^N total operations.")
            return time_c, reasons
        elif branching >= 2 and is_dnc:
            # e.g., Merge sort or divide-and-conquer
            time_c = "O(N log N)"
            reasons.append("Divide-and-conquer recursion with linear combination step yielding O(N log N) by the Master Theorem.")
            return time_c, reasons
        elif is_dnc:
            # e.g., Binary search recursive
            time_c = "O(log N)"
            reasons.append("Recursive binary halving: The problem size is divided by 2 at each recursive step, resulting in O(log N) depth.")
            return time_c, reasons
        else:
            # Linear recursion e.g., factorial
            time_c = "O(N)"
            reasons.append("Linear recursion with N sequential calls down to base case.")
            return time_c, reasons

    # Sorting
    if has_sort:
        if max_loop_depth >= 1:
            time_c = "O(N log N)"
            reasons.append("Includes O(N log N) sorting step combined with linear passes; dominated by O(N log N).")
        else:
            time_c = "O(N log N)"
            reasons.append("Dominated by standard Dual-Pivot Quicksort / TimSort operation with O(N log N) time complexity.")
        return time_c, reasons

    # Nested loops
    if max_loop_depth >= 3:
        time_c = "O(N^3)"
        reasons.append("Three nested loops each iterating proportionally to input size N, producing N^3 operations.")
        return time_c, reasons
    elif max_loop_depth == 2:
        if has_log_step:
            time_c = "O(N log N)"
            reasons.append("Outer loop iterates N times while inner loop halves the search space logarithmically O(log N), yielding O(N log N).")
        else:
            time_c = "O(N^2)"
            reasons.append("Quadratic time complexity: Nested loops where inner loop runs for each iteration of the outer loop.")
        return time_c, reasons
    elif max_loop_depth == 1:
        if has_log_step:
            time_c = "O(log N)"
            reasons.append("Iterative binary search or logarithmic reduction: Loop step divides range by 2 at each iteration.")
        else:
            time_c = "O(N)"
            reasons.append("Linear iteration: Code traverses input elements via a single sequential loop.")
        return time_c, reasons
    else:
        time_c = "O(1)"
        reasons.append("Constant time: No loops, recursive calls, or unbounded operations detected.")
        return time_c, reasons


def _is_single_scalar_input(code: str) -> bool:
    """Checks whether the primary Java method accepts only a single scalar parameter (e.g. int year)."""
    clean = strip_java_comments_and_strings(code)
    method_match = re.search(
        r"(?:public|private|protected|static|\s)+\s+[\w<>\[\]]+\s+(\w+)\s*\(([^)]*)\)\s*\{",
        clean,
    )
    if not method_match:
        return False
    params_str = method_match.group(2).strip()
    if not params_str:
        return False
    params = [p.strip() for p in params_str.split(",") if p.strip()]
    if len(params) != 1:
        return False
    param = params[0]
    if "[]" in param or "..." in param:
        return False
    if re.search(r"\b(String|CharSequence|List|Set|Map|Collection|Queue|Deque|Stack)\b", param):
        return False
    scalar_types = r"\b(int|long|short|byte|boolean|char|float|double|Integer|Long|Short|Byte|Boolean|Character|Float|Double)\b"
    return bool(re.search(scalar_types, param))


def match_problem_catalogue(question: str, code: str) -> Optional[Dict[str, Any]]:
    """
    Finds matching problem in the coding approaches catalogue by question keywords and code.
    """
    catalogue = _load_approaches_catalogue()
    if not catalogue:
        return None

    q_lower = (question or "").lower()
    c_lower = (strip_java_comments_and_strings(code) or "").lower()
    
    best_problem = None
    best_score = 0

    for prob in catalogue:
        score = 0
        for alias in prob.get("aliases", []):
            if alias.lower() in q_lower:
                score += 3
            elif alias.lower() in c_lower:
                score += 2
        if prob.get("id") in q_lower:
            score += 2
        elif prob.get("id") in c_lower:
            score += 1
        for word in prob.get("title", "").lower().split():
            if len(word) > 3 and word in q_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_problem = prob

    if best_score >= 2:
        return best_problem
    return None


def identify_student_approach(problem_data: Optional[Dict[str, Any]], code: str, time_c: str, space_c: str, recursion_info: Dict[str, Any], max_loop_depth: int) -> Dict[str, Any]:
    """
    Identifies which algorithmic approach the student used and matches it with optimal/alternative approaches.
    """
    clean = strip_java_comments_and_strings(code)
    has_hash = bool(re.search(r"\b(HashMap|HashSet)\b", clean))
    has_sort = bool(re.search(r"\b(Arrays\.sort|Collections\.sort|\.sort\()\b", clean))
    has_two_pointers = bool(re.search(r"\b(left|right|start|end|low|high|p1|p2)\b", clean) and max_loop_depth >= 1)
    
    # Baseline approach classification
    if recursion_info["hasRecursion"]:
        if recursion_info["branchingFactor"] >= 2:
            approach_name = "Tree Recursion"
            approach_type = "recursive"
        else:
            approach_name = "Linear Recursion"
            approach_type = "recursive"
    elif max_loop_depth >= 2:
        approach_name = "Nested Loops (Brute Force)"
        approach_type = "brute_force"
    elif has_hash:
        approach_name = "Hash Table Lookup"
        approach_type = "hash_table"
    elif has_sort:
        approach_name = "Sorting-Based Approach"
        approach_type = "sorting"
    elif has_two_pointers:
        approach_name = "Two Pointers Technique"
        approach_type = "two_pointers"
    elif max_loop_depth == 1:
        approach_name = "Linear Iteration"
        approach_type = "iterative"
    else:
        approach_name = "Constant Time Direct Computation"
        approach_type = "direct"

    comparison_approaches = []
    optimal_approach = None
    is_student_optimal = False
    tradeoff_advice = None

    if problem_data and "approaches" in problem_data:
        catalogue_approaches = problem_data["approaches"]
        tradeoff_advice = problem_data.get("bestTradeoff")

        # Find matching catalogue approach for the student
        matched_cat_approach = None
        # First prioritize matching exact approachType (e.g. iterative vs recursive)
        for cat_app in catalogue_approaches:
            if cat_app.get("approachType") == approach_type:
                matched_cat_approach = cat_app
                approach_name = cat_app.get("name", approach_name)
                break
        # Fall back to matching by time complexity if approachType differed
        if not matched_cat_approach:
            for cat_app in catalogue_approaches:
                if cat_app.get("timeComplexity") == time_c:
                    matched_cat_approach = cat_app
                    approach_name = cat_app.get("name", approach_name)
                    break

        if matched_cat_approach and matched_cat_approach.get("isOptimal"):
            is_student_optimal = True

        for cat_app in catalogue_approaches:
            if cat_app.get("isOptimal") and not optimal_approach:
                optimal_approach = cat_app
            comparison_approaches.append({
                "name": cat_app.get("name"),
                "timeComplexity": cat_app.get("timeComplexity"),
                "spaceComplexity": cat_app.get("spaceComplexity"),
                "isOptimal": cat_app.get("isOptimal", False),
                "summary": cat_app.get("summary", ""),
                "tradeOff": cat_app.get("tradeOff", ""),
            })

    # If no catalogue match, infer an optimal alternative if student is quadratic or exponential
    if not optimal_approach:
        if time_c in ("O(N^2)", "O(N^3)"):
            if _is_single_scalar_input(code):
                optimal_approach = {
                    "name": "Direct Arithmetic / Conditional Approach",
                    "timeComplexity": "O(1)",
                    "spaceComplexity": "O(1)",
                    "summary": "Direct arithmetic or condition-based computation without loops.",
                    "tradeOff": "A direct arithmetic or condition-based solution is possible; the loops can be removed to achieve O(1) time and O(1) auxiliary space.",
                }
            else:
                # Check if inner loop only selects the current element (e.g. guarded by i == j)
                has_index_guard = bool(re.search(r"\bif\s*\(\s*([a-zA-Z_]\w*)\s*==\s*([a-zA-Z_]\w*)\s*\)", clean))
                if has_index_guard:
                    tradeoff_msg = "The inner loop only selects the current element and can be removed; compute the result in a single pass with O(N) time and O(1) auxiliary space."
                else:
                    tradeoff_msg = "The inner loop repeats work for every element. Check whether it is really needed; many problems can be solved with a single pass over the input."

                optimal_approach = {
                    "name": "Single-Pass Linear Approach",
                    "timeComplexity": "O(N)",
                    "spaceComplexity": "O(1)",
                    "summary": "Process elements in a single sequential pass without redundant nested iterations.",
                    "tradeOff": tradeoff_msg,
                }
        elif time_c == "O(2^N)":
            optimal_approach = {
                "name": "Iterative / Dynamic Programming Approach",
                "timeComplexity": "O(N)",
                "spaceComplexity": "O(1)",
                "summary": "Compute values sequentially with rolling variables or memoization table.",
                "tradeOff": "Avoids exponential duplicate computations and eliminates recursion stack overhead.",
            }
        else:
            is_student_optimal = True

    return {
        "studentApproachName": approach_name,
        "studentApproachType": approach_type,
        "isOptimal": is_student_optimal,
        "optimalApproach": optimal_approach,
        "comparisonApproaches": comparison_approaches,
        "tradeoffAdvice": tradeoff_advice,
    }


def analyze_java_complexity(question: str, code: str) -> Dict[str, Any]:
    """
    Main entry point for intelligent complexity analysis.
    Combines static AST/loop/recursion inspection, auxiliary space accounting,
    and catalogue comparison.
    """
    if not code or not code.strip():
        return {
            "timeComplexity": "O(1)",
            "spaceComplexity": "O(1)",
            "approach": "Empty / No Code",
            "explanation": "No executable code provided.",
            "isEstimate": False,
            "structuralDetails": {},
            "comparison": {},
            "suggestions": [],
        }

    # 1. Structural Static Analysis
    max_loop_depth, loop_details = count_loop_nesting_depth(code)
    recursion_info = analyze_recursion_patterns(code)
    time_c, time_reasons = estimate_time_complexity(code, max_loop_depth, recursion_info)
    space_c, space_reasons = analyze_auxiliary_space(code, recursion_info["hasRecursion"], recursion_info["branchingFactor"], max_loop_depth)

    # 2. Problem Catalogue & Approach Matching
    problem_data = match_problem_catalogue(question, code)
    approach_data = identify_student_approach(problem_data, code, time_c, space_c, recursion_info, max_loop_depth)

    # 3. Formulate Actionable Suggestions
    suggestions = []
    if approach_data.get("optimalApproach") and not approach_data.get("isOptimal"):
        opt = approach_data["optimalApproach"]
        suggestions.append(
            f"Consider using the {opt.get('name')} to achieve {opt.get('timeComplexity')} time and {opt.get('spaceComplexity')} space."
        )
        if opt.get("tradeOff"):
            suggestions.append(opt.get("tradeOff"))
    elif approach_data.get("isOptimal"):
        suggestions.append("Your algorithmic approach achieves optimal time complexity for this problem.")
    
    if recursion_info["hasRecursion"] and time_c != "O(log N)":
        suggestions.append("Recursive calls consume call-stack frames. An iterative approach uses O(1) auxiliary stack space.")

    # 4. Construct Comprehensive Explanation
    all_reasons = time_reasons + space_reasons
    explanation = " ".join(all_reasons)

    return {
        "timeComplexity": time_c,
        "spaceComplexity": space_c,
        "approach": approach_data["studentApproachName"],
        "approachType": approach_data["studentApproachType"],
        "isOptimal": approach_data["isOptimal"],
        "explanation": explanation,
        "isEstimate": False,
        "structuralDetails": {
            "maxLoopNesting": max_loop_depth,
            "hasRecursion": recursion_info["hasRecursion"],
            "recursionMethod": recursion_info["methodName"],
            "branchingFactor": recursion_info["branchingFactor"],
            "loopSummary": loop_details,
            "spaceSummary": space_reasons,
        },
        "optimalApproach": approach_data["optimalApproach"],
        "comparisonApproaches": approach_data["comparisonApproaches"],
        "tradeoffAdvice": approach_data["tradeoffAdvice"],
        "suggestions": suggestions,
    }
