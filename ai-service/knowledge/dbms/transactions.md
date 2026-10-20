# Database Transactions & ACID Properties

## ACID Properties
- **Atomicity**: All operations in a transaction succeed or all fail (All or Nothing).
- **Consistency**: Database transitions from one valid state to another, preserving constraints.
- **Isolation**: Concurrent execution of transactions yields same state as sequential execution.
- **Durability**: Committed changes persist permanently even after system crashes.

## SQL Keys & Joins
- **Primary Key**: Uniquely identifies each row; cannot contain NULL values.
- **Foreign Key**: Column referencing primary key of another table to maintain referential integrity.
- **JOINs**: `INNER JOIN` (matching rows), `LEFT JOIN` (all left + matching right), `RIGHT JOIN`, `FULL JOIN`.
- **Indexing**: Data structure (usually B-Tree or Hash) accelerating row retrieval at cost of additional write overhead.
