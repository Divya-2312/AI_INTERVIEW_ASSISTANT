#!/usr/bin/env python3
"""
Generates synthetic SFT training data for:
1. HR Question Evaluation (task: evaluate_answer, interviewType: hr)
2. Code Time & Space Complexity Finding (task: analyze_code_complexity)

Guarantees:
- Group-split integrity: All rows derived from the same source question or problem
  preserve the exact canonical `source_id` (zero leak between train/val/test splits).
- Broad complexity coverage: O(1), O(log N), O(N), O(N log N), O(N^2), O(N^3), and O(2^N),
  with >= 30 examples for both O(N^3) and O(2^N).
- Diverse coding patterns: for-loops, while-loops, recursion, helper methods, and Java Streams.
- Verifiable reasons stored in every complexity record's explanation.
"""

import json
import re
from pathlib import Path


def generate_hr_evaluations(hr_records):
    eval_rows = []

    for i, r in enumerate(hr_records):
        qid = r.get("id", f"hr-{i+1:03d}")
        q_text = r.get("questionText", "")
        guidance = r.get("answerGuidance", "")
        category = r.get("category", "General")

        concepts = [
            f"Context and situation for {category.lower()}",
            "Concrete personal actions taken",
            "Quantifiable or tangible outcome",
            "Professional self-reflection and ownership"
        ]

        ref_ans = guidance if guidance else f"Structured STAR answer addressing {q_text} with measurable outcome."

        # Case 1: Strong STAR Response (High Score 90-96)
        strong_answer = (
            f"In my previous project, we faced a situation related to {q_text.lower().rstrip('?')}. "
            f"My specific task was to address this by focusing on {guidance.split(';')[0].lower() if ';' in guidance else guidance[:60].lower()}. "
            f"I initiated a structured plan: I coordinated with our team lead, broke down the problem into distinct milestones, "
            f"and communicated transparently across all stakeholders. As a result, we delivered the solution two days ahead of schedule, "
            f"improved our pipeline reliability by 30%, and received commendation from our project director."
        )

        inp_strong = {
            "interviewType": "hr",
            "subject": "hr",
            "question": q_text,
            "answer": strong_answer,
            "expectedConcepts": concepts,
            "questionFormat": "theory",
            "reference_answer": ref_ans
        }
        out_strong = {
            "score": 94,
            "relevance": 1.0,
            "correctness": 0.95,
            "accuracy": 0.95,
            "communication": 0.95,
            "isIrrelevant": False,
            "feedback": "Outstanding answer utilizing the STAR methodology with a specific scenario, clear personal actions, and measurable business impact.",
            "strengths": [
                "Structured STAR framework narrative",
                "Specific quantifiable metric (30% improvement)",
                "Clear personal ownership and stakeholder communication"
            ],
            "weaknesses": [],
            "coveredConcepts": concepts,
            "missingConcepts": [],
            "improvementSuggestion": "Keep this strong structure; maintain this level of clarity in interview discussions.",
            "scoreReason": "High score for providing a genuine, well-structured example that directly demonstrates targeted behavioral competencies."
        }
        eval_rows.append({
            "task": "evaluate_answer",
            "input": inp_strong,
            "output": out_strong,
            "source_id": qid,
            "case_type": "hr_star_strong",
            "source": "synthetic_rubric"
        })

        # Case 2: Partial / Generic Response (Score 55-65)
        generic_answer = (
            f"Whenever I face situations involving {q_text.lower().rstrip('?')}, I always try my best to stay calm and work hard. "
            f"I believe teamwork and dedication are the most important things in any job. I listen to feedback and do whatever is needed "
            f"to help the company succeed and learn new things along the way."
        )

        inp_generic = {
            "interviewType": "hr",
            "subject": "hr",
            "question": q_text,
            "answer": generic_answer,
            "expectedConcepts": concepts,
            "questionFormat": "theory",
            "reference_answer": ref_ans
        }
        out_generic = {
            "score": 60,
            "relevance": 0.80,
            "correctness": 0.65,
            "accuracy": 0.50,
            "communication": 0.70,
            "isIrrelevant": False,
            "feedback": "Good professional tone and positive attitude, but speaks in broad generalities without citing a specific past project or measurable outcome.",
            "strengths": [
                "Professional tone and positive mindset",
                "Understands core values of teamwork and learning"
            ],
            "weaknesses": [
                "Lacks a specific concrete project or scenario",
                "No quantifiable results or business impact described"
            ],
            "coveredConcepts": concepts[:2],
            "missingConcepts": concepts[2:],
            "improvementSuggestion": "Ground your answer in a specific situation: use the STAR method to describe an exact challenge, your actions, and the measurable outcome.",
            "scoreReason": "Partial credit awarded. The response demonstrates good interpersonal intent but lacks experiential evidence."
        }
        eval_rows.append({
            "task": "evaluate_answer",
            "input": inp_generic,
            "output": out_generic,
            "source_id": qid,
            "case_type": "hr_generic_partial",
            "source": "synthetic_rubric"
        })

        # Case 3: Cliché / Buzzword Dump (Score 25-35)
        buzzword_answer = (
            "I am a highly synergistic, results-oriented paradigm shifter who always leverages core competencies "
            "to maximize ROI and optimize high-velocity deliverables in dynamic agile environments."
        )
        inp_buzzword = {
            "interviewType": "hr",
            "subject": "hr",
            "question": q_text,
            "answer": buzzword_answer,
            "expectedConcepts": concepts,
            "questionFormat": "theory",
            "reference_answer": ref_ans
        }
        out_buzzword = {
            "score": 30,
            "relevance": 0.35,
            "correctness": 0.30,
            "accuracy": 0.20,
            "communication": 0.45,
            "isIrrelevant": False,
            "feedback": "The response relies heavily on corporate buzzwords and clichés without providing any tangible story, personal action, or evidence.",
            "strengths": ["Enthusiastic vocabulary"],
            "weaknesses": [
                "Relies on buzzwords and clichés without substance",
                "Provides zero evidence or past experience to support claims"
            ],
            "coveredConcepts": [],
            "missingConcepts": concepts,
            "improvementSuggestion": "Avoid corporate buzzwords. Tell an authentic story from your university or internship experience that proves these skills in action.",
            "scoreReason": "Low score because buzzwords without verifiable evidence do not demonstrate behavioral competence."
        }
        eval_rows.append({
            "task": "evaluate_answer",
            "input": inp_buzzword,
            "output": out_buzzword,
            "source_id": qid,
            "case_type": "hr_buzzword_dump",
            "source": "synthetic_rubric"
        })

        # Case 4: Irrelevant Answer (Score 0)
        wrong_answer = (
            "In relational database management systems, normalization is the process of organizing data to reduce redundancy "
            "and improve data integrity using first, second, and third normal forms."
            if i % 2 == 0 else
            "My favorite food is Italian pasta and in my free time I enjoy playing football and playing video games on weekends."
        )
        inp_wrong = {
            "interviewType": "hr",
            "subject": "hr",
            "question": q_text,
            "answer": wrong_answer,
            "expectedConcepts": concepts,
            "questionFormat": "theory",
            "reference_answer": ref_ans
        }
        out_wrong = {
            "score": 0,
            "relevance": 0.0,
            "correctness": 0.0,
            "accuracy": 0.0,
            "communication": 0.20,
            "isIrrelevant": True,
            "feedback": "The response does not address the behavioral interview question asked.",
            "strengths": [],
            "weaknesses": ["Response is completely unrelated to the interview question."],
            "coveredConcepts": [],
            "missingConcepts": concepts,
            "improvementSuggestion": "Directly answer the question asked with a relevant professional or academic experience.",
            "scoreReason": "Zero score awarded because the answer is completely off-topic and fails to address the question."
        }
        eval_rows.append({
            "task": "evaluate_answer",
            "input": inp_wrong,
            "output": out_wrong,
            "source_id": qid,
            "case_type": "hr_irrelevant",
            "source": "synthetic_rubric"
        })

    return eval_rows


