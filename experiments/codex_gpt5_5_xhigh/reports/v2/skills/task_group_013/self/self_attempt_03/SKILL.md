---
name: tg013-self-attempt-03
description: Transferable SOP for Northstar Care Intake Portal healthcare intake tasks.
---

# Northstar Care Intake Portal SOP

## Access And Navigation

- Use the task prompt's portal URL, email, and password. After login, use the top navigation: Patients, Benefits, Pharmacies, Transfers, Referrals, Charts, Programs, Queue, Documents, and Policies.
- Search or open records by the exact ID from the prompt. Detail pages are usually stable at `/<module>/<ID>`, e.g. `/patients/NSP-1008`, `/benefits/NSP-1008`, `/transfers/TR-2604`.
- Prefer detail pages over list badges when deciding. List pages are good for finding records, but detail pages contain the fields and dates needed for controlled outputs.
- Policies are authoritative for thresholds: registration gates, dialysis freshness, orthopedic scheduling, chart readiness, and chronic program enrollment.
- Final answers must match the provided template exactly. Do not add evidence notes or extra keys. Use the enum strings exactly as shown in the template, not the pipe-separated placeholder text.
- Sort primary rows by the requested ID ascending. Sort all set-like arrays ascending, including IDs, issue codes, blocked reasons, missing items, packet items, and practice names.

## Registration Readiness

Use Patients, Benefits, Pharmacies, Charts, and visible policy context.

Field rules:
- `medical_insurance` passes only when Coverage Status is active and Network Status is in network. Inactive, terminated, pending COB, out of network, or network exception needed blocks. A card image never overrides portal-verified eligibility.
- `pbm` is required for Medication Managed = yes or medication-managed/specialty medication intake. It passes only when PBM Status is active. Use `not_required` only when medication management/PBM is not needed.
- `pharmacy` is required when PBM is required. It passes only when Pharmacy Network Status is in network and the preferred pharmacy is not mail-order-only unless mail order is acceptable for the service. Use `not_required` only when PBM/pharmacy is not needed.
- `demographics` passes only when identity, phone, address, consent, and emergency contact are complete/yes. Chart-level Demographics Complete = no is also a demographics defect when the task asks to review related registration details.
- `pharmacy_network_status` mirrors the required pharmacy gate: `in_network`, `out_of_network`, or `not_required`.

Risk and decision:
- `risk` is `high` when current clinical/lifestyle indicators need clinical review, such as very high BP, current smoking with other uncontrolled risks, daily alcohol use with risk comorbidities, renal/diabetes complexity, missing critical clinical instructions, or comparable red flags.
- `risk` is `moderate` for nonblocking but notable risks such as former/unknown smoking, low exercise, due/unknown vaccination, multiple chronic conditions, elevated BP below high-risk level, or medication/adherence concerns.
- `risk` is `low` when no meaningful clinical/lifestyle concerns are visible.
- Add `clinical_review_required` to `blocked_reasons` for high-risk clinical review; this normally makes `overall_decision` `manual_review` unless a true administrative block exists.
- Add insurance/PBM/pharmacy/demographic blocked reasons exactly for failed gates. If any administrative gate blocks, `overall_decision` is `blocked`. If no blocks but clinical review is required, use `manual_review`. If every gate passes and risk does not require review, use `ready`.
- `ready_count` counts only `overall_decision: ready`. `highest_risk_patient_id` is the patient with the highest risk level; break ties by patient ID ascending unless the prompt gives another rule. `manual_review_patient_ids` contains only manual-review IDs.

## Dialysis Transfer Readiness

Use Transfers, linked patient details if needed, and the dialysis policy.

