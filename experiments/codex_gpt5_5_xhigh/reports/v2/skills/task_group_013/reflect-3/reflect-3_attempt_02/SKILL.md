---
name: tg013-reflect-3-attempt-02
description: Transferable SOP for Northstar Care Intake Portal healthcare intake tasks.
---

# Northstar Care Intake Portal SOP

Use this skill for Northstar Care Intake Portal tasks that ask for structured readiness, transfer, referral, chart, or chronic-care enrollment JSON.

## Portal Workflow

1. Read the task prompt and `input/payloads/answer_template.json` first. The template is the output contract: keep the exact keys, enum strings, booleans, nulls, and date fields it requires.
2. Open the portal URL from the prompt/environment note and sign in with the prompt credentials.
3. Use the top navigation and search boxes to find each requested ID. Detail pages carry the decisive fields; list pages are only an index.
4. Open related pages linked from the detail page, especially `Patients`, `Benefits`, `Charts`, `Programs`, linked referrals, queue items, and `Policies`.
5. Use the policy page as the tiebreaker. Do not infer from badge colors alone; read the text value.
6. Return only JSON. Sort primary rows by the requested ID ascending. Sort ID arrays ascending. Sort set arrays alphabetically unless the prompt gives a different explicit order. Recompute summary counts from the row decisions.

## Registration Readiness

Use patient, benefits, and when relevant chart/program pages.

- `medical_insurance`: pass only when coverage is active on the review date and the medical network is in network. Inactive or terminated coverage adds `insurance_inactive`; out of network adds `insurance_out_of_network`. A stale/missing card image never overrides portal-verified eligibility.
- `pbm`: pass when PBM/prescription benefit is active. `not located`, inactive, missing, or expired PBM adds `pbm_inactive`. Use `not_required` only when the record/policy clearly says PBM is not needed.
- `pharmacy`: pass when the preferred pharmacy is in network. Out-of-network preferred pharmacy adds `pharmacy_out_of_network`. Use `not_required` only when pharmacy/PBM checks are explicitly unnecessary.
- `demographics`: pass only when address, consent, emergency contact, identity, and phone verification are complete; any `no` or missing required item adds `demographics_incomplete`.
- `risk`: assign `high` for multiple serious clinical/lifestyle flags such as current smoking with declined/unknown vaccination, daily alcohol, severe/uncontrolled vitals, polypharmacy, or renal/diabetes complexity. Use `moderate` for one or two meaningful flags, and `low` for stable records with no material flags.
- Final decision: any administrative block gives `blocked`; no admin block plus high risk gives `manual_review` with `clinical_review_required`; all gates pass with low/moderate risk gives `ready`. If a record is already blocked, include only reasons the task asks to report, but do not let clinical risk override hard admin blocks.

## Dialysis Transfers

Use transfer detail plus linked patient/chart details when asked.

- Required packet items: labs, infection screen, dialysis prescription, medication list, allergy list, authorization, confidentiality statement, referring contact, and transport note.
- Put missing, draft, expired, non-final, or otherwise unusable packet items in `missing_packet_items`.
- Put labs or infection screens in `stale_items` only when the item is otherwise usable but outside the freshness window for the requested start date: labs within 30 days, infection screen within 14 days. Expired/draft/missing labs or infection screens are missing, not stale.
- `authorization_valid` and `confidentiality_valid` are true only for usable final/received items, not draft/missing/expired.
- `start_compatibility`: `chair held` and `chair available, not held` both map to `compatible`; `capacity review` maps to `capacity_review`; `waitlist` maps to `waitlist`.
- Decision precedence: missing packet -> `hold_missing_packet`; otherwise waitlist/capacity issue -> `hold_capacity`; otherwise `accept`.
- `route_owner`: missing packet -> `referring_facility`; capacity issue -> `capacity_coordinator`; complete packet but chart prep unfinished -> `chart_prep`; complete and ready -> `intake_complete`.

## Orthopedics Referrals

Use referral details, policy, and any linked referral IDs.

