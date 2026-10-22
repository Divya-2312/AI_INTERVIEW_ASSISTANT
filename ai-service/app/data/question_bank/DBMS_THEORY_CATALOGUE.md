# DBMS Theory Topic Catalogue

Total Topics: 100 | Status: Needs Human Review (`needs_human_review: true`)

| ID | Difficulty | Category | Question | Expected Concepts |
|---|---|---|---|---|
| dbms-theory-001 | Easy | Keys | What is a primary key? | primary key, uniqueness, not null |
| dbms-theory-002 | Easy | Keys | What is a foreign key? | foreign key, referential integrity |
| dbms-theory-003 | Medium | Keys | What is a candidate key? | candidate key, minimal superkey |
| dbms-theory-004 | Medium | Keys | What is a composite key? | composite key, multiple columns |
| dbms-theory-005 | Medium | Keys | What is a super key? | super key, uniqueness |
| dbms-theory-006 | Hard | Keys | What is the difference between a primary key and a unique key? | primary key, unique key |
| dbms-theory-007 | Easy | Keys | What is a NULL value in a database? | NULL, missing data |
| dbms-theory-008 | Medium | ER Model | What is an entity and an entity set in the ER model? | entity, entity set |
| dbms-theory-009 | Medium | ER Model | What is the difference between a weak entity and a strong entity? | weak entity, strong entity, partial key |
| dbms-theory-010 | Medium | ER Model | What are the types of relationships (cardinality) in an ER diagram? | cardinality, one-to-one, one-to-many, many-to-many |
| dbms-theory-011 | Hard | ER Model | How is a many-to-many relationship implemented in a relational schema? | junction table, associative entity |
| dbms-theory-012 | Medium | ER Model | What is an attribute, and what types of attributes exist? | attribute, simple, composite, derived, multivalued |
| dbms-theory-013 | Hard | ER Model | What is generalization and specialization in ER modeling? | generalization, specialization, inheritance |
| dbms-theory-014 | Easy | ER Model | What is a relationship in the ER model? | relationship, association |
| dbms-theory-015 | Medium | Keys | What happens if you try to insert a duplicate value into a primary key column? | primary key constraint violation |
| dbms-theory-016 | Easy | Normalization | What is normalization and why is it done? | normalization, redundancy, data anomalies |
| dbms-theory-017 | Medium | Normalization | What is First Normal Form (1NF)? | 1NF, atomic values |
| dbms-theory-018 | Medium | Normalization | What is Second Normal Form (2NF)? | 2NF, partial dependency |
| dbms-theory-019 | Medium | Normalization | What is Third Normal Form (3NF)? | 3NF, transitive dependency |
| dbms-theory-020 | Hard | Normalization | What is Boyce-Codd Normal Form (BCNF), and how does it differ from 3NF? | BCNF, functional dependency |
| dbms-theory-021 | Medium | Normalization | Give an example of an update anomaly caused by an unnormalized table. | update anomaly |
| dbms-theory-022 | Medium | Normalization | Give an example of an insertion anomaly caused by an unnormalized table. | insertion anomaly |
| dbms-theory-023 | Medium | Normalization | Give an example of a deletion anomaly caused by an unnormalized table. | deletion anomaly |
| dbms-theory-024 | Hard | Normalization | What is denormalization, and when might it be used? | denormalization, performance tradeoff |
| dbms-theory-025 | Medium | Normalization | What is a functional dependency? | functional dependency |
| dbms-theory-026 | Hard | Normalization | What is a partial dependency? | partial dependency, composite key |
| dbms-theory-027 | Hard | Normalization | What is a transitive dependency? | transitive dependency |
| dbms-theory-028 | Medium | Normalization | Why might you choose not to fully normalize a database? | normalization tradeoffs, query performance |
| dbms-theory-029 | Hard | Normalization | What is Fourth Normal Form (4NF)? | 4NF, multivalued dependency |
| dbms-theory-030 | Medium | Normalization | How do you decide which normal form is 'good enough' for a real-world schema? | practical normalization |
| dbms-theory-031 | Easy | SQL | What is the difference between WHERE and HAVING? | WHERE clause, HAVING clause, GROUP BY |
| dbms-theory-032 | Medium | SQL | What is the difference between INNER JOIN and LEFT JOIN? | INNER JOIN, LEFT JOIN |
| dbms-theory-033 | Medium | SQL | What is the difference between LEFT JOIN and RIGHT JOIN? | LEFT JOIN, RIGHT JOIN |
| dbms-theory-034 | Hard | SQL | What is a FULL OUTER JOIN? | FULL OUTER JOIN |
| dbms-theory-035 | Medium | SQL | What does a self join do, and when would you use one? | self join |
| dbms-theory-036 | Easy | SQL | What is the difference between DELETE, TRUNCATE, and DROP? | DELETE, TRUNCATE, DROP |
| dbms-theory-037 | Medium | SQL | What is a subquery, and can you give an example use case? | subquery, nested query |
| dbms-theory-038 | Hard | SQL | What is the difference between a correlated subquery and a regular subquery? | correlated subquery |
| dbms-theory-039 | Medium | SQL | What is a view in SQL? | view, virtual table |
| dbms-theory-040 | Hard | SQL | What is the difference between a view and a materialized view? | view, materialized view |
| dbms-theory-041 | Medium | SQL | What does GROUP BY do, and how does it interact with aggregate functions? | GROUP BY, aggregate functions |
| dbms-theory-042 | Medium | SQL | What is the difference between UNION and UNION ALL? | UNION, UNION ALL |
| dbms-theory-043 | Easy | SQL | What is a stored procedure? | stored procedure |
| dbms-theory-044 | Medium | SQL | What is a trigger in SQL? | trigger |
| dbms-theory-045 | Hard | SQL | What is the difference between clustered and non-clustered indexes? | clustered index, non-clustered index |
| dbms-theory-046 | Easy | Transactions | What are the ACID properties of a transaction? | ACID, atomicity, consistency, isolation, durability |
| dbms-theory-047 | Medium | Transactions | What is the difference between COMMIT and ROLLBACK? | COMMIT, ROLLBACK |
| dbms-theory-048 | Hard | Transactions | What are the four standard transaction isolation levels? | isolation levels |
| dbms-theory-049 | Medium | Transactions | What is a dirty read? | dirty read |
| dbms-theory-050 | Medium | Transactions | What is a non-repeatable read? | non-repeatable read |
| dbms-theory-051 | Medium | Transactions | What is a phantom read? | phantom read |
| dbms-theory-052 | Hard | Transactions | What is a deadlock in the context of database transactions? | deadlock, lock ordering |
| dbms-theory-053 | Medium | Transactions | What is the difference between optimistic and pessimistic concurrency control? | optimistic locking, pessimistic locking |
| dbms-theory-054 | Medium | Transactions | What is a two-phase locking (2PL) protocol? | two-phase locking |
| dbms-theory-055 | Hard | Transactions | What is the difference between a shared lock and an exclusive lock? | shared lock, exclusive lock |
| dbms-theory-056 | Medium | Transactions | What is a savepoint in a transaction? | savepoint |
| dbms-theory-057 | Hard | Transactions | What is the difference between a database lock and a database latch? | lock, latch |
| dbms-theory-058 | Medium | Transactions | What does 'consistency' mean in the ACID properties, specifically? | consistency, constraints |
| dbms-theory-059 | Hard | Transactions | What is Multi-Version Concurrency Control (MVCC)? | MVCC |
| dbms-theory-060 | Medium | Transactions | Why is durability important, and how is it typically implemented? | durability, write-ahead log |
| dbms-theory-061 | Easy | Indexing | What is an index in a database, and why is it useful? | index, query performance |
| dbms-theory-062 | Medium | Indexing | What is the tradeoff of adding too many indexes to a table? | index overhead |
| dbms-theory-063 | Hard | Indexing | How does a B-tree index generally work? | B-tree, balanced tree |
| dbms-theory-064 | Medium | Indexing | What is a composite (multi-column) index, and when is it useful? | composite index, column order |
| dbms-theory-065 | Hard | Indexing | Why might a query still do a full table scan even if a relevant index exists? | query optimizer, index selectivity |
| dbms-theory-066 | Medium | Indexing | What is EXPLAIN (or a query execution plan) used for? | EXPLAIN, query plan |
| dbms-theory-067 | Hard | Indexing | What is index selectivity, and why does it matter? | selectivity |
| dbms-theory-068 | Medium | Indexing | What is a covering index? | covering index |
| dbms-theory-069 | Medium | Indexing | Should you index a column that is frequently updated? | index write cost |
| dbms-theory-070 | Hard | Indexing | What is the difference between a hash index and a B-tree index? | hash index, B-tree index |
| dbms-theory-071 | Easy | General | What is the difference between SQL and NoSQL databases? | SQL, NoSQL, schema |
| dbms-theory-072 | Medium | General | What is a schema in the context of a database? | schema |
| dbms-theory-073 | Medium | General | What is database sharding? | sharding, horizontal partitioning |
| dbms-theory-074 | Hard | General | What is the difference between vertical scaling and horizontal scaling for a database? | vertical scaling, horizontal scaling |
| dbms-theory-075 | Medium | General | What is database replication, and why is it used? | replication, read replicas |
| dbms-theory-076 | Hard | General | What is the CAP theorem? | CAP theorem |
| dbms-theory-077 | Medium | General | What is a data warehouse, and how does it differ from a typical transactional database? | data warehouse, OLAP, OLTP |
| dbms-theory-078 | Medium | General | What is a primary use case for a document-oriented NoSQL database like MongoDB? | document database, flexible schema |
| dbms-theory-079 | Hard | General | What is eventual consistency? | eventual consistency |
| dbms-theory-080 | Medium | General | What is a database constraint, and name a few common types. | constraints, NOT NULL, UNIQUE, CHECK |
| dbms-theory-081 | Medium | General | What is the difference between a natural key and a surrogate key? | natural key, surrogate key |
| dbms-theory-082 | Hard | General | What is referential integrity, and how is it enforced? | referential integrity, foreign key constraint |
| dbms-theory-083 | Medium | General | What does ON DELETE CASCADE do on a foreign key? | ON DELETE CASCADE |
| dbms-theory-084 | Medium | General | What is a database transaction log used for? | transaction log, write-ahead logging, recovery |
| dbms-theory-085 | Hard | General | What is the difference between OLTP and OLAP systems? | OLTP, OLAP |
| dbms-theory-086 | Easy | General | What does DDL, DML, and DCL stand for in SQL? | DDL, DML, DCL |
| dbms-theory-087 | Easy | SQL | What does the DISTINCT keyword do? | DISTINCT |
| dbms-theory-088 | Medium | SQL | What is a CROSS JOIN? | CROSS JOIN, Cartesian product |
| dbms-theory-089 | Medium | SQL | What is the purpose of the LIKE operator? | LIKE, wildcard matching |
| dbms-theory-090 | Easy | SQL | What is the difference between COUNT(*) and COUNT(column_name)? | COUNT aggregate |
| dbms-theory-091 | Medium | Normalization | What is a lossless join decomposition? | lossless decomposition |
| dbms-theory-092 | Hard | Indexing | What is the difference between a B-tree and a B+ tree, as commonly used for database indexes? | B+ tree |
| dbms-theory-093 | Hard | Transactions | What is the two-phase commit (2PC) protocol used for? | two-phase commit, distributed transactions |
| dbms-theory-094 | Medium | General | What is a checkpoint in database recovery? | checkpoint, recovery |
| dbms-theory-095 | Medium | SQL | What is the difference between a scalar function and an aggregate function in SQL? | scalar function, aggregate function |
| dbms-theory-096 | Medium | General | What is a data dictionary (or system catalog) in a DBMS? | data dictionary, metadata |
| dbms-theory-097 | Hard | Normalization | What is a multivalued dependency? | multivalued dependency |
| dbms-theory-098 | Easy | General | What is an entity-relationship (ER) diagram used for? | ER diagram |
| dbms-theory-099 | Medium | SQL | What does the BETWEEN operator do? | BETWEEN |
| dbms-theory-100 | Medium | General | What is the difference between a physical schema and a logical schema? | physical schema, logical schema |

