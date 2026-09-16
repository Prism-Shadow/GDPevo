---
name: ehr-quality-json
description: Use this skill for EHR quality-governance tasks that require reading a read-only task environment API and returning normalized JSON packets, especially duplicate-chart merge readiness, referral coordination, care-transition handoffs, ServiceRequest validation, ICD-10/service-code checks, provider contact lookup, and referral batch audits. Use it whenever the prompt mentions EHR, referrals, duplicate candidates, patient active lists, handoff packets, audit queues, ICD validation, or strict answer_template JSON.
compatibility: Requires shell access with curl or Python 3 for HTTP GET requests to the task environment described by the prompt or environment_access.md.
---

# EHR Quality JSON

Use this skill to solve read-only EHR quality-governance tasks that ask for a normalized JSON answer against an `answer_template.json`.

## Operating Rules

1. Read the user prompt, `input/payloads/answer_template.json`, and any other payload files before querying the API.
2. Extract every explicit ID: patient IDs, duplicate candidate IDs, referral IDs, ServiceRequest IDs, provider IDs, batch IDs, dates, and requested service lines.
3. Use only allowed GET endpoints from the task environment. Do not infer from unavailable source code or hidden evaluator behavior.
4. Treat the template as the output contract. If the template has metadata keys such as `description`, `schema`, `types`, or `required_top_level_keys`, do not emit those metadata keys unless they are actual required answer keys.
5. Return JSON only. Use exact template key names, null where the template permits null, booleans as booleans, and dates as `YYYY-MM-DD`.
6. Sort arrays when the template says they are sets or sorted. For object arrays, follow the template ordering rule; otherwise use stable domain order such as code ascending, ID ascending, or newest-to-oldest for encounter timelines.
7. Do not fabricate missing evidence. Leave fields null, false, empty, or blocked according to the template when the API does not support a claim.

## Evidence Collection

Use `scripts/ehr_fetch.py` when it saves time. From this skill directory:

```bash
python scripts/ehr_fetch.py --base-url "$TASK_ENV_BASE_URL" --patients "<patient-id>" --patient-subresources all
python scripts/ehr_fetch.py --base-url "$TASK_ENV_BASE_URL" --duplicates "<duplicate-candidate-id>"
python scripts/ehr_fetch.py --base-url "$TASK_ENV_BASE_URL" --referrals "<referral-id>" --batch "<batch-id>" --directories --audit-logs
```

The script only performs GET requests and prints a JSON evidence bundle. Manual `curl -s` calls are also fine.

Useful endpoint families:

- Patient demographics: `/api/patients/{patient_id}`
- Patient active lists and history: `/conditions`, `/medications`, `/allergies`, `/encounters`, `/immunizations`, `/documents`, `/service-requests`, `/disclosures`
- Duplicate review: `/api/duplicates/{candidate_id}` and `/api/duplicates/candidates`
- Referrals: `/api/referrals/{referral_id}` and `/api/referrals`; client-filter referral search by `batch_id`, `service_line`, `requested_date`, and explicit IDs
- Validation directories: `/api/icd10/{code}`, `/api/providers/{provider_id}`, `/api/service-codes/{code}` plus their collection endpoints
- Audit evidence: `/api/audit-logs`; client-filter by patient IDs, candidate IDs, event text, or summary text

## Source Precedence

- Active condition, medication, and allergy unions come from patient subresource endpoints, filtered to `status == "active"`. Use `normalized_key`, de-duplicate, and sort.
- Duplicate-candidate merge previews are hints, not the authority for active clinical unions. Compare preview keys with active endpoint unions when the template asks for reconciliation or keys added from active endpoints.
- Referral records control referral ID, batch, requested date, service line, authorization, urgency, receiving provider, diagnosis code, diagnosis narrative, status, and declared received-document types.
- Patient documents provide concrete `document_id`, type, status, date, and source. Prefer final documents relevant to the requested packet; exclude chart summaries and unrelated exports when the template asks for packet evidence.
- Provider directory records are authoritative for provider name, role, facility, service line, phone, and fax. Patient demographics often embed primary-care-provider details, but still verify IDs when contact fields matter.
- ICD-10 records are authoritative for chapter, whether laterality is required, and expected narrative terms.
- Service-code records are authoritative for active/inactive service codes and service-line fit.

## Duplicate Merge Readiness

For duplicate packets, fetch the duplicate candidate and both patient demographics, active lists, documents, and relevant audit logs.

Determine target/source from the strongest evidence:

- Use `merge_preview.preferred_target_patient_id` and `merge_preview.source_patient_id` when both are present.
- Confirm with patient demographics: a source duplicate often has `canonical_status == "duplicate"` and `canonical_patient_id` pointing to the target, while the target is active.
- If the candidate is unresolved, preferred target/source are absent, or material conflicts remain, emit a review-hold/manual-review disposition and null target/source only if the template allows null.

Classify identity evidence:

- Copy candidate `match_signals` and `conflict_signals` into the requested normalized fields, sorted if set semantics apply.
- Compare demographics directly. Exact matches usually include DOB, insurance, phone, sex, and primary-care provider. Variant names or normalized address differences can be non-blocking conflicts when the candidate still identifies a target/source.
- Treat different DOB, insurance, phone, given name with no clear variant, or opposite laterality problems as manual-review signals.

For clinical unions, union active endpoint keys across all patient IDs. Track inactive keys separately only if the template asks for excluded distractors.