- Coding requires an orthopedic/supported musculoskeletal code, usually an `M...` ICD-10 code, and a narrative that matches the code. Non-musculoskeletal chapters such as diabetes/endocrine codes are `invalid_chapter`.
- Laterality must agree across code, narrative, and laterality field. Examples: right knee code/narrative/right field match; left knee must be left; spine/n-a can match when appropriate.
- Scheduling requires valid coding, laterality consistency, records received, imaging received, authorization approved or explicitly not required, and duplicate clearance.
- Add issue codes for every unresolved problem: `invalid_chapter`, `diagnosis_mismatch`, `laterality_mismatch`, `missing_records`, `missing_imaging`, `authorization_gap`, `duplicate_referral`.
- Treat missing or pending authorization as `authorization_gap` unless the record explicitly says authorization is not required.
- Treat concrete linked referral IDs or strong same-patient/same-condition duplicate context as duplicate review. A weak note such as "same physician only" by itself is not enough.
- Choose one `readiness_status` by the main unresolved blocker: `coding_clarification` for coding/laterality issues, `duplicate_review` for duplicates, `pending_records` for records/imaging gaps, `authorization_followup` for auth-only gaps, otherwise `ready_to_schedule`.
- `priority_tier`: ready records use `schedule`; `stat review` -> `tier_1`; `urgent` -> `tier_2`; routine -> `tier_3`.
- `follow_up_practice` is the referring practice for non-ready records and `null` for ready records. `follow_up_practices` is the unique sorted list of non-ready practices.

## Chart Onboarding

Use chart detail first, then patient detail if demographics or clinical context is unclear.

- A chart is ready only when chart creation, demographics, history, active problems, current vitals, care plan or clinical instructions, and orientation communication are complete.
- `missing_sections`:
  - `chart_not_created` when no chart exists.
  - `demographics`, `history`, `problems`, or `vitals` for incomplete/no/not-current values.
  - `care_plan_or_instructions` when the care plan/instruction requirement is missing, draft, pending, or otherwise not usable. A documented care plan or sent/not-needed clinical instructions can satisfy this section if the record clearly presents one as sufficient.
  - `orientation_message` when orientation is missing, not sent, or draft. Queued orientation is a real state, but it is not complete.
- `orientation_state`: map visible values to `sent`, `queued`, `missing` (`not sent` counts as missing), or `draft`.
- `bmi_class`: compute only when height/weight or BMI is visible. Otherwise use `not_available`. Normal is BMI <25, overweight is 25-29.9, obese is >=30.
- `next_owner`: registration gaps or no chart -> `registration_desk`; clinical sections/vitals/care plan/problems -> `clinical_intake`; only orientation remaining -> `patient_communications`; no missing sections -> `ready`.

## Chronic-Care Programs

Use program detail plus patient/chart details for diagnosis support and recent evidence.

- Requirements for diabetes/hypertension pathways: active diagnosis support, recent HbA1c or BP/vitals as applicable, signed consent, and complete program form.
- `missing_items`:
  - `diagnosis_support` when the proposed program is not supported by active diagnoses/problem codes.
  - `recent_hba1c_or_bp` when the needed recent lab/vital evidence is absent.
  - `consent_signed` for not obtained, declined, verbal-pending-signature, missing, or any non-signed consent.
  - `program_form_complete` for not started, incomplete, draft, or missing forms.
- `consent_outcome`: signed -> `signed`; declined -> `declined`; all other non-signed consent states -> `not_obtained`.
- Decision precedence: missing consent -> `hold_missing_consent`; missing diagnosis support or recent evidence -> `clinical_review`; missing/incomplete form -> `hold_missing_form`; complete with renal flag, poor adherence, or markedly uncontrolled A1c/BP -> `enroll_with_nurse_escalation`; otherwise `enroll`.
- `follow_up_cadence`: use `weekly_nurse_call` for renal risk, nurse escalation, poor adherence, clinical review, or markedly uncontrolled values; `biweekly_checkin` for moderate risk/variable adherence; `monthly_checkin` for stable enrollments.
- `coordinator_queue` includes patients needing coordinator action: consent/form holds, clinical review, or nurse escalation. Keep it sorted by patient ID. `escalation_count` counts `enroll_with_nurse_escalation` decisions.

## Pitfalls

- Detail pages can contradict list-page summaries; trust detail pages.
- Status words matter: `draft`, `pending`, `not started`, `missing`, `expired`, `not located`, and `not sent` are not complete/usable.
- For transfers, future-dated but missing/draft documents are still missing. Do not mark them stale unless they are otherwise usable.
- For referrals, pending authorization is not approved.
- Use `not_required` only from an explicit portal value or policy signal, not from absence of a problem.
- Do not add narrative evidence or extra keys to the final JSON.
