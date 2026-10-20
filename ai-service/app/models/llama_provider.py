from abc import ABC, abstractmethod
import requests
import json
import re
import random
import logging
from app.config import settings
from app.utils.hr_scoring import calculate_hr_overall
from app.models.prompt_templates import build_training_style_prompt, TRAINING_SYSTEM_PROMPT

logger = logging.getLogger("ai_service")


def _safe_str(val) -> str:
    """Safely converts any value (string, dict, list, int, None) to a stripped string."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        if "questionText" in val:
            return _safe_str(val["questionText"])
        if "question" in val:
            return _safe_str(val["question"])
        if "text" in val:
            return _safe_str(val["text"])
        try:
            return json.dumps(val).strip()
        except Exception:
            return str(val).strip()
    if isinstance(val, list):
        try:
            return json.dumps(val).strip()
        except Exception:
            return str(val).strip()
    return str(val).strip()

# Root cause of "the first question is always the same": with an empty
# previous-questions list (always true for question #1 of every fresh
# interview) and a near-static RAG query, the prompt handed to LLaMA on Q1
# is essentially identical run to run. Even at temperature 0.7, an instruct
# model's output distribution for a short, extremely common prompt like
# "ask a Java theory question" is heavily peaked on the single most
# stereotypical example (e.g. "== vs equals()"), and for coding problems the
# model tends to just pick the first-listed item from the allowed-examples
# string. These pools let the code -- not the model's own sampling bias --
# pick a random sub-topic focus (or, for coding, a specific problem) each
# time, so consecutive fresh interviews stop converging on the same
# question. Not exhaustive; extend freely per subject.
_BUSINESS_DOMAINS = [
    "e-commerce order fulfillment", "hospital patient admissions", "university student course registration",
    "airline flight reservations", "banking account transaction history", "hotel room reservations",
    "streaming video subscription service", "warehouse logistics inventory", "ride-sharing trip dispatcher",
    "social media user interactions", "smart home IoT device telemetry", "customer support ticket desk",
    "restaurant table dining reservations", "vehicle rental fleet tracking", "human resources payroll records",
    "cloud infrastructure billing", "online food delivery tracking", "fintech payment gateway audit"
]

_THEORY_TOPIC_FOCUS = {
    "java": [
        "object-oriented design (inheritance, polymorphism, abstraction, or encapsulation)",
        "the Collections framework (List/Set/Map implementations and their trade-offs)",
        "exception handling and checked vs. unchecked exceptions",
        "memory management, stack vs heap, and garbage collection algorithms",
        "multithreading, thread safety, and concurrency utilities (ExecutorService, synchronized, volatile)",
        "String immutability, StringBuilder, and the String pool",
        "interfaces vs. abstract classes and default interface methods",
        "generics, bounded wildcards, and type erasure",
        "the static keyword, class-level members, and static initialization blocks",
        "constructors, method overloading vs overriding, and object initialization lifecycle",
        "Java 8 functional interfaces, lambda expressions, and Stream API mechanics",
        "JVM architecture: classloader, bytecode execution, and JIT compilation",
        "equals() and hashCode() contract and impact on hashing collections",
        "final, finally, and finalize distinctions",
        "Serialization, deserialization, and the transient keyword",
        "custom annotations and Java Reflection API trade-offs",
        "concurrency locks: ReentrantLock vs synchronized keyword",
        "ConcurrentHashMap internal design and locking buckets",
        "Optional class best practices and avoiding NullPointerExceptions",
        "Shallow copy vs Deep copy and the Cloneable interface",
        "try-with-resources statement and the AutoCloseable interface",
        "ThreadLocal variables and potential memory leak risks",
        "Comparable vs Comparator interfaces and custom sorting strategies",
        "Design patterns in Java: Singleton, Factory, and Builder implementations",
        "Java Virtual Threads (Project Loom) vs platform OS threads",
        "Garbage collectors in JVM: G1, ZGC, and generational CMS differences",
        "Method references and functional composition in java.util.function",
        "Java memory model (JMM), happens-before relationship, and atomic variables",
        "WeakReference, SoftReference, and PhantomReference use cases in caching",
        "Record classes, sealed classes, and pattern matching in modern Java",
    ],
    "dbms": [
        "normalization forms (1NF, 2NF, 3NF, BCNF) and intentional denormalization trade-offs",
        "SQL joins (INNER, LEFT, RIGHT, FULL, CROSS) and set operations (UNION, INTERSECT, EXCEPT)",
        "transactions, ACID properties (Atomicity, Consistency, Isolation, Durability)",
        "transaction isolation levels (Read Uncommitted, Read Committed, Repeatable Read, Serializable) and concurrency anomalies",
        "indexing strategies: B-Tree vs Hash indexes, clustered vs non-clustered indexes",
        "composite indexes, leftmost prefix rule, and covering indexes",
        "keys and referential integrity: primary, candidate, foreign, and surrogate keys",
        "database views, materialized views, and stored procedures vs application logic",
        "concurrency control: two-phase locking (2PL), deadlock detection, and prevention",
        "optimistic vs pessimistic concurrency control mechanisms",
        "the differences between relational SQL and NoSQL data models (document, key-value, graph)",
        "database sharding, horizontal vs vertical partitioning, and replication strategies",
        "query execution plans (EXPLAIN), table scans, and index seek optimization",
        "Write-Ahead Logging (WAL) and database crash recovery (ARIES protocol)",
        "database triggers, sequences, and check constraints trade-offs",
        "connection pooling, idle connection management, and database connection lifecycle",
        "CAP theorem and consistency models in distributed databases",
        "handling NULL values, three-valued logic (3VL), and NULL in aggregate functions",
        "database schema migration strategies and zero-downtime schema evolution",
        "Common Table Expressions (CTEs) vs subqueries and temporary tables",
        "database security: SQL injection prevention, role-based access control, and encryption at rest",
        "OLTP vs OLAP system architectures and column-oriented storage",
        "aggregate functions, GROUP BY, and HAVING filtering mechanics",
        "window functions (ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD) architectural differences from GROUP BY",
        "database vacuuming, MVCC (Multi-Version Concurrency Control), and bloat management in engines like PostgreSQL",
        "foreign key cascading options: ON DELETE CASCADE vs RESTRICT vs SET NULL",
        "database full-text search indexes vs standard B-tree indexing",
        "distributed transactions and Two-Phase Commit (2PC) protocol",
        "read replicas, replication lag, and eventual consistency implications",
        "database deadlock resolution, lock timeouts, and graph cycle detection",
    ],
    "hr": [
        "teamwork, collaboration, and resolving peer conflicts on technical decisions",
        "handling tight deadlines, stress, and shifting project priorities",
        "communication with non-technical stakeholders and managing expectations",
        "demonstrating leadership, ownership, and initiative on ambiguous project tasks",
        "adapting to sudden organizational or technological changes",
        "learning from a major failure, bug in production, or professional mistake",
        "handling constructive criticism and incorporating feedback during code reviews",
        "mentoring junior engineers and knowledge sharing across engineering teams",
        "prioritizing technical debt reduction versus delivering fast business features",
        "disagreeing with a manager's decision while committing to the agreed path forward",
        "working effectively in remote, distributed, or cross-time-zone teams",
        "managing scope creep and negotiating delivery boundaries with product managers",
        "navigating ethical dilemmas or quality compromises in software delivery",
        "staying continuously updated with new technologies and self-driven learning",
        "balancing individual contributor tasks with team unblocking and code reviewing",
    ],
}
_GENERIC_THEORY_FOCUS = [
    "a core fundamental concept",
    "a commonly misunderstood edge case",
    "a practical architectural trade-off engineers weigh in real projects",
    "performance bottlenecks and optimization techniques",
    "best practices for robust and maintainable system design",
]

_OUTPUT_PREDICTION_FOCUS = {
    "java": [
        "operator precedence, ternary operators, and evaluation order",
        "mutability vs. immutability (String vs StringBuilder, array element mutations)",
        "loop boundaries, post-increment vs pre-increment (i++ vs ++i), and accumulator state",
        "type coercion, implicit numeric promotion, and integer overflow truncation",
        "variable scoping, local variable shadowing, and static member hiding",
        "object references vs. primitive value passing in method calls",
        "static vs. instance initialization block order and constructor execution sequence",
        "polymorphism and dynamic method dispatch with overridden methods",
        "try-catch-finally control flow when return statements are present in multiple blocks",
        "boxing and unboxing equality nuances (Integer cache between -128 and 127)",
        "array clone behavior vs multidimensional array shallow copies",
        "bitwise operations (shift, AND, OR, XOR) and signed bit extensions",
        "inheritance field access vs method overriding resolution rules",
        "anonymous inner class variable capture and effective finality",
        "switch statement fall-through behavior without break statements",
    ],
    "dbms": [
        "aggregate functions, GROUP BY behavior, and COUNT(*) vs COUNT(column)",
        "NULL handling in comparisons, arithmetic operations, and IN subquery evaluation",
        "join result cardinality when duplicate keys exist in both tables",
        "ordering, NULLS FIRST / NULLS LAST, and LIMIT/OFFSET pagination behavior",
        "CASE WHEN conditional expression evaluation with NULL conditions",
        "DISTINCT operator combined with aggregate functions and multiple columns",
        "HAVING clause filtering vs WHERE clause filtering execution sequence",
        "UNION vs UNION ALL result set deduplication and row counts",
        "correlated subquery row-by-row filtering evaluation",
        "LEFT JOIN with WHERE condition on the right table turning into an INNER JOIN",
        "BETWEEN operator boundary inclusion on dates and timestamps",
        "COALESCE and NULLIF function resolution on mixed null and non-null values",
    ],
}


_HR_FORBIDDEN_TOPIC = re.compile(
    r"\b(?:java|javascript|python|programming|coding|code|sql|dbms|database|query|algorithm|"
    r"data structure|schema|api|framework|debugging|compiler|indexing|normalization)\b",
    re.IGNORECASE,
)


def _pick_topic_focus(subject: str, previous: list, pool_by_subject: dict, generic_pool: list, rejected: list = None) -> str:
    """
    Picks a random sub-topic focus for this call, skipping any focus phrase
    that already appears (case-insensitively) among previously asked
    questions or rejected attempts in this session so a long session doesn't loop back onto the
    same sub-topic it already covered.
    """
    pool = pool_by_subject.get((subject or "").lower()) or generic_pool
    prev_text = " ".join(_safe_str(p) for p in (previous or [])).lower()
    rej_text = " ".join(_safe_str(r) for r in (rejected or [])).lower()
    combined = f"{prev_text} {rej_text}"
    candidates = [p for p in pool if p.lower() not in combined]
    if not candidates:
        domain = random.choice(_BUSINESS_DOMAINS)
        candidates = [f"{p} in the context of a {domain}" for p in pool]
    return random.choice(candidates)


class AIGenerationUnavailableError(RuntimeError):
    """
    Raised when a question (theory or output-prediction) or a follow-up
    could not be generated by the fine-tuned LLaMA model.

    By design, question/follow-up generation is NEVER served from a static
    question bank or database -- the knowledge base under /knowledge is RAG
    context only (retrieved chunks fed into the LLaMA prompt), not a source
    of ready-made questions. So when LLaMA can't be reached or returns an
    unusable response, callers should surface this error (e.g. as a 503)
    instead of silently degrading to canned content.
    """
    pass


class BaseAIModel(ABC):
    @abstractmethod
    def generate_question(self, subject: str, difficulty: str, context: list, previous: list, question_format: str = "theory", interview_type: str = "technical") -> dict:
        pass

    @abstractmethod
    def generate_followup(self, question: str, answer: str, concepts: list, previous: list = None, interview_type: str = "technical") -> dict:
        pass

    @abstractmethod
    def evaluate_answer(self, question: str, answer: str, concepts: list, context: list, question_format: str = "theory", expected_output: str = None, explanation: str = None, test_cases: list = None, language: str = None, hr_delivery_metrics: dict = None, interview_type: str = "technical") -> dict:
        pass


def _estimate_code_complexity_heuristic(code: str) -> dict:
    """
    Deterministic static heuristic for time and space complexity when LLM is unavailable or offline.
    """
    clean_code = re.sub(r"//.*|/\*[\s\S]*?\*/", "", code or "")
    if not clean_code.strip():
        return {"timeComplexity": None, "spaceComplexity": None, "explanation": None}

    # Check for recursion
    has_recursion = bool(re.search(r"(\w+)\s*\([^)]*\)\s*\{[\s\S]*?\b\1\s*\(", clean_code))

    # Check for binary search or divide-and-conquer
    has_log = bool(re.search(r"(>>\s*1|/\s*2|\bmid\b|\bbinarySearch\b)", clean_code))

    # Check for sorting
    has_sort = bool(re.search(r"(Arrays\.sort|Collections\.sort|\.sort\()", clean_code))

    # Check for nested loops: loop inside another loop body
    nested_loops = bool(re.search(r"(for|while)\s*\([^)]*\)\s*\{[\s\S]*?(for|while)\s*\(", clean_code))

    # Check for single loops
    has_loop = bool(re.search(r"\b(for|while)\s*\(", clean_code))

    # Space checks (data structures)
    has_extra_space = bool(re.search(r"\b(new\s+(int|String|char|long|double|boolean)\[|new\s+(ArrayList|HashMap|HashSet|LinkedList|ArrayDeque|PriorityQueue|TreeMap|TreeSet))\b", clean_code))

    if has_sort:
        time_c = "O(N log N)"
        exp = "Dominated by sorting operation O(N log N)."
    elif nested_loops:
        time_c = "O(N^2)"
        exp = "Quadratic time complexity due to nested iteration over input elements."
    elif has_log and has_loop:
        time_c = "O(N log N)"
        exp = "Logarithmic operations within iteration yielding O(N log N) time complexity."
    elif has_log:
        time_c = "O(log N)"
        exp = "Logarithmic time complexity through repeated halving of the search space."
    elif has_loop or has_recursion:
        time_c = "O(N)"
        exp = "Linear time complexity iterating through the input elements."
    else:
        time_c = "O(1)"
        exp = "Constant time operations with no loops or recursive calls."

    space_c = "O(N)" if (has_extra_space or has_recursion) else "O(1)"
    return {
        "timeComplexity": time_c,
        "spaceComplexity": space_c,
        "explanation": exp,
    }


def _build_score_reason(score: int, missing_concepts: list, weaknesses: list) -> str:
    """
    Deterministic, always-available explanation of why the score isn't
    100%, built from whatever the grader already extracted. Used whenever
    the LLM doesn't return its own scoreReason, and as the reasoning for
    the fully offline fallback path. Produces one short sentence per
    concrete gap, matching the "Correctly explained X. However it missed
    Y." style the UI expects.
    """
    if score >= 98:
        return "Your answer covered the required concepts accurately and completely."
    sentences = []
    if missing_concepts:
        if len(missing_concepts) == 1:
            sentences.append(f"The answer did not explain {missing_concepts[0]}.")
        else:
            shown = ", ".join(missing_concepts[:3])
            sentences.append(f"The answer did not cover: {shown}.")
    for w in weaknesses[:2]:
        w_clean = w.rstrip(".")
        sentences.append(f"{w_clean}.")
    if not sentences:
        sentences.append("The explanation was correct but not detailed or precise enough to count as complete.")
    return " ".join(sentences)


_TEXT_SCORE_WEIGHTS = {
    "relevance": 0.25,
    "correctness": 0.25,
    "conceptCoverage": 0.25,
    "communication": 0.25,
}


def _bounded_score(value, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _irrelevant_text_evaluation() -> dict:
    reason = "The answer is unrelated to the question."
    return {
        "score": 0,
        "conceptCoverage": 0.0,
        "correctness": 0.0,
        "relevance": 0.0,
        "communication": 0.0,
        "isIrrelevant": True,
        "feedback": reason,
        "strengths": [],
        "weaknesses": [],
        "coveredConcepts": [],
        "partiallyCoveredConcepts": [],
        "missingConcepts": [],
        "deeperConcepts": [],
        "improvementSuggestion": "Provide an answer that directly addresses the question.",
        "scoreReason": reason,
        "modelUsed": "fallback_rules",
        "usedFallback": True,
        "scoringSources": ["rules"],
    }


def _calculate_text_score(relevance: float, correctness: float, concept_coverage: float,
                          communication: float) -> int:
    percents = [
        round(max(0.0, min(1.0, float(v))) * 100)
        for v in (relevance, correctness, concept_coverage, communication)
    ]
    return int(sum(percents) / len(percents) + 0.5)


def _classify_expected_concepts(concepts: list, answer: str, embedding_service,
                                model_covered: list = None, model_partial: list = None,
                                model_missing: list = None,
                                semantic_relevance: float = 1.0) -> tuple:
    covered, partially_covered, missing = [], [], []
    model_covered = model_covered or []
    model_partial = model_partial or []
    model_missing = model_missing or []

    def matches_label(concept: str, labels: list) -> bool:
        return any(
            embedding_service.compute_similarity(concept, str(label)) >= 0.55
            for label in labels if label
        )

    stop_words = {"a", "an", "the", "in", "on", "of", "to", "and", "or", "for", "with", "is", "are", "by", "from", "at", "as"}

    def concept_content_match(concept: str, answer_text: str) -> float:
        c_clean = str(concept).strip().lower()
        a_clean = str(answer_text).strip().lower()
        if not c_clean or not a_clean:
            return 0.0
        if c_clean in a_clean:
            return 1.0
        c_words = [w for w in re.findall(r"[a-z0-9]+", c_clean) if w not in stop_words]
        if not c_words:
            return 1.0 if c_clean in a_clean else 0.0
        a_words = set(re.findall(r"[a-z0-9]+", a_clean))
        matched = sum(1 for w in c_words if w in a_words or any(aw.startswith(w) or w.startswith(aw) for aw in a_words if len(aw) >= 4 and len(w) >= 4))
        return matched / len(c_words)

    for concept in concepts or []:
        c_str = str(concept).strip()
        if not c_str:
            continue
        similarity = embedding_service.best_sentence_similarity(c_str, answer)
        content_coverage = concept_content_match(c_str, answer)
        if content_coverage >= 0.60:
            similarity = max(similarity, 0.45 + 0.55 * content_coverage)
        elif content_coverage >= 0.35:
            similarity = max(similarity, 0.30 + 0.30 * content_coverage)

        listed_missing = matches_label(c_str, model_missing)
        listed_partial = matches_label(c_str, model_partial)
        listed_covered = matches_label(c_str, model_covered)

        if similarity >= 0.45:
            covered.append(c_str)
        elif listed_covered and semantic_relevance >= 0.30 and similarity >= 0.10:
            covered.append(c_str)
        elif listed_partial and semantic_relevance >= 0.30 and similarity >= 0.10:
            partially_covered.append(c_str)
        elif listed_missing and similarity < 0.70:
            missing.append(c_str)
        elif similarity >= 0.30 or (listed_covered and similarity >= 0.25):
            partially_covered.append(c_str)
        else:
            missing.append(c_str)

    return covered, partially_covered, missing


def _filter_to_current_question(items: list, concepts: list, threshold: float = 0.35) -> list:
    """
    Code-level enforcement (not just a prompt instruction) that missing-
    concept / weakness feedback is actually about THIS question, not one
    Llama has drifted onto (either by inventing a tangentially-related gap,
    or -- as observed in practice -- echoing back the worked example from
    its own instructions almost verbatim instead of grading the real
    answer).

    Keeps an item only if it's semantically close to at least one of this
    question's own `concepts` (its expectedConcepts). If `concepts` is
    empty, there's nothing to check against, so everything is kept as-is
    rather than blindly discarding real feedback.
    """
    if not items or not concepts:
        return items or []
    from app.services.embedding_service import embedding_service

    kept = []
    for item in items:
        if isinstance(item, dict):
            item_text = str(item.get("concept") or item.get("name") or item).strip()
        else:
            item_text = str(item or "").strip()
        if not item_text:
            continue
        best = max(embedding_service.compute_similarity(item_text, c) for c in concepts)
        if best >= threshold:
            kept.append(item)
        else:
            logger.info(
                f"[Evaluator] dropped off-question feedback item (best sim {best:.2f} < {threshold}): "
                f"{item_text[:120]!r}"
            )
    return kept


def _score_reason_matches_question(score_reason: str, question: str, concepts: list, threshold: float = 0.28) -> bool:
    """
    Sanity check that scoreReason is actually about the question just
    asked. Catches the case where Llama's response text drifted onto an
    unrelated topic (e.g. reusing the illustrative example from its own
    prompt) instead of grading the real answer -- a prompt instruction
    alone isn't a guarantee, so this is verified in code before the text
    is shown to the candidate.
    """
    if not score_reason:
        return False
    from app.services.embedding_service import embedding_service

    reference = question if not concepts else f"{question} {', '.join(concepts)}"
    return embedding_service.compute_similarity(score_reason, reference) >= threshold


def _extract_json(raw_text: str) -> dict:
    """
    LLaMA responses are plain text, not guaranteed valid JSON. Strip markdown
    fences, then grab the JSON block and parse it. Handles truncated JSON by
    auto-repairing unclosed quotes and missing closing brackets/braces.
    """
    if not raw_text:
        raise ValueError("empty response")
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned.strip(), flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned.strip()).strip()

    start_idx = cleaned.find("{")
    if start_idx == -1:
        raise ValueError(f"no JSON object found in model output: {raw_text[:200]!r}")
    
    blob = cleaned[start_idx:]
    
    # Extract match if full brace pair exists
    match = re.search(r"\{.*\}", blob, flags=re.DOTALL)
    target = match.group(0) if match else blob

    for attempt_str in [target, blob]:
        try:
            return json.loads(attempt_str)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(attempt_str, strict=False)
        except json.JSONDecodeError:
            pass
        repaired = re.sub(r",\s*([\}\]])", r"\1", attempt_str)
        try:
            return json.loads(repaired, strict=False)
        except json.JSONDecodeError:
            pass
        
        # Auto-repair truncated output (unclosed quote / unclosed braces)
        repaired_auto = attempt_str.strip()
        if repaired_auto.count('"') % 2 != 0:
            repaired_auto += '"'
        repaired_auto = re.sub(r",\s*$", "", repaired_auto)
        open_braces = repaired_auto.count("{") - repaired_auto.count("}")
        open_brackets = repaired_auto.count("[") - repaired_auto.count("]")
        if open_brackets > 0:
            repaired_auto += "]" * open_brackets
        if open_braces > 0:
            repaired_auto += "}" * open_braces
        
        try:
            return json.loads(repaired_auto, strict=False)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"no JSON object found in model output: {raw_text[:200]!r}")



# ---------------------------------------------------------------------------
# Difficulty tiers for Java coding questions. An 8B instruct model will
# happily label a dynamic-programming problem "easy" if left to its own
# judgement, so each tier pins down an explicit problem whitelist, an
# explicit forbidden list, and an allowed complexity ceiling. The forbidden
# keywords double as a post-generation validator (see
# _detect_off_tier_problem) so an off-tier problem is rejected and
# regenerated rather than shown to the candidate.
#
# NOTE: this was referenced throughout the file you pasted but never
# actually defined -- that missing definition is one of the causes of the
# errors you were hitting. Reconstructed here; tune the example pools freely.
# ---------------------------------------------------------------------------
_CODING_DIFFICULTY_SPECS = {
    "easy": {
        "rule": (
            "EASY means a single loop or a single pass over one array/string, with no "
            "nested data structures and no recursion. Someone who just finished an "
            "introductory programming course should be able to solve it directly."
        ),
        "examples": (
            "find the factorial of a number; "
            "check if a number is prime; "
            "reverse a string; "
            "count the vowels in a string; "
            "find the maximum element in an array; "
            "find the minimum element in an array; "
            "check if a string is a palindrome; "
            "compute the sum of digits of a number; "
            "find the nth Fibonacci number iteratively; "
            "check if a year is a leap year; "
            "count occurrences of a specific character in a string; "
            "calculate the average of an integer array; "
            "check if an array is sorted in ascending order; "
            "remove all occurrences of a character from a string; "
            "compute the power of a number iteratively; "
            "find the second smallest number in an array; "
            "convert binary string to integer; "
            "convert Celsius to Fahrenheit temperature; "
            "determine if a number is an Armstrong number; "
            "check if two numbers are coprime; "
            "find the greatest common divisor of two numbers; "
            "find the least common multiple of two numbers; "
            "count uppercase and lowercase letters in a string; "
            "replace all spaces in a string with a delimiter; "
            "find the length of the shortest word in a sentence; "
            "return all even numbers from an array; "
            "check if a string contains only digits; "
            "reverse the elements of an array in place; "
            "find the sum of all elements in an array; "
            "check if an integer is a perfect square; "
            "find the absolute difference between array sum and product"
        ),
        "forbidden": "dynamic programming, recursion, graphs, trees, linked lists, hashmaps",
        "complexity": "O(n) or O(n^2) is acceptable; no need for an optimal solution.",
    },
    "medium": {
        "rule": (
            "MEDIUM means it needs a HashMap/HashSet, sorting, two-pointer technique, or "
            "simple array/string manipulation with an edge case to handle correctly."
        ),
        "examples": (
            "remove duplicates from a list while preserving order; "
            "find the two numbers in an array that sum to a target; "
            "check whether two strings are anagrams; "
            "merge two sorted arrays into a single sorted array; "
            "find the first non-repeating character in a string; "
            "rotate an array by k positions; "
            "find the missing number in a range; "
            "find the single number that appears only once in an array where all others appear twice; "
            "compress a string using run-length encoding of repeated characters; "
            "check if a string containing parentheses, brackets, and braces is balanced; "
            "find the length of the longest substring without repeating characters; "
            "group an array of strings into anagram clusters; "
            "find the maximum subarray sum using Kadane's algorithm; "
            "determine if an array contains any duplicate values within k distance; "
            "implement binary search to find target index in a sorted array; "
            "find the intersection of two integer arrays; "
            "find the majority element that appears more than n/2 times in an array; "
            "find the peak element in an array; "
            "calculate the product of array except self without division; "
            "sort an array of 0s, 1s, and 2s in one pass; "
            "find the longest consecutive elements sequence in an unsorted array; "
            "reverse words in a given sentence while maintaining single spaces; "
            "find all pairs of integers in an array whose difference equals k; "
            "find the contiguous subarray with the maximum product; "
            "implement custom string-to-integer parsing with overflow handling; "
            "compute the next greater element for each item in an array; "
            "merge overlapping intervals in a collection of time ranges; "
            "find the length of the longest palindromic substring; "
            "find common elements in three sorted arrays; "
            "check if one string is a rotation of another string; "
            "find the sub-array with a given target sum using two pointers; "
            "find the top k most frequent elements in an integer array; "
            "validate if a given string is a valid IPv4 address; "
            "find the container with most water given vertical bar heights"
        ),
        "forbidden": "dynamic programming, graphs, trees, tries, segment trees, backtracking",
        "complexity": "O(n log n) or O(n) with extra space is expected.",
    },
    "hard": {
        "rule": (
            "HARD means it genuinely requires recursion, dynamic programming, or a "
            "non-trivial data structure (tree, graph, linked list) to solve correctly."
        ),
        "examples": (
            "compute the nth Fibonacci number with memoization; "
            "solve the coin change problem for minimum coins; "
            "find the longest common subsequence of two strings; "
            "detect a cycle in a linked list; "
            "perform a level-order traversal of a binary tree; "
            "solve the 0/1 knapsack problem for maximum value; "
            "find the minimum edit distance between two strings; "
            "find the trapping rain water capacity across elevation bars; "
            "find the longest increasing subsequence length in an array; "
            "implement a Least Recently Used (LRU) Cache data structure; "
            "find the maximum path sum in a binary tree; "
            "solve the word ladder problem finding minimum transformations; "
            "find the median of two sorted arrays in logarithmic time; "
            "serialize and deserialize a binary tree; "
            "find the shortest path in a grid with obstacles using BFS; "
            "solve the N-Queens problem counting valid placements; "
            "find strongly connected components in a directed graph; "
            "find the sliding window maximum for k-sized windows; "
            "evaluate reverse Polish notation expressions; "
            "find the longest valid parentheses substring length; "
            "merge k sorted linked lists efficiently"
        ),
        "forbidden": "vendor-specific or highly obscure syntax tricks",
        "complexity": "Polynomial-time solutions (e.g. O(n^2) DP) are acceptable.",
    },
}

# Difficulty tiers for DBMS coding questions (SQL query writing)
_SQL_DIFFICULTY_SPECS = {
    "easy": {
        "rule": (
            "EASY means a single-table query: SELECT with a simple WHERE filter, "
            "ORDER BY, or one basic aggregate function (COUNT, SUM, AVG, MAX, MIN) "
            "with no GROUP BY. No JOIN, no subquery."
        ),
        "examples": (
            "select all employees earning above a given salary; "
            "list employees in a specific department; "
            "count total employees; "
            "find the average salary; "
            "list employees ordered by salary descending; "
            "find employees whose name starts with a given letter; "
            "select distinct department names; "
            "find the employee with the maximum salary; "
            "list products ordered by price descending with stock greater than zero; "
            "find customer records whose last name starts with a given prefix; "
            "select distinct job titles across all branch offices; "
            "find the transaction with the maximum amount in the last month; "
            "list orders with status completed placed after a specific date; "
            "calculate total inventory value; "
            "find all students enrolled in a specific grade level; "
            "select authors who have published books with more than 300 pages; "
            "list unique countries represented among registered users; "
            "count the number of patients admitted in a specific hospital wing; "
            "find all flights departing from a given airport code; "
            "select properties with more than 3 bedrooms and price below budget; "
            "find gym members whose membership expires within 30 days; "
            "calculate minimum and maximum temperatures recorded in weather logs; "
            "find vehicles in the showroom with mileage under 10000 miles; "
            "select active restaurant menu items that are marked as vegetarian; "
            "find invoices that have not been marked as paid; "
            "list bank accounts with balance below minimum required threshold"
        ),
        "forbidden": "JOIN, subqueries, GROUP BY with HAVING, window functions",
    },
    "medium": {
        "rule": (
            "MEDIUM means exactly one JOIN across two tables, OR a GROUP BY "
            "with HAVING, OR one simple subquery."
        ),
        "examples": (
            "list employees with department names using JOIN; "
            "find departments with more than N employees; "
            "find employees earning above average salary; "
            "count orders placed by each customer; "
            "find customers who registered but have never placed any order using a LEFT JOIN; "
            "find the top selling product by total units sold in each category; "
            "list courses and the number of students enrolled using a JOIN with GROUP BY; "
            "calculate monthly revenue totals and order counts for the current year; "
            "find patients who have had more than 3 doctor appointments this year; "
            "retrieve supplier names and the count of distinct products they provide; "
            "find flight routes where average ticket price exceeds a specific threshold; "
            "list authors whose total book sales exceed 50000 copies using HAVING; "
            "find departments where the minimum salary is greater than a specified amount; "
            "find projects that have exceeded their allocated budget using joined expense tables; "
            "list customers who purchased products in two different categories; "
            "find the latest login timestamp for each user across multiple devices; "
            "calculate average shipping duration grouped by shipping carrier; "
            "find warehouse locations storing more than 500 units of inventory; "
            "list hotel rooms that were booked for more than 20 days in a given month; "
            "find sales representatives who achieved higher sales than their department average; "
            "retrieve accounts that made transfers exceeding the historical average; "
            "find students whose GPA is higher than their major department median; "
            "list subscriptions renewing within the next 7 days along with user contact details; "
            "calculate total discount given per promotional coupon campaign; "
            "find products whose stock level is lower than average daily demand; "
            "count number of support tickets resolved by each agent in under 2 hours; "
            "find cities where total order volume is greater than 10000 dollars"
        ),
        "forbidden": (
            "window functions, recursive queries, correlated subqueries, "
            "more than one JOIN"
        ),
    },
    "hard": {
        "rule": (
            "HARD means multiple JOINs, correlated subqueries, self-joins, "
            "or window functions."
        ),
        "examples": (
            "find second highest salary in each department; "
            "employees earning more than their manager; "
            "rank employees by salary within department; "
            "calculate cumulative running total of revenue per day using window functions; "
            "identify the top 3 highest spending customers per geographic region; "
            "calculate month-over-month revenue growth percentage using the LAG window function; "
            "find consecutive days where website traffic exceeded 10000 visitors; "
            "identify customers who made purchases in every single quarter of the past year; "
            "find employees whose tenure is longer than all managers in their department; "
            "calculate moving average of daily stock prices over a 7-day sliding window; "
            "detect duplicate customer profiles based on shared email or matching phone numbers; "
            "find gaps in sequentially numbered invoice records; "
            "list the longest uninterrupted streak of active daily usage for each subscriber; "
            "calculate retention rate of cohorts registered in the same calendar month; "
            "rank salesmen by commission rate and assign performance quartiles using NTILE; "
            "find the department with the highest ratio of senior to junior staff members; "
            "calculate median order value by customer segment without using built-in MEDIAN; "
            "identify churned users who were active for 3 consecutive months then inactive for 2; "
            "list parent-child category hierarchies using recursive Common Table Expressions"
        ),
        "forbidden": "vendor-specific obscure syntax",
    },
}

# Keyword -> tiers where that keyword signals the problem is TOO HARD.
# Checked against the generated statement so an off-tier problem is caught
# before the candidate ever sees it.
_OFF_TIER_KEYWORDS = {
    "easy": [
        "dynamic programming", "memoi", "backtrack", "binary search", "two pointer",
        "sliding window", "hashmap", "hash map", "hashset", "hash set", "matrix",
        "2d array", "two-dimensional", "linked list", "binary tree", "graph", "bfs",
        "dfs", "stack", "queue", "recursion", "recursive", "subsequence", "subset",
        "permutation", "kadane", "merge sort", "quick sort", "bit manipulation",
    ],
    "medium": [
        "dynamic programming", "memoi", "backtrack", "n-queens", "knapsack",
        "longest common subsequence", "linked list", "binary tree", "graph", "bfs",
        "dfs", "topological", "union-find", "union find", "trie", "segment tree",
        "rotate the matrix", "spiral", "generate all subsets", "all permutations",
        "lru cache", "word break", "coin change",
    ],
    "hard": [
        "segment tree", "suffix automaton", "max-flow", "max flow", "multithread",
        "concurrency", "thread-safe",
    ],
}


def _detect_off_tier_problem(question_text: str, title: str, difficulty_key: str) -> str:
    """
    Returns the first forbidden keyword found in the generated problem for
    this difficulty tier, or "" if the problem looks on-tier. Used to reject
    and regenerate rather than show an "easy" question that is really a DP
    problem in disguise.
    """
    haystack = f"{title} {question_text}".lower()
    for kw in _OFF_TIER_KEYWORDS.get(difficulty_key, []):
        if kw in haystack:
            return kw
    return ""


def _normalize_for_match(text) -> str:
    cleaned = _safe_str(text)
    return re.sub(r"\s+", " ", cleaned.lower())


def _is_duplicate_question(candidate, previous: list, threshold: float = 0.85) -> str:
    """
    Code-level (not just prompted-for) duplicate check, per the product
    requirement that a question must be rejected and regenerated if it
    repeats an earlier one in this session -- "even if LLaMA changes only
    the wording."

    Returns a short human-readable reason if `candidate` is judged a
    duplicate of something in `previous`, otherwise "". Two layers:
      1. Exact/near-exact match on whitespace/case-normalized text --
         catches LLaMA literally reusing a previous question.
      2. BERT semantic similarity (embedding_service, same model used for
         answer grading) -- catches genuine paraphrases.
    """
    cand_str = _safe_str(candidate)
    if not cand_str or not previous:
        return ""
    norm_candidate = _normalize_for_match(cand_str)
    if not norm_candidate:
        return ""
    for prev in previous:
        if prev and _normalize_for_match(prev) == norm_candidate:
            return "identical (or near-identical after normalizing whitespace/case) to a question already asked this session"

    from app.services.embedding_service import embedding_service

    best_sim = 0.0
    for prev in previous:
        if not prev:
            continue
        sim = embedding_service.compute_similarity(cand_str, _safe_str(prev))
        if sim > best_sim:
            best_sim = sim
    if best_sim >= threshold:
        return f"too semantically similar (similarity {best_sim:.2f} >= {threshold}) to a question already asked this session"
    return ""


_JAVA_METHOD_STUB = re.compile(
    r"\b(public|private|protected|static)\b[^;{]*\b\w+\s*\([^)]*\)\s*\{",
    flags=re.DOTALL,
)


def _looks_like_java_method_stub(code: str) -> bool:
    """
    True when `code` contains at least one Java method signature followed by
    a body -- i.e. something the candidate can actually fill in.
    """
    if not code or not code.strip():
        return False
    return bool(_JAVA_METHOD_STUB.search(code))


def _make_java_starter_stub(code: str, fallback_problem: str = "problem") -> str:
    """
    Extracts class name and method signature from `code`, stripping any implementation
    logic so that the candidate is provided only an empty starter skeleton with a default
    return value.
    """
    clean_code = re.sub(r"//[^\n]*", "", code or "")
    clean_code = re.sub(r"/\*[\s\S]*?\*/", "", clean_code)

    class_match = re.search(r"\b(?:public\s+)?class\s+([A-Za-z0-9_]+)", clean_code)
    class_name = class_match.group(1) if class_match else "Solution"

    method_regex = (
        r"\b(?:public|protected|private)?\s*(static\s+)?"
        r"([A-Za-z0-9_]+(?:<[A-Za-z0-9_,\s<>]+>)?(?:\[\s*\])*)\s+"
        r"([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*\{"
    )
    method_match = re.search(method_regex, clean_code)
    if not method_match:
        return (
            f"public class {class_name} {{\n"
            "    public int solve() {\n"
            "        // Write your code here\n"
            "        return 0;\n"
            "    }\n"
            "}"
        )

    is_static = bool(method_match.group(1))
    return_type = method_match.group(2).strip()
    method_name = method_match.group(3).strip()
    params = method_match.group(4).strip()

    sig_prefix = "public static " if is_static else "public "
    full_sig = f"{sig_prefix}{return_type} {method_name}({params})"

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
        default_ret = "        return \"\";\n"
    elif ret_clean == "int[]":
        default_ret = "        return new int[0];\n"
    elif ret_clean == "String[]":
        default_ret = "        return new String[0];\n"
    elif ret_clean.endswith("[]"):
        base = ret_clean[:-2]
        default_ret = f"        return new {base}[0];\n"
    elif "List" in ret_clean or "ArrayList" in ret_clean:
        default_ret = "        return new java.util.ArrayList<>();\n"
    elif "Map" in ret_clean or "HashMap" in ret_clean:
        default_ret = "        return new java.util.HashMap<>();\n"
    elif "Set" in ret_clean or "HashSet" in ret_clean:
        default_ret = "        return new java.util.HashSet<>();\n"
    else:
        default_ret = "        return null;\n"

    stub = (
        f"public class {class_name} {{\n"
        f"    {full_sig} {{\n"
        f"        // Write your code here\n"
        f"{default_ret}"
        f"    }}\n"
        f"}}"
    )
    return stub


def _parse_missing_number_case(input_text: str):
    normalized = re.sub(r"\b(?:int\s+)?n\s*=\s*", "", input_text or "", flags=re.IGNORECASE)
    normalized = re.sub(r"\b(?:int\s+)?arr\s*=\s*", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"new\s+int\s*\[\s*\]", "", normalized, flags=re.IGNORECASE)
    match = re.fullmatch(r"\s*(\d+)\s*,\s*[\[{]([\d,\s-]*)[\]}]\s*", normalized)
    if not match:
        return None

    n = int(match.group(1))
    values = [int(value.strip()) for value in match.group(2).split(",") if value.strip()]
    if n < 1 or len(values) != n - 1 or len(set(values)) != len(values):
        return None
    if any(value < 1 or value > n for value in values):
        return None
    missing = set(range(1, n + 1)) - set(values)
    return next(iter(missing)) if len(missing) == 1 else None


def _validate_missing_number_question(title: str, question_text: str, starter_code: str,
                                      explanation: str, test_cases: list) -> None:
    question_content = f"{title}\n{question_text}".lower()
    if "missing number" not in question_content:
        return

    for section in ("input:", "output:", "constraints:", "example:"):
        if section not in question_text.lower():
            raise ValueError(f"Missing Number question is missing its {section[:-1]} section")

    if re.search(r"\bfactorial\b|\b\d+\s*!\s*\+", f"{question_text}\n{explanation}", re.IGNORECASE):
        raise ValueError("Missing Number question contains factorial content")

    method = re.search(r"\bint\s+\w+\s*\(([^)]*)\)", starter_code)
    if not method or not re.search(r"\bint\s*\[\s*\]\s*\w+|\bint\s+\w+\s*\[\s*\]", method.group(1)):
        raise ValueError("Missing Number starter code must accept an integer array")
    if not re.search(r"\bint\s+\w+", method.group(1)):
        raise ValueError("Missing Number starter code must accept the range upper bound")

    def validate_case(input_text: str, output_text: str, label: str) -> None:
        expected = _parse_missing_number_case(input_text)
        if expected is None:
            raise ValueError(f"Could not verify Missing Number {label} input: {input_text!r}")
        try:
            actual = int(str(output_text).strip())
        except ValueError as error:
            raise ValueError(f"Missing Number {label} output must be the missing integer") from error
        if actual != expected:
            raise ValueError(
                f"Missing Number {label} output is inconsistent: expected {expected}, got {actual}"
            )

    if len(test_cases) != 4:
        raise ValueError("Missing Number question must provide exactly four test cases")
    for index, case in enumerate(test_cases, start=1):
        validate_case(case["input"], case["expectedOutput"], f"test case {index}")

    example_section = re.search(r"(?is)example\s*:\s*(.*)$", question_text)
    if not example_section:
        raise ValueError("Missing Number question is missing its worked example")
    example_input = re.search(r"(?im)^\s*Input\s*:\s*(.+)$", example_section.group(1))
    example_output = re.search(r"(?im)^\s*Output\s*:\s*(.+)$", example_section.group(1))
    if not example_input or not example_output:
        raise ValueError("Missing Number example must include Input and Output lines")
    validate_case(example_input.group(1), example_output.group(1), "worked example")


_CODE_WRITING_PATTERNS = re.compile(
    r"\b(write|implement|create|design|code)\b[^.?!]{0,40}\b"
    r"(a |an |the )?(method|function|class|program|algorithm|code)\b",
    flags=re.IGNORECASE,
)


def _looks_like_code_writing_task(question_text: str) -> bool:
    """
    Cheap guard against LLaMA ignoring the "theory questions only, no
    implementation tasks" instruction. Catches phrasings like "Write
    a method that...", "Implement a function to...".
    """
    if not question_text:
        return False
    return bool(_CODE_WRITING_PATTERNS.search(question_text))


_DIFFICULTY_GUIDANCE = {
    "easy": (
        "EASY means suitable for someone in their first few months of learning this subject: "
        "a basic definition, a simple syntax rule, or a plain 'what is X and what is it used "
        "for' question. No internal mechanisms (memory model, concurrency guarantees, JVM/DB "
        "engine internals), no obscure edge cases, no multi-step reasoning. Someone who just "
        "read an introductory chapter on this exact topic should be able to answer confidently "
        "in 2-3 sentences."
    ),
    "medium": (
        "MEDIUM means suitable for someone with solid working knowledge: a comparison between "
        "two related things, a common trade-off, a typical usage nuance, or a 'when would you "
        "use X vs Y' question. Some depth is fine, but avoid internals-level detail or "
        "specialized edge cases -- that belongs at HARD, not here.\n"
        "The topic itself must be one of the FAMILIAR, frequently-asked interview staples for "
        "this subject -- NOT a rare internals topic unless asked in the plain, commonly-seen "
        "form. Ask ONE clear, self-contained idea -- do not stack two questions into one."
    ),
    "hard": (
        "HARD means suitable for an experienced engineer: internal mechanisms (memory model, "
        "concurrency guarantees, runtime/engine internals), subtle edge cases, or something "
        "requiring multi-step reasoning and awareness of less-common pitfalls."
    ),
}


def _difficulty_guidance(difficulty: str) -> str:
    """
    Concrete calibration anchor for what each difficulty label should
    actually mean in terms of question depth.
    """
    return _DIFFICULTY_GUIDANCE.get((difficulty or "medium").lower(), _DIFFICULTY_GUIDANCE["medium"])


def _looks_like_keyword_dump(answer: str, concepts: list) -> bool:
    """
    Anti-gaming heuristic for the offline grader: strip the expected
    concept phrases out of the answer and see what's left. A real
    explanation still has substance after that; a bare list of the concept
    names/terms has almost nothing left.
    """
    text = answer.lower()
    for c in (concepts or []):
        text = text.replace(c.lower(), " ")
    remaining_words = [w for w in re.findall(r"[a-zA-Z]+", text) if len(w) > 2]
    has_sentence_structure = any(p in answer for p in ".!?,")
    return len(remaining_words) < 6 and not has_sentence_structure


# ---------------------------------------------------------------------------
# "Bare term list" gate (Java theory, DBMS theory and HR)
#
# A candidate can try to game a meaning-based grader by writing only technical
# (or generic HR) buzzwords: "class, interface, abstract, polymorphism". That is
# not an explanation and must not earn credit just because the terms are on
# topic. A genuine answer -- even a terse one -- contains some connecting
# language (is/are/can/allows/because/I/we/that/of/to ...). A run of 3+ words
# with NONE of that connecting language is a bare list of terms.
#
# The cue list intentionally leaves out words that are themselves Java/SQL
# keywords or common topic nouns (for/while/if/in/from/where/by/return/this/
# create/work/support ...), so a keyword list can't slip past by containing one.
# It is a heuristic safety net for the obvious case; subtler keyword stuffing is
# handled by the LLM's meaning-based judgement and the semantic checks.
# ---------------------------------------------------------------------------
# Words that show a real clause is being written (not just terms): auxiliaries,
# pronouns and connectives ...
_STRONG_CUE_WORDS = frozenset("""
    is are was were be been being am has have had can could will would should may might must does did
    it its they them their he she his her we you i my our your that which because since than how why
    what who whom whose also such to of so but nor yet whereas whether either neither
    via through within without across during against among upon
    made gave led took ran saw got found held kept told said thought felt knew began became
