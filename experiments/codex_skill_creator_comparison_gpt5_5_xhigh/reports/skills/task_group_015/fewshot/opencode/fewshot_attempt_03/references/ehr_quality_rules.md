# EHR Quality Rules

Apply these rules through the current prompt and answer template. They are reusable heuristics, not fixed answer values.

## Duplicate Chart Packets

- Fetch the duplicate candidate by ID and both patient records. Verify demographics yourself: date of birth, phone, insurance, sex, address normalization, primary care provider, name variants, suffixes, and canonical status.
- A candidate is merge-ready only when the candidate is active/open, has an explicit preferred target and source, the target is the canonical/active record, and conflicts are minor or explainable by normalization. High-risk conflicts such as different given name, different phone, different DOB/insurance, or opposite-laterality active problems require manual review.
- When manual review is required, use review/hold dispositions and leave merge target/source null if the template's enum and nullable fields support that.
- Build active condition/medication/allergy unions from patient active-list endpoints, not only from duplicate preview. If the template asks for reconciliation, report active endpoint keys missing from the preview.
- Evidence documents for merge packets should be identity, merge-review, or external-continuity documents with final status. Exclude unrelated chart summaries or stale/unrelated documents.
- Audit evidence should involve identity review, merge review, external imports, or the relevant patients. Exclude unrelated completed merges or unrelated patient history.

## Referral Coordination Packets

- Reconcile the referral row with patient detail, active conditions, medications, allergies, encounters, documents, provider detail, and ICD-10.
- Include active diagnoses from active condition records. Mark `referral_relevant` true for the referral's primary diagnosis, active referral-intake symptoms, or conditions directly matching the referral narrative/service line.
- Validate the primary diagnosis through ICD-10. `valid_matches_narrative` requires a valid code, a suitable service-line chapter, and narrative terms/laterality that match the ICD entry and patient evidence.
- Choose supporting codes from active referral-relevant symptom or secondary diagnosis records, not from unrelated chronic conditions.
- Allergy readiness is complete when active allergy records provide allergen, reaction, severity, status, and source needed by the template. Missing, conflicting, or unknown allergy evidence should block readiness when the template lists allergy blockers.
- Required documents must be present in the referral row or patient documents and, when patient document details exist, should be final rather than preliminary/cancelled. For cardiology-style packets, an echocardiogram plus office note is a complete packet when the template asks for those.
- Select recent encounter evidence by matching diagnosis codes, care-plan notes, medication mentions, provider, signed status, and recency to the referral narrative.
- Highlight active medications that explain or support the referral: medications mentioned in the selected encounter, medications tied to referral-relevant conditions, and service-line-specific medications. Do not list every baseline medication unless the template asks for all active meds.
- Readiness is ready only when authorization, required documents, provider, allergy, and diagnosis-code checks have no blockers. Use the template's blocker codes for any missing authorization, documents, clinical mismatch, allergy issue, provider issue, or code issue.

## Care Transition Handoff Packets

- Patient and recipient fields come from patient detail and provider detail.
- Active condition, medication, and allergy key arrays come from active endpoint records and are sorted ascending.
- Select handoff encounters for the packet by transition relevance first, then recency: care-transition encounters, signed/amended encounters with the handoff diagnosis/service-line evidence, handoff-specific care-plan notes, and medication mentions. Exclude unrelated newer encounters, amended/telehealth distractors, and stale outside-window records unless the template asks for risk evidence.
- Risk-flag evidence may use active lists and any current encounter that supports the risk, even if that encounter is not one of the selected handoff encounters.
- Map common risk flags from evidence:
  - memory/cognitive condition keys -> cognitive memory-loss flags
  - orthopedic OA plus fall-risk notes or pain meds -> fall-risk note flags
  - hypertension condition keys -> hypertension flags
  - diabetes plus insulin medication -> insulin-dependent diabetes and perioperative glucose-plan flags
  - active latex allergy -> latex allergy flags
- Latest immunization means the most recent immunization by date. Disclosure readiness requires a disclosure for the recipient/provider or facility with permitted status.
- A packet can be ready with risk flags when required patient, recipient, active lists, handoff encounters, immunization, and permitted disclosure exist and there are no blocking issue codes.

## ServiceRequest Quality Review

- ServiceRequests are patient-scoped. Fetch `/api/patients/{patient_id}/service-requests` and locate the requested ID.
- Validate service code existence, active status, order kind, and service line. Validate requester and performer provider IDs and ensure the performer service line fits the requested service.
- Validate every reason code through ICD-10 and compare each to active patient conditions, encounters, and service-line evidence. `matches_patient_evidence` should be false when a valid code is unrelated to the patient evidence.
- SBAR coverage is complete only when situation, background, assessment, and recommendation are all non-empty.
- For quality-governance packets, report the normalized actionable status requested by the template. If the source request is draft but all service code, provider, reason-code, patient-evidence, and SBAR checks pass, the normalized packet may be ready/active according to the template instead of simply echoing the draft queue state.

## Referral Batch Audits

- Filter the referral list by the requested batch ID in memory if the API does not filter server-side. Counts are based on the filtered rows only.
- For service-line audits, use the template's expected chapter when it provides one. Otherwise infer from service line: orthopedics usually expects Musculoskeletal; cardiology Circulatory; pulmonology Respiratory; neurology Nervous system; oncology Neoplasms.
- `invalid_or_out_of_range` includes unknown ICD-10 codes and valid codes whose chapter is outside the expected service-line chapter.
- Narrative mismatch checks compare normalized referral narrative against ICD expected terms. Laterality mismatch occurs when the narrative names the opposite side. Missing laterality occurs when the ICD entry requires a side but the narrative omits one. Narrative mismatch occurs when the body site/condition terms do not match even if laterality is not the issue.
- Same-patient duplicate groups come from duplicate/resubmission signals such as repeated patient/service/narrative rows, duplicate IDs, or coordination notes indicating a resubmission. When the policy asks for all duplicate group rows as blockers, include both the original and resubmitted rows in Tier 1.
- Insurance anomalies are different patients sharing an insurance ID within the audited batch, especially when duplicate-candidate signals also exist. Recommend verification rather than merge when identity conflicts are unresolved.
- Authorization queues come from `authorization_status`: missing and pending are separate.
- Records-request queues contain rows missing required office-note documentation.
- Imaging follow-up queues contain rows whose coordination note says imaging is pending or whose documents contain no imaging evidence. For orthopedic batches, `xray`, `mri`, and similar imaging labels count as imaging evidence; if the note explicitly says imaging is pending, keep the row in the imaging queue even when one imaging label is present.
- Tier 1 is for urgent rows and duplicate blockers. Tier 2 is for routine clinical/coding/authorization blockers. Tier 3 is for administrative document completion when no urgent, duplicate, coding, or clinical mismatch blocker exists.
- Summary counts must equal the emitted arrays and filtered batch rows, not unfiltered API totals.
