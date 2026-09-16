---
name: northstar-payer-operations
description: Payer operations analyst for Northstar Health Plan. Navigate a shared read-only SQL and API environment for utilization management, prior authorization, pharmacy appeals, payment integrity repricing, peer-to-peer final determinations, and therapy margin analysis. Use when the task is a Northstar payer workflow (UM nurse review, appeals coordinator, payment integrity analyst, peer-to-peer coordinator, or UM-finance queue analysis) that requires structured determination outputs with business audit trails.
---

# Northstar Payer Operations

Shared payer-operations environment for UM, appeals, payment review, and queue analysis. Every task uses the same environment and follows three stages: discover the schema, gather the evidence, and produce the determination.

## Environment

Base URL from the task context. All requests need:

```
Authorization: Bearer pa-review-token-014
```

**SQL endpoint** (primary tool):

```
POST {base}/sql/query
Content-Type: application/json
{"sql": "<query>"}
```

Max 500 rows per query. Use `SELECT * FROM {table} WHERE …` to pull evidence for the target business ID.

**Business REST endpoints** (use when they provide a more direct path):

- `GET /api/tables` — full schema listing
- `GET /api/cases` — all case summaries
- `GET /api/cases/{case_id}` — single case
- `GET /api/policies` — all policies
- `GET /api/policies/{policy_id}` — single policy
- `GET /api/documents/{document_id}` — single document
- `GET /api/rate-schedules` — all rate schedules
- `GET /api/appeals` — all appeal records

## Workflow

### Stage 1: Orient

1. Read the prompt and `task_context.json` for the target business ID, requester role, and answer template.
2. Read the answer template to know every required field, enum, ordering rule, and precision constraint.
3. Query `sqlite_master` or `/api/tables` to confirm available tables. Read [schema.md](references/schema.md) when you need column-level detail.

### Stage 2: Gather Evidence

Pull every record related to the target business ID. The typical query pattern:

```sql
SELECT * FROM cases          WHERE case_id = '{target}'
SELECT * FROM request_lines   WHERE case_id = '{target}'
SELECT * FROM documents       WHERE case_id = '{target}'
SELECT * FROM document_facts  WHERE case_id = '{target}'
SELECT * FROM case_criteria   WHERE case_id = '{target}'
SELECT * FROM authorizations  WHERE case_id = '{target}'
SELECT * FROM members         WHERE member_id = (SELECT member_id FROM cases WHERE case_id = '{target}')
SELECT * FROM policy_criteria WHERE policy_id = (SELECT policy_id FROM cases WHERE case_id = '{target}')
```

For workflow-specific tables, see [workflows.md](references/workflows.md).

**Document staleness rule:** A document with `is_current = 0` is stale. Stale documents must go in `excluded_documents` / `exception_record_ids`, never as controlling evidence.

### Stage 3: Produce the Determination

1. **Map criteria**: Compare `case_criteria` results and `document_facts` against `policy_criteria`. Each criterion is `met`, `not_met`, `unclear`, or `not_applicable`.

2. **Decide recommendation**: Based on criteria results:
   - All `met` → approve / approval letter
   - Any `not_met` with `result_if_missing = "deny"` → deny / adverse determination
   - Any `not_met` or `unclear` with `result_if_missing = "pend"` → pend for information

3. **Build the basis_audit**:
   - `source_precedence`: Choose from the six defined rules based on the business priority at play.
   - `controlling_record_ids`: Document IDs, criteria IDs, claim line IDs, or policy IDs that directly control the result. Order by operational evidence order.
   - `exception_record_ids`: Stale documents, unmet criteria, missing information, or excluded records. Order: criteria/route gaps before stale/excluded records.
   - `precedence_record_order`: Controlling then exception records in source-precedence order, highest priority first.

4. **Fill the answer template exactly**: Every field, every enum value, every ordering rule as the template specifies. Use `null` for absent modifiers, not empty strings. Round currency to two decimal places. Use integer service units. Dates in `YYYY-MM-DD`.

## Ordering Rules (recurring)

- Document IDs: ascending
- CPT codes: ascending
- Claim lines: source claim line order
- Medication names: alphabetical
- Segments (below_threshold / charge_sensitive): alphabetical by enum value
- Enum lists with fixed choices: use the order shown in choices
- basis_audit precedence: controlling then exceptions, highest priority first
- Exception records: criteria/route gaps before stale/excluded records

## Enum Reference for basis_audit.source_precedence

| Value | When to Use |
|---|---|
| `current_clinical_records_over_stale_export` | Current documents control; stale export records are excluded |
| `payer_appeal_before_manufacturer_assistance` | Appeal evidence takes priority over assistance program data |
| `effective_benchmark_by_plan_modifier_and_date` | Benchmark selection by current effective dates, rejecting stale schedules |
| `new_patient_specific_p2p_information` | P2P discussion outcome plus clinical evidence; new info may change the review |
| `margin_threshold_then_charge_sensitivity` | Below-threshold rows control; charge-sensitive rows are secondary |
| `appeal_deadline_then_clinical_then_payment_integrity` | Appeal deadline priority, then clinical records, then payment data |

## Detailed Workflows

For step-by-step patterns with query examples, field mappings, and computation rules for each business operation, read [workflows.md](references/workflows.md). Load it when you need:
- UM prior authorization determination procedure
- Pharmacy appeals intake with manufacturer assistance screen
- Payment integrity claim repricing against benchmarks
- Peer-to-peer final determination with appeal deadline calculation
- Therapy margin queue analysis with threshold and charge sensitivity
