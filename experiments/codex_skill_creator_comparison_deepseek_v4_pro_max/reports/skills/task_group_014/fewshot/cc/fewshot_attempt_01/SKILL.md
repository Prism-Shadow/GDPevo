---
name: northstar-ops
description: Solve Northstar Health Plan payer-operations tasks that require querying a shared REST+SQL environment and returning structured JSON conforming to a supplied answer template. Use this skill whenever the prompt mentions Northstar Health Plan, payer operations, UM review, prior authorization, pharmacy appeals, payment integrity, claim repricing, peer-to-peer, margin queue analysis, or any task instructing you to use a shared payer-operations environment with a SQL endpoint and bearer token.
---

# Northstar Payer Operations

Solve structured Northstar Health Plan payer-operations tasks using the shared
environment. Every task shares the same access pattern: read the prompt plus
two payloads, query the environment, apply business rules, and return a single
JSON object matching the supplied answer template.

## Environment Access

The prompt names a base URL with a placeholder. Use the running environment to
resolve it: check `environment_access.md` or an equivalent env-access file in
the workspace, or confirm the concrete URL from the task environment.

All tasks use the same environment credentials:

- SQL endpoint: `POST /sql/query` at the base URL
- Authorization header: `Authorization: Bearer pa-review-token-014`
- Available REST endpoints: `GET /`, `GET /portal`, `GET /api/tables`,
  `GET /api/cases`, `GET /api/cases/{case_id}`, `GET /api/policies`,
  `GET /api/policies/{policy_id}`, `GET /api/documents/{document_id}`,
  `GET /api/rate-schedules`, `GET /api/appeals`

Do not inspect environment source files, SQLite files, manifests, or setup
scripts directly. Use only the REST endpoints and the SQL query endpoint.

## Input Files

Every task supplies two payloads under `input/payloads/`:

**`task_context.json`** — Business context for this specific request. Contains
the target business IDs, requester role, reporting date, environment access
details, and local memos with operational hints. Read this first to understand
what records you need to find.

**`answer_template.json`** — The exact output schema. Every field, enum choice,
ordering rule, precision constraint, and normalization note is authoritative.
The template tells you exactly what to return. Study it before you start
querying so you know which data to collect.

Read both payloads before touching the environment.

## Workflow

### 1. Orient yourself

Read the prompt, then `task_context.json`, then `answer_template.json`. Note:

- The target business ID (the case, claim, appeal, or queue you are resolving)
- The requester role (this tells you which domain and business rules apply)
- Every required top-level key and every nested object key from the template
- The allowed enum values for every constrained field
- Any ordering rules the template specifies
- Any precision rules (currency to cents, dates to YYYY-MM-DD, null for absent
  modifiers, etc.)

The `local_memo` and `work_item` fields in task_context often contain critical
operational details: service domain, business due dates, formulas, or specific
instructions about how to calculate values.

### 2. Explore the environment

Start with `GET /` and `GET /portal` to understand the available data model.

Then use `GET /api/tables` to see the table catalog for SQL queries. For each
target ID, query the relevant business endpoints and SQL tables:

- `GET /api/cases/{case_id}` for case-level information
- `GET /api/policies/{policy_id}` for clinical or coverage policy criteria
- `GET /api/documents/{document_id}` for clinical documents, evaluations,
  plans of care, diagnostic reports, or P2P event records
- `GET /api/rate-schedules` for benchmark rate data (payment integrity tasks)
- `GET /api/appeals` for appeal records (pharmacy and appeal tasks)
- `POST /sql/query` with `SELECT *` queries against the tables discovered
  through `GET /api/tables`

The SQL endpoint accepts a JSON body with a `query` field containing the SQL
string. Use it to join records, filter by case/claim ID, and collect all the
facts the template demands.

### 3. Classify records

Every answer template requires you to distinguish controlling records from
exception/gap records. This is the core business judgment. Apply these rules
drawn from the five canonical task patterns:

**Source-precedence rules** — Choose the one that matches the task domain:

| Rule | When to use it |
|------|----------------|
| `current_clinical_records_over_stale_export` | UM nurse review, prior authorization: current clinical documents (evals, POCs) take precedence over stale or outdated records |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeals: the payer appeal record and documented trial evidence control before manufacturer assistance program data |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity / claim repricing: the current effective benchmark schedule (by plan, modifier, date) replaces any stale legacy schedule |
| `new_patient_specific_p2p_information` | Peer-to-peer: P2P event findings and direct clinical evidence control the final determination |
| `margin_threshold_then_charge_sensitivity` | Margin queue: rows below the revenue-to-cost threshold are the primary action items; charge-sensitive rows above threshold are monitored separately |
| `appeal_deadline_then_clinical_then_payment_integrity` | Multi-factor appeals: deadline compliance is first gate, clinical evidence next, payment integrity last |

**Controlling records** are the environment records that directly determine the
result: current clinical documents, the active benchmark schedule, the P2P event,
the appeal record, the margin queue rows. Use the environment's native record
IDs (DOC-*, APL-*, TRIAL-*, BM-*, P2P-*, CL-*, SM-*, etc.).

**Exception/gap records** are stale or superseded records, missing criteria,
missing packet items, or non-record gaps (like `household_income_proof`). List
criteria gaps before stale records, per the template ordering rule.

**Evidence vs. excluded documents**: When the template asks for `evidence_documents`
and `excluded_documents`, put current clinical records in evidence and stale
or superseded records in excluded. Order both lists ascending by document ID.

### 4. Build the criteria results

