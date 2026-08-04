---
name: northstar-payer-operations
description: Solve Northstar Health Plan payer operations tasks (UM review, appeals, payment integrity, P2P, margin analysis) by querying the shared REST+SQL environment and mapping responses to structured JSON answer templates.
tags: [northstar, payer, healthcare, prior-authorization, claims, appeals]
---

# Northstar Payer Operations Skill

## Purpose

This skill solves structured payer-operations tasks for Northstar Health Plan. Each task supplies a target business ID and an answer template. The agent retrieves records from the shared payer environment and returns a single JSON object conforming to the template.

## Environment

The environment is a REST+SQL service. The base URL is provided in each task prompt (typically `http://task-env:9014`). Use two access modes:

### REST Endpoints (GET)

| Endpoint | Use |
|---|---|
| `GET /api/cases/{case_id}` | Primary case record, criteria, documents, request lines, authorizations, P2P events |
| `GET /api/policies` | Active policy summaries |
| `GET /api/rate-schedules` | Payment benchmark schedules for repricing |
| `GET /api/appeals` | All appeal records (use to confirm target appeal) |
| `GET /api/documents/{document_id}` | Individual document detail if needed |

### SQL Queries (POST /sql/query)

Always include header `Authorization: Bearer pa-review-token-014` and `Content-Type: application/json`. Body: `{"sql": "<statement>", "params": []}`.

Allowed SQL: `SELECT`, `WITH`, `PRAGMA table_info(<table>)`. Start with `PRAGMA table_info` when you need column names.

Key tables: `cases`, `case_criteria`, `documents`, `document_facts`, `request_lines`, `claim_lines`, `claims`, `authorizations`, `appeals`, `p2p_events`, `drug_trials`, `assistance_screen`, `payment_benchmarks`, `service_margin`, `policies`, `policy_criteria`, `members`, `plans`, `providers`.

## Task Workflow

1. **Read the prompt and task context** — extract target ID, requester role, reporting date, service domain.
2. **Read the answer template** — study every required field, enum choices, ordering rules, and numeric precision.
3. **Collect environment data** — use REST endpoints for the target case, then SQL for any supporting tables.
4. **Map data to template** — translate environment facts into the answer shape. Respect enum values, sort orders, and null rules exactly.
5. **Return JSON only** — no markdown, prose, or explanation outside the JSON object.

## Domain-Specific Rules

### UM Nurse Determination (physical therapy)

- Evaluate criteria from the case's `criteria` array. Use the `result` field directly — the environment has already scored each criterion.
- `evidence_documents`: all documents with `is_current: 1`.
- `excluded_documents`: all documents with `is_current: 0` (stale exports, outdated records).
- `basis_audit.source_precedence`: use `"current_clinical_records_over_stale_export"` when stale records exist.
- Sort document IDs ascending.
- Recommendation maps directly from criteria results: all met → `"approve"`, any not_met → review denial path.

### Pharmacy Appeals Coordinator (drugs)

- Use both the case REST endpoint and SQL on `drug_trials` to classify medication failures.
- `documented_failures`: trials where `documented: 1`, lowercase medication name, alphabetical order.
- `undocumented_or_insufficient_failures`: trials where `documented: 0`, or where fill records are missing.
- `criteria_results`: copy from case `criteria` array. Use value `"partial"` when some but not all evidence exists.
- `required_packet_items`: list the packet items mentioned in appeal notes. Payer appeal items (denial, authorization, rationale, failure evidence) before assistance items (income proof). Do NOT include items that are evidence gaps but not standard packet requirements.
- `missing_packet_items`: appeal evidence gaps first, then assistance gaps.
- `assistance`: copy from case `assistance_screen`. Map `pending_missing_*` statuses to `"eligible_missing_information"`.
- `source_precedence`: `"payer_appeal_before_manufacturer_assistance"`.

### Payment Integrity Claim Repricing (cardiac imaging)

- Fetch claim lines from the case REST endpoint and benchmarks from `GET /api/rate-schedules` or SQL on `payment_benchmarks`.
- Match each claim line by `cpt_code`, `modifier` (treat null as exact match on null), `plan_type`, and `service_domain`.
- **Stale vs current**: check `effective_start` / `effective_end` against the service date. Current benchmarks have effective dates covering the service period. Stale (Legacy) schedules have ended effective periods.
- `correct_allowed_amount`: benchmark `allowed_amount` × `units`.
- `recovery_amount`: `correct_allowed_amount` − `paid_amount` (positive when underpaid, negative when overpaid — but use the underpayment amount per template instructions).
- All currency values rounded to 2 decimal places.
- `disposition`: `"correct_upward"` when recovery > 0, `"correct_downward"` when recovery < 0, `"no_change"` when 0.
- `benchmark_source`: the name from the current benchmark entry (e.g., `"Northstar Commercial Imaging Schedule"`).
- `benchmark_version`: the version string (e.g., `"2026Q2"`).
- `stale_source_rejected`: the name of the rejected stale source.
- `source_precedence`: `"effective_benchmark_by_plan_modifier_and_date"`.
- Sort lines in claim-line order (by `line_number`).
- Use `null` (JSON null) for absent modifiers, never empty string.

