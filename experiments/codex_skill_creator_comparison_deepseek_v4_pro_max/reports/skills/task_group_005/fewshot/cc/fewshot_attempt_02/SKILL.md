---
name: erp-finance-close
description: Use this skill when the user needs to reconcile claims, AP bills, payments, prepaid schedules, GL accounts, vendor onboarding, or compliance screenings against a shared ERP finance REST API. Invoke it for close-review batches, stale-export cleanup, prepaid-amortization reconciliation, vendor risk-release calls, account-change payment gates, or any task that cross-references a local batch file against live API records and returns a structured JSON decision. The API base URL is always supplied by the runner as TASK_ENV_BASE_URL; endpoints are discoverable at /endpoints. Do not use this skill when the user needs general accounting advice, data entry without API access, or formatting-only tasks that lack a reconciliation step.
---

# ERP Finance Close & Reconciliation

This skill covers batch reconciliation and release-review tasks against a
shared ERP/compliance REST API. Every task follows the same core workflow:
discover endpoints, fetch current records for the batch, cross-reference
against local context, apply business rules, and return a single JSON
decision object.

## Quick start

1. Read the prompt and every local payload file.
2. Read the answer template so you know exactly what shape to return.
3. Call `GET <TASK_ENV_BASE_URL>/endpoints` and note which endpoints match the
   entities in the prompt (claims, bills, payments, vendors, prepaid invoices,
   GL balances, compliance, close logs).
4. Fetch the correct records for every ID in the batch. Most endpoints support
   exact-match query parameters; paginate with `limit` and `offset` as needed.
5. Join API records to batch entries by the primary key (`claim_id` or
   `business_id`). The join is the core of every task.
6. Read [references/patterns.md](references/patterns.md) for the decision
   framework that matches your task subtype.
7. Apply the rules, compute any aggregations (totals, UBO counts, variances),
   and fill the answer template fields exactly.
8. Return only valid JSON. Do not include narrative text outside the JSON.

## Currency and ordering conventions

- All currency amounts are USD. Report to two decimals.
- Sort every list of IDs ascending by the ID string.
- When a template demands a specific key order, preserve it exactly.

## API discovery and navigation

The API base URL is provided by the runner as `<TASK_ENV_BASE_URL>`. Call
`/endpoints` to see every available route. All endpoints listed in
[references/endpoints.md](references/endpoints.md) are known to exist; treat
that catalog as a lookup, not an assumption that every route will be live.

The API returns JSON arrays. Use query-string filters to narrow to the batch
identifiers you need. For example:

```
GET <TASK_ENV_BASE_URL>/api/claims?claim_id=CLM-YYYY-MMM-NNN
GET <TASK_ENV_BASE_URL>/api/compliance/ownership/BUS-YYYY-NNNN
```

When a single-ID path exists (e.g., `/api/compliance/ownership/{business_id}`),
prefer it over filtering a list endpoint. Call one ID at a time in parallel
when the batch is small.

## Answer template discipline

Every task ships an `answer_template.json` in the payloads. Read it before
fetching data so you know which fields must be populated, which keys are
required, and which enum values are allowed. The template defines both the
schema and, through property descriptions, the computation rules.

Key things to watch for in templates:
- `ordering` fields: sort IDs ascending by the named key.
- `allowed_values` / `required_members`: use only those values; never invent
  new ones.
- `precision: 2` on numbers: always two-decimal USD.
- `required_keys` / `required_top_level_keys`: every one must appear in the
  output, even if the value is an empty list or zero.

## Task subtypes

[references/patterns.md](references/patterns.md) details decision logic for
each family of task. Read the section that matches your prompt:

- **Claims close / reimbursement-AP**: classify claim_ids into payable,
  blocked, and paid by cross-referencing claim status, linked AP bills, and
  payment records.
- **Vendor onboarding risk**: classify business_ids as approve / awaiting_info
  / escalate by checking compliance ownership, registry, screening, and bank
  endpoints; count reportable UBOs and flag hard stops.
- **Prepaid close reconciliation**: reconcile prepaid invoice schedules against
  GL ending balances for specific accounts; compute schedule totals, variance,
  and flag invoices with default/missing terms or data exceptions.
- **Stale AP snapshot cleanup**: reconcile a stale CSV/export against live API
  claim/bill/payment records; assign a correction category to each stale row
  and determine the true batch readiness.
- **Account-change payment release**: check vendor and compliance records after
  account-change events; decide release/hold/escalate per business; flag bank
  mismatches, invalid tax IDs, expired licenses, and risk-score overrides.

## Edge cases and cross-checking

- A claim may have no linked AP bill, or a bill with no payment. Treat missing
  records as actionable signals, not errors.
- A vendor may appear in multiple compliance endpoints with conflicting data;
  the most restrictive signal (e.g., sanctions hit, closed bank) governs.
- Prepaid invoices with amortization terms of 0 or null are
  "default/missing term" -- flag them and still include them in schedule totals
  using whatever amortization data the record carries.
- When a stale snapshot row disagrees with live API data, the live data is the
  system of record. The snapshot is only context.
- Close-log entries record prior actions on a batch; check them when the
  template includes a `close_log_required` field to decide whether a fresh log
  entry is needed.