---

## Detailed Reference Answers

### 1. [dbms-theory-001] What is a primary key?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: Keys
- **Expected Concepts**: `primary key, uniqueness, not null`
- **Needs Human Review**: `true`

**Reference Answer:**
> A primary key is a column (or set of columns) that uniquely identifies each row in a table. It cannot contain NULL values and must be unique across all rows.

### 2. [dbms-theory-002] What is a foreign key?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: Keys
- **Expected Concepts**: `foreign key, referential integrity`
- **Needs Human Review**: `true`

**Reference Answer:**
> A foreign key is a column in one table that references the primary key of another table, establishing a link between the two and enforcing referential integrity (you can't insert a foreign key value that doesn't exist in the referenced table).

### 3. [dbms-theory-003] What is a candidate key?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Keys
- **Expected Concepts**: `candidate key, minimal superkey`
- **Needs Human Review**: `true`

**Reference Answer:**
> A candidate key is any minimal set of columns that can uniquely identify a row -- a table can have multiple candidate keys, and one of them is chosen as the primary key; the rest become alternate keys.

### 4. [dbms-theory-004] What is a composite key?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Keys
- **Expected Concepts**: `composite key, multiple columns`
- **Needs Human Review**: `true`

**Reference Answer:**
> A composite key is a primary key made up of two or more columns, where no single column is sufficient to uniquely identify a row but the combination is, e.g. (student_id, course_id) in an enrollment table.

