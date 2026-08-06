# Northstar Payer Operations Skill

## Overview
Use this skill when solving Northstar Health Plan payer operations tasks — prior authorizations, appeals, payment integrity corrections, peer-to-peer summaries, and margin queue analysis. The environment is a shared read-only payer operations portal with REST endpoints and a SQL interface.

## Environment Setup
The task will provide a base URL and a bearer token. Use these to interact with the environment:
- All REST endpoints require header `Authorization: Bearer <token>`
- The SQL endpoint is `POST /sql/query` with JSON body `{"sql": "<statement>"}` — note the key is `sql`, not `query`
- When neither REST nor SQL is specified, prefer the business REST endpoints first; they return pre-joined, comprehensive results

## Data Access Strategy

### Step 1: Use business REST endpoints first
Start with `GET /api/cases/{target_id}` — this returns a rich, pre-joined payload containing the case record, member details, provider info, plan context, request lines, criteria results (with fact traceability), documents (with facts), authorizations, claims with claim lines, appeals, drug trials, P2P events, and assistance screens all in a single call.

### Step 2: Supplement with focused lookups
- `GET /api/policies/{policy_id}` — returns policy criteria with `approval_required` flags and `result_if_missing` defaults
- `GET /api/rate-schedules` — returns all benchmark rates for repricing; filter by `plan_type`, `service_domain`, `cpt_code`, `modifier`, and effective date range
- `GET /api/appeals` — returns all appeals with deadlines, paths, and packet status
- `POST /sql/query` — use only when data isn't available through REST (e.g., `service_margin` table queries); key name is `sql`, always `SELECT *` with specific WHERE filters

### Step 3: Reconcile records to the task date
Always filter records to those effective as of the task's reporting date. For benchmarks and policies, check `effective_start` and `effective_end` ranges. For documents, prefer `is_current = 1`.

## Business Domain Patterns

### Source Precedence Rules
Every determination uses one of six source-precedence rules. Match the rule to the task type:

| Rule | When to apply |
|---|---|
| `current_clinical_records_over_stale_export` | Current clinical docs (eval, POC) supersede older exports or unrelated episode records. Use for prior auth, UM nurse review. |
| `payer_appeal_before_manufacturer_assistance` | Appeal packet items are evaluated before assistance program items. Use for pharmacy appeals with manufacturer assistance screens. |
| `effective_benchmark_by_plan_modifier_and_date` | Current benchmark schedules (matching plan type, CPT, modifier, and effective date) override stale/legacy schedules. Use for payment integrity repricing. |
| `new_patient_specific_p2p_information` | P2P events may supply new patient-specific info that changes a review; generic provider arguments do not. Use for P2P summaries and MD review closures. |
| `margin_threshold_then_charge_sensitivity` | Below-threshold margin issues (revenue/cost < threshold) take priority, then charge-sensitive rows are flagged separately. Use for finance margin queue analysis. |
| `appeal_deadline_then_clinical_then_payment_integrity` | Multi-priority queue ordering: deadlines first, then clinical urgency, then payment integrity items. Use for mixed queue triage. |

### Basis Audit Construction
Every answer includes a `basis_audit` with four components:

