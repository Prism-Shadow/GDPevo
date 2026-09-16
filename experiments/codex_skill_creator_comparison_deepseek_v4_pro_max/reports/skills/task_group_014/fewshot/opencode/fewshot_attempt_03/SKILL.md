---
name: northstar-payer-ops
description: Produce structured payer-operations determinations for Northstar Health Plan work items. Use this skill whenever the prompt involves Northstar Health Plan payer operations, utilization management nurse review, pharmacy appeals coordination, payment integrity claim repricing, peer-to-peer summaries, therapy margin queue analysis, or any task that references the Northstar payer-operations environment with the /sql/query endpoint and bearer token pa-review-token-014. Do not use for general healthcare questions unrelated to the Northstar environment.
---

# Northstar Payer Operations

You are producing a structured determination using the shared Northstar payer-operations environment. Every task follows the same core workflow: connect, discover the schema, gather all relevant data for the target business identifier, apply the domain-specific business rules, and return a single JSON object matching the provided answer template.

## Environment Connection

The environment is accessed at a base URL provided in the prompt (referenced as `<TASK_ENV_BASE_URL>` or a concrete URL). Use these endpoints:

```bash
# Schema discovery (always run first)
curl -s <BASE_URL>/api/tables | python3 -m json.tool

# SQL queries (primary data access)
curl -s -X POST <BASE_URL>/sql/query \
  -H "Authorization: Bearer pa-review-token-014" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT ..."}'
```

The SQL endpoint requires the field name `sql` (not `query`). The response contains `columns` (list of column name strings), `rows` (list of row objects), and `row_count`.

Business REST endpoints exist as supplements (`GET /api/cases`, `GET /api/cases/{case_id}`, `GET /api/policies`, `GET /api/documents/{document_id}`, `GET /api/rate-schedules`, `GET /api/appeals`) but SQL is the primary data gathering path. Prefer SQL joins over calling individual REST endpoints one at a time.

## Schema Discovery

Before querying data, read the full table catalog from `GET /api/tables`. The response lists every table with column names, types, primary keys, and not-null constraints. Key tables and their relationships are documented in [references/schema-map.md](references/schema-map.md). Read that reference for the full table catalog with join paths.

## Data Gathering Strategy

For any work item, follow this three-pass approach:

**Pass 1 — Core record.** Pull the primary record by its business ID from the prompt.

**Pass 2 — Related records.** Join outward from the core record to collect all related context. Use a single multi-table query when practical, or parallel queries across tables. Always gather: member demographics, provider details, plan/coverage info, policy and policy criteria, case-specific criteria results, request lines, documents with `is_current` flag, and authorization records.

**Pass 3 — Domain-specific data.** Depending on the work type, also query: `payment_benchmarks` for claim repricing, `drug_trials` and `assistance_screen` for pharmacy appeals, `p2p_events` for peer-to-peer, or `service_margin` for margin queue analysis.

## Answer Template Adherence

Every task provides an answer template (in `input/payloads/answer_template.json` or referenced in the prompt). This template is the output contract. Read it carefully and follow every constraint:

- **Required top-level keys.** Return every key listed in `required_top_level_fields`. Do not add keys unless `additional_properties` or `additional_fields_allowed` explicitly permits it.
- **Enum values.** Use exactly the string values from `choices` or `value_enum` arrays. Do not invent new values.
- **Type matching.** Match the declared types: `string`, `integer`, `number`, `boolean`, `list`, `object`, `list[string]`, `list<object>`.
- **Ordering rules.** When a field has an ordering spec, sort items accordingly (ascending, alphabetical, operational order, claim-line order).
- **Numeric precision.** Round to the specified decimal places. For currency in USD, round to two decimal places. For ratios, use four decimal places.
- **Date format.** Use `YYYY-MM-DD` format for all dates.
- **Null handling.** Use `null` (JSON null, not the string `"null"`) for absent values only when the schema explicitly allows it.
- **Output format.** Return **only** the JSON object. No markdown fences, no prose, no commentary before or after the JSON.

## Business Rules by Domain

### Physical Therapy Prior Authorization

When the service domain is `physical_therapy` and the request type is `prior_authorization`:

