---
name: tg013-reflect-3-attempt-03
description: Transferable SOP for Northstar Care Intake Portal healthcare intake tasks.
---

# Northstar Care Intake Portal SOP

Use the task prompt credentials to sign in, then inspect the named record IDs in the portal. Prefer the detail page for each record, plus linked patient, benefits, pharmacy, chart, program, queue, policy, and explicitly linked duplicate/referral pages when the prompt calls for them. Return only the requested JSON schema. Keep primary rows sorted by ID ascending. Keep set-like arrays sorted consistently, preferably lexicographically unless the prompt gives another order.

## General Portal Practice

- Do not infer from list rows alone. Open each record detail page.
- The policy page is useful for current operating rules:
  - Registration: medical coverage must be active and in network; medication-managed intake requires active PBM and in-network preferred pharmacy.
  - Dialysis transfers: labs current within 30 days of requested start; infection screen current within 14 days; dialysis prescription must be final; medication list, allergy list, authorization, confidentiality statement, referring contact, and transport note are required.
  - Orthopedics: scheduling requires supported musculoskeletal coding, narrative/laterality agreement, records and imaging, required authorization, and duplicate review.
  - Charts: ready only when chart exists and demographics, history, active problems, current vitals, care plan or clinical instructions, and orientation communication are complete.
  - Chronic care: diabetes/hypertension pathways require diagnosis support, recent HbA1c or BP, consent, and complete program form; renal risk changes cadence and can require nurse escalation.

## Registration Readiness

For each patient, inspect `/patients/<id>`, `/benefits/<id>`, pharmacy network, and chart/program context if relevant.

- `medical_insurance`: pass only when coverage is active and medical network is in network. Inactive, terminated, or out-of-network coverage blocks.
- `pbm`: for medication-managed patients, pass only when PBM is active. `not located`, inactive, missing, or expired blocks. Use `not_required` only when the record is clearly not medication-managed.
- `pharmacy`: for medication-managed patients, pass only when the preferred pharmacy is in network. Otherwise use `not_required`.
- `demographics`: block if required registration fields are incomplete, especially address, consent, identity, phone, or emergency contact when the portal shows it as required/missing.
- `risk`: use `low` for clean clinical/lifestyle profiles, `moderate` for chronic conditions or routine lifestyle warnings, and `high` only for strong clinical-review signals such as multiple high-risk lifestyle/clinical findings, marked polypharmacy, or portal hot/warning combinations. High risk adds `clinical_review_required`.
- `overall_decision`: `blocked` for administrative gate blockers; `manual_review` for clinical-review-only cases; `ready` only when gates pass and no clinical review is required.
- `blocked_reasons`: include all applicable enum reasons: inactive/terminated coverage as `insurance_inactive`, out-of-network medical as `insurance_out_of_network`, inactive/not-located PBM as `pbm_inactive`, out-of-network pharmacy as `pharmacy_out_of_network`, incomplete demographics as `demographics_incomplete`, and high risk as `clinical_review_required`.

## Dialysis Transfers

Open each `/transfers/<id>` record.

- Missing packet items are any required packet elements with status `missing`, `draft`, `expired`, or otherwise not usable. Dialysis prescription must be `final`; merely received is not enough for that item.
- `stale_items` is only for otherwise usable labs or infection screens outside the freshness window. Do not put draft/missing/expired labs or infection screens in stale; put them in `missing_packet_items`.
- Labs are current when dated within 30 days of requested start. Infection screen is current within 14 days of requested start.
- `authorization_valid` and `confidentiality_valid` are true only when those items are final/received and usable, not draft/missing/expired.
- `start_compatibility`: map chair availability `capacity review` to `capacity_review`, waitlist language to `waitlist`, and available/usable chair language to `compatible`.
- `decision`: use `hold_missing_packet` before capacity holds when packet items are missing; use `hold_capacity` only when the packet is usable but start/chair capacity blocks; use `accept` only when packet, freshness, capacity, and prep are all acceptable.
- `route_owner`: `referring_facility` for packet/document defects, `capacity_coordinator` for capacity-only holds, `chart_prep` when packet/capacity pass but chart prep remains, and `intake_complete` when accepted.