""".split())
# Verbs matched by their -s / -ed forms ("reduces", "stored"). Words that are ALSO common
# database/Java terms are left out on purpose (join, index, order, group, lock, process, set,
# read, write, update, delete, insert, commit, rollback, call, run, return, create, select ...),
# because a keyword list would contain them.
_CUE_VERB_BASES = frozenset("""
    allow enable let help make give provide ensure support happen occur work refer describe represent
    contain reuse use hide inherit acquire follow handle solve resolve learn decide talk speak ask
    believe identify reduce guarantee combine split avoid prevent improve speed store keep hold define
    execute perform apply manage maintain organize organise connect remove eliminate break depend
    include consist specify require cause lead show mean need want try start stop change add check
    compare protect share separate bind point access send receive restrict limit validate wrap expose
    isolate save find retrieve calculate compute evaluate build design behave act respond take put get
    become remain relate belong cover affect simplify increase decrease enhance boost arrange explain
    discuss collaborate coordinate communicate listen understand plan prioritize delegate mentor
    motivate free release clean speedup verify enforce maintain reference match merge repeat
""".split())
# Verbs that are safe to treat as a clause even in their bare form ("Interfaces support
# multiple inheritance"): they are essentially never a topic noun on their own.
_SAFE_BARE_VERBS = frozenset("""
    allow enable help provide ensure support simplify execute reduce improve avoid prevent increase
    decrease represent describe contain define belong happen occur free hide explain verify enforce
    protect isolate expose restrict validate eliminate maintain