def generate_complexity_analysis_records(coding_records):
    complexity_rows = []

    for i, r in enumerate(coding_records):
        qid = r.get("id", f"code-{i+1:03d}")
        title = r.get("title", "Algorithm Problem")
        desc = r.get("description", "")
        starter = r.get("starterCode", "")
        method_match = re.search(r"public\s+static\s+(\w+)\s+(\w+)\s*\(([^)]*)\)", starter)
        ret_type = method_match.group(1) if method_match else "int"
        method_name = method_match.group(2) if method_match else "solve"
        params = method_match.group(3) if method_match else "int[] nums"

        # -------------------------------------------------------------
        # Pattern 1: Linear Scan O(N) time, O(1) space
        # Variety: standard for-loop, while-loop, and Stream API
        # -------------------------------------------------------------
        if i % 3 == 0:
            # Stream API style
            code_linear = (
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    if (nums == null || nums.length == 0) return 0;\n"
                f"    return (int) java.util.Arrays.stream(nums)\n"
                f"        .filter(x -> x > 0)\n"
                f"        .count();\n"
                f"}}"
                if "[]" in params else
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    return java.util.stream.IntStream.rangeClosed(1, n)\n"
                f"        .filter(x -> x % 2 == 0)\n"
                f"        .sum();\n"
                f"}}"
            )
            lin_exp = "Single pass through the input stream filtering elements takes linear O(N) time and O(1) auxiliary memory."
        elif i % 3 == 1:
            # While loop style
            code_linear = (
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int idx = 0, acc = 0;\n"
                f"    while (idx < nums.length) {{\n"
                f"        acc += nums[idx];\n"
                f"        idx++;\n"
                f"    }}\n"
                f"    return acc;\n"
                f"}}"
                if "[]" in params else
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int curr = 1, sum = 0;\n"
                f"    while (curr <= n) {{\n"
                f"        sum += curr;\n"
                f"        curr++;\n"
                f"    }}\n"
                f"    return sum;\n"
                f"}}"
            )
            lin_exp = "A single while-loop increments the pointer across all N elements, executing in linear O(N) time with O(1) auxiliary space."
        else:
            # Standard for loop
            code_linear = (
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int count = 0;\n"
                f"    for (int i = 0; i < nums.length; i++) {{\n"
                f"        count += nums[i];\n"
                f"    }}\n"
                f"    return count;\n"
                f"}}"
                if "[]" in params else
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int res = 0;\n"
                f"    for (int i = 1; i <= n; i++) {{\n"
                f"        res += i;\n"
                f"    }}\n"
                f"    return res;\n"
                f"}}"
            )
            lin_exp = "Iterates through the input elements once in a single for loop with constant auxiliary memory."

        complexity_rows.append({
            "task": "analyze_code_complexity",
            "input": {
                "language": "java",
                "question": f"{title}: {desc}",
                "code": code_linear
            },
            "output": {
                "timeComplexity": "O(N)",
                "spaceComplexity": "O(1)",
                "explanation": lin_exp
            },
            "source_id": qid,
            "case_type": "linear",
            "source": "synthetic_rubric"
        })

        # -------------------------------------------------------------
        # Pattern 2: Nested Loops O(N^2) time, O(1) space
        # Variety: nested for, nested while, helper method calls
        # -------------------------------------------------------------
        if i % 3 == 0:
            # Helper method invocation inside loop
            code_quadratic = (
                f"private static boolean containsDuplicate(int[] arr, int target, int start) {{\n"
                f"    for (int k = start; k < arr.length; k++) {{\n"
                f"        if (arr[k] == target) return true;\n"
                f"    }}\n"
                f"    return false;\n"
                f"}}\n"
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int dupes = 0;\n"
                f"    for (int i = 0; i < nums.length; i++) {{\n"
                f"        if (containsDuplicate(nums, nums[i], i + 1)) dupes++;\n"
                f"    }}\n"
                f"    return dupes;\n"
                f"}}"
                if "[]" in params else
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int count = 0;\n"
                f"    for (int i = 0; i < n; i++) {{\n"
                f"        for (int j = 0; j < n; j++) count += (i * j);\n"
                f"    }}\n"
                f"    return count;\n"
                f"}}"
            )
            quad_exp = "Outer loop runs N times calling a linear search helper of size up to N, yielding O(N^2) quadratic time complexity and O(1) auxiliary space."
        elif i % 3 == 1:
            # Nested while-loop
            code_quadratic = (
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int i = 0, matches = 0;\n"
                f"    while (i < nums.length) {{\n"
                f"        int j = i + 1;\n"
                f"        while (j < nums.length) {{\n"
                f"            if (nums[i] == nums[j]) matches++;\n"
                f"            j++;\n"
                f"        }}\n"
                f"        i++;\n"
                f"    }}\n"
                f"    return matches;\n"
                f"}}"
                if "[]" in params else
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int i = 0, total = 0;\n"
                f"    while (i < n) {{\n"
                f"        int j = 0;\n"
                f"        while (j < n) {{\n"
                f"            total += (i + j);\n"
                f"            j++;\n"
                f"        }}\n"
                f"        i++;\n"
                f"    }}\n"
                f"    return total;\n"
                f"}}"
            )
            quad_exp = "Nested while-loops compare all pairs of elements, yielding quadratic O(N^2) time complexity and O(1) auxiliary space."
        else:
            # Standard nested for-loop
            code_quadratic = (
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int pairs = 0;\n"
                f"    for (int i = 0; i < nums.length; i++) {{\n"
                f"        for (int j = i + 1; j < nums.length; j++) {{\n"
                f"            if (nums[i] == nums[j]) pairs++;\n"
                f"        }}\n"
                f"    }}\n"
                f"    return pairs;\n"
                f"}}"
                if "[]" in params else
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int total = 0;\n"
                f"    for (int i = 0; i < n; i++) {{\n"
                f"        for (int j = 0; j < n; j++) {{\n"
                f"            total += (i + j);\n"
                f"        }}\n"
                f"    }}\n"
                f"    return total;\n"
                f"}}"
            )
            quad_exp = "Quadratic time complexity due to nested loops comparing every pair of elements, using O(1) space."

        complexity_rows.append({
            "task": "analyze_code_complexity",
            "input": {
                "language": "java",
                "question": f"{title}: {desc}",
                "code": code_quadratic
            },
            "output": {
                "timeComplexity": "O(N^2)",
                "spaceComplexity": "O(1)",
                "explanation": quad_exp
            },
            "source_id": qid,
            "case_type": "quadratic",
            "source": "synthetic_rubric"
        })

        # -------------------------------------------------------------
        # Pattern 3: Logarithmic O(log N) or Sorting O(N log N)
        # -------------------------------------------------------------
        if i % 2 == 0:
            # Binary search: O(log N)
            code_bs = (
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int low = 0, high = nums.length - 1;\n"
                f"    while (low <= high) {{\n"
                f"        int mid = low + (high - low) / 2;\n"
                f"        if (nums[mid] == 0) return mid;\n"
                f"        if (nums[mid] < 0) low = mid + 1;\n"
                f"        else high = mid - 1;\n"
                f"    }}\n"
                f"    return -1;\n"
                f"}}"
                if "[]" in params else
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    int low = 1, high = n;\n"
                f"    while (low <= high) {{\n"
                f"        int mid = low + (high - low) / 2;\n"
                f"        if (mid == n) return mid;\n"
                f"        if (mid < n) low = mid + 1; else high = mid - 1;\n"
                f"    }}\n"
                f"    return low;\n"
                f"}}"
            )
            complexity_rows.append({
                "task": "analyze_code_complexity",
                "input": {
                    "language": "java",
                    "question": f"{title}: {desc}",
                    "code": code_bs
                },
                "output": {
                    "timeComplexity": "O(log N)",
                    "spaceComplexity": "O(1)",
                    "explanation": "Logarithmic time complexity through repeated halving of the search space with O(1) auxiliary space."
                },
                "source_id": qid,
                "case_type": "logarithmic",
                "source": "synthetic_rubric"
            })
        else:
            # Sorting + Scan: O(N log N)
            code_sort = (
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    java.util.Arrays.sort(nums);\n"
                f"    int left = 0, right = nums.length - 1;\n"
                f"    while (left < right) {{\n"
                f"        if (nums[left] + nums[right] == 0) return left;\n"
                f"        left++; right--;\n"
                f"    }}\n"
                f"    return -1;\n"
                f"}}"
                if "[]" in params else
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    java.util.PriorityQueue<Integer> pq = new java.util.PriorityQueue<>();\n"
                f"    for (int i = 0; i < n; i++) pq.offer(i);\n"
                f"    return pq.peek();\n"
                f"}}"
            )
            complexity_rows.append({
                "task": "analyze_code_complexity",
                "input": {
                    "language": "java",
                    "question": f"{title}: {desc}",
                    "code": code_sort
                },
                "output": {
                    "timeComplexity": "O(N log N)",
                    "spaceComplexity": "O(1)" if "[]" in params else "O(N)",
                    "explanation": "Sorting or heap-based processing dominates the overall runtime with O(N log N) time complexity."
                },
                "source_id": qid,
                "case_type": "sorting",
                "source": "synthetic_rubric"
            })

        # -------------------------------------------------------------
        # Pattern 4: Hash Table O(N) time, O(N) space
        # -------------------------------------------------------------
        code_hash = (
            f"public static {ret_type} {method_name}({params}) {{\n"
            f"    java.util.HashMap<Integer, Integer> map = new java.util.HashMap<>();\n"
            f"    for (int x : nums) {{\n"
            f"        map.put(x, map.getOrDefault(x, 0) + 1);\n"
            f"    }}\n"
            f"    return map.size();\n"
            f"}}"
            if "[]" in params else
            f"public static {ret_type} {method_name}({params}) {{\n"
            f"    java.util.HashSet<Integer> set = new java.util.HashSet<>();\n"
            f"    for (int i = 0; i < n; i++) {{\n"
            f"        set.add(i * 2);\n"
            f"    }}\n"
            f"    return set.size();\n"
            f"}}"
        )
        complexity_rows.append({
            "task": "analyze_code_complexity",
            "input": {
                "language": "java",
                "question": f"{title}: {desc}",
                "code": code_hash
            },
            "output": {
                "timeComplexity": "O(N)",
                "spaceComplexity": "O(N)",
                "explanation": "Single pass populating a hash-based data structure takes linear time and linear O(N) auxiliary space."
            },
            "source_id": qid,
            "case_type": "hash_linear_space",
            "source": "synthetic_rubric"
        })

        # -------------------------------------------------------------
        # Pattern 5: Constant Time O(1) time, O(1) space (for 35 records)
        # -------------------------------------------------------------
        if i < 35:
            code_cst = (
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    if (nums == null || nums.length == 0) return 0;\n"
                f"    return nums[0] + nums[nums.length - 1];\n"
                f"}}"
                if "[]" in params else
                f"public static {ret_type} {method_name}({params}) {{\n"
                f"    // Direct arithmetic closed-form calculation\n"
                f"    return (n * (n + 1)) / 2;\n"
                f"}}"
            )
            complexity_rows.append({
                "task": "analyze_code_complexity",
                "input": {
                    "language": "java",
                    "question": f"{title}: {desc}",
                    "code": code_cst
                },
                "output": {
                    "timeComplexity": "O(1)",
                    "spaceComplexity": "O(1)",
                    "explanation": "Executes a fixed sequence of basic arithmetic and index operations independent of input size N, running in O(1) constant time and O(1) space."
                },
                "source_id": qid,
                "case_type": "constant",
                "source": "synthetic_rubric"
            })

        # -------------------------------------------------------------
        # Pattern 6: Cubic Time O(N^3) time, O(1) space
        # REQUIRED: At least 30 examples. We generate for i in range(0, 40).
        # Variety: triple for-loop, triple while-loop, helper method call, Stream API.
        # -------------------------------------------------------------
        if i < 40:
            if i % 4 == 0:
                # Style A: Triple nested for-loops (3-Sum brute force)
                code_cubic = (
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    int count = 0;\n"
                    f"    int n = nums.length;\n"
                    f"    for (int i = 0; i < n; i++) {{\n"
                    f"        for (int j = i + 1; j < n; j++) {{\n"
                    f"            for (int k = j + 1; k < n; k++) {{\n"
                    f"                if (nums[i] + nums[j] + nums[k] == 0) {{\n"
                    f"                    count++;\n"
                    f"                }}\n"
                    f"            }}\n"
                    f"        }}\n"
                    f"    }}\n"
                    f"    return count;\n"
                    f"}}"
                    if "[]" in params else
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    int count = 0;\n"
                    f"    for (int i = 0; i < n; i++) {{\n"
                    f"        for (int j = 0; j < n; j++) {{\n"
                    f"            for (int k = 0; k < n; k++) {{\n"
                    f"                count += (i + j + k);\n"
                    f"            }}\n"
                    f"        }}\n"
                    f"    }}\n"
                    f"    return count;\n"
                    f"}}"
                )
                exp_cubic = "Three nested for-loops each scale with input length N, performing constant-time additions inside the inner loop, yielding cubic O(N^3) time complexity and O(1) space."
            elif i % 4 == 1:
                # Style B: Triple nested while-loops
                code_cubic = (
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    int triplets = 0, n = nums.length;\n"
                    f"    int i = 0;\n"
                    f"    while (i < n) {{\n"
                    f"        int j = i + 1;\n"
                    f"        while (j < n) {{\n"
                    f"            int k = j + 1;\n"
                    f"            while (k < n) {{\n"
                    f"                if (nums[i] * nums[j] == nums[k]) triplets++;\n"
                    f"                k++;\n"
                    f"            }}\n"
                    f"            j++;\n"
                    f"        }}\n"
                    f"        i++;\n"
                    f"    }}\n"
                    f"    return triplets;\n"
                    f"}}"
                    if "[]" in params else
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    int i = 0, acc = 0;\n"
                    f"    while (i < n) {{\n"
                    f"        int j = 0;\n"
                    f"        while (j < n) {{\n"
                    f"            int k = 0;\n"
                    f"            while (k < n) {{\n"
                    f"                acc += (i * j + k);\n"
                    f"                k++;\n"
                    f"            }}\n"
                    f"            j++;\n"
                    f"        }}\n"
                    f"        i++;\n"
                    f"    }}\n"
                    f"    return acc;\n"
                    f"}}"
                )
                exp_cubic = "Three nested while-loops iterate across indices up to N with constant operations inside the deepest loop, giving O(N^3) time complexity and O(1) space."
            elif i % 4 == 2:
                # Style C: Nested loop calling a linear helper method
                code_cubic = (
                    f"private static int countOccurrences(int[] arr, int target) {{\n"
                    f"    int matches = 0;\n"
                    f"    for (int x : arr) if (x == target) matches++;\n"
                    f"    return matches;\n"
                    f"}}\n"
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    int total = 0, n = nums.length;\n"
                    f"    for (int i = 0; i < n; i++) {{\n"
                    f"        for (int j = 0; j < n; j++) {{\n"
                    f"            total += countOccurrences(nums, nums[i] + nums[j]);\n"
                    f"        }}\n"
                    f"    }}\n"
                    f"    return total;\n"
                    f"}}"
                    if "[]" in params else
                    f"private static int linearHelper(int limit) {{\n"
                    f"    int sum = 0;\n"
                    f"    for (int k = 0; k < limit; k++) sum += k;\n"
                    f"    return sum;\n"
                    f"}}\n"
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    int ans = 0;\n"
                    f"    for (int i = 0; i < n; i++) {{\n"
                    f"        for (int j = 0; j < n; j++) ans += linearHelper(n);\n"
                    f"    }}\n"
                    f"    return ans;\n"
                    f"}}"
                )
                exp_cubic = "Double nested loop of size N^2 calls a helper method running in linear O(N) time on each iteration, resulting in cubic O(N^3) total time complexity."
            else:
                # Style D: Stream API nested iterations
                code_cubic = (
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    int n = nums.length;\n"
                    f"    return (int) java.util.stream.IntStream.range(0, n)\n"
                    f"        .mapToLong(i -> java.util.stream.IntStream.range(0, n)\n"
                    f"            .mapToLong(j -> java.util.stream.IntStream.range(0, n)\n"
                    f"                .filter(k -> nums[i] + nums[j] == nums[k])\n"
                    f"                .count())\n"
                    f"            .sum())\n"
                    f"        .sum();\n"
                    f"}}"
                    if "[]" in params else
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    return (int) java.util.stream.IntStream.range(0, n)\n"
                    f"        .mapToLong(i -> java.util.stream.IntStream.range(0, n)\n"
                    f"            .mapToLong(j -> java.util.stream.IntStream.range(0, n)\n"
                    f"                .map(k -> i + j + k)\n"
                    f"                .sum())\n"
                    f"            .sum())\n"
                    f"        .sum();\n"
                    f"}}"
                )
                exp_cubic = "Three nested Stream range pipelines iterate over dimension N performing element filtering, yielding cubic O(N^3) time complexity."

            complexity_rows.append({
                "task": "analyze_code_complexity",
                "input": {
                    "language": "java",
                    "question": f"{title}: {desc}",
                    "code": code_cubic
                },
                "output": {
                    "timeComplexity": "O(N^3)",
                    "spaceComplexity": "O(1)",
                    "explanation": exp_cubic
                },
                "source_id": qid,
                "case_type": "cubic",
                "source": "synthetic_rubric"
            })

        # -------------------------------------------------------------
        # Pattern 7: Exponential Time O(2^N) time, O(N) space
        # REQUIRED: At least 30 examples. We generate for i in range(0, 40).
        # Variety: pure recursion, helper method recursion, recursive knapsack/subsets.
        # -------------------------------------------------------------
        if i < 40:
            if i % 3 == 0:
                # Style A: Pure binary recursive branching (Fibonacci style)
                code_exp = (
                    f"public static int fibBranch(int n) {{\n"
                    f"    if (n <= 1) return n;\n"
                    f"    return fibBranch(n - 1) + fibBranch(n - 2);\n"
                    f"}}\n"
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    int n = nums.length;\n"
                    f"    return fibBranch(n);\n"
                    f"}}"
                    if "[]" in params else
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    if (n <= 1) return n;\n"
                    f"    return {method_name}(n - 1) + {method_name}(n - 2);\n"
                    f"}}"
                )
                exp_reason = "Binary branching recursive calls at each step create a recursion tree of depth N, yielding 2^N leaf calls for exponential O(2^N) time complexity and O(N) call stack space."
            elif i % 3 == 1:
                # Style B: Power set / Subsets recursion with helper method
                code_exp = (
                    f"private static void generateSubsets(int[] arr, int index, java.util.List<Integer> curr, java.util.List<java.util.List<Integer>> res) {{\n"
                    f"    if (index == arr.length) {{\n"
                    f"        res.add(new java.util.ArrayList<>(curr));\n"
                    f"        return;\n"
                    f"    }}\n"
                    f"    generateSubsets(arr, index + 1, curr, res);\n"
                    f"    curr.add(arr[index]);\n"
                    f"    generateSubsets(arr, index + 1, curr, res);\n"
                    f"    curr.remove(curr.size() - 1);\n"
                    f"}}\n"
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    java.util.List<java.util.List<Integer>> result = new java.util.ArrayList<>();\n"
                    f"    generateSubsets(nums, 0, new java.util.ArrayList<>(), result);\n"
                    f"    return result.size();\n"
                    f"}}"
                    if "[]" in params else
                    f"private static void powerSet(int curr, int max, java.util.List<Integer> path) {{\n"
                    f"    if (curr > max) return;\n"
                    f"    powerSet(curr + 1, max, path);\n"
                    f"    path.add(curr);\n"
                    f"    powerSet(curr + 1, max, path);\n"
                    f"    path.remove(path.size() - 1);\n"
                    f"}}\n"
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    java.util.List<Integer> path = new java.util.ArrayList<>();\n"
                    f"    powerSet(1, n, path);\n"
                    f"    return path.size();\n"
                    f"}}"
                )
                exp_reason = "Generating all subsets explores 2 choices (include/exclude) for each of the N elements, requiring 2^N operations in O(2^N) time complexity and O(N) call stack space."
            else:
                # Style C: Recursive 0/1 knapsack / combination branch without memoization
                code_exp = (
                    f"private static int knapsackRec(int[] arr, int idx, int capacity) {{\n"
                    f"    if (idx >= arr.length || capacity <= 0) return 0;\n"
                    f"    int without = knapsackRec(arr, idx + 1, capacity);\n"
                    f"    int with = 0;\n"
                    f"    if (arr[idx] <= capacity) with = arr[idx] + knapsackRec(arr, idx + 1, capacity - arr[idx]);\n"
                    f"    return Math.max(with, without);\n"
                    f"}}\n"
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    return knapsackRec(nums, 0, 50);\n"
                    f"}}"
                    if "[]" in params else
                    f"private static int countCombos(int n, int target) {{\n"
                    f"    if (target == 0) return 1;\n"
                    f"    if (n <= 0 || target < 0) return 0;\n"
                    f"    return countCombos(n - 1, target - n) + countCombos(n - 1, target);\n"
                    f"}}\n"
                    f"public static {ret_type} {method_name}({params}) {{\n"
                    f"    return countCombos(n, 20);\n"
                    f"}}"
                )
                exp_reason = "Unmemoized recursive branching evaluates both inclusion and exclusion at every stage, generating a binary decision tree of depth N with O(2^N) time complexity and O(N) stack frames."

            complexity_rows.append({
                "task": "analyze_code_complexity",
                "input": {
                    "language": "java",
                    "question": f"{title}: {desc}",
                    "code": code_exp
                },
                "output": {
                    "timeComplexity": "O(2^N)",
                    "spaceComplexity": "O(N)",
                    "explanation": exp_reason
                },
                "source_id": qid,
                "case_type": "exponential",
                "source": "synthetic_rubric"
            })

    return complexity_rows
