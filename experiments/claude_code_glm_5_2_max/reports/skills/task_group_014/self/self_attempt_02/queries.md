# Reusable SQL Templates

Parameterized `POST /sql/query` templates per archetype. Substitute the placeholder in
`<ANGLE_BRACKETS>` with the value from the task's `task_context.json` (the target business
ID, queue row IDs, etc.). Send as JSON body `{"sql": "<the SELECT>"}` with the
`Authorization: Bearer <token>` header from `environment_access.md`.

These templates fetch **only the target record(s)**. Never broaden the `WHERE` to bring in
distractor rows. Result cap is 500 rows; these queries are well under it.

Conventions:
- `<TARGET_CASE_ID>` — the case/business ID for the task (e.g. from `target_business_id`,
  `target.case_id`, `work_item.case_id`, `business_id`).
- `<TARGET_APPEAL_ID>` — the appeal ID (e.g. `target_appeal_id`).
- `<POLICY_ID>` — `cases.policy_id` for the target case (fetch from the case row first).
- `<CLAIM_ID>` — the claim ID (e.g. `target.claim_id`).
- `<QUEUE_IDS>` — comma-quoted list from `finance_memo.queue_row_ids`.

## 0. Discover schema (once per session)

```
GET /api/tables
```

## 1. UM nurse prior-auth determination

Case + member + plan + provider:
```sql
SELECT c.case_id, c.member_id, c.provider_id, c.policy_id, c.request_type,
       c.service_domain, c.request_date, c.due_date, c.current_stage,
       c.current_status, c.urgency, c.summary,
       m.patient_name, m.dob, m.plan_id, m.plan_type, m.product, m.member_status,
       p.payer_name, p.plan_type AS p_plan_type, p.state, p.network,
       p.effective_start, p.effective_end,
       pr.provider_name, pr.specialty
FROM cases c
LEFT JOIN members m ON c.member_id = m.member_id
LEFT JOIN plans p ON m.plan_id = p.plan_id
LEFT JOIN providers pr ON c.provider_id = pr.provider_id
WHERE c.case_id = '<TARGET_CASE_ID>'
```

Requested therapy lines:
```sql
SELECT line_id, case_id, cpt_code, modifier, service_name, requested_units,
       requested_start, requested_end, diagnosis_codes, billed_charge
FROM request_lines
WHERE case_id = '<TARGET_CASE_ID>'
ORDER BY line_id
```

Policy + criteria + pre-computed results:
```sql
SELECT policy_id, policy_name, version, effective_start, effective_end, precedence, summary
FROM policies WHERE policy_id = '<POLICY_ID>'
```
```sql
SELECT criterion_id, policy_id, criterion_key, criterion_text, approval_required,
       result_if_missing
FROM policy_criteria
WHERE policy_id = '<POLICY_ID>'
ORDER BY criterion_id
```
```sql
SELECT case_id, criterion_id, result, evidence_fact_ids, gap_description, reviewer_scope
FROM case_criteria
WHERE case_id = '<TARGET_CASE_ID>'
ORDER BY criterion_id
```

Evidence documents + facts:
```sql
SELECT document_id, case_id, document_type, document_date, received_date,
       source_system, is_current, title, summary
FROM documents
WHERE case_id = '<TARGET_CASE_ID>'
ORDER BY document_id
```
```sql
SELECT fact_id, document_id, case_id, fact_key, fact_value, numeric_value, unit,
       supports_criteria
FROM document_facts
WHERE case_id = '<TARGET_CASE_ID>'
ORDER BY fact_id
```

Authorization:
```sql
SELECT auth_id, case_id, auth_number, status, approved_units, approved_start,
       approved_end, approved_cpt, approved_modifier, denial_reason
FROM authorizations
WHERE case_id = '<TARGET_CASE_ID>'
```

## 2. Pharmacy coverage appeal + assistance