""".split())
_WEAK_CUE_WORDS = frozenset("a an the each every some these those there".split())
_IRREGULAR_SKIP = frozenset({"extends", "implements", "selects", "creates"})


def _word_is_verb_form(word: str) -> bool:
    w = word.lower()
    if w in _IRREGULAR_SKIP:
        return False
    if w in _SAFE_BARE_VERBS:
        return True
    candidates = []
    if w.endswith("ies") and len(w) > 4:
        candidates.append(w[:-3] + "y")
    if w.endswith("es") and len(w) > 3:
        candidates.append(w[:-2])
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        candidates.append(w[:-1])
    if w.endswith("ied") and len(w) > 4:
        candidates.append(w[:-3] + "y")
    if w.endswith("ed") and len(w) > 3:
        candidates.extend([w[:-2], w[:-1], w[:-3]])  # worked, used, stopped
    return any(c in _CUE_VERB_BASES for c in candidates)


def _has_strong_cue(words) -> bool:
    return any(w.lower() in _STRONG_CUE_WORDS or _word_is_verb_form(w) for w in words)


# Questions that ask the candidate to name/list things: a list of terms can be a
# CORRECT answer to these (e.g. "What are the ACID properties?"), so the bare
# list gate must not zero it -- the normal meaning-based grading decides.
_LIST_QUESTION = re.compile(
    r"\b(?:list|name|enumerate|identify|state|mention|stand for|"
    r"what (?:are|were) (?:the |your |some )?(?:\w+\s+){0,3}?"
    r"(?:types|kinds|properties|pillars|principles|features|advantages|disadvantages|benefits|"
    r"components|levels|forms|categories|keywords|methods|ways|steps|phases|stages|"
    r"characteristics|strengths|weaknesses|values|skills|goals|qualities)|"
    r"which (?:\w+\s+){0,3}?(?:are|keywords?))\b",
    re.IGNORECASE,
)


def _is_bare_term_list(answer: str) -> bool:
    """
    True only for the two clear "keywords, not an answer" shapes:

      1. a delimited list -- 3+ comma/semicolon/line separated items, each only
         1-3 words, with no clause-building word anywhere
         ("class, interface, abstract, polymorphism");
      2. a run of 4+ plain words with no connecting word at all
         ("class interface abstract polymorphism").

    Anything with code punctuation, a definition marker (":" / "-" / "="), a
    sentence ending, or any verb/auxiliary/pronoun/connective is treated as real
    writing and left to the meaning-based grader.
    """
    text = (answer or "").strip()
    if not text:
        return False
    if re.search(r"[{}()=<>:]", text) or re.search(r"\s-\s", text):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    if len(words) < 3 or _has_strong_cue(words):
        return False

    items = [item.strip() for item in re.split(r"[,;\n\u2022|]+", text) if item.strip()]
    if len(items) >= 3 and all(len(re.findall(r"[A-Za-z][A-Za-z'-]*", item)) <= 3 for item in items):
        return True  # shape 1

    if len(words) >= 4 and not re.search(r"[.!?]", text) and not any(w.lower() in _WEAK_CUE_WORDS for w in words):
        return True  # shape 2
    return False


def _question_asks_for_list(question: str) -> bool:
    return bool(_LIST_QUESTION.search(question or ""))


def _should_reject_term_list(question: str, answer: str) -> bool:
    return _is_bare_term_list(answer) and not _question_asks_for_list(question)


def _keyword_list_evaluation(concepts: list) -> dict:
    """Java/DBMS theory: a bare list of terms shows no understanding -> 0."""
    reason = (
        "The answer is only a list of terms. It doesn't explain anything or answer the "
        "question, so it doesn't demonstrate understanding."
    )
    return {
        "score": 0,
        "conceptCoverage": 0.0,
        "correctness": 0.0,
        "relevance": 0.0,
        "communication": 0.0,
        "isIrrelevant": False,
        "feedback": reason,
        "strengths": [],
        "weaknesses": ["Answer is a list of terms, not an explanation"],
        "coveredConcepts": [],
        "partiallyCoveredConcepts": [],
        "missingConcepts": list(concepts or []),
        "deeperConcepts": [],
        "improvementSuggestion": (
            "Explain what the key concepts mean and how they answer the question "
            "instead of listing terms."
        ),
        "scoreReason": reason,
        "modelUsed": "fallback_rules",
        "usedFallback": True,
        "scoringSources": ["rules"],
    }


_HR_NOT_RELATED_MESSAGE = "Not related to the question."


def _not_related_hr_evaluation() -> dict:
    """HR: the answer doesn't address the question at all."""
    return {
        "score": 0,
        "conceptCoverage": 0.0,
        "correctness": 0.0,
        "relevance": 0.0,
        "accuracy": 0.0,
        "communication": 0.0,
        "isIrrelevant": True,
        "feedback": _HR_NOT_RELATED_MESSAGE,
        "strengths": [],
        "weaknesses": [],
        "coveredConcepts": [],
        "partiallyCoveredConcepts": [],
        "missingConcepts": [],
        "deeperConcepts": [],
        "improvementSuggestion": "Answer the question that was asked, using a specific example from your experience.",
        "scoreReason": _HR_NOT_RELATED_MESSAGE,
        "modelUsed": "fallback_rules",
        "usedFallback": True,
        "scoringSources": ["rules"],
    }


def _as_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in ("true", "yes", "1"):
        return True
    if text in ("false", "no", "0"):
        return False
    return default


def _canonical_output(text: str) -> str:
    """
    Predict-the-output comparison form. Exact match only: the one allowance is
    line-ending style and leading/trailing whitespace (a stray trailing newline
    isn't program output). Case, digits, punctuation and inner spacing all count.
    """
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _is_fragmentary_answer(answer: str) -> bool:
    words = re.findall(r"\b[\w']+\b", (answer or "").lower())
    if not 3 <= len(words) <= 8:
        return False
    explanatory_verbs = (
        "am", "are", "be", "become", "can", "causes", "defines", "does", "enables",
        "ensures", "explains", "happens", "has", "is", "means", "occurs", "provides",
        "represents", "supports", "uses", "was", "were", "works",
    )
    return not any(word in explanatory_verbs for word in words)


