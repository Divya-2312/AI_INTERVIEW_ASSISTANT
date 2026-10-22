# Java Theory Topic Catalogue

Total Topics: 100 | Status: Needs Human Review (`needs_human_review: true`)

| ID | Difficulty | Category | Question | Expected Concepts |
|---|---|---|---|---|
| java-theory-001 | Easy | OOP | What is encapsulation in Java and why is it useful? | encapsulation, access modifiers, data hiding |
| java-theory-002 | Easy | OOP | What is the difference between a class and an object? | class, object, instantiation |
| java-theory-003 | Easy | OOP | What is inheritance in Java? | inheritance, extends, code reuse |
| java-theory-004 | Medium | OOP | What is polymorphism, and what are its two types in Java? | polymorphism, overloading, overriding, dynamic dispatch |
| java-theory-005 | Medium | OOP | What is abstraction, and how is it achieved in Java? | abstraction, abstract class, interface |
| java-theory-006 | Medium | OOP | What is the difference between method overloading and method overriding? | overloading, overriding, polymorphism |
| java-theory-007 | Easy | OOP | What is the purpose of a constructor in Java? | constructor, initialization |
| java-theory-008 | Medium | OOP | What is the difference between `this` and `super` keywords? | this keyword, super keyword |
| java-theory-009 | Medium | OOP | What is the difference between an abstract class and an interface? | abstract class, interface, multiple inheritance |
| java-theory-010 | Hard | OOP | Why doesn't Java support multiple inheritance of classes, and how do interfaces work around this? | diamond problem, multiple inheritance, interfaces |
| java-theory-011 | Easy | OOP | What are access modifiers in Java and what are the four types? | access modifiers, private, protected, public, default |
| java-theory-012 | Medium | OOP | What does the `final` keyword mean when applied to a class, method, and variable? | final keyword, immutability |
| java-theory-013 | Medium | OOP | What is composition, and why is 'favor composition over inheritance' good advice? | composition, inheritance, coupling |
| java-theory-014 | Hard | OOP | What are default methods in interfaces, and why were they introduced in Java 8? | default methods, interface evolution, Java 8 |
| java-theory-015 | Medium | OOP | What is the difference between static and instance members? | static, instance members, class-level state |
| java-theory-016 | Easy | Collections | What is the difference between ArrayList and LinkedList? | ArrayList, LinkedList, time complexity |
| java-theory-017 | Medium | Collections | What is the difference between HashMap and Hashtable? | HashMap, Hashtable, thread safety |
| java-theory-018 | Medium | Collections | What is the difference between HashSet and TreeSet? | HashSet, TreeSet, ordering |
| java-theory-019 | Medium | Collections | What is the difference between Comparable and Comparator? | Comparable, Comparator, sorting |
| java-theory-020 | Hard | Collections | What is a ConcurrentModificationException and when does it occur? | ConcurrentModificationException, fail-fast iterator |
| java-theory-021 | Hard | Collections | What is the difference between fail-fast and fail-safe iterators? | fail-fast, fail-safe, iterator |
| java-theory-022 | Hard | Collections | How does HashMap work internally in Java? | hashCode, buckets, collision resolution |
| java-theory-023 | Medium | Collections | Why must a class override both equals() and hashCode() together? | equals contract, hashCode contract |
| java-theory-024 | Easy | Collections | What is an Iterator and how is it used? | Iterator, hasNext, next |
| java-theory-025 | Medium | Collections | What is a Deque and what makes it useful? | Deque, double-ended queue |
| java-theory-026 | Medium | Collections | What is a PriorityQueue and how does it order elements? | PriorityQueue, heap, natural ordering |
| java-theory-027 | Easy | Collections | What is the difference between the Collection and Collections types? | Collection interface, Collections utility class |
| java-theory-028 | Hard | Collections | What is a bounded wildcard, and what's the difference between `? extends T` and `? super T`? | generics, wildcards, PECS |
| java-theory-029 | Medium | Collections | How do you make a collection thread-safe in Java? | thread safety, Collections.synchronizedList, concurrent collections |
| java-theory-030 | Medium | Collections | What is the difference between List, Set, and Map? | List, Set, Map |
| java-theory-031 | Hard | Collections | What is the difference between TreeMap and LinkedHashMap in terms of ordering? | TreeMap, LinkedHashMap, ordering |
| java-theory-032 | Easy | Exceptions | What is the difference between checked and unchecked exceptions? | checked exceptions, unchecked exceptions, RuntimeException |
| java-theory-033 | Easy | Exceptions | What is the purpose of the finally block? | try-catch-finally, cleanup |
| java-theory-034 | Medium | Exceptions | What is the difference between throw and throws? | throw, throws |
| java-theory-035 | Medium | Exceptions | How do you create a custom exception in Java? | custom exception, extends Exception |
| java-theory-036 | Medium | Exceptions | What is try-with-resources and why is it useful? | try-with-resources, AutoCloseable |
| java-theory-037 | Hard | Exceptions | What is the difference between finally and finalize()? | finally, finalize |
| java-theory-038 | Medium | Exceptions | Can you catch multiple exception types in one catch block? | multi-catch, pipe syntax |
| java-theory-039 | Hard | Exceptions | What is the Java exception class hierarchy? | Throwable, Exception, Error |
| java-theory-040 | Medium | Exceptions | What commonly causes a NullPointerException? | NullPointerException, null reference |
| java-theory-041 | Hard | Exceptions | What is the difference between StackOverflowError and OutOfMemoryError? | StackOverflowError, OutOfMemoryError |
| java-theory-042 | Easy | Multithreading | What is the difference between a process and a thread? | process, thread |
| java-theory-043 | Medium | Multithreading | What is the difference between extending Thread and implementing Runnable? | Thread class, Runnable interface |
| java-theory-044 | Medium | Multithreading | What does the synchronized keyword do? | synchronized, monitor lock, mutual exclusion |
| java-theory-045 | Hard | Multithreading | What does the volatile keyword guarantee, and what doesn't it guarantee? | volatile, visibility, atomicity |
| java-theory-046 | Hard | Multithreading | What is a deadlock, and how can it be avoided? | deadlock, lock ordering |
| java-theory-047 | Medium | Multithreading | What is the Executor framework and why is it preferred over manually creating threads? | ExecutorService, thread pool |
| java-theory-048 | Medium | Multithreading | What is the difference between Runnable and Callable? | Runnable, Callable, Future |
| java-theory-049 | Hard | Multithreading | What is the difference between wait()/notify() and Condition (from Lock)? | wait/notify, Condition, Lock |
| java-theory-050 | Hard | Multithreading | What is the difference between synchronized and ReentrantLock? | synchronized, ReentrantLock |
| java-theory-051 | Medium | Multithreading | What are atomic classes like AtomicInteger used for? | AtomicInteger, compare-and-swap, lock-free |
| java-theory-052 | Easy | Multithreading | What are the main states in a Java thread's lifecycle? | thread lifecycle, thread states |
| java-theory-053 | Medium | Multithreading | What is a daemon thread? | daemon thread, JVM shutdown |
| java-theory-054 | Hard | Multithreading | How would you implement a producer-consumer pattern in Java? | producer-consumer, BlockingQueue |
| java-theory-055 | Hard | Multithreading | What is CompletableFuture used for? | CompletableFuture, asynchronous programming |
| java-theory-056 | Medium | Multithreading | What is ThreadLocal used for? | ThreadLocal, per-thread state |
| java-theory-057 | Medium | JVM | What are the main memory areas in the JVM? | heap, stack, method area |
| java-theory-058 | Easy | JVM | What is the difference between the stack and the heap? | stack memory, heap memory |
| java-theory-059 | Medium | JVM | What is garbage collection in Java? | garbage collection, memory management |
| java-theory-060 | Hard | JVM | How does the JVM decide an object is eligible for garbage collection? | reachability, GC roots |
| java-theory-061 | Medium | JVM | What is the difference between a memory leak in C++ and a 'memory leak' in Java? | memory leak, lingering references |
| java-theory-062 | Hard | JVM | What is class loading in Java, and what are the main class loaders? | class loading, ClassLoader hierarchy |
| java-theory-063 | Hard | JVM | What is JIT (Just-In-Time) compilation? | JIT compiler, bytecode, native code |
| java-theory-064 | Medium | JVM | What is the Java String pool? | string pool, string interning |
| java-theory-065 | Hard | JVM | What are strong, weak, soft, and phantom references? | reference types, WeakReference, SoftReference |
| java-theory-066 | Medium | JVM | What is a StackOverflowError caused by at the JVM level? | StackOverflowError, call stack |
| java-theory-067 | Easy | Strings | Why are Strings immutable in Java? | string immutability, string pool, thread safety |
| java-theory-068 | Medium | Strings | What is the difference between String, StringBuilder, and StringBuffer? | String, StringBuilder, StringBuffer |
| java-theory-069 | Easy | Strings | What is the difference between == and .equals() when comparing Strings? | == operator, equals method, reference vs value |
| java-theory-070 | Medium | Strings | What is string interning? | intern(), string pool |
| java-theory-071 | Medium | Strings | Why is concatenating strings in a loop with + inefficient? | string concatenation, StringBuilder |
| java-theory-072 | Hard | Strings | How would you check if two strings are anagrams of each other? | anagram, character frequency |
| java-theory-073 | Hard | Strings | How would you check if a string is a palindrome efficiently? | palindrome, two-pointer |
| java-theory-074 | Medium | Strings | What does String.substring() do, and is it safe on shared underlying arrays in modern Java? | substring, string internals |
| java-theory-075 | Medium | Strings | What is the time complexity of common StringBuilder operations? | StringBuilder, amortized complexity |
| java-theory-076 | Hard | Strings | How would you remove duplicate characters from a string while preserving order? | duplicates, LinkedHashSet |
| java-theory-077 | Medium | Generics | What is type erasure in Java generics? | type erasure, generics implementation |
| java-theory-078 | Medium | Generics | What is a generic method, and how do you write one? | generic method, type parameter |
| java-theory-079 | Hard | Generics | Why are raw types (using a generic class without a type argument) discouraged? | raw types, unchecked warnings |
| java-theory-080 | Medium | Generics | Can you create an array of a generic type in Java? Why or why not? | generic array creation, type erasure |
| java-theory-081 | Easy | Generics | What is the benefit of using generics instead of raw Object types in collections? | generics, type safety |
| java-theory-082 | Medium | Functional | What is a lambda expression in Java? | lambda expression, functional interface |
| java-theory-083 | Medium | Functional | What is a functional interface? | functional interface, @FunctionalInterface |
| java-theory-084 | Medium | Functional | What is the Stream API used for? | Stream API, functional-style operations |
| java-theory-085 | Hard | Functional | What is the difference between map() and flatMap() in streams? | map, flatMap, stream of streams |
| java-theory-086 | Medium | Functional | What is Optional and what problem does it solve? | Optional, null safety |
| java-theory-087 | Medium | Functional | What is a method reference and when would you use one? | method reference, :: |
| java-theory-088 | Hard | Functional | What are Collectors, and give an example of a common one. | Collectors, terminal operation |
| java-theory-089 | Hard | Functional | What is the difference between stream() and parallelStream()? | parallelStream, fork-join pool |
| java-theory-090 | Medium | Functional | What does the reduce() operation do in streams? | reduce, aggregation |
| java-theory-091 | Easy | Functional | What is the difference between forEach() on a Stream and a traditional for loop? | forEach, terminal operation |
| java-theory-092 | Easy | Keywords | What does the static keyword mean in Java? | static keyword, class-level |
| java-theory-093 | Medium | Keywords | What is the transient keyword used for? | transient, serialization |
| java-theory-094 | Hard | Keywords | What does the native keyword indicate? | native keyword, JNI |
| java-theory-095 | Easy | Keywords | What is the purpose of the instanceof operator? | instanceof, type checking |
| java-theory-096 | Medium | Keywords | What are varargs in Java and how do you declare them? | varargs, variable arguments |
| java-theory-097 | Medium | Keywords | What is an enum in Java and what can it contain? | enum, enumeration |
| java-theory-098 | Hard | Keywords | What is the purpose of annotations in Java, and give an example. | annotations, metadata |
| java-theory-099 | Medium | Keywords | What is the difference between == comparing primitives vs objects? | == operator, primitives vs objects |
| java-theory-100 | Hard | Keywords | What is autoboxing and unboxing, and what pitfall can it cause? | autoboxing, unboxing, Integer cache |

