# Evidence Playbook

## Endpoint Map

Use the task's allowed read-only API routes. Common route families:

- Patients: demographics and identifiers from `/api/patients/{patient_id}`.
- Active lists: `/conditions`, `/medications`, and `/allergies` under the patient route.
- Timeline/evidence: patient encounters, documents, immunizations, disclosures, and service requests.
- Duplicate review: duplicate candidate detail plus both patient charts.
- Referrals: referral detail for single packets; referral list/search for batch audits.
- Directories: providers, ICD-10 codes, and service codes by stable ID/code.
- Audit logs: filter list results by candidate, patient, referral, ServiceRequest, document, or merge identifiers mentioned in the task evidence.

If a search endpoint supports query parameters, use the most specific parameter from the prompt. If query support is uncertain, fetch the list endpoint and filter locally by exact ID, batch ID, patient ID, service line, or date.

## Active-List Reconciliation

- Use only records whose status is active or equivalent unless the schema asks for exclusions.
- Emit `normalized_key` values, not display labels, when the template asks for condition, medication, or allergy keys.
- For duplicate-merge packets, build the union of active keys across the merge participants from patient active-list endpoints. Treat duplicate-preview active lists as hints; report additions from patient endpoints when the schema asks.
- Keep inactive, entered-in-error, stale, and unrelated records out of active unions. Include them only in explicit excluded-distractor fields.

## Duplicate Review and Merge Readiness

- Use duplicate-candidate status, candidate decision fields, source/target references, and patient demographics together. Do not infer a merge from demographic similarity alone.
- Classify match signals from exact or normalized identity agreement: date of birth, phone, insurance, same or variant name, address normalization, shared external continuity evidence, or same PCP when supported.
- Classify conflict signals from substantive disagreement: different date of birth, different insurance, different phone, incompatible names, different addresses, or clinical conflicts such as opposite laterality.
- Emit merge target/source only when the candidate and evidence support a merge. If the template allows nulls and the evidence requires review, leave merge IDs null and choose the review disposition.
- Use audit logs and final identity/continuity documents as evidence when requested; exclude unrelated summaries or non-final documents unless the template says otherwise.

## Referral Coordination

- Reconcile referral detail with the active patient chart. Referral-intake diagnoses can supplement the active problem list when the schema asks for referral-relevant diagnoses.
- Validate primary and supporting diagnosis codes with `/api/icd10/{code}`. Mark validity by whether the code exists, its chapter fits the service line/template, and the code narrative matches the referral narrative and patient evidence.
- For allergies, prefer active documented allergy records and referral-form allergy fields. Use incomplete/conflicting statuses only when the available records lack reaction/severity/status or disagree.
- Select recent encounter evidence by relevance to the referral reason and care-plan tags, then by signed/amended status and recency.
- Required documents are service-specific. Include final received documents, mark missing or preliminary/cancelled documents as blockers when the template treats them as required.
- Medication highlights should include active medications relevant to the referral reason first, then other active medications only if the schema or prompt asks for them.

## ServiceRequest Quality

- Validate the ServiceRequest's `status`, `intent`, `priority`, patient, requester, performer, authored date, occurrence date, service code, and reason codes against the environment records.
- Resolve performer service line from the provider directory.
- Validate service codes with `/api/service-codes/{code}` and reason codes with ICD-10 lookups.
- For SBAR coverage, inspect structured sections or document/encounter text fields for situation, background, assessment, and recommendation. Emit missing sections exactly as template enums.

## Care-Transition Packets

- Recipient information comes from `/api/providers/{provider_id}`.
- Handoff encounters should be selected by the prompt's specialty, transition purpose, date window, encounter type, signed status, and recency. Preserve the requested order, often newest to oldest.
- Latest immunization means latest by administered/documented date among applicable immunization records.
- Disclosure must match the recipient and purpose and have a permitted/current status when readiness requires it.
- Derive risk flags only from active chart evidence and selected/relevant encounters. Typical derivations include active cognitive condition, fall-risk encounter note, hypertension, insulin-treated diabetes, active latex allergy, and perioperative glucose-planning need.

## Batch Referral Audits

- Use all rows in the requested batch for record counts. Use distinct patient IDs for unique-patient counts.
- Invalid or out-of-range code rows require ICD-10 lookup evidence. Compare actual chapter against the expected chapter in the template or service line.
- Narrative/laterality mismatches require comparing the referral narrative with ICD expected terms and patient evidence. Laterality mismatch, missing laterality, and narrative mismatch can co-exist when supported.
- Duplicate groups are same-patient resubmissions within the audited scope; keep separate same-patient clinical referrals out of duplicate groups when evidence shows a distinct clinical review.
- Insurance anomalies are cross-patient or same-patient insurance patterns requested by the schema. Do not convert shared insurance into a duplicate-patient conclusion without duplicate-candidate evidence.
- Follow-up queues come from missing authorization, pending authorization, missing required records, and missing/pending imaging fields in referral or document evidence.
- Tier action plans should be mutually consistent with urgency and blockers: immediate for urgent coding issues or duplicate blockers, short-term for routine coding/auth/document blockers, and administrative for document-only completion.
- Summary counts must match the emitted arrays and the audited referral rows. Recompute after sorting and deduplicating.

## Output Checks

- Match the template's top-level key order when practical.
- Preserve booleans as booleans, numbers as numbers, and allowed `null` values as JSON null.
- Sort ID arrays ascending unless the template says newest-to-oldest or another stable order.
- For object arrays, sort by the template's named key, commonly referral ID, code, risk flag, or date.
- Do not include source notes, endpoint dumps, confidence statements, or markdown in the answer.
