---
name: tg013-fewshot-attempt-02
description: Transferable SOP for Northstar Care Intake Portal healthcare intake tasks.
---

# Northstar Care Intake SOP

Use this skill for Northstar Care Intake Portal tasks that ask you to audit registration, dialysis transfer, orthopedic referral, chart onboarding, or chronic-care program readiness and return structured JSON.

## Portal Workflow

1. Sign in at `<TASK_ENV_BASE_URL>/login` with the credentials from the task prompt.
2. Use the portal pages as the source of truth. The main routes are:
   - `/patients`, `/benefits`, `/transfers`, `/referrals`, `/charts`, `/programs`, `/queue`, `/documents`, `/policies`
   - Detail routes usually work as `/patients/{id}`, `/benefits/{patient_id}`, `/transfers/{id}`, `/referrals/{id}`, `/charts/{id}`, `/programs/{id}`.
   - Search list pages with `?q=<ID>` when direct navigation is uncertain.
3. Open `/policies` once for the applicable family. The policy page defines current freshness windows and readiness requirements.
4. Read field text, not badge color. Badge colors are hints; status words such as `missing`, `draft`, `expired`, `not located`, `pending`, `sent`, and `not needed` drive decisions.
5. For patient registration tasks, the patient page links Benefits, Chart, and Program. The Benefits page is the authoritative place for coverage, network, PBM, and pharmacy network fields.
6. For coordinator queue fields, search `/queue?q=<ID>` for each requested ID and include the ID when a queue row is linked to it, regardless of queue status.

## JSON Contract

- Return only JSON matching the provided `input/payloads/answer_template.json`: no evidence notes, no extra keys, no enum variants outside the template or prompt.
- Preserve fixed metadata such as `task_id` and `review_date` from the template/prompt.
- Sort entity rows by the requested ID field ascending.
- Sort ID arrays ascending. Sort set-like arrays, such as `blocked_reasons`, `missing_packet_items`, `stale_items`, `issue_codes`, `missing_items`, and unique name arrays, alphabetically unless the prompt says otherwise.
- Compute count fields from your final row decisions, not from portal summary counts.
- If a single `highest_*_patient_id` is required, rank severity first and use the sorted-last ID among tied highest-severity patients unless the task gives a different tie rule.

## Registration Readiness

Inspect the patient page and Benefits page.

Gate rules:

- `medical_insurance`: `pass` only when `Coverage Status` is active on the review date and `Network Status` is in network. `inactive`, `terminated`, or inactive by termination date blocks with `insurance_inactive`; out-of-network blocks with `insurance_out_of_network`. A missing or stale card image does not override portal-verified eligibility.
- `pbm`: for medication-managed intake, `pass` only when `Pbm Status` is active. `not located`, inactive, expired, or missing blocks with `pbm_inactive`. Use `not_required` only when the portal/task clearly says PBM is not required.
- `pharmacy`: for medication-managed intake, `pass` only when the preferred pharmacy network status is in network. Out-of-network blocks with `pharmacy_out_of_network`. Use `not_required` only when pharmacy network is not required.
- `pharmacy_network_status` mirrors the pharmacy network finding: `in_network`, `out_of_network`, or `not_required`.
- `demographics`: `pass` only when address, consent, emergency contact, identity, and phone verification items are complete/yes. Any no/missing item blocks with `demographics_incomplete`.
- `risk`: assign `low`, `moderate`, or `high` from clinical/lifestyle indicators. Chronic disease, smoking, poor exercise, missing vaccination, older age, or medication complexity usually raise to `moderate`; multiple such factors, daily alcohol, unknown/current smoking with other concerns, renal/medication-managed complexity, missing medication clarity, or other clinical safety concern raises to `high`.

Decision rules:

- Add `clinical_review_required` to `blocked_reasons` when risk is `high`.
- `ready` when all required gates pass and risk is not high.
- `manual_review` when the only issue is clinical review or another non-administrative review need.
- `blocked` when any administrative gate blocks: insurance, PBM, pharmacy, or demographics. Include all applicable blocked reasons.
- `manual_review_patient_ids` contains only rows with `overall_decision: manual_review`; `ready_count` counts `ready` rows.

## Dialysis Transfer Readiness

Inspect the transfer detail and the renal transfer policy.

Packet rules:

