# EHR Quality Patterns

This reference captures reusable patterns for the EHR quality-governance JSON tasks. Read only the sections that match the current prompt.

## Universal Normalization Rules

- Start from the template, not from memory. The same clinical theme can use different key names, enum spellings, or ordering rules across tasks.
- Keep IDs stable and exact. Do not replace IDs with names when an ID is requested.
- Include every required key even when the value is `[]`, `false`, or `null`.
- Sort set-like string arrays alphabetically unless the template gives a different rule.
- Sort object arrays by the template's rule: usually by `referral_id`, `code`, `risk_flag`, `group_id`, or newest-to-oldest date.
- Exclude distractors explicitly when the template has exclusion fields. A record can be useful evidence for one section and still be excluded from a different section.
- Recompute counts after final filtering. Summary counts should equal the arrays in the emitted JSON, not a rough total from an endpoint.

## Endpoint Map

Use the documented base URL and these endpoint families:

| Need | Endpoint Pattern | Notes |
| --- | --- | --- |
| Patient demographics and PCP | `GET /api/patients/{patient_id}` | Use for MRN, DOB, display name, canonical status, insurance, phone, PCP. |
| Active conditions | `GET /api/patients/{patient_id}/conditions` | Filter to `status == "active"` for active unions and diagnosis evidence. |
| Active medications | `GET /api/patients/{patient_id}/medications` | Filter to active status unless the template asks for inactive/excluded records. |
| Active allergies | `GET /api/patients/{patient_id}/allergies` | Preserve allergen, reaction, severity, status, source when requested. |
| Encounters | `GET /api/patients/{patient_id}/encounters` | Select by date, signed status, type, diagnoses, care plan notes, and service-line relevance. |
| Documents | `GET /api/patients/{patient_id}/documents` | Check type, status, source, date, and whether it is required or merely a distractor. |
| Immunizations | `GET /api/patients/{patient_id}/immunizations` | Choose latest by date when requested. |
| Disclosures | `GET /api/patients/{patient_id}/disclosures` | Match recipient, status, date, and purpose to packet scope. |
| ServiceRequests | `GET /api/patients/{patient_id}/service-requests` | Find the named request locally inside the returned array. |
| Duplicate candidates | `GET /api/duplicates/{candidate_id}` | Use status, patient IDs, match/conflict signals, and merge preview as candidate evidence. |
| Referrals | `GET /api/referrals/{referral_id}` or `GET /api/referrals` | For batches, fetch the collection and filter locally by exact batch ID and service line. |
| ICD-10 | `GET /api/icd10/{code}` | Use chapter, expected terms, and laterality requirement for validation. |
| Providers | `GET /api/providers/{provider_id}` | Use for full provider contact and service line. |
| Service codes | `GET /api/service-codes/{code}` | Use for service-code validity and performer service line. |
| Audit logs | `GET /api/audit-logs` | Filter locally to prompt patients/candidates and relevant event summaries. |

## Duplicate-Chart Merge Readiness

Evidence to collect:

- Duplicate candidate detail.
- Both patient details.
- Both patients' active conditions, medications, and allergies.
- Relevant documents for identity or outside continuity.
- Relevant audit logs for identity review, duplicate marking, imports, or merge events.
- Provider directory entries for packet contacts.

Decision pattern:

- A merge-ready duplicate usually has a live/open candidate, strong identity match signals, no material clinical identity conflict, and a concrete preferred target/source.
- A review hold keeps merge target/source null when conflicts are clinically meaningful or no canonical target/source is established.
- Do not infer merge readiness from shared insurance alone; compare DOB, phone, names, addresses, PCP, canonical status, and conflict signals.
- Use patient active-list endpoints for unioned condition/medication/allergy keys. Compare those unions to any duplicate preview and record keys added from authoritative active endpoints when the template asks.
- Select packet documents narrowly: identity support and external continuity documents are useful; generic chart summaries and unrelated documents are distractors unless the prompt says otherwise.
- Specialist contacts usually come from the provider associated with the relevant external continuity or referral evidence; PCP contact comes from patient detail or provider lookup.

## Referral Coordination Packets

Evidence to collect:

- Referral detail.
- Patient detail and active clinical lists.
- Allergies, encounters, documents, and provider directory.
- ICD-10 lookup for referral diagnosis and any supporting codes.

Decision pattern:

- Use the referral's service line, diagnosis narrative, active conditions, and recent signed encounters to decide which diagnoses belong in the packet.
- Add referral-intake diagnosis codes when they are referral-relevant even if they are not already in the active problem list, if the template expects this reconciliation.
- Validate primary diagnosis by ICD code existence, chapter, expected terms, laterality, and narrative match.
- Required documents are service-line specific. Confirm both the referral row's `documents_received` and actual document endpoint status/date when document IDs are required.
- Allergy readiness requires active, specific allergy records or a clear no-known-allergies state. Incomplete notes become follow-up/blocking issues only if the actual allergy evidence is incomplete or conflicting.
- Medication highlights should be active medications relevant to the referral diagnosis or major comorbidities; order referral-relevant medications before general active medications unless the template says set semantics apply.
- Overall readiness combines authorization, referral status, code validity, required documents, allergies, and provider resolution.
- For normalized letter fields, choose the enum that best summarizes the evidence; do not invent a new enum.

## Care-Transition Packets

Evidence to collect:

- Patient detail and recipient provider directory entry.
- Active condition, medication, and allergy lists.
- Encounters, immunizations, disclosures, and relevant documents if present.

Decision pattern:

- Select handoff encounters by the requested service-line transition window, not simply the latest records.
- Prefer signed or amended encounters that explain the handoff, perioperative context, care plan, or specialty transition.
- Keep stale or unrelated encounters out of the handoff list, but still allow them as risk-flag evidence if the template's evidence section asks for that supporting history.
- Choose latest immunization by date.
- Disclosure readiness requires a disclosure matching the recipient/provider and purpose with a permitted status.
- Risk flags come from active clinical lists and corroborating encounters. Emit risk-flag evidence arrays even when some evidence arrays are empty.
- A packet can be ready with risk flags when required packet components are present and risk flags only require attention, not blocking remediation.

## ServiceRequest and SBAR Validation

Evidence to collect:

- The named patient's ServiceRequest list, then select the named request.
- Requester and performer provider directory entries.
- Service-code lookup.
- ICD-10 lookup for every reason code.
- Patient active conditions and relevant encounters/documents for matches_patient_evidence.
- Duplicate candidate detail if duplicate-review outcome is in scope.

Decision pattern:

- Validate the service code against the service-code directory and use its service line for performer service-line checks.
- Validate each reason code independently with ICD lookup. `matches_patient_evidence` should reflect active conditions, encounter diagnoses, documents, or care plan evidence for that patient.
- SBAR is complete only when situation, background, assessment, and recommendation are all present with meaningful content.
- For duplicate review holds, preserve null merge IDs if the candidate has conflicts or lacks a preferred source/target.
- If a raw status appears inconsistent with quality-governance evidence, use the template wording and surrounding evidence to decide whether the answer wants raw status or normalized readiness/status. Record only the normalized JSON value in the final answer.

## Referral Batch Audits

Evidence to collect:

- Referral collection filtered exactly to the requested batch/service line/date.
- ICD-10 lookup for each diagnosis code in scope.
- Patient detail for each patient in scope when uniqueness, insurance anomalies, or duplicate grouping is requested.
- Provider directory for owner/receiving providers if action-plan owner IDs or service lines need verification.

Decision pattern:

- Compute `record_count` from filtered referral rows and `unique_patient_count` from distinct patient IDs.
- Invalid/out-of-range diagnosis rows are codes that are unknown or in the wrong chapter for the requested service line. Use the ICD directory chapter, not diagnosis narrative alone.
- Laterality/narrative mismatches compare referral narrative against ICD expected terms. Use these checks:
  - `laterality_mismatch` when left/right in narrative contradicts left/right in expected terms.
  - `missing_laterality` when the ICD code requires laterality and the narrative omits it.
  - `narrative_mismatch` when the body part or condition family does not match expected terms, even if laterality is absent.
- Duplicate referral groups are same-patient resubmissions for the same clinical review. Do not merge separate clinical referrals solely because the patient repeats.
- Shared insurance across different patients is an anomaly to verify, not proof of a patient duplicate.
- Follow-up queues are derived from exact referral fields:
  - Missing authorization goes to authorization-missing.
  - Pending authorization goes to authorization-pending.
  - Missing office note goes to records request when the template defines that queue.
  - Missing or pending imaging goes to imaging follow-up when imaging is required for the service-line scenario.
- Tiering should be deterministic:
  - Tier 1 for urgent coding issues or duplicate blockers.
  - Tier 2 for routine coding, authorization, clinical mismatch, or document blockers.
  - Tier 3 for administrative document completion without urgent clinical/coding blocker.
- Summary counts must match the emitted arrays and tier lists exactly.
