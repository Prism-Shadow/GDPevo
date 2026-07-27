---
name: ehr-quality-governance-packets
description: Build normalized JSON packets and audits from a read-only EHR quality-governance API. Use for duplicate chart merge readiness, referral coordination, care transition handoffs, ServiceRequest quality review, and referral batch audits where Codex must inspect patient, provider, ICD-10, service-code, document, disclosure, encounter, audit-log, and active clinical-list evidence and return schema-conformant JSON only.
---

# EHR Quality Governance Packets

## Core Workflow

1. Read the task prompt and every input payload before calling the API.
2. Treat the answer template as the output contract: preserve top-level keys, field names, types, enum values, date formats, nullability, and ordering rules.
3. Read `environment_access.md` in the task workspace for the base URL and allowed endpoint list. Use only those endpoints. Do not browse the web for task evidence.
4. Fetch detail records instead of relying only on list summaries. If a list endpoint ignores query parameters, retrieve the list and filter client-side.
5. Cross-check every emitted identifier and coded value against API evidence. Return JSON only, with no prose, comments, Markdown, or reasoning.

## Evidence Collection

Use the endpoints named by the task and template:

- Duplicate candidates: get `/api/duplicates/candidates`, then `/api/duplicates/{candidate_id}`.
- Referrals: get `/api/referrals`, then `/api/referrals/{referral_id}` for requested records; filter the list client-side for batch, patient, service line, or status.
- Patients: get `/api/patients/{patient_id}` for demographics and PCP.
- Active lists: get patient `conditions`, `medications`, and `allergies` endpoints for every relevant patient.
- Encounters, documents, immunizations, disclosures: get the patient-specific endpoint when the template asks for evidence, handoff records, required documents, disclosure readiness, or latest immunization.
- ServiceRequests: locate them through `/api/patients/{patient_id}/service-requests`.
- Directories: use `/api/providers`, `/api/providers/{provider_id}`, `/api/icd10`, `/api/icd10/{code}`, `/api/service-codes`, and `/api/service-codes/{code}` to validate provider, diagnosis, and service-code fields.
- Audit logs: use `/api/audit-logs` and filter by relevant patient IDs, events, summaries, and dates.

## Normalization Rules

- Emit API IDs, codes, dates, statuses, names, phone numbers, fax numbers, and normalized keys exactly as returned unless the template explicitly asks for a normalized label.
- Use active clinical records only for active condition, medication, and allergy lists. Exclude inactive, entered-in-error, stale, cancelled, preliminary, or unrelated records unless the template asks for excluded distractors.
- Build set arrays by de-duplicating exact emitted values and sorting ascending unless the template states another order.
- For object arrays, follow the template order. Common orders are code ascending, referral ID ascending, newest-to-oldest encounter date, or risk flag ascending.
- Do not replace an API `normalized_key` with a medication or allergen name. Generic keys can appear in real records; preserve the key when the schema asks for keys and use the name only when the schema asks for medication or allergen details.
- Use `null` only where the template allows it. Use empty arrays for absent set evidence.

## Duplicate Review And Merge Packets

1. Verify the duplicate candidate contains the requested patient IDs.
2. Determine the merge target from the candidate `merge_preview.preferred_target_patient_id`, patient `canonical_status`, and any duplicate patient `canonical_patient_id`.
3. Treat a duplicate as ready to merge only when a canonical target/source is supported and no severe identity or clinical conflict blocks the merge.
4. Treat `needs_review`, missing target/source, different phone, different given name, different DOB, different insurance, different address, or opposite-laterality clinical conflicts as manual-review signals. Do not invent a target/source when the candidate keeps them null.
5. Build active condition, medication, and allergy unions from patient active-list endpoints, not from duplicate preview alone. Report keys added from active endpoints when the template asks for reconciliation.
6. Keep duplicate candidate `match_signals` and `conflict_signals`; derive demographic matches/conflicts from patient detail fields such as DOB, insurance, phone, name variants, address normalization, PCP, and canonical status.
7. For merge packet evidence, include final identity or external-continuity documents that support identity or chart continuity. Exclude generic chart summaries and unrelated documents when the template asks for document evidence. Include audit logs tied to the candidate patients and duplicate/import/identity events; exclude unrelated merge events.

## Referral Coordination Packets

1. Start from referral detail, then reconcile against the patient chart, provider directory, ICD-10 directory, documents, encounters, medications, and allergies.
2. Validate the referral diagnosis code with ICD-10 lookup:
   - `invalid_code` when the code is absent from the ICD directory.
   - `wrong_service_chapter` or out-of-range when the code chapter conflicts with the service line or template's expected chapter.
   - `valid_matches_narrative` when the code is valid and the narrative or chart evidence matches expected terms.
   - `valid_but_narrative_mismatch` when the code is valid but the referral narrative conflicts with expected terms or laterality.