### 5. [dbms-theory-005] What is a super key?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Keys
- **Expected Concepts**: `super key, uniqueness`
- **Needs Human Review**: `true`

**Reference Answer:**
> A super key is any set of one or more columns that can uniquely identify a row -- it may contain extra columns beyond what's strictly necessary. Every candidate key is a super key, but not every super key is minimal enough to be a candidate key.

### 6. [dbms-theory-006] What is the difference between a primary key and a unique key?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Keys
- **Expected Concepts**: `primary key, unique key`
- **Needs Human Review**: `true`

**Reference Answer:**
> A table can have only one primary key, which cannot be NULL. A table can have multiple unique keys, and (in most databases) a unique key column can contain one NULL value, since NULL is not considered equal to another NULL for uniqueness checks.

### 7. [dbms-theory-007] What is a NULL value in a database?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: Keys
- **Expected Concepts**: `NULL, missing data`
- **Needs Human Review**: `true`

**Reference Answer:**
> NULL represents missing, unknown, or inapplicable data -- it is not the same as zero or an empty string, and comparisons with NULL using = or != return unknown (neither true nor false), which is why IS NULL / IS NOT NULL are used instead.

### 8. [dbms-theory-008] What is an entity and an entity set in the ER model?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: ER Model
- **Expected Concepts**: `entity, entity set`
- **Needs Human Review**: `true`

**Reference Answer:**
> An entity is a real-world object or concept (e.g. a specific student) with attributes. An entity set is a collection of similar entities (e.g. all students), typically mapped to a table in the relational model.

### 9. [dbms-theory-009] What is the difference between a weak entity and a strong entity?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: ER Model
- **Expected Concepts**: `weak entity, strong entity, partial key`
- **Needs Human Review**: `true`

**Reference Answer:**
> A strong entity has its own primary key and can exist independently. A weak entity cannot be uniquely identified by its own attributes alone -- it depends on a strong (identifying) entity's key plus a partial key of its own, e.g. a 'room' entity that only makes sense in the context of a specific 'building'.

### 10. [dbms-theory-010] What are the types of relationships (cardinality) in an ER diagram?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: ER Model
- **Expected Concepts**: `cardinality, one-to-one, one-to-many, many-to-many`
- **Needs Human Review**: `true`

**Reference Answer:**
> One-to-one (each entity in A relates to at most one in B, and vice versa), one-to-many (one entity in A relates to many in B, but each in B relates to only one in A), and many-to-many (entities in A can relate to many in B and vice versa, typically implemented via a junction/bridge table).

### 11. [dbms-theory-011] How is a many-to-many relationship implemented in a relational schema?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: ER Model
- **Expected Concepts**: `junction table, associative entity`
- **Needs Human Review**: `true`

**Reference Answer:**
> A many-to-many relationship is implemented using a separate junction (bridge/associative) table containing foreign keys to both related tables' primary keys, often combined as a composite primary key, e.g. an Enrollment table linking Students and Courses.

### 12. [dbms-theory-012] What is an attribute, and what types of attributes exist?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: ER Model
- **Expected Concepts**: `attribute, simple, composite, derived, multivalued`
- **Needs Human Review**: `true`

**Reference Answer:**
> An attribute is a property of an entity (e.g. name, age). Types include simple (atomic, e.g. age), composite (made of sub-parts, e.g. address = street+city+zip), derived (computed from another attribute, e.g. age from date of birth), and multivalued (an entity can have multiple values, e.g. phone numbers).

### 13. [dbms-theory-013] What is generalization and specialization in ER modeling?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: ER Model
- **Expected Concepts**: `generalization, specialization, inheritance`
- **Needs Human Review**: `true`

**Reference Answer:**
> Generalization combines lower-level entities that share common attributes into a higher-level generalized entity (bottom-up). Specialization does the reverse: identifying subgroups within an entity that have distinct attributes (top-down) -- both are ways of modeling an inheritance-like relationship, e.g. 'Vehicle' generalized from 'Car' and 'Truck'.

### 14. [dbms-theory-014] What is a relationship in the ER model?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: ER Model
- **Expected Concepts**: `relationship, association`
- **Needs Human Review**: `true`

**Reference Answer:**
> A relationship represents an association between two or more entities, e.g. a 'Enrolls' relationship connecting a Student entity and a Course entity.

### 15. [dbms-theory-015] What happens if you try to insert a duplicate value into a primary key column?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Keys
- **Expected Concepts**: `primary key constraint violation`
- **Needs Human Review**: `true`

**Reference Answer:**
> The database rejects the insert (or update) with a constraint violation error, since the primary key constraint enforces that every value in that column (or column combination) must be unique across the table.

### 16. [dbms-theory-016] What is normalization and why is it done?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: Normalization
- **Expected Concepts**: `normalization, redundancy, data anomalies`
- **Needs Human Review**: `true`

**Reference Answer:**
> Normalization is the process of organizing a database schema to reduce data redundancy and avoid update/insertion/deletion anomalies, typically by decomposing tables and enforcing dependencies through a series of normal forms.

### 17. [dbms-theory-017] What is First Normal Form (1NF)?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `1NF, atomic values`
- **Needs Human Review**: `true`

**Reference Answer:**
> A table is in 1NF if every column holds atomic (indivisible) values -- no repeating groups or multi-valued columns -- and each row is uniquely identifiable, typically via a primary key.

### 18. [dbms-theory-018] What is Second Normal Form (2NF)?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `2NF, partial dependency`
- **Needs Human Review**: `true`

**Reference Answer:**
> A table is in 2NF if it is in 1NF and has no partial dependency: every non-key attribute must depend on the ENTIRE primary key, not just part of a composite key. This only matters when the primary key is composite.

### 19. [dbms-theory-019] What is Third Normal Form (3NF)?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `3NF, transitive dependency`
- **Needs Human Review**: `true`

**Reference Answer:**
> A table is in 3NF if it is in 2NF and has no transitive dependency: no non-key attribute depends on another non-key attribute -- every non-key attribute must depend directly (and only) on the primary key.

