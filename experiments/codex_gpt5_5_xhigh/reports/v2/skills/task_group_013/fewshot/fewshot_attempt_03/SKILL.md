---
name: tg013-fewshot-attempt-03
description: Transferable SOP for Northstar Care Intake Portal healthcare intake tasks.
---

# Northstar Care Intake SOP

Use this skill for Northstar Care Intake Portal tasks that ask for JSON audits of patients, transfers, referrals, charts, benefits, or chronic-care programs.

## Portal Workflow

- Read the prompt and `input/payloads/answer_template.json` first. The template is the output contract.
- Use the prompt's portal URL and credentials. If the prompt uses `<TASK_ENV_BASE_URL>`, substitute the URL from the environment access note.
- Sign in at `/login`. The post-login redirect can be unreliable; use the top navigation or direct routes after the session cookie is set.
- Useful direct routes are `/patients/{patient_id}`, `/benefits/{patient_id}`, `/transfers/{transfer_id}`, `/referrals/{referral_id}`, `/charts/{patient_id}`, `/programs/{patient_id}`, `/documents`, and `/policies`.
- The search pages are helpful for finding links, but direct detail routes are usually faster. Detail pages expose fields as label/value rows; badge color is secondary to the text value.
- For patient-centered work, start at the patient detail page and follow related links or registration link fields to benefits, chart, PBM, pharmacy, or program pages.
- Read `/policies` when a task mentions policy/context. The policy summaries are authoritative for freshness windows and gating requirements.

## JSON Discipline

- Return JSON only. Do not include narrative evidence, comments, markdown fences, or extra keys.
- Preserve the template's top-level keys, nested shape, and scalar types. Use only enum strings shown in the prompt/template.
- Sort row arrays by their primary ID ascending, such as `patient_id`, `transfer_id`, or `referral_id`.
- Treat issue/reason/item arrays as sets: deduplicate and sort lexicographically by the exact output strings.
- Sort aggregate ID arrays and unique string arrays ascending. Counts must be derived from the final rows.
- Use `[]` for no issues. Use `null` only where the template explicitly allows it, such as a missing follow-up practice.

## Registration Readiness

Inspect the patient page plus benefits/PBM/pharmacy data.

- `medical_insurance`: pass only when `Coverage Status` is active and `Network Status` is in network. Inactive or terminated coverage maps to `insurance_inactive`; out-of-network coverage maps to `insurance_out_of_network`. A missing or stale card image never overrides portal-verified eligibility.
- `pbm`: for medication-managed intake, pass only when PBM status is active. Missing, not located, inactive, or expired PBM status maps to `pbm_inactive`. Use `not_required` only when the patient/service does not require medication management/PBM.
- `pharmacy`: for medication-managed intake, pass only when the preferred pharmacy network status is in network. Out-of-network maps to `pharmacy_out_of_network`; use `not_required` only when pharmacy validation is not required.
- `pharmacy_network_status`: copy the benefits pharmacy network result as `in_network`, `out_of_network`, or `not_required`.
- `demographics`: pass only when address, consent, emergency contact, identity verification, and phone verification are all complete/yes. Any missing demographic item maps to `demographics_incomplete`.
- `risk`: low for clean clinical/lifestyle profile, moderate for some risk flags, high for multiple significant flags such as current/unknown smoking, daily alcohol, very low/unknown exercise, declined/due vaccination, serious chronic conditions, polypharmacy, or special handling. High risk adds `clinical_review_required`.
- `overall_decision`: `blocked` if any administrative gate reason exists; `manual_review` if the only blocker is clinical review; `ready` only with no blocked reasons.
- `highest_risk_patient_id`: choose the patient with highest risk severity. If tied, prefer the record with stronger risk indicators, then the lowest ID if still tied.

## Dialysis Transfer Readiness

Inspect each transfer detail, linked patient context if needed, and policy `POL-REN-02`.