- Required packet names are exactly: `labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, `transport note`.
- A packet item is missing when its status is `missing`, `draft`, `expired`, blank, or otherwise not final/usable. Put it in `missing_packet_items`.
- `final` and `received` are usable unless the policy requires a stricter label for that item.
- Labs are current within 30 days of requested start. Infection screening is current within 14 days of requested start. If labs or infection screen are otherwise usable but outside the freshness window, put them in `stale_items`, not `missing_packet_items`.
- If labs or infection screen status itself is `expired`, `missing`, or `draft`, treat it as missing rather than stale.
- `authorization_valid` is true only when authorization is usable/final. `confidentiality_valid` is true only when confidentiality statement is usable/final.

Capacity and routing:

- Map requested chair availability to `start_compatibility`: confirmed/available chair means `compatible`; capacity review means `capacity_review`; waitlist/no chair means `waitlist`.
- Decision precedence: any missing or stale packet item => `hold_missing_packet`; else capacity review or waitlist => `hold_capacity`; else `accept`.
- Route owner precedence: missing/stale packet => `referring_facility`; capacity hold => `capacity_coordinator`; packet/capacity OK but chart prep incomplete => `chart_prep`; accepted and chart prep ready => `intake_complete`.
- `accepted_count` counts `accept`. Authorization/confidentiality problem arrays contain transfer IDs where the corresponding valid boolean is false.

## Orthopedic Referral Readiness

Inspect the referral detail and referral policy.

Coding and issue rules:

- `chapter_valid` is true for an M-code or a supported musculoskeletal diagnosis for orthopedics. Non-musculoskeletal codes/service families usually add `invalid_chapter`.
- `narrative_match` is true only when ICD code, diagnosis narrative, and service family describe the same condition. Mismatches add `diagnosis_mismatch`.
- `laterality_match` is true only when code suffix, narrative, and `Laterality` agree. Add `laterality_mismatch` for left/right/n/a conflicts on lateral conditions.
- `missing_records` and `missing_imaging` come directly from `Records Received` and `Imaging Received`.
- Authorization statuses `missing`, `pending`, expired, or not approved add `authorization_gap`.
- Add `duplicate_referral` when linked referral IDs are present or the portal clearly identifies a duplicate. Keep `duplicate_linked_referral_ids` sorted.

Readiness precedence:

- `duplicate_review` if `duplicate_referral` is present.
- Else `coding_clarification` if any coding issue is present.
- Else `pending_records` if records or imaging are missing, even when authorization also needs follow-up.
- Else `authorization_followup` if authorization is the only issue.
- Else `ready_to_schedule`.

Other fields:

- `follow_up_practice` is the referring practice for any non-ready referral; use null for ready referrals unless the template says otherwise.
- `follow_up_practices` is the unique sorted list of non-null follow-up practices.
- `priority_tier`: ready referrals use `schedule`. Stat review or urgent clinical-record gaps are usually `tier_1`; routine or single authorization follow-up is usually `tier_2`; lower-priority administrative/duplicate-context follow-up can be `tier_3`. Use visible urgency and context over received-date guessing.

## Chart Onboarding Readiness

Inspect the chart detail and chart policy.

Required section rules:

- `chart_ready` is true only when the chart exists and all required sections are complete.
- Add `chart_not_created` when `Chart Created` is no.
- Add `demographics`, `history`, `problems`, or `vitals` when the corresponding complete/current field is no, missing, or unusable.
- `problem_list_complete` mirrors `Problems Complete`.
- For `care_plan_or_instructions`, the requirement is satisfied when either an onboarding care plan is documented/usable or clinical instructions are documented/usable or explicitly `not needed`. Do not mark missing just because one of the two fields is missing if the other satisfies the requirement.
- `orientation_state` maps directly from Orientation Message: `sent`, `queued`, `draft`, or `missing`. Only `sent` satisfies readiness; queued/draft/missing add `orientation_message`.
- `bmi_class` is `not_available` when no BMI or height/weight data is visible. Otherwise use standard classes: normal 18.5-24.9, overweight 25-29.9, obese >=30.

Owner precedence:

- `registration_desk` for chart not created or demographics gaps.
- `clinical_intake` for history, problem list, vitals, or care-plan/instruction gaps.
- `patient_communications` when the only remaining gap is orientation communication.
- `ready` when `chart_ready` is true.

## Chronic-Care Program Enrollment

Inspect the program detail, chronic-care policy, related chart/patient pages if needed, and queue membership.

Missing item rules:

- `diagnosis_support`: proposed program is not supported by active diagnoses or renal flag. Diabetes/hypertension pathways need matching active diagnoses; renal risk programs need renal support.
- `recent_hba1c_or_bp`: neither a relevant recent HbA1c nor a usable BP/vital is present for the proposed program.
- `consent_signed`: consent is not signed, including `not obtained` or `declined`.
- `program_form_complete`: program form is not complete.
- `consent_outcome`: `signed`, `not_obtained`, or `declined` from Consent Status.

Decision precedence:

- `hold_missing_consent` when consent is not signed, even if other items are also missing.
- Else `clinical_review` when diagnosis support is missing or the portal indicates clinical review is needed.
- Else `hold_missing_form` when the form is incomplete.
- Else `enroll_with_nurse_escalation` when enrollment can proceed but renal flag, uncontrolled HbA1c/BP, poor or unknown adherence, or explicit escalation requires nurse involvement.
- Else `enroll`.

Cadence and queue:

- `weekly_nurse_call` for renal flag, nurse escalation, clinical review, poor/unknown adherence with risk, or uncontrolled HbA1c/BP.
- `biweekly_checkin` for moderate metabolic risk or missing consent/form follow-up without urgent nurse escalation.
- `monthly_checkin` for stable, complete lower-risk enrollment.
- Copy `proposed_program`, `coordinator`, and `telehealth_preference` exactly from the portal.
- `coordinator_queue` is the sorted list of requested patient/program IDs found on the Queue page. `escalation_count` counts only `enroll_with_nurse_escalation` rows.

## Common Pitfalls

- Do not use local source files or inferred backend data. The portal fields and policy page are the working record.
- Do not let list-page summaries replace detail-page fields.
- `pending` authorization is a gap; queued orientation is not complete; draft or expired transfer documents are missing.
- A chart can exist without being ready.
- Pharmacy network and PBM requirements are tied to medication-managed intake; use `not_required` only with explicit evidence.
- Transfer freshness is relative to the requested start date, not the current date.
- Queue status is separate from readiness decisions; use it only for fields that ask for queue membership or owner routing.
