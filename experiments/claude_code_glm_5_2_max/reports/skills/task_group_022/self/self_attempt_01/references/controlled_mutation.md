# Controlled Mutation Protocol (correction tasks)

A few tasks ask you to **correct** one data-quality contradiction and report whether the correction landed (e.g. a raw/canonical carrier-status contradiction). Read-only scorecard tasks never use this path. Use it only when the request names an `approved_correction` and a `correction_status_rule`.

## Goal
Change exactly the approved minimal canonical field on exactly the one affected source row, write exactly one audit row, confirm the new value in a post-change read, and report `APPLIED` only when all of that holds. Otherwise report `NOT_APPLIED` with what you actually observed.

## Step 1 — discover the contradiction (read-only)
- Use `GET /api/schema` + `GET /api/data-dictionary` to find the raw source column and the canonical (reconciled) column for the field in scope.
- The request says the contradiction is **exactly one**. Find the single source row where raw and canonical disagree within the named batch/cohort/cutoff. If you find zero or more than one, that is an observation to report — do not force a fit.
- Capture the full correction target: scan/source row id, shipment/entity id, field name, old (current canonical) value, and the intended new canonical value. The new value is the value the correction will set; if it is not derivable from the contradiction + dictionary, stop rather than guess.

## Step 2 — capture pre-correction state (read-only)
Run the backlog/cohort query the request defines (e.g. shipments whose effective final carrier status is not DELIVERED, at/before the cutoff, in the named batch) against the **current** data. Record the pre-correction counts. This is the baseline the report will compare against.

## Step 3 — mutate via the transaction endpoint
Single `POST /api/sql/transaction` with the approved statements, in order:

1. The guarded `UPDATE` that sets the one canonical field on the one source row. The guard must identify the row uniquely (by its stable source row id) **and** assert the old value, so a no-op or wrong-target update changes 0 rows rather than silently writing the wrong thing.
2. The `INSERT INTO correction_audit` with **all** audit columns, taking its values verbatim from the request's `approved_correction` block (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor).

Set `expected_total_changes` to the number of business rows the UPDATE will change (here 1). The audit `INSERT` counts as an audit row, not a "business row change." `expected_total_changes` is 0–12 and must match the actual changed-row count.

Allowed: guarded `UPDATE` of `carrier_scans` or `inventory_movements`; `INSERT INTO correction_audit` with all audit columns. Nothing else. Raw source values, source identity fields, and any unrelated business rows must remain unchanged.

## Step 4 — verify (read-only)
- Re-query the corrected row and confirm the canonical field now equals the new value.
- Re-run the same backlog/cohort query from Step 2 to get post-correction counts (post-correction backlog, post-correction delivered count, delta = post − pre).
- Query `GET /api/correction-audit` (or the audit table) and confirm exactly one audit row for this correction_key landed, with all columns matching the request's `approved_correction`.

## Step 5 — apply the success rule
The request's `correction_status_rule` defines success crisply (e.g. "exactly one business row and one audit row commit, and a post-change query confirms the corrected canonical value"). Evaluate it literally:
- `APPLIED` only when every conjunct of the success rule is true as observed.
- `NOT_APPLIED` for any other outcome — failed guard (0 rows), unexpected mutation count, audit mismatch, failed verification, or a server-rejected transaction.

Report what you actually observed (the affected-business-rows / audit-rows counts, the pre/post backlog numbers, the corrected target) **regardless** of the status — `NOT_APPLIED` is reported with real numbers, never fabricated successes.

## Hard constraints
- Mutate exactly one canonical field on one row. Never touch raw source values, identity fields, or unrelated rows.
- Never use `expected_total_changes` to mask a guard failure; if the guard updates 0 rows, the transaction honesty rule already failed — report `NOT_APPLIED`.
- If the contradiction count is not exactly one, or the new value is not derivable, do not mutate; report `NOT_APPLIED` with the discovery finding.