### 20. [dbms-theory-020] What is Boyce-Codd Normal Form (BCNF), and how does it differ from 3NF?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Normalization
- **Expected Concepts**: `BCNF, functional dependency`
- **Needs Human Review**: `true`

**Reference Answer:**
> BCNF is a stricter version of 3NF: for every non-trivial functional dependency X -> Y, X must be a super key. 3NF allows a specific exception where Y is part of a candidate key even if X isn't a super key; BCNF doesn't allow that exception, eliminating a few remaining anomalies 3NF can miss.

### 21. [dbms-theory-021] Give an example of an update anomaly caused by an unnormalized table.
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `update anomaly`
- **Needs Human Review**: `true`

**Reference Answer:**
> If a student's department name is stored redundantly in every row of an enrollment table (once per course they take), updating that department's name requires updating it in every one of those rows -- missing even one leaves the data inconsistent.

### 22. [dbms-theory-022] Give an example of an insertion anomaly caused by an unnormalized table.
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `insertion anomaly`
- **Needs Human Review**: `true`

**Reference Answer:**
> If department information is only stored alongside student-course enrollment rows, you can't record a new department that has no students enrolled yet, because there's no row to insert it into without a student/course to attach it to.

### 23. [dbms-theory-023] Give an example of a deletion anomaly caused by an unnormalized table.
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `deletion anomaly`
- **Needs Human Review**: `true`

**Reference Answer:**
> If a table stores both order details and product details combined, deleting the last order for a product also deletes all information about that product itself, even though the product should still exist independently.

### 24. [dbms-theory-024] What is denormalization, and when might it be used?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Normalization
- **Expected Concepts**: `denormalization, performance tradeoff`
- **Needs Human Review**: `true`

**Reference Answer:**
> Denormalization intentionally introduces some redundancy (merging normalized tables or duplicating data) to improve read performance for specific query patterns, trading off some update complexity and storage for faster reads -- often used in reporting/analytics (data warehouses) where reads vastly outnumber writes.

### 25. [dbms-theory-025] What is a functional dependency?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `functional dependency`
- **Needs Human Review**: `true`

**Reference Answer:**
> A functional dependency X -> Y means that the value of X determines the value of Y: given the same value of X, Y must always be the same. E.g. student_id -> student_name, since each student ID maps to exactly one name.

### 26. [dbms-theory-026] What is a partial dependency?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Normalization
- **Expected Concepts**: `partial dependency, composite key`
- **Needs Human Review**: `true`

**Reference Answer:**
> A partial dependency occurs when a non-key attribute depends on only part of a composite primary key, rather than the whole key -- this violates 2NF and is a common source of update anomalies.

### 27. [dbms-theory-027] What is a transitive dependency?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Normalization
- **Expected Concepts**: `transitive dependency`
- **Needs Human Review**: `true`

**Reference Answer:**
> A transitive dependency occurs when a non-key attribute depends on another non-key attribute, which in turn depends on the primary key (A -> B -> C, so A -> C indirectly) -- this violates 3NF.

### 28. [dbms-theory-028] Why might you choose not to fully normalize a database?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `normalization tradeoffs, query performance`
- **Needs Human Review**: `true`

**Reference Answer:**
> Fully normalized schemas can require many joins to reconstruct commonly needed data, which can hurt read performance for read-heavy workloads. Some denormalization is a deliberate tradeoff to reduce join overhead at the cost of some redundancy and write complexity.

### 29. [dbms-theory-029] What is Fourth Normal Form (4NF)?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Normalization
- **Expected Concepts**: `4NF, multivalued dependency`
- **Needs Human Review**: `true`

**Reference Answer:**
> 4NF addresses multivalued dependencies: a table is in 4NF if it's in BCNF and has no non-trivial multivalued dependency, i.e. no table stores two or more independent multivalued facts about the same entity in a single table (e.g. a student's languages and hobbies shouldn't be cross-joined into one table).

### 30. [dbms-theory-030] How do you decide which normal form is 'good enough' for a real-world schema?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `practical normalization`
- **Needs Human Review**: `true`

**Reference Answer:**
> Most production schemas aim for 3NF (or BCNF) as a solid default that avoids the common anomalies, then selectively denormalize specific tables/columns where performance profiling shows joins are a genuine bottleneck -- normalization level is a design tradeoff, not an absolute requirement.

### 31. [dbms-theory-031] What is the difference between WHERE and HAVING?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: SQL
- **Expected Concepts**: `WHERE clause, HAVING clause, GROUP BY`
- **Needs Human Review**: `true`

**Reference Answer:**
> WHERE filters individual rows before any grouping/aggregation happens, and cannot reference aggregate functions. HAVING filters groups after GROUP BY has been applied, and can reference aggregate functions like COUNT() or SUM().

### 32. [dbms-theory-032] What is the difference between INNER JOIN and LEFT JOIN?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `INNER JOIN, LEFT JOIN`
- **Needs Human Review**: `true`

**Reference Answer:**
> INNER JOIN returns only rows that have matching values in both tables. LEFT JOIN returns all rows from the left table, plus matching rows from the right table -- if there's no match, the right table's columns are NULL for that row.

### 33. [dbms-theory-033] What is the difference between LEFT JOIN and RIGHT JOIN?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `LEFT JOIN, RIGHT JOIN`
- **Needs Human Review**: `true`

**Reference Answer:**
> LEFT JOIN keeps all rows from the left (first-listed) table, filling unmatched right-table columns with NULL. RIGHT JOIN does the mirror opposite, keeping all rows from the right table. A RIGHT JOIN can always be rewritten as a LEFT JOIN by swapping table order.

### 34. [dbms-theory-034] What is a FULL OUTER JOIN?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: SQL
- **Expected Concepts**: `FULL OUTER JOIN`
- **Needs Human Review**: `true`

**Reference Answer:**
> A FULL OUTER JOIN returns all rows from both tables, matching where possible, and filling with NULL on whichever side has no match -- effectively a union of LEFT JOIN and RIGHT JOIN results.

### 35. [dbms-theory-035] What does a self join do, and when would you use one?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `self join`
- **Needs Human Review**: `true`

**Reference Answer:**
> A self join joins a table to itself (using table aliases to distinguish the two references), typically used to compare rows within the same table, e.g. finding employees who report to a specific manager stored in the same Employees table.

### 36. [dbms-theory-036] What is the difference between DELETE, TRUNCATE, and DROP?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: SQL
- **Expected Concepts**: `DELETE, TRUNCATE, DROP`
- **Needs Human Review**: `true`

**Reference Answer:**
> DELETE removes specific rows (can be filtered with WHERE) and is logged row-by-row, so it can be rolled back and triggers fire. TRUNCATE removes all rows quickly by deallocating data pages, usually can't be filtered, and typically can't be rolled back in some databases. DROP removes the entire table structure along with its data.

