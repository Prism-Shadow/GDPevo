---
name: northstar-payer-determination
description: Produce a structured Northstar Health Plan payer-operations determination by querying the shared read-only environment over the network and returning exactly one JSON object that conforms to the task's answer_template.json, including the standard basis_audit trail. Covers UM prior-authorization determinations, pharmacy appeal & manufacturer-assistance intake dispositions, payment-integrity claim repricing, peer-to-peer summaries, and UM-finance margin-queue analysis.
---

# Northstar Payer-Operations Determination

You are handed a Northstar Health Plan payer-operations work item. Review the
relevant records in the shared **read-only** environment and return **exactly one
JSON object** that conforms to the task's `answer_template.json`, ending in the
standard `basis_audit` block.

## Inputs (under the task's `input/` directory — read all three first)

- `prompt.txt` — the narrative request: target ID, requester role, reporting
  date/period, and what the deliverable must include.
- `payloads/task_context.json` — machine-readable parameters. The **target
  business ID** key varies by archetype (`target_business_id`, `business_id`,
  `target.claim_id`, `target.case_id`, `work_item.case_id`, etc.). Also carries
  `requester_role`, `reporting_date`/`reporting_period`, the environment access
  block, and any task-specific parameters (queue row IDs, thresholds,
  total-cost definitions, appeal windows). Honor these verbatim.
- `payloads/answer_template.json` — the **authoritative output contract**:
  required top-level keys, per-field types/enums, list ordering rules, numeric
  precision, `additional_fields_allowed`, and the `basis_audit` schema. It is
  the source of truth for the shape of your answer.

## Environment access — network only

Reach the environment exactly as described in `environment_access.md` (details
in `references/environment_and_data_model.md`). **Never** open, read, grep, or
otherwise inspect environment source files, generated data files, SQLite
database files, manifests, or setup scripts — use the HTTP endpoints only.

- Base URL: from `environment_access.md`.
- `GET /api/...` business endpoints are **open** (no auth): `/portal`,
  `/api/tables`, `/api/cases`, `/api/cases/{case_id}`, `/api/policies`,
  `/api/policies/{policy_id}`, `/api/documents/{document_id}`,
  `/api/rate-schedules`, `/api/appeals`.
- `POST /sql/query` requires header `Authorization: Bearer pa-review-token-014`
  and JSON body `{"sql": "<SQL>"}` (SQLite dialect). Response shape:
  `{"columns":[...], "rows":[...], "row_count":N, "max_rows":500, "limited":bool}`.
  **Check `limited`** — if true, narrow your query (add `WHERE`/`LIMIT`) until it
  is false so no rows are silently dropped.

Use `GET /api/tables` to confirm the current schema, then use SQL for joins and
targeted retrieval and the `GET /api/...` endpoints for single-record lookups.

## Procedure

1. **Read the three inputs.** Capture the target business ID, role, reporting
   date/period, and any task parameters. Note the exact required keys, enums,
   and ordering rules from the template.
2. **Classify the archetype.** From role + service domain + requested output,
   map to one of the archetypes in `references/task_archetypes.md`. This fixes
   the `source_precedence` rule and the business logic to apply.
3. **Gather evidence (network only).** Pull the target record and every related
   record the archetype needs. Prefer the **current/effective** record and
   identify any **stale/legacy alternative** that must be rejected or excluded.
   Apply date, `plan_type`, modifier, and version filtering to pick the
   controlling record.
4. **Compute the determination** per the archetype logic and the template's
   enums. Apply task_context parameters verbatim — e.g., use only the listed
   queue row IDs; the given threshold; the given total-cost definition; the
   given appeal window.
5. **Build the `basis_audit`** per `references/basis_audit.md`: pick
   `source_precedence` for the archetype; populate `controlling_record_ids`,
   `exception_record_ids`, and `precedence_record_order` using the prescribed
   orderings.
6. **Emit one JSON object** conforming to `answer_template.json`. No markdown,
   no comments, no prose outside the JSON. Follow
   `references/output_conventions.md` (list orderings, currency to cents,
   `null` for absent modifiers, date/ratio formats, integer units).
7. **Self-check** against the template: every required top-level key present;
   every enum value in the allowed set; every list in the specified order;
   `additional_fields_allowed` respected; numeric precision correct; no extra
   keys when disallowed.

## References

- `references/environment_and_data_model.md` — endpoint behavior, SQL wire
  format, and the full table/column data model.
- `references/task_archetypes.md` — the task archetypes, what each reviews, key
  outputs, and the `source_precedence` mapping.
- `references/basis_audit.md` — the `basis_audit` structure and ordering rules
  (identical across all templates) plus the `source_precedence` decision table.
- `references/output_conventions.md` — JSON-only output, list orderings, and
  numeric/date/null conventions.