---

## Detailed Reference Answers

### 1. [java-theory-001] What is encapsulation in Java and why is it useful?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: OOP
- **Expected Concepts**: `encapsulation, access modifiers, data hiding`
- **Needs Human Review**: `true`

**Reference Answer:**
> Encapsulation means bundling data (fields) and the methods that operate on it inside a class, and restricting direct access to the fields using private access modifiers with public getters/setters. It protects internal state from invalid changes and lets you change the implementation without breaking callers.

### 2. [java-theory-002] What is the difference between a class and an object?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: OOP
- **Expected Concepts**: `class, object, instantiation`
- **Needs Human Review**: `true`

**Reference Answer:**
> A class is a blueprint/template that defines fields and methods. An object is a runtime instance of a class created with `new`, occupying its own memory and holding its own copy of instance fields.

### 3. [java-theory-003] What is inheritance in Java?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: OOP
- **Expected Concepts**: `inheritance, extends, code reuse`
- **Needs Human Review**: `true`

**Reference Answer:**
> Inheritance lets a class (subclass) acquire the fields and methods of another class (superclass) using `extends`, enabling code reuse and establishing an IS-A relationship. Java supports single inheritance for classes.

### 4. [java-theory-004] What is polymorphism, and what are its two types in Java?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: OOP
- **Expected Concepts**: `polymorphism, overloading, overriding, dynamic dispatch`
- **Needs Human Review**: `true`