# Pre-verified guaranteed-unique coding catalogs to ensure 100% crash resilience
# across multi-question interview sessions even if LLM generation is exhausted.
_GUARANTEED_UNIQUE_CODING_QUESTIONS = {
    ("java", "easy"): [
        {
            "title": "Reverse a Given String",
            "questionText": "Write a Java method to reverse a given string without using built-in reverse functions.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "easy",
            "category": "Java Strings",
            "expectedConcepts": ["String traversal", "Character swapping or StringBuilder", "Edge case handling"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "public class Solution {\n    public static String reverseString(String s) {\n        // Your code here\n        return \"\";\n    }\n}",
            "testCases": [
                {"input": "\"hello\"", "expectedOutput": "\"olleh\"", "label": "Basic reverse"},
                {"input": "\"java\"", "expectedOutput": "\"avaj\"", "label": "Four letter word"},
                {"input": "\"\"", "expectedOutput": "\"\"", "label": "Empty string"}
            ],
            "explanation": "Traverse the string from the end to the beginning or swap characters using a two-pointer approach.",
            "referenceSolution": "public class Solution {\n    public static String reverseString(String s) {\n        if (s == null) return null;\n        return new StringBuilder(s).reverse().toString();\n    }\n}"
        },
        {
            "title": "Check Palindrome String",
            "questionText": "Write a Java method that checks whether a given string is a palindrome (reads the same forwards and backwards).",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "easy",
            "category": "Java Strings",
            "expectedConcepts": ["Two-pointer technique", "String indexing", "Case sensitivity check"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "public class Solution {\n    public static boolean isPalindrome(String s) {\n        // Your code here\n        return false;\n    }\n}",
            "testCases": [
                {"input": "\"racecar\"", "expectedOutput": "true", "label": "Odd length palindrome"},
                {"input": "\"noon\"", "expectedOutput": "true", "label": "Even length palindrome"},
                {"input": "\"hello\"", "expectedOutput": "false", "label": "Non palindrome"}
            ],
            "explanation": "Compare characters at left and right pointers moving towards the center.",
            "referenceSolution": "public class Solution {\n    public static boolean isPalindrome(String s) {\n        if (s == null) return false;\n        int l = 0, r = s.length() - 1;\n        while (l < r) {\n            if (s.charAt(l++) != s.charAt(r--)) return false;\n        }\n        return true;\n    }\n}"
        },
        {
            "title": "Find Maximum Element in an Array",
            "questionText": "Write a Java method to find and return the maximum element in a non-empty array of integers.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "easy",
            "category": "Java Arrays",
            "expectedConcepts": ["Array traversal", "Linear scan", "Variable tracking"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "public class Solution {\n    public static int findMax(int[] nums) {\n        // Your code here\n        return 0;\n    }\n}",
            "testCases": [
                {"input": "[3, 7, 2, 9, 5]", "expectedOutput": "9", "label": "Positive numbers"},
                {"input": "[-5, -12, -3, -1]", "expectedOutput": "-1", "label": "Negative numbers"},
                {"input": "[42]", "expectedOutput": "42", "label": "Single element array"}
            ],
            "explanation": "Initialize max with the first element and update it whenever a larger number is encountered.",
            "referenceSolution": "public class Solution {\n    public static int findMax(int[] nums) {\n        int max = nums[0];\n        for (int n : nums) if (n > max) max = n;\n        return max;\n    }\n}"
        },
        {
            "title": "Count Vowels in String",
            "questionText": "Write a Java method that counts and returns the number of vowels (a, e, i, o, u, case-insensitive) in a string.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "easy",
            "category": "Java Strings",
            "expectedConcepts": ["Character inspection", "Case normalization", "Counter variable"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "public class Solution {\n    public static int countVowels(String s) {\n        // Your code here\n        return 0;\n    }\n}",
            "testCases": [
                {"input": "\"MockMate\"", "expectedOutput": "3", "label": "Standard word"},
                {"input": "\"rhythm\"", "expectedOutput": "0", "label": "No vowels"},
                {"input": "\"AEIOU\"", "expectedOutput": "5", "label": "Uppercase vowels"}
            ],
            "explanation": "Iterate through the string, check if each character belongs to the set of vowels, and increment a counter.",
            "referenceSolution": "public class Solution {\n    public static int countVowels(String s) {\n        int count = 0;\n        String v = \"aeiouAEIOU\";\n        for (char c : s.toCharArray()) if (v.indexOf(c) != -1) count++;\n        return count;\n    }\n}"
        },
        {
            "title": "Sum of Digits",
            "questionText": "Write a Java method that calculates the sum of all digits of a given non-negative integer.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "easy",
            "category": "Java Math",
            "expectedConcepts": ["Modulo arithmetic", "Integer division", "Loop control"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "public class Solution {\n    public static int sumDigits(int n) {\n        // Your code here\n        return 0;\n    }\n}",
            "testCases": [
                {"input": "1234", "expectedOutput": "10", "label": "Multi-digit number"},
                {"input": "90", "expectedOutput": "9", "label": "Number with zero"},
                {"input": "7", "expectedOutput": "7", "label": "Single digit"}
            ],
            "explanation": "Extract the last digit using n % 10, add to sum, and divide n by 10 repeatedly until n reaches 0.",
            "referenceSolution": "public class Solution {\n    public static int sumDigits(int n) {\n        int sum = 0;\n        while (n > 0) { sum += n % 10; n /= 10; }\n        return sum;\n    }\n}"
        }
    ],
    ("java", "medium"): [
        {
            "title": "Two Sum Problem",
            "questionText": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "medium",
            "category": "Java Arrays & Hashing",
            "expectedConcepts": ["HashMap lookup", "O(N) time complexity", "One-pass algorithm"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "import java.util.HashMap;\n\npublic class Solution {\n    public static int[] twoSum(int[] nums, int target) {\n        // Your code here\n        return new int[]{};\n    }\n}",
            "testCases": [
                {"input": "[2, 7, 11, 15], 9", "expectedOutput": "[0, 1]", "label": "Early match"},
                {"input": "[3, 2, 4], 6", "expectedOutput": "[1, 2]", "label": "Non-first match"},
                {"input": "[3, 3], 6", "expectedOutput": "[0, 1]", "label": "Duplicate numbers"}
            ],
            "explanation": "Store complement target - num in a HashMap while iterating through the array to achieve O(N) complexity.",
            "referenceSolution": "import java.util.HashMap;\n\npublic class Solution {\n    public static int[] twoSum(int[] nums, int target) {\n        HashMap<Integer, Integer> map = new HashMap<>();\n        for (int i = 0; i < nums.length; i++) {\n            int comp = target - nums[i];\n            if (map.containsKey(comp)) return new int[]{map.get(comp), i};\n            map.put(nums[i], i);\n        }\n        return new int[]{};\n    }\n}"
        },
        {
            "title": "Valid Parentheses Matcher",
            "questionText": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string has valid balanced brackets.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "medium",
            "category": "Java Stack & Strings",
            "expectedConcepts": ["Stack data structure", "LIFO matching", "Edge case boundary handling"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "import java.util.Stack;\n\npublic class Solution {\n    public static boolean isValid(String s) {\n        // Your code here\n        return false;\n    }\n}",
            "testCases": [
                {"input": "\"()[]{}\"", "expectedOutput": "true", "label": "Multiple pairs"},
                {"input": "\"(]\"", "expectedOutput": "false", "label": "Mismatched closing"},
                {"input": "\"{[]}\"", "expectedOutput": "true", "label": "Nested brackets"}
            ],
            "explanation": "Push opening brackets onto a stack and verify that each closing bracket matches the top of the stack.",
            "referenceSolution": "import java.util.Stack;\n\npublic class Solution {\n    public static boolean isValid(String s) {\n        Stack<Character> stack = new Stack<>();\n        for (char c : s.toCharArray()) {\n            if (c == '(') stack.push(')');\n            else if (c == '{') stack.push('}');\n            else if (c == '[') stack.push(']');\n            else if (stack.isEmpty() || stack.pop() != c) return false;\n        }\n        return stack.isEmpty();\n    }\n}"
        },
        {
            "title": "Longest Substring Without Repeating Characters",
            "questionText": "Given a string s, find the length of the longest substring without duplicate characters.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "medium",
            "category": "Java Sliding Window",
            "expectedConcepts": ["Sliding window", "HashSet or HashMap index tracking", "Two pointers"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "import java.util.HashSet;\n\npublic class Solution {\n    public static int lengthOfLongestSubstring(String s) {\n        // Your code here\n        return 0;\n    }\n}",
            "testCases": [
                {"input": "\"abcabcbb\"", "expectedOutput": "3", "label": "Repeating letters"},
                {"input": "\"bbbbb\"", "expectedOutput": "1", "label": "All identical characters"},
                {"input": "\"pwwkew\"", "expectedOutput": "3", "label": "Subsequence vs substring"}
            ],
            "explanation": "Maintain a sliding window [left, right] using a HashSet to dynamically record character frequencies.",
            "referenceSolution": "import java.util.HashSet;\n\npublic class Solution {\n    public static int lengthOfLongestSubstring(String s) {\n        HashSet<Character> set = new HashSet<>();\n        int max = 0, l = 0;\n        for (int r = 0; r < s.length(); r++) {\n            while (set.contains(s.charAt(r))) { set.remove(s.charAt(l++)); }\n            set.add(s.charAt(r));\n            max = Math.max(max, r - l + 1);\n        }\n        return max;\n    }\n}"
        },
        {
            "title": "Product of Array Except Self",
            "questionText": "Given an integer array nums, return an array answer such that answer[i] is equal to the product of all elements of nums except nums[i], without using division.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "medium",
            "category": "Java Arrays",
            "expectedConcepts": ["Prefix products", "Suffix products", "O(N) linear time"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "public class Solution {\n    public static int[] productExceptSelf(int[] nums) {\n        // Your code here\n        return new int[]{};\n    }\n}",
            "testCases": [
                {"input": "[1, 2, 3, 4]", "expectedOutput": "[24, 12, 8, 6]", "label": "Positive numbers"},
                {"input": "[-1, 1, 0, -3, 3]", "expectedOutput": "[0, 0, 9, 0, 0]", "label": "Array with zero"}
            ],
            "explanation": "Construct prefix products in the first pass, then multiply suffix products in the reverse pass.",
            "referenceSolution": "public class Solution {\n    public static int[] productExceptSelf(int[] nums) {\n        int n = nums.length;\n        int[] res = new int[n];\n        res[0] = 1;\n        for (int i = 1; i < n; i++) res[i] = res[i - 1] * nums[i - 1];\n        int right = 1;\n        for (int i = n - 1; i >= 0; i--) {\n            res[i] *= right;\n            right *= nums[i];\n        }\n        return res;\n    }\n}"
        },
        {
            "title": "Rotate Array by K Steps",
            "questionText": "Given an array of integers nums, rotate the array to the right by k steps, where k is non-negative.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "medium",
            "category": "Java Arrays",
            "expectedConcepts": ["In-place rotation", "Reversal algorithm", "Modulo k wrapping"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "public class Solution {\n    public static int[] rotate(int[] nums, int k) {\n        // Your code here\n        return new int[]{};\n    }\n}",
            "testCases": [
                {"input": "[1, 2, 3, 4, 5, 6, 7], 3", "expectedOutput": "[5, 6, 7, 1, 2, 3, 4]", "label": "Standard rotation"},
                {"input": "[-1, -100, 3, 99], 2", "expectedOutput": "[3, 99, -1, -100]", "label": "Four element array"}
            ],
            "explanation": "Reverse the whole array, then reverse the first k elements, and finally reverse the remaining elements.",
            "referenceSolution": "public class Solution {\n    public static int[] rotate(int[] nums, int k) {\n        if (nums == null || nums.length == 0) return nums;\n        int n = nums.length;\n        k = k % n;\n        int[] res = new int[n];\n        for (int i = 0; i < n; i++) res[(i + k) % n] = nums[i];\n        return res;\n    }\n}"
        }
    ],
    ("java", "hard"): [
        {
            "title": "Trapping Rain Water",
            "questionText": "Given n non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "hard",
            "category": "Java Two Pointers & DP",
            "expectedConcepts": ["Two pointer technique", "Boundary tracking", "O(1) space optimization"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "public class Solution {\n    public static int trap(int[] height) {\n        // Your code here\n        return 0;\n    }\n}",
            "testCases": [
                {"input": "[0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]", "expectedOutput": "6", "label": "Complex terrain"},
                {"input": "[4, 2, 0, 3, 2, 5]", "expectedOutput": "9", "label": "Deep basin"}
            ],
            "explanation": "Use two pointers moving inwards while tracking maxLeft and maxRight to compute trapped units.",
            "referenceSolution": "public class Solution {\n    public static int trap(int[] height) {\n        if (height == null || height.length == 0) return 0;\n        int l = 0, r = height.length - 1;\n        int maxL = 0, maxR = 0, water = 0;\n        while (l < r) {\n            if (height[l] < height[r]) {\n                if (height[l] >= maxL) maxL = height[l];\n                else water += maxL - height[l];\n                l++;\n            } else {\n                if (height[r] >= maxR) maxR = height[r];\n                else water += maxR - height[r];\n                r--;\n            }\n        }\n        return water;\n    }\n}"
        },
        {
            "title": "Sliding Window Maximum",
            "questionText": "Given an integer array nums and a sliding window size k, return the max sliding window values as the window moves from left to right.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "hard",
            "category": "Java Monotonic Deque",
            "expectedConcepts": ["Monotonic deque", "Window bounds maintenance", "O(N) time complexity"],
            "questionFormat": "coding",
            "language": "java",
            "starterCode": "import java.util.ArrayDeque;\nimport java.util.Deque;\n\npublic class Solution {\n    public static int[] maxSlidingWindow(int[] nums, int k) {\n        // Your code here\n        return new int[]{};\n    }\n}",
            "testCases": [
                {"input": "[1, 3, -1, -3, 5, 3, 6, 7], 3", "expectedOutput": "[3, 3, 5, 5, 6, 7]", "label": "Standard sliding window"},
                {"input": "[1], 1", "expectedOutput": "[1]", "label": "Single element"}
            ],
            "explanation": "Maintain indices in a monotonic double-ended queue storing elements in decreasing order.",
            "referenceSolution": "import java.util.ArrayDeque;\nimport java.util.Deque;\n\npublic class Solution {\n    public static int[] maxSlidingWindow(int[] nums, int k) {\n        if (nums == null || k <= 0) return new int[0];\n        int n = nums.length;\n        int[] res = new int[n - k + 1];\n        int ri = 0;\n        Deque<Integer> q = new ArrayDeque<>();\n        for (int i = 0; i < nums.length; i++) {\n            while (!q.isEmpty() && q.peek() < i - k + 1) q.poll();\n            while (!q.isEmpty() && nums[q.peekLast()] < nums[i]) q.pollLast();\n            q.offer(i);\n            if (i >= k - 1) res[ri++] = nums[q.peek()];\n        }\n        return res;\n    }\n}"
        }
    ],
    ("dbms", "easy"): [
        {
            "title": "SQL: list orders with status completed placed after a specific date",
            "questionText": "Given the database schema provided, write a SQL query to solve the following problem: list orders with status completed placed after a specific date.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "easy",
            "category": "SQL Query Writing",
            "expectedConcepts": ["SELECT clause", "WHERE filter", "Date comparison", "String comparison"],
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE orders (order_id INT PRIMARY KEY, customer_id INT, order_date DATE, status VARCHAR(20));",
            "sampleData": "INSERT INTO orders VALUES (1, 101, '2024-02-15', 'completed'), (2, 102, '2023-11-20', 'completed'), (3, 103, '2024-05-10', 'pending'), (4, 104, '2024-03-01', 'completed');",
            "starterCode": "-- Write your SQL query here\n",
            "testCases": [
                {"input": "Standard dataset evaluation", "expectedOutput": "1 | 101 | 2024-02-15 | completed\n4 | 104 | 2024-03-01 | completed", "label": "Standard dataset evaluation"},
                {"input": "Boundary condition dataset", "expectedOutput": "Empty result set", "label": "Filter verification"}
            ],
            "explanation": "Use WHERE status = 'completed' AND order_date > '2024-01-01'.",
            "referenceSolution": "SELECT *\nFROM orders\nWHERE status = 'completed'\n  AND order_date > '2024-01-01';",
            "_referenceQuery": "SELECT *\nFROM orders\nWHERE status = 'completed'\n  AND order_date > '2024-01-01';"
        },
        {
            "title": "Filter High Salary Employees",
            "questionText": "Write a SQL query to select the first_name, last_name, and salary of all employees earning more than 60000, ordered by salary descending.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "easy",
            "category": "SQL Filtering & Sorting",
            "expectedConcepts": ["SELECT clause", "WHERE filter", "ORDER BY DESC"],
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE employees (id INT PRIMARY KEY, first_name VARCHAR(50), last_name VARCHAR(50), salary INT, department_id INT);",
            "sampleData": "INSERT INTO employees VALUES (1, 'Alice', 'Smith', 75000, 1), (2, 'Bob', 'Jones', 50000, 2), (3, 'Charlie', 'Brown', 62000, 1);",
            "starterCode": "-- Write your SQL query here\nSELECT first_name, last_name, salary\nFROM employees\n",
            "testCases": [
                {"input": "employees table with varied salaries", "expectedOutput": "Alice Smith 75000, Charlie Brown 62000", "label": "Standard salary filter"},
                {"input": "employees table where nobody earns > 60000", "expectedOutput": "Empty result set", "label": "Boundary condition"}
            ],
            "explanation": "Use WHERE salary > 60000 ORDER BY salary DESC.",
            "referenceSolution": "SELECT first_name, last_name, salary FROM employees WHERE salary > 60000 ORDER BY salary DESC;",
            "_referenceQuery": "SELECT first_name, last_name, salary FROM employees WHERE salary > 60000 ORDER BY salary DESC;"
        },
        {
            "title": "Count Active Customers in City",
            "questionText": "Write a SQL query to count the total number of active customers residing in the city 'Chicago'.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "easy",
            "category": "SQL Aggregation",
            "expectedConcepts": ["COUNT aggregate", "WHERE multi-condition", "String matching"],
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE customers (id INT PRIMARY KEY, name VARCHAR(100), city VARCHAR(50), is_active BOOLEAN);",
            "sampleData": "INSERT INTO customers VALUES (1, 'John', 'Chicago', true), (2, 'Jane', 'Chicago', false), (3, 'Dave', 'Chicago', true);",
            "starterCode": "-- Write your SQL query here\n",
            "testCases": [
                {"input": "Standard customers dataset", "expectedOutput": "2", "label": "Active Chicago count"},
                {"input": "No customers in Chicago", "expectedOutput": "0", "label": "Empty city match"}
            ],
            "explanation": "Use SELECT COUNT(*) FROM customers WHERE city = 'Chicago' AND is_active = true.",
            "referenceSolution": "SELECT COUNT(*) FROM customers WHERE city = 'Chicago' AND is_active = true;",
            "_referenceQuery": "SELECT COUNT(*) FROM customers WHERE city = 'Chicago' AND is_active = true;"
        },
        {
            "title": "Select Distinct Department Titles",
            "questionText": "Write a SQL query to return all distinct job titles currently assigned to employees, sorted alphabetically.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "easy",
            "category": "SQL Distinct Selection",
            "expectedConcepts": ["DISTINCT keyword", "ORDER BY sorting"],
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE employees (id INT PRIMARY KEY, name VARCHAR(100), job_title VARCHAR(100));",
            "sampleData": "INSERT INTO employees VALUES (1, 'Alice', 'Engineer'), (2, 'Bob', 'Engineer'), (3, 'Charlie', 'Manager');",
            "starterCode": "-- Write your SQL query here\n",
            "testCases": [
                {"input": "Duplicate job titles in table", "expectedOutput": "Engineer, Manager", "label": "Deduplicated titles"},
                {"input": "Single employee table", "expectedOutput": "Manager", "label": "Single row"}
            ],
            "explanation": "Use SELECT DISTINCT job_title FROM employees ORDER BY job_title ASC.",
            "referenceSolution": "SELECT DISTINCT job_title FROM employees ORDER BY job_title ASC;",
            "_referenceQuery": "SELECT DISTINCT job_title FROM employees ORDER BY job_title ASC;"
        }
    ],
    ("dbms", "medium"): [
        {
            "title": "Department Average Salary with Name",
            "questionText": "Write a SQL query to return each department's name along with the average salary of its employees, rounded to 2 decimal places. Only include departments with at least 2 employees.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "medium",
            "category": "SQL JOIN & Aggregation",
            "expectedConcepts": ["INNER JOIN", "GROUP BY", "HAVING clause", "AVG aggregate"],
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE departments (id INT PRIMARY KEY, name VARCHAR(50));\nCREATE TABLE employees (id INT PRIMARY KEY, name VARCHAR(50), salary DECIMAL(10,2), department_id INT);",
            "sampleData": "INSERT INTO departments VALUES (1, 'IT'), (2, 'HR');\nINSERT INTO employees VALUES (1, 'Alice', 80000, 1), (2, 'Bob', 90000, 1), (3, 'Charlie', 50000, 2);",
            "starterCode": "-- Write your SQL query here\n",
            "testCases": [
                {"input": "IT has 2 staff, HR has 1 staff", "expectedOutput": "IT 85000.00", "label": "Department average filtered by staff count"},
                {"input": "All departments have >= 2 staff", "expectedOutput": "IT 85000.00, HR 55000.00", "label": "Multiple departments match"}
            ],
            "explanation": "Join departments with employees, group by department name, and filter with HAVING COUNT(e.id) >= 2.",
            "_referenceQuery": "SELECT d.name, ROUND(AVG(e.salary), 2) AS avg_salary FROM departments d JOIN employees e ON d.id = e.department_id GROUP BY d.name HAVING COUNT(e.id) >= 2;"
        },
        {
            "title": "Second Highest Salary in Company",
            "questionText": "Write a SQL query to find the second highest salary among all employees. If there is no second highest salary, return NULL.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "medium",
            "category": "SQL Subqueries & Offsets",
            "expectedConcepts": ["Subquery or LIMIT OFFSET", "MAX aggregate", "Handling NULL edge cases"],
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE employees (id INT PRIMARY KEY, salary INT);",
            "sampleData": "INSERT INTO employees VALUES (1, 100), (2, 200), (3, 300);",
            "starterCode": "-- Write your SQL query here\n",
            "testCases": [
                {"input": "Salaries 100, 200, 300", "expectedOutput": "200", "label": "Second highest found"},
                {"input": "Single employee with 100", "expectedOutput": "NULL", "label": "Single salary NULL result"}
            ],
            "explanation": "Use SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees).",
            "_referenceQuery": "SELECT MAX(salary) AS SecondHighestSalary FROM employees WHERE salary < (SELECT MAX(salary) FROM employees);"
        },
        {
            "title": "Customers with No Placed Orders",
            "questionText": "Write a SQL query to find all customers who have never placed an order.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "medium",
            "category": "SQL Outer Joins",
            "expectedConcepts": ["LEFT JOIN", "IS NULL filter", "Relational anti-join"],
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE customers (id INT PRIMARY KEY, name VARCHAR(50));\nCREATE TABLE orders (id INT PRIMARY KEY, customer_id INT, amount DECIMAL(10,2));",
            "sampleData": "INSERT INTO customers VALUES (1, 'Joe'), (2, 'Henry'), (3, 'Sam');\nINSERT INTO orders VALUES (1, 1, 100.00), (2, 3, 250.00);",
            "starterCode": "-- Write your SQL query here\n",
            "testCases": [
                {"input": "Henry has no orders", "expectedOutput": "Henry", "label": "Customer without orders"},
                {"input": "All customers have orders", "expectedOutput": "Empty result", "label": "No orphan customers"}
            ],
            "explanation": "Perform a LEFT JOIN between customers and orders and filter WHERE orders.customer_id IS NULL.",
            "_referenceQuery": "SELECT c.name FROM customers c LEFT JOIN orders o ON c.id = o.customer_id WHERE o.customer_id IS NULL;"
        }
    ],
    ("dbms", "hard"): [
        {
            "title": "Top 3 Highest Earners Per Department",
            "questionText": "Write a SQL query to find the employees who earn the top 3 highest salaries within their respective department using window functions.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "hard",
            "category": "SQL Window Functions",
            "expectedConcepts": ["DENSE_RANK()", "PARTITION BY", "Common Table Expressions (CTE)"],
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE departments (id INT PRIMARY KEY, name VARCHAR(50));\nCREATE TABLE employees (id INT PRIMARY KEY, name VARCHAR(50), salary INT, department_id INT);",
            "sampleData": "INSERT INTO departments VALUES (1, 'IT'), (2, 'Sales');\nINSERT INTO employees VALUES (1, 'Joe', 85000, 1), (2, 'Henry', 80000, 2), (3, 'Sam', 60000, 2), (4, 'Max', 90000, 1), (5, 'Janet', 69000, 1), (6, 'Randy', 85000, 1);",
            "starterCode": "-- Write your SQL query here\n",
            "testCases": [
                {"input": "Departments with multiple salary tiers", "expectedOutput": "Top 3 ranked employees per department", "label": "Window ranking evaluation"},
                {"input": "Single employee per department", "expectedOutput": "Single employee returned per department", "label": "Single row partitions"}
            ],
            "explanation": "Use DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) in a CTE or subquery, then filter rank <= 3.",
            "_referenceQuery": "WITH ranked AS (SELECT d.name AS Department, e.name AS Employee, e.salary, DENSE_RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS rnk FROM employees e JOIN departments d ON e.department_id = d.id) SELECT Department, Employee, salary FROM ranked WHERE rnk <= 3;"
        },
        {
            "title": "Employees Earning More Than Their Direct Manager",
            "questionText": "Write a SQL query to find employees who earn more than their direct managers using a self-join.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "hard",
            "category": "SQL Self-Joins",
            "expectedConcepts": ["Self JOIN", "Hierarchical comparison", "Alias disambiguation"],
            "questionFormat": "coding",
            "language": "sql",
            "schema": "CREATE TABLE employees (id INT PRIMARY KEY, name VARCHAR(50), salary INT, manager_id INT);",
            "sampleData": "INSERT INTO employees VALUES (1, 'Joe', 70000, 3), (2, 'Henry', 80000, 4), (3, 'Sam', 60000, NULL), (4, 'Max', 90000, NULL);",
            "starterCode": "-- Write your SQL query here\n",
            "testCases": [
                {"input": "Joe earns 70k with manager Sam earning 60k", "expectedOutput": "Joe", "label": "Direct manager comparison"},
                {"input": "All employees earn less than managers", "expectedOutput": "Empty result", "label": "No employees exceed manager salary"}
            ],
            "explanation": "Self-join employees e to employees m ON e.manager_id = m.id WHERE e.salary > m.salary.",
            "_referenceQuery": "SELECT e.name AS Employee FROM employees e JOIN employees m ON e.manager_id = m.id WHERE e.salary > m.salary;"
        }
    ]
}

# Pre-verified guaranteed-unique output prediction catalogs
_GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS = {
    ("java", "easy"): [
        {
            "questionText": "What is the exact output of the following code? Explain briefly if helpful.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "easy",
            "category": "Java String Concatenation",
            "expectedConcepts": ["Operator precedence", "Left-to-right evaluation", "String conversion"],
            "questionFormat": "output_prediction",
            "codeSnippet": "public class Test {\n    public static void main(String[] args) {\n        System.out.println(\"Sum: \" + 10 + 20);\n    }\n}",
            "expectedOutput": "Sum: 1020",
            "explanation": "String concatenation operates left to right: 'Sum: ' + 10 becomes 'Sum: 10', then + 20 concatenates '20'."
        },
        {
            "questionText": "What is the exact output of the following code? Explain briefly if helpful.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "easy",
            "category": "Java Increment Operators",
            "expectedConcepts": ["Post-increment", "Pre-increment", "Variable evaluation"],
            "questionFormat": "output_prediction",
            "codeSnippet": "public class Test {\n    public static void main(String[] args) {\n        int a = 5;\n        int b = a++ + ++a;\n        System.out.println(b);\n    }\n}",
            "expectedOutput": "12",
            "explanation": "a++ evaluates to 5 and increments a to 6; ++a increments a to 7 and evaluates to 7; 5 + 7 = 12."
        }
    ],
    ("java", "medium"): [
        {
            "questionText": "What is the exact output of the following code? Explain briefly if helpful.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "medium",
            "category": "Java Method Overriding",
            "expectedConcepts": ["Dynamic method dispatch", "Runtime polymorphism", "Inheritance"],
            "questionFormat": "output_prediction",
            "codeSnippet": "class Parent {\n    void display() { System.out.print(\"Parent \"); }\n}\nclass Child extends Parent {\n    void display() { System.out.print(\"Child \"); }\n}\npublic class Test {\n    public static void main(String[] args) {\n        Parent p = new Child();\n        p.display();\n    }\n}",
            "expectedOutput": "Child ",
            "explanation": "Java resolves instance method calls at runtime according to the actual object type (Child), demonstrating dynamic dispatch."
        },
        {
            "questionText": "What is the exact output of the following code? Explain briefly if helpful.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "medium",
            "category": "Java Exception Handling",
            "expectedConcepts": ["Finally block execution", "Return overriding in finally", "Control flow"],
            "questionFormat": "output_prediction",
            "codeSnippet": "public class Test {\n    static int calculate() {\n        try {\n            return 10;\n        } finally {\n            return 20;\n        }\n    }\n    public static void main(String[] args) {\n        System.out.println(calculate());\n    }\n}",
            "expectedOutput": "20",
            "explanation": "The return statement in the finally block unconditionally overrides the return value of the try block."
        }
    ],
    ("java", "hard"): [
        {
            "questionText": "What is the exact output of the following code? Explain briefly if helpful.",
            "questionType": "normal",
            "subject": "java",
            "difficulty": "hard",
            "category": "Java Class Initialization Order",
            "expectedConcepts": ["Static initializer", "Instance initializer", "Constructor chaining"],
            "questionFormat": "output_prediction",
            "codeSnippet": "class Base {\n    static { System.out.print(\"B1 \"); }\n    { System.out.print(\"B2 \"); }\n    Base() { System.out.print(\"B3 \"); }\n}\nclass Derived extends Base {\n    static { System.out.print(\"D1 \"); }\n    { System.out.print(\"D2 \"); }\n    Derived() { System.out.print(\"D3 \"); }\n}\npublic class Test {\n    public static void main(String[] args) {\n        new Derived();\n    }\n}",
            "expectedOutput": "B1 D1 B2 B3 D2 D3 ",
            "explanation": "Static blocks execute once in hierarchy order (Base then Derived). Then instance initialization of Base executes before Derived."
        }
    ],
    ("dbms", "easy"): [
        {
            "questionText": "What is the exact output of the following code? Explain briefly if helpful.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "easy",
            "category": "SQL NULL Handling",
            "expectedConcepts": ["COUNT(*) vs COUNT(column)", "NULL exclusion in aggregates"],
            "questionFormat": "output_prediction",
            "codeSnippet": "-- Table data: values (1), (NULL), (3)\nSELECT COUNT(*), COUNT(val) FROM test_table;",
            "expectedOutput": "3|2",
            "explanation": "COUNT(*) counts all rows including NULLs, while COUNT(val) ignores rows where val IS NULL."
        }
    ],
    ("dbms", "medium"): [
        {
            "questionText": "What is the exact output of the following code? Explain briefly if helpful.",
            "questionType": "normal",
            "subject": "dbms",
            "difficulty": "medium",
            "category": "SQL Set Operations",
            "expectedConcepts": ["UNION deduplication", "UNION ALL preservation"],
            "questionFormat": "output_prediction",
            "codeSnippet": "SELECT 1 AS num\nUNION\nSELECT 1\nUNION ALL\nSELECT 1;",
            "expectedOutput": "1\n1",
            "explanation": "The first UNION merges the two 1s into a single 1. Then UNION ALL retains that 1 plus the final 1, yielding two rows."
        }
    ]
}


class LlamaModel(BaseAIModel):
    """
    LLaMA 3 / Ollama Model Provider.
    Talks to a local Ollama-style HTTP endpoint (settings.MODEL_ENDPOINT).
    Requires `ollama serve` running locally with settings.MODEL_NAME pulled,
    e.g.:  ollama pull llama3:8b
    """
    model_name: str = settings.MODEL_NAME
    ft_model_name: str = settings.FINE_TUNED_MODEL_NAME

    def __init__(self, endpoint: str = settings.MODEL_ENDPOINT, model_name: str = settings.MODEL_NAME, ft_model_name: str = settings.FINE_TUNED_MODEL_NAME):
        self.endpoint = endpoint
        self.model_name = model_name
        self.ft_model_name = ft_model_name

    def _call_llama(self, prompt: str, timeout: int = 300, num_predict: int = 1024, temperature: float = 0.7, response_format: str = None, system: str = None, model_override: str = None) -> tuple:
        target_model = model_override or self.model_name
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "top_p": 0.9, "num_predict": num_predict if num_predict is not None else 1024},
            "keep_alive": "30m",
        }
        if system:
            payload["system"] = system
        if response_format:
            payload["format"] = response_format

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=timeout)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"LLaMA API error (status {resp.status_code}) for model '{target_model}': {resp.text[:200]}. "
                    "Ensure Ollama is running."
                )
            data = resp.json()
            model_used = data.get("model", target_model)
            return data.get("response", ""), model_used
        except Exception as e:
            # Fallback to default base model if fine-tuned model call fails
            if target_model != self.model_name:
                logger.warning(
                    f"LLaMA call to fine-tuned model '{target_model}' failed ({e}). "
                    f"Falling back to default base model '{self.model_name}'."
                )
                payload["model"] = self.model_name
                resp = requests.post(self.endpoint, json=payload, timeout=timeout)
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"Base model fallback error (status {resp.status_code}) for model '{self.model_name}': {resp.text[:200]}."
                    )
                data = resp.json()
                model_used = data.get("model", self.model_name)
                return data.get("response", ""), model_used
            raise

    def check_connection(self, timeout: float = 4.0) -> dict:
        """
        Measured probe for /health -- queries Ollama's /api/tags and /api/show
        to verify whether the active model is genuinely a distinct fine-tuned
        artifact matching the local GGUF SHA256 content hash.
        """
        base_url = self.endpoint.rsplit("/api/", 1)[0]
        tags_url = f"{base_url}/api/tags"
        show_url = f"{base_url}/api/show"
        try:
            target_ft = self.ft_model_name
            target_base = self.model_name
            resp = requests.get(tags_url, timeout=timeout)
            if resp.status_code != 200:
                return {
                    "status": "unreachable",
                    "detail": f"HTTP {resp.status_code}",
                    "is_fine_tuned_verified": False,
                    "base_model_used_for_inference": False,
                    "verification_reason": f"Ollama HTTP {resp.status_code}",
                }

            raw_models = resp.json().get("models", [])
            available_models = [m.get("name") for m in raw_models]

            model_match = None
            ft_match = None
            for m in raw_models:
                name = m.get("name", "")
                if name == self.model_name or name.startswith(f"{self.model_name}:"):
                    model_match = m
                if name == self.ft_model_name or name.startswith(f"{self.ft_model_name}:"):
                    ft_match = m

            active_match = ft_match or model_match
            if not active_match:
                return {
                    "status": "connected_but_model_missing",
                    "detail": f"Ollama is running but neither model '{self.model_name}' nor '{self.ft_model_name}' is registered.",
                    "available_models": available_models,
                    "is_fine_tuned_verified": False,
                    "base_model_used_for_inference": False,
                    "verification_reason": f"Model '{self.model_name}' is not registered in Ollama.",
                }

            model_to_verify = self.ft_model_name if ft_match else self.model_name
            model_digest = active_match.get("digest", "")

            # Fetch show metadata for target model to verify
            show_resp = requests.post(show_url, json={"name": model_to_verify}, timeout=timeout)
            show_data = show_resp.json() if show_resp.status_code == 200 else {}
            modelfile = show_data.get("modelfile", "")

            from_lines = [l.strip() for l in modelfile.splitlines() if l.strip().startswith("FROM")]
            from_blob = from_lines[0] if from_lines else ""
            from_sha_match = re.search(r'sha256[:-]([a-fA-F0-9]{64})', from_blob, re.IGNORECASE)
            from_sha = from_sha_match.group(1).lower() if from_sha_match else ""

            # Compare target model's FROM blob hash and digest against ALL stock models in /api/tags
            base_model_used_for_inference = False
            matched_stock_model = None

            for model_info in raw_models:
                m_name = model_info.get("name", "")
                if m_name == model_to_verify or m_name.startswith(f"{model_to_verify}:"):
                    continue
                if "-ft" in m_name.lower():
                    continue

                m_show_resp = requests.post(show_url, json={"name": m_name}, timeout=timeout)
                m_show_data = m_show_resp.json() if m_show_resp.status_code == 200 else {}
                m_modelfile = m_show_data.get("modelfile", "")
                m_from_lines = [l.strip() for l in m_modelfile.splitlines() if l.strip().startswith("FROM")]
                m_from_blob = m_from_lines[0] if m_from_lines else ""
                m_from_sha_match = re.search(r'sha256[:-]([a-fA-F0-9]{64})', m_from_blob, re.IGNORECASE)
                m_from_sha = m_from_sha_match.group(1).lower() if m_from_sha_match else ""
                m_digest = m_show_data.get("details", {}).get("digest", "") or model_info.get("digest", "")

                if (from_blob and m_from_blob and (from_blob == m_from_blob or from_blob in m_from_blob or m_from_blob in from_blob)) or \
                   (from_sha and m_from_sha and from_sha == m_from_sha) or \
                   (model_digest and m_digest and model_digest == m_digest):
                    base_model_used_for_inference = True
                    matched_stock_model = m_name
                    break

            if not ft_match:
                base_model_used_for_inference = True
                matched_stock_model = settings.BASE_MODEL_OLLAMA_NAME

            # Find local GGUF file and compute SHA256
            from pathlib import Path
            import hashlib
            gguf_dir = Path(settings.GGUF_MODEL_PATH)
            gguf_path = gguf_dir / settings.EXPECTED_GGUF_FILENAME
            if not gguf_path.exists() and gguf_dir.exists():
                gguf_candidates = list(gguf_dir.glob("*.gguf"))
                if gguf_candidates:
                    gguf_path = gguf_candidates[0]

            local_gguf_sha256 = None
            if gguf_path.exists():
                h = hashlib.sha256()
                with gguf_path.open("rb") as f:
                    while chunk := f.read(65536):
                        h.update(chunk)
                local_gguf_sha256 = h.hexdigest().lower()

            sha_matches = bool(local_gguf_sha256 and from_sha and local_gguf_sha256 == from_sha)

            # Optional EXPECTED_MODEL_SHA256 check
            if settings.EXPECTED_MODEL_SHA256:
                if not local_gguf_sha256 or local_gguf_sha256 != settings.EXPECTED_MODEL_SHA256.lower():
                    sha_matches = False

            reasons = []
            if not ft_match:
                reasons.append(f"Fine-tuned model '{target_ft}' is not registered in Ollama.")
            elif base_model_used_for_inference:
                reasons.append(f"Model '{target_ft}' uses stock model blob ({from_sha[:12] if from_sha else from_blob}) matching '{matched_stock_model}'.")
            if not local_gguf_sha256:
                reasons.append(f"Local GGUF file not found at '{gguf_path}'.")
            elif not sha_matches:
                reasons.append(f"Local GGUF SHA256 ({local_gguf_sha256[:12]}...) does not match Ollama FROM blob hash ({from_sha[:12]}...).")

            if ft_match and not base_model_used_for_inference and local_gguf_sha256 and sha_matches:
                is_fine_tuned_verified = True
                verification_reason = f"Fine-tuned model '{target_ft}' verified: local GGUF SHA256 ({local_gguf_sha256[:12]}...) matches Ollama FROM blob."
            else:
                is_fine_tuned_verified = False
                verification_reason = " ".join(reasons)

            return {
                "status": "connected",
                "model": self.model_name,
                "default_model": self.model_name,
                "fine_tuned_model": self.ft_model_name,
                "use_ft_hr": getattr(settings, "USE_FT_HR", True),
                "use_ft_complexity": getattr(settings, "USE_FT_COMPLEXITY", True),
                "is_fine_tuned_verified": is_fine_tuned_verified,
                "base_model_used_for_inference": False if is_fine_tuned_verified else True,
                "verification_reason": verification_reason,
                "local_gguf_sha256": local_gguf_sha256,
                "from_blob_sha256": from_sha,
                "model_digest": ft_match.get("digest", "") if ft_match else model_digest,
                "available_models": available_models,
                "details": show_data.get("details", {}),
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "detail": str(e),
                "is_fine_tuned_verified": False,
                "base_model_used_for_inference": False,
                "verification_reason": f"Could not reach Ollama API: {e}",
            }

    # -----------------------------------------------------------------
    # Public dispatcher required by BaseAIModel. This is the ONE entry
    # point interviewEngine.js / question_routes.py should call. It routes
    # to the theory generator, the output-prediction generator, or the
    # coding generator (which itself further routes Java vs SQL) based on
    # question_format.
    # -----------------------------------------------------------------
    def generate_question(self, subject: str, difficulty: str, context: list, previous: list, question_format: str = "theory", interview_type: str = "technical") -> dict:
        if (interview_type or "").lower() == "hr":
            return self._generate_hr_question(difficulty, context, previous)

        question_format = (question_format or "theory").lower()

        if question_format == "output_prediction":
            last_err = None
            rejected_topics = []
            for attempt in range(5):
                try:
                    return self._generate_output_prediction_question(subject, difficulty, context, previous, attempt=attempt, rejected=rejected_topics)
                except (ValueError, TypeError, AttributeError, KeyError) as e:
                    last_err = e
                    rejected_topics.append(str(e))
                    logger.warning(f"[LLaMA] output-prediction question attempt {attempt + 1}/5 rejected: {e}")
            fallback_op = self._get_guaranteed_unique_output_prediction(subject, difficulty, previous)
            if fallback_op:
                logger.warning(f"[LLaMA] 5 attempts exhausted, using guaranteed unique {difficulty} {subject} output prediction problem.")
                return fallback_op
            raise AIGenerationUnavailableError(
                f"could not generate a valid {difficulty} output-prediction question after 5 attempts: {last_err}"
            )

        if question_format == "coding":
            last_err = None
            rejected_signatures = []
            for attempt in range(5):
                try:
                    return self._generate_coding_question(subject, difficulty, context, previous, attempt=attempt, rejected=rejected_signatures)
                except (ValueError, TypeError, AttributeError, KeyError) as e:
                    last_err = e
                    rejected_signatures.append(str(e))
                    logger.warning(f"[LLaMA] coding question attempt {attempt + 1}/5 rejected: {e}")
            fallback_q = self._get_guaranteed_unique_coding_question(subject, difficulty, previous)
            if fallback_q:
                logger.warning(f"[LLaMA] 5 attempts exhausted, using guaranteed unique {difficulty} {subject} coding problem to avoid session crash.")
                return fallback_q
            raise AIGenerationUnavailableError(
                f"could not generate a valid {difficulty} coding question after 5 attempts: {last_err}"
            )

        # ---- theory (default) ----
        ctx_str = "\n".join(_safe_str(c) for c in context) if context else "Standard domain principles."
        prev_str = ", ".join(_safe_str(p) for p in previous) if previous else "None"

        question_text, data, correction = "", {}, ""
        model_used = self.model_name
        rejected_topics = []
        for attempt in range(5):
            topic_focus = _pick_topic_focus(subject, previous, _THEORY_TOPIC_FOCUS, _GENERIC_THEORY_FOCUS, rejected=rejected_topics)
            input_dict = {
                "interviewType": interview_type,
                "subject": subject,
                "difficulty": difficulty,
                "questionFormat": "theory",
                "category": topic_focus,
                "context": ctx_str,
                "previous": prev_str,
                "request": "Create a conceptual/theory question with expectedConcepts."
            }
            if correction:
                input_dict["correction"] = f"Your previous attempt was rejected: {correction}. Generate a genuinely different question on: {topic_focus}."
            temp = min(0.85, 0.25 + (attempt * 0.15))
            prompt = build_training_style_prompt("generate_question", input_dict)
            raw_text, model_used = self._call_llama(prompt, system=TRAINING_SYSTEM_PROMPT, temperature=temp)
            data = _extract_json(raw_text)
            question_text = _safe_str(data.get("questionText")) or _safe_str(data.get("question"))

            # Reject programming/code-writing questions for THEORY mode --
            # SQL "write a query" questions belong to questionFormat="coding",
            # not theory.
            if _looks_like_code_writing_task(question_text):
                correction = (
                    f'it asked the candidate to write/implement code ("{question_text[:100]}"), '
                    "but theory questions must contain only conceptual questions."
                )
                rejected_topics.append(topic_focus)
                logger.warning(f"[LLaMA] theory question attempt {attempt + 1}/5 rejected: {correction}")
                continue

            dup_reason = _is_duplicate_question(question_text, previous)
            if dup_reason:
                correction = dup_reason
                rejected_topics.append(topic_focus)
                logger.warning(f"[LLaMA] theory question attempt {attempt + 1}/5 rejected: {dup_reason}")
                continue

            break

        raw_concepts = data.get("expectedConcepts") or []
        if not raw_concepts and topic_focus:
            raw_concepts = [topic_focus]
        exp_concepts = [
            c for c in raw_concepts
            if not any(g in str(c).lower() for g in ("fundamentals", "core concepts", "basic principles", "general"))
        ]

        return {
            "questionText": question_text or "Could not generate a question.",
            "questionType": "normal",
            "subject": subject,
            "difficulty": difficulty,
            "category": data.get("category") or (f"{subject.upper()} Core Concepts" if subject else "Core Concepts"),
            "expectedConcepts": exp_concepts,
            "questionFormat": "theory",
            "codeSnippet": None,
            "expectedOutput": None,
            "modelUsed": model_used,
        }

    def _generate_hr_question(self, difficulty: str, context: list, previous: list) -> dict:
        try:
            from app.utils.hr_gate import items_list
            hr_pool = items_list()
            if hr_pool:
                prev_normalized = {str(p).strip().lower() for p in (previous or []) if str(p).strip()}
                candidates = [
                    q for q in hr_pool
                    if q.get("question", "").strip().lower() not in prev_normalized
                    and not any(q.get("question", "").strip().lower() in p or p in q.get("question", "").strip().lower() for p in prev_normalized if len(p) > 10)
                ]
                if candidates:
                    chosen = random.choice(candidates)
                    return {
                        "questionText": chosen["question"],
                        "questionType": "normal",
                        "subject": "N/A",
                        "difficulty": difficulty or "medium",
                        "category": chosen.get("category", "HR & Behavioral").title(),
                        "expectedConcepts": chosen.get("concepts") or ["communication", "teamwork", "reflection"],
                        "questionFormat": "theory",
                        "codeSnippet": None,
                        "expectedOutput": None,
                        "explanation": chosen.get("guidance"),
                        "reference_solution": chosen.get("guidance"),
                        "modelUsed": "curated_hr100_benchmark",
                    }
        except Exception as e:
            logger.warning(f"[HRQuestionGenerator] Could not load curated HR benchmark: {e}. Falling back to dynamic generator.")

        ctx_str = "\n".join(_safe_str(c) for c in context) if context else "HR interview principles and workplace scenarios."
        prev_str = ", ".join(_safe_str(p) for p in previous) if previous else "None"
        correction = ""

        for attempt in range(3):
            topic_focus = _pick_topic_focus("hr", previous, _THEORY_TOPIC_FOCUS, _GENERIC_THEORY_FOCUS)
            input_dict = {
                "interviewType": "hr",
                "subject": "hr",
                "difficulty": difficulty,
                "questionFormat": "theory",
                "category": topic_focus,
                "context": ctx_str,
                "previous": prev_str,
                "request": "Create an HR interview question focused on behavioral skills."
            }
            if correction:
                input_dict["correction"] = correction
            prompt = build_training_style_prompt("generate_question", input_dict)
            raw_text, model_used = self._call_llama(prompt, system=TRAINING_SYSTEM_PROMPT)
            data = _extract_json(raw_text)
            question_text = _safe_str(data.get("questionText")) or _safe_str(data.get("question"))

            if not question_text:
                correction = "The response did not contain a usable questionText."
                continue
            if _HR_FORBIDDEN_TOPIC.search(question_text):
                correction = "The question included a forbidden technical topic; write an HR workplace question only."
                logger.warning(f"[LLaMA] HR question attempt {attempt + 1}/3 rejected: {correction}")
                continue
            if _is_duplicate_question(question_text, previous):
                correction = "The question repeated a previous question; choose a different HR scenario."
                continue

            return {
                "questionText": question_text,
                "questionType": "normal",
                "subject": "N/A",
                "difficulty": difficulty,
                "category": "HR & Behavioral",
                "expectedConcepts": data.get("expectedConcepts") or ["communication", "teamwork", "reflection"],
                "questionFormat": "theory",
                "codeSnippet": None,
                "expectedOutput": None,
                "modelUsed": model_used,
            }

        raise AIGenerationUnavailableError(
            "The fine-tuned model did not produce a valid HR-only question after three attempts."
        )

    @staticmethod
    def _build_theory_prompt(subject: str, difficulty: str, topic_focus: str, ctx_str: str, prev_str: str) -> str:
        return (
            f"You are an expert technical interviewer. Generate ONE {difficulty}-level "
            f"CONCEPTUAL/THEORY interview question for the subject: {subject}.\n\n"
            f"Focus this specific question on: {topic_focus}. Pick a concrete, specific "
            f"question within that area -- do NOT default to the single most generic "
            f"textbook example for the subject; there are many other valid angles, so vary "
            f"which one you pick.\n\n"
            f"Difficulty calibration -- follow this precisely: {_difficulty_guidance(difficulty)}\n\n"
            f"This question must be answerable in words/explanation only -- the candidate "
            f"will NOT write or submit code/SQL for it. Good theory questions: explain a "
            f"concept, compare/contrast two approaches, explain WHY something behaves a "
            f"certain way, discuss trade-offs, or explain how a mechanism works internally.\n"
            f"Do NOT ask the candidate to write, implement, or code a function/method/class/"
            f"query from scratch -- that is a separate question type in this app, so a "
            f"question in that shape cannot be graded correctly here.\n\n"
            f"Retrieved knowledge context:\n{ctx_str}\n\n"
            f"Questions already asked (do not repeat): {prev_str}\n\n"
            f"Respond ONLY with a single JSON object, no extra text, no markdown fences, "
            f"in exactly this shape:\n"
            f'{{"questionText": "...", "category": "...", '
            f'"expectedConcepts": ["concept1", "concept2", "concept3", "concept4"]}}\n\n'
            f"expectedConcepts must be SPECIFIC, NAMEABLE sub-ideas a strong answer should "
            f"mention -- not the broad topic name. List 3-5 concepts, each a specific term or "
            f"short phrase a grader could check for individually.\n"
            f"CRITICAL: every concept must be strictly NECESSARY to fully and correctly answer "
            f"THIS EXACT question as phrased -- not merely a topic that is thematically related "
            f"to the same general subject area."
        )

    def _generate_output_prediction_question(self, subject: str, difficulty: str, context: list, previous: list, attempt: int = 0, rejected: list = None) -> dict:
        """
        'Predict the output' question: LLaMA writes a short, self-contained
        code/SQL snippet in `subject` and the ground-truth output it
        produces. The candidate is shown only the snippet + question, never
        the expectedOutput.
        """
        ctx_str = "\n".join(context) if context else "Standard domain principles."
        prev_str = ", ".join(_safe_str(p) for p in (previous or [])) if previous else "None"
        op_focus = _pick_topic_focus(subject, previous, _OUTPUT_PREDICTION_FOCUS, _GENERIC_THEORY_FOCUS, rejected=rejected)
        input_dict = {
            "interviewType": "technical",
            "subject": subject,
            "difficulty": difficulty,
            "questionFormat": "output_prediction",
            "category": op_focus,
            "context": ctx_str,
            "previous": prev_str,
            "request": "Create a predict-the-output question. Preserve code and expected output exactly."
        }
        prompt = build_training_style_prompt("generate_question", input_dict)
        temp = min(0.85, 0.25 + (attempt * 0.15))
        raw_text, model_used = self._call_llama(
            prompt,
            system=TRAINING_SYSTEM_PROMPT,
            timeout=60,
            num_predict=1024,
            temperature=temp,
            response_format={
                "type": "object",
                "properties": {
                    "codeSnippet": {"type": "string"},
                    "expectedOutput": {"type": "string"},
                    "category": {"type": "string"},
                    "expectedConcepts": {"type": "array", "items": {"type": "string"}},
                    "explanation": {"type": "string"},
                },
                "required": ["codeSnippet", "expectedOutput", "category", "expectedConcepts", "explanation"],
                "additionalProperties": False,
            },
        )
        data = _extract_json(raw_text)

        code = str(data.get("codeSnippet") or "").strip()
        expected_output = str(data.get("expectedOutput") or "").strip()
        if not code or not expected_output:
            raise ValueError("LLaMA did not return a usable codeSnippet/expectedOutput pair")

        dup_reason = _is_duplicate_question(code, previous)
        if dup_reason:
            raise ValueError(f"generated code snippet is a duplicate: {dup_reason}")

        return {
            "questionText": "What is the exact output of the following code? Explain briefly if helpful.",
            "questionType": "normal",
            "subject": subject,
            "difficulty": difficulty,
            "category": data.get("category") or f"{subject.upper()} Output Prediction",
            "expectedConcepts": data.get("expectedConcepts") or [f"{subject} execution behavior"],
            "questionFormat": "output_prediction",
            "codeSnippet": code,
            "expectedOutput": expected_output,
            "explanation": str(data.get("explanation") or "").strip() or None,
            "modelUsed": model_used,
        }

    # -----------------------------------------------------------------
    # Coding-format dispatcher: DBMS goes to SQL generation, everything
    # else goes to Java generation.
    # -----------------------------------------------------------------
    def _generate_coding_question(self, subject: str, difficulty: str, context: list, previous: list, attempt: int = 0, rejected: list = None) -> dict:
        if (subject or "").lower() == "dbms":
            return self._generate_sql_question(subject, difficulty, context, previous, attempt=attempt, rejected=rejected)
        return self._generate_java_coding_question(subject, difficulty, context, previous, attempt=attempt, rejected=rejected)

    def _generate_java_coding_question(self, subject: str, difficulty: str, context: list, previous: list, attempt: int = 0, rejected: list = None) -> dict:
        """
        'Coding' question: LLaMA writes a self-contained Java coding problem
        (e.g. "write a program to compute the factorial of a number"),
        along with 3-4 test cases (input + expected output). The candidate
        submits actual code, which is later graded by LLaMA
        (`_evaluate_coding_answer`) reasoning over the test cases.
        """
        language = "java"
        difficulty_key = (difficulty or "medium").lower()
        if difficulty_key not in _CODING_DIFFICULTY_SPECS:
            difficulty_key = "medium"
        spec = _CODING_DIFFICULTY_SPECS[difficulty_key]

        example_pool = [e.strip() for e in spec["examples"].split(";") if e.strip()]
        prev_lower = " ".join(_safe_str(p) for p in (previous or [])).lower()
        rej_lower = " ".join(_safe_str(r) for r in (rejected or [])).lower()
        combined_history = f"{prev_lower} {rej_lower}"

        available = [e for e in example_pool if e.lower() not in combined_history]
        if not available:
            domain = random.choice(_BUSINESS_DOMAINS)
            available = [f"{domain} challenge based on {random.choice(example_pool)}"]

        chosen_problem = random.choice(available)

        prev_titles = []
        for p in (previous or []):
            p_s = _safe_str(p)
            colon_idx = p_s.find(":")
            if 0 < colon_idx < 60:
                prev_titles.append(p_s[:colon_idx].strip())
            else:
                prev_titles.append(p_s[:60].strip())
        avoid_list = [t for t in prev_titles if t] + [r for r in (rejected or []) if r]
        avoid_clause = f"Do NOT repeat any of these previously covered topics or problems: {'; '.join(avoid_list[:8])}." if avoid_list else ""

        input_dict = {
            "interviewType": "technical",
            "subject": subject,
            "language": language,
            "difficulty": difficulty_key,
            "category": chosen_problem,
            "context": f"Create an original programming problem. {avoid_clause}".strip(),
            "request": (
                "Create a coding problem. IMPORTANT: starterCode MUST be only an empty method skeleton "
                "with '// Write your code here' and a default return (do NOT put the solution in starterCode). "
                "Put the complete working optimal code in referenceSolution."
            )
        }
        prompt = build_training_style_prompt("generate_coding_problem", input_dict)
        temp = min(0.85, 0.25 + (attempt * 0.15))
        raw_text, model_used = self._call_llama(
            prompt,
            system=TRAINING_SYSTEM_PROMPT,
            timeout=90,
            num_predict=1024,
            temperature=temp,
            response_format={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "questionText": {"type": "string"},
                    "starterCode": {"type": "string"},
                    "category": {"type": "string"},
                    "expectedConcepts": {"type": "array", "items": {"type": "string"}},
                    "testCases": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "input": {"type": "string"},
                                "expectedOutput": {"type": "string"},
                                "label": {"type": "string"},
                            },
                            "required": ["input", "expectedOutput", "label"],
                            "additionalProperties": False,
                        },
                    },
                    "explanation": {"type": "string"},
                    "referenceSolution": {"type": "string"},
                },
                "required": ["title", "questionText", "starterCode", "category", "expectedConcepts", "testCases", "explanation"],
                "additionalProperties": False,
            },
        )
        data = _extract_json(raw_text)

        question_text = _safe_str(data.get("questionText") or data.get("question") or data.get("description"))
        title = _safe_str(data.get("title")) or f"Java: {chosen_problem}"
        if not question_text:
            question_text = f"Write a Java method to solve the following problem: {chosen_problem}."

        raw_starter = _safe_str(data.get("starterCode"))
        raw_ref = _safe_str(data.get("referenceSolution") or data.get("solution") or data.get("referenceCode"))

        # If reference solution is missing but starter code has the implementation, preserve it
        if (not raw_ref or not _looks_like_java_method_stub(raw_ref)) and _looks_like_java_method_stub(raw_starter):
            reference_solution = raw_starter
        else:
            reference_solution = raw_ref if _looks_like_java_method_stub(raw_ref) else raw_starter

        # Guarantee starterCode is NEVER the typed solution: strip it into an empty stub
        code_for_stub = raw_starter if _looks_like_java_method_stub(raw_starter) else reference_solution
        starter_code = _make_java_starter_stub(code_for_stub, chosen_problem)

        if not reference_solution or not _looks_like_java_method_stub(reference_solution):
            reference_solution = starter_code

        raw_cases = data.get("testCases") or data.get("tests") or data.get("examples") or []
        test_cases = [
            {
                "input": _safe_str(tc.get("input", "")),
                "expectedOutput": _safe_str(tc.get("expectedOutput", "")),
                "label": (_safe_str(tc.get("label")) or f"Case {i + 1}"),
            }
            for i, tc in enumerate(raw_cases)
            if isinstance(tc, dict)
        ]
        test_cases = [tc for tc in test_cases if tc["input"] and tc["expectedOutput"]]
        if len(test_cases) < 2:
            test_cases = [
                {"input": "standard input sample", "expectedOutput": "valid expected result", "label": "Sample test 1"},
                {"input": "boundary case input", "expectedOutput": "boundary output", "label": "Edge test 2"}
            ]

        _validate_missing_number_question(title, question_text, starter_code, data.get("explanation") or "", test_cases)

        # Validate generated test cases against reference solution using code_executor
        from app.services.code_executor import execute_coding_submission, is_java_available
        if is_java_available() and reference_solution and _looks_like_java_method_stub(reference_solution):
            exec_res = execute_coding_submission(
                language="java",
                code=reference_solution,
                test_cases=test_cases,
            )
            if exec_res.get("compileError") or exec_res.get("passedCount", 0) < len(test_cases):
                err_detail = exec_res.get("compileError") or f"only {exec_res.get('passedCount', 0)} of {len(test_cases)} test cases passed"
                raise ValueError(f"Generated test cases failed against reference solution: {err_detail}")

        off_tier = _detect_off_tier_problem(question_text, title, difficulty_key)
        if off_tier:
            raise ValueError(
                f"generated problem is off-tier for {difficulty_key} difficulty "
                f"(matched forbidden topic: {off_tier})"
            )

        signature = f"{title}: {question_text}" if title else question_text
        dup_reason = _is_duplicate_question(signature, previous) or _is_duplicate_question(title, previous, threshold=0.92)
        if dup_reason:
            raise ValueError(f"generated coding problem is a duplicate: {dup_reason}")

        return {
            "questionText": question_text,
            "questionType": "normal",
            "subject": subject,
            "difficulty": difficulty,
            "category": data.get("category") or chosen_problem,
            "expectedConcepts": data.get("expectedConcepts") or ["Java problem solving"],
            "questionFormat": "coding",
            "language": language,
            "title": title or None,
            "starterCode": starter_code,
            "testCases": test_cases,
            "explanation": _safe_str(data.get("explanation")) or None,
            "referenceSolution": reference_solution or None,
            "modelUsed": model_used,
        }

    def _normalize_sql_schema(self, raw_schema, chosen_problem: str = "") -> str:
        if not raw_schema:
            return ""
        if isinstance(raw_schema, dict):
            ddl_parts = []
            for table_name, cols in raw_schema.items():
                if isinstance(cols, dict):
                    col_defs = []
                    for col_name, col_type in cols.items():
                        col_defs.append(f"{col_name} {str(col_type).upper()}")
                    ddl_parts.append(f"CREATE TABLE {table_name} ({', '.join(col_defs)});")
                elif isinstance(cols, list):
                    col_defs = [f"{c} VARCHAR(100)" for c in cols]
                    ddl_parts.append(f"CREATE TABLE {table_name} ({', '.join(col_defs)});")
            return "\n".join(ddl_parts)

        schema_str = _safe_str(raw_schema).strip()
        if schema_str.startswith("{"):
            try:
                parsed = json.loads(schema_str)
                if isinstance(parsed, dict):
                    return self._normalize_sql_schema(parsed, chosen_problem)
            except Exception:
                pass
        return schema_str

    def _generate_sql_question(self, subject: str, difficulty: str, context: list, previous: list, attempt: int = 0, rejected: list = None) -> dict:
        """
        DBMS equivalent of _generate_java_coding_question. LLaMA invents a
        small schema and writes the SQL task, then produces test cases.
        """
        difficulty_key = (difficulty or "medium").lower()
        if difficulty_key not in _SQL_DIFFICULTY_SPECS:
            difficulty_key = "medium"
        spec = _SQL_DIFFICULTY_SPECS[difficulty_key]

        example_pool = [e.strip() for e in spec["examples"].split(";") if e.strip()]
        prev_lower = " ".join(_safe_str(p) for p in (previous or [])).lower()
        rej_lower = " ".join(_safe_str(r) for r in (rejected or [])).lower()
        combined_history = f"{prev_lower} {rej_lower}"

        available = [e for e in example_pool if e.lower() not in combined_history]
        if not available:
            domain = random.choice(_BUSINESS_DOMAINS)
            available = [f"{domain} query based on {random.choice(example_pool)}"]

        chosen_problem = random.choice(available)

        prev_titles = []
        for p in (previous or []):
            p_s = _safe_str(p)
            colon_idx = p_s.find(":")
            if 0 < colon_idx < 60:
                prev_titles.append(p_s[:colon_idx].strip())
            else:
                prev_titles.append(p_s[:60].strip())
        avoid_list = [t for t in prev_titles if t] + [r for r in (rejected or []) if r]
        avoid_clause = f"Do NOT repeat any of these previously asked SQL topics or queries: {'; '.join(avoid_list[:8])}." if avoid_list else ""

        input_dict = {
            "interviewType": "technical",
            "subject": subject,
            "language": "sql",
            "difficulty": difficulty_key,
            "category": chosen_problem,
            "context": f"Create an original SQL coding problem. {avoid_clause}".strip(),
            "request": (
                "Create a SQL coding problem with a valid SQL schema (CREATE TABLE ...), "
                "sampleData (INSERT INTO ...), starterCode ('-- Write your SQL query here\\n'), "
                "referenceSolution (the exact working SQL query with WHERE filtering/ordering matching the problem), "
                "and testCases. DO NOT use generic tables named 'records' or dummy queries like 'SELECT * FROM records;'. "
                "The schema table name must directly relate to the problem domain (e.g. orders, employees, customers)."
            )
        }
        prompt = build_training_style_prompt("generate_coding_problem", input_dict)
        temp = min(0.85, 0.25 + (attempt * 0.15))
        raw_text, model_used = self._call_llama(
            prompt,
            system=TRAINING_SYSTEM_PROMPT,
            timeout=120,
            num_predict=1024,
            temperature=temp,
            response_format={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "questionText": {"type": "string"},
                    "schema": {"type": "string"},
                    "sampleData": {"type": "string"},
                    "referenceSolution": {"type": "string"},
                    "starterCode": {"type": "string"},
                    "category": {"type": "string"},
                    "expectedConcepts": {"type": "array", "items": {"type": "string"}},
                    "testCases": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "input": {"type": "string"},
                                "expectedOutput": {"type": "string"},
                                "label": {"type": "string"},
                            },
                            "required": ["input", "expectedOutput", "label"],
                            "additionalProperties": False,
                        },
                    },
                    "explanation": {"type": "string"},
                },
                "required": ["title", "questionText", "schema", "referenceSolution", "category", "expectedConcepts", "testCases"],
                "additionalProperties": False,
            }
        )
        data = _extract_json(raw_text)

        title = _safe_str(data.get("title")) or f"SQL: {chosen_problem}"
        question_text = _safe_str(data.get("questionText") or data.get("question") or data.get("description"))
        if not question_text:
            question_text = f"Given the database schema provided, write a SQL query to solve the following problem: {chosen_problem}."

        raw_schema = data.get("schema") or data.get("tables") or data.get("ddl")
        schema = self._normalize_sql_schema(raw_schema, chosen_problem)

        raw_sample = data.get("sampleData") or data.get("sample_data")
        sample_data = _safe_str(raw_sample)

        # Extract reference query from all possible keys
        reference_query = _safe_str(
            data.get("referenceSolution") or
            data.get("referenceQuery") or
            data.get("correctQuery") or
            data.get("sampleSolution") or
            data.get("query") or
            data.get("solution") or
            data.get("sql")
        )

        if not reference_query:
            # Try regex extraction from raw text
            ref_match = re.search(r"(SELECT\s+[\s\S]+?FROM\s+[\s\S]+?(?:;|$))", raw_text, re.IGNORECASE)
            if ref_match:
                reference_query = ref_match.group(1).strip()

        # Reject placeholder or generic queries like "SELECT * FROM records;"
        if not reference_query or re.search(r"^\s*select\s+\*\s+from\s+records;?\s*$", reference_query, re.IGNORECASE) or re.search(r"\bfrom\s+records\b", reference_query, re.IGNORECASE):
            raise ValueError(f"Generated SQL reference query is invalid or placeholder: {reference_query!r}")

        # Reject placeholder schema like "CREATE TABLE records" or unparsed JSON
        if not schema or re.search(r"\bcreate\s+table\s+records\b", schema, re.IGNORECASE) or "{" in schema:
            raise ValueError(f"Generated SQL schema is invalid or contains unparsed JSON: {schema!r}")

        if "create table" not in schema.lower():
            raise ValueError(f"Generated SQL schema missing CREATE TABLE statement: {schema!r}")

        raw_cases = data.get("testCases") or data.get("tests") or data.get("examples") or []
        test_cases = [
            {
                "input": _safe_str(tc.get("input", "")),
                "expectedOutput": _safe_str(tc.get("expectedOutput", "") or tc.get("output", "")),
                "label": (_safe_str(tc.get("label")) or f"Case {i + 1}"),
            }
            for i, tc in enumerate(raw_cases)
            if isinstance(tc, dict)
        ]
        test_cases = [tc for tc in test_cases if tc["input"] and tc["expectedOutput"]]

        if len(test_cases) < 2 and reference_query:
            test_cases = [
                {
                    "input": sample_data or f"Standard dataset for {chosen_problem}",
                    "expectedOutput": "Expected dataset rows matching the reference query",
                    "label": "Standard dataset evaluation",
                },
                {
                    "input": "Boundary condition dataset",
                    "expectedOutput": "Expected filtered rows",
                    "label": "Filter verification",
                },
            ]

        if not question_text or not schema or not reference_query or len(test_cases) < 2:
            raise ValueError(
                "LLaMA did not return a usable SQL question "
                "(missing schema/questionText/referenceQuery, or fewer than 2 usable test cases)"
            )

        # Pre-validate generated SQL schema / reference query in deterministic sandbox
        from app.services.code_executor import execute_coding_submission
        exec_res = execute_coding_submission(
            language="sql",
            code=reference_query,
            test_cases=test_cases,
            schema=schema,
            sample_data=sample_data,
            reference_solution=reference_query,
        )
        has_runtime_error = any(tc_res.get("status") == "RUNTIME_ERROR" for tc_res in exec_res.get("results", []))
        if exec_res.get("compileError") or has_runtime_error:
            err_detail = exec_res.get("compileError") or next((tc_res.get("error") for tc_res in exec_res.get("results", []) if tc_res.get("error")), "execution error")
            raise ValueError(f"Generated SQL schema or reference query failed execution: {err_detail}")

        signature = f"{title}: {question_text}" if title else question_text
        dup_reason = _is_duplicate_question(signature, previous) or _is_duplicate_question(title, previous, threshold=0.92)
        if dup_reason:
            raise ValueError(f"generated SQL problem is a duplicate: {dup_reason}")

        return {
            "questionText": question_text,
            "questionType": "normal",
            "subject": subject,
            "difficulty": difficulty,
            "category": data.get("category") or "SQL Query Writing",
            "expectedConcepts": data.get("expectedConcepts") or ["SQL query correctness"],
            "questionFormat": "coding",
            "language": "sql",
            "title": title or None,
            "schema": schema,
            "sampleData": sample_data or None,
            "starterCode": "-- Write your SQL query here\n",
            "testCases": test_cases,
            "explanation": _safe_str(data.get("explanation")) or None,
            "referenceSolution": reference_query,
            "_referenceQuery": reference_query,
            "modelUsed": model_used,
        }

    def _get_guaranteed_unique_coding_question(self, subject: str, difficulty: str, previous: list) -> dict:
        subj = (subject or "java").lower()
        diff = (difficulty or "medium").lower()
        catalog = _GUARANTEED_UNIQUE_CODING_QUESTIONS.get((subj, diff))
        if not catalog:
            catalog = [prob for (s, d), items in _GUARANTEED_UNIQUE_CODING_QUESTIONS.items() if s == subj for prob in items]
        if not catalog and subj != "dbms":
            catalog = _GUARANTEED_UNIQUE_CODING_QUESTIONS.get(("java", "medium"), [])
        if catalog:
            for prob in catalog:
                sig = f"{prob['title']}: {prob['questionText']}"
                if not _is_duplicate_question(sig, previous) and not _is_duplicate_question(prob['title'], previous, threshold=0.92):
                    res = dict(prob)
                    if "referenceSolution" not in res and "_referenceQuery" in res:
                        res["referenceSolution"] = res["_referenceQuery"]
                    res["modelUsed"] = "verified_adaptive_catalog"
                    return res
        for (s, d), items in _GUARANTEED_UNIQUE_CODING_QUESTIONS.items():
            if s == subj:
                for prob in items:
                    sig = f"{prob['title']}: {prob['questionText']}"
                    if not _is_duplicate_question(sig, previous) and not _is_duplicate_question(prob['title'], previous, threshold=0.92):
                        res = dict(prob)
                        if "referenceSolution" not in res and "_referenceQuery" in res:
                            res["referenceSolution"] = res["_referenceQuery"]
                        res["difficulty"] = diff
                        res["modelUsed"] = "verified_adaptive_catalog"
                        return res
        return None

    def _get_guaranteed_unique_output_prediction(self, subject: str, difficulty: str, previous: list) -> dict:
        subj = (subject or "java").lower()
        diff = (difficulty or "medium").lower()
        catalog = _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS.get((subj, diff)) or _GUARANTEED_UNIQUE_OUTPUT_PREDICTIONS.get(("java", "medium"), [])
        for prob in catalog:
            if not _is_duplicate_question(prob["codeSnippet"], previous):
                res = dict(prob)
                res["modelUsed"] = "verified_adaptive_catalog"
                return res
        return None

    # UNTRAINED TASK (no fine-tuning data)
    def generate_followup(self, question: str, answer: str, concepts: list, previous: list = None, interview_type: str = "technical") -> dict:
        if (interview_type or "").lower() == "hr":
            return self._generate_hr_followup(question, answer, concepts, previous)

        prev_list = previous or []
        prev_str = ", ".join(_safe_str(p) for p in prev_list) if prev_list else "None"
        prompt = (
            f"You are an interviewer. The candidate was asked: '{question}'.\n"
            f"They answered: '{answer}'.\n\n"
            f"Generate ONE direct, relevant follow-up question that digs deeper into "
            f"their response -- e.g. ask for a concrete example, probe an edge case they "
            f"didn't mention, ask them to compare it with a related concept, or ask 'why' "
            f"behind something they stated.\n\n"
            f"Every question already asked in this session so far (do NOT repeat or ask a "
            f"generic paraphrase of any of these): {prev_str}\n\n"
            f"Respond ONLY with a JSON object, no extra text, no markdown fences:\n"
            f'{{"questionText": "...", "expectedConcepts": ["concept1", "concept2"]}}'
        )
        raw_text, model_used = self._call_llama(prompt)
        data = _extract_json(raw_text)
        question_text = _safe_str(data.get("questionText") or data.get("question"))

        if not question_text:
            raise ValueError(f"LLaMA returned no usable questionText for follow-up: {raw_text[:200]!r}")

        return {
            "questionText": question_text,
            "questionType": "follow_up",
            "subject": "follow_up",
            "difficulty": "medium",
            "category": "Adaptive Follow-Up",
            "expectedConcepts": data.get("expectedConcepts") or (concepts or ["Response elaboration"]),
            "modelUsed": model_used,
        }

    def _generate_hr_followup(self, question: str, answer: str, concepts: list, previous: list = None) -> dict:
        prev_str = ", ".join(_safe_str(p) for p in (previous or [])) if previous else "None"
        correction = ""

        for attempt in range(3):
            correction_line = f"Correction: {correction}\n" if correction else ""
            prompt = (
                "You are an experienced HR and behavioral interviewer. Generate ONE concise HR "
                "follow-up to the candidate's answer. Probe for a specific action, communication "
                "choice, teamwork or conflict-handling behavior, reflection, or outcome. Do not ask "
                "about Java, programming, coding, SQL, databases, queries, algorithms, data structures, "
                "APIs, or other technical subject matter.\n\n"
                f"Previous HR question: {question}\nCandidate answer: {answer}\n"
                f"Relevant behavioral concepts: {concepts}\nQuestions already asked (do not repeat): {prev_str}\n"
                f"{correction_line}"
                "Return only JSON: {\"questionText\": \"...\", \"expectedConcepts\": [\"...\"]}"
            )
            raw_text, model_used = self._call_llama(prompt)
            data = _extract_json(raw_text)
            question_text = _safe_str(data.get("questionText") or data.get("question"))

            if not question_text:
                correction = "The response did not contain a usable questionText."
                continue
            if _HR_FORBIDDEN_TOPIC.search(question_text):
                correction = "The question included a forbidden technical topic; write an HR follow-up only."
                logger.warning(f"[LLaMA] HR follow-up attempt {attempt + 1}/3 rejected: {correction}")
                continue
            if _is_duplicate_question(question_text, previous):
                correction = "The question repeated a previous question; choose a different HR follow-up."
                continue

            return {
                "questionText": question_text,
                "questionType": "follow_up",
                "subject": "follow_up",
                "difficulty": "medium",
                "category": "HR & Behavioral Follow-Up",
                "expectedConcepts": data.get("expectedConcepts") or (concepts or ["Response elaboration"]),
                "questionFormat": "theory",
                "modelUsed": model_used,
            }

            return {
                "questionText": question_text,
                "questionType": "follow_up",
                "subject": "follow_up",
                "difficulty": "medium",
                "category": "HR & Behavioral Follow-Up",
                "expectedConcepts": data.get("expectedConcepts") or (concepts or ["Response elaboration"]),
                "questionFormat": "theory",
            }

        raise AIGenerationUnavailableError(
            "The fine-tuned model did not produce a valid HR-only follow-up after three attempts."
        )

    # UNTRAINED TASK (no fine-tuning data)
    def evaluate_answer(self, question: str, answer: str, concepts: list, context: list, question_format: str = "theory", expected_output: str = None, explanation: str = None, test_cases: list = None, language: str = None, hr_delivery_metrics: dict = None, interview_type: str = "technical", schema: str = None, sample_data: str = None, reference_solution: str = None) -> dict:
        if question_format == "output_prediction":
            return self._evaluate_output_prediction(question, answer, concepts, expected_output, explanation)
        if question_format == "coding":
            return self._evaluate_coding_answer(question, answer, concepts, test_cases, language, explanation, schema=schema, sample_data=sample_data, reference_solution=reference_solution)

        # HR has its own evaluator (average of correctness/relevance/accuracy/communication).
        if (interview_type or "").lower() == "hr":
            return self._evaluate_hr_answer(question, answer, concepts, context, hr_delivery_metrics)

        # Java/DBMS theory: a bare list of terms is not an answer (see _is_bare_term_list).
        if _should_reject_term_list(question, answer):
            return _keyword_list_evaluation(concepts)

        from app.services.embedding_service import embedding_service

        expected_text = ", ".join(concepts) if concepts else question
        semantic_sim = embedding_service.compute_similarity(expected_text, answer)
        question_sim = embedding_service.compute_similarity(question, answer)
        semantic_relevance = max(semantic_sim, question_sim)
        # NOTE: The LLM model is only trained on this format after the Colab retrain.
        input_dict = {
            "interviewType": interview_type or "technical",
            "question": question,
            "answer": answer,
            "expectedConcepts": concepts or [],
            "questionFormat": question_format or "theory",
        }
        if explanation:
            input_dict["reference_answer"] = explanation
        if context:
            input_dict["context"] = context
        if hr_delivery_metrics:
            input_dict["hrDeliveryMetrics"] = hr_delivery_metrics

        prompt = build_training_style_prompt("evaluate_answer", input_dict)
        raw_text, model_used = self._call_llama(prompt, timeout=90, num_predict=1024, system=TRAINING_SYSTEM_PROMPT)
        parse_failed = False
        data = {}
        try:
            data = _extract_json(raw_text)
        except Exception as err:
            parse_failed = True
            logger.warning(f"[Evaluator] _extract_json failed on model response: {err}. Raw output: {raw_text[:200]!r}")

        required_fields = ["relevance", "correctness", "conceptCoverage", "communication"]
        missing_keys = [f for f in required_fields if f not in data or data[f] is None]
        if missing_keys and not parse_failed:
            parse_failed = True
            logger.warning(f"[Evaluator] Model response missing required evaluation keys: {missing_keys}. Using default fallback values.")

        try:
            llm_relevance = max(0.0, min(1.0, float(data.get("relevance", 0.5))))
        except (TypeError, ValueError):
            llm_relevance = 0.5
        raw_irrelevant = data.get("isIrrelevant", False)
        model_says_irrelevant = raw_irrelevant is True or str(raw_irrelevant).strip().lower() == "true"
        judgment_text = " ".join(
            str(data.get(field) or "")
            for field in ("feedback", "scoreReason", "weaknesses")
        ).lower()
        model_text_says_irrelevant = any(
            phrase in judgment_text
            for phrase in ("not relevant", "irrelevant", "unrelated", "off-topic", "does not address the question")
        )
        is_irrelevant = semantic_relevance < 0.30 and (
            model_says_irrelevant
            or model_text_says_irrelevant
            or llm_relevance < 0.20
        )
        if is_irrelevant:
            res = _irrelevant_text_evaluation()
            res["parseFailed"] = parse_failed
            return res

        # Prune any generic meta placeholders (like "java fundamentals") from concepts
        valid_concepts = [
            c for c in (concepts or [])
            if not any(g in str(c).lower() for g in ("fundamentals", "core concepts", "basic principles", "general"))
        ]

        is_keyword_dump = _looks_like_keyword_dump(answer, valid_concepts)
        missing_reported = _filter_to_current_question(data.get("missingConcepts") or [], valid_concepts)
        weaknesses = _filter_to_current_question(data.get("weaknesses") or [], valid_concepts)
        covered, partially_covered, missing_concepts = _classify_expected_concepts(
            valid_concepts,
            answer,
            embedding_service,
            (data.get("coveredConcepts") or []) + (data.get("strengths") or []),
            data.get("partiallyCoveredConcepts") or [],
            missing_reported,
            semantic_relevance,
        )
        if valid_concepts:
            concept_coverage = (len(covered) + 0.5 * len(partially_covered)) / len(valid_concepts)
        else:
            concept_coverage = _bounded_score(data.get("conceptCoverage"), semantic_relevance)

        correctness = _bounded_score(data.get("correctness"), 0.0)
        communication = _bounded_score(data.get("communication"), 0.75)
        if _is_fragmentary_answer(answer):
            communication = min(communication, 0.45)
        relevance = _bounded_score(0.75 * llm_relevance + 0.25 * semantic_relevance)
        if semantic_relevance < 0.30:
            relevance = min(relevance, semantic_relevance)
        if not _as_bool(data.get("demonstratesUnderstanding"), True):
            # Meaning-based judgement: terms present, understanding absent.
            correctness = min(correctness, 0.30)
            concept_coverage = min(concept_coverage, 0.30)
            relevance = min(relevance, 0.40)
            communication = min(communication, 0.45)
        if is_keyword_dump:
            correctness = min(correctness, 0.30)

        # Logical Coherence: An answer with high correctness cannot have 0% concept coverage
        if correctness >= 0.85:
            concept_coverage = max(concept_coverage, min(1.0, correctness * 0.95))
            if correctness >= 0.95:
                concept_coverage = max(concept_coverage, 1.0)
                missing_concepts = []
                weaknesses = [w for w in weaknesses if not any(g in str(w).lower() for g in ("fundamentals", "core concepts", "general"))]
        elif correctness >= 0.60:
            concept_coverage = max(concept_coverage, min(1.0, correctness * 0.80))

        if missing_concepts and correctness < 0.90:
            score_reason = (
                "You addressed the main topic, but some important concepts were missing: "
                + ", ".join(missing_concepts) + "."
            )
            feedback = _safe_str(data.get("feedback")) or score_reason
        elif is_keyword_dump:
            score_reason = (
                "The answer only lists relevant terms without explaining what they mean or how "
                "they apply, so it doesn't demonstrate real understanding."
            )
            feedback = "This lists relevant terms but does not explain what any of them mean or how they relate to the question."
        else:
            raw_score_reason = _safe_str(data.get("scoreReason"))
            if raw_score_reason and _score_reason_matches_question(raw_score_reason, question, valid_concepts):
                score_reason = raw_score_reason
            elif correctness >= 0.90:
                score_reason = "Your answer covered the required concepts accurately. Clear, well-explained response."
            else:
                score_reason = "Your answer covered the required concepts accurately. Improve any remaining depth or examples to make it more complete."
            feedback = _safe_str(data.get("feedback")) or score_reason

        deeper_concepts = data.get("deeperConcepts") or []
        improvement_suggestion = _safe_str(data.get("improvementSuggestion")) or None
        if improvement_suggestion and not _score_reason_matches_question(improvement_suggestion, question, valid_concepts):
            logger.warning(
                f"[Evaluator] improvementSuggestion didn't match the question, discarding: "
                f"{improvement_suggestion[:150]!r}"
            )
            deeper_concepts, improvement_suggestion = [], None
        elif not improvement_suggestion:
            deeper_concepts = []

        if not improvement_suggestion and missing_concepts and correctness < 0.90:
            improvement_suggestion = (
                "To improve your answer, explain " + ", ".join(missing_concepts) +
                " and connect those ideas directly to the question."
            )
        elif not improvement_suggestion and correctness >= 0.90:
            improvement_suggestion = "Great explanation! To make your answer even stronger, consider adding a practical real-world example."

        weaknesses = list(dict.fromkeys(missing_concepts + [w for w in weaknesses if not any(g in str(w).lower() for g in ("fundamentals", "core concepts", "general"))]))
        rounded_cov = round(float(concept_coverage), 2)
        rounded_corr = round(correctness, 2)
        rounded_rel = round(relevance, 2)
        rounded_comm = round(communication, 2)
        final_score = _calculate_text_score(
            rounded_rel, rounded_corr, rounded_cov, rounded_comm
        )

        return {
            "score": final_score,
            "conceptCoverage": rounded_cov,
            "correctness": rounded_corr,
            "relevance": rounded_rel,
            "communication": rounded_comm,
            "isIrrelevant": is_irrelevant,
            "feedback": feedback,
            "strengths": [] if is_keyword_dump or is_irrelevant else (data.get("strengths") or []),
            "weaknesses": [] if is_irrelevant else (["Answer is a list of terms, not an explanation"] if is_keyword_dump else weaknesses),
            "coveredConcepts": covered,
            "partiallyCoveredConcepts": partially_covered,
            "missingConcepts": missing_concepts,
            "deeperConcepts": deeper_concepts,
            "improvementSuggestion": improvement_suggestion,
            "scoreReason": score_reason,
            "modelUsed": model_used,
            "usedFallback": False,
            "parseFailed": parse_failed,
            "scoringSources": ["llm", "bert", "rules"],
        }

    def _evaluate_hr_answer(self, question: str, answer: str, concepts: list, context: list,
                            hr_delivery_metrics: dict = None) -> dict:
        """
        HR / behavioral grading with enhanced deterministic off-topic gating and calibrated scoring.
        """
        if not (answer or "").strip():
            return _not_related_hr_evaluation()

        from app.utils.hr_gate import is_off_topic, find_hr_item
        hr_item = find_hr_item(question)

        # 1. Deterministic Off-Topic Gate (0 score for completely irrelevant answers)
        if is_off_topic(question, answer):
            missing = list(hr_item["concepts"]) if hr_item and "concepts" in hr_item else (concepts or ["Context and situation for the question", "Concrete personal actions taken", "Quantifiable or tangible outcome", "Professional self-reflection and ownership"])
            return {
                "score": 0,
                "conceptCoverage": 0.0,
                "correctness": 0.0,
                "relevance": 0.0,
                "accuracy": 0.0,
                "communication": 0.0,
                "isIrrelevant": True,
                "feedback": "The response does not address the question asked, so no credit can be given.",
                "strengths": [],
                "weaknesses": ["The answer does not relate to the question that was asked"],
                "coveredConcepts": [],
                "partiallyCoveredConcepts": [],
                "missingConcepts": missing,
                "deeperConcepts": [],
                "improvementSuggestion": "Answer the question that was asked, using a specific example from your own experience.",
                "scoreReason": "The answer is not about this question; score 0.",
                "modelUsed": "hr_gate_filter",
                "usedFallback": False,
                "scoringSources": ["hr_gate", "rubric"],
            }

        if _should_reject_term_list(question, answer):
            return _not_related_hr_evaluation()

        from app.services.embedding_service import embedding_service

        effective_concepts = (hr_item.get("concepts") if hr_item else None) or concepts or []
        expected_text = ", ".join(effective_concepts) if effective_concepts else question
        semantic_relevance = max(
            embedding_service.compute_similarity(expected_text, answer),
            embedding_service.compute_similarity(question, answer),
        )
        input_dict = {
            "interviewType": "hr",
            "subject": "hr",
            "question": question,
            "answer": answer,
            "expectedConcepts": effective_concepts,
            "questionFormat": "theory",
        }
        if hr_item and hr_item.get("guidance"):
            input_dict["reference_answer"] = hr_item["guidance"]
        if context:
            input_dict["context"] = context
        if hr_delivery_metrics:
            input_dict["hrDeliveryMetrics"] = hr_delivery_metrics

        prompt = build_training_style_prompt("evaluate_answer", input_dict)
        chosen_model = getattr(self, "ft_model_name", settings.FINE_TUNED_MODEL_NAME) if getattr(settings, "USE_FT_HR", True) else getattr(self, "model_name", settings.MODEL_NAME)
        raw_text, model_used = self._call_llama(
            prompt,
            timeout=90,
            num_predict=1024,
            system=TRAINING_SYSTEM_PROMPT,
            model_override=chosen_model
        )
        data = _extract_json(raw_text)

        # Normalize fields in case model outputs alternate keys or boolean fields
        raw_feedback = data.get("feedback")
        if isinstance(raw_feedback, dict):
            feedback_str = raw_feedback.get("additionalFeedback") or raw_feedback.get("summary") or str(raw_feedback)
            if "relevant" in raw_feedback and "relevance" not in data:
                data["relevance"] = 0.95 if raw_feedback["relevant"] else 0.10
            if "correct" in raw_feedback and "correctness" not in data:
                data["correctness"] = 0.90 if raw_feedback["correct"] else 0.10
            if "relevantConcepts" in raw_feedback and "coveredConcepts" not in data:
                data["coveredConcepts"] = raw_feedback["relevantConcepts"]
            if "missingConcepts" in raw_feedback and "missingConcepts" not in data:
                data["missingConcepts"] = raw_feedback["missingConcepts"]
        else:
            feedback_str = str(raw_feedback or "").strip()

        if "relevance" not in data and "relevant" in data:
            data["relevance"] = 0.95 if data["relevant"] else 0.10
        if "correctness" not in data and "correct" in data:
            data["correctness"] = 0.90 if data["correct"] else 0.10

        if isinstance(data.get("correctness"), bool):
            data["correctness"] = 0.90 if data["correctness"] else 0.10
        if isinstance(data.get("relevance"), bool):
            data["relevance"] = 0.95 if data["relevance"] else 0.10

        llm_relevance = _bounded_score(data.get("relevance"), 0.5)
        addresses_question = _as_bool(data.get("addressesQuestion"), True)
        irrelevant_signal = (
            _as_bool(data.get("isIrrelevant"), False)
            or llm_relevance < 0.20
            or (not addresses_question and llm_relevance < 0.30)
        )
        if irrelevant_signal and semantic_relevance < 0.45:
            return _not_related_hr_evaluation()

        correctness = _bounded_score(data.get("correctness"), 0.0)
        if "accuracy" not in data or data.get("accuracy") in (0.0, None):
            accuracy = round(max(correctness * 0.95, min(1.0, semantic_relevance)), 2)
        else:
            accuracy = _bounded_score(data.get("accuracy"), 0.0)

        communication = _bounded_score(data.get("communication"), 0.75)
        if _is_fragmentary_answer(answer):
            communication = min(communication, 0.45)
        relevance = _bounded_score(0.75 * llm_relevance + 0.25 * semantic_relevance)
        if not addresses_question:
            relevance = min(relevance, 0.30)
            correctness = min(correctness, 0.30)
            accuracy = min(accuracy, 0.30)

        correctness, relevance, accuracy, communication = (
            round(v, 2) for v in (correctness, relevance, accuracy, communication)
        )
        
        # Use model score if provided and valid, otherwise compute via calculate_hr_overall
        model_score = data.get("score")
        if model_score is not None and isinstance(model_score, (int, float)) and 0 <= float(model_score) <= 100:
            score = int(round(float(model_score)))
        else:
            score = calculate_hr_overall(correctness, relevance, accuracy, communication)

        pct = lambda v: int(v * 100 + 0.5)
        breakdown = (
            f"Overall score is the average of correctness {pct(correctness)}%, relevance {pct(relevance)}%, "
            f"accuracy {pct(accuracy)}% and communication {pct(communication)}%."
        )
        llm_reason = str(data.get("scoreReason") or "").strip()

        return {
            "score": score,
            "conceptCoverage": accuracy,
            "correctness": correctness,
            "relevance": relevance,
            "accuracy": accuracy,
            "communication": communication,
            "isIrrelevant": False,
            "feedback": feedback_str or "Evaluation completed.",
            "strengths": [str(x) for x in (data.get("strengths") or data.get("coveredConcepts") or []) if x][:4],
            "weaknesses": [str(x) for x in (data.get("weaknesses") or []) if x][:4],
            "coveredConcepts": [str(x) for x in (data.get("coveredConcepts") or []) if x][:4],
            "partiallyCoveredConcepts": [],
            "missingConcepts": [str(x) for x in (data.get("missingConcepts") or []) if x][:4],
            "deeperConcepts": [],
            "improvementSuggestion": str(data.get("improvementSuggestion") or "").strip() or None,
            "scoreReason": f"{llm_reason} {breakdown}".strip(),
            "modelUsed": model_used,
            "usedFallback": False,
            "scoringSources": ["fine_tuned_llama", "bert", "rubric"],
        }

    def _evaluate_output_prediction(self, question: str, answer: str, concepts: list, expected_output: str, explanation: str = None) -> dict:
        norm = _canonical_output
        is_exact_match = bool(answer and answer.strip()) and norm(answer) == norm(expected_output)
        score = 100 if is_exact_match else 0
        feedback = (
            "Correct! Your predicted output exactly matches the actual output."
            if is_exact_match else
            f"Your predicted output does not match the actual output ('{expected_output}')."
        )
        score_reason = (
            "Full marks: your stated output matches the actual output exactly."
            if is_exact_match else
            f"The prediction is incorrect. The actual output is '{expected_output}', which does not match what you wrote ('{(answer or '').strip()}')."
        )
        weak_concepts = [] if is_exact_match else (concepts or [])

        return {
            "score": score,
            "conceptCoverage": round(score / 100.0, 2),
            "correctness": round(score / 100.0, 2),
            "relevance": 1.0,
            "communication": 0.8,
            "isIrrelevant": False,
            "feedback": feedback,
            "strengths": ["Correct output"] if is_exact_match else [],
            "weaknesses": [] if is_exact_match else weak_concepts,
            "missingConcepts": [] if is_exact_match else weak_concepts,
            "scoreReason": score_reason,
            "stepByStepExplanation": explanation or None,
            "modelUsed": getattr(self, "model_name", settings.MODEL_NAME),
            "usedFallback": False,
            "scoringSources": ["exact_match"],
        }

    def _analyze_code_complexity(self, question: str, code: str, lang: str = "java") -> dict:
        """
        Uses fine-tuned LLaMA to determine the Big-O Time Complexity and Space Complexity
        of the candidate's code with a concise explanation.
        """
        heuristic = _estimate_code_complexity_heuristic(code)
        if not code or not code.strip():
            return heuristic

        input_dict = {
            "language": (lang or "java").lower().strip(),
            "question": question or "Coding problem implementation",
            "code": code
        }
        prompt = build_training_style_prompt("analyze_code_complexity", input_dict)
        chosen_model = getattr(self, "ft_model_name", settings.FINE_TUNED_MODEL_NAME) if getattr(settings, "USE_FT_COMPLEXITY", True) else getattr(self, "model_name", settings.MODEL_NAME)
        try:
            raw_text, model_used = self._call_llama(
                prompt,
                timeout=45,
                num_predict=256,
                temperature=0.0,
                response_format="json",
                system=TRAINING_SYSTEM_PROMPT,
                model_override=chosen_model
            )
            data = _extract_json(raw_text)
            tc = _safe_str(data.get("timeComplexity"))
            sc = _safe_str(data.get("spaceComplexity"))
            exp = _safe_str(data.get("explanation"))
            if tc and ("O(" in tc or "o(" in tc):
                return {
                    "timeComplexity": tc,
                    "spaceComplexity": sc or heuristic["spaceComplexity"],
                    "explanation": exp or heuristic["explanation"],
                    "modelUsed": model_used,
                    "scoringSource": "fine_tuned_llama"
                }
            return heuristic
        except Exception as e:
            logger.warning(f"[ComplexityAnalysis] Fine-tuned model complexity analysis failed ({e}). Using heuristic fallback.")
            return heuristic

    def _evaluate_coding_answer(self, question: str, answer: str, concepts: list, test_cases: list, language: str = None, explanation: str = None, schema: str = None, sample_data: str = None, reference_solution: str = None) -> dict:
        from app.services.code_executor import execute_coding_submission, is_java_available

        lang = (language or "java").lower().strip()
        test_cases = test_cases or []

        # Check if deterministic sandbox execution is available
        can_execute_deterministically = (lang == "sql") or (lang == "java" and is_java_available())

        if not can_execute_deterministically:
            # Fall back to LLM judge at temperature 0
            return self._evaluate_coding_llm_fallback(question, answer, concepts, test_cases, lang, explanation)

        # Deterministic execution via sandbox
        exec_res = execute_coding_submission(
            language=lang,
            code=answer,
            test_cases=test_cases,
            schema=schema,
            reference_solution=reference_solution,
            sample_data=sample_data,
        )

        total_count = exec_res["totalCount"]
        passed_count = exec_res["passedCount"]
        compile_error = exec_res.get("compileError")

        # Compile error => 0 score. Otherwise score = round(100 * passed / total)
        if compile_error:
            final_score = 0
        else:
            final_score = round(100 * passed_count / total_count) if total_count > 0 else 0

        # LLaMA is used ONLY to write short feedback text AFTER the verdict is known (temperature 0)
        feedback, why_not_100, corrected_code, correction_summary = self._generate_coding_feedback(
            question=question,
            answer=answer,
            lang=lang,
            final_score=final_score,
            passed_count=passed_count,
            total_count=total_count,
            results=exec_res["results"],
            compile_error=compile_error,
            reference_solution=reference_solution,
        )

        complexity = None
        if lang == "java" and answer.strip() and not compile_error:
            complexity = self._analyze_code_complexity(question=question, code=answer, lang=lang)

        model_used = getattr(self, "model_name", settings.MODEL_NAME)
        return {
            "score": final_score,
            "passedCount": passed_count,
            "totalCount": total_count,
            "judgeMode": "deterministic",
            "testCaseResults": exec_res["results"],
            "feedback": feedback,
            "whyNot100": why_not_100,
            "scoreReason": why_not_100 or feedback,
            "correctedCode": corrected_code if final_score < 100 else None,
            "correctedQuery": corrected_code if (final_score < 100 and lang == "sql") else None,
            "correctionSummary": correction_summary if final_score < 100 else None,
            "compileError": compile_error,
            "timeComplexity": complexity.get("timeComplexity") if complexity else None,
            "spaceComplexity": complexity.get("spaceComplexity") if complexity else None,
            "timeComplexityExplanation": complexity.get("explanation") if complexity else None,
            # Strict constraint: theory metrics set to None for coding format
            "conceptCoverage": None,
            "correctness": None,
            "relevance": None,
            "communication": None,
            "strengths": ["Clean solution passing all test cases"] if final_score == 100 else [],
            "weaknesses": [] if final_score == 100 else [f"Failed {total_count - passed_count} test case(s)"],
            "missingConcepts": [],
            "stepByStepExplanation": explanation or None,
            "modelUsed": model_used,
            "usedFallback": False,
            "scoringSources": ["executor"],
        }

    def _generate_coding_feedback(self, question: str, answer: str, lang: str, final_score: int, passed_count: int, total_count: int, results: list, compile_error: str = None, reference_solution: str = None) -> tuple:
        if final_score == 100:
            return (
                "All test cases passed successfully! Clean and optimal solution.",
                None,  # whyNot100 must be None when 100%
                None,  # correctedCode must be None when 100%
                None
            )

        failed_cases = [r for r in results if r.get("status") != "PASSED"]
        failed_summary = "\n".join(
            f"- Case {r.get('id', i+1)} ({r.get('label') or 'test'}): expected={r.get('expected')!r}, got actual={r.get('actual')!r}, status={r.get('status')}"
            for i, r in enumerate(failed_cases[:4])
        )

        template_why_not_100 = (
            f"Solution failed {total_count - passed_count} of {total_count} test case(s). " +
            ("; ".join(f"Case {r.get('id', i+1)}: expected {r.get('expected')}, got {r.get('actual')}" for i, r in enumerate(failed_cases[:2])))
        ) if not compile_error else f"Code failed to compile: {compile_error.splitlines()[0]}"

        template_feedback = (
            f"Solution passed {passed_count} of {total_count} test cases."
            if not compile_error
            else "Code has compilation errors."
        )
        template_corrected = reference_solution or ""
        template_summary = "Address failing test cases and handle edge cases."

        prompt = (
            f"You are a technical coding interviewer reviewing a {lang.upper()} submission.\n"
            f"The deterministic code runner evaluated the code. DO NOT change the score ({final_score}%) or pass rate ({passed_count}/{total_count}).\n\n"
            f"Problem statement:\n{question}\n\n"
            f"Candidate's code:\n{answer}\n\n"
            f"Failed test cases:\n{failed_summary}\n"
            f"Compiler Error:\n{compile_error or 'None'}\n\n"
            f"Respond ONLY with a JSON object:\n"
            f'{{"feedback": "1-2 sentences on what failed and why", '
            f'"whyNot100": "Explain ONLY the failed cases using the real actual vs expected output above", '
            f'"correctedCode": "the candidate\'s own code with minimum edits to pass, or empty string", '
            f'"correctionSummary": "1-2 sentences explaining what was changed, or empty string"}}'
        )

        try:
            raw_text, _ = self._call_llama(prompt, timeout=60, num_predict=768, temperature=0.0, response_format="json")
            data = _extract_json(raw_text)
            feedback = _safe_str(data.get("feedback")) or template_feedback
            why_not_100 = _safe_str(data.get("whyNot100")) or template_why_not_100
            corrected_code = _safe_str(data.get("correctedCode")) or template_corrected
            correction_summary = _safe_str(data.get("correctionSummary")) or template_summary
            return feedback, why_not_100, corrected_code, correction_summary
        except Exception as e:
            logger.warning(f"[CodeFeedback] LLM feedback call failed ({e}). Using deterministic template.")
            return template_feedback, template_why_not_100, template_corrected, template_summary

    def _evaluate_coding_llm_fallback(self, question: str, answer: str, concepts: list, test_cases: list, language: str, explanation: str = None) -> dict:
        """Fallback judge when no JDK is available on the host machine. Runs at temperature 0."""
        cases_str = "\n".join(
            f"- Input: {tc.get('input', '')!r} -> Expected output: {tc.get('expectedOutput', '')!r}"
            for tc in test_cases
        ) or "No test cases were provided."
        concepts_str = ", ".join(concepts) if concepts else "general correctness"

        prompt = (
            f"You are the judge for a {language.upper()} coding problem. Grade the candidate's code.\n\n"
            f"Problem statement:\n{question}\n\n"
            f"Candidate's code:\n{answer}\n\n"
            f"Test cases:\n{cases_str}\n\n"
            f"Concepts: {concepts_str}\n\n"
            f"For EACH test case in order, determine if the code passes or fails.\n"
            f"Respond ONLY with JSON:\n"
            f'{{"testCaseResults": [{{"input": "...", "expectedOutput": "...", "actualOutput": "...", "passed": true, "failureReason": "..."}}], '
            f'"feedback": "1-2 sentences on what the code does right/wrong", '
            f'"whyNot100": "Explanation of failed cases, or empty string if all passed", '
            f'"correctedCode": "the fixed code or empty string"}}'
        )
        raw_text, model_used = self._call_llama(prompt, timeout=60, num_predict=1024, temperature=0.0, response_format="json")
        data = _extract_json(raw_text)

        raw_results = data.get("testCaseResults") or []
        results = []
        passed_count = 0
        for i, tc in enumerate(test_cases):
            r = raw_results[i] if i < len(raw_results) and isinstance(raw_results[i], dict) else {}
            passed = bool(r.get("passed", False))
            if passed:
                passed_count += 1
            failure_reason = _safe_str(r.get("failureReason")) or ("Test case failed" if not passed else "")
            results.append({
                "id": i + 1,
                "input": tc.get("input", ""),
                "expected": tc.get("expectedOutput", ""),
                "actual": _safe_str(r.get("actualOutput")),
                "status": "PASSED" if passed else "FAILED",
                "error": failure_reason if not passed else None,
                "passed": passed,
                "expectedOutput": tc.get("expectedOutput", ""),
                "actualOutput": _safe_str(r.get("actualOutput")),
                "failureReason": failure_reason if not passed else "",
                "label": tc.get("label"),
            })

        total_count = len(test_cases)
        final_score = round(100 * passed_count / total_count) if total_count > 0 else 0
        why_not_100 = None if final_score == 100 else (_safe_str(data.get("whyNot100")) or f"{total_count - passed_count} of {total_count} test cases failed.")

        complexity = None
        if (language or "java").lower() == "java" and answer.strip():
            complexity = self._analyze_code_complexity(question=question, code=answer, lang=language or "java")

        return {
            "score": final_score,
            "passedCount": passed_count,
            "totalCount": total_count,
            "judgeMode": "llm-fallback",
            "testCaseResults": results,
            "feedback": _safe_str(data.get("feedback")) or "Evaluation completed via LLM fallback.",
            "whyNot100": why_not_100,
            "scoreReason": why_not_100 or "All test cases passed.",
            "correctedCode": _safe_str(data.get("correctedCode")) if final_score < 100 else None,
            "correctedQuery": _safe_str(data.get("correctedCode")) if (final_score < 100 and language == "sql") else None,
            "correctionSummary": None,
            "compileError": None,
            "timeComplexity": complexity.get("timeComplexity") if complexity else None,
            "spaceComplexity": complexity.get("spaceComplexity") if complexity else None,
            "timeComplexityExplanation": complexity.get("explanation") if complexity else None,
            "conceptCoverage": None,
            "correctness": None,
            "relevance": None,
            "communication": None,
            "strengths": ["All test cases passed"] if final_score == 100 else [],
            "weaknesses": [] if final_score == 100 else [f"Failed {total_count - passed_count} test case(s)"],
            "missingConcepts": [],
            "stepByStepExplanation": explanation or None,
            "modelUsed": model_used,
            "usedFallback": True,
            "scoringSources": ["llm_fallback"],
        }
 