For evidence IDs, include final identity-verification or external-continuity documents and audit logs that mention identity review, duplicate review, external import, or the involved patients. Exclude unrelated chart summaries or unrelated historical audit events.

## Referral Coordination Packets

For a single referral, fetch the referral, patient demographics, active conditions, medications, allergies, encounters, documents, receiving provider, and relevant ICD codes.

- Emit all active diagnoses requested by the template, marking `referral_relevant` true for the referral diagnosis, same service-line diagnoses, and supporting symptom/encounter codes that match the referral narrative.
- Validate the primary diagnosis code with `/api/icd10/{code}`. The validation is good when the code exists, chapter fits the service line or template expectation, and the narrative matches an expected term or close clinical synonym.
- Supporting codes come from active conditions or recent encounters that directly support the referral narrative.
- Allergy readiness is complete when active allergy records contain allergen, reaction, severity, status, and source. Missing details, conflicting active records, or unclear status should block only when the template says allergy completeness is required.
- Select recent encounter evidence by clinical relevance to the referral, not just newest date. Prefer signed encounters whose diagnoses, care-plan notes, or medication mentions align with the referral.
- Required document evidence should combine referral `documents_received` with patient document records. Use patient document IDs/status/dates when a concrete document exists.
- Authorization readiness is ready only when authorization, required documents, provider, and diagnosis validation are all acceptable. Otherwise choose the hold reason that matches the blocker.

## Care-Transition Handoffs

For transition packets, fetch patient demographics, recipient provider, active lists, encounters, immunizations, disclosures, and documents if requested.

- Handoff encounters should be recent and relevant to the transition service line or surgery/handoff purpose. Do not blindly choose the newest encounters if newer records are unrelated.
- When the template asks for source selection, list included encounter IDs in the same order as the emitted encounters and list reviewed-but-excluded stale or irrelevant encounter IDs separately.
- Latest immunization is the most recent immunization by date unless the prompt narrows vaccine type.
- The disclosure must match the patient and recipient provider or recipient facility. `permitted` disclosures support readiness; denied, expired, pending, or missing disclosures are blockers.
- Derive risk flags from active conditions, active medications, active allergies, and encounter notes. Use the template's allowed flag values exactly. For surgery-oriented handoffs, common triggers are cognitive diagnoses, fall-risk notes, hypertension, insulin-treated diabetes, latex allergy, and perioperative glucose-plan notes.
- Readiness is `not_ready` if required patient, recipient, active-list, encounter, immunization, or disclosure evidence is missing or not permitted. Use `ready_with_risk_flags` when no blocker remains but risk flags are present.

## ServiceRequest Quality Checks

ServiceRequests are patient-scoped, so fetch `/api/patients/{patient_id}/service-requests` and select the requested ID.

- Validate `service_code` against `/api/service-codes/{code}`. It is valid only when active and aligned with the performer provider's service line.
- Validate every reason code through `/api/icd10/{code}`. Sort validation objects by code when requested.
- `matches_patient_evidence` is true when the code appears in active patient conditions, relevant encounters, or other patient evidence tied to the order.
- SBAR completeness requires non-empty `situation`, `background`, `assessment`, and `recommendation`.
- In quality-readiness templates, a draft ServiceRequest that has a valid service code, valid matching reason codes, a valid performer, and complete SBAR may be emitted as operationally active/ready if the schema is asking for the validated status rather than the raw stored state. Preserve the raw status when the prompt asks for raw extraction.

## Referral Batch Audits

For batch audits, fetch `/api/referrals`, filter to the exact batch ID and service line/date in the prompt, then fetch needed patients, providers, and ICD records.

Audit each referral row:

- Count total rows and distinct patient IDs after filtering.
- For invalid or out-of-range code lists, include unknown ICD codes and codes whose ICD chapter does not match the template's expected chapter for the service line.
- For narrative mismatches, compare the referral narrative to ICD expected terms. Use `laterality_mismatch` when the side conflicts, `missing_laterality` when the code requires a side but the narrative omits it, and `narrative_mismatch` when the condition/body-site meaning differs beyond laterality.
- Avoid double-labeling a same-condition missing-side case as a narrative mismatch unless the condition itself is also wrong.
- Duplicate referral groups are same-patient resubmissions in the same batch, especially when IDs or notes indicate duplicate/resubmission or rows are clinically overlapping. Sort group IDs and referral IDs.
- Insurance anomalies require patient lookup. Same insurance across different patient IDs is not by itself a merge decision; report it as a verification anomaly unless duplicate evidence independently supports a merge.
- Follow-up queues usually come from referral fields: missing or pending authorization, missing office-note records, and missing or pending imaging. If coordination notes say imaging is pending, include the row even if one imaging-type document is present.
- Tier 1 is for urgent coding issues or duplicate blockers. Tier 2 is for routine coding, authorization, or clinical-document blockers. Tier 3 is for administrative document completion without coding/auth/duplicate blockers. Rows with no blockers count as validated ready.
- Use the receiving or owner provider ID from the referral/provider evidence for action-plan ownership.

## Final Sanity Check

Before final output:

- Re-read the template and confirm every required top-level key is present.
- Confirm every emitted ID came from the prompt or API evidence.
- Check sorting and set de-duplication.
- Check that excluded distractors are only included when the template asks for them.
- Ensure there is no prose before or after the JSON.