Most templates include a `criteria_results` object mapping criterion IDs to
outcomes. Available outcome values across all domains:

- `met` — the criterion is clearly satisfied by environment records
- `not_met` — the criterion is clearly not satisfied
- `partial` — partly satisfied (pharmacy failure criteria only)
- `unclear` — insufficient information to determine
- `not_applicable` — criterion does not apply to this case

Criterion IDs follow domain prefixes: `PT-` for physical therapy, `DRUG-` for
pharmacy, `PET-` for cardiac PET imaging. Use exactly the keys the template
requires, in the order the template lists them.

### 5. Handle domain-specific patterns

**Prior authorization (UM nurse):** Compare requested therapy lines against
policy criteria and current clinical evidence. Classify documents as evidence
or excluded. For standard therapy reviews, approved units are integer service
units across the approved date range. The CPT list is ascending.

**Pharmacy appeal:** Distinguish documented drug trial failures from
undocumented or insufficient ones. Documented means a trial record exists in
the environment with clear outcome evidence. Insufficient means a record exists
but does not adequately document a failure. The appeal path depends on whether
the case is expedited. The appeal deadline is typically 30 calendar days from
the denial date for standard internal appeals, or 180 days from the adverse
determination for internal appeals when specified.

**Payment integrity / claim repricing:** Compare the paid amounts against the
current benchmark schedule. Reject stale schedules. Recovery amount is the
difference between correct allowed and paid totals; use the absolute difference
even when the correction is upward (the template's `recovery_amount` field
represents the correction magnitude, not a signed value, unless the template
explicitly says otherwise). Compute `correct_allowed_amount` per line by
multiplying the benchmark rate by claim-line units, then sum for the total.

**Peer-to-peer:** Determine whether the P2P supplied new patient-specific
information that materially changed the review. If the P2P outcome is
`uphold_intended_adverse_decision`, set `new_information_changed_review` to
`false` (the intended decision stood). List any PET-over-SPECT factors that
remain unsupported. Calculate the internal appeal deadline as 180 calendar days
from the final adverse determination date when the plan specifies that window.

**Margin queue:** Compute `total_cost` as `variable_cost + fixed_cost_allocated`
from the environment data. Compute `margin` as `revenue - total_cost`. Compute
`revenue_to_cost_ratio` as `revenue / total_cost` to 4 decimal places. A row is
`below_threshold` when the ratio is strictly less than the threshold (typically
1.2). A row is `charge_sensitive` based on the flag from the source data. The
top issue is the below-threshold row with the lowest ratio (largest gap).
Compute `gap_to_120pct` as `(1.2 * total_cost) - revenue` for that top issue.
Negative margins produce ratios below 1.0.

### 6. Build the basis_audit

Every task requires a `basis_audit` with this exact structure:

```json
{
  "source_precedence": "<one of the six rules>",
  "precedence_record_order": ["<highest-priority first>", "..."],
  "controlling_record_ids": ["<records that control the result>", "..."],
  "exception_record_ids": ["<gaps, stale records, missing items>", "..."]
}
```

**`source_precedence`**: Pick the single best-matching rule from the table above.

**`precedence_record_order`**: List controlling records then exception records,
highest priority first. This shows the full decision trail.

**`controlling_record_ids`**: Only the records that directly control the result.
Order them by operational evidence order (the order in which they were reviewed
or the order in which they appear as evidence).

**`exception_record_ids`**: Criteria or route gaps before stale or excluded
records when both appear. Include non-record gap identifiers (like
`household_income_proof` or criterion IDs) when they are the reason for
a pending, denial, or information request.

## Output Rules

1. Return exactly one JSON object. No markdown fences, no prose, no commentary.
2. Every key the template marks as required must be present.
3. Use exactly the enum values the template defines. Do not invent new ones.
4. Follow all ordering rules: alphabetical, ascending, claim-line order,
   operational evidence order, packet order, or any other order the template
   specifies.
5. Use `null` for absent modifiers, never an empty string.
6. Round currency to two decimal places (cents). Use JSON numbers.
7. Use YYYY-MM-DD for dates. Use `null` for dates only when the template
   explicitly allows it.
8. Do not add extra fields unless the template says `additionalProperties` or
   `additional_fields_allowed` is true.

## Common Pitfalls

- **Using stale records**: Always check whether a record is current. A clinical
  document from two years ago that the template calls "stale" goes in excluded
  documents, not evidence.
- **Wrong source precedence**: The precedence rule must match the task domain.
  A pharmacy appeal does not use `current_clinical_records_over_stale_export`.
- **Forgetting null for absent modifiers**: An empty string `""` is not the
  same as `null`. The template explicitly requires `null`.
- **Currency precision**: Round to cents. A value of `235` is fine as `235.0`
  or `235.00` in JSON — both represent the same number. But `235.001` does not.
- **Missing exception records**: When a denial or information request is driven
  by a missing criterion, the criterion ID belongs in `exception_record_ids`.
- **Wrong ratio calculation**: `revenue_to_cost_ratio` is `revenue / cost`, not
  `cost / revenue`. Below-threshold means the ratio is less than the threshold.
- **Ordering**: When the template says "ascending document_id", sort by the
  document ID strings in ascending order. When it says "alphabetical by enum
  value", sort alphabetically. When it says "claim-line order", preserve the
  order from the source claim or environment data.

## Reference

See [references/patterns.md](references/patterns.md) for a detailed breakdown
of each task domain, field-by-field mappings, and additional examples of
correct record classification from the five canonical training tasks.
