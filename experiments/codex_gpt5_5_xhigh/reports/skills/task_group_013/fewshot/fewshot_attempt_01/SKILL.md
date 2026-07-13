---
name: tg013-fewshot-attempt-01
description: Transferable SOP for Northstar Care Intake Portal healthcare intake tasks.
---

# Northstar Care Intake Portal SOP

Use this skill for Northstar Care Intake Portal audits involving registration, dialysis transfers, referrals, chart onboarding, or chronic-care program enrollment.

## Operating Procedure

1. Open the task's `<TASK_ENV_BASE_URL>` and sign in with the credentials in the prompt.
2. Read the prompt and `input/payloads/answer_template.json` first. The template controls exact keys, enum spellings, booleans, counts, and whether a review date is required.
3. Use the portal tabs and exact-ID search:
   - `Patients` for patient demographics, clinical/lifestyle indicators, and links to Benefits/Chart/Program.
   - `Benefits` for medical coverage, network status, PBM status, and preferred pharmacy network status.
   - `Transfers` for dialysis transfer packet documents, chair availability, requested start date, and chart prep.
   - `Referrals` for referral coding, records/imaging, authorization, duplicate links, urgency, and practice contact.
   - `Charts` for chart onboarding completeness, vitals, care plan/instructions, problems, and orientation.
   - `Programs` for chronic-care enrollment fields.
   - `Queue` only when the task asks for queue state or the template needs queue membership.
   - `Policies` for current high-level rules; apply them over assumptions from list badges.
4. Open the detail page for every requested ID. List rows are useful for triage but not enough for final decisions.
5. Preserve the template shape exactly. Do not add evidence notes or extra keys. Sort record arrays by the requested ID ascending. Sort all set-like arrays, including issue codes, missing items, linked IDs, follow-up practices, queue IDs, and problem ID lists.

## General Output Conventions

- Use only enum strings shown in the prompt/template.
- Keep booleans as JSON booleans, not strings.
- `ready_count`, `accepted_count`, or similar totals count only records with the final ready/accepted/enroll outcome named by the template.
- If a field is copied from the portal, preserve its text exactly unless the template requires an enum mapping.
- For review dates, use the prompt's "as of" date or the template value. Do not substitute the current date.

## Registration Readiness

Review the patient detail page and the Benefits detail page.

Gate rules:

- `medical_insurance` passes only when `Coverage Status` is active on the review date and `Network Status` is in network.
- Block medical insurance for inactive/terminated coverage with `insurance_inactive`; block out-of-network medical coverage with `insurance_out_of_network`.
- `pbm` is required for medication-managed intake. It passes only when `Pbm Status` is active. Missing, not located, inactive, or expired PBM blocks with `pbm_inactive`. If medication management/PBM is not required, use `not_required`.
- `pharmacy` is required when medication/PBM handling is required. Use `Pharmacy Network Status` from Benefits. In network passes; out of network blocks with `pharmacy_out_of_network`; not required uses `not_required`.
- `pharmacy_network_status` mirrors the Benefits pharmacy network result as `in_network`, `out_of_network`, or `not_required`.
- `demographics` passes only when required demographic fields are complete: address, consent, emergency contact, identity verification, and phone verification. Any missing/no item blocks with `demographics_incomplete`.
- `risk` is clinical/lifestyle risk, separate from administrative gates:
  - `high`: multiple significant risk indicators such as daily alcohol, current smoking, unknown/low exercise with chronic disease, polypharmacy, no listed meds for a medication-managed intake, declined vaccination, or other serious combined concerns.
  - `moderate`: chronic condition or one to two lifestyle risks without a high-risk cluster.
  - `low`: no meaningful clinical/lifestyle concerns.
- Add `clinical_review_required` when risk is high.

Decision precedence:

- `blocked` if any hard administrative gate blocks: medical insurance, PBM, pharmacy, or demographics.
- `manual_review` if administrative gates pass but high clinical risk requires review.
- `ready` only when all required gates pass and risk is not high.
- `manual_review_patient_ids` contains only manual-review decisions.
- `highest_risk_patient_id` is the patient with the highest risk severity; if labels tie, use the patient with more/high-impact risk indicators, then a deterministic ID sort.

## Dialysis Transfer Readiness

Review each Transfer detail page. Required packet items are: labs, infection screen, dialysis prescription, medication list, allergy list, authorization, confidentiality statement, referring contact, and transport note.

Packet rules:

- Put an item in `missing_packet_items` when its status is missing, draft, expired, not final/usable, or otherwise not acceptable.
- Dialysis prescription must be final.
- Authorization and confidentiality statement must be valid/final/usable. Set `authorization_valid` and `confidentiality_valid` from those statuses.
- Labs are current only within 30 days of the requested start date.
- Infection screen is current only within 14 days of the requested start date.
- Put labs or infection screen in `stale_items` only when the item is otherwise usable/received/final but outside its freshness window. If status is missing/draft/expired, put it in `missing_packet_items` instead, not `stale_items`.

Capacity and owner:

- Map chair availability to `start_compatibility`: clearly available or "chair available, not held" is `compatible`; "capacity review" is `capacity_review`; waitlist/no chair is `waitlist`.
- `decision` is `hold_missing_packet` when any required packet item is missing or stale. Use `hold_capacity` when the packet is acceptable but capacity is not compatible. Use `accept` only when packet, freshness, capacity, and chart prep are acceptable.
- `route_owner` precedence:
  - packet/freshness/authorization/confidentiality problems: `referring_facility`
  - no packet problem but capacity review/waitlist: `capacity_coordinator`
  - packet and capacity acceptable but chart prep unfinished: `chart_prep`
  - all complete: `intake_complete`