**Reference Answer:**
> Polymorphism means the same method call can behave differently depending on the object. Compile-time (static) polymorphism is method overloading, resolved at compile time by signature. Runtime (dynamic) polymorphism is method overriding, resolved at runtime via the actual object type (dynamic dispatch).

### 5. [java-theory-005] What is abstraction, and how is it achieved in Java?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: OOP
- **Expected Concepts**: `abstraction, abstract class, interface`
- **Needs Human Review**: `true`

**Reference Answer:**
> Abstraction means exposing only essential behavior while hiding implementation details. In Java it's achieved using abstract classes (partial implementation, can have state) and interfaces (a contract of method signatures, historically no state).

### 6. [java-theory-006] What is the difference between method overloading and method overriding?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: OOP
- **Expected Concepts**: `overloading, overriding, polymorphism`
- **Needs Human Review**: `true`

**Reference Answer:**
> Overloading is defining multiple methods with the same name but different parameter lists in the same class (compile-time). Overriding is redefining a superclass method with the same signature in a subclass to change its behavior (runtime, requires inheritance).

### 7. [java-theory-007] What is the purpose of a constructor in Java?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: OOP
- **Expected Concepts**: `constructor, initialization`
- **Needs Human Review**: `true`

**Reference Answer:**
> A constructor initializes a newly created object's state. It has the same name as the class, no return type, and runs automatically when `new` is used. Java provides a default no-arg constructor if none is defined.

### 8. [java-theory-008] What is the difference between `this` and `super` keywords?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: OOP
- **Expected Concepts**: `this keyword, super keyword`
- **Needs Human Review**: `true`

**Reference Answer:**
> `this` refers to the current object instance and is used to access its own fields/methods or call another constructor in the same class. `super` refers to the immediate superclass and is used to access its fields/methods or call its constructor.

### 9. [java-theory-009] What is the difference between an abstract class and an interface?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: OOP
- **Expected Concepts**: `abstract class, interface, multiple inheritance`
- **Needs Human Review**: `true`

**Reference Answer:**
> An abstract class can have both abstract and concrete methods, constructors, and instance state, but a class can extend only one. An interface defines a contract (methods, since Java 8 also default/static methods) with no instance state, and a class can implement multiple interfaces.

### 10. [java-theory-010] Why doesn't Java support multiple inheritance of classes, and how do interfaces work around this?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: OOP
- **Expected Concepts**: `diamond problem, multiple inheritance, interfaces`
- **Needs Human Review**: `true`

**Reference Answer:**
> Multiple class inheritance can cause the 'diamond problem', ambiguity about which superclass's state/method to use when two parents define the same member. Java avoids this for classes but allows implementing multiple interfaces, since interfaces (until default methods) had no state; even with default methods, Java forces the implementing class to explicitly resolve any conflicting default method.

### 11. [java-theory-011] What are access modifiers in Java and what are the four types?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: OOP
- **Expected Concepts**: `access modifiers, private, protected, public, default`
- **Needs Human Review**: `true`

**Reference Answer:**
> Access modifiers control visibility of classes/members: `private` (class only), default/package-private (same package), `protected` (same package + subclasses), and `public` (everywhere).

### 12. [java-theory-012] What does the `final` keyword mean when applied to a class, method, and variable?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: OOP
- **Expected Concepts**: `final keyword, immutability`
- **Needs Human Review**: `true`

**Reference Answer:**
> On a class, `final` prevents it from being subclassed. On a method, it prevents overriding in subclasses. On a variable, it makes the reference (or primitive value) unmodifiable after initialization -- for objects, the reference can't change but the object's internal state still can.

### 13. [java-theory-013] What is composition, and why is 'favor composition over inheritance' good advice?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: OOP
- **Expected Concepts**: `composition, inheritance, coupling`
- **Needs Human Review**: `true`

**Reference Answer:**
> Composition means a class holds a reference to another class instance (HAS-A) rather than extending it. It's often preferred because it avoids tight coupling and fragile base-class problems from deep inheritance hierarchies, and allows behavior to be changed at runtime by swapping the composed object.

### 14. [java-theory-014] What are default methods in interfaces, and why were they introduced in Java 8?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: OOP
- **Expected Concepts**: `default methods, interface evolution, Java 8`
- **Needs Human Review**: `true`

**Reference Answer:**
> Default methods let an interface provide a method body using the `default` keyword. They were introduced so existing interfaces (like those in the Collections framework) could gain new methods (e.g. `forEach`, `stream`) without breaking every class that already implements them.

### 15. [java-theory-015] What is the difference between static and instance members?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: OOP
- **Expected Concepts**: `static, instance members, class-level state`
- **Needs Human Review**: `true`

**Reference Answer:**
> Static members belong to the class itself and are shared across all instances (one copy in memory). Instance members belong to each individual object, with each object having its own copy. Static members can be accessed without creating an object.

### 16. [java-theory-016] What is the difference between ArrayList and LinkedList?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Collections
- **Expected Concepts**: `ArrayList, LinkedList, time complexity`
- **Needs Human Review**: `true`

**Reference Answer:**
> ArrayList is backed by a dynamic array: fast random access (O(1) get) but slow insert/delete in the middle (O(n) shifting). LinkedList is a doubly linked list: O(1) insert/delete at known nodes but O(n) random access since it must traverse from an end.

### 17. [java-theory-017] What is the difference between HashMap and Hashtable?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Collections
- **Expected Concepts**: `HashMap, Hashtable, thread safety`
- **Needs Human Review**: `true`

**Reference Answer:**
> HashMap is not synchronized (not thread-safe) and allows one null key and multiple null values. Hashtable is synchronized (thread-safe but slower) and does not allow null keys or values. In modern code, `ConcurrentHashMap` is generally preferred over Hashtable for thread safety.

### 18. [java-theory-018] What is the difference between HashSet and TreeSet?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Collections
- **Expected Concepts**: `HashSet, TreeSet, ordering`
- **Needs Human Review**: `true`

**Reference Answer:**
> HashSet stores elements in a hash table with no guaranteed order, offering O(1) average add/contains. TreeSet stores elements in a sorted order (via a red-black tree, using natural ordering or a Comparator), with O(log n) operations.

### 19. [java-theory-019] What is the difference between Comparable and Comparator?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Collections
- **Expected Concepts**: `Comparable, Comparator, sorting`
- **Needs Human Review**: `true`

**Reference Answer:**
> Comparable is implemented by the class itself to define a single natural ordering via `compareTo()`. Comparator is a separate class/lambda implementing `compare()`, letting you define multiple different orderings without modifying the original class.

### 20. [java-theory-020] What is a ConcurrentModificationException and when does it occur?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Collections
- **Expected Concepts**: `ConcurrentModificationException, fail-fast iterator`
- **Needs Human Review**: `true`

