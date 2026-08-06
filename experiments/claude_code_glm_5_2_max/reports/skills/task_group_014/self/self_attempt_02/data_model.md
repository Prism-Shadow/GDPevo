# Northstar Environment — Data Model

The shared read-only environment exposes 19 tables through `GET /api/tables` (schema) and
`POST /sql/query` (data). This file is a reference for the tables, their key columns, and how
they join. **Always confirm the live schema with `GET /api/tables` before relying on this** —
if columns differ, trust the live schema.

All IDs are `TEXT`. Booleans may be stored as `INTEGER` (0/1) — coerce to bool in JSON.
Currency is `REAL` in USD. Dates are `TEXT` in `YYYY-MM-DD` (or `YYYY-MM` for `period`;
`scheduled_at` may be ISO 8601 with a time).

## Core case / member / plan / provider

- **cases** — `case_id` (pk), `member_id`, `provider_id`, `request_type`,
  `service_domain`, `policy_id`, `request_date`, `due_date`, `current_stage`,
  `current_status`, `urgency`, `summary`. The hub record. `case_id` is the target for most
  archetypes; `policy_id` links the policy; `service_domain` and `request_type` identify the
  archetype.
- **members** — `member_id` (pk), `patient_name`, `dob`, `plan_id`, `plan_type`, `product`,
  `employer_group`, `member_status`. `plan_type` (commercial / medicaid / medicare_advantage /
  workers_comp) is essential for benchmark selection.
- **plans** — `plan_id` (pk), `payer_name`, `plan_type`, `state`, `network`,
  `effective_start`, `effective_end`, `notes`.
- **providers** — `provider_id` (pk), `provider_name`, `specialty`, `npi`, `phone`, `fax`,
  `organization`.

## Policy + criteria

- **policies** — `policy_id` (pk), `policy_name`, `version`, `effective_start`,
  `effective_end`, `precedence` (int, lower = higher priority), `summary`.
- **policy_criteria** — `criterion_id` (pk), `policy_id`, `criterion_key`, `criterion_text`,
  `approval_required` (0/1), `result_if_missing` (pend / deny / uphold / …). Defines what
  each criterion means and what happens if it is unmet.
- **case_criteria** — pk (`case_id`, `criterion_id`), `result` (met / not_met / unclear /
  not_applicable / partial), `evidence_fact_ids`, `gap_description`, `reviewer_scope`
  (nurse / appeals / medical_director / …). **The pre-computed criterion results for a case.**
  This is usually the authoritative input to criteria_results; reconcile against
  `document_facts` when a gap is described.

## Clinical evidence

- **documents** — `document_id` (pk), `case_id`, `document_type`, `document_date`,
  `received_date`, `source_system`, `is_current` (0/1), `title`, `summary`. `is_current=0`
  with `document_type` like `stale_export` marks a record to exclude.
- **document_facts** — `fact_id` (pk), `document_id`, `case_id`, `fact_key`, `fact_value`,
  `numeric_value`, `unit`, `supports_criteria` (criterion_id or null). The atomic evidence
  facts; `supports_criteria` ties a fact to a criterion. A document with no facts (or only
  facts where `supports_criteria` is null) is not relied-upon evidence.

## Authorizations, appeals, P2P, assistance, drugs

- **authorizations** — `auth_id` (pk), `case_id`, `auth_number`, `status`,
  `approved_units`, `approved_start`, `approved_end`, `approved_cpt` (comma-separated CPT
  string), `approved_modifier`, `denial_reason`. `status` may be `recommended_approval`,
  `approved`, `denied`, etc. For denials, `auth_number` may be null and `approved_units` 0.
- **appeals** — `appeal_id` (pk), `case_id`, `denial_date`, `received_date`,
  `appeal_type_requested`, `appeal_path` (standard_internal / expedited_internal /
  external_review / not_eligible), `expedited_attestation`, `appeal_deadline`, `outcome`,
  `owner`, `notes`. `notes` often lists the required packet items.
- **assistance_screen** — `case_id` (pk), `program_name`, `income_percent_fpl`,
  `insurance_type`, `denial_required` (0/1), `denial_on_file` (0/1), `missing_fields`
  (comma-separated field ids), `assistance_status`.
- **drug_trials** — `trial_id` (pk), `case_id`, `medication`, `outcome`, `documented` (0/1),
  `start_date`, `end_date`, `notes`. `documented=1` → documented failure; `documented=0` →
  undocumented/insufficient failure (the notes explain the gap, e.g. missing fill record).
- **p2p_events** — `p2p_id` (pk), `case_id`, `scheduled_at`, `duration_minutes`,
  `provider_argument`, `new_information`, `outcome` (not_applicable /
  overturn_to_approval / uphold_intended_adverse_decision), `final_status`, `reviewer`,
  `notes`. `new_information` states whether new patient-specific info was supplied.

## Claims + payment benchmarks

- **claims** — `claim_id` (pk), `member_id`, `case_id`, `payer`, `received_date`,
  `claim_status` (e.g. `paid_stale_schedule`, `paid`), `auth_number`, `billed_total`,
  `paid_total`. `claim_status` hints at the stale-schedule problem.
- **claim_lines** — `claim_line_id` (pk), `claim_id`, `line_number`, `cpt_code`, `modifier`
  (or null), `units`, `billed_amount`, `paid_amount`, `denial_code`, `service_date`.
  Reprice each line individually; preserve `line_number` order.
- **payment_benchmarks** — `benchmark_id` (pk), `payer`, `plan_type`, `service_domain`,
  `cpt_code`, `modifier` (or null), `effective_start`, `effective_end`, `allowed_amount`,
  `source_name`, `source_version`. **Natural key for matching a claim line** =
  (payer, plan_type, cpt_code, modifier, effective window containing the service date).
  Multiple rows can share a natural key (duplicates) or carry CPTs/modifiers that match no
  claim line (distractors, e.g. a "Distractor Schedule") — dedup and ignore as needed.

## Margin queue

- **service_margin** — `month_id` (pk), `period` (`YYYY-MM`), `payer`, `payer_segment`
  (medicaid / commercial / workers_comp / medicare_advantage), `service_domain`
  (physical_therapy / speech_therapy / occupational_therapy), `cpt_code`, `visits`,
  `net_revenue`, `variable_cost`, `fixed_cost_allocated`, `charge_sensitive` (0/1). One row
  per payer-service-month. For margin tasks, use **only** the `month_id`s listed in
  `task_context.finance_memo.queue_row_ids`.

## Common join patterns

- Case → evidence: `cases.case_id = documents.case_id = document_facts.case_id`.
- Case → criteria: `cases.policy_id = policies.policy_id = policy_criteria.policy_id`;
  results via `case_criteria` on `case_id` + `criterion_id`.
- Case → authorization: `authorizations.case_id = cases.case_id`.
- Claim → lines → member plan_type: `claims.case_id = cases.case_id`;
  `claims.member_id = members.member_id` (for `plan_type`); `claim_lines.claim_id`.
- Claim line → benchmark: match on `payer`, `members.plan_type`, `claim_lines.cpt_code`,
  `claim_lines.modifier`, and `claim_lines.service_date` within
  `[payment_benchmarks.effective_start, payment_benchmarks.effective_end]`.
- Appeal → assistance/drugs: `appeals.case_id = assistance_screen.case_id =
  drug_trials.case_id`.
- P2P: `p2p_events.case_id = cases.case_id`; CPT from `request_lines` for the same case.
