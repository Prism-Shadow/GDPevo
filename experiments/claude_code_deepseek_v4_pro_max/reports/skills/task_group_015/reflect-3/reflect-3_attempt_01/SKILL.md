# EHR Quality-Governance Skill

## Purpose

Solve structured EHR quality-governance tasks — duplicate-chart merge readiness, referral coordination, care-transition packets, service-request quality review, and referral-batch audits — by reading from a read-only EHR API and producing normalized JSON outputs that conform to an answer template.

## Preconditions

- A base URL (`TASK_ENV_BASE_URL`) for the EHR API is provided in the task.
- Every task includes an answer template (`input/payloads/answer_template.json`) that defines the exact JSON shape, required keys, enum values, and ordering rules.
- Some tasks include supporting payload files (e.g. `merge_packet_request.json`) that name the case objects to work with.

## Entry Protocol

### Step 1 — Read all inputs

Read the `prompt.txt` and every file under `input/payloads/` before making any API call. Identify:

- **Case objects**: patient IDs, duplicate-candidate IDs, referral IDs, batch IDs, service-request IDs, provider IDs — every identifier named in the prompt or payloads.
- **Answer template shape**: top-level required keys, nested object schemas, enum constraints, array ordering rules (alphabetical, newest-to-oldest, by referral ID), set-vs-list semantics.
- **Expected values**: where the template says `"enum: a | b | c"`, you may only emit one of those exact strings; where it says `"string; required value train_NNN"`, you must emit that literal.

### Step 2 — Gather all source data from the API

For every case object, fetch every relevant endpoint. The standard endpoint families are:

| Family | Endpoint pattern | Returns |
|---|---|---|
| Patient detail | `GET /api/patients/{id}` | Demographics, PCP, insurance, MRN |
| Active conditions | `GET /api/patients/{id}/conditions` | Condition list with `normalized_key`, `code`, `status` |
| Active medications | `GET /api/patients/{id}/medications` | Medication list with `normalized_key`, `status` |
| Active allergies | `GET /api/patients/{id}/allergies` | Allergy list with `normalized_key`, `status` |
| Encounters | `GET /api/patients/{id}/encounters` | Encounter history with diagnoses, care plans |
| Immunizations | `GET /api/patients/{id}/immunizations` | Immunization records |
| Documents | `GET /api/patients/{id}/documents` | Document metadata (type, status, source) |
| Disclosures | `GET /api/patients/{id}/disclosures` | Disclosure records |
| Service requests | `GET /api/patients/{id}/service-requests` | ServiceRequest resources |
| Duplicate candidates | `GET /api/duplicates/{id}` | Match/conflict signals, merge preview |
| Referral detail | `GET /api/referrals/{id}` | Single referral record |
| Referral list | `GET /api/referrals` | All referrals (filter by batch_id in code) |
| ICD-10 lookup | `GET /api/icd10/{code}` | Chapter, expected_terms, requires_laterality |
| Provider detail | `GET /api/providers/{id}` | Provider name, role, facility, contact |
| Service codes | `GET /api/service-codes/{code}` | Code validity, service_line, order_kind |
| Audit logs | `GET /api/audit-logs` | All audit entries (filter by patient/relevance) |

Fetch all relevant endpoints in parallel where possible. Do not skip endpoints — a missing document or disclosure can change readiness answers.

### Step 3 — Normalize and filter

**Active-only filtering.** For clinical lists (conditions, medications, allergies), only include records where `"status": "active"`. Exclude `inactive`, `entered-in-error`, `resolved`, and any other non-active status. Capture inactive items only when the answer template explicitly asks for excluded/distractor keys.

**Use normalized_key values.** When the answer template asks for keys (condition_keys, medication_keys, allergy_keys), use the `normalized_key` field from the API response, not the `code`, `id`, or human-readable `description`.

**Set unions.** When combining clinical lists from two patients (merge tasks), take the union of distinct `normalized_key` values from both patients' active records. Sort the union alphabetically unless the template states otherwise.

**Sorting defaults.** Unless the template specifies a different ordering:
- Arrays of string keys/IDs/codes: sort alphabetically/lexicographically ascending.
- Arrays of encounter objects: sort by date descending (newest first).
- Arrays of referral objects: sort by `referral_id` ascending.
- Arrays flagged as "set semantics" may be emitted in any order (the evaluator normalizes), but alphabetical sorting is safe.

