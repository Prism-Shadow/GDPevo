---
name: northstar-payer-ops
description: Structured determination and audit-trail output for Northstar Health Plan payer operations. Query a shared SQL + REST environment to produce utilization management, pharmacy appeal, payment integrity, peer-to-peer, and margin-queue determinations as JSON matching a provided answer template. Use when the task requires (1) querying the Northstar payer environment, (2) building a structured JSON determination with a basis_audit trail, or (3) resolving payer workflows that span cases, claims, authorizations, policies, documents, appeals, benchmarks, or service-margin tables.
---

# Northstar Payer Operations

Use the shared payer-operations environment to query case, claim, authorization, policy, document, appeal, benchmark, and service-margin records and return a single structured JSON object matching the provided answer template. Every determination must include a `basis_audit` block that records the source-precedence rule, ordered record trail, controlling records, and exception records.

## Environment Access

The environment is accessed at the base URL provided in the task prompt or context as `<TASK_ENV_BASE_URL>`. Confirm the exact URL before issuing any request.

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` or `/portal` | Portal landing page |
| GET | `/api/tables` | List all database tables with column definitions |
| GET | `/api/cases` | List all cases |
| GET | `/api/cases/{case_id}` | Single case record |
| GET | `/api/policies` | List all policies |
| GET | `/api/policies/{policy_id}` | Single policy record |
| GET | `/api/documents/{document_id}` | Single document record |
| GET | `/api/rate-schedules` | List rate schedules |
| GET | `/api/appeals` | List all appeals |

### SQL Endpoint

```
POST /sql/query
Authorization: Bearer pa-review-token-014
Content-Type: application/json

