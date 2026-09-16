# EHR Quality Rules

## Duplicate Merge And Duplicate Review

Fetch the duplicate candidate, both patient details, both active clinical lists, relevant documents, and audit logs.

Use active patient endpoints as authoritative for clinical key unions. The candidate `merge_preview` is a preview only; add any active condition, medication, or allergy keys found in patient endpoints but missing from the preview, and list inactive or unrelated keys only in explicit excluded-distractor fields.

Choose merge target/source this way:

- Prefer the candidate's preferred target and source when present and consistent with patient canonical status.
- Confirm the source patient points to the target when the source has duplicate canonical status and a canonical patient ID.
- Emit merge-ready dispositions only when identity match signals are strong and conflicts are minor normalization issues.
- Emit manual review or review-hold dispositions when the candidate status is review-oriented, the preferred target/source is absent, or conflict signals include hard demographic or clinical contradictions such as different given name, different phone, different DOB/insurance/address, or opposite-laterality problems.
- For review-hold or do-not-merge outcomes, leave merge target/source null when the template permits null and do not invent a canonical direction.

Populate identity signals directly from the candidate, sorted when set-like. Build demographic matches/conflicts by comparing patient detail fields: DOB, sex, phone, insurance ID, PCP, address, name components, suffix, and canonical linkage. Normalize labels to the template's style.

For packet evidence, include final identity verification, registration, external continuity, or specialty continuity documents that support identity or ongoing care. Exclude general chart summaries and unrelated documents. Include audit log IDs whose patient, event, or summary matches the requested duplicate review, identity review, merge, or external import; exclude unrelated audit rows even when returned by the endpoint.

## Referral Coordination Packets

Fetch referral detail, patient detail, active conditions/medications/allergies, encounters, documents, receiving provider, ICD-10 lookup for diagnosis codes, and any supporting providers.

Use active diagnoses from the patient condition endpoint. Mark referral-relevant diagnoses when they match the referral service line, referral diagnosis narrative, recent encounter diagnoses, or supporting symptom codes. Include referral-intake conditions when active and relevant.

Validate the primary referral code with `/api/icd10/{code}`:

- `valid_matches_narrative`: lookup succeeds and the narrative matches expected terms or known synonyms.
- `valid_but_narrative_mismatch`: lookup succeeds but expected terms do not match the narrative or laterality.
- `wrong_service_chapter`: lookup succeeds but the code chapter is outside the expected service-line chapter.
- `invalid_code`: lookup fails.

When an ICD record has `requires_laterality`, compare left/right terms in the code's expected terms with the referral narrative. Emit laterality mismatch or missing-laterality findings according to the template.

For allergy readiness, use active allergy records with allergen, reaction, severity, status, and source. Mark complete when details are present and non-conflicting. Mark clarification needed when details are missing, statuses conflict, or referral notes explicitly request confirmation.

For recent encounter evidence, prefer signed or amended encounters that match the referral service line, diagnosis codes, medications, and care-plan notes. Use the most recent relevant encounter over unrelated newer encounters. Populate care-plan tags from the template's enum by matching diagnosis, symptom, specialty, and medication evidence.

For required documents, compare the referral's `documents_received` and patient documents against service-line requirements. Cardiology referrals commonly require a final echocardiogram and an office note when the template asks for those fields. Orthopedic referrals commonly require an office note and imaging such as xray or MRI when the audit template asks for document queues. Treat cancelled, preliminary, missing, or note-indicated pending documents as blockers when the template says so.

For medication highlights, emit active medications that are relevant to the referral problem: diuretics for heart failure, antihypertensives for blood pressure, insulin or other diabetes medications for perioperative glucose risk, statins or antiplatelets for cardiovascular context, and other active medications only if the template permits a generic reason.

Authorization readiness should combine referral status, authorization status, provider availability, code validation, document completeness, and allergy readiness. Missing or pending authorization blocks send-readiness unless the template defines it as non-blocking. Missing required documents, invalid codes, clinical mismatch, missing provider, or incomplete allergy details should emit the matching blocking issue codes.

## Care Transition Packets

Fetch patient detail, recipient provider, active conditions/medications/allergies, encounters, immunizations, and disclosures.

Active key arrays come from active endpoint records only, de-duplicated by normalized key and sorted ascending.

Select handoff encounters by relevance before raw recency. Prefer encounters within the handoff window that match the transition specialty, care-transition type, diagnosis codes, medications, or care-plan notes. Exclude stale encounters outside the window and unrelated encounters even if they are newer. Sort selected handoff encounters newest to oldest, and sort excluded IDs ascending unless the template says otherwise.