- `authorization_problem_transfers` and `confidentiality_problem_transfers` contain IDs where the corresponding validity boolean is false.

## Orthopedics Referral Scheduling

Review Referral details and Policies. Do not treat duplicate hints alone as a duplicate unless linked referral IDs or equivalent explicit duplicate links are present.

Issue codes:

- `invalid_chapter`: ICD/service family is not an M-code or supported musculoskeletal referral for orthopedics.
- `diagnosis_mismatch`: diagnosis narrative does not match the coded condition/service family.
- `laterality_mismatch`: code, narrative, and laterality disagree.
- `missing_records`: clinical records are not received.
- `missing_imaging`: required imaging is not received.
- `authorization_gap`: authorization is missing, pending, expired, or otherwise not approved when payer authorization is required.
- `duplicate_referral`: linked referral IDs or explicit duplicate record links require review.

Status precedence:

- `ready_to_schedule`: no issue codes.
- `duplicate_review`: any `duplicate_referral`.
- `coding_clarification`: coding/laterality issues without duplicate precedence.
- `pending_records`: missing records or imaging without higher duplicate/coding precedence.
- `authorization_followup`: only authorization-related follow-up remains.

Other fields:

- `coding.chapter_valid`, `coding.narrative_match`, and `coding.laterality_match` are direct boolean inverses of the corresponding coding issues.
- `duplicate_linked_referral_ids` is the sorted list of explicit linked referrals.
- `follow_up_practice` is the referring practice name for any non-ready referral; use `null` for ready records if the template expects it.
- `follow_up_practices` is the sorted unique set of non-null follow-up practices.
- Priority tiers are driven by urgency plus the work needed: `schedule` for ready, `tier_1` for stat/urgent clinical record or imaging blockers, `tier_2` for routine follow-up, and `tier_3` for lower operational-only follow-up such as authorization-only urgent records when no clinical packet blocker exists.

## Chart Onboarding Readiness

Review Chart details. A chart can exist without being ready.

Missing sections:

- `chart_not_created`: chart created is no.
- `demographics`: demographics complete is no.
- `history`: history complete is no.
- `problems`: problems complete is no.
- `vitals`: vitals are absent or `Vitals.Current` is no.
- `care_plan_or_instructions`: neither an onboarding care plan nor applicable clinical instructions are usable/present. Do not flag when the portal indicates instructions are not needed.
- `orientation_message`: orientation is missing, draft, or queued; `sent` is complete.

Derived fields:

- `chart_ready` is true only when `missing_sections` is empty.
- `problem_list_complete` mirrors `Problems Complete`.
- `orientation_state` maps portal orientation to `sent`, `queued`, `missing`, or `draft`.
- `bmi_class`: use portal BMI if present; otherwise compute from height/weight if available. `normal` is BMI < 25, `overweight` is 25 to < 30, `obese` is >= 30, and `not_available` when BMI cannot be determined.
- `next_owner` precedence:
  - missing chart or registration demographics: `registration_desk`
  - missing clinical chart content, problems, vitals, care plan/instructions: `clinical_intake`
  - only orientation communication is incomplete: `patient_communications`
  - no missing sections: `ready`

## Chronic-Care Program Enrollment

Review Program details, related chart/patient details if needed, and any queue rows if the template asks for coordinator queue membership.

Required readiness:

- Diabetes, hypertension, and cardiometabolic pathways require active supporting diagnosis, recent HbA1c or BP as applicable, signed consent, and a complete program form.
- Renal risk monitoring requires renal support/flag and may change cadence or require nurse escalation.
- `missing_items`:
  - `diagnosis_support`: active diagnoses do not support the proposed program.
  - `recent_hba1c_or_bp`: required recent lab/vital evidence is absent.
  - `consent_signed`: consent is not signed; declined consent is still missing signed consent.
  - `program_form_complete`: program form is not complete.
- `consent_outcome` maps portal consent to `signed`, `not_obtained`, or `declined`.
- Copy `proposed_program`, `coordinator`, and `telehealth_preference` from the portal.

Decision precedence:

- `hold_missing_consent` when consent is not signed, even if other items are also missing.
- `clinical_review` when diagnosis support or recent lab/vital support is missing, unless consent hold has precedence.
- `hold_missing_form` when the form is the remaining blocker.
- `enroll_with_nurse_escalation` when enrollment can proceed but renal flag, poor adherence, severe vitals/labs, or similar clinical risk requires nurse involvement.
- `enroll` when all requirements pass and no nurse escalation is indicated.

Cadence and queues:

- `weekly_nurse_call` for renal flag, nurse escalation, poor adherence, clinical review, or severe uncontrolled vitals/labs.
- `biweekly_checkin` for elevated cardiometabolic risk without renal/nurse escalation.
- `monthly_checkin` for stable lower-risk enrollment.
- `coordinator_queue` should include sorted patient IDs needing coordinator action: holds, clinical review, and nurse escalation. Clean enrollments normally stay out of the queue unless the portal/task explicitly lists them.
- `escalation_count` counts records with `enroll_with_nurse_escalation`.
