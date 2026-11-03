import json
import os
import sys

# Ensure app is in path
sys.path.insert(0, os.path.abspath("ai-service"))

from app.models.llama_provider import _THEORY_ITEMS_LIST, find_theory_item

with open("ai-service/tests/data/paraphrase_answers.json", "r", encoding="utf-8") as f:
    items = json.load(f)

# 1. Update java-theory-001 wrong answer with exact user quote
items[0]["answers"]["wrong"] = "encapsulation means making a class inside another class so it is hidden, it is useful becoz then you dont need constructors"

# 2. Define reversed answers for all 50 items
reversed_answers = {
    "java-theory-001": "Encapsulation means making all class fields public and methods private so outside code can directly modify internal variables without getters or setters.",
    "java-theory-002": "An object is the blueprint written in source code, while a class is the runtime instance created in heap memory using new.",
    "java-theory-003": "Inheritance allows a superclass to inherit all properties and methods from its child subclass using the implements keyword.",
    "java-theory-004": "Method overloading is runtime polymorphism where a subclass overrides a parent method, while method overriding is compile time polymorphism within the same class.",
    "java-theory-005": "Abstraction exposes the internal background implementation details to the user and hides the public interfaces.",
    "java-theory-006": "Overloading is resolved dynamically at runtime in subclasses with identical parameters, while overriding is resolved at compile time in the same class.",
    "java-theory-007": "A constructor is called when an object is destroyed to clean up memory, and it must have a return type like void or int.",
    "java-theory-008": "The this keyword refers to the parent superclass methods, while super refers to the current class instance variables.",
    "java-theory-009": "A class can extend multiple abstract classes, but can only implement a single interface, and interfaces contain constructors.",
    "java-theory-010": "Java allows multiple inheritance of classes because the diamond problem creates no ambiguity, while interfaces are banned because they carry mutable state.",
    "java-theory-011": "Private is the most open modifier accessible everywhere, while public is strictly restricted to only within the declaring class.",
    "java-theory-012": "A final variable can be reassigned freely anywhere, a final method must be overridden by all subclasses, and a final class is designed to be inherited.",
    "java-theory-013": "Inheritance provides weak loose coupling while composition tightly couples classes through fragile base class dependencies.",
    "java-theory-014": "Default methods break backward compatibility by forcing all existing implementing classes to rewrite their code.",
    "java-theory-015": "Static members belong to individual object instances created with new, whereas instance members are shared globally by the class.",
    "java-theory-016": "ArrayList is backed by doubly linked node pointers, while LinkedList is backed by a contiguous fixed-size primitive array.",
    "java-theory-017": "HashMap is synchronized and thread-safe forbidding null keys, while Hashtable is unsynchronized and allows null keys.",
    "java-theory-018": "HashSet keeps elements in sorted natural order using red-black trees, while TreeSet uses hash buckets with no ordering guarantees.",
    "java-theory-019": "Comparable defines external comparison logic with compare(o1, o2), whereas Comparator defines natural internal ordering inside the class with compareTo.",
    "java-theory-081": "generics let you store any type in one list together like int and String mixed, raw objects only allow one type",
    "dbms-theory-001": "A primary key allows multiple duplicate records and permits NULL values across every column in the table.",
    "dbms-theory-002": "A foreign key creates primary values in a child table that have no relation or reference to any parent table.",
    "dbms-theory-003": "A candidate key is a column that contains non-unique duplicate values and cannot be chosen as a primary key.",
    "dbms-theory-004": "A composite key is strictly a single single-column key that cannot combine multiple attributes.",
    "dbms-theory-005": "A super key is a minimal set of attributes that cannot have any extra unnecessary columns added to it.",
    "dbms-theory-006": "A primary key allows multiple NULL values per table, whereas a unique key can only exist once per database and permits no NULLs.",
    "dbms-theory-007": "A NULL value in a database represents the number zero or an empty string, and equals another NULL with = operator.",
    "dbms-theory-008": "An entity set is a single real-world object, while an entity is a collection of all similar tables in a database.",
    "dbms-theory-009": "A strong entity depends on a foreign owner table for its primary key, while a weak entity has its own independent primary key.",
    "dbms-theory-010": "A one-to-one relationship means one row in table A relates to infinite rows in table B and vice versa without restrictions.",
    "dbms-theory-011": "A many-to-many relationship is implemented by adding direct foreign keys between the two tables without using any junction table.",
    "dbms-theory-012": "A derived attribute is physically stored on disk, whereas a stored attribute is computed dynamically by queries at runtime.",
    "dbms-theory-013": "Generalization is a top-down process dividing entities into subclasses, while specialization is bottom-up combining entities into a superclass.",
    "dbms-theory-014": "A relationship in an ER model represents the data types of columns, not any association between entities.",
    "dbms-theory-015": "Inserting duplicate values into a primary key succeeds silently and replaces existing rows without throwing any constraint errors.",
    "dbms-theory-016": "Normalization increases data redundancy and duplication to maximize insertion and deletion anomalies in relational tables.",
    "dbms-theory-017": "First normal form allows composite attributes and repeating groups of comma-separated multiple values in a single column.",
    "dbms-theory-018": "Second normal form permits partial dependencies where non-key attributes depend only on a subset of the candidate key.",
    "dbms-theory-019": "Third normal form requires non-prime attributes to have transitive dependencies on the primary key through another non-key column.",
    "dbms-theory-020": "BCNF is a weaker normal form than 3NF that allows functional dependencies where the left side is not a super key.",
    "fu-01": "ArithmeticException is a checked exception that requires a mandatory try-catch block, while IOException is unchecked and ignored at compile time.",
    "fu-02": "If two objects are equal according to equals(), their hashCode() values must be completely different to prevent hash collisions.",
    "fu-03": "ConcurrentHashMap ensures thread safety by placing a single global synchronized lock over the entire table for all reads and writes.",
    "fu-04": "Using the plus operator for string concatenation inside a loop modifies the string in-place on the stack with O(1) time and zero garbage collection.",
    "fu-05": "Volatile makes compound operations like i++ completely atomic and thread-safe without needing any synchronization.",
    "fu-06": "A composite index ordered by column A then column B performs fastest when queries filter only on column B and omit column A.",
    "fu-07": "A dirty read occurs when reading committed data, while a non-repeatable read happens when reading uncommitted changes that roll back.",
    "fu-08": "Binary search trees are better than B+ trees for disk storage because their deep tree structure maximizes the number of disk I/O operations.",
    "fu-09": "The N+1 problem is solved by issuing N separate individual queries instead of joining tables or eager loading in one query.",
    "fu-10": "Write-ahead logging writes database data pages to disk first, and only writes log records if the server does not crash."
}