Packet item rules:
- Required item names are exactly: `labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, `transport note`.
- Put items in `missing_packet_items` when their status is missing, draft, expired, pending, not started, incomplete, or otherwise not final/usable. Dialysis prescription must be final.
- Labs are fresh within 30 days before the requested start date. Infection screen is fresh within 14 days before the requested start date.
- Put `labs` or `infection screen` in `stale_items` only when the item is otherwise usable/received/final but outside its freshness window. If status is expired/draft/missing, treat it as missing, not stale.
- `authorization_valid` is true only when authorization is final/usable and not expired/missing/draft. `confidentiality_valid` follows the same rule for the confidentiality statement.

Capacity, decision, and owner:
- Map Requested Chair Availability: chair held -> `compatible`; capacity review or chair available but not held -> `capacity_review`; waitlist -> `waitlist`.
- Decision precedence is packet first, then capacity, then chart prep. Any missing or stale packet item gives `hold_missing_packet`. If packet is clean but start compatibility is capacity_review/waitlist, use `hold_capacity`. Use `accept` only when packet is clean, capacity is compatible, and chart prep is complete or otherwise intake-ready.
- Route owner precedence: packet/auth/confidentiality problems -> `referring_facility`; capacity-only problem -> `capacity_coordinator`; clean packet/capacity but chart prep not complete -> `chart_prep`; accepted transfer -> `intake_complete`.
- `accepted_count` counts `accept`. Authorization/confidentiality problem arrays contain transfer IDs where the corresponding boolean is false.

## Orthopedic Referral Scheduling

Use Referrals and the orthopedics policy. Open linked referral IDs only when the current record cites them as duplicate context.

Coding:
- `chapter_valid` is true for supported musculoskeletal/orthopedic ICD-10 codes, usually M-codes and supported injury codes such as S83.*. Non-orthopedic codes such as E11.9 fail with `invalid_chapter`.
- `narrative_match` is false when the diagnosis narrative does not match the ICD code/body area. Use `diagnosis_mismatch`.
- `laterality_match` is false when Laterality conflicts with the ICD/narrative, e.g. right code with left narrative. Use `laterality_mismatch`.

Readiness status precedence:
- `coding_clarification` for invalid chapter, diagnosis mismatch, or laterality mismatch.
- `duplicate_review` when linked referral IDs or duplicate hints indicate the same patient/demographics and same condition. Put confirmed duplicate IDs in `duplicate_linked_referral_ids`; do not treat a linked but unrelated record as a duplicate.
- `pending_records` when required records or imaging are missing. Add `missing_records` and/or `missing_imaging`.
- `authorization_followup` when coding/docs/duplicates are clean but authorization is missing, pending, expired, or otherwise not approved when required. Add `authorization_gap`.
- `ready_to_schedule` only when coding fits, laterality matches, no duplicate review is needed, records and imaging are present, and authorization is approved or not required.

Other fields:
- `priority_tier`: `schedule` for ready-to-schedule records; otherwise map stat review -> `tier_1`, urgent -> `tier_2`, routine -> `tier_3`.
- `follow_up_practice` is the referring practice name when follow-up is needed; use null when ready. `follow_up_practices` is the sorted unique list of non-null practice names.
- Include all true `issue_codes`, sorted, even if the primary `readiness_status` reflects only the highest-precedence issue.

## Chart Onboarding

Use Charts and linked Patients if demographics context is needed.

Readiness rules:
- `chart_ready` is true only when all required sections are complete: chart created, demographics, history, active/applicable problems, current vitals, care plan or clinical instructions, and orientation communication.
- Missing section names must use the template enums: `chart_not_created`, `demographics`, `history`, `problems`, `vitals`, `care_plan_or_instructions`, `orientation_message`.
- `chart_not_created` applies when Chart Created is no. Other missing sections still matter only if visible, but a nonexistent chart is never ready.
- `vitals` is missing when Vitals.Current is no or vitals are absent.
- `care_plan_or_instructions` is missing when the care plan is missing/draft and clinical instructions are missing, pending, or not usable. A documented care plan or sent/final usable instructions satisfy this section.
- `orientation_state` maps portal text: sent -> `sent`, queued -> `queued`, not sent/missing -> `missing`, draft -> `draft`. Only sent is complete for chart readiness.
- `problem_list_complete` mirrors Problems Complete.
- `next_owner`: registration/demographic/chart-creation gaps -> `registration_desk`; clinical sections, problems, vitals, or care plan/instructions -> `clinical_intake`; only orientation/communication missing -> `patient_communications`; fully ready -> `ready`.
- `bmi_class`: use portal BMI if shown. `not_available` when absent; `normal` for BMI under 25, `overweight` for 25.0-29.9, `obese` for 30.0 or greater.

## Chronic-Care Program Enrollment

Use Programs first, then related Patients and Charts for diagnosis support and chart context.

Required checks:
- `proposed_program`, `coordinator`, and `telehealth_preference` are copied from the program page.
- `consent_outcome`: signed -> `signed`; not obtained or verbal pending signature -> `not_obtained`; declined -> `declined`.
- `program_form_complete` is satisfied only by Program Form Status = complete. Incomplete/not started/draft adds `program_form_complete` to `missing_items`.
- `consent_signed` is missing unless consent is signed. A declined consent is not signed and should not be treated as merely ready.
- `diagnosis_support` is missing when the proposed program is not supported by active program diagnoses and corroborating patient/chart conditions or problem codes. Diabetes pathways need diabetes support; hypertension/cardiometabolic pathways need diabetes and/or hypertension support as applicable; renal risk monitoring needs renal flag or CKD/renal support.
- `recent_hba1c_or_bp` is missing when the pathway lacks the needed recent measure: diabetes needs HbA1c, hypertension/renal/cardiometabolic pathways need recent BP or the specified lab/vital. Use the review date in the prompt when assessing recency.

Decision and cadence:
- If consent is missing/not obtained, use `hold_missing_consent` unless a stronger clinical-review issue dominates.
- If the only blocker is an incomplete/missing program form, use `hold_missing_form`.
- Use `clinical_review` for declined consent, unsupported diagnosis, missing required clinical measures, conflicting chart/program evidence, or other clinical ambiguity.
- Use `enroll_with_nurse_escalation` when enrollment requirements are met but renal flag, renal-risk program, severe HbA1c/BP elevation, poor adherence, or similar risk requires nurse involvement.
- Use `enroll` when consent, diagnosis support, recent measures, and form are all complete and no escalation is needed.
- Cadence: weekly nurse call for renal flag/renal-risk, nurse escalation, poor adherence, or severe uncontrolled values; biweekly checkin for moderate uncontrolled diabetes/BP or variable adherence; monthly checkin for stable values without escalation.
- `coordinator_queue` should include sorted patient IDs needing coordinator action: missing consent/form, clinical review, or nurse escalation. Omit straightforward enrollments with no follow-up need. `escalation_count` counts only `enroll_with_nurse_escalation`.

## Common Pitfalls

- Do not use enum placeholders containing pipes from the template; choose one valid enum value.
- Do not include narrative evidence in final JSON.
- For transfers, stale lab/screen and unusable status are different: expired/draft/missing goes to `missing_packet_items`; usable but outside the date window goes to `stale_items`.
- For referrals, authorization gaps do not make a record schedulable, but coding, duplicate, and records/imaging issues usually take precedence for the singular readiness status.
- For charts, queued orientation is not sent; a chart can exist and still be unready.
- For chronic programs, the program page can propose a pathway that is not supported by patient/chart diagnoses. Cross-check before enrolling.
