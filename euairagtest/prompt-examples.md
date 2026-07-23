# Prompt Examples

---

## sql-reviewer

### Production ETL Review

```
review load_bet_selection.sql

Context: production ETL, runs daily at 02:00 UTC. Target table ~500M rows.
Known issue: query has been getting slower over the past month.
```

### DDL Review

```
review create_anl_payment_tables.sql

DDL only — focus on distribution style, sort keys, encoding, data types, and naming conventions.
Tables will be joined frequently with anl_account.bf_h_account on account_id. Expected ~200M rows.
```

---

## sql-comparator

### Refactor (Same Output Expected)

```
compare load_bet_selection_v2.sql with load_bet_selection.sql

Refactor — same output expected. v2 rewrites the temp table chain to use CTEs.
Target table: omni_base.fact_payments.
```

### Intentional Change

```
compare add_runner_data.sql with load_bet_selection.sql

Intentional change: v2 adds runner-level data from wrk_sportsbook.bf_trunner.
Existing columns should remain unchanged. New columns: runner_name, runner_result, runner_sp_price.
Flag anything that affects existing output beyond the intended additions.
```

---

## sql-optimizer

### Basic Optimization

```
optimize slow_customer_lifetime_value.sql

Takes 45 minutes, target is under 5. Runs daily at 03:00 UTC.
```

### With EXPLAIN Plan

```
optimize bet_selection_aggregation.sql

Takes 90 minutes, used to take 10. I suspect the table needs VACUUM.

EXPLAIN:
[paste EXPLAIN output]

STL_ALERT_EVENT_LOG:
[paste alerts]
```

---

## sql-review-validator

### Validate a Code Review

```
validate the review report load_bet_selection_review.md

SQL file: load_bet_selection.sql
Metadata was already provided during the review.
```

### Validate an Optimization Report

```
validate the optimization report slow_customer_lifetime_value_optimization.md

SQL file: slow_customer_lifetime_value.sql
Challenge the rewrites — make sure none change output semantics.
```