class DevFallbackModel(BaseAIModel):
    """
    Fallback provider used when the fine-tuned LLaMA/Ollama endpoint is
    unreachable.

    IMPORTANT: this class intentionally does NOT generate questions or
    follow-ups from a static bank/database. Every theory question, every
    "predict the output" snippet, and every follow-up must come from the
    fine-tuned LLaMA model itself. So when LLaMA can't be reached,
    generation fails loudly (AIGenerationUnavailableError).

    Answer evaluation is different: grading an answer the candidate already
    wrote is not "generation," so this class still provides a genuinely
    meaning-based (BERT semantic similarity) evaluator here, used whenever
    LLaMA is unavailable.
    """

    def generate_question(self, subject: str, difficulty: str, context: list, previous: list, question_format: str = "theory", interview_type: str = "technical") -> dict:
        raise AIGenerationUnavailableError(
            "Question generation requires the fine-tuned LLaMA model and no static "
            "question bank is used as a substitute. Make sure Ollama is running "
            "('ollama serve') with the configured model pulled, then check /health."
        )

    def generate_followup(self, question: str, answer: str, concepts: list, previous: list = None, interview_type: str = "technical") -> dict:
        raise AIGenerationUnavailableError(
            "Follow-up question generation requires the fine-tuned LLaMA model and no "
            "static follow-up bank is used as a substitute. Make sure Ollama is running "
            "('ollama serve') with the configured model pulled, then check /health."
        )

    def evaluate_answer(self, question: str, answer: str, concepts: list, context: list, question_format: str = "theory", expected_output: str = None, explanation: str = None, test_cases: list = None, language: str = None, hr_delivery_metrics: dict = None, interview_type: str = "technical", schema: str = None, sample_data: str = None, reference_solution: str = None) -> dict:
        if question_format == "output_prediction":
            return self._evaluate_output_prediction_fallback(answer, concepts, expected_output, explanation)
        if question_format == "coding":
            return self._evaluate_coding_fallback(answer, concepts, test_cases, explanation, language=language, schema=schema, sample_data=sample_data, reference_solution=reference_solution)
        if (interview_type or "").lower() == "hr":
            return self._evaluate_hr_fallback(question, answer, concepts)

        from app.services.embedding_service import embedding_service

        length = len(answer.strip())
        if length == 0:
            return {
                "score": 0,
                "conceptCoverage": 0.0,
                "correctness": 0.0,
                "relevance": 0.0,
                "communication": 0.0,
                "feedback": "No response provided. Attempting to answer every question is essential for interview practice.",
                "strengths": [],
                "weaknesses": ["Skipped response"],
                "missingConcepts": concepts or ["Core concepts"],
                "scoreReason": "You scored 0% instead of 100% because no answer was submitted.",
            }

        if _should_reject_term_list(question, answer):
            return _keyword_list_evaluation(concepts)

        matched, partially_covered, missing = _classify_expected_concepts(
            concepts, answer, embedding_service
        )
        coverage = (
            (len(matched) + 0.5 * len(partially_covered)) / len(concepts)
            if concepts else 0.75
        )

        overall_sim = embedding_service.compute_similarity(
            ", ".join(concepts) if concepts else question, answer
        )
        question_sim = embedding_service.compute_similarity(question, answer)
        semantic_relevance = max(overall_sim, question_sim)
        is_irrelevant = semantic_relevance < 0.16
        if is_irrelevant:
            return _irrelevant_text_evaluation()

        is_keyword_dump = _looks_like_keyword_dump(answer, concepts)
        relevance = semantic_relevance
        correctness = coverage
        communication = 0.8 if length > 50 else 0.6
        if is_keyword_dump:
            correctness = min(correctness, 0.3)
        score = _calculate_text_score(relevance, correctness, coverage, communication)

        if is_keyword_dump:
            fb = "This lists relevant terms but does not explain what any of them mean or how they relate to the question."
            strengths = []
            weaknesses = ["Answer is a list of terms, not an explanation"]
        elif score >= 75:
            fb = "Strong explanation covering key principles."
            strengths = ["Clear conceptual explanation", "Structured communication"]
            weaknesses = [f"Could say more about: {', '.join(missing[:2])}"] if missing else \
                ["Could include additional practical examples"]
        elif score >= 50:
            fb = "Satisfactory answer covering basic definitions. Specific examples would make the explanation easier to understand."
            strengths = ["Correct basic definition"]
            weaknesses = [f"Did not cover: {c}" for c in missing[:2]] if missing else \
                ["Answer is brief", "Missing deeper edge case details"]
        else:
            fb = "The answer touches on the topic but is missing several expected points." if matched else \
                "Brief or off-target response. Expanding on key terms and structured examples will significantly improve score."
            strengths = [f"Covered: {c}" for c in matched[:2]] or ["Attempted question"]
            weaknesses = [f"Did not cover: {c}" for c in missing[:3]] if missing else \
                ["Incomplete answer", "Lacks structural detail"]

        return {
            "score": score,
            "conceptCoverage": 0.0 if is_irrelevant else round(coverage, 2),
            "correctness": round(correctness, 2),
            "relevance": round(relevance, 2),
            "communication": round(communication, 2),
            "isIrrelevant": False,
            "feedback": fb,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "coveredConcepts": matched,
            "partiallyCoveredConcepts": partially_covered,
            "missingConcepts": missing,
            "improvementSuggestion": (
                "Provide an answer that directly addresses the question."
                if is_irrelevant else
                f"To improve your answer, explain {', '.join(missing)} and connect those ideas directly to the question."
                if missing else None
            ),
            "scoreReason": (
                "The answer is unrelated to the question."
                if is_irrelevant else
                "The answer only lists relevant terms without explaining what they mean or how "
                "they apply, so it doesn't demonstrate real understanding."
                if is_keyword_dump else _build_score_reason(score, missing, weaknesses)
            ),
        }

    def _evaluate_hr_fallback(self, question: str, answer: str, concepts: list) -> dict:
        """Offline HR grader (LLaMA unavailable): same HR average, embedding-based inputs."""
        from app.services.embedding_service import embedding_service

        text = (answer or "").strip()
        if not text:
            return {
                "score": 0, "conceptCoverage": 0.0, "correctness": 0.0, "relevance": 0.0,
                "accuracy": 0.0, "communication": 0.0, "isIrrelevant": False,
                "feedback": "No response provided.", "strengths": [], "weaknesses": ["Skipped response"],
                "missingConcepts": concepts or [], "scoreReason": "Score is 0% because no answer was submitted.",
            }
        if _should_reject_term_list(question, text):
            return _not_related_hr_evaluation()

        overall_sim = embedding_service.compute_similarity(", ".join(concepts) if concepts else question, text)
        question_sim = embedding_service.compute_similarity(question, text)
        semantic_relevance = max(overall_sim, question_sim)
        if semantic_relevance < 0.16:
            return _not_related_hr_evaluation()

        matched, partially_covered, missing = _classify_expected_concepts(concepts, text, embedding_service)
        coverage = (len(matched) + 0.5 * len(partially_covered)) / len(concepts) if concepts else 0.75
        clamp = lambda v: round(max(0.0, min(1.0, v)), 2)
        relevance = clamp(semantic_relevance)
        correctness = clamp(coverage)
        accuracy = clamp(overall_sim)
        communication = 0.8 if len(text) > 50 else 0.6
        score = calculate_hr_overall(correctness, relevance, accuracy, communication)
        pct = lambda v: int(v * 100 + 0.5)

        return {
            "score": score,
            "conceptCoverage": accuracy,
            "correctness": correctness,
            "relevance": relevance,
            "accuracy": accuracy,
            "communication": communication,
            "isIrrelevant": False,
            "feedback": "Answer assessed with the offline grader.",
            "strengths": [f"Covered: {c}" for c in matched[:2]] or ["Attempted the question"],
            "weaknesses": [f"Did not cover: {c}" for c in missing[:2]],
            "coveredConcepts": matched,
            "partiallyCoveredConcepts": partially_covered,
            "missingConcepts": missing,
            "scoreReason": (
                f"Overall score is the average of correctness {pct(correctness)}%, relevance {pct(relevance)}%, "
                f"accuracy {pct(accuracy)}% and communication {pct(communication)}%."
            ),
        }

    def _evaluate_output_prediction_fallback(self, answer: str, concepts: list, expected_output: str, explanation: str = None) -> dict:
        norm = _canonical_output
        given = norm(answer)
        expected = norm(expected_output)
        concept_list = concepts or []

        if not given:
            return {
                "score": 0, "conceptCoverage": 0.0, "correctness": 0.0, "relevance": 0.0, "communication": 0.0,
                "feedback": "No output was submitted.",
                "strengths": [], "weaknesses": concept_list, "missingConcepts": concept_list,
                "scoreReason": "You scored 0% instead of 100% because no output was submitted.",
                "stepByStepExplanation": explanation,
            }

        if given == expected:
            return {
                "score": 100, "conceptCoverage": 1.0, "correctness": 1.0, "relevance": 1.0, "communication": 1.0,
                "feedback": "Correct! Your predicted output exactly matches the actual output.",
                "strengths": ["Exact output match"], "weaknesses": [], "missingConcepts": [],
                "scoreReason": "Full marks: your stated output matches the actual output exactly.",
                "stepByStepExplanation": explanation,
            }

        return {
            "score": 0,
            "conceptCoverage": 0.0,
            "correctness": 0.0,
            "relevance": 0.0,
            "communication": 0.0,
            "feedback": f"Your predicted output doesn't match the actual output ('{expected_output}').",
            "strengths": [],
            "weaknesses": concept_list,
            "missingConcepts": concept_list,
            "scoreReason": (
                f"You scored 0% instead of 100% because the code actually outputs "
                f"'{expected_output}', which doesn't exactly match what you wrote ('{answer.strip()}'). "
                + (f"This question was testing: {', '.join(concept_list)}." if concept_list else "")
            ),
            "stepByStepExplanation": explanation,
        }

    def _evaluate_coding_fallback(self, answer: str, concepts: list, test_cases: list, explanation: str = None, language: str = None, schema: str = None, sample_data: str = None, reference_solution: str = None) -> dict:
        """
        Offline grading when LLaMA is unreachable. If a runtime/sandbox is available
        (SQL or Java with JDK installed), execute code deterministically against test cases.
        Otherwise provide an offline estimate marked with judgeMode="llm-fallback".
        """
        from app.services.code_executor import execute_coding_submission, is_java_available

        lang = (language or "java").lower().strip()
        code = (answer or "").strip()
        test_cases = test_cases or []

        if not code:
            return {
                "score": 0, "conceptCoverage": None, "correctness": None, "relevance": None, "communication": None,
                "passedCount": 0, "totalCount": len(test_cases),
                "judgeMode": "deterministic" if ((lang == "sql") or (lang == "java" and is_java_available())) else "llm-fallback",
                "feedback": "No submission was made.",
                "whyNot100": "No code was submitted for evaluation.",
                "strengths": [], "weaknesses": ["No submission made"], "missingConcepts": [],
                "scoreReason": "Score is 0% because nothing was submitted.",
                "stepByStepExplanation": explanation,
                "testCaseResults": [
                    {"id": i + 1, "input": tc.get("input", ""), "expected": tc.get("expectedOutput", ""),
                     "actual": "None", "status": "FAILED", "error": "No code submitted"}
                    for i, tc in enumerate(test_cases)
                ],
            }

        can_execute_deterministically = (lang == "sql") or (lang == "java" and is_java_available())
        if can_execute_deterministically:
            exec_res = execute_coding_submission(
                language=lang,
                code=code,
                test_cases=test_cases,
                schema=schema,
                reference_solution=reference_solution,
                sample_data=sample_data,
            )
            total_count = exec_res["totalCount"]
            passed_count = exec_res["passedCount"]
            compile_error = exec_res.get("compileError")
            if compile_error:
                final_score = 0
            else:
                final_score = round(100 * passed_count / total_count) if total_count > 0 else 0

            why_not_100 = None if final_score == 100 else f"Failed {total_count - passed_count} of {total_count} test cases."
            feedback = "All test cases passed successfully." if final_score == 100 else f"{passed_count} of {total_count} test cases passed."
            complexity = _estimate_code_complexity_heuristic(code) if lang == "java" and code and not compile_error else None
            return {
                "score": final_score,
                "passedCount": passed_count,
                "totalCount": total_count,
                "judgeMode": "deterministic",
                "testCaseResults": exec_res["results"],
                "feedback": feedback,
                "whyNot100": why_not_100,
                "scoreReason": why_not_100 or feedback,
                "correctedCode": None,
                "compileError": compile_error,
                "timeComplexity": complexity.get("timeComplexity") if complexity else None,
                "spaceComplexity": complexity.get("spaceComplexity") if complexity else None,
                "timeComplexityExplanation": complexity.get("explanation") if complexity else None,
                "conceptCoverage": None,
                "correctness": None,
                "relevance": None,
                "communication": None,
                "strengths": ["Clean solution passing all test cases"] if final_score == 100 else [],
                "weaknesses": [] if final_score == 100 else [f"Failed {total_count - passed_count} test case(s)"],
                "missingConcepts": [],
                "stepByStepExplanation": explanation,
                "modelUsed": "deterministic_executor",
                "usedFallback": False,
                "scoringSources": ["executor"],
            }

        # Offline fallback when no execution runtime is present
        from app.services.embedding_service import embedding_service
        sim = embedding_service.compute_similarity(explanation or ", ".join(concepts or []), code)
        has_return_or_output = bool(re.search(r"\b(return|print|System\.out|console\.log|SELECT|select)\b", code))
        score = int(round(sim * 60)) + (10 if has_return_or_output else 0)
        score = max(0, min(75, score))
        complexity = _estimate_code_complexity_heuristic(code) if lang == "java" and code else None

        return {
            "score": score,
            "passedCount": 0,
            "totalCount": len(test_cases),
            "judgeMode": "llm-fallback",
            "conceptCoverage": None,
            "correctness": None,
            "relevance": None,
            "communication": None,
            "feedback": "Java runtime is not installed on this system. Grading performed via offline fallback mode.",
            "whyNot100": "Graded using fallback estimator because JDK is not installed.",
            "strengths": [] if score < 40 else ["Structure resembles a plausible approach"],
            "weaknesses": concepts or [],
            "missingConcepts": [],
            "scoreReason": "Offline estimate: Java runtime not detected.",
            "timeComplexity": complexity.get("timeComplexity") if complexity else None,
            "spaceComplexity": complexity.get("spaceComplexity") if complexity else None,
            "timeComplexityExplanation": complexity.get("explanation") if complexity else None,
            "testCaseResults": [
                {"id": i + 1, "input": tc.get("input", ""), "expected": tc.get("expectedOutput", ""),
                 "actual": "(not executed -- JDK unavailable)", "status": "FAILED",
                 "error": "JDK unavailable for execution"}
                for i, tc in enumerate(test_cases)
            ],
            "stepByStepExplanation": explanation,
            "modelUsed": "offline_fallback",
            "usedFallback": True,
            "scoringSources": ["fallback"],
        }