### 37. [dbms-theory-037] What is a subquery, and can you give an example use case?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `subquery, nested query`
- **Needs Human Review**: `true`

**Reference Answer:**
> A subquery is a query nested inside another query, often in WHERE, FROM, or SELECT. Example: finding employees earning more than the average salary: `SELECT * FROM Employees WHERE salary > (SELECT AVG(salary) FROM Employees)`.

### 38. [dbms-theory-038] What is the difference between a correlated subquery and a regular subquery?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: SQL
- **Expected Concepts**: `correlated subquery`
- **Needs Human Review**: `true`

**Reference Answer:**
> A regular subquery executes once, independently of the outer query. A correlated subquery references a column from the outer query and is conceptually re-evaluated for each row the outer query processes, which can make it slower if not optimized by the query planner.

### 39. [dbms-theory-039] What is a view in SQL?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `view, virtual table`
- **Needs Human Review**: `true`

**Reference Answer:**
> A view is a saved, named query that behaves like a virtual table -- it doesn't store data itself (unless it's a materialized view), but presents the results of its underlying query each time it's queried, useful for simplifying complex joins or restricting access to specific columns.

### 40. [dbms-theory-040] What is the difference between a view and a materialized view?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: SQL
- **Expected Concepts**: `view, materialized view`
- **Needs Human Review**: `true`

**Reference Answer:**
> A regular view re-runs its underlying query every time it's accessed, always reflecting current data. A materialized view stores (caches) the query's result physically, which is much faster to read but can become stale until it's refreshed.

### 41. [dbms-theory-041] What does GROUP BY do, and how does it interact with aggregate functions?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `GROUP BY, aggregate functions`
- **Needs Human Review**: `true`

**Reference Answer:**
> GROUP BY groups rows that share the same value(s) in specified columns into summary rows, which aggregate functions (COUNT, SUM, AVG, MAX, MIN) then operate on per group rather than across the whole table.

### 42. [dbms-theory-042] What is the difference between UNION and UNION ALL?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `UNION, UNION ALL`
- **Needs Human Review**: `true`

**Reference Answer:**
> UNION combines the result sets of two queries and removes duplicate rows (which requires an extra sort/dedup step). UNION ALL combines them without removing duplicates, making it faster when you know duplicates aren't a concern or are wanted.

### 43. [dbms-theory-043] What is a stored procedure?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: SQL
- **Expected Concepts**: `stored procedure`
- **Needs Human Review**: `true`

**Reference Answer:**
> A stored procedure is a precompiled, named block of SQL/procedural code stored in the database that can be called/executed with parameters, useful for encapsulating reusable logic and reducing repeated round-trips from the application.

### 44. [dbms-theory-044] What is a trigger in SQL?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `trigger`
- **Needs Human Review**: `true`

**Reference Answer:**
> A trigger is a piece of code that automatically executes in response to a specific event (INSERT, UPDATE, DELETE) on a table, often used to enforce business rules, maintain audit logs, or keep derived data in sync.

### 45. [dbms-theory-045] What is the difference between clustered and non-clustered indexes?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: SQL
- **Expected Concepts**: `clustered index, non-clustered index`
- **Needs Human Review**: `true`

**Reference Answer:**
> A clustered index determines the physical storage order of table rows -- a table can have only one, since data can only be physically sorted one way. A non-clustered index is a separate structure with pointers back to the actual rows, and a table can have many of these.

### 46. [dbms-theory-046] What are the ACID properties of a transaction?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: Transactions
- **Expected Concepts**: `ACID, atomicity, consistency, isolation, durability`
- **Needs Human Review**: `true`

**Reference Answer:**
> Atomicity: a transaction is all-or-nothing. Consistency: a transaction takes the database from one valid state to another, respecting constraints. Isolation: concurrent transactions don't interfere with each other's intermediate states. Durability: once committed, changes survive even a crash.

### 47. [dbms-theory-047] What is the difference between COMMIT and ROLLBACK?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Transactions
- **Expected Concepts**: `COMMIT, ROLLBACK`
- **Needs Human Review**: `true`

**Reference Answer:**
> COMMIT permanently saves all changes made in the current transaction. ROLLBACK undoes all changes made in the current transaction, reverting the database to its state before the transaction began.

### 48. [dbms-theory-048] What are the four standard transaction isolation levels?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Transactions
- **Expected Concepts**: `isolation levels`
- **Needs Human Review**: `true`

**Reference Answer:**
> Read Uncommitted (may see uncommitted changes from other transactions, 'dirty reads'), Read Committed (only sees committed data, but values can change between reads within the same transaction), Repeatable Read (same rows read twice return the same values within a transaction, but new rows can appear -- 'phantom reads'), and Serializable (transactions behave as if executed one at a time, strictest and slowest).

### 49. [dbms-theory-049] What is a dirty read?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Transactions
- **Expected Concepts**: `dirty read`
- **Needs Human Review**: `true`

**Reference Answer:**
> A dirty read happens when a transaction reads data that another transaction has modified but not yet committed -- if that other transaction rolls back, the first transaction had read data that never actually existed.

### 50. [dbms-theory-050] What is a non-repeatable read?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Transactions
- **Expected Concepts**: `non-repeatable read`
- **Needs Human Review**: `true`

**Reference Answer:**
> A non-repeatable read happens when a transaction reads the same row twice and gets different values, because another transaction updated and committed a change to that row in between the two reads.

### 51. [dbms-theory-051] What is a phantom read?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Transactions
- **Expected Concepts**: `phantom read`
- **Needs Human Review**: `true`

**Reference Answer:**
> A phantom read happens when a transaction re-runs a query and gets a different SET of rows (new rows appearing or existing rows disappearing), because another transaction inserted or deleted rows matching the query's condition in between.

### 52. [dbms-theory-052] What is a deadlock in the context of database transactions?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Transactions
- **Expected Concepts**: `deadlock, lock ordering`
- **Needs Human Review**: `true`

**Reference Answer:**
> A deadlock occurs when two or more transactions each hold a lock that the other needs, so neither can proceed -- the database typically detects this and forcibly rolls back one of the transactions (the 'deadlock victim') to break the cycle.

### 53. [dbms-theory-053] What is the difference between optimistic and pessimistic concurrency control?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Transactions
- **Expected Concepts**: `optimistic locking, pessimistic locking`
- **Needs Human Review**: `true`

