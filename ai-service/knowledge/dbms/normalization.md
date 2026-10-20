# Database Normalization Knowledge

## Purpose
Normalization is the process of structuring relational database tables to minimize data redundancy and prevent update, insertion, and deletion anomalies.

## Normal Forms
1. **1NF (First Normal Form)**: Eliminate repeating groups; ensure atomic values in each column; set unique primary key.
2. **2NF (Second Normal Form)**: Must be in 1NF; eliminate partial functional dependencies (all non-key attributes fully dependent on whole primary key).
3. **3NF (Third Normal Form)**: Must be in 2NF; eliminate transitive functional dependencies (non-key attribute dependent on another non-key attribute).
4. **BCNF (Boyce-Codd Normal Form)**: Stricter 3NF; for every functional dependency X -> Y, X must be a super key.
