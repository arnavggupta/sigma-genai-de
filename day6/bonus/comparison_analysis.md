# NL2SQL vs Cortex Analyst — Sigma DataTech Evaluation  
Team: Sigma DataTech Team  
Date: 2026-05-25  

---

## 5-Question Head-to-Head Results

| # | Question | Module 2 SQL Correct? | Cortex SQL Correct? | Module 2 Time | Cortex Time |
|---|----------|----------------------|---------------------|---------------|--------------|
| 1 | Total transaction count | YES | YES | ~N/A (not logged) | ~16.46s |
| 2 | Failed transaction count | YES | YES | ~N/A (not logged) | ~14.61s |
| 3 | Highest revenue merchant | YES | YES | ~N/A (not logged) | ~26.79s |
| 4 | Failure rate by payment method | YES | YES | ~N/A (not logged) | ~319.33s |
| 5 | Total revenue (with COMPLETED filter) | YES | YES | ~N/A (not logged) | ~22.24s |

---

## Observations

### Where Module 2 NL2SQL was better:
- Strong **guardrail enforcement**: blocked unsafe queries like `DROP TABLE`, ensuring production safety.
- More **robust business logic handling** in some cases (e.g., explicitly using `CASE WHEN` aggregation patterns).
- Produced **richer metrics** (e.g., failure rate percentage with rounding + extra aggregates like total/failed counts).
- More consistent SQL formatting for analytics use cases.

### Where Cortex Analyst was better:
- Cleaner and more **direct SQL generation** with minimal extra logic.
- Faster and more consistent response times for most queries (except one outlier).
- Good use of **JOIN-aware semantic understanding** (Merchant + Transaction relationship handled correctly).
- Simpler queries are easier to read and maintain.

---

## Business Rule Accuracy

### Question 5 (Critical Test: Revenue only for COMPLETED transactions)

- **Module 2:**  
  Used `SUM(CASE WHEN STATUS='COMPLETED' THEN AMOUNT ELSE 0 END)`  
  ✔ Correctly enforces business rule inside aggregation.

- **Cortex:**  
  Used `WHERE STATUS = 'COMPLETED'`  
  ✔ Also correctly enforces business rule via filter clause.

👉 **Conclusion:** Both systems correctly applied the business rule, but in different styles:
- Module 2 → expression-level filtering (CASE WHEN)
- Cortex → row-level filtering (WHERE clause)

---

## Key Performance Insight

- Cortex showed a major latency spike in Question 4 (~319s), indicating potential inefficiency in:
  - query planning
  - semantic model translation
  - or warehouse cold start behavior

- Module 2 does not show execution latency in logs, but is expected to be more predictable since logic is deterministic Python + prompt-based SQL generation.

---

## Your Recommendation

**Recommended approach: Hybrid (Module 2 NL2SQL + Cortex Analyst)**

**Reason:**
Module 2 NL2SQL provides strong guardrails, safety enforcement, and flexible logic generation, while Cortex Analyst provides tighter integration with Snowflake semantics and simpler SQL generation. However, Cortex shows performance variability and lacks explicit safety controls like DROP/DDL blocking. A hybrid architecture would use Module 2 for validation + guardrails and Cortex for semantic SQL generation, combining safety with intelligence and scalability.