**Reference Answer:**
> Pessimistic concurrency control locks data upfront before reading/writing, preventing conflicts by blocking other transactions. Optimistic concurrency control allows transactions to proceed without locking, then checks for conflicts (e.g. via a version number) only at commit time, rolling back if a conflict is detected -- better for low-contention workloads.

### 54. [dbms-theory-054] What is a two-phase locking (2PL) protocol?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Transactions
- **Expected Concepts**: `two-phase locking`
- **Needs Human Review**: `true`

**Reference Answer:**
> 2PL has a growing phase (a transaction can acquire locks but not release any) followed by a shrinking phase (locks can be released but not acquired), which guarantees serializability of concurrent transactions.

### 55. [dbms-theory-055] What is the difference between a shared lock and an exclusive lock?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Transactions
- **Expected Concepts**: `shared lock, exclusive lock`
- **Needs Human Review**: `true`

**Reference Answer:**
> A shared (read) lock allows multiple transactions to read the same data concurrently but blocks writes. An exclusive (write) lock allows only the holding transaction to read or write that data, blocking all other access until it's released.

### 56. [dbms-theory-056] What is a savepoint in a transaction?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Transactions
- **Expected Concepts**: `savepoint`
- **Needs Human Review**: `true`

**Reference Answer:**
> A savepoint marks a point within a transaction that you can later roll back to, without undoing the entire transaction -- useful for partial rollback of a specific operation while keeping earlier work in the same transaction.

### 57. [dbms-theory-057] What is the difference between a database lock and a database latch?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Transactions
- **Expected Concepts**: `lock, latch`
- **Needs Human Review**: `true`

**Reference Answer:**
> Locks protect the logical consistency of data (rows/tables) and are held for the duration of a transaction, visible to the application. Latches are lightweight, short-duration synchronization primitives protecting internal memory structures (like buffer pages), held only for the duration of the operation, invisible to the application.

### 58. [dbms-theory-058] What does 'consistency' mean in the ACID properties, specifically?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Transactions
- **Expected Concepts**: `consistency, constraints`
- **Needs Human Review**: `true`

**Reference Answer:**
> Consistency means a transaction must bring the database from one valid state to another valid state, respecting all defined rules: constraints, cascades, triggers, and data types -- a transaction that would violate a constraint is rejected entirely.

### 59. [dbms-theory-059] What is Multi-Version Concurrency Control (MVCC)?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Transactions
- **Expected Concepts**: `MVCC`
- **Needs Human Review**: `true`

**Reference Answer:**
> MVCC allows readers to see a consistent snapshot of the database without blocking writers (and vice versa) by keeping multiple versions of a row -- each transaction sees the version of the data as it existed at the start of its transaction (or statement), avoiding many locking conflicts. Used by PostgreSQL, MySQL InnoDB, and others.

### 60. [dbms-theory-060] Why is durability important, and how is it typically implemented?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Transactions
- **Expected Concepts**: `durability, write-ahead log`
- **Needs Human Review**: `true`

**Reference Answer:**
> Durability guarantees that once a transaction commits, its changes survive even a power failure or crash. It's typically implemented via a write-ahead log (WAL): changes are written to a durable log before being applied, so the database can replay the log to recover committed changes after a crash.

### 61. [dbms-theory-061] What is an index in a database, and why is it useful?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: Indexing
- **Expected Concepts**: `index, query performance`
- **Needs Human Review**: `true`

**Reference Answer:**
> An index is a data structure (commonly a B-tree) that speeds up lookups on a column by avoiding a full table scan, at the cost of extra storage and slightly slower writes (since the index must also be updated).

### 62. [dbms-theory-062] What is the tradeoff of adding too many indexes to a table?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Indexing
- **Expected Concepts**: `index overhead`
- **Needs Human Review**: `true`

**Reference Answer:**
> Every index speeds up reads on that column but slows down writes (INSERT/UPDATE/DELETE), since each index must also be updated, and consumes additional disk space -- indexes should be added deliberately based on actual query patterns, not blanket-applied to every column.

### 63. [dbms-theory-063] How does a B-tree index generally work?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Indexing
- **Expected Concepts**: `B-tree, balanced tree`
- **Needs Human Review**: `true`

**Reference Answer:**
> A B-tree is a balanced, sorted tree structure where each node can have multiple children, keeping the tree shallow even for large datasets. Lookups, range scans, insertions, and deletions are all O(log n), and its sorted structure also supports efficient range queries and ORDER BY.

### 64. [dbms-theory-064] What is a composite (multi-column) index, and when is it useful?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Indexing
- **Expected Concepts**: `composite index, column order`
- **Needs Human Review**: `true`

**Reference Answer:**
> A composite index spans multiple columns in a defined order, useful when queries commonly filter/sort on that same combination of columns. Column order matters: the index is most effective for queries that filter on a left-to-right prefix of the indexed columns.

### 65. [dbms-theory-065] Why might a query still do a full table scan even if a relevant index exists?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Indexing
- **Expected Concepts**: `query optimizer, index selectivity`
- **Needs Human Review**: `true`

**Reference Answer:**
> The query optimizer may decide a full scan is cheaper if the index has low selectivity (matches a large fraction of rows), if a function/expression is applied to the indexed column in the WHERE clause preventing index use, or if the table is small enough that scanning is faster than the overhead of using the index.

### 66. [dbms-theory-066] What is EXPLAIN (or a query execution plan) used for?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Indexing
- **Expected Concepts**: `EXPLAIN, query plan`
- **Needs Human Review**: `true`

**Reference Answer:**
> EXPLAIN shows the database's chosen execution plan for a query -- which indexes (if any) it will use, join order, and estimated cost -- helping developers diagnose slow queries and decide whether an index or query rewrite is needed.

### 67. [dbms-theory-067] What is index selectivity, and why does it matter?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Indexing
- **Expected Concepts**: `selectivity`
- **Needs Human Review**: `true`

**Reference Answer:**
> Selectivity is the ratio of distinct values to total rows for a column. A highly selective column (e.g. a unique ID) benefits greatly from indexing since it narrows results a lot. A low-selectivity column (e.g. a boolean flag) benefits far less, since the index doesn't narrow the candidate rows much.

### 68. [dbms-theory-068] What is a covering index?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Indexing
- **Expected Concepts**: `covering index`
- **Needs Human Review**: `true`

**Reference Answer:**
> A covering index contains all the columns a query needs (in its SELECT, WHERE, and ORDER BY), so the database can satisfy the query entirely from the index itself without a separate lookup into the actual table rows, which is faster.

### 69. [dbms-theory-069] Should you index a column that is frequently updated?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Indexing
- **Expected Concepts**: `index write cost`
- **Needs Human Review**: `true`