**Reference Answer:**
> It's thrown when a collection is structurally modified (add/remove) while being iterated with a fail-fast iterator, other than through the iterator's own `remove()` method. Java's non-concurrent collections detect this via an internal modification counter checked on each `next()` call.

### 21. [java-theory-021] What is the difference between fail-fast and fail-safe iterators?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Collections
- **Expected Concepts**: `fail-fast, fail-safe, iterator`
- **Needs Human Review**: `true`

**Reference Answer:**
> Fail-fast iterators (e.g. ArrayList, HashMap) throw ConcurrentModificationException if the collection is modified during iteration, since they operate directly on the collection. Fail-safe iterators (e.g. CopyOnWriteArrayList, ConcurrentHashMap) operate on a snapshot or allow safe concurrent modification, so they don't throw, though they may not reflect the latest changes.

### 22. [java-theory-022] How does HashMap work internally in Java?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Collections
- **Expected Concepts**: `hashCode, buckets, collision resolution`
- **Needs Human Review**: `true`

**Reference Answer:**
> A HashMap stores entries in an array of buckets, choosing a bucket via the key's hashCode() (after an internal hash spreading function). Collisions within a bucket are handled with a linked list (or, since Java 8, a balanced tree once a bucket exceeds a threshold, for better worst-case lookup). get()/put() are O(1) average, O(n)/O(log n) worst case.

### 23. [java-theory-023] Why must a class override both equals() and hashCode() together?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Collections
- **Expected Concepts**: `equals contract, hashCode contract`
- **Needs Human Review**: `true`

**Reference Answer:**
> Hash-based collections (HashMap, HashSet) use hashCode() to locate the bucket and equals() to confirm the exact match. If two equal objects have different hashCodes, they can land in different buckets and the collection will fail to find/deduplicate them correctly, violating the equals/hashCode contract.

### 24. [java-theory-024] What is an Iterator and how is it used?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Collections
- **Expected Concepts**: `Iterator, hasNext, next`
- **Needs Human Review**: `true`

**Reference Answer:**
> An Iterator is an object that lets you traverse a collection one element at a time using `hasNext()` to check for more elements and `next()` to retrieve the next one, without exposing the collection's internal structure.

### 25. [java-theory-025] What is a Deque and what makes it useful?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Collections
- **Expected Concepts**: `Deque, double-ended queue`
- **Needs Human Review**: `true`

**Reference Answer:**
> A Deque (double-ended queue) supports insertion and removal at both ends efficiently. It can be used as a stack (push/pop) or a queue (offer/poll), and ArrayDeque is generally faster than Stack/LinkedList for these purposes.

### 26. [java-theory-026] What is a PriorityQueue and how does it order elements?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Collections
- **Expected Concepts**: `PriorityQueue, heap, natural ordering`
- **Needs Human Review**: `true`

**Reference Answer:**
> PriorityQueue is backed by a binary heap and always returns the smallest element first (by natural ordering, or a supplied Comparator) when you call `poll()`. It does not guarantee overall sorted iteration order, only that the head is the minimum.

### 27. [java-theory-027] What is the difference between the Collection and Collections types?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Collections
- **Expected Concepts**: `Collection interface, Collections utility class`
- **Needs Human Review**: `true`

**Reference Answer:**
> Collection is the root interface of the collections framework (List, Set, Queue extend it). Collections is a utility class with static helper methods like `sort()`, `unmodifiableList()`, and `synchronizedList()`.

### 28. [java-theory-028] What is a bounded wildcard, and what's the difference between `? extends T` and `? super T`?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Collections
- **Expected Concepts**: `generics, wildcards, PECS`
- **Needs Human Review**: `true`

**Reference Answer:**
> `? extends T` accepts T or any subtype, useful for reading (Producer) since you only know it's at least a T. `? super T` accepts T or any supertype, useful for writing (Consumer) since you can safely add a T. This is the PECS rule: Producer Extends, Consumer Super.

### 29. [java-theory-029] How do you make a collection thread-safe in Java?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Collections
- **Expected Concepts**: `thread safety, Collections.synchronizedList, concurrent collections`
- **Needs Human Review**: `true`

**Reference Answer:**
> You can wrap it with `Collections.synchronizedList/Map/Set(...)` (coarse locking on every operation), or use classes from `java.util.concurrent` like ConcurrentHashMap or CopyOnWriteArrayList, which offer finer-grained, often better-performing thread safety.

### 30. [java-theory-030] What is the difference between List, Set, and Map?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Collections
- **Expected Concepts**: `List, Set, Map`
- **Needs Human Review**: `true`

**Reference Answer:**
> A List is an ordered collection that allows duplicates and indexed access. A Set is a collection with no duplicate elements (order depends on implementation). A Map stores key-value pairs with unique keys, not a subtype of Collection.

### 31. [java-theory-031] What is the difference between TreeMap and LinkedHashMap in terms of ordering?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Collections
- **Expected Concepts**: `TreeMap, LinkedHashMap, ordering`
- **Needs Human Review**: `true`

**Reference Answer:**
> TreeMap keeps entries sorted by key (natural order or a Comparator), backed by a red-black tree, O(log n) operations. LinkedHashMap keeps entries in insertion order (or optionally access order for LRU-style caches), backed by a hash table plus a linked list, O(1) average operations.

### 32. [java-theory-032] What is the difference between checked and unchecked exceptions?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Exceptions
- **Expected Concepts**: `checked exceptions, unchecked exceptions, RuntimeException`
- **Needs Human Review**: `true`

**Reference Answer:**
> Checked exceptions (subclasses of Exception, not RuntimeException, e.g. IOException) must be either caught or declared with `throws` at compile time. Unchecked exceptions (subclasses of RuntimeException, e.g. NullPointerException) are not checked at compile time and usually indicate programming bugs.

### 33. [java-theory-033] What is the purpose of the finally block?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Exceptions
- **Expected Concepts**: `try-catch-finally, cleanup`
- **Needs Human Review**: `true`

**Reference Answer:**
> The finally block always executes after try/catch (whether or not an exception occurred, and even if the try block returns), and is typically used for cleanup like closing resources.

### 34. [java-theory-034] What is the difference between throw and throws?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Exceptions
- **Expected Concepts**: `throw, throws`
- **Needs Human Review**: `true`

**Reference Answer:**
> `throw` is used inside a method to actually raise an exception instance (e.g. `throw new IllegalArgumentException(...)`). `throws` is used in a method signature to declare that the method might propagate a checked exception to its caller.

### 35. [java-theory-035] How do you create a custom exception in Java?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Exceptions
- **Expected Concepts**: `custom exception, extends Exception`
- **Needs Human Review**: `true`

**Reference Answer:**
> Create a class that extends Exception (checked) or RuntimeException (unchecked), typically providing constructors that call the superclass constructor with a message and/or cause, e.g. `class InvalidAgeException extends RuntimeException { ... }`.

### 36. [java-theory-036] What is try-with-resources and why is it useful?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Exceptions
- **Expected Concepts**: `try-with-resources, AutoCloseable`
- **Needs Human Review**: `true`