Appeal + assistance + drug trials:
```sql
SELECT appeal_id, case_id, denial_date, received_date, appeal_type_requested,
       appeal_path, expedited_attestation, appeal_deadline, outcome, owner, notes
FROM appeals
WHERE case_id = '<TARGET_CASE_ID>' OR appeal_id = '<TARGET_APPEAL_ID>'
```
```sql
SELECT case_id, program_name, income_percent_fpl, insurance_type, denial_required,
       denial_on_file, missing_fields, assistance_status
FROM assistance_screen
WHERE case_id = '<TARGET_CASE_ID>'
```
```sql
SELECT trial_id, case_id, medication, outcome, documented, start_date, end_date, notes
FROM drug_trials
WHERE case_id = '<TARGET_CASE_ID>'
ORDER BY trial_id
```
Plus the policy/criteria and case_criteria queries from Archetype 1 (same pattern, with the
appeal case's `policy_id`).

## 3. Claim repricing / payment integrity

Claim + lines + member plan type + auth number:
```sql
SELECT cl.claim_id, cl.member_id, cl.case_id, cl.payer, cl.received_date,
       cl.claim_status, cl.auth_number, cl.billed_total, cl.paid_total,
       m.plan_type
FROM claims cl
LEFT JOIN members m ON cl.member_id = m.member_id
WHERE cl.claim_id = '<CLAIM_ID>'
```
```sql
SELECT claim_line_id, claim_id, line_number, cpt_code, modifier, units,
       billed_amount, paid_amount, denial_code, service_date
FROM claim_lines
WHERE claim_id = '<CLAIM_ID>'
ORDER BY line_number
```

Benchmark candidates for the claim's service domain / payer / plan type (then filter in code
by CPT, modifier, and the service_date within the effective window; dedup identical rows):
```sql
SELECT benchmark_id, payer, plan_type, service_domain, cpt_code, modifier,
       effective_start, effective_end, allowed_amount, source_name, source_version
FROM payment_benchmarks
WHERE service_domain = '<SERVICE_DOMAIN>'
  AND payer = '<PAYER>'
  AND plan_type = '<PLAN_TYPE>'
ORDER BY source_name, cpt_code, modifier, effective_start
```

## 4. Peer-to-peer final summary

P2P event + requested line + criteria + auth:
```sql
SELECT p2p_id, case_id, scheduled_at, duration_minutes, provider_argument,
       new_information, outcome, final_status, reviewer, notes
FROM p2p_events
WHERE case_id = '<TARGET_CASE_ID>'
```
```sql
SELECT line_id, case_id, cpt_code, modifier, service_name, requested_units,
       requested_start, requested_end, diagnosis_codes, billed_charge
FROM request_lines
WHERE case_id = '<TARGET_CASE_ID>'
ORDER BY line_id
```
Plus the policy/criteria, case_criteria, documents, document_facts, and authorizations
queries from Archetype 1 (same case ID).

## 5. Therapy margin queue

Only the listed queue rows (ignore `SM-D-*` distractors):
```sql
SELECT month_id, period, payer, payer_segment, service_domain, cpt_code, visits,
       net_revenue, variable_cost, fixed_cost_allocated, charge_sensitive
FROM service_margin
WHERE month_id IN (<QUEUE_IDS>)
ORDER BY month_id
```
Then order the output rows by `task_context.finance_memo.queue_row_ids`, **not** by the SQL
`ORDER BY`, which is only for stable retrieval.

## Tips

- If you need the target case's `policy_id` before querying criteria, run the case query
  first and read `policy_id` from the result.
- `modifier` is nullable; in SQLite `WHERE modifier = NULL` matches nothing — use
  `IS NULL` / `IS NOT NULL` when filtering benchmarks by modifier presence.
- `is_current`, `approval_required`, `documented`, `denial_required`, `denial_on_file`, and
  `charge_sensitive` are 0/1 integers; coerce to booleans in JSON.
- For currency, compute in floating point and round to 2 decimals only at the end; for
  ratios, round to 4 decimals.
