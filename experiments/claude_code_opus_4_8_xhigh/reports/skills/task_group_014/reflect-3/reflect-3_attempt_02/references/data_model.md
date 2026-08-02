# Payer-operations data model (reference)

The environment is a small relational payer-operations dataset exposed for read-only
querying (a SQL-style query interface plus business list/detail endpoints). Always confirm
the live schema from the environment's own table listing; the model below is the stable
shape and the joins you will reuse. Everything keys off a business id (a case / claim /
appeal / queue id) that the task hands you.

## Core entities and how they join

- **cases** (`case_id` PK): `member_id`, `provider_id`, `request_type`, `service_domain`,
  `policy_id`, `request_date`, `due_date`, `current_stage`, `current_status`, `urgency`,
  `summary`. The hub for authorization/appeal/P2P/claim-review work items.
  - `case_id -> members.member_id -> plans.plan_id` for member/plan context.
  - `case_id / policy_id -> policies -> policy_criteria` for the rule set.
- **members** (`member_id` PK): `patient_name`, `dob`, `plan_id`, `plan_type`, `product`,
  `employer_group`, `member_status`.
- **plans** (`plan_id` PK): `payer_name`, `plan_type`, `state`, `network`,
  `effective_start`, `effective_end`, `notes`.
- **providers** (`provider_id` PK): specialty/NPI/organization/contact.

## Policy & criteria

- **policies** (`policy_id` PK): `policy_name`, `version`, `effective_start/end`,
  `precedence`, `summary`.
- **policy_criteria** (`criterion_id` PK, by `policy_id`): `criterion_key`,
  `criterion_text`, `approval_required`, `result_if_missing` (e.g. `pend` / `deny` /
  `uphold`). Defines the criteria a case is evaluated against and the fallback if unproven.
- **case_criteria** (PK `case_id`+`criterion_id`): `result` (`met` / `not_met` /
  `partial` / `unclear` / `not_applicable`), `evidence_fact_ids`, `gap_description`,
  `reviewer_scope`. **This is where per-case criterion results come from — copy them.**

## Evidence

- **documents** (`document_id` PK, by `case_id`): `document_type`, `document_date`,
  `received_date`, `source_system`, **`is_current`** (1 = current/relied-on,
  0 = stale/superseded/excluded), `title`, `summary`.
- **document_facts** (`fact_id` PK): `document_id`, `case_id`, `fact_key`, `fact_value`,
  `numeric_value`, `unit`, `supports_criteria` (the criterion a fact substantiates).

## Decision records

- **authorizations** (`auth_id` PK, by `case_id`): `auth_number`, `status`,
  `approved_units`, `approved_start/end`, `approved_cpt` (comma-joined), `approved_modifier`,
  `denial_reason`. Source for the authorization block and approve/deny status.
- **request_lines** (`line_id` PK, by `case_id`): requested `cpt_code`, `modifier`,
  `service_name`, `requested_units`, `requested_start/end`, `diagnosis_codes`,
  `billed_charge`. The requested service lines.
- **appeals** (`appeal_id` PK, by `case_id`): `denial_date`, `received_date`,
  `appeal_type_requested`, `appeal_path`, `expedited_attestation`, `appeal_deadline`,
  `outcome`, `owner`, `notes` (notes often list the required packet).
- **drug_trials** (`trial_id` PK, by `case_id`): `medication`, `outcome`, **`documented`**
  (1 = documented failure, 0 = referenced/insufficient), `start/end_date`, `notes`.
- **assistance_screen** (PK `case_id`): `program_name`, `income_percent_fpl`,
  `insurance_type`, `denial_required`, `denial_on_file`, `missing_fields`,
  `assistance_status`. Manufacturer-assistance eligibility + gaps.
- **p2p_events** (`p2p_id` PK, by `case_id`): `scheduled_at`, `duration_minutes`,
  `provider_argument`, `new_information`, `outcome`, `final_status`, `reviewer`, `notes`.

## Claims & payment

- **claims** (`claim_id` PK): `member_id`, `case_id`, `payer`, `received_date`,
  `claim_status`, `auth_number`, `billed_total`, `paid_total`.
- **claim_lines** (`claim_line_id` PK, by `claim_id`): `line_number`, `cpt_code`,
  `modifier`, `units`, `billed_amount`, `paid_amount`, `denial_code`, `service_date`.
- **payment_benchmarks** (`benchmark_id` PK): `payer`, `plan_type`, `service_domain`,
  `cpt_code`, `modifier`, `effective_start`, `effective_end`, `allowed_amount`,
  `source_name`, `source_version`. Multiple rows per CPT — choose by effective date and
  the most specific match; older/expired rows are the stale source to reject. Watch for
  same-value duplicate rows and out-of-scope "distractor" schedules.

## Finance

- **service_margin** (`month_id` PK): `period`, `payer`, `payer_segment`,
  `service_domain`, `cpt_code`, `visits`, `net_revenue`, `variable_cost`,
  `fixed_cost_allocated`, **`charge_sensitive`** (0/1). One row per payer-segment/CPT/month;
  the task's memo lists which `month_id`s are in scope.

## Recurring patterns

- Nearly every table carries the `case_id`, so start from the target id and fan out.
- A "current vs stale/excluded" signal appears in several forms: `documents.is_current`,
  benchmark effective windows, `drug_trials.documented`. Use it to split relied-on records
  from excluded ones.
- Ids follow readable conventions (e.g. records tied to a given case share its stem); when
  two candidate rows tie on value, prefer the one scoped to the target case and treat the
  other as a distractor.
