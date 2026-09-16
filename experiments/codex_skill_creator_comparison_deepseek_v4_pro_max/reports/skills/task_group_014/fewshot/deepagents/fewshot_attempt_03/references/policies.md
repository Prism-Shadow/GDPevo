# Policy Framework

Five active policies are registered in the Northstar environment. Each policy is linked to cases via `cases.policy_id` and defines criteria via `policy_criteria`.

## Policy Index

| Policy ID | Name | Version | Precedence | Domains |
|---|---|---|---|---|
| POL-PT-LUMBAR-2026 | Lumbar Physical Therapy Medical Necessity | 2026.2 | 10 | physical_therapy |
| POL-ST-PEDS-2026 | Pediatric Speech Therapy Prior Authorization | 2026.1 | 11 | speech_therapy |
| POL-DRUG-EXC-2026 | Specialty Drug Coverage Exception Appeal | 2026.3 | 20 | pharmacy appeals |
| POL-PET-MPI-2026 | PET Myocardial Perfusion Imaging Medical Necessity | 2026.4 | 30 | cardiac_imaging (PET MPI) |
| POL-CLAIM-RATE-2026 | Outpatient Imaging and Surgery Payment Benchmark | 2026.2 | 40 | cardiac_imaging (payment) |

Lower precedence numbers indicate higher priority when policies overlap.

## Criteria Mappings

### POL-PT-LUMBAR-2026 — Lumbar Physical Therapy

Criteria keys used in answer templates: `PT-ACTIVE`, `PT-DEFICIT`, `PT-DX`, `PT-POC`, `PT-UNITS`.

Query to retrieve the full criteria for a case:

```sql
SELECT pc.criterion_id, pc.criterion_key, pc.criterion_text,
       pc.approval_required, pc.result_if_missing,
       cc.result, cc.evidence_fact_ids, cc.gap_description, cc.reviewer_scope
FROM policy_criteria pc
LEFT JOIN case_criteria cc ON pc.criterion_id = cc.criterion_id AND cc.case_id = '<CASE_ID>'
WHERE pc.policy_id = 'POL-PT-LUMBAR-2026'
ORDER BY pc.criterion_key;
```

Criterion evaluation logic:
- Each criterion in the answer template maps to a `criterion_id` via its criterion_key prefix (PT-ACTIVE, PT-DEFICIT, PT-DX, PT-POC, PT-UNITS).
- The `case_criteria.result` column gives the pre-computed result. Evaluate it alongside supporting `document_facts` whose `supports_criteria` field references the same criterion_id.
- Criteria that are `met` across all required keys → `approve` recommendation.
- Any `not_met` → check if `reviewer_scope = md_required`. If so, route to `medical_director_review`. Otherwise, `deny` if criteria can be resolved at nurse level.

### POL-DRUG-EXC-2026 — Specialty Drug Coverage Exception Appeal

Criteria keys: `DRUG-AUTH`, `DRUG-DENIAL`, `DRUG-RATIONALE`, `DRUG-FAILURES`.

```sql
SELECT pc.criterion_id, pc.criterion_key, pc.criterion_text,
       pc.approval_required, pc.result_if_missing
FROM policy_criteria pc
WHERE pc.policy_id = 'POL-DRUG-EXC-2026'
ORDER BY pc.criterion_key;
```

Evaluation logic:
- `DRUG-AUTH`: Member authorization must be on file (check appeals table and documents).
- `DRUG-DENIAL`: A payer denial notice must exist (check `appeals.denial_date` and documents).
- `DRUG-RATIONALE`: Prescriber rationale must be documented.
- `DRUG-FAILURES`: Formulary failure evidence — check `drug_trials` for documented failures of preferred alternatives. The `documented` column (1 = documented, 0 = not) separates `documented_failures` from `undocumented_or_insufficient_failures`.

### POL-PET-MPI-2026 — PET Myocardial Perfusion Imaging

Criteria keys: `PET-IND`, `PET-FACTOR`.

```sql
SELECT pc.criterion_id, pc.criterion_key, pc.criterion_text,
       pc.approval_required, pc.result_if_missing,
       cc.result, cc.gap_description
FROM policy_criteria pc
LEFT JOIN case_criteria cc ON pc.criterion_id = cc.criterion_id AND cc.case_id = '<CASE_ID>'
WHERE pc.policy_id = 'POL-PET-MPI-2026'
ORDER BY pc.criterion_key;
```

Evaluation logic:
- `PET-IND`: Covered cardiac indication. Must be `met`.
- `PET-FACTOR`: At least one PET-over-SPECT factor (prior equivocal SPECT, BMI limitation, or attenuation artifact) must be supported.
- If `PET-FACTOR` is `not_met`, list the three specific missing factors in `missing_pet_factors` using the enum values: `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`.
- Recommended alternative when PET is denied: `SPECT MPI`.

### POL-CLAIM-RATE-2026 — Payment Benchmark

This policy governs which benchmark source to use for claim repricing. The actual benchmark values live in `payment_benchmarks`.

Query pattern for matching benchmarks:

```sql
SELECT pb.*
FROM payment_benchmarks pb
JOIN claims cl ON cl.claim_id = '<CLAIM_ID>'
JOIN members m ON cl.member_id = m.member_id
JOIN plans p ON m.plan_id = p.plan_id
WHERE pb.payer = cl.payer
  AND pb.plan_type = m.plan_type
  AND pb.cpt_code IN (SELECT cpt_code FROM claim_lines WHERE claim_id = '<CLAIM_ID>')
ORDER BY pb.effective_start DESC;
```

Then for each claim line, select the benchmark that matches by cpt_code and modifier and has the most recent effective_start that covers the claim's service_date. Reject benchmarks from `Legacy Imaging Export` or any source_version not current.

### POL-ST-PEDS-2026 — Pediatric Speech Therapy

Not used in train tasks. Covers pediatric speech therapy prior-authorization criteria.

## Criteria Result Values

| Value | Meaning |
|---|---|
| met | Criterion is satisfied by evidence |
| not_met | Evidence fails to satisfy the criterion |
| unclear | Evidence is insufficient to determine |
| not_applicable | Criterion does not apply to this case |