## Orthopedic Referrals

Open `/referrals/<id>` and any explicitly linked referral IDs.

- Coding:
  - `chapter_valid` is true for M-code or supported musculoskeletal diagnosis.
  - `narrative_match` is true when the ICD code meaning matches the diagnosis narrative.
  - `laterality_match` is true when narrative, ICD laterality, and laterality field agree; non-lateral diagnoses can be `n/a`.
- Issue codes:
  - non-musculoskeletal or unsupported chapter: `invalid_chapter`
  - code/narrative condition mismatch: `diagnosis_mismatch`
  - side mismatch: `laterality_mismatch`
  - records missing: `missing_records`
  - imaging missing: `missing_imaging`
  - authorization missing/pending when required: `authorization_gap`
  - explicit linked duplicate or strong same-patient/same-condition duplicate evidence: `duplicate_referral`
- Readiness status should name the main action queue: `coding_clarification` for coding/laterality defects, `pending_records` for missing records/imaging, `authorization_followup` for authorization-only blockers, `duplicate_review` for duplicate blockers, and `ready_to_schedule` only when all checks pass.
- `priority_tier`: use `schedule` for ready referrals; otherwise map stat/same-day to `tier_1`, urgent to `tier_2`, and routine to `tier_3`.
- `follow_up_practice` is the referring practice when follow-up is needed; otherwise null.

## Chart Onboarding

Open `/charts/<patient_id>` and the linked patient page.

- `chart_ready` is true only when chart exists and no required section is missing.
- Missing sections:
  - chart does not exist: `chart_not_created`
  - demographics incomplete: `demographics`
  - history incomplete: `history`
  - problems incomplete or applicable active problems missing: `problems`
  - vitals not current or absent: `vitals`
  - care plan missing/draft and no completed clinical instructions: `care_plan_or_instructions`
  - orientation missing/draft/not sent when communication is still required: `orientation_message`
- `orientation_state`: map exactly from portal status to `sent`, `queued`, `missing`, or `draft`.
- `next_owner`: `registration_desk` for missing chart/demographics, `clinical_intake` for history/problems/vitals/care plan, `patient_communications` for orientation-only work, and `ready` when complete.
- `problem_list_complete` follows the portal `Problems Complete` field.
- `bmi_class`: use BMI only if height/weight or BMI is visible. Otherwise `not_available`.

## Chronic-Care Enrollment

Open `/programs/<id>` and linked patient/chart details.

- Required checks:
  - Program diagnosis support must match the proposed pathway.
  - Diabetes/hypertension programs need recent HbA1c or BP evidence.
  - Consent must be signed. `not obtained` and `declined` are not signed.
  - Program form must be complete.
- `missing_items`: add `diagnosis_support`, `recent_hba1c_or_bp`, `consent_signed`, and/or `program_form_complete` for every missing requirement.
- `consent_outcome`: `signed`, `not_obtained`, or `declined` from the program page.
- Decision precedence:
  - missing diagnosis support or clinically inconsistent pathway: `clinical_review`
  - missing/declined/not-obtained consent: `hold_missing_consent`
  - incomplete/not-started form with otherwise supported pathway: `hold_missing_form`
  - supported pathway with renal risk or uncontrolled values needing nurse involvement: `enroll_with_nurse_escalation`
  - all requirements met without escalation: `enroll`
- Cadence: weekly nurse call for renal risk with uncontrolled HbA1c/BP, poor adherence, or escalation; biweekly for renal/moderate-risk monitoring; monthly for stable, lower-risk enrollment.
- Put patients needing consent/form follow-up, clinical review, or nurse escalation in `coordinator_queue`; keep the queue sorted by patient ID. `escalation_count` counts `enroll_with_nurse_escalation` rows.