**Reference Answer:**
> It depends: indexing speeds up reads on that column, but every update also has to update the index, adding write overhead. For a frequently updated column that's rarely searched on, the write cost may outweigh the read benefit.

### 70. [dbms-theory-070] What is the difference between a hash index and a B-tree index?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Indexing
- **Expected Concepts**: `hash index, B-tree index`
- **Needs Human Review**: `true`

**Reference Answer:**
> A hash index offers very fast O(1) equality lookups but cannot support range queries or ORDER BY efficiently, since hashing destroys ordering. A B-tree index is slightly slower for pure equality lookups (O(log n)) but supports range queries, sorting, and prefix matching, which is why B-tree is the more common general-purpose default.

### 71. [dbms-theory-071] What is the difference between SQL and NoSQL databases?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: General
- **Expected Concepts**: `SQL, NoSQL, schema`
- **Needs Human Review**: `true`

**Reference Answer:**
> SQL (relational) databases use structured, predefined schemas with tables and enforce ACID transactions and strong consistency, well-suited for relational data with complex queries. NoSQL databases (document, key-value, column-family, graph) offer flexible/dynamic schemas and typically prioritize horizontal scalability and availability, often with eventual rather than strong consistency.

### 72. [dbms-theory-072] What is a schema in the context of a database?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `schema`
- **Needs Human Review**: `true`

**Reference Answer:**
> A schema is the structural blueprint of a database: the tables, columns, data types, relationships, and constraints that define how data is organized, independent of the actual data stored in it.

### 73. [dbms-theory-073] What is database sharding?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `sharding, horizontal partitioning`
- **Needs Human Review**: `true`

**Reference Answer:**
> Sharding splits a large database horizontally across multiple servers, with each shard holding a subset of the rows (e.g. partitioned by a hash of a user ID), allowing the database to scale beyond what a single machine can handle, at the cost of added complexity for cross-shard queries.

### 74. [dbms-theory-074] What is the difference between vertical scaling and horizontal scaling for a database?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: General
- **Expected Concepts**: `vertical scaling, horizontal scaling`
- **Needs Human Review**: `true`

**Reference Answer:**
> Vertical scaling means adding more resources (CPU, RAM, faster disks) to a single database server. Horizontal scaling means adding more servers and distributing the data/load across them (e.g. via sharding or read replicas) -- horizontal scaling has a much higher ceiling but is architecturally more complex.

### 75. [dbms-theory-075] What is database replication, and why is it used?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `replication, read replicas`
- **Needs Human Review**: `true`

**Reference Answer:**
> Replication maintains copies of the database on multiple servers, used for high availability (failover if the primary goes down), and for scaling read throughput (read replicas handle read queries while writes go to the primary).

### 76. [dbms-theory-076] What is the CAP theorem?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: General
- **Expected Concepts**: `CAP theorem`
- **Needs Human Review**: `true`

**Reference Answer:**
> The CAP theorem states that a distributed data system can only guarantee two of three properties simultaneously during a network partition: Consistency (all nodes see the same data), Availability (every request gets a response), and Partition tolerance (the system keeps working despite network splits) -- since partitions are generally unavoidable in distributed systems, the real-world tradeoff is usually between consistency and availability.

### 77. [dbms-theory-077] What is a data warehouse, and how does it differ from a typical transactional database?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `data warehouse, OLAP, OLTP`
- **Needs Human Review**: `true`

**Reference Answer:**
> A transactional (OLTP) database is optimized for many small, fast reads/writes of current operational data. A data warehouse (OLAP) is optimized for large, complex analytical queries over historical data, often denormalized (e.g. star schema) for faster aggregate reporting rather than transactional consistency.

### 78. [dbms-theory-078] What is a primary use case for a document-oriented NoSQL database like MongoDB?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `document database, flexible schema`
- **Needs Human Review**: `true`

**Reference Answer:**
> Document databases suit data with a flexible or evolving structure that doesn't map cleanly to rigid tables, or where an entire related object is naturally read/written together (e.g. a user profile with nested preferences), avoiding the joins a relational model would need for the same access pattern.

### 79. [dbms-theory-079] What is eventual consistency?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: General
- **Expected Concepts**: `eventual consistency`
- **Needs Human Review**: `true`

**Reference Answer:**
> Eventual consistency means that, given no new updates, all replicas of a piece of data will eventually converge to the same value, but there may be a window where different nodes temporarily return stale/different results -- a tradeoff many distributed NoSQL systems make in favor of higher availability.

### 80. [dbms-theory-080] What is a database constraint, and name a few common types.
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `constraints, NOT NULL, UNIQUE, CHECK`
- **Needs Human Review**: `true`

**Reference Answer:**
> A constraint is a rule enforced on column(s) to maintain data integrity. Common types: NOT NULL (value required), UNIQUE (no duplicate values), CHECK (value must satisfy a condition, e.g. age >= 0), PRIMARY KEY, and FOREIGN KEY.

### 81. [dbms-theory-081] What is the difference between a natural key and a surrogate key?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `natural key, surrogate key`
- **Needs Human Review**: `true`

**Reference Answer:**
> A natural key is derived from real-world data that already uniquely identifies a row (e.g. an email address or national ID). A surrogate key is an artificial, system-generated identifier (e.g. an auto-incrementing integer or UUID) with no business meaning, often preferred because it's stable even if the natural attributes change.

### 82. [dbms-theory-082] What is referential integrity, and how is it enforced?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: General
- **Expected Concepts**: `referential integrity, foreign key constraint`
- **Needs Human Review**: `true`

**Reference Answer:**
> Referential integrity ensures that a foreign key value always references an existing row in the related table (or is NULL, if allowed). It's enforced via foreign key constraints, which reject inserts/updates that would create a dangling reference, and typically define what happens on delete/update of the referenced row (CASCADE, RESTRICT, SET NULL).

### 83. [dbms-theory-083] What does ON DELETE CASCADE do on a foreign key?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `ON DELETE CASCADE`
- **Needs Human Review**: `true`

**Reference Answer:**
> It automatically deletes any dependent rows in the referencing table when the referenced row in the parent table is deleted, keeping referential integrity without requiring the application to manually delete child rows first.

### 84. [dbms-theory-084] What is a database transaction log used for?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `transaction log, write-ahead logging, recovery`
- **Needs Human Review**: `true`

**Reference Answer:**
> A transaction log records all changes before they're applied to the actual data files (write-ahead logging), enabling crash recovery (replaying committed-but-not-yet-flushed changes) and rollback of uncommitted transactions.

### 85. [dbms-theory-085] What is the difference between OLTP and OLAP systems?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: General
- **Expected Concepts**: `OLTP, OLAP`
- **Needs Human Review**: `true`

