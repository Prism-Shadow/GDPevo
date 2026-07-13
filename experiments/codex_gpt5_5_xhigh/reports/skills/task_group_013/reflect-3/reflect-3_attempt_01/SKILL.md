---
name: tg013-reflect-3-attempt-01
description: Transferable SOP for Northstar Care Intake Portal healthcare intake tasks.
---

# Northstar Care Intake SOP

## Portal Workflow

Sign in with the credentials from the task prompt, then use the header routes and direct record URLs:

- Patients: `/patients/<patient_id>`
- Benefits: `/benefits/<patient_id>`
- Transfers: `/transfers/<transfer_id>`
- Referrals: `/referrals/<referral_id>`
- Charts: `/charts/<patient_id>`
- Programs: `/programs/<patient_id>`
- Queue checks: `/queue?q=<record_id>`
- Policy/context: `/policies` and `/documents`

Record detail pages are definition-list style. Prefer the detail page over list summaries, and use portal-verified fields over stale card images or outside assumptions. Return only the requested JSON shape, exact enum strings, no extra keys, and rows sorted by the requested ID. Sort set-like arrays as instructed; when the prompt gives an item list, use that list order for item arrays.

## Registration Readiness

Use `/patients/<id>` for demographics, medication-managed status, and clinical/lifestyle risk. Use `/benefits/<id>` for medical coverage, PBM, and pharmacy network.

Gate rules:

- `medical_insurance`: pass only when coverage is `active` and medical network is `in network`. Inactive, terminated, pending, or missing coverage gives `insurance_inactive`; out-of-network or network-exception statuses give `insurance_out_of_network`.
- `pbm`: required only for medication-managed intake. Active PBM passes; inactive, pending, missing, or not located blocks with `pbm_inactive`. If not medication-managed, use `not_required`.
- `pharmacy`: required only for medication-managed intake. In-network passes; out-of-network blocks with `pharmacy_out_of_network`. If not medication-managed, use `not_required`.
- `demographics`: core address, consent, identity, and phone must be complete. Treat clear no/blank values as `demographics_incomplete`; do not let an emergency-contact-only issue override otherwise complete core demographics unless the task explicitly says it is required.
- `risk`: classify from clinical conditions and lifestyle indicators. Current smoking, daily alcohol, poor/unknown exercise, declined/unknown vaccination, renal/diabetes/heart-failure comorbidity, and complex medication history increase risk. High risk adds `clinical_review_required`.

Decision rules:

- Any administrative blocked reason normally makes `overall_decision` `blocked`.
- If administrative gates pass but high clinical risk is present, use `manual_review`.
- Use `ready` only when all required gates pass and clinical risk is low or moderate.
- `pharmacy_network_status` mirrors the benefit pharmacy network when pharmacy is required; otherwise `not_required`.

## Dialysis Transfers

Use `/transfers/<id>` first; it usually contains patient ID, requested start date, chair state, chart-prep state, and all packet item statuses/dates.

Packet rules:

- Missing, draft, expired, or otherwise non-final/non-usable items go in `missing_packet_items`.
- Labs are current within 30 days of requested start. Infection screens are current within 14 days of requested start.
- Put labs or infection screens in `stale_items` only when the item is otherwise usable (`received`/`final`) but outside the freshness window. If the status is missing/draft/expired, put it in `missing_packet_items`, not `stale_items`.
- Authorization/confidentiality booleans are true only when the corresponding item is final/received and usable.

Decision and routing:

- `start_compatibility`: chair held or chair available/not held -> `compatible`; capacity review -> `capacity_review`; waitlist -> `waitlist`.
- `decision`: missing packet items -> `hold_missing_packet`; otherwise capacity review/waitlist -> `hold_capacity`; otherwise `accept`.
- `route_owner`: missing packet -> `referring_facility`; capacity-only issue -> `capacity_coordinator`; packet/capacity okay but chart prep incomplete -> `chart_prep`; fully ready -> `intake_complete`.

## Orthopedics Referrals

Use `/referrals/<id>` and open any `Linked Referral Ids`.

Coding and issue rules:

- `chapter_valid` is true for M-code musculoskeletal diagnoses and supported musculoskeletal injury/spine codes; false for non-orthopedic chapters such as endocrine codes.
- `narrative_match` requires the diagnosis narrative/service context to fit the orthopedic code. Non-orthopedic narratives in an orthopedic scheduling review should trigger `diagnosis_mismatch`.
- `laterality_match` requires code, narrative, and laterality to agree. Spine or true n/a cases can match.
- Missing records -> `missing_records`; missing imaging -> `missing_imaging`.
- Authorization statuses `missing` or `pending` create `authorization_gap`; `approved` and `not required` are usable.
- Visible linked referrals or strong duplicate hints should drive `duplicate_referral`/`duplicate_review`; include linked IDs exactly as displayed.

Readiness precedence:

1. `duplicate_review`
2. `coding_clarification`
3. `pending_records`
4. `authorization_followup`
5. `ready_to_schedule`

Use `priority_tier` from urgency: ready records -> `schedule`; stat review -> `tier_1`; urgent -> `tier_2`; routine -> `tier_3`. Set `follow_up_practice` to the practice name for non-ready records and `null` for ready records. Top-level follow-up practices are unique and sorted.

## Chart Onboarding

Use `/charts/<patient_id>` for chart sections and `/patients/<patient_id>` only for related demographics/clinical context. Do not infer BMI from blood pressure; if no height/weight/BMI appears, use `not_available`.

Readiness requires:

- Chart created
- Demographics complete
- History complete
- Applicable active problems/problem list complete
- Current vitals
- Care plan or clinical instructions complete
- Orientation communication accounted for

Map missing sections directly: chart not created -> `chart_not_created`; demographics/history/problems/vitals false -> their matching enum. Draft/missing care plans or pending nurse-edit instructions usually mean `care_plan_or_instructions`. Preserve `orientation_state` exactly as `sent`, `queued`, `draft`, or `missing`; do not collapse `queued` into `missing`, but do not count a chart ready unless the prompt's readiness rule is satisfied.

Owner precedence:

- Registration/setup gaps (`chart_not_created`, demographics, history) -> `registration_desk`
- Clinical content gaps (problems, vitals, care plan/instructions) -> `clinical_intake`
- Only orientation communication remaining -> `patient_communications`
- No gaps -> `ready`

BMI classes, when BMI is available: normal `<25`, overweight `25` to `<30`, obese `>=30`.

## Chronic-Care Programs

Use `/programs/<patient_id>` for proposed program, active diagnoses, HbA1c/BP, renal flag, consent, form status, cadence clues, coordinator, and telehealth preference. Use `/charts/<patient_id>` and `/patients/<patient_id>` to verify supporting diagnoses or missing chart context when the program page is incomplete. Check `/queue?q=<patient_id>` for visible coordinator queue membership.

Missing item rules:

- `diagnosis_support`: proposed diabetes/hypertension/renal pathway lacks an active supporting diagnosis or renal-risk flag.
- `recent_hba1c_or_bp`: no recent usable HbA1c for diabetes-oriented programs or no recent usable BP for hypertension/renal monitoring.
- `consent_signed`: consent is not signed, including not obtained, declined, or verbal pending signature.
- `program_form_complete`: form is not complete (`not started`, `incomplete`, `draft`, blank).

Decision precedence:

1. Missing/declined consent -> `hold_missing_consent`
2. Missing diagnosis support or recent metric -> `clinical_review`
3. Missing/incomplete form only -> `hold_missing_form`
4. Enrollable renal-risk or uncontrolled metric needing nurse involvement -> `enroll_with_nurse_escalation`
5. Otherwise -> `enroll`

Cadence:

- `weekly_nurse_call`: renal flag with uncontrolled HbA1c/BP, poor adherence, or nurse escalation; also very high non-renal HbA1c/BP.
- `biweekly_checkin`: renal risk or moderately abnormal metrics without weekly-level concern.
- `monthly_checkin`: stable metrics and no escalation signal.

Map consent outcome to `signed`, `not_obtained`, or `declined`. `coordinator_queue` should include visible open program queue IDs and other records requiring coordinator action from holds, clinical review, or nurse escalation. `escalation_count` counts records with `enroll_with_nurse_escalation`.

## Common Pitfalls

- Do not treat card-image status as overriding portal-verified eligibility.
- Do not put expired/draft dialysis labs or infection screens in `stale_items`; they are missing packet items.
- Do not ignore duplicate referral links just because coding or authorization is also problematic.
- Do not infer unavailable BMI.
- Keep display strings such as practice names, coordinator names, proposed programs, and telehealth preferences exactly as shown.
