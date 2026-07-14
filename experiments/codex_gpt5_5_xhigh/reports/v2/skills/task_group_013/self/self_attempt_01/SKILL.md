---
name: tg013-self-attempt-01
description: Transferable SOP for Northstar Care Intake Portal healthcare intake tasks.
---

# Northstar Care Intake Portal SOP

Use the portal URL supplied for `<TASK_ENV_BASE_URL>` and sign in with the credentials in the task prompt. Work from portal records and visible policy/context pages, not local assumptions. The top navigation has the main families: Patients, Benefits, Pharmacies, Transfers, Referrals, Charts, Programs, Queue, Documents, Policies. Search pages accept `?q=...`, but list rows are triage only; open detail pages before deciding.

## Universal Output Rules

- Return only JSON matching the provided template. Do not add evidence, prose, or extra keys.
- Use exact enum strings from the prompt/template. If a template displays `a | b`, output only `a` or `b`, without spaces or pipes.
- Sort main row arrays by the requested ID key ascending. Sort ID arrays ascending. Sort set-like arrays such as issue codes, missing items, stale items, and blocked reasons lexicographically by exact enum string unless the prompt gives another order.
- Recompute aggregate fields from row decisions: counts, highest-risk ID, queue/exception ID lists, and status summary arrays must agree with the detailed rows.
- Use the review date in the record or prompt. For transfers, freshness is relative to the requested start date, not today's date.

## Portal Navigation

- Patient detail pages (`/patients/{patient_id}`) show demographics, medication-managed status, registration links, and clinical/lifestyle risk indicators.
- Benefits detail pages (`/benefits/{patient_id}`) are the reliable source for medical coverage, network, PBM, preferred pharmacy, review date, and pharmacy network status.
- Transfer, referral, chart, and program details live at `/transfers/{id}`, `/referrals/{id}`, `/charts/{patient_id}`, and `/programs/{patient_id}`.
- Queue rows point to linked records. Use the queue only when asked about queue membership or queue work; do not substitute it for the linked record detail.
- Policies contain controlling rules. Documents usually summarize context; use them if the prompt points there, but still verify record fields.

## Registration Gates

- `medical_insurance` passes only when portal-verified coverage is active on the review date and `Network Status` is in network. `inactive` or `terminated` blocks with `insurance_inactive`; out-of-network blocks with `insurance_out_of_network`. A card image never overrides the portal eligibility snapshot.
- If `Medication Managed` is `yes`, PBM and pharmacy are required. PBM passes only when `Pbm Status` is active; missing, inactive, not located, or terminated PBM blocks with `pbm_inactive`. Preferred pharmacy passes only when `Pharmacy Network Status` is in network; out-of-network or mail-order-only status blocks with `pharmacy_out_of_network`.
- If `Medication Managed` is `no`, set PBM/pharmacy gates and pharmacy network status to `not_required` when those fields are requested.
- `demographics` passes only when address, consent, emergency contact, identity, and phone verification are complete/yes. Any gap blocks with `demographics_incomplete`.
- Clinical/lifestyle risk is separate from administrative gates. Treat current smoking, daily alcohol, declined/unknown vaccination, unknown smoking/exercise, very low exercise, multiple chronic diseases, renal/dialysis context, significant allergies, and polypharmacy as risk flags. Use `high` for multiple or serious flags, `moderate` for limited nonblocking flags, and `low` when minimal.
- Overall decision: `blocked` if any hard administrative gate blocks; `manual_review` when gates pass but high clinical risk requires review; otherwise `ready`. Add `clinical_review_required` only for risk-driven manual review. `ready_count` counts only `ready`; manual-review ID lists include only `manual_review`. For highest-risk ties, choose the lowest patient ID.

## Dialysis Transfers

