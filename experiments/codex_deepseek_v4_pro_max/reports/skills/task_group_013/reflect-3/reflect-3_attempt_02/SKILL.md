 # Cedar Ridge Intake Coordination — Skill

 ## Purpose

 Solve healthcare-intake tasks that require reading structured data from a shared coordination portal and producing a single structured JSON answer. The portal exposes patient records, coverage, referrals, transfers, chart data, program candidates, ICD metadata, pharmacy listings, facility capacity, documents, and a read-only SQL endpoint.

 ## Core workflow

 1. Read `input/payloads/answer_template.json` to learn the exact required output shape, allowed enum values, ordering rules, and normalization notes. Treat the template as the authoritative contract.
 2. Use the portal's GET endpoints and the `/query` SQL endpoint to gather every piece of data referenced by the task prompt (rosters, patients, referrals, transfers, documents, coverage, PBM, pharmacy, ICD, facility capacity, program candidates, charts).
 3. Cross-reference fields across tables — for example, validate that a referral's payer and insurance ID match the patient's actual coverage, or that an ICD code's service family aligns with the referral's service line.
 4. Apply deterministic business rules to derive computed fields (eligibility, readiness, risk, registration/enrollment status, blocker codes) from the raw data.
 5. Assemble the JSON answer strictly according to the template: use only allowed enum values, sort lists as specified, treat unordered sets as unordered, and include every required key.

## Data-gathering strategy

- Start by listing all database tables with `SELECT name FROM sqlite_master WHERE type='table'`.
- Query the tables directly when you need filtered or aggregated views — the `/query` endpoint accepts parameterized SQL.
- Use the REST GET endpoints (`/patients/{id}`, `/referrals/{id}`, `/transfers/{id}`, `/chart/{id}`, `/icd/{code}`, `/pharmacies`, `/programs/{code}/candidates`) for rich single-entity responses that include joined child records (documents, coverage, PBM, pharmacy preferences, lifestyle, clinical history, chart artifacts).
- For batch tasks, first fetch the batch rows via SQL or a filtered GET, then pull each referenced entity individually.

## Common business rules

### Insurance / coverage validation

- A patient's coverage is **valid** when `status = 'active'` and the target `service_line` appears in the coverage's `service_lines` column.
- Coverage is **invalid** when it is expired, pending, or the service line is excluded.
- Coverage is **missing** when no coverage record exists.
- Compare the referral's `payer` and `insurance_id` against the patient's actual coverage record. A mismatch between the referral-level payer and the patient-level coverage payer is common and may or may not be a blocker — check the template's allowed issue codes.
- When the same `insurance_id` or `policy_number` appears on referrals for different patients, flag it as a shared-insurance anomaly.

### PBM / prescription validation

- PBM is **valid** when `active = 1`, `status = 'approved'`, and the PBM's `policy_number` matches the coverage `policy_number`.
- A mismatched policy number is a policy mismatch. A pending or rejected PBM is invalid.

### Pharmacy network

- Look up the patient's preferred pharmacy (rank 1) in the `/pharmacies` list. Use its `network_status` to set `in_network`, `out_of_network`, or `unknown` (when no pharmacy preference exists).

### ICD / coding discrepancies

- Retrieve the ICD metadata via `/icd/{code}`.
- **Chapter mismatch**: the `chapter` does not belong to the expected range for the referral's `service_line` (e.g. an I00-I99 cardiology code on a pulmonary referral).
- **Laterality mismatch**: the ICD has a non-null `laterality` but the referral's `diagnosis_description` does not mention it.
- **Narrative mismatch**: the `diagnosis_description` is generic ("specialty consultation") while the ICD describes a specific condition — flag when the template includes this issue type.
- **Service-family mismatch**: the ICD's `service_family` does not match the referral's `service_line`.

### Duplicate handling

- Two referrals are duplicates when they share the same `patient_id` and `insurance_id` (or the same patient with substantially the same clinical content).
- Mark one as the primary (typically the earlier `referral_id` or the one with more complete data) and recommend consolidation.
- Referrals flagged `"possible duplicate"` in notes but with different patients or different ICDs may need human review rather than automatic consolidation.

### Document / packet completeness

- Determine which document types are required from the template's allowed-values list.
- A document is **missing** when no record exists for that `doc_type` and patient/transfer, or when it exists but `finalized = 0` (draft).
- A document is **stale** when its `received_date` is older than the freshness limit (the template may list which doc types have freshness limits). Compute staleness relative to the evaluation date — the `as_of_date` field or the current context date.
- "Transportation" may appear in the allowed document list but is sometimes sourced from the transfer's `transportation` field rather than a separate document record. Treat the field value `null` as missing.

### Capacity / feasibility

- For transfer/facility tasks, sum `open_chairs` across all locations for the requested start date and modality.
- If no capacity row exists for that date, capacity is **unavailable** (0).
- Feasibility combines packet readiness and capacity: a patient whose packet is incomplete cannot start even if chairs are open.

### Eligibility & enrollment (program tasks)

- A candidate is **eligible** when: their chronic conditions include the program's target condition(s), consent is signed (not declined or missing), they have an active chart (`existing_chart = 1`), and the candidate's `target_condition` matches the program.
- **Enroll** when eligible with all required chart artifacts present and no high-touch flags.
- **Hold** when eligible but recent hospitalization, ED visit, low adherence, or CKD require closer monitoring.
- **Reject** when ineligible for any reason.

### Risk stratification

- Lifestyle risk derives from smoking status, alcohol use, exercise frequency, and sleep hours. Combine these into low/medium/high using the patterns observed in the portal's lifestyle table.
- Overall risk may incorporate lifestyle risk plus administrative factors (coverage gaps, missing contacts).

## Output construction rules

- Every list whose template says "ascending" must be sorted by the stated key using standard string or date comparison.
- Lists marked "unordered set" should still be emitted as a JSON array; order does not matter but avoid duplicates.
- Use the exact enum strings from the template — do not invent new ones or change case.
- Count-based summary objects must be internally consistent with the per-entity results.
- Do not include free-form prose, explanations, or extra keys outside the template.
- Always re-verify count totals match the patient/referral/transfer lists.

## Exploration tips

- When the answer depends on cross-entity relationships (e.g. referral → patient → coverage → pharmacy), pull each entity fully with its GET endpoint and inspect all nested arrays.
- Use SQL with `WHERE … IN (…)` to fetch exactly the rows for the batch or roster at hand, then drill into individual records.
- If the template introduces a computed field (e.g. `overall_risk`, `feasibility`), work out the derivation from the raw fields before writing the answer.
- ICD chapter ranges: `J00-J99` = pulmonary, `I00-I99` = cardiology, `M00-M99` = musculoskeletal/orthopedics, `S00-T88` = injury, `R00-R99` = symptoms, `E00-E89` = endocrine.