**Reference Answer:**
> OLTP (Online Transaction Processing) systems handle many short, frequent read/write transactions on current data (e.g. an e-commerce checkout). OLAP (Online Analytical Processing) systems handle complex, long-running analytical queries over large historical datasets (e.g. quarterly sales trend analysis), often using denormalized/star-schema structures optimized for aggregation.

### 86. [dbms-theory-086] What does DDL, DML, and DCL stand for in SQL?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: General
- **Expected Concepts**: `DDL, DML, DCL`
- **Needs Human Review**: `true`

**Reference Answer:**
> DDL (Data Definition Language: CREATE, ALTER, DROP) defines/modifies schema structure. DML (Data Manipulation Language: SELECT, INSERT, UPDATE, DELETE) manipulates the actual data. DCL (Data Control Language: GRANT, REVOKE) manages permissions/access control.

### 87. [dbms-theory-087] What does the DISTINCT keyword do?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: SQL
- **Expected Concepts**: `DISTINCT`
- **Needs Human Review**: `true`

**Reference Answer:**
> DISTINCT removes duplicate rows from the query's result set, keeping only unique combinations of the selected columns.

### 88. [dbms-theory-088] What is a CROSS JOIN?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `CROSS JOIN, Cartesian product`
- **Needs Human Review**: `true`

**Reference Answer:**
> A CROSS JOIN produces the Cartesian product of two tables -- every row of the first table paired with every row of the second -- with no join condition, resulting in rows_A * rows_B total rows. It's rarely used intentionally except for generating combinations.

### 89. [dbms-theory-089] What is the purpose of the LIKE operator?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `LIKE, wildcard matching`
- **Needs Human Review**: `true`

**Reference Answer:**
> LIKE performs pattern matching in a WHERE clause using wildcards: % matches any sequence of characters, and _ matches exactly one character, e.g. `WHERE name LIKE 'A%'` matches names starting with A.

### 90. [dbms-theory-090] What is the difference between COUNT(*) and COUNT(column_name)?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: SQL
- **Expected Concepts**: `COUNT aggregate`
- **Needs Human Review**: `true`

**Reference Answer:**
> COUNT(*) counts all rows in the group, including rows where columns are NULL. COUNT(column_name) counts only rows where that specific column is NOT NULL.

### 91. [dbms-theory-091] What is a lossless join decomposition?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: Normalization
- **Expected Concepts**: `lossless decomposition`
- **Needs Human Review**: `true`

**Reference Answer:**
> A lossless join decomposition splits a table into smaller tables such that joining them back together (via natural join) reproduces exactly the original data, with no spurious or missing rows -- a required property of correct normalization.

### 92. [dbms-theory-092] What is the difference between a B-tree and a B+ tree, as commonly used for database indexes?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Indexing
- **Expected Concepts**: `B+ tree`
- **Needs Human Review**: `true`

**Reference Answer:**
> In a B+ tree, all actual data (or row pointers) is stored only in leaf nodes, which are also linked together for efficient range scans; internal nodes only store keys for navigation. A plain B-tree can store data in internal nodes too. Most database indexes use B+ trees specifically because of the efficient sequential leaf traversal for range queries.

### 93. [dbms-theory-093] What is the two-phase commit (2PC) protocol used for?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Transactions
- **Expected Concepts**: `two-phase commit, distributed transactions`
- **Needs Human Review**: `true`

**Reference Answer:**
> 2PC coordinates a transaction across multiple databases/nodes: in the prepare phase, all participants confirm they CAN commit; only if all agree does the coordinator send a commit phase to actually apply changes everywhere, ensuring atomicity across distributed systems (at the cost of blocking if the coordinator fails).

### 94. [dbms-theory-094] What is a checkpoint in database recovery?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `checkpoint, recovery`
- **Needs Human Review**: `true`

**Reference Answer:**
> A checkpoint is a point where the database writes all its in-memory changes to disk and records this in the transaction log, so recovery after a crash only needs to replay the log from the last checkpoint forward, rather than from the very beginning.

### 95. [dbms-theory-095] What is the difference between a scalar function and an aggregate function in SQL?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `scalar function, aggregate function`
- **Needs Human Review**: `true`

**Reference Answer:**
> A scalar function operates on a single value per row and returns one result per row (e.g. UPPER(), ROUND()). An aggregate function operates across multiple rows (typically a group) and returns a single summarized result (e.g. SUM(), AVG(), COUNT()).

### 96. [dbms-theory-096] What is a data dictionary (or system catalog) in a DBMS?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `data dictionary, metadata`
- **Needs Human Review**: `true`

**Reference Answer:**
> A data dictionary is metadata the DBMS maintains about the database itself: table definitions, column types, constraints, indexes, and permissions -- essentially the database's description of its own structure, queryable by the DBMS and sometimes by users.

### 97. [dbms-theory-097] What is a multivalued dependency?
- **Subject**: DBMS
- **Difficulty**: Hard
- **Category**: Normalization
- **Expected Concepts**: `multivalued dependency`
- **Needs Human Review**: `true`

**Reference Answer:**
> A multivalued dependency exists when, for a given value of attribute A, there is a set of values for attribute B that is independent of any other attribute C in the same relation -- this can cause redundancy that even BCNF doesn't catch, addressed by 4NF.

### 98. [dbms-theory-098] What is an entity-relationship (ER) diagram used for?
- **Subject**: DBMS
- **Difficulty**: Easy
- **Category**: General
- **Expected Concepts**: `ER diagram`
- **Needs Human Review**: `true`

**Reference Answer:**
> An ER diagram is a visual representation of a database's entities, their attributes, and the relationships between them, used during database design to plan the schema before creating actual tables.

### 99. [dbms-theory-099] What does the BETWEEN operator do?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: SQL
- **Expected Concepts**: `BETWEEN`
- **Needs Human Review**: `true`

**Reference Answer:**
> BETWEEN checks if a value falls within an inclusive range, e.g. `WHERE age BETWEEN 18 AND 30` is equivalent to `age >= 18 AND age <= 30`.

### 100. [dbms-theory-100] What is the difference between a physical schema and a logical schema?
- **Subject**: DBMS
- **Difficulty**: Medium
- **Category**: General
- **Expected Concepts**: `physical schema, logical schema`
- **Needs Human Review**: `true`

**Reference Answer:**
> The logical schema describes the structure of the data (tables, columns, relationships, constraints) independent of how it's stored. The physical schema describes how that data is actually stored on disk -- file organization, indexing structures, partitioning -- which can change without affecting the logical schema (data independence).