- Required packet items are `labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, and `transport note`.
- Statuses `missing`, `draft`, `expired`, or otherwise not final/usable go in `missing_packet_items` using the exact packet item name. Dialysis prescriptions must be final.
- Labs are current within 30 days of requested start; infection screens are current within 14 days. Only usable labs/infection screens that are outside those windows go in `stale_items`; unusable statuses go in `missing_packet_items` instead.
- `authorization_valid` and `confidentiality_valid` are true only when those items are usable/final, not draft/expired/missing.
- Map chair status to `start_compatibility`: chair held -> `compatible`; waitlist -> `waitlist`; capacity review or chair available but not held -> `capacity_review`.
- Decision precedence: any missing or stale packet item -> `hold_missing_packet`; else non-compatible capacity -> `hold_capacity`; else `accept`.
- Route owner precedence: packet/auth/confidentiality problems -> `referring_facility`; capacity issue -> `capacity_coordinator`; packet and capacity clear but chart prep not complete -> `chart_prep`; all clear -> `intake_complete`.

## Orthopedic Referrals

- Scheduling requires a supported musculoskeletal diagnosis/code, narrative agreement, laterality agreement, records, imaging, and required authorization.
- `chapter_valid` is true for supported orthopedic/musculoskeletal codes such as M-codes and explicitly supported injury codes. Non-orthopedic codes or service families create `invalid_chapter`.
- `narrative_match` checks whether the ICD code meaning matches the diagnosis narrative. A mismatch creates `diagnosis_mismatch`.
- `laterality_match` checks code, narrative, and laterality together. Right-knee codes/narratives must be right; left-knee codes must be left; spine codes should indicate spine or no side. Mismatch creates `laterality_mismatch`.
- Missing records or imaging create `missing_records` and/or `missing_imaging`. Authorization statuses `missing` or `pending` create `authorization_gap`; `approved` and truly `not required` are acceptable.
- Do not treat a linked referral ID as an automatic duplicate. Open/compare linked records or duplicate hints against patient demographics and condition. Only same patient/demographics with same or overlapping condition creates `duplicate_referral`; include confirmed linked duplicate IDs sorted.
- `readiness_status`: no issues -> `ready_to_schedule`; duplicate issue -> `duplicate_review`; coding/laterality issue -> `coding_clarification`; records or imaging gap -> `pending_records`; authorization-only gap -> `authorization_followup`.
- Priority tier normally maps from urgency: ready records -> `schedule`; stat review -> `tier_1`; urgent -> `tier_2`; routine -> `tier_3`.
- `follow_up_practice` is the referring practice when follow-up is needed; use `null` for ready records.

## Chart Onboarding

- A chart is ready only when the chart is created and demographics, history, active problems, current vitals, care plan or clinical instructions, and orientation communication are complete.
- Add `chart_not_created` when `Chart Created` is not yes. Add `demographics`, `history`, `problems`, or `vitals` when the matching complete/current field is no or missing.
- Add `care_plan_or_instructions` when the care plan is missing/draft or clinical instructions are pending, unless the record explicitly says instructions are not needed and no care plan is required.
- Orientation state maps as: sent -> `sent`; queued -> `queued`; draft -> `draft`; not sent/missing/not invited -> `missing`. Only sent is fully complete for readiness.
- `chart_ready` is true only when `missing_sections` is empty. `problem_list_complete` mirrors the problems-complete field.
- BMI class: if BMI/height/weight is unavailable, use `not_available`; otherwise normal is 18.5-24.9, overweight 25-29.9, obese >=30.
- `next_owner` precedence: chart not created or demographics gap -> `registration_desk`; clinical section/vitals/care-plan gap -> `clinical_intake`; orientation-only gap -> `patient_communications`; no gaps -> `ready`.

## Chronic-Care Programs

- Use the program detail page as primary source for proposed program, active diagnoses, BP, recent HbA1c, renal flag, consent, form status, coordinator, telehealth preference, last visit, and adherence.
- Diagnosis support: diabetes pathways need active Type 2 diabetes; hypertension pathways need active hypertension; cardiometabolic combo needs the relevant cardio/metabolic diagnoses; renal-risk monitoring needs renal flag and/or CKD support. Unsupported pathway -> `diagnosis_support`.
- Recent data: diabetes needs a recent HbA1c; hypertension/renal-risk needs recent BP or required vitals/labs. Missing or stale evidence -> `recent_hba1c_or_bp`.
- Consent outcome: `signed` only when consent status is signed; explicit declined -> `declined`; not obtained/verbal pending signature/missing -> `not_obtained`. Missing signed consent adds `consent_signed`.
- Program form must be `complete`; incomplete, not started, draft, or pending adds `program_form_complete`.
- Decision order: unsupported diagnosis or missing clinical evidence -> `clinical_review`; missing/declined consent -> `hold_missing_consent`; incomplete form -> `hold_missing_form`; otherwise renal flag, renal-risk program, poor adherence, or markedly abnormal HbA1c/BP -> `enroll_with_nurse_escalation`; otherwise `enroll`.
- Cadence: renal risk or nurse escalation -> `weekly_nurse_call`; uncontrolled but not escalated diabetes/BP/adherence -> `biweekly_checkin`; stable routine enrollment -> `monthly_checkin`.
- Coordinator queue should include patients needing non-routine action: any hold, `clinical_review`, or `enroll_with_nurse_escalation`. `escalation_count` counts only nurse-escalation enrollments unless the prompt defines it differently.

## Common Pitfalls

- Do not rely on list badges when detail pages contain more precise status/date fields.
- Do not use `not_required` for a missing, pending, inactive, or not-located item.
- For transfers, `chair available, not held` is not an accept state; it still needs capacity coordination.
- For transfer freshness, stale applies only to otherwise usable labs or infection screens; expired/draft/missing items are missing packet items.
- For referrals, same physician alone is not a duplicate. Verify demographics and condition.
- `Chart Created: yes` does not imply onboarding readiness.
- `verbal pending signature` is not signed consent.