1. **`source_precedence`** — select the applicable rule from the table above
2. **`controlling_record_ids`** — the environment record IDs that directly control the determination (e.g., the authorization record, current clinical documents, effective benchmarks, P2P event, the below-threshold row)
3. **`exception_record_ids`** — records that explain gaps, exclusions, denials, missing information, or route priority (e.g., stale documents, undocumented trial records, criteria that are not met, stale benchmarks, charge-sensitive rows that aren't below threshold)
4. **`precedence_record_order`** — concatenate controlling IDs first (in priority order), then exception IDs. Within exceptions: criteria/route gaps before stale/excluded records

### Criteria Evaluation
- Policy criteria carry an `approval_required` flag — only criteria with `approval_required = 1` gate approval; those with `approval_required = 0` are informative
- Each criterion has a `result_if_missing` that dictates what happens when it fails: `pend` (hold for info), `deny`, or `correct`
- Map each criterion to one of: `met`, `not_met`, `partial`, `unclear`, `not_applicable`
- Track which document facts support each criterion via `evidence_fact_ids`
- **Unresolved criteria**: when a task asks for `unresolved_criteria`, include criteria that are `not_met` and require resolution — not criteria whose status is genuinely unknown
- For multi-criterion policies, the most restrictive unmet criterion determines the final status

### Document Triage
- **Evidence documents** (`evidence_documents`): current clinical/eval/POC documents that directly support the determination — list in ascending document_id order
- **Excluded documents** (`excluded_documents`): stale exports, unrelated episodes, or documents whose `is_current = 0` — list in ascending document_id order
- For claims/repricing: the EOB/remittance document and its facts identify the stale schedule used

### Packet Assessment (Appeals)
- Required packet items listed in appeal notes define the minimum for a complete filing
- Compare required items against documents present in the case
- Separate appeal evidence gaps (listed first in `missing_packet_items`) from assistance information gaps (listed after)
- Documented vs undocumented failures: check `drug_trials` — `documented = 1` means evidence exists; `documented = 0` with notes like "fill missing" means the failure is insufficiently evidenced

## Task-Type Quick Reference

### Prior Authorization (UM Nurse Review)
- Review case, member/plan status, request lines, policy criteria, clinical documents, and authorization status
- Criteria driving the determination come from `case_criteria` (pre-evaluated) and `policy_criteria` (policy defaults)
- Total requested units across all lines vs policy unit limits
- If all required criteria are `met` → `approve` / `nurse_approval`
- If any criterion is `not_met` with `result_if_missing = deny` → `deny` / `medical_director_review`
- Authorization object: take `auth_number`, `approved_units`, date ranges, CPTs (sorted ascending), and modifier from the existing authorization record

### Pharmacy Appeal + Assistance
- Appeal routing: `standard_internal` (30-day deadline from denial) or `expedited_internal` (shorter deadline, requires attestation)
- Documented failures: medications with `documented = 1` in drug trials → alphabetical order
- Undocumented/insufficient failures: medications with `documented = 0` or missing fill records → alphabetical order
- Assistance status: `eligible_ready` (all fields present), `eligible_missing_information` (fields missing), `not_eligible`, `not_applicable`
- Next action: `request_more_information` when both appeal evidence and assistance info have gaps; `file_appeal` when appeal packet is complete but assistance is separate

### Payment Integrity (Claim Repricing)
- Match claim lines to current benchmark rates by: plan_type, service_domain, cpt_code, modifier, and effective date range
- Stale source = the benchmark with an earlier effective_end that was used for the original payment
- `correct_allowed_amount` per line = benchmark `allowed_amount` × line `units`
- `recovery_amount` = `correct_allowed_amount` − `paid_amount` (positive for underpayments)
- Claim-level totals are sums across all lines
- Disposition per line: `correct_upward` (underpaid), `correct_downward` (overpaid), `no_change`, `deny_line`
- `resubmission_route`: `payment_integrity_correction` for standard corrections

### Peer-to-Peer Final Summary
- P2P outcome: `overturn_to_approval` (new clinical info changed the review) or `uphold_intended_adverse_decision` (no new patient-specific info)
- `new_information_changed_review`: `true` only when the P2P supplies patient-specific clinical facts that materially alter the criteria assessment; generic arguments about modality quality do not qualify
- Unresolved criteria are those that remain `not_met` after the P2P
- `recommended_alternative`: `SPECT MPI` when PET is denied for missing PET-over-SPECT factors; `PET MPI` when SPECT was denied and PET factors are met; `none` otherwise
- **Internal appeal deadline**: calculated from the final adverse determination date (the P2P completion date when the P2P upholds denial) using the plan's stated appeal window (e.g., 180 calendar days)

### Margin Queue Analysis
- `total_cost` = `variable_cost` + `fixed_cost_allocated` (as defined in the task's finance memo)
- `revenue_to_cost_ratio` = `net_revenue` / `total_cost`
- `margin` = `net_revenue` − `total_cost`
- `below_threshold` = ratio < task-specified threshold
- Recommended actions: `payer_contract_review` (below threshold), `monitor_charge_sensitive` (above threshold but charge-sensitive), `monitor_no_action` (above threshold, not charge-sensitive)
- `top_issue`: the below-threshold row with format `{segment}_{cpt_code}`; use `none` if no rows are below threshold
- `gap_to_120pct`: `(threshold × total_cost) − net_revenue` for the top issue
- Aggregate segments alphabetically

## Numeric Precision
- Currency: round to 2 decimal places (cents)
- Ratios: round to 4 decimal places
- Integer fields (units, visits): use whole integers
- Dates: ISO 8601 `YYYY-MM-DD` format; use `null` for absent modifiers (not empty string)

## Answer Construction Checklist
1. Read the task prompt and identify the task type, target ID(s), reporting date, and requester role
2. Fetch the primary case/appeal/claim via `GET /api/cases/{id}`
3. Fetch supporting records (policy, rate schedules, appeals list) as needed
4. Map every required field from the answer template to an environment record
5. Classify documents into evidence vs excluded
6. Select the correct `source_precedence` rule for the task type
7. Build `basis_audit`: controlling records first, then exception records, in the correct priority order
8. Compute all numeric values using the precision rules above
9. Sort lists according to their specified ordering rules
10. Return exactly one JSON object matching the answer template — no markdown, no prose outside the JSON
