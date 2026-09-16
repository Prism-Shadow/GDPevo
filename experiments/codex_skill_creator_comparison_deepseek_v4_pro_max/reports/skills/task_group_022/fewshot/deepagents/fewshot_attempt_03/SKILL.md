---
name: atlas-ops-scoring
description: >
  Analytical scoring and data correction for the Atlas Commerce Operations
  database through an authenticated REST API. Use when a task asks to compute
  production-shipping scorecards, refund-settlement reconciliations, carrier
  quality corrections, warehouse productivity reviews, or enterprise support
  health reports against Atlas records. Covers both read-only SQL analytics
  (cutoff-based eligibility, tiered classification, ranking, breach detection,
  leakage candidate identification) and single-field transactional corrections
  with audit verification. Trigger when the workspace mentions Atlas Commerce
  Operations, an atlas-ops API, cutoff-based business metrics, or any of the
  five named review types.
license: MIT
compatibility: designed for deepagents-code
---

# Atlas Ops Scoring

## Overview

This skill is the reusable toolkit for analytical review tasks and controlled
data corrections against the Atlas Commerce Operations database. It assumes a
task-specific request payload, a JSON answer template, and a running task
environment that exposes the Atlas API. The skill provides the correct workflow,
endpoint details, SQL patterns, and correction protocol — it does not contain
task-specific threshold values or final answer records.

Every task begins the same way: discover the schema, read the data dictionary,
map the request payload's business definitions to columns, query, compute, and
write the result exactly to the answer template.

## When to Load References

- [api_endpoints.md](references/api_endpoints.md) — always load first; contains
  every endpoint, its purpose, request/response shape, and auth header.
- [sql_patterns.md](references/sql_patterns.md) — load when you need patterns for
  cutoff windows, effective-final status, tiered classification, ranking,
  leakage/exception detection, SLA breach logic, rounding, or rate formulas.
- [transaction_protocol.md](references/transaction_protocol.md) — load only for
  tasks that require a controlled data correction (POST /api/sql/transaction).
  Skip it for read-only analytical tasks.

## General Workflow for Read-Only Analytical Tasks

1. **Read the request payload.** It lives in the task's `input/payloads/`
   directory. It contains the cutoff, business definitions, aggregation rules,
   rounding policy, status tier rules, and the list of required output fields.

2. **Read the answer template.** The JSON Schema template in the same payloads
   directory defines every required field, its type, constraints, and ordering
   rules. The final output must validate against this schema exactly.

3. **Discover the schema.** Call `GET /api/schema`. Identify every table and
   column mentioned by the request's business definitions. Pay attention to
   foreign keys that link orders → shipments → scans, orders → refunds,
   tasks → employees/teams, cases → accounts, etc.

4. **Read the data dictionary.** Call `GET /api/data-dictionary`. For every
   column you plan to filter or group by, confirm the value set. In particular,
   confirm the exact string labels for status values (e.g. `DELIVERED` vs
   `COMPLETED`), account tiers (`GOLD` vs `SILVER`), priority levels (`URGENT`
   vs `HIGH`), and region names.

5. **Design the queries.** Break the analytics into a small set of focused
   aggregations rather than one giant query. A typical decomposition:
   - One query for the eligible population count.
   - One query for per-entity state at the cutoff (e.g. each order's effective
     shipment status, each case's active time).
   - One or more queries for breaching/severe/exception candidates.
   - One query for ranked groupings (by region, by team, by reason code).

6. **Execute queries.** Use `POST /api/sql` for each. Keep intermediate results
   at full precision.

7. **Compute derived metrics.** Apply the request's formulas (rates, medians,
   rankings) in code. Only round final reported values.

8. **Classify tiers.** Apply the request's tier conditions top-to-bottom;
   first match wins.

9. **Assemble the answer.** Build a JSON object with exactly the fields required
   by the template, in any order (JSON object keys are unordered). Verify each
   field's type, constraints, and ordering rules.

10. **Write the answer.** Save as `answer.json` in the task workspace root.
    Do not include commentary, markdown, or extra fields.

## Workflow for Transactional Correction Tasks

1. Follow steps 1–5 from the read-only workflow to understand the data and
   locate the contradiction.

2. Run a `SELECT` to confirm the exact row, column, and current value of the
   field that contradicts the canonical source.

3. Load [transaction_protocol.md](references/transaction_protocol.md) and
   follow the four-step sequence: build the transaction with UPDATE + INSERT
   audit, submit to `POST /api/sql/transaction`, verify both the changed row
   and the audit record, then report `APPLIED` or `NOT_APPLIED`.

4. If the task also requires a pre/post change analytical comparison (e.g.
   backlog count before and after), compute both from read-only queries and
   include them in the answer.

## Common Pitfalls

- **Using the wrong status label.** The data dictionary often reveals that
  effective states use different strings than the request's colloquial terms.
  Always confirm with the dictionary.

- **Forgetting the denominator.** Incomplete or unresolved entities still count
  in the eligible denominator unless the request explicitly excludes them.

- **Sorting before rounding.** Rank by unrounded values. Only round the values
  that appear in the final output.

- **Overwriting raw values.** Correction tasks must only touch the single
  canonical column. Source fields, identifiers, and unrelated rows must stay
  unchanged.

- **Late cutoff confusion.** A cutoff of `2026-04-15T23:59:59Z` includes
  everything through that second. Timestamps at `2026-04-16T00:00:00Z` are
  excluded.

- **Even-count median.** When the request says "for an even count average the
  two central values", sort the values, take the two middle values, compute
  their mean, then round to the requested precision.

## Task Types Recognized by This Skill

The skill covers these Atlas review types. Each has a characteristic request
payload shape; use the schema and data dictionary to map business terms to
columns.

- **Fulfillment scorecard** — campaign cohort, shipment delivery cutoff,
  on-time rate, warehouse region ranking, severe exception classification,
  HEALTHY/WATCH/CRITICAL tiers.

- **Refund reconciliation** — account-tier settlement window, logical refunds
  vs reversals, FX conversion, leakage candidates, reason-code ranking,
  LOW/MODERATE/HIGH risk tiers.

- **Carrier quality correction** — single canonical field contradiction,
  controlled UPDATE + audit INSERT, pre/post backlog comparison,
  APPLIED/NOT_APPLIED status.

- **Warehouse productivity** — task creation window, completion units,
  units-per-hour employee ranking, rework rate, delayed high-priority tasks,
  team completion-rate ranking, STABLE/PRESSURED/AT_RISK tiers.

- **Support health** — case opening window, priority-tiered SLA thresholds,
  first-response and resolution breach detection, severe active case
  identification, worst-account ranking, median resolution hours,
  CONTROLLED/ELEVATED/SEVERE risk tiers.
