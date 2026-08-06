# Operations data model

The payer-operations environment exposes a relational schema you query
read-only. Confirm exact tables/columns by listing the schema before you
query (names below are the model these environments typically use). Every
answer field traces back to one of these tables.

## Anchor tables (pick by task shape)

- **cases** — the work item for prior-auth / appeal / peer-to-peer / claim
  review shapes. Key columns: `case_id` (PK), `member_id`, `provider_id`,
  `request_type`, `service_domain`, `policy_id`, `request_date`, `due_date`,
  `current_stage`, `current_status`, `urgency`, `summary`.
- **claims** — payment/repricing shape. `claim_id` (PK), `member_id`,
  `case_id`, `payer`, `received_date`, `claim_status`, `auth_number`,
  `billed_total`, `paid_total`.
- **appeals** — appeal shape. `appeal_id` (PK), `case_id`, `denial_date`,
  `received_date`, `appeal_type_requested`, `appeal_path`,
  `expedited_attestation`, `appeal_deadline`, `outcome`, `owner`, `notes`.
- **p2p_events** — peer-to-peer shape. `p2p_id` (PK), `case_id`,
  `scheduled_at`, `duration_minutes`, `provider_argument`, `new_information`,
  `outcome`, `final_status`, `reviewer`, `notes`.
- **service_margin** — finance/margin-queue shape. `month_id` (PK), `period`,
  `payer`, `payer_segment`, `service_domain`, `cpt_code`, `visits`,
  `net_revenue`, `variable_cost`, `fixed_cost_allocated`, `charge_sensitive`.

## Context / policy tables

- **members** — `member_id` (PK), `patient_name`, `dob`, `plan_id`,
  `plan_type`, `product`, `employer_group`, `member_status`.
- **plans** — `plan_id` (PK), `payer_name`, `plan_type`, `state`, `network`,
  `effective_start`, `effective_end`, `notes`.
- **providers** — `provider_id` (PK), `provider_name`, `specialty`, `npi`,
  `phone`, `fax`, `organization`.
- **policies** — `policy_id` (PK), `policy_name`, `version`,
  `effective_start`, `effective_end`, `precedence`, `summary`.
- **policy_criteria** — the criteria a policy defines. `criterion_id` (PK),
  `policy_id`, `criterion_key`, `criterion_text`, `approval_required`,
  `result_if_missing`. The set of `criterion_id`s for the case's policy is the
  key set for `criteria_results` (filter to the ids the template requires).

## Case-specific evidence tables (join on `case_id`)

- **case_criteria** — the per-case result for each criterion. `case_id`,
  `criterion_id`, `result`, `evidence_fact_ids`, `gap_description`,
  `reviewer_scope`. `result` feeds `criteria_results`; `gap_description`
  names the specific missing item behind a `not_met`/`partial`.
- **request_lines** — requested service lines. `line_id` (PK), `case_id`,
  `cpt_code`, `modifier`, `service_name`, `requested_units`,
  `requested_start`, `requested_end`, `diagnosis_codes`, `billed_charge`.
- **documents** — evidence documents. `document_id` (PK), `case_id`,
  `document_type`, `document_date`, `received_date`, `source_system`,
  `is_current`, `title`, `summary`. `is_current` splits evidence (current)
  from excluded/stale (not current).
- **document_facts** — extracted facts. `fact_id` (PK), `document_id`,
  `case_id`, `fact_key`, `fact_value`, `numeric_value`, `unit`,
  `supports_criteria` (which criterion the fact supports).
- **authorizations** — the auth record. `auth_id` (PK), `case_id`,
  `auth_number`, `status`, `approved_units`, `approved_start`,
  `approved_end`, `approved_cpt` (may be a comma-joined string → split and
  sort), `approved_modifier`, `denial_reason`.
- **drug_trials** — prior medication trials for drug appeals. `trial_id`
  (PK), `case_id`, `medication`, `outcome`, `documented` (1/0), `start_date`,
  `end_date`, `notes`. `documented=1` → a documented failure;
  `documented=0` → undocumented/insufficient.
- **assistance_screen** — manufacturer-assistance intake. `case_id` (PK),
  `program_name`, `income_percent_fpl`, `insurance_type`, `denial_required`,
  `denial_on_file`, `missing_fields`, `assistance_status`.
- **claim_lines** — claim detail lines. `claim_line_id` (PK), `claim_id`,
  `line_number`, `cpt_code`, `modifier`, `units`, `billed_amount`,
  `paid_amount`, `denial_code`, `service_date`. Emit lines in `line_number`
  order; `line_id` in output = `claim_line_id`.
- **payment_benchmarks** — rate schedules for repricing. `benchmark_id` (PK),
  `payer`, `plan_type`, `service_domain`, `cpt_code`, `modifier`,
  `effective_start`, `effective_end`, `allowed_amount`, `source_name`,
  `source_version`. Choose the row matching payer + plan_type +
  service_domain + cpt + modifier whose effective window contains the service
  date; treat an expired/superseded schedule as the stale source to reject.

## Join graph (typical)

```
cases.member_id      -> members.member_id -> members.plan_id -> plans.plan_id
cases.provider_id    -> providers.provider_id
cases.policy_id      -> policies.policy_id -> policy_criteria.policy_id
case_id              -> case_criteria, request_lines, documents, authorizations,
                        appeals, drug_trials, assistance_screen, p2p_events
documents.document_id-> document_facts.document_id
claims.claim_id      -> claim_lines.claim_id
claims.member_id     -> members ; claims.case_id -> cases
repricing            -> payment_benchmarks (match on payer/plan_type/
                        service_domain/cpt/modifier/date)
```

The member's `plan_type` (commercial / medicaid / workers_comp /
medicare_advantage) is what you match benchmarks and plan rules against — read
it from the member/plan, not from a distractor row.
