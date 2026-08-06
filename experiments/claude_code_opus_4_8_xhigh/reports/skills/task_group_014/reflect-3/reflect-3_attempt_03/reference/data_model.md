# Environment data model

The operations environment is a small read-only relational database of payer operations, reached
through a SQL query endpoint and business GET endpoints. Always confirm the live schema at runtime
(retrieve the environment's table/schema listing) before writing queries — column names below are
the typical shape, not a substitute for checking.

Query strategy: start from the target business ID given in `task_context.json` and pull every
row that references it. Most tables carry a `case_id` (or the target's own primary key), so a
handful of `WHERE case_id = '<target>'` / `WHERE <pk> = '<target>'` queries retrieve the full
picture. Join outward to member, plan, provider, policy, and rate-schedule rows as needed.

## Tables and key columns

- **cases** (`case_id` pk) — `member_id`, `provider_id`, `request_type`, `service_domain`,
  `policy_id`, `request_date`, `due_date`, `current_stage`, `current_status`, `urgency`,
  `summary`. The hub row for most tasks; `policy_id` links to the governing policy.
- **members** (`member_id` pk) — `patient_name`, `dob`, `plan_id`, `plan_type`, `product`,
  `employer_group`, `member_status`. `plan_type` (commercial / medicaid / medicare_advantage /
  workers_comp) selects the correct rate benchmark.
- **plans** (`plan_id` pk) — payer, plan_type, state, network, effective window.
- **providers** (`provider_id` pk) — name, specialty, npi, org.
- **policies** (`policy_id` pk) — `policy_name`, `version`, effective window, `precedence`,
  `summary`. The `version`/`summary` describe the medical-necessity rule set.
- **policy_criteria** (`criterion_id` pk) — `policy_id`, `criterion_key`, `criterion_text`,
  `approval_required`, `result_if_missing` (approve/pend/deny/uphold default when unmet).
- **case_criteria** (`case_id`+`criterion_id` pk) — the *adjudicated* per-case result:
  `result` (met/not_met/partial/unclear/not_applicable), `evidence_fact_ids`, `gap_description`,
  `reviewer_scope`. This is the source of truth for `criteria_results` fields.
- **request_lines** (`line_id` pk) — `case_id`, `cpt_code`, `modifier`, `service_name`,
  `requested_units`, `requested_start`/`_end`, `diagnosis_codes`, `billed_charge`.
- **documents** (`document_id` pk) — `case_id`, `document_type`, `document_date`,
  `received_date`, `source_system`, `is_current` (1 = current, 0 = stale/superseded), `title`,
  `summary`. `is_current` splits evidence vs excluded documents.
- **document_facts** (`fact_id` pk) — `document_id`, `case_id`, `fact_key`, `fact_value`,
  `numeric_value`, `unit`, `supports_criteria` (which criterion the fact backs).
- **authorizations** (`auth_id` pk) — `case_id`, `auth_number`, `status`, `approved_units`,
  `approved_start`/`_end`, `approved_cpt` (comma-separated), `approved_modifier`,
  `denial_reason`. The recommended/decided authorization outcome for a case.
- **appeals** (`appeal_id` pk) — `case_id`, `denial_date`, `received_date`,
  `appeal_type_requested`, `appeal_path`, `expedited_attestation`, `appeal_deadline`, `outcome`,
  `owner`, `notes` (the `notes` often enumerate the required packet items).
- **assistance_screen** (`case_id` pk) — `program_name`, `income_percent_fpl`, `insurance_type`,
  `denial_required`, `denial_on_file`, `missing_fields` (comma-separated), `assistance_status`.
- **drug_trials** (`trial_id` pk) — `case_id`, `medication`, `outcome`, `documented` (1/0),
  `start_date`, `end_date`, `notes`. `documented` splits documented vs undocumented/insufficient
  medication failures.
- **claims** (`claim_id` pk) — `member_id`, `case_id`, `payer`, `received_date`, `claim_status`,
  `auth_number`, `billed_total`, `paid_total`.
- **claim_lines** (`claim_line_id` pk) — `claim_id`, `line_number`, `cpt_code`, `modifier`,
  `units`, `billed_amount`, `paid_amount`, `denial_code`, `service_date`. Keep claim-line order.
- **payment_benchmarks** (`benchmark_id` pk) — `payer`, `plan_type`, `service_domain`,
  `cpt_code`, `modifier`, `effective_start`, `effective_end`, `allowed_amount`, `source_name`,
  `source_version`. The rate schedules; select by plan_type + cpt + modifier + service-date
  window. Watch for expired schedules and distractor schedules keyed to unrelated CPTs.
- **p2p_events** (`p2p_id` pk) — `case_id`, `scheduled_at`, `duration_minutes`,
  `provider_argument`, `new_information`, `outcome`, `final_status`, `reviewer`, `notes`.
- **service_margin** (`month_id` pk) — `period`, `payer`, `payer_segment`, `service_domain`,
  `cpt_code`, `visits`, `net_revenue`, `variable_cost`, `fixed_cost_allocated`,
  `charge_sensitive` (1/0). The finance-queue rows.

## Recurring signals

- **Currency flags:** `documents.is_current`, benchmark effective windows vs. service date,
  document/claim status strings, `drug_trials.documented`.
- **Scope filters:** the task memo may restrict you to specific row IDs, a reporting period, or a
  single claim/appeal — honor that scope exactly and ignore unrelated rows.
- **Comma-separated fields:** `approved_cpt`, `missing_fields`, `diagnosis_codes` are lists packed
  into one string — split them when the answer needs a list.