**Criteria mapping.** The five PT criteria are `PT-ACTIVE` (active plan), `PT-DEFICIT` (functional deficit), `PT-DX` (qualifying diagnosis), `PT-POC` (plan of care on file), and `PT-UNITS` (units within policy limits). Determine each from `case_criteria` joined with `document_facts`. The `evidence_fact_ids` column in `case_criteria` links to `fact_id` in `document_facts`. A criterion is `met` when the result is `met`; `not_met` when `not_met`; `unclear` when evidence is ambiguous; `not_applicable` when irrelevant.

**Unit calculation.** The standard PT authorization period is 2 visits per week for 12 weeks = 24 units. Approved units come from `authorizations.approved_units` or, when no prior auth exists, from the policy-standard calculation.

**Authorization fields.** The auth_number follows the pattern `NPA-` prefix. Approved CPT codes come from `request_lines.cpt_code` and `authorizations.approved_cpt` (a comma-separated list in the database). Sort CPT codes ascending. The standard PT modifier is `GP`.

**Evidence vs. excluded documents.** Current documents (`is_current = 1`) with relevant clinical facts are evidence documents. Stale documents (`is_current = 0`) or documents from outdated export sources are excluded. Order document IDs ascending.

**Recommendation routing:**
- All criteria met → `approve` / `nurse_approval` / `issue_approval`
- Any criterion `not_met` or `unclear` → `pend_for_information` / `pending_information` / `request_more_information`
- Medical necessity question → `escalate_to_md` / `medical_director_review`

### Pharmacy Coverage Appeal and Assistance Intake

When the work type is a pharmacy/coverage appeal:

**Drug identification.** The drug name comes from the appeal case context. Supported drugs: Vraylar, Dupixent, Humira, Ozempic, Rinvoq, Skyrizi.

**Appeal path and deadline.** Read from the `appeals` table. The appeal deadline is 30 calendar days from the denial date. Check `expedited_attestation` to determine if expedited. The appeal path (`standard_internal`, `expedited_internal`, `external_review`) comes from `appeal_path`.

**Medication trial classification.** Query `drug_trials` by case_id:
- `documented_failures`: medications where `documented = 1` and the outcome indicates failure (e.g., `failed`, `intolerable`, `ineffective`). List in alphabetical order.
- `undocumented_or_insufficient_failures`: medications where `documented = 0` or the outcome is insufficient (e.g., `unknown`, `pending`, `partial`). List in alphabetical order.

**Criteria results.** The four drug criteria:
- `DRUG-AUTH` — prior authorization exists or is not required
- `DRUG-DENIAL` — a coverage denial is on file
- `DRUG-RATIONALE` — prescriber clinical rationale is documented
- `DRUG-FAILURES` — required formulary failures are demonstrated

Results come from `case_criteria`. `DRUG-FAILURES` is `partial` when some but not all required failures are documented.

**Packet requirements.** Required items are those the appeal and assistance workflows need based on the criteria and appeal records. Missing items are required items not found in the environment data. Order required items with payer appeal items before assistance items. Order missing items with appeal evidence gaps before assistance information gaps. See [references/packet-items.md](references/packet-items.md) for the full item catalog.

**Assistance program.** Map drug to program: Vraylar → Vraylar Connect, Dupixent → Dupixent MyWay, Humira → Humira Complete. Status is `eligible_ready` when all criteria and documentation are complete; `eligible_missing_information` when eligible but missing required fields; `not_eligible` when criteria are not met; `not_applicable` when no program matches.

**Next action:**
- Missing required information → `request_more_information`
- All complete and eligible → `file_appeal` or `submit_assistance_application`

### Payment Integrity Claim Repricing

When the work type is payment integrity or claim repricing:

**Benchmark selection.** Query `payment_benchmarks` filtering by the claim's `payer` (from `claims` table), the member's `plan_type` (from `members` table), and the CPT/modifier pairs from `claim_lines`. Match on `service_domain` when available.

Distinguish current from stale benchmarks by comparing `effective_start` and `effective_end` dates against the service date or reporting date. The current benchmark is the one with effective dates covering the service period. A stale benchmark is one with expired effective dates or from a different source schedule.