### P2P Coordinator (PET MPI)

- Collect case with P2P event and criteria from the REST endpoint.
- `criteria_results`: copy from the case criteria array.
- `unresolved_criteria`: list criterion IDs where the result is `"not_met"` and the gap is material. Even if the final decision is adverse, criteria whose requirements remain unmet and whose gap descriptions are meaningful belong here.
- `missing_pet_factors`: for PET MPI, list all PET-over-SPECT factors that remain unsupported. Order as shown in the template choices array.
- `p2p_outcome`: from the P2P event `outcome` field.
- `final_status`: from the authorization `status` field.
- `new_information_changed_review`: `true` only if the P2P's `new_information` field describes actual new patient-specific data that altered the review.
- `internal_appeal_deadline`: when final status is `"denied"`, add 180 calendar days to the P2P event date (use `scheduled_at`). Use `null` when no adverse determination.
- `recommended_alternative`: for denied PET, recommend `"SPECT MPI"`.
- `letter_type`: `"denial"` for fully denied, `"approval"` for approved, `"partial_denial"` for partially approved.
- `source_precedence`: `"new_patient_specific_p2p_information"`.

### Margin Queue Analysis (therapy finance)

- Query `service_margin` table using the `queue_row_ids` from the task context.
- `total_cost`: `variable_cost` + `fixed_cost_allocated`.
- `margin`: `net_revenue` − `total_cost`.
- `revenue_to_cost_ratio`: `net_revenue` / `total_cost`, 4 decimal places.
- `below_threshold`: `true` when ratio < `threshold_revenue_to_cost_ratio`.
- `charge_sensitive`: from the `charge_sensitive` column (1 → `true`, 0 → `false`).
- `recommended_action`: below threshold → `"payer_contract_review"`, charge sensitive → `"monitor_charge_sensitive"`, otherwise → `"monitor_no_action"`.
- `below_threshold_segments`: payer segments where any row is below threshold, alphabetical.
- `charge_sensitive_segments`: payer segments where any row is charge sensitive, alphabetical.
- `top_issue`: combine the payer segment and CPT of the row with the lowest revenue-to-cost ratio among below-threshold rows, formatted as `"{segment}_{cpt}"`.
- `gap_to_120pct`: `(threshold × total_cost) − net_revenue` for the top below-threshold row, rounded to 2 decimal places.
- `source_precedence`: `"margin_threshold_then_charge_sensitivity"`.

## Basis Audit Construction

Every answer includes a `basis_audit` object with four keys:

- **`source_precedence`**: pick the enum value matching the domain (see domain rules above).
- **`controlling_record_ids`**: list every environment record ID that directly drives the result (document IDs, benchmark IDs, trial IDs, P2P event IDs, policy IDs, row month_ids). Order by operational evidence priority.
- **`exception_record_ids`**: list records that represent gaps, denials, missing information, stale data, or exclusions. Include stale documents, undocumented trials, below-threshold rows, or denied criteria. Order: criteria/route gaps before stale/excluded records.
- **`precedence_record_order`**: concatenate controlling IDs first, then exception IDs, maintaining the order within each group. This field is the union in precedence order.

## Common Pitfalls

- **Do not guess enums**: always match the exact string from the template's choices.
- **Sort orders matter**: ascending document IDs, alphabetical segments, alphabetical medication names, claim-line order. Check each template's ordering rule.
- **Numeric precision**: ratios at 4 decimal places, currency at 2. Use JSON numbers, not strings.
- **Null modifier**: use JSON `null`, never `""` or `"null"`.
- **Unresolved criteria**: a criterion can be both `"not_met"` AND unresolved when the gap persists. List it in `unresolved_criteria` as well as recording `"not_met"` in `criteria_results`.
- **Stale records**: always check `is_current` on documents and `effective_start`/`effective_end` on benchmarks. Current beats stale.
- **Drug trials**: distinguish documented (`documented: 1`) from referenced-but-undocumented (`documented: 0`). The latter goes in `undocumented_or_insufficient_failures`.
- **Required vs missing packet items**: required includes the standard items a complete packet needs. Missing includes only what's actually absent — don't add items to required just because they're missing.