**Reference Answer:**
> Try-with-resources automatically closes any resource implementing AutoCloseable (like streams) at the end of the try block, even if an exception occurs, removing the need for manual close() calls in a finally block and avoiding resource leaks.

### 37. [java-theory-037] What is the difference between finally and finalize()?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Exceptions
- **Expected Concepts**: `finally, finalize`
- **Needs Human Review**: `true`

**Reference Answer:**
> finally is a block that always runs after a try/catch for cleanup. finalize() is a deprecated Object method the garbage collector may call before reclaiming an object's memory -- its timing is unpredictable, so it should not be relied on for cleanup; try-with-resources/AutoCloseable is the modern replacement.

### 38. [java-theory-038] Can you catch multiple exception types in one catch block?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Exceptions
- **Expected Concepts**: `multi-catch, pipe syntax`
- **Needs Human Review**: `true`

**Reference Answer:**
> Yes, using multi-catch syntax: `catch (IOException | SQLException e) { ... }`. The caught types must not be related by subclassing, and the resulting variable is implicitly final.

### 39. [java-theory-039] What is the Java exception class hierarchy?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Exceptions
- **Expected Concepts**: `Throwable, Exception, Error`
- **Needs Human Review**: `true`

**Reference Answer:**
> Throwable is the root, with two main branches: Error (serious, usually unrecoverable JVM-level problems like OutOfMemoryError, not meant to be caught) and Exception (recoverable conditions), which further splits into checked exceptions and RuntimeException (unchecked).

### 40. [java-theory-040] What commonly causes a NullPointerException?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Exceptions
- **Expected Concepts**: `NullPointerException, null reference`
- **Needs Human Review**: `true`

**Reference Answer:**
> It occurs when you try to use a null reference as if it were an object -- calling a method on it, accessing a field, or indexing a null array. Common causes include unchecked return values from methods that can return null, or uninitialized fields.

### 41. [java-theory-041] What is the difference between StackOverflowError and OutOfMemoryError?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Exceptions
- **Expected Concepts**: `StackOverflowError, OutOfMemoryError`
- **Needs Human Review**: `true`

**Reference Answer:**
> StackOverflowError occurs when the call stack exceeds its size limit, typically from deep or infinite recursion. OutOfMemoryError occurs when the JVM can't allocate more heap memory for objects, e.g. from a memory leak or genuinely needing more heap than allocated.

### 42. [java-theory-042] What is the difference between a process and a thread?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Multithreading
- **Expected Concepts**: `process, thread`
- **Needs Human Review**: `true`

**Reference Answer:**
> A process is an independent program with its own memory space. A thread is a lightweight unit of execution within a process, sharing the process's memory with other threads of the same process, making inter-thread communication cheaper but requiring synchronization.

### 43. [java-theory-043] What is the difference between extending Thread and implementing Runnable?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Multithreading
- **Expected Concepts**: `Thread class, Runnable interface`
- **Needs Human Review**: `true`

**Reference Answer:**
> Extending Thread uses up Java's single-inheritance slot and ties the task to being a Thread. Implementing Runnable separates the task (what to run) from the thread (how it runs), allows the class to extend something else, and lets the same Runnable be reused/submitted to an ExecutorService.

### 44. [java-theory-044] What does the synchronized keyword do?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Multithreading
- **Expected Concepts**: `synchronized, monitor lock, mutual exclusion`
- **Needs Human Review**: `true`

**Reference Answer:**
> It ensures only one thread can execute a synchronized method/block on a given object's monitor lock at a time, preventing race conditions on shared mutable state, at the cost of reduced concurrency.

### 45. [java-theory-045] What does the volatile keyword guarantee, and what doesn't it guarantee?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Multithreading
- **Expected Concepts**: `volatile, visibility, atomicity`
- **Needs Human Review**: `true`

**Reference Answer:**
> volatile guarantees visibility -- writes by one thread are immediately visible to other threads (no caching stale values) -- and prevents certain compiler reorderings. It does NOT guarantee atomicity for compound operations like `count++`, which still need synchronization or an atomic class.

### 46. [java-theory-046] What is a deadlock, and how can it be avoided?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Multithreading
- **Expected Concepts**: `deadlock, lock ordering`
- **Needs Human Review**: `true`

**Reference Answer:**
> A deadlock occurs when two or more threads each hold a lock the other needs, so neither can proceed. It can be avoided by always acquiring locks in a consistent global order, using timeouts (tryLock), or minimizing the scope/number of locks held simultaneously.

### 47. [java-theory-047] What is the Executor framework and why is it preferred over manually creating threads?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Multithreading
- **Expected Concepts**: `ExecutorService, thread pool`
- **Needs Human Review**: `true`

**Reference Answer:**
> The Executor framework (ExecutorService, thread pools) manages a pool of reusable threads for you, avoiding the overhead of creating a new thread per task, and provides higher-level task submission (submit/invokeAll) and lifecycle management (shutdown).

### 48. [java-theory-048] What is the difference between Runnable and Callable?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Multithreading
- **Expected Concepts**: `Runnable, Callable, Future`
- **Needs Human Review**: `true`

**Reference Answer:**
> Runnable's run() method returns nothing and can't throw checked exceptions. Callable's call() method returns a value and can throw checked exceptions, and is typically submitted to an ExecutorService, returning a Future to retrieve the result later.

### 49. [java-theory-049] What is the difference between wait()/notify() and Condition (from Lock)?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Multithreading
- **Expected Concepts**: `wait/notify, Condition, Lock`
- **Needs Human Review**: `true`

**Reference Answer:**
> wait()/notify()/notifyAll() are Object methods used inside synchronized blocks for inter-thread signaling tied to the object's intrinsic monitor. Condition (from java.util.concurrent.locks) works with explicit Lock objects, supports multiple independent condition queues per lock, and offers more flexible signaling (e.g. timed awaits, interruptible waits).

### 50. [java-theory-050] What is the difference between synchronized and ReentrantLock?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Multithreading
- **Expected Concepts**: `synchronized, ReentrantLock`
- **Needs Human Review**: `true`

**Reference Answer:**
> synchronized is simpler, JVM-managed, and locks/unlocks automatically at block boundaries. ReentrantLock offers more control: tryLock() with timeout, interruptible lock acquisition, fairness policies, and multiple Condition objects, but must be unlocked manually (typically in a finally block).

### 51. [java-theory-051] What are atomic classes like AtomicInteger used for?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Multithreading
- **Expected Concepts**: `AtomicInteger, compare-and-swap, lock-free`
- **Needs Human Review**: `true`

**Reference Answer:**
> They provide lock-free, thread-safe operations (like increment, compare-and-set) on single variables using low-level compare-and-swap (CAS) hardware instructions, which is often faster than using synchronized for simple counters.

### 52. [java-theory-052] What are the main states in a Java thread's lifecycle?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Multithreading
- **Expected Concepts**: `thread lifecycle, thread states`
- **Needs Human Review**: `true`