Choose the latest immunization by max date. Choose disclosure records that match the recipient provider and requested purpose; status must be permitted for unblocked send-readiness.

Derive risk flags from active conditions, medications, allergies, and encounter notes:

- Cognitive or memory-loss flags from active cognitive conditions or relevant recent notes.
- Fall-risk or perioperative-note flags from orthopedic handoff notes, osteoarthritis, mobility limitations, or pain-medication context.
- Hypertension from active hypertension.
- Insulin-dependent diabetes and perioperative glucose-plan flags from active diabetes plus active insulin or a care-transition note requesting a glucose plan.
- Latex allergy from active allergy records, with empty condition/medication/encounter evidence if the evidence schema has no allergy field.

Packet readiness is not blocked by risk flags alone. Emit a risk-aware ready status when required patient, recipient, active lists, handoff encounters, immunization, and permitted disclosure are present. Emit not-ready and blocking issue codes for missing core evidence or non-permitted disclosure.

## ServiceRequest Quality Checks

Fetch the patient's service requests, filter to the requested ServiceRequest ID, then fetch service code, requester provider, performer provider, patient conditions, encounters, and ICD-10 lookups for all reason codes.

Validate service code as true only when the service-code lookup exists, is active, and matches the performer service line. Dereference requester and performer IDs from the provider directory.

Validate each reason code with `/api/icd10/{code}`. `matches_patient_evidence` is true when the code appears in active conditions, relevant encounters, ServiceRequest narrative/SBAR text, or specialty-consistent evidence.

Check SBAR completeness by requiring non-empty situation, background, assessment, and recommendation fields. Emit present and missing sections as template enum values.

For quality-review outputs, normalize a draft order to the operational status implied by validation when the template asks for validated quality signals rather than raw-source echo. A draft order with complete SBAR, valid active service code, valid providers, and evidence-matching reason codes can be emitted as active; otherwise keep or downgrade according to the blocking evidence.

## Referral Batch Audits

Fetch referrals, then filter locally to the requested batch ID, service line, and requested date. Fetch ICD-10 for every diagnosis code, patient details for involved patients, and provider details for receiving providers. Do not let unrelated rows returned by the endpoint affect counts.

Batch counts:

- `record_count`/`total_referral_rows`: number of filtered referral rows.
- `unique_patient_count`/`unique_patients`: distinct patient IDs in filtered rows.
- Urgent/routine counts: count filtered rows by urgency.
- Issue counts: count emitted issue arrays or queues after de-duplication rules from the template.

Invalid or out-of-range code referrals include unknown ICD codes and codes whose ICD chapter is outside the template's expected chapter for the service line. For orthopedic audits, use the template's expected chapter exactly; do not treat injury codes as in-range unless the template allows the Injury chapter.

Laterality or narrative mismatch referrals are based on ICD expected terms:

- `laterality_mismatch`: the code's expected left/right side conflicts with the referral narrative.
- `missing_laterality`: the ICD requires laterality but the narrative omits a side.
- `narrative_mismatch`: the narrative does not match expected condition/anatomic terms or uses a different clinical concept.

Duplicate groups are same-patient resubmissions in the same batch and clinical context, especially when a referral ID or coordination note marks a duplicate. Include all rows in the duplicate group. If no group ID is supplied, construct a deterministic ID from batch and patient ID using uppercase letters, digits, and hyphens.

Insurance-patient anomalies are shared insurance IDs across different patients in the audited rows. Use patient detail records for insurance IDs. Treat same-patient separate clinical referrals as separate clinical reviews unless they meet the duplicate-group rule.

Follow-up queues:

- `authorization_missing`: authorization status missing.
- `authorization_pending`: authorization status pending.
- `records_request`: missing required office-note records.
- `imaging_follow_up`: missing required imaging or coordination notes that indicate imaging is pending, even if some imaging-like document is already listed.

Action tiers:

- Tier 1: urgent referrals with coding/laterality/narrative blockers or any duplicate-blocker group rows.
- Tier 2: routine referrals with coding, authorization, document, imaging, or clinical mismatch blockers.
- Tier 3: administrative document completion when the referral is otherwise clinically/code-valid and needs only routine document completion.

Owner provider IDs should come from the referral receiving/performer provider. Sort referral object arrays by referral ID unless the template gives a different rule, and recompute summary counts from the emitted normalized arrays.