{"query": "<SQL statement>"}
```

The endpoint returns JSON with a `rows` array and `columns` array. Use this for complex joins, filtered lookups, and cross-table analysis. Prefer REST endpoints for single-record fetches; use SQL for filtered multi-table queries. The bearer token is always `pa-review-token-014`.

### Workflow

1. Read the task prompt and the answer template to identify the target business ID, the required JSON shape, and any task-specific constraints.
2. Use REST endpoints (or SQL) to pull the target case, member, policy, and other context records.
3. Write focused SQL queries to extract claim lines, criteria results, document facts, drug trials, benchmarks, margin rows, or other detailed records as the task demands.
4. Apply the business rules in [references/business_rules.md](references/business_rules.md) relevant to the task domain.
5. Look up the full database schema in [references/schema.md](references/schema.md) when planning queries.
6. Construct the JSON answer strictly matching the template. Do not include prose, markdown, or commentary outside the JSON.
7. Build the `basis_audit` block last, after all evidence is assembled.

## Basis Audit (Every Answer)

Every determination JSON must include a `basis_audit` object with exactly four keys:

- `source_precedence` — one enum from the table below
- `precedence_record_order` — all controlling and exception record IDs in priority order (highest priority first)
- `controlling_record_ids` — records that directly control the result
- `exception_record_ids` — records that explain exclusions, denials, missing information, gaps, or route priority

### Source Precedence Rules

Choose the rule that matches the task's evidence hierarchy:

| Rule | When to Use |
|------|-------------|
| `current_clinical_records_over_stale_export` | Clinical document review where older/stale records must be excluded in favor of current records |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeal intake where payer appeal evidence precedes manufacturer assistance screening |
| `effective_benchmark_by_plan_modifier_and_date` | Claim repricing where the current effective benchmark by plan, modifier, and effective date controls |
| `new_patient_specific_p2p_information` | Peer-to-peer review where new patient-specific P2P information supersedes the earlier clinical record |
| `margin_threshold_then_charge_sensitivity` | Margin queue analysis where revenue-to-cost threshold classification precedes charge-sensitivity flagging |
| `appeal_deadline_then_clinical_then_payment_integrity` | Mixed workflows where appeal deadlines, clinical evidence, and payment integrity records are layered in that order |

### Ordering Rules

- `controlling_record_ids`: Use the operational evidence order (records that directly control the result).
- `exception_record_ids`: Business gap/exception order — criteria or route gaps before stale or excluded records when both appear.
- `precedence_record_order`: List controlling and exception records together in source-precedence priority, highest first.

Gap identifiers that are not environment record IDs (e.g., `household_income_proof`, `PET-FACTOR`, `prior_equivocal_spect`) may appear in `exception_record_ids` and `precedence_record_order` when they represent data gaps the environment cannot fill.

## Task-Specific Guidance

### UM Nurse Determination (Physical Therapy)

- Check `case_criteria` for criteria results; use `PT-ACTIVE`, `PT-DEFICIT`, `PT-DX`, `PT-POC`, `PT-UNITS` criterion keys.
- Inspect `documents` with `is_current` flag to separate current evidence from stale records.
- Use `document_facts` to verify clinical facts that support each criterion.
- Check `authorizations` for existing auth records (approved units, dates, CPT codes, modifier).
- The determination letter is `approval` when all criteria are met; `information_request` when pended; `adverse_determination` when denied.

### Pharmacy Appeal Intake

- Pull the `appeals` record for routing, deadline, and path.
- Query `drug_trials` for prior medication attempts; classify each as documented (documented=1) or undocumented/insufficient (documented=0).
- Use `case_criteria` with `DRUG-AUTH`, `DRUG-DENIAL`, `DRUG-RATIONALE`, `DRUG-FAILURES` keys.
- Query `assistance_screen` for manufacturer program status and missing fields.
- Payer appeal items precede manufacturer assistance items in packet ordering.
- If a prior medication fill record is missing but required for criteria, include it in `missing_packet_items` and `undocumented_or_insufficient_failures`.
- Calculate the appeal deadline: 30 calendar days from denial_date for standard internal appeals.

### Claim Repricing (Payment Integrity)

- Pull the `claims` record for paid_total, payer, and auth_number.
- Query `claim_lines` sorted by `line_number` for each line's CPT, modifier, units, and paid_amount.
- Query `payment_benchmarks` filtered by the claim's payer, plan_type, service_domain, and CPT codes.
- Reject stale benchmarks: prefer the benchmark with the most recent `effective_start` that covers the claim date. Name the stale source in `stale_source_rejected`.
- Correct allowed amount for each line = benchmark allowed_amount x line units.
- Recovery amount = correct_allowed_amount - paid_amount (positive = underpayment/upward correction, negative = overpayment/downward correction).
- Recovery amounts at the claim level: correct_allowed_total - paid_total.
- Use `null` for absent modifiers, not an empty string.

### Peer-to-Peer Summary (Cardiac Imaging)

- Pull the `p2p_events` record for outcome, new_information, and provider_argument.
- Check `case_criteria` for PET-IND and PET-FACTOR results.
- P2P outcome: `overturn_to_approval` if the P2P changed the decision; `uphold_intended_adverse_decision` if the denial stands.
- `new_information_changed_review`: true only when the P2P event's new_information field contains material new patient-specific data.
- Missing PET factors are drawn from `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact` — include each that remains unsupported after the P2P.
- Recommended alternative: `SPECT MPI` when PET is denied and SPECT is a valid alternative for that indication.
- Internal appeal deadline: 180 calendar days from the final adverse determination date. Use the P2P event date if the P2P was the final adverse step.

### Margin Queue Analysis

- Query `service_margin` filtered by the `queue_row_ids` from the task context.
- `total_cost` = variable_cost + fixed_cost_allocated.
- `margin` = net_revenue - total_cost.
- `revenue_to_cost_ratio` = net_revenue / total_cost (4 decimal places).
- `below_threshold`: true when revenue_to_cost_ratio < threshold (typically 1.2).
- `charge_sensitive`: true when the row's charge_sensitive flag is 1.
- `recommended_action`: `payer_contract_review` for below-threshold rows; `monitor_charge_sensitive` for above-threshold but charge-sensitive rows; `monitor_no_action` otherwise.
- `gap_to_120pct`: (1.2 x total_cost) - net_revenue for the top below-threshold issue.
- `top_issue`: the CPT code and payer_segment combination with the largest gap to 120% among below-threshold rows.

## Reference Files

- [references/schema.md](references/schema.md) — Full database schema with all 19 tables and column definitions. Load when planning SQL queries or exploring data relationships.
- [references/business_rules.md](references/business_rules.md) — Domain business rules, payer segments, policy criteria patterns, appeal deadline calculations, and operational classification logic.

## Output Format

- Return exactly one JSON object. No markdown, no prose, no commentary outside the JSON.
- Currency values: JSON numbers rounded to two decimal places (cents).
- Ratios: JSON numbers rounded to four decimal places.
- Dates: ISO 8601 calendar dates in YYYY-MM-DD format.
- Modifiers: Use `null` when absent, not an empty string.
- Enum values: Use the exact casing and underscore style from the answer template.
- Lists: Sort per the ordering rules in the template (ascending, alphabetical, operational order, or as specified).
- Do not add extra keys beyond what the template requires unless the template explicitly allows additional properties.

## Verification Checklist

Before finalizing, confirm:

1. Every required top-level key from the answer template is present.
2. The `basis_audit` block has all four keys and an appropriate `source_precedence` rule.
3. Controlling records form a coherent path from evidence to determination.
4. Exception records identify every gap, excluded record, or unresolved criterion.
5. Currency values are rounded to cents and sum correctly.
6. Dates are ISO 8601 YYYY-MM-DD.
7. Lists follow the ordering rules specified in the template.
8. No extraneous commentary or markdown outside the JSON.
