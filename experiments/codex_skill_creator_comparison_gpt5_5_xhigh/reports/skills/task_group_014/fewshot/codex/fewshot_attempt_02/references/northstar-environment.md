# Northstar Environment Reference

## Access

Use the base URL, SQL endpoint, and bearer token from the active task prompt or `task_context.json`. The SQL endpoint accepts JSON shaped like:

```json
{"sql": "select * from cases where case_id = '<target_id>'"}
```

Prefer targeted SQL over broad listing. `GET /api/tables` is useful to confirm schemas at solve time. Business endpoints include cases, policies, documents, rate schedules, appeals, and the portal.

## Tables

- `cases(case_id, member_id, provider_id, request_type, service_domain, policy_id, request_date, due_date, current_stage, current_status, urgency, summary)`
- `members(member_id, patient_name, dob, plan_id, plan_type, product, employer_group, member_status)`
- `plans(plan_id, payer_name, plan_type, state, network, effective_start, effective_end, notes)`
- `providers(provider_id, provider_name, specialty, npi, phone, fax, organization)`
- `request_lines(line_id, case_id, cpt_code, modifier, service_name, requested_units, requested_start, requested_end, diagnosis_codes, billed_charge)`
- `policies(policy_id, policy_name, version, effective_start, effective_end, precedence, summary)`
- `policy_criteria(criterion_id, policy_id, criterion_key, criterion_text, approval_required, result_if_missing)`
- `case_criteria(case_id, criterion_id, result, evidence_fact_ids, gap_description, reviewer_scope)`
- `documents(document_id, case_id, document_type, document_date, received_date, source_system, is_current, title, summary)`
- `document_facts(fact_id, document_id, case_id, fact_key, fact_value, numeric_value, unit, supports_criteria)`
- `authorizations(auth_id, case_id, auth_number, status, approved_units, approved_start, approved_end, approved_cpt, approved_modifier, denial_reason)`
- `appeals(appeal_id, case_id, denial_date, received_date, appeal_type_requested, appeal_path, expedited_attestation, appeal_deadline, outcome, owner, notes)`
- `drug_trials(trial_id, case_id, medication, outcome, documented, start_date, end_date, notes)`
- `assistance_screen(case_id, program_name, income_percent_fpl, insurance_type, denial_required, denial_on_file, missing_fields, assistance_status)`
- `p2p_events(p2p_id, case_id, scheduled_at, duration_minutes, provider_argument, new_information, outcome, final_status, reviewer, notes)`
- `claims(claim_id, member_id, case_id, payer, received_date, claim_status, auth_number, billed_total, paid_total)`
- `claim_lines(claim_line_id, claim_id, line_number, cpt_code, modifier, units, billed_amount, paid_amount, denial_code, service_date)`
- `payment_benchmarks(benchmark_id, payer, plan_type, service_domain, cpt_code, modifier, effective_start, effective_end, allowed_amount, source_name, source_version)`
- `service_margin(month_id, period, payer, payer_segment, service_domain, cpt_code, visits, net_revenue, variable_cost, fixed_cost_allocated, charge_sensitive)`

## Query Patterns

For a case-centered task, query:

```sql
select * from cases where case_id = '<case_id>';
select * from request_lines where case_id = '<case_id>' order by line_id;
select * from authorizations where case_id = '<case_id>' order by auth_id;
select * from case_criteria where case_id = '<case_id>' order by criterion_id;
select * from documents where case_id = '<case_id>' order by document_id;
select * from document_facts where case_id = '<case_id>' order by document_id, fact_id;
select pc.* from policy_criteria pc join cases c on c.policy_id = pc.policy_id where c.case_id = '<case_id>' order by pc.criterion_id;
```

For a pharmacy appeal, add:

```sql
select * from appeals where case_id = '<case_id>' or appeal_id = '<appeal_id>' order by appeal_id;
select * from drug_trials where case_id = '<case_id>' order by lower(medication), trial_id;
select * from assistance_screen where case_id = '<case_id>';
```

For P2P, add:

```sql
select * from p2p_events where case_id = '<case_id>' order by scheduled_at, p2p_id;
```

For a claim, query by claim ID first, then use returned claim/case/member fields:

```sql
select * from claims where claim_id = '<claim_id>';
select * from claim_lines where claim_id = '<claim_id>' order by line_number;
select m.*, p.* from claims cl join members m on m.member_id = cl.member_id join plans p on p.plan_id = m.plan_id where cl.claim_id = '<claim_id>';
```

Match payment benchmarks for each claim line with the claim payer, member plan type, case service domain, line CPT/modifier, and line service date:

```sql
select * from payment_benchmarks
where payer = '<payer>'
  and plan_type = '<plan_type>'
  and service_domain = '<service_domain>'
  and cpt_code = '<cpt_code>'
  and modifier = '<modifier>'
  and effective_start <= '<service_date>' and effective_end >= '<service_date>'
order by effective_start desc, source_version desc;
```

For a claim line with no modifier, replace the modifier predicate with `and modifier is null`.

For service-margin queue rows:

```sql
select * from service_margin where month_id in ('<row_id_1>', '<row_id_2>') order by period, payer_segment, cpt_code;
```

After querying, reorder rows to match the `queue_row_ids` order in `task_context`.

## Normalization

- Split comma-separated CPT, criteria, missing-field, and evidence ID fields only when the environment stores them as delimited text.
- Sort document IDs ascending when the template requires ascending document order.
- Sort medication names alphabetically and lowercase them when the template says medication names are lowercase.
- Preserve line order from `claim_lines.line_number`, not lexical line ID order.
- Preserve template-specific enum spellings exactly.
- Round money to two decimals and ratios to the precision specified in the template.
