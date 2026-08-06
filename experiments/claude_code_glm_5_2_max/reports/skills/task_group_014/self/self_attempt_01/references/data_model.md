# Northstar Data Model

19 tables. The case is the hub; everything fans out from `case_id` (and, for claims, `claim_id`). Columns marked PK are primary keys; NN = not null.

## Core case workflow

**cases** `case_id` PK | `member_id` NN | `provider_id` NN | `request_type` NN | `service_domain` NN | `policy_id` NN | `request_date` NN | `due_date` NN | `current_stage` NN | `current_status` NN | `urgency` NN | `summary` NN

**members** `member_id` PK | `patient_name` NN | `dob` NN | `plan_id` NN | `plan_type` NN | `product` NN | `employer_group` | `member_status` NN
**providers** `provider_id` PK | `provider_name` NN | `specialty` NN | `npi` NN | `phone` | `fax` | `organization`
**plans** `plan_id` PK | `payer_name` NN | `plan_type` NN | `state` NN | `network` NN | `effective_start` NN | `effective_end` NN | `notes`

## Policy & criteria

**policies** `policy_id` PK | `policy_name` NN | `version` NN | `effective_start` NN | `effective_end` NN | `precedence` NN | `summary` NN
**policy_criteria** `criterion_id` PK | `policy_id` NN | `criterion_key` NN | `criterion_text` NN | `approval_required` NN | `result_if_missing` NN
- `approval_required` = 1 means the criterion must be `met` to approve.
- `result_if_missing` ∈ {`pend`, `deny`} — what to do when the criterion is unclear/missing.

**case_criteria** `case_id` PK NN | `criterion_id` PK NN | `result` NN | `evidence_fact_ids` | `gap_description` | `reviewer_scope`
- The per-case, per-criterion evaluation. `result` ∈ {met, not_met, unclear, not_applicable, partial}. `gap_description` populates exception records when not met/unclear.

## Requested services

**request_lines** `line_id` PK | `case_id` NN | `cpt_code` NN | `modifier` | `service_name` NN | `requested_units` NN | `requested_start` | `requested_end` | `diagnosis_codes` | `billed_charge` NN

## Evidence documents

**documents** `document_id` PK | `case_id` NN | `document_type` NN | `document_date` NN | `received_date` NN | `source_system` NN | `is_current` NN | `title` NN | `summary` NN
- `is_current` (0/1) is the stale-vs-current signal. `is_current=0` (e.g. `document_type='stale_export'`) → excluded, exception record.

**document_facts** `fact_id` PK | `document_id` NN | `case_id` NN | `fact_key` NN | `fact_value` NN | `numeric_value` | `unit` | `supports_criteria`
- Structured facts that satisfy criteria. `supports_criteria` links a fact to a criterion ID.

## Authorizations & appeals

**authorizations** `auth_id` PK | `case_id` NN | `auth_number` | `status` NN | `approved_units` | `approved_start` | `approved_end` | `approved_cpt` | `approved_modifier` | `denial_reason`
- `approved_cpt` may be a comma-separated string of CPT codes. `approved_modifier` is a line modifier (e.g. `GP`).

**appeals** `appeal_id` PK | `case_id` NN | `denial_date` NN | `received_date` NN | `appeal_type_requested` NN | `appeal_path` NN | `expedited_attestation` NN | `appeal_deadline` NN | `outcome` | `owner` | `notes`
- `appeal_path` ∈ {standard_internal, expedited_internal, external_review, not_eligible}. `expedited_attestation` indicates expedited risk.

**assistance_screen** `case_id` PK | `program_name` NN | `income_percent_fpl` | `insurance_type` NN | `denial_required` NN | `denial_on_file` NN | `missing_fields` | `assistance_status` NN
- Manufacturer assistance intake. `denial_required`/`denial_on_file` (0/1) drive whether the appeal packet is complete. `missing_fields` is a delimited list.

**drug_trials** `trial_id` PK | `case_id` NN | `medication` NN | `outcome` NN | `documented` NN | `start_date` | `end_date` | `notes`
- Step-therapy / formulary-failure evidence. `documented` (0/1) splits `documented_failures` from `undocumented_or_insufficient_failures`.

**p2p_events** `p2p_id` PK | `case_id` NN | `scheduled_at` NN | `duration_minutes` NN | `provider_argument` | `new_information` | `outcome` | `final_status` | `reviewer` | `notes`
- `new_information` (patient-specific) is what can overturn an intended adverse decision.

## Claims & payment (SQL only — no business endpoint)

**claims** `claim_id` PK | `member_id` NN | `case_id` | `payer` NN | `received_date` NN | `claim_status` NN | `auth_number` | `billed_total` NN | `paid_total` NN
**claim_lines** `claim_line_id` PK | `claim_id` NN | `line_number` NN | `cpt_code` NN | `modifier` | `units` NN | `billed_amount` NN | `paid_amount` NN | `denial_code` | `service_date` NN
- `modifier` is nullable → emit `null` in the answer when absent. Order lines by `line_number`.

**payment_benchmarks** `benchmark_id` PK | `payer` NN | `plan_type` NN | `service_domain` NN | `cpt_code` NN | `modifier` | `effective_start` NN | `effective_end` NN | `allowed_amount` NN | `source_name` NN | `source_version` NN
- Multiple rows per CPT (stale + current). Match on payer+plan_type+cpt+modifier with service_date inside [effective_start, effective_end]. A source with `effective_end` < service_date is stale → `stale_source_rejected`.

## Margin queue (SQL only)

**service_margin** `month_id` PK | `period` NN | `payer` NN | `payer_segment` NN | `service_domain` NN | `cpt_code` NN | `visits` NN | `net_revenue` NN | `variable_cost` NN | `fixed_cost_allocated` NN | `charge_sensitive` NN
- `total_cost` = `variable_cost` + `fixed_cost_allocated`. `revenue_to_cost_ratio` = `net_revenue` / `total_cost`. `margin` = `net_revenue` − `total_cost`. `charge_sensitive` (0/1) flags rows to monitor separately from below-threshold issues.

## Relationship cheat-sheet

```
member ──< cases >── provider
              │
   ┌──────────┼────────────────────────────┐
 policy ──< policy_criteria          request_lines
   │                                    │
case_criteria ── evidence ── documents ── document_facts
              │
   ┌──────────┼───────────┬──────────────┬─────────────┐
authorizations  appeals   assistance_screen  drug_trials  p2p_events
                                                              │
claims ──< claim_lines ──> payment_benchmarks (match cpt+modifier+date)

service_margin  (standalone queue; keyed by month_id; filter by queue_row_ids)
```