# Replace java-theory-020 (item 19) with java-theory-081
items[19] = {
    "questionId": "java-theory-081",
    "question": "What is the benefit of using generics instead of raw Object types in collections?",
    "answers": {
        "good": "Generics allow you to specify the exact type of objects stored in a collection like List<String>, enabling the compiler to detect type mismatches at compile time rather than failing with ClassCastExceptions at runtime, and avoiding the need for manual type casting.",
        "partial": "Generics provide compile time type safety so you don't need manual casting and avoid runtime ClassCastExceptions.",
        "wrong": "Generics are used to compress collections into zip archives so they use less memory on disk.",
        "reversed": "generics let you store any type in one list together like int and String mixed, raw objects only allow one type",
        "vague": "Generics are used with Java collections."
    }
}

# Attach reversed to all items
for item in items:
    qid = item["questionId"]
    if qid in reversed_answers:
        item["answers"]["reversed"] = reversed_answers[qid]
    else:
        print(f"MISSING REVERSED FOR {qid}!")

# Verify all 50 items have 5 answers
for i, item in enumerate(items):
    qid = item["questionId"]
    ans = item["answers"]
    for k in ["good", "partial", "wrong", "reversed", "vague"]:
        assert k in ans, f"Item {i} ({qid}) missing answer key {k}"
        assert len(ans[k].strip()) > 0, f"Item {i} ({qid}) empty answer key {k}"

with open("ai-service/tests/data/paraphrase_answers.json", "w", encoding="utf-8") as f:
    json.dump(items, f, indent=2)

print(f"Successfully updated ai-service/tests/data/paraphrase_answers.json with 50 items x 5 answers!")
