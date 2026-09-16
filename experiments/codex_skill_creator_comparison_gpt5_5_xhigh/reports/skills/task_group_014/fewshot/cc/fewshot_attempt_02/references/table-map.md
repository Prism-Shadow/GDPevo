# Northstar Environment Table Map

Use this reference for the payer-operations environment exposed by the task. Query `/api/tables` in the live task if you need to confirm schema changes.

## SQL Endpoint

- Endpoint: `POST /sql/query`
- Header: `Authorization: Bearer <token from task>`
- JSON body: `{"sql": "select ..."}`
- Response shape: `columns`, `rows`, `row_count`, `limited`, `max_rows`

## Core Tables

- `cases`: `case_id`, `member_id`, `provider_id`, `request_type`, `service_domain`, `policy_id`, `request_date`, `due_date`, `current_stage`, `current_status`, `urgency`, `summary`
- `members`: `member_id`, `patient_name`, `dob`, `plan_id`, `plan_type`, `product`, `employer_group`, `member_status`
- `plans`: `plan_id`, `payer_name`, `plan_type`, `state`, `network`, `effective_start`, `effective_end`, `notes`
- `providers`: `provider_id`, `provider_name`, `specialty`, `npi`, `phone`, `fax`, `organization`
- `policies`: `policy_id`, `policy_name`, `version`, `effective_start`, `effective_end`, `precedence`, `summary`
- `policy_criteria`: `criterion_id`, `policy_id`, `criterion_key`, `criterion_text`, `approval_required`, `result_if_missing`

## Authorization And Clinical Review

- `request_lines`: `line_id`, `case_id`, `cpt_code`, `modifier`, `service_name`, `requested_units`, `requested_start`, `requested_end`, `diagnosis_codes`, `billed_charge`
- `case_criteria`: `case_id`, `criterion_id`, `result`, `evidence_fact_ids`, `gap_description`, `reviewer_scope`
- `documents`: `document_id`, `case_id`, `document_type`, `document_date`, `received_date`, `source_system`, `is_current`, `title`, `summary`
- `document_facts`: `fact_id`, `document_id`, `case_id`, `fact_key`, `fact_value`, `numeric_value`, `unit`, `supports_criteria`
- `authorizations`: `auth_id`, `case_id`, `auth_number`, `status`, `approved_units`, `approved_start`, `approved_end`, `approved_cpt`, `approved_modifier`, `denial_reason`
- `p2p_events`: `p2p_id`, `case_id`, `scheduled_at`, `duration_minutes`, `provider_argument`, `new_information`, `outcome`, `final_status`, `reviewer`, `notes`

## Appeal And Pharmacy

- `appeals`: `appeal_id`, `case_id`, `denial_date`, `received_date`, `appeal_type_requested`, `appeal_path`, `expedited_attestation`, `appeal_deadline`, `outcome`, `owner`, `notes`
- `drug_trials`: `trial_id`, `case_id`, `medication`, `outcome`, `documented`, `start_date`, `end_date`, `notes`
- `assistance_screen`: `case_id`, `program_name`, `income_percent_fpl`, `insurance_type`, `denial_required`, `denial_on_file`, `missing_fields`, `assistance_status`

## Payment Integrity

- `claims`: `claim_id`, `member_id`, `case_id`, `payer`, `received_date`, `claim_status`, `auth_number`, `billed_total`, `paid_total`
- `claim_lines`: `claim_line_id`, `claim_id`, `line_number`, `cpt_code`, `modifier`, `units`, `billed_amount`, `paid_amount`, `denial_code`, `service_date`
- `payment_benchmarks`: `benchmark_id`, `payer`, `plan_type`, `service_domain`, `cpt_code`, `modifier`, `effective_start`, `effective_end`, `allowed_amount`, `source_name`, `source_version`

## Finance

- `service_margin`: `month_id`, `period`, `payer`, `payer_segment`, `service_domain`, `cpt_code`, `visits`, `net_revenue`, `variable_cost`, `fixed_cost_allocated`, `charge_sensitive`

## Query Patterns

Start with the smallest target set:

```sql
select * from cases where case_id = '<case_id>';
select * from request_lines where case_id = '<case_id>' order by line_id;
select * from case_criteria where case_id = '<case_id>' order by criterion_id;
select * from documents where case_id = '<case_id>' order by is_current desc, document_date desc, document_id;
select * from document_facts where case_id = '<case_id>' order by document_id, fact_id;
select * from authorizations where case_id = '<case_id>' order by auth_id;
```

Appeal/pharmacy:

```sql
select * from appeals where case_id = '<case_id>' order by received_date desc, appeal_id;
select * from drug_trials where case_id = '<case_id>' order by medication, trial_id;
select * from assistance_screen where case_id = '<case_id>';
```

P2P:

```sql
select * from p2p_events where case_id = '<case_id>' order by scheduled_at desc, p2p_id;
```

Claims and benchmarks:

```sql
select * from claims where claim_id = '<claim_id>';
select * from claim_lines where claim_id = '<claim_id>' order by line_number;
select * from payment_benchmarks
where cpt_code in ('<line cpt codes>')
  and effective_start <= '<service_date>'
  and effective_end >= '<service_date>'
order by cpt_code, modifier, effective_start desc;
```

Finance queue:

```sql
select * from service_margin
where month_id in ('<row id 1>', '<row id 2>')
order by case
  when month_id = '<row id 1>' then 1
  when month_id = '<row id 2>' then 2
  else 999
end;
```

Adapt filters to the exact IDs and dates in the task. Do not carry values from examples into a new task.