**Reference Answer:**
> NEW (created, not started), RUNNABLE (executing or ready to execute), BLOCKED (waiting for a monitor lock), WAITING/TIMED_WAITING (waiting for another thread's action), and TERMINATED (finished execution).

### 53. [java-theory-053] What is a daemon thread?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Multithreading
- **Expected Concepts**: `daemon thread, JVM shutdown`
- **Needs Human Review**: `true`

**Reference Answer:**
> A daemon thread runs in the background and does not prevent the JVM from exiting -- when all non-daemon threads finish, the JVM terminates even if daemon threads are still running. Set via `thread.setDaemon(true)` before starting it.

### 54. [java-theory-054] How would you implement a producer-consumer pattern in Java?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Multithreading
- **Expected Concepts**: `producer-consumer, BlockingQueue`
- **Needs Human Review**: `true`

**Reference Answer:**
> The simplest way is a BlockingQueue (e.g. ArrayBlockingQueue): producer threads call put() (which blocks if full) and consumer threads call take() (which blocks if empty), handling all the wait/notify coordination internally without manual synchronized/wait/notify code.

### 55. [java-theory-055] What is CompletableFuture used for?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Multithreading
- **Expected Concepts**: `CompletableFuture, asynchronous programming`
- **Needs Human Review**: `true`

**Reference Answer:**
> It represents a future result of an asynchronous computation and allows chaining dependent async operations (thenApply, thenCompose, thenCombine) without blocking, and combining multiple futures -- a more composable alternative to plain Future.

### 56. [java-theory-056] What is ThreadLocal used for?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Multithreading
- **Expected Concepts**: `ThreadLocal, per-thread state`
- **Needs Human Review**: `true`

**Reference Answer:**
> ThreadLocal gives each thread its own independent copy of a variable, useful for per-thread state (like a SimpleDateFormat instance or a per-request context) without needing synchronization, since threads never see each other's values.

### 57. [java-theory-057] What are the main memory areas in the JVM?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: JVM
- **Expected Concepts**: `heap, stack, method area`
- **Needs Human Review**: `true`

**Reference Answer:**
> The Heap stores objects and is shared across threads (subject to garbage collection). The Stack stores per-thread method call frames, local variables, and partial results (each thread has its own). The Method Area/Metaspace stores class metadata, and the PC Register tracks the current instruction per thread.

### 58. [java-theory-058] What is the difference between the stack and the heap?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: JVM
- **Expected Concepts**: `stack memory, heap memory`
- **Needs Human Review**: `true`

**Reference Answer:**
> The stack stores primitive local variables and object references, is per-thread, and is automatically reclaimed when a method returns. The heap stores actual objects, is shared across all threads, and is managed by the garbage collector.

### 59. [java-theory-059] What is garbage collection in Java?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: JVM
- **Expected Concepts**: `garbage collection, memory management`
- **Needs Human Review**: `true`

**Reference Answer:**
> Garbage collection automatically reclaims memory used by objects that are no longer reachable from any live reference, so the programmer doesn't need to manually free memory, reducing memory leaks and dangling pointer bugs (though leaks are still possible via lingering references).

### 60. [java-theory-060] How does the JVM decide an object is eligible for garbage collection?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: JVM
- **Expected Concepts**: `reachability, GC roots`
- **Needs Human Review**: `true`

**Reference Answer:**
> An object is eligible for GC when it's unreachable from any GC root (active thread stacks, static references, JNI references, etc.) through any chain of references -- reachability, not reference counting, is what Java's collectors use, which also avoids the classic circular-reference leak problem of naive reference counting.

### 61. [java-theory-061] What is the difference between a memory leak in C++ and a 'memory leak' in Java?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: JVM
- **Expected Concepts**: `memory leak, lingering references`
- **Needs Human Review**: `true`

**Reference Answer:**
> In C++, a leak is forgetting to free allocated memory. In Java, since GC handles freeing, a 'leak' means objects are still reachable (e.g. held in a static collection, an unclosed listener, or a cache without eviction) even though they're logically no longer needed, so GC can never reclaim them.

### 62. [java-theory-062] What is class loading in Java, and what are the main class loaders?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: JVM
- **Expected Concepts**: `class loading, ClassLoader hierarchy`
- **Needs Human Review**: `true`

**Reference Answer:**
> Class loading dynamically loads .class bytecode into the JVM when first needed, following a delegation hierarchy: the Bootstrap loader (core JDK classes), the Platform/Extension loader, and the Application/System loader (your classpath), each delegating to its parent first.

### 63. [java-theory-063] What is JIT (Just-In-Time) compilation?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: JVM
- **Expected Concepts**: `JIT compiler, bytecode, native code`
- **Needs Human Review**: `true`

**Reference Answer:**
> The JVM initially interprets bytecode, but the JIT compiler identifies frequently executed ('hot') code paths and compiles them to native machine code at runtime for much faster subsequent execution, combining the portability of bytecode with near-native performance for hot paths.

### 64. [java-theory-064] What is the Java String pool?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: JVM
- **Expected Concepts**: `string pool, string interning`
- **Needs Human Review**: `true`

**Reference Answer:**
> The string pool (part of the heap in modern JVMs) is a special area where string literals are stored and reused: identical literal strings share the same object rather than allocating a new one each time, saving memory. `String.intern()` can manually add a string to the pool.

### 65. [java-theory-065] What are strong, weak, soft, and phantom references?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: JVM
- **Expected Concepts**: `reference types, WeakReference, SoftReference`
- **Needs Human Review**: `true`

**Reference Answer:**
> Strong references (normal references) prevent GC entirely. Soft references allow GC only when memory is low (useful for memory-sensitive caches). Weak references allow GC as soon as no strong references remain (useful for canonicalizing mappings without preventing cleanup). Phantom references are enqueued after finalization, used for precise post-GC cleanup tracking.

### 66. [java-theory-066] What is a StackOverflowError caused by at the JVM level?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: JVM
- **Expected Concepts**: `StackOverflowError, call stack`
- **Needs Human Review**: `true`

**Reference Answer:**
> Each method call pushes a new frame onto the thread's fixed-size call stack. Deep or infinite recursion keeps pushing frames until the stack's memory limit is exceeded, at which point the JVM throws StackOverflowError.

### 67. [java-theory-067] Why are Strings immutable in Java?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Strings
- **Expected Concepts**: `string immutability, string pool, thread safety`
- **Needs Human Review**: `true`

**Reference Answer:**
> Once created, a String's contents can never change; any 'modification' method returns a new String. This enables safe string pooling/sharing, makes Strings inherently thread-safe, and lets String be safely used as a HashMap key (its hashCode can be cached).

### 68. [java-theory-068] What is the difference between String, StringBuilder, and StringBuffer?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Strings
- **Expected Concepts**: `String, StringBuilder, StringBuffer`
- **Needs Human Review**: `true`

**Reference Answer:**
> String is immutable. StringBuilder is mutable and not thread-safe, so it's faster for single-threaded, heavy string manipulation (e.g. in a loop). StringBuffer is mutable and synchronized (thread-safe), so it's slower but safe to share across threads.

### 69. [java-theory-069] What is the difference between == and .equals() when comparing Strings?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Strings
- **Expected Concepts**: `== operator, equals method, reference vs value`
- **Needs Human Review**: `true`

**Reference Answer:**
> == compares object references (are they the exact same object in memory), while .equals() compares the actual character contents. Two different String objects can have equal content but different references, so .equals() should be used for content comparison.

### 70. [java-theory-070] What is string interning?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Strings
- **Expected Concepts**: `intern(), string pool`
- **Needs Human Review**: `true`

**Reference Answer:**
> Interning ensures a string is stored (or reused, if already present) in the JVM's string pool. String literals are automatically interned; `str.intern()` can be called on a dynamically created string to get the pooled reference, letting it be compared with == against other interned strings.

### 71. [java-theory-071] Why is concatenating strings in a loop with + inefficient?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Strings
- **Expected Concepts**: `string concatenation, StringBuilder`
- **Needs Human Review**: `true`

**Reference Answer:**
> Since Strings are immutable, each `+` in a loop creates a brand-new String object, copying all previous characters -- O(n) work per iteration, O(n^2) overall for n concatenations. Using a StringBuilder and calling append() amortizes this to O(n) overall.

### 72. [java-theory-072] How would you check if two strings are anagrams of each other?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Strings
- **Expected Concepts**: `anagram, character frequency`
- **Needs Human Review**: `true`

**Reference Answer:**
> Compare character frequency: if lengths differ, they can't be anagrams; otherwise count occurrences of each character in both strings (e.g. via an int[26] array for lowercase letters) and confirm the counts match, or sort both strings and compare equality.

### 73. [java-theory-073] How would you check if a string is a palindrome efficiently?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Strings
- **Expected Concepts**: `palindrome, two-pointer`
- **Needs Human Review**: `true`

**Reference Answer:**
> Use two pointers starting at both ends, moving inward and comparing characters at each step; if any pair differs, it's not a palindrome. This runs in O(n) time and O(1) extra space, versus reversing the string which uses O(n) extra space.

### 74. [java-theory-074] What does String.substring() do, and is it safe on shared underlying arrays in modern Java?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Strings
- **Expected Concepts**: `substring, string internals`
- **Needs Human Review**: `true`

**Reference Answer:**
> substring(beginIndex, endIndex) returns a new String containing characters from beginIndex up to (not including) endIndex. In Java 7+, substring() copies the relevant characters into a new char/byte array rather than sharing the original's backing array, avoiding the old memory-retention pitfall where a small substring kept a huge original string alive.

### 75. [java-theory-075] What is the time complexity of common StringBuilder operations?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Strings
- **Expected Concepts**: `StringBuilder, amortized complexity`
- **Needs Human Review**: `true`

**Reference Answer:**
> append() is amortized O(1) (occasionally O(n) when the internal buffer needs to grow/copy), similar to ArrayList's add(). insert() at an arbitrary position is O(n) since it shifts subsequent characters.

### 76. [java-theory-076] How would you remove duplicate characters from a string while preserving order?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Strings
- **Expected Concepts**: `duplicates, LinkedHashSet`
- **Needs Human Review**: `true`

**Reference Answer:**
> Iterate through the string, tracking seen characters in a HashSet (or use a LinkedHashSet of characters directly), appending a character to the result only the first time it's seen -- this is O(n) time and preserves the original order of first occurrence.

### 77. [java-theory-077] What is type erasure in Java generics?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Generics
- **Expected Concepts**: `type erasure, generics implementation`
- **Needs Human Review**: `true`

**Reference Answer:**
> The compiler enforces generic type checks at compile time but then erases the generic type information, replacing type parameters with their bounds (or Object) in the compiled bytecode. This is why you can't do `new T()` or check `instanceof List<String>` at runtime -- the specific type argument isn't available anymore.

### 78. [java-theory-078] What is a generic method, and how do you write one?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Generics
- **Expected Concepts**: `generic method, type parameter`
- **Needs Human Review**: `true`

**Reference Answer:**
> A generic method declares its own type parameter(s) independent of the class, e.g. `public static <T> T firstElement(List<T> list) { return list.get(0); }`, allowing it to work with any type while preserving compile-time type safety.

### 79. [java-theory-079] Why are raw types (using a generic class without a type argument) discouraged?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Generics
- **Expected Concepts**: `raw types, unchecked warnings`
- **Needs Human Review**: `true`

**Reference Answer:**
> Using a raw type (e.g. `List list` instead of `List<String>`) disables generic type checking entirely for that variable, reintroducing the risk of ClassCastException at runtime and losing all the compile-time safety generics provide -- it exists mainly for backward compatibility with pre-generics code.

### 80. [java-theory-080] Can you create an array of a generic type in Java? Why or why not?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Generics
- **Expected Concepts**: `generic array creation, type erasure`
- **Needs Human Review**: `true`

**Reference Answer:**
> No, `new T[10]` is not allowed directly because of type erasure -- the JVM wouldn't know the actual runtime component type needed to create the array safely. Workarounds include using `Object[]` internally with casts, or accepting a Class<T> to use reflection's Array.newInstance().

### 81. [java-theory-081] What is the benefit of using generics instead of raw Object types in collections?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Generics
- **Expected Concepts**: `generics, type safety`
- **Needs Human Review**: `true`

**Reference Answer:**
> Generics let you specify the exact type a collection holds (e.g. `List<String>`), so the compiler catches type mismatches at compile time and you avoid needing to manually cast objects retrieved from the collection, preventing runtime ClassCastExceptions.

### 82. [java-theory-082] What is a lambda expression in Java?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Functional
- **Expected Concepts**: `lambda expression, functional interface`
- **Needs Human Review**: `true`

**Reference Answer:**
> A lambda expression is a concise way to write an anonymous implementation of a functional interface (an interface with exactly one abstract method), e.g. `(a, b) -> a + b`, avoiding the boilerplate of an anonymous inner class.

### 83. [java-theory-083] What is a functional interface?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Functional
- **Expected Concepts**: `functional interface, @FunctionalInterface`
- **Needs Human Review**: `true`

**Reference Answer:**
> An interface with exactly one abstract method (it may have default/static methods too), which can therefore be implemented with a lambda expression or method reference. Examples include Runnable, Comparator, and the java.util.function interfaces (Function, Predicate, Supplier, Consumer).

### 84. [java-theory-084] What is the Stream API used for?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Functional
- **Expected Concepts**: `Stream API, functional-style operations`
- **Needs Human Review**: `true`

**Reference Answer:**
> The Stream API lets you process sequences of elements in a declarative, functional style using chained operations like filter, map, sorted, and collect, instead of writing manual loops -- streams don't store data themselves and are typically consumed once.

### 85. [java-theory-085] What is the difference between map() and flatMap() in streams?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Functional
- **Expected Concepts**: `map, flatMap, stream of streams`
- **Needs Human Review**: `true`

**Reference Answer:**
> map() transforms each element into exactly one new element (a 1-to-1 mapping), potentially producing a Stream of Streams if each element maps to a collection. flatMap() transforms each element into a stream and then flattens all those streams into a single stream, useful for un-nesting (e.g. List<List<Integer>> to a flat Stream<Integer>).

### 86. [java-theory-086] What is Optional and what problem does it solve?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Functional
- **Expected Concepts**: `Optional, null safety`
- **Needs Human Review**: `true`

**Reference Answer:**
> Optional<T> is a container that may or may not hold a non-null value, used as a return type to explicitly signal 'this might not have a value' instead of returning null, forcing callers to consciously handle the absent case (via isPresent/orElse/map) rather than risking an unchecked NullPointerException.

### 87. [java-theory-087] What is a method reference and when would you use one?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Functional
- **Expected Concepts**: `method reference, ::`
- **Needs Human Review**: `true`

**Reference Answer:**
> A method reference (e.g. `String::toUpperCase`, `System.out::println`) is shorthand for a lambda that just calls an existing method, improving readability when the lambda body would be nothing more than a single method call.

### 88. [java-theory-088] What are Collectors, and give an example of a common one.
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Functional
- **Expected Concepts**: `Collectors, terminal operation`
- **Needs Human Review**: `true`

**Reference Answer:**
> Collectors are used with Stream.collect() as a terminal operation to accumulate stream elements into a result, such as a List, Set, Map, or a joined String. Example: `list.stream().collect(Collectors.toList())` or `Collectors.groupingBy(...)` to group elements by a classifier function.

### 89. [java-theory-089] What is the difference between stream() and parallelStream()?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Functional
- **Expected Concepts**: `parallelStream, fork-join pool`
- **Needs Human Review**: `true`

**Reference Answer:**
> stream() processes elements sequentially on the calling thread. parallelStream() splits the work across multiple threads (using the common ForkJoinPool) to potentially process elements concurrently -- beneficial for large datasets and CPU-bound work, but risky for operations with shared mutable state or where ordering matters.

### 90. [java-theory-090] What does the reduce() operation do in streams?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Functional
- **Expected Concepts**: `reduce, aggregation`
- **Needs Human Review**: `true`

**Reference Answer:**
> reduce() combines stream elements into a single result by repeatedly applying a combining function, e.g. `stream.reduce(0, (a, b) -> a + b)` to sum all elements, or without an identity value, returning an Optional in case the stream is empty.

### 91. [java-theory-091] What is the difference between forEach() on a Stream and a traditional for loop?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Functional
- **Expected Concepts**: `forEach, terminal operation`
- **Needs Human Review**: `true`

**Reference Answer:**
> forEach() is a terminal operation on a Stream that applies an action to each element, typically written in a functional style with a lambda; it doesn't support early termination (like break) or index-based access the way a traditional for loop does.

### 92. [java-theory-092] What does the static keyword mean in Java?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Keywords
- **Expected Concepts**: `static keyword, class-level`
- **Needs Human Review**: `true`

**Reference Answer:**
> static marks a member (field, method, nested class, or initializer block) as belonging to the class itself rather than any particular instance, so it can be accessed without creating an object, and is shared across all instances.

### 93. [java-theory-093] What is the transient keyword used for?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Keywords
- **Expected Concepts**: `transient, serialization`
- **Needs Human Review**: `true`

**Reference Answer:**
> transient marks a field to be excluded from default Java serialization -- when an object is serialized, transient fields are skipped and restored to their default value (e.g. null, 0) upon deserialization, useful for fields that shouldn't/can't be persisted (like a database connection).

### 94. [java-theory-094] What does the native keyword indicate?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Keywords
- **Expected Concepts**: `native keyword, JNI`
- **Needs Human Review**: `true`

**Reference Answer:**
> native marks a method whose implementation is provided in platform-specific code (typically C/C++) outside the JVM, accessed via the Java Native Interface (JNI) -- the method has no Java body, just a declaration.

### 95. [java-theory-095] What is the purpose of the instanceof operator?
- **Subject**: JAVA
- **Difficulty**: Easy
- **Category**: Keywords
- **Expected Concepts**: `instanceof, type checking`
- **Needs Human Review**: `true`

**Reference Answer:**
> instanceof checks at runtime whether an object is an instance of a specific class or interface (or a subtype of it), returning a boolean, commonly used before an explicit downcast to avoid a ClassCastException.

### 96. [java-theory-096] What are varargs in Java and how do you declare them?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Keywords
- **Expected Concepts**: `varargs, variable arguments`
- **Needs Human Review**: `true`

**Reference Answer:**
> Varargs (variable-length arguments) let a method accept zero or more arguments of a type as if it were an array, declared with `...`, e.g. `void print(String... items)`. Internally, the compiler packages the arguments into an array.

### 97. [java-theory-097] What is an enum in Java and what can it contain?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Keywords
- **Expected Concepts**: `enum, enumeration`
- **Needs Human Review**: `true`

**Reference Answer:**
> An enum defines a fixed set of named constants (e.g. `enum Day { MONDAY, TUESDAY, ... }`). Unlike in some languages, Java enums are full classes: they can have fields, constructors, and methods, and can even implement interfaces.

### 98. [java-theory-098] What is the purpose of annotations in Java, and give an example.
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Keywords
- **Expected Concepts**: `annotations, metadata`
- **Needs Human Review**: `true`

**Reference Answer:**
> Annotations attach metadata to code (classes, methods, fields) that tools, the compiler, or the runtime (via reflection) can process without changing the program's direct behavior. Examples: @Override (compiler check that a method actually overrides a superclass method), @Deprecated, @FunctionalInterface, and framework annotations like @Autowired in Spring.

### 99. [java-theory-099] What is the difference between == comparing primitives vs objects?
- **Subject**: JAVA
- **Difficulty**: Medium
- **Category**: Keywords
- **Expected Concepts**: `== operator, primitives vs objects`
- **Needs Human Review**: `true`

**Reference Answer:**
> For primitives, == compares actual values directly (e.g. `5 == 5` is true). For objects, == compares references -- whether both variables point to the exact same object in memory -- not their logical content, which is why .equals() is used for content comparison of objects.

### 100. [java-theory-100] What is autoboxing and unboxing, and what pitfall can it cause?
- **Subject**: JAVA
- **Difficulty**: Hard
- **Category**: Keywords
- **Expected Concepts**: `autoboxing, unboxing, Integer cache`
- **Needs Human Review**: `true`

**Reference Answer:**
> Autoboxing automatically converts a primitive to its wrapper class (int to Integer) and unboxing does the reverse, happening implicitly in many contexts. A common pitfall: comparing boxed Integers with == outside the cached range (-128 to 127) compares references, not values, so `Integer a = 200; Integer b = 200; a == b` can unexpectedly be false.