**Line-level correction.** For each claim line (ordered by `line_number`):
- `paid_amount` comes from `claim_lines.paid_amount`
- `correct_allowed_amount` = benchmark `allowed_amount` x `units`
- `recovery_amount` = `correct_allowed_amount` - `paid_amount` (positive means underpayment, `correct_upward`)
- `disposition` is `correct_upward` when recovery > 0, `correct_downward` when recovery < 0

**Totals:**
- `paid_total` = sum of all line `paid_amount`
- `correct_allowed_total` = sum of all line `correct_allowed_amount`
- `recovery_amount` = `correct_allowed_total` - `paid_total`

**Benchmark source naming.** Use `source_name` from `payment_benchmarks` for `benchmark_source`. Use `source_version` for `benchmark_version`. The `stale_source_rejected` is the name of the expired or inapplicable schedule.

**Resubmission route.** `payment_integrity_correction` for standard repricing. Priority is `standard` unless urgency flags indicate otherwise.

**Auth number.** Read from `claims.auth_number` or from the associated `authorizations` table.

### Peer-to-Peer Summary

When the work type is peer-to-peer:

**P2P event data.** Query `p2p_events` by `case_id`. Key fields: `p2p_id`, `provider_argument`, `new_information`, `outcome`, `final_status`. The `outcome` maps to `p2p_outcome`: `overturned` → `overturn_to_approval`; `upheld` → `uphold_intended_adverse_decision`; absent/null → `not_applicable`.

**New information check.** Set `new_information_changed_review` to `true` only when the P2P supplied new patient-specific information that materially changed a criterion assessment. If the information is present but does not change any result, set it to `false`.

**Criteria for PET MPI (cardiac imaging domain):**
- `PET-IND` — appropriate indication for PET myocardial perfusion imaging
- `PET-FACTOR` — at least one PET-over-SPECT factor is supported

**PET-over-SPECT factors.** The three factors to check are `prior_equivocal_spect`, `bmi_limitation`, and `attenuation_artifact`. List any that remain unsupported after P2P, in the order shown above. If all three are unsupported, list all three; if some are supported, only list the unsupported ones.

**Unresolved criteria.** List any criterion IDs whose result is `not_met` or `unclear` after the P2P. List in ascending criterion ID order.

**Internal appeal deadline.** When the final determination is adverse (denied), the internal appeal deadline is 180 calendar days from the final adverse determination date. Use `null` when no adverse determination exists.

**Recommended alternative.** `SPECT MPI` when PET is denied but SPECT is clinically appropriate; `PET MPI` when PET is approved; `none` when no alternative applies.

**Letter type.** `approval` for approved, `denial` for denied, `partial_denial` for partially approved, `no_letter` for non-final outcomes.

### Therapy Margin Queue Analysis

When the work type is margin/finance queue analysis:

**Data source.** Query `service_margin` using the `month_id` values listed in the task context's `queue_row_ids`.

**Key calculations:**
- `total_cost` = `variable_cost` + `fixed_cost_allocated`
- `margin` = `net_revenue` - `total_cost`
- `revenue_to_cost_ratio` = `net_revenue` / `total_cost` (round to 4 decimal places)

**Threshold check.** A row is `below_threshold` when its `revenue_to_cost_ratio` < `threshold_revenue_to_cost_ratio` (from the task context, typically 1.2).

**Charge sensitivity.** Read directly from the `charge_sensitive` column (integer: 1 = true, 0 = false).

**Recommended actions:**
- `below_threshold` = true → `payer_contract_review`
- `below_threshold` = false and `charge_sensitive` = true → `monitor_charge_sensitive`
- `below_threshold` = false and `charge_sensitive` = false → `monitor_no_action`

**Segment aggregation.** `below_threshold_segments` lists distinct payer_segments from rows where `below_threshold` is true (alphabetical order). `charge_sensitive_segments` lists distinct payer_segments from rows where `charge_sensitive` is true (alphabetical order).

**Top issue.** Among rows with `below_threshold` = true, identify the one with the largest dollar gap (largest shortfall relative to threshold). The `top_issue` is `"{payer_segment}_{cpt_code}"` for that row. If no rows are below threshold, use `"none"`.

