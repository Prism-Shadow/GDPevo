# Northstar Payer Operations — Data Model

The shared environment exposes these tables (confirm the live list and columns via the
environment's tables-listing endpoint at solve time). Key columns and relationships:

## Core entities
- **cases** — `case_id` (pk), `member_id`, `provider_id`, `request_type`, `service_domain`,
  `policy_id`, `request_date`, `due_date`, `current_stage`, `current_status`, `urgency`, `summary`.
  The hub record. `service_domain` drives which policy/rate/margin records apply.
- **members** — `member_id` (pk), `patient_name`, `dob`, `plan_id`, `plan_type`, `product`,
  `employer_group`, `member_status`. Join `plan_id` → plans.
- **plans** — `plan_id` (pk), `payer_name`, `plan_type`, `state`, `network`, `effective_start`,
  `effective_end`, `notes`. `plan_type` (commercial / medicaid / workers_comp / medicare_advantage)
  selects rate benchmarks and appeal rules.
- **providers** — `provider_id` (pk), `provider_name`, `specialty`, `npi`, phone/fax, `organization`.

## Clinical evidence & policy
- **request_lines** — `line_id` (pk), `case_id`, `cpt_code`, `modifier`, `service_name`,
  `requested_units`, `requested_start`, `requested_end`, `diagnosis_codes`, `billed_charge`.
  The therapy/imaging services requested.
- **documents** — `document_id` (pk), `case_id`, `document_type`, `document_date`, `received_date`,
  `source_system`, `is_current` (0/1), `title`, `summary`. `is_current = 0` ⇒ stale/excluded.
- **document_facts** — `fact_id` (pk), `document_id`, `case_id`, `fact_key`, `fact_value`,
  `numeric_value`, `unit`, `supports_criteria` (criterion_id). Atomic clinical facts tied to a
  criterion; the evidence behind each `met`/`not_met`.
- **policies** — `policy_id` (pk), `policy_name`, `version`, `effective_start`, `effective_end`,
  `precedence`, `summary`.
- **policy_criteria** — `criterion_id` (pk), `policy_id`, `criterion_key`, `criterion_text`,
  `approval_required` (0/1), `result_if_missing` (pend/deny/uphold/…). Defines the rules.
- **case_criteria** — (`case_id`, `criterion_id`) pk, `result` (met/not_met/partial/unclear/…),
  `evidence_fact_ids`, `gap_description`, `reviewer_scope`. The per-case criterion results.
- **authorizations** — `auth_id` (pk), `case_id`, `auth_number`, `status`, `approved_units`,
  `approved_start`, `approved_end`, `approved_cpt` (comma-string in env → list in answer),
  `approved_modifier`, `denial_reason`. Existing recommendation/decision to echo or override.

## Appeals & pharmacy
- **appeals** — `appeal_id` (pk), `case_id`, `denial_date`, `received_date`, `appeal_type_requested`,
  `appeal_path` (standard_internal / expedited_internal / external_review / not_eligible),
  `expedited_attestation`, `appeal_deadline`, `outcome`, `owner`, `notes` (often lists the required
  packet items).
- **drug_trials** — `trial_id` (pk), `case_id`, `medication`, `outcome`, `documented` (0/1),
  `start_date`, `end_date`, `notes`. `documented` splits prior failures into documented vs
  undocumented/insufficient.
- **assistance_screen** — `case_id` (pk), `program_name`, `income_percent_fpl`, `insurance_type`,
  `denial_required`, `denial_on_file`, `missing_fields` (comma-string), `assistance_status`.
  Manufacturer-assistance eligibility and gaps.

## Peer-to-peer
- **p2p_events** — `p2p_id` (pk), `case_id`, `scheduled_at`, `duration_minutes`, `provider_argument`,
  `new_information`, `outcome` (not_applicable / overturn_to_approval / uphold_intended_adverse_decision),
  `final_status`, `reviewer`, `notes`. The completed P2P discussion and its result.

## Claims & payment
- **claims** — `claim_id` (pk), `member_id`, `case_id`, `payer`, `received_date`, `claim_status`,
  `auth_number`, `billed_total`, `paid_total`.
- **claim_lines** — `claim_line_id` (pk), `claim_id`, `line_number`, `cpt_code`, `modifier` (nullable),
  `units`, `billed_amount`, `paid_amount`, `denial_code`, `service_date`. Reprice each line.
- **payment_benchmarks** — `benchmark_id` (pk), `payer`, `plan_type`, `service_domain`, `cpt_code`,
  `modifier` (nullable), `effective_start`, `effective_end`, `allowed_amount`, `source_name`,
  `source_version`. Pick by payer+plan_type+service_domain+cpt+modifier effective on the service date.
  Watch for stale sources (effective_end < service_date) and distractor schedules (CPT not on claim).

## Finance
- **service_margin** — `month_id` (pk), `period`, `payer`, `payer_segment` (medicaid / commercial /
  workers_comp), `service_domain`, `cpt_code`, `visits`, `net_revenue`, `variable_cost`,
  `fixed_cost_allocated`, `charge_sensitive` (0/1). `total_cost = variable_cost + fixed_cost_allocated`.

## Useful joins
- Case → member/plan/provider: `cases JOIN members ON member_id JOIN plans ON plan_id JOIN providers ON provider_id`.
- Case → policy & criteria: `cases JOIN policies ON policy_id JOIN policy_criteria ON policy_id`; per-case
  results via `case_criteria ON case_id`.
- Case → evidence: `documents ON case_id` → `document_facts ON document_id`; `supports_criteria` links a
  fact to a `policy_criteria.criterion_id`.
- Case → request lines / authorization / appeal / p2p: each keyed by `case_id`.
- Claim → lines: `claim_lines ON claim_id` (order by `line_number`); claim → case via `case_id`.
- Margin: filter `service_margin` by the `month_id` list in `task_context` (keep that order in the answer).