3. Choose supporting diagnosis codes from active conditions and the most relevant encounter diagnoses, especially symptoms or comorbidities named in the referral narrative or care plan.
4. Select the recent encounter that best matches the referral service line, diagnosis, symptoms, and care plan. Prefer signed or amended encounters and do not choose the latest unrelated visit just because it is newest.
5. Determine required document readiness from both referral `documents_received` and patient documents. Use final patient document IDs where actual document IDs are requested; use referral document labels to mark office-note or authorization presence when no document endpoint record exists.
6. Resolve the receiving provider by `receiving_provider_id`; missing or wrong-service providers are blockers.
7. Build allergy readiness from active allergy records:
   - complete when active records contain allergen, reaction, severity, status, and source;
   - no-known-allergies when the active allergy endpoint is empty and the task does not require confirmation;
   - incomplete when required details are missing or the task explicitly requires clarification;
   - conflicting when active records contradict each other.
8. Highlight only service-relevant active medications unless the schema asks for all medications. For cardiology, prioritize diuretics for heart failure, antihypertensives or ACE inhibitors for blood pressure, diabetes medications when clinically relevant, and lipid/CAD medications if the referral asks for them.
9. Classify readiness by the highest-priority blocker: missing provider or invalid code, authorization missing or pending, missing required documents, allergy clarification, clinical mismatch, then ready to send.

## Care Transition Packets

1. Emit patient and recipient fields from patient detail and provider detail.
2. Emit active condition, medication, and allergy key arrays from active-list endpoints, sorted ascending.
3. Select handoff encounters by service-line relevance, diagnosis overlap, care-transition notes, and signed/amended status. Use the requested count from the template. Sort selected encounters newest to oldest and list excluded reviewed encounters separately when requested.
4. Choose the latest immunization by max immunization date.
5. Choose the disclosure matching the target recipient provider, facility, and purpose. A permitted disclosure supports sending; missing, pending, denied, or expired disclosure is a blocker.
6. Derive risk flags only from active chart evidence and selected relevant encounters. Common mappings:
   - memory-loss or cognitive impairment condition: cognitive memory-loss risk;
   - fall-risk or handoff note requiring fall-risk documentation: fall-risk note required;
   - hypertension condition: hypertension;
   - diabetes plus insulin medication: insulin-dependent diabetes and perioperative glucose-plan needs;
   - active latex allergy: latex allergy.
7. Mark ready with risk flags when required packet components are present and disclosure is permitted but risk flags should travel with the packet. Mark not ready for missing patient, recipient, active lists, handoff encounters, immunization, disclosure, or non-permitted disclosure.

## ServiceRequest Quality Review

1. Retrieve ServiceRequests through the patient-specific endpoint and select the requested ID.
2. Validate `service_code` against service-code directory, including active flag and service line.
3. Resolve requester and performer providers. Use the performer provider's directory service line for `performer_service_line`.
4. Validate each reason code with ICD-10 lookup and patient evidence. A code matches patient evidence when it appears in active conditions or relevant encounters or is supported by the ServiceRequest narrative/SBAR.
5. Sort reason-code validation objects by code when requested.
6. For SBAR coverage, mark each of situation, background, assessment, and recommendation present only when the corresponding section exists and is non-empty.

## Referral Batch Audits

1. Fetch all referrals and filter client-side to the requested batch. Count total referral rows and distinct patients from the filtered rows.
2. Validate each diagnosis code against ICD-10. Use the template's expected chapter or the service-line chapter policy supplied by the task. Unknown codes are invalid; out-of-range chapters are invalid for the audit even if the code exists.
3. Check narrative and laterality independently:
   - `laterality_mismatch` when the code requires laterality and the narrative names the opposite side;
   - `missing_laterality` when the code requires laterality and the narrative omits a side;
   - `narrative_mismatch` when none of the ICD expected terms or accepted clinical synonyms appear in the narrative.
   Multiple mismatch types may apply to the same referral.
4. Detect duplicate groups within the batch by same patient, same requested date/service line, resubmission or duplicate coordination notes, and overlapping clinical intent. Include all rows in a duplicate group when the template says all duplicate group rows are blockers.
5. Do not treat same-patient referrals with distinct clinical purposes as duplicates; record them as separate clinical reviews if the template asks for insurance or patient anomalies.
6. Find insurance anomalies by grouping batch patients by insurance ID and comparing demographics. Shared insurance across different patients is not enough to merge; assign a verify-membership disposition unless duplicate-candidate evidence resolves it.
7. Build follow-up queues directly from referral facts:
   - authorization missing/pending from `authorization_status`;
   - records request when required office-note records are absent;
   - imaging follow-up when required imaging is absent or the coordination note explicitly says imaging is pending.
8. Assign action tiers by severity:
   - Tier 1: urgent coding issues, invalid/out-of-range urgent referrals, or duplicate blockers;
   - Tier 2: routine coding, authorization, clinical, or document blockers;
   - Tier 3: administrative document completion without urgent clinical or coding risk.
   Use the receiving provider as owner unless the template names another owner rule.
9. Compute summary counts from the final normalized arrays and queues after de-duplication, not from intermediate scratch lists.

## Final JSON Check

Before responding, verify:

- The JSON parses.
- Required top-level keys are present and no extra prose appears.
- Enum values are exactly from the template.
- Sorted arrays follow the template's ordering.
- Dates are `YYYY-MM-DD`.
- Every emitted evidence ID can be traced to an API response.
- Distractor and excluded arrays contain only records that were actually reviewed and intentionally left out.
