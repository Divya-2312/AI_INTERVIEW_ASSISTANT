# Java Object-Oriented Programming (OOP) Knowledge

## Core Pillars
1. **Encapsulation**: Hiding implementation details by keeping variables private and exposing access via public getters and setters. Promotes data integrity.
2. **Inheritance**: Mechanism where a subclass inherits state and behaviors from a superclass using the `extends` keyword. Enables code reusability. Java supports single class inheritance and multiple interface inheritance.
3. **Polymorphism**: Ability of an object to take many forms.
   - *Compile-time (Static)*: Method Overloading (same method name, different parameter lists in the same class).
   - *Runtime (Dynamic)*: Method Overriding (subclass provides specific implementation of a superclass method using `@Override`).
4. **Abstraction**: Hiding internal mechanics and displaying only essential functionality to the user using abstract classes (`abstract` keyword) and interfaces (`interface` keyword).

## Key Terms
- **JDK (Java Development Kit)**: Complete software environment containing tools (javac, debugger) and JRE to develop Java apps.
- **JRE (Java Runtime Environment)**: Implementation of JVM providing libraries and binaries required to run Java bytecode.
- **JVM (Java Virtual Machine)**: Abstract computing machine that executes compiled Java bytecode (.class files).
- **Exceptions**: `Throwable` parent class with `Exception` (checked at compile-time like `IOException`) and `RuntimeException` (unchecked at runtime like `NullPointerException`).
