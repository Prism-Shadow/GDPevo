# Execution Pipeline

Step-by-step procedure for one Atlas Commerce Operations task. Run it once per task.
This is process only — no task-specific values, queries, or results.

## Phase 0 — Guard checks

1. Confirm `/work` (and the task's `input/` dir) contains only the canonical layout:
   `prompt.txt` and `payloads/answer_template.json` plus the single
   `payloads/<domain>_request.json` plus (at repo root) `environment_access.md`.
   If anything else is present → stop, write `contamination_report.txt`, do not solve.
2. Open `environment_access.md`. Capture the base URL and the bearer token verbatim.
   This file is the sole source for network access.

## Phase 1 — Load the task definition

3. Read `input/prompt.txt` to learn the audience, the goal, and the output filename
   (always `answer.json`). Note whether it says "analytical only / no correction"
   (read-only) or asks for a correction (write-back).
4. Read `input/payloads/<domain>_request.json` fully. Extract, in order:
   - Scope filters: population flag (PRODUCTION vs test/internal), tier/segment,
     region(s), the membership window (created/opened/scan-effective), and the
     cutoff timestamp.
   - Definitions: one rule per metric/sub-metric (completeness, on-time, severe
     exception, SLA breach, rework, leakage, etc.).
   - Rollups & ranking: numerator/denominator, dimension rollup, sort keys,
     tie-breaks, result sizes.
   - Policy: the cascading enum rule list + thresholds.
   - Correction block (if present): scope, reason_code, actor, audit_id,
     correction_key, corrected_at, and the APPLIED/NOT_APPLIED success rule.
   - required_output list.
5. Read `input/payloads/answer_template.json` fully. Extract, per field: type,
   bounds, `multipleOf`/`precision`/`decimal_places`, array size + `uniqueItems` +
   ordering, enum, and `additionalProperties:false`. Cross-check the required list
   against the request's `required_output`; they should agree on names.

## Phase 2 — Connect and context-load

6. `GET /api/schema` (with the bearer token). Parse every table's DDL; note
   primary keys, foreign keys, CHECK constraints, and which columns are raw vs
   canonical. Identify the tables a task touches (orders/shipments/carrier_scans,
   refund_attempts/payment_events/fx_rates/orders, warehouse_tasks/employees,
   support_cases/case_events/accounts).
7. `GET /api/data-dictionary`. Read `conventions` (timestamps, dates, money minor
   units, FX direction, raw-vs-canonical) and every relevant column description.
8. If a correction is involved, `GET /api/correction-audit` to see current audit
   rows and avoid `correction_key` collision.

## Phase 3 — Define the cohort (one query, reused)

9. Write a single cohort CTE that materializes the eligible population from the
   payload scope. Encode each filter literally as stated (population flag value,
   tier/segment IN list, region IN list, window comparator and inclusivity,
   cutoff). Emit the cohort count first and sanity-check it is plausible.
10. Save this cohort CTE as a building block. Every downstream query must start
    `FROM <cohort>` (or `JOIN <cohort>`) so denominators never drift.

## Phase 4 — Compute metrics inside the cohort

11. For each definition, translate it to SQL over canonical columns and append-only
    event tables filtered `<= cutoff`. Pay special attention to:
    - Universal ("every shipment") quantifiers → use `NOT EXISTS` a failing shipment,
      not `EXISTS` a passing one.
    - Per-row promise/SLA thresholds → join the per-row threshold, not a literal.
    - 24h/strict boundary comparators exactly as written.
    - Money: convert each row's minor amount by the *service_date* `fx_rates` rate
      for that row's currency (`amount_minor / 100 * usd_per_unit` when minor is
      cents), then aggregate in USD.
12. Keep all intermediate ratios and rank keys **unrounded**. Carry the full
    precision into ordering.

## Phase 5 — Rank, sort, size

13. Build each array output with an ORDER BY that mirrors the payload's stated order
    keys and directions, then the tie-breaks, then apply the required fixed size
    (LIMIT n). Sort IDs ascending where the template says so. Guarantee uniqueness
    with DISTINCT or `uniqueItems`.

## Phase 6 — Status / risk classification

14. Evaluate the cascading rule list top-down against the unrounded metrics from the
    fixed cohort. First matching rule wins; the "otherwise" bucket is terminal. Each
    rule typically ANDs a rate threshold with a second clause — both must hold.

## Phase 7 — Correction (only if the task asks)

15. From the audit evidence, identify the single raw↔canonical contradiction in the
    named batch/cutoff scope: the one scan/source row whose canonical field should
    move from old_value → new_value.
16. Build a transaction with, in order:
    - one guarded `UPDATE carrier_scans|inventory_movements SET <canonical_field>=?
      WHERE <row_id>=?` (params: new_value, source_row_id),
    - one `INSERT INTO correction_audit (<all 11 columns>) VALUES (?,…,?)`.
    Set `expected_total_changes` = 2.
17. Submit via `POST /api/sql/transaction`. Then `POST /api/sql` a verification
    SELECT confirming the canonical field now equals new_value for that row, and a
    count that exactly one audit row exists for the correction_key. Report `APPLIED`
    iff "one business row changed, one audit row inserted, verification confirms the
    new canonical value"; else `NOT_APPLIED` with observed counts. Never mutate raw,
    identity, or out-of-scope rows.

## Phase 8 — Assemble and validate

18. Build a single JSON object whose keys and shapes match the template exactly.
    Apply final rounding only to the fields the template marks.
19. Validate against the template: required ⊆ present keys, no extra keys (template
    is `additionalProperties:false`), integer vs number types, bounds, stepping
    (`multipleOf`), enum membership, array sizes/`uniqueItems`/ordering. Prefer a
    real JSON-Schema validator if available.
20. Write the object to `answer.json` — pure JSON, no commentary, no surrounding
    text, no trailing prose.

## Phase 9 — Self-review before finishing

21. Re-read the request's remaining denominators: is every ratio using the fixed
    cohort? Are no-shipment / unresponded / not-yet-resolved rows handled per the
    "remains in denominator" clauses? Are boundary comparators correct? Is the
    sorted output truncated to the exact size with correct tie-breaks? Did any
    rounding leak into an ordering key? Confirm `correction_status` (if any) reflects
    an actual verification query, not an assumption.