### Step 4 — Validate codes and signals

**ICD-10 validation.** For any diagnosis code, fetch its ICD-10 entry. Check:
- `chapter`: is it appropriate for the service line? For orthopedics, the expected chapter is typically "Musculoskeletal." Codes from "Respiratory," "Neoplasms," or "Circulatory" may signal an out-of-range issue.
- `requires_laterality`: if `true`, the diagnosis narrative or patient evidence must include a laterality term (left/right/bilateral). Missing laterality in the narrative is a flag.
- `expected_terms`: the narrative should contain or be consistent with at least one expected term. A narrative that describes a completely different body part or condition is a narrative mismatch.
- Code validity: an unknown/404 code is an `unknown_code` issue.

**Match/conflict signals.** Read `match_signals` and `conflict_signals` directly from the duplicate-candidate endpoint. Supplement with demographic comparison:
- Same value → demographic match (label the field: `dob`, `phone`, `insurance_id`, `family_name`, `sex`).
- Different value → demographic conflict (label the field: `given_name`, `address`, `phone`).

### Step 5 — Determine readiness and disposition

**Merge readiness.** Weigh match signals against conflict signals:
- Strong match signals (same DOB, same phone, same insurance, shared external clinical documents) with zero or minor conflicts (address abbreviation, nickname variant) → ready to merge.
- Significant conflicts (different names, different phones, opposite laterality problems) with few matches → do not merge or needs review.
- A `preferred_target_patient_id` in the merge preview is authoritative for target/source assignment.
- The `status` field on the duplicate candidate (open, needs_review, confirmed_duplicate) informs the candidate_status and decision.

**Referral readiness.** A referral is ready to send when:
- Authorization is approved (not missing or pending).
- Required documents (echo, office note for cardiology) are received with `status: final`.
- Diagnosis code matches its narrative and belongs to the appropriate chapter.
- Allergy documentation is complete (an active allergy with a note to confirm is still documented — follow_up_needed for a clarification is not a letter blocker unless the template says it is).
- Blocking issues only include genuinely missing prerequisites: missing authorization, missing required documents, invalid diagnosis code, clinical mismatch. A coordination note about confirming details is not necessarily a blocker.

**Risk flags for care transitions.** Derive from active clinical data and encounter care plans:
- Condition evidence: e.g. `memory_loss` condition → cognitive risk; `hypertension` condition → hypertension risk; `diabetes_type_2` with insulin medication → insulin-dependent diabetes risk.
- Medication evidence: insulin → perioperative glucose concern; any medication with allergy cross-reactivity.
- Allergy evidence: latex allergy → surgical risk.
- Encounter care-plan evidence: a care-transition encounter noting "glucose plan" or "fall-risk note" needed → corresponding risk flags.
- Include all supported risk flags; report empty evidence arrays when a flag is present but no encounter/condition/medication directly ties to it.

### Step 6 — Construct the answer

1. Start from the answer template shape — do not add, remove, or rename keys.
2. Fill every required field. For nullable fields (`string | null`), use `null` (JSON null) when the source data has no value.
3. Use only the exact enum strings defined in the template.
4. Ensure internal consistency: summary counts must match array lengths; every referral in a batch must be accounted for across all buckets (or counted as clean); selected and excluded encounter lists must partition the reviewed set.
5. Boolean fields use JSON `true`/`false` (not strings).
6. Dates use `YYYY-MM-DD` format.
7. Return the JSON object directly — no explanatory prose, no markdown fences.

### Step 7 — Pre-submission consistency checks

Before finalizing, verify:
- [ ] Every `task_id` field matches the task identifier from the prompt.
- [ ] Arrays labeled "sorted alphabetically" are actually sorted.
- [ ] Arrays labeled "sorted by referral_id" or "newest to oldest" follow their ordering rules.
- [ ] All enum values match the template's allowed sets exactly (including case and underscores).
- [ ] Summary count integers equal the lengths of their corresponding arrays.
- [ ] No duplicate entries in set-semantics arrays.
- [ ] Both `clinical_unions` and `active_key_unions` (when both present) contain the same key sets — they are redundant representations of the same data.
- [ ] `excluded_distractors` only contain items that are genuinely inactive, stale, or unrelated (different patient, different case).