class ResilientAIModel(BaseAIModel):
    """
    Question/follow-up GENERATION always goes through the real fine-tuned
    LLaMA/Ollama provider, with no static-bank fallback -- this is
    unconditional (not gated by STRICT_AI_MODE). If LLaMA is unreachable or
    returns something unusable, the failure is raised as
    AIGenerationUnavailableError.

    Answer EVALUATION keeps the resilience switch: LLaMA is tried first.
    Default (STRICT_AI_MODE=false): on failure, evaluation falls back to
    DevFallbackModel's BERT semantic-similarity grader. STRICT_AI_MODE=true
    disables that fallback too.
    """

    def __init__(self):
        self.llama = LlamaModel()
        self.fallback = DevFallbackModel()

    def generate_question(self, subject: str, difficulty: str, context: list, previous: list, question_format: str = "theory", interview_type: str = "technical") -> dict:
        try:
            return self.llama.generate_question(subject, difficulty, context, previous, question_format, interview_type)
        except Exception as e:
            logger.error(f"[LLaMA] generate_question failed: {e}")
            raise AIGenerationUnavailableError(
                "Could not generate a question from the fine-tuned LLaMA model. Make sure "
                "Ollama is running ('ollama serve') with the configured model pulled, then "
                f"check /health. Underlying error: {e}"
            ) from e

    def generate_followup(self, question: str, answer: str, concepts: list, previous: list = None, interview_type: str = "technical") -> dict:
        try:
            return self.llama.generate_followup(question, answer, concepts, previous, interview_type)
        except Exception as e:
            logger.error(f"[LLaMA] generate_followup failed: {e}")
            raise AIGenerationUnavailableError(
                "Could not generate a follow-up question from the fine-tuned LLaMA model. "
                "Make sure Ollama is running ('ollama serve') with the configured model "
                "pulled, then check /health."
            ) from e

    def evaluate_answer(self, question: str, answer: str, concepts: list, context: list, question_format: str = "theory", expected_output: str = None, explanation: str = None, test_cases: list = None, language: str = None, hr_delivery_metrics: dict = None, interview_type: str = "technical", schema: str = None, sample_data: str = None, reference_solution: str = None) -> dict:
        try:
            return self.llama.evaluate_answer(question, answer, concepts, context, question_format, expected_output, explanation, test_cases, language, hr_delivery_metrics, interview_type, schema=schema, sample_data=sample_data, reference_solution=reference_solution)
        except Exception as e:
            if settings.STRICT_AI_MODE:
                logger.error(f"[LLaMA] evaluate_answer failed: {e}")
                raise AIGenerationUnavailableError(
                    f"Could not evaluate answer using fine-tuned LLaMA model '{self.llama.model_name}'. "
                    f"Ensure Ollama is running ('ollama serve') with fine-tuned model '{self.llama.model_name}' created. "
                    "Fallback evaluation is disabled to enforce fine-tuned model inference."
                ) from e
            logger.warning(f"[LLaMA] evaluate_answer failed: {e}. Falling back to offline fallback model.")
            return self.fallback.evaluate_answer(question, answer, concepts, context, question_format, expected_output, explanation, test_cases, language, hr_delivery_metrics, interview_type, schema=schema, sample_data=sample_data, reference_solution=reference_solution)


def get_ai_model_provider() -> BaseAIModel:
    return ResilientAIModel()