**Gap to 120%.** For the top issue row: `gap_to_120pct` = (`total_cost` x `threshold_revenue_to_cost_ratio`) - `net_revenue`. Round to 2 decimal places. When `top_issue` is `"none"`, the gap is 0.

## Basis Audit Construction

Every determination requires a `basis_audit` object with four required keys: `source_precedence`, `controlling_record_ids`, `exception_record_ids`, and `precedence_record_order`. Read [references/basis-audit.md](references/basis-audit.md) for the detailed construction guide covering all six precedence rules and the ordering conventions for each array.

### Quick Reference

**Select the source_precedence rule by domain:**

| Domain | Rule |
|--------|------|
| Prior authorization with current vs. stale documents | `current_clinical_records_over_stale_export` |
| Pharmacy appeal with manufacturer assistance | `payer_appeal_before_manufacturer_assistance` |
| Claim repricing with benchmark schedules | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer with new clinical information | `new_patient_specific_p2p_information` |
| Margin queue analysis | `margin_threshold_then_charge_sensitivity` |
| Appeal with clinical and payment integrity | `appeal_deadline_then_clinical_then_payment_integrity` |

**Populating the arrays:**
- `controlling_record_ids`: environment record IDs that directly determine the outcome. These are the database records whose values drive the final result (document IDs, trial IDs, benchmark IDs, claim line IDs, P2P event IDs, month IDs).
- `exception_record_ids`: record IDs explaining gaps, exclusions, or routing decisions. Also include non-record identifiers (like criterion IDs or field names as strings) when they represent gaps. List criteria/route gaps before stale/excluded records.
- `precedence_record_order`: all controlling and exception records combined, ordered by the selected precedence rule priority (highest first). When two records tie, controlling records come before exception records.

## Workflow Summary

For every Northstar task, execute this sequence:

1. **Read the prompt and payloads.** Identify the target business ID, the work type, the answer template, and any task context with specific instructions.
2. **Read the answer template thoroughly.** Note every required key, enum constraint, ordering rule, and precision requirement.
3. **Discover the schema.** Call `GET /api/tables` to confirm table and column availability.
4. **Gather data in three passes.** Core record → related records → domain-specific records.
5. **Apply domain business rules.** Use the rules in the corresponding section above for the work type.
6. **Construct the basis_audit.** Select the correct `source_precedence` rule and populate the record ID arrays.
7. **Output exactly one JSON object.** No markdown, no prose, no extra fields beyond the template contract.

## SQL Query Patterns

Use curl with the POST endpoint. The JSON body must have the key `sql`:

```bash
curl -s -X POST <BASE_URL>/sql/query \
  -H "Authorization: Bearer pa-review-token-014" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM cases WHERE case_id = '\''CASE-XX-XXX'\''"}'
```

The response shape is `{"columns": [...], "rows": [...], "row_count": N, "limited": false, "max_rows": 500}`.

When joining across tables, use standard SQL JOIN syntax. The database supports basic SQL: SELECT, FROM, JOIN, WHERE, ORDER BY, GROUP BY. String literals use single quotes. Escape single quotes in shell by using the `'\''` pattern within single-quoted curl strings.

For queries with multiple string conditions, consider using a Python helper script (see [references/sql-helper.md](references/sql-helper.md)) to avoid shell escaping issues.

## Common Pitfalls

- **Wrong JSON key for SQL.** The endpoint expects `"sql"`, not `"query"`. Using `"query"` returns an error.
- **Adding extra top-level keys.** The answer template's `additional_fields_allowed: false` means strict adherence. Do not add commentary fields.
- **Wrong enum values.** Always match the exact case and spelling from the template choices.
- **Incorrect audit precedence.** Select the precedence rule that matches the business domain from the table above.
- **Including markdown fences.** Return raw JSON, not ```json ... ```.
- **Ordering violations.** Pay attention to ordering rules on lists -- alphabetical, ascending, operational order, or claim-line order matter.
- **Date miscalculation.** Appeal deadlines and authorization periods use calendar days, not business days. Use Python's `datetime` for date arithmetic when needed.
- **Modifier null handling.** When a claim line or benchmark has no modifier, use `null` in JSON, not the string `"null"` or an empty string.