## Common Patterns

### Merge Packet Pattern

When a task asks for a duplicate-chart merge readiness packet:
1. Fetch the duplicate candidate to get match/conflict signals and merge preview.
2. Fetch both patients' full clinical lists, documents, and demographics.
3. Compute the active-key union from individual patient endpoints.
4. Compare the union against the merge preview to identify keys the preview missed (reconciliation).
5. Filter audit logs to only those referencing the relevant patient IDs and merge-related events.
6. Select documents that are identity-verification or external-continuity documents; exclude chart summaries and unrelated clinical notes.
7. The specialist contact is the provider associated with the external clinical document that links the two patients.

### Referral Coordination Pattern

When a task asks for a referral coordination packet:
1. Fetch the referral detail and the patient's clinical lists.
2. Validate the referral's diagnosis code via ICD-10 lookup.
3. The most recent encounter whose care plan mentions the referral reason is the primary encounter evidence.
4. Document readiness: check both that the referral lists the document type as received AND that a corresponding document record exists for the patient with `status: final`.
5. Cardio-relevant medications are those with highlight reasons of heart_failure_diuretic or blood_pressure_management.
6. The referral letter fields should be chosen from the template's enums based on the evidence, not invented.

### Care Transition Pattern

When a task asks for a care-transition packet:
1. The patient and recipient come from the prompt directly.
2. Handoff encounters should be the most recent encounters whose diagnoses relate to the target specialty. A care_transition encounter mentioning the surgery is the anchor; supplement with recent office visits sharing the relevant diagnosis codes.
3. Exclude encounters that are older, have no specialty-relevant diagnoses, or are clearly unrelated.
4. The latest immunization is the one with the most recent date.
5. The disclosure where recipient_provider_id matches the target provider and status is "permitted" is the applicable disclosure.
6. Risk flags span conditions, medications, and care-plan notes. Each flag needs at least one piece of evidence from the clinical data.

### Service Request Quality Pattern

When a task asks for service-request quality review:
1. Validate the service code via the service-codes endpoint (active + correct service_line).
2. Validate each reason code via ICD-10: check validity, chapter, and whether the code matches the patient's active conditions.
3. SBAR completeness: check that all four sections (situation, background, assessment, recommendation) are present and non-empty.
4. For duplicate review alongside a service request: the duplicate candidate's status and signals are independent of the service request; report each on its own evidence.

### Batch Audit Pattern

When a task asks for a referral-batch audit:
1. Fetch all referrals and filter to the target batch_id.
2. For each referral, validate the diagnosis code against ICD-10 (chapter appropriateness, narrative match, laterality).
3. Group duplicate referrals by patient_id where coordination notes or repeated patient IDs indicate resubmission.
4. Check for insurance anomalies by grouping patients who share an insurance_id but are confirmed different individuals.
5. Populate follow-up queues by checking authorization_status, documents_received, and coordination notes.
6. Assign action-plan tiers:
   - **Tier 1**: urgent referrals with coding issues or duplicate blockers.
   - **Tier 2**: routine referrals with coding, authorization, or document issues.
   - **Tier 3**: referrals needing only administrative document completion (missing office notes, pending imaging).
7. Every referral in the batch must be accounted for: either assigned to a tier, listed as a clean/validated referral (counted in validated_ready_no_follow_up_count), or listed in a follow-up queue. The sum of all tier counts plus the validated-ready count should equal the total referral rows (minus overlaps where one referral appears in multiple buckets, if the template counts those independently).
8. Duplicate-blocker referral IDs in the tiering policy should include both the original and the duplicate submissions in the duplicate group.

## Guardrails

- Never invent enum values. If the evidence doesn't perfectly match any template enum, choose the closest one — do not create new strings.
- Never include a field that isn't in the answer template, and never omit a required field.
- Empty arrays use `[]`, not `null`, unless the template explicitly types the field as nullable.
- When two sections of the answer template represent the same underlying data (e.g. `clinical_unions` and `active_key_unions`), they must be identical.
- The `authoritative_source` enum in list reconciliation is a fixed value from the template, not a free-text description of your method.
- Exclusion lists must only contain items you actually reviewed and rejected. Do not fabricate distractors.
- For nullable fields, prefer `null` over an empty string when the source data provides no value.