- Required packet items, using these exact output names: `labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, `transport note`.
- Put an item in `missing_packet_items` when its portal status is missing, draft, expired, not final where final is required, or otherwise unusable. Dialysis prescription must be final. Authorization and confidentiality must be valid/final or otherwise usable.
- Labs are fresh only within 30 days before the requested start date. Infection screen is fresh only within 14 days before the requested start date.
- Put usable but out-of-window labs/infection screen in `stale_items`. If labs or infection screen status is missing/draft/expired, list it in `missing_packet_items` instead of `stale_items`.
- `authorization_valid` is false when authorization is missing, draft, expired, or not usable. `confidentiality_valid` follows the same rule for the confidentiality statement.
- `start_compatibility`: `compatible` for chair held or chair available/not held; `capacity_review` for capacity review; `waitlist` for waitlist.
- Decision precedence: any missing or stale packet item means `hold_missing_packet`; otherwise capacity review or waitlist means `hold_capacity`; otherwise `accept`.
- `route_owner`: `referring_facility` for missing/stale packet work; `capacity_coordinator` for capacity-only holds; `chart_prep` when accepted but chart prep is not complete; `intake_complete` when accepted and chart prep is complete.
- `authorization_problem_transfers` and `confidentiality_problem_transfers` contain sorted transfer IDs where the corresponding boolean is false.

## Orthopedic Referral Readiness

Inspect referral detail fields and policy `POL-REF-03`.

- `coding.chapter_valid`: true for supported orthopedic/musculoskeletal service/code combinations, commonly M-code musculoskeletal diagnoses. Non-orthopedic service families or unrelated diagnosis chapters are invalid.
- `coding.narrative_match`: true when diagnosis narrative matches the code/service. Add `diagnosis_mismatch` when the narrative describes a different condition or service family.
- `coding.laterality_match`: true when laterality is consistent with the narrative/code; `n/a` is acceptable when laterality is not clinically applicable. Add `laterality_mismatch` only for a real inconsistency.
- Issue code mapping: invalid chapter -> `invalid_chapter`; missing records -> `missing_records`; missing imaging -> `missing_imaging`; missing or pending required authorization -> `authorization_gap`; linked duplicate referral or strong duplicate link -> `duplicate_referral`.
- `readiness_status` precedence: `duplicate_review`, then `coding_clarification`, then `pending_records`, then `authorization_followup`, then `ready_to_schedule`.
- `priority_tier`: use `schedule` only for ready referrals. Use the visible urgency/context to choose tiers; stat/same-day or urgent records with records/imaging gaps or duplicate review are usually `tier_1`, routine authorization-only follow-up is usually `tier_2`, and lower-priority authorization follow-up with possible duplicate context is usually `tier_3`.
- `follow_up_practice` is the referral `Practice` when any follow-up is needed; otherwise `null`. Aggregate `follow_up_practices` as unique sorted practice names.

## Chart Onboarding Readiness

Inspect the chart page and any linked patient details requested.

- A chart can exist without being ready. `chart_ready` is true only when chart creation, demographics, history, problems, current vitals, care plan or clinical instructions, and orientation communication are complete.
- `missing_sections`: add `chart_not_created` if no chart exists; add `demographics`, `history`, `problems`, or `vitals` when those fields are incomplete or not current; add `orientation_message` unless orientation is sent; add `care_plan_or_instructions` only when both care plan and applicable clinical instructions are absent/unusable. `not needed` can satisfy clinical instructions.
- `problem_list_complete` mirrors the portal's `Problems Complete` field.
- `orientation_state` is the visible state normalized to `sent`, `queued`, `missing`, or `draft`.
- `bmi_class`: use `not_available` when height/weight/BMI is absent. Otherwise normal is 18.5-24.9, overweight is 25.0-29.9, obese is 30.0 or higher.
- `next_owner` precedence: `registration_desk` for missing chart/demographics; `clinical_intake` for history/problems/vitals/care-plan clinical gaps; `patient_communications` when only orientation remains; `ready` when no sections are missing.

## Chronic-Care Program Enrollment

Inspect each program detail and related patient/chart context if the prompt asks.

- `proposed_program`, `coordinator`, and `telehealth_preference` come directly from the program detail page.
- `missing_items`: add `diagnosis_support` when active diagnoses do not support the proposed program; add `recent_hba1c_or_bp` when the program lacks required recent lab/vital support; add `consent_signed` when consent is not signed, including declined/not obtained; add `program_form_complete` when the form is not complete.
- `consent_outcome`: signed -> `signed`, not obtained/missing -> `not_obtained`, declined -> `declined`.
- Enrollment decision precedence: consent not signed -> `hold_missing_consent`; diagnosis support or clinical mismatch -> `clinical_review`; only form incomplete -> `hold_missing_form`; all requirements met but renal flag/high-risk nurse involvement is needed -> `enroll_with_nurse_escalation`; otherwise `enroll`.
- `follow_up_cadence`: use `weekly_nurse_call` for renal flag, nurse escalation, clinical review, poor/unknown adherence, or high-risk labs/vitals; `biweekly_checkin` for moderate cardiometabolic follow-up without renal escalation; `monthly_checkin` for stable low-risk enrollment.
- `coordinator_queue` contains sorted patient IDs needing coordinator action: holds, clinical review, missing consent/form follow-up, or nurse escalation. Plain `enroll` with no follow-up is usually excluded.
- `escalation_count` counts rows whose decision is exactly `enroll_with_nurse_escalation`.

## Common Pitfalls

- Do not infer from badge color alone; use the text value.
- Do not include stale labs/infection screen in both `missing_packet_items` and `stale_items`.
- Do not let capacity problems hide packet problems; packet holds take precedence.
- Do not mark a chart ready just because it was created.
- Do not treat declined consent as signed; it is both `declined` and missing consent.
- Do not leave placeholder enum strings from the template in the final answer.
