---
name: tg013-self-attempt-02
description: Transferable SOP for Northstar Care Intake Portal healthcare intake tasks.
---

# Northstar Care Intake Portal SOP

Use this skill for Northstar Care Intake Portal tasks that ask for structured JSON decisions about registration, dialysis transfers, orthopedic referrals, chart onboarding, or chronic-care enrollment.

## Portal Workflow

1. Sign in at `<TASK_ENV_BASE_URL>/login` with the credentials in the task prompt.
2. Start from the business section named by the prompt:
   - `/patients/{patient_id}` for demographics, clinical/lifestyle indicators, medication-managed flag, and links.
   - `/benefits/{patient_id}` for medical coverage, network, PBM, and preferred pharmacy status.
   - `/charts/{patient_id}` for chart creation, chart completeness, vitals, care plan/instructions, and orientation.
   - `/transfers/{transfer_id}` for transfer packet, requested start, chair status, and chart-prep status.
   - `/referrals/{referral_id}` for referral coding, records, imaging, authorization, duplicate hints, urgency, and practice contact.
   - `/programs/{patient_id}` for chronic-care program, diagnoses, HbA1c/BP, consent, form status, renal flag, coordinator, and telehealth preference.
3. Check `/policies` for the current portal rules. Use visible policy text over assumptions.
4. Follow links on detail pages instead of relying on list-table summaries when a decision depends on a field.
5. Build the final JSON from the task's `answer_template.json`. Use the template's exact top-level keys, row keys, booleans, enum strings, and date fields.

## Output Rules

- Return only valid JSON when requested. Do not add explanations, evidence, comments, or extra keys.
- Sort primary row arrays by the requested ID ascending (`patient_id`, `transfer_id`, or `referral_id`).
- Sort all ID arrays and set-like arrays ascending/alphabetically unless the prompt says otherwise.
- Keep enum values exact. Strip template placeholder spaces around values such as `"accept | hold_capacity"` before output.
- Derive summary fields from rows:
  - `ready_count` or `accepted_count`: count rows with the corresponding ready/accept decision.
  - problem ID arrays: include exactly the rows where that problem boolean/decision applies.
  - unique practice/name arrays: sort unique non-null values.
- For empty sets, output `[]`; for absent optional text fields that are part of the template, output `null` only when the template/prompt allows it.

## Registration Gate Audit

Inspect `/patients/{id}`, `/benefits/{id}`, and the preferred pharmacy/network fields.

Gate rules:

- `medical_insurance`: `pass` only when coverage is active on the review date and medical network is in network. Inactive, terminated, pending COB, out of network, or "network exception needed" blocks.
- `pbm`: required when `Medication Managed` is yes or the service is medication-managed/specialty medication. Pass only for `Pbm Status: active`; inactive, pending, or not located blocks. Use `not_required` when medication/PBM review is not required.
- `pharmacy`: required when PBM/medication-managed review is required. Pass only for `Pharmacy Network Status: in network` and a usable preferred pharmacy. Use `not_required` when pharmacy review is not required.
- `demographics`: pass only when identity, phone, address, consent, and emergency contact are complete/yes on the patient record.
- `pharmacy_network_status`: mirror the benefit/pharmacy network as `in_network`, `out_of_network`, or `not_required`.

Blocked reasons:

- `insurance_inactive`: coverage inactive, terminated, or otherwise not active.
- `insurance_out_of_network`: medical network not in network or needs exception.
- `pbm_inactive`: PBM inactive, pending, missing, or not located when required.
- `pharmacy_out_of_network`: required pharmacy is out of network or unusable.
- `demographics_incomplete`: any required demographic item is incomplete.
- `clinical_review_required`: clinical/lifestyle risk is high or portal/policy says clinical review is needed.

Risk rules:

- Start at `low`.
- Use `moderate` for one or more non-acute concerns such as chronic diagnosis, low exercise, unknown smoking, former smoking, due/unknown vaccination, elevated BP, multiple medications, or relevant allergy.
- Use `high` for current smoking, daily alcohol, declined vaccination, severe BP, multiple significant chronic conditions, or combined lifestyle risks. High risk should add `clinical_review_required`.

Overall decision:

- `blocked` if any hard administrative gate blocks: medical insurance, PBM, pharmacy, or demographics.
- `manual_review` if administrative gates pass but risk is high or clinical review is required.
- `ready` only when all required gates pass and risk does not require review.

## Dialysis Transfer Readiness

Inspect `/transfers/{transfer_id}`. Each packet item appears under `Documents.<Item>.Status` and `.Date`.

Required packet items:

`labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, `transport note`.

Packet rules:

- Put any missing, draft, expired, pending, or otherwise not final/usable item in `missing_packet_items`.
- `Dialysis Prescription` must be `final`; `received` is not enough if the portal distinguishes finality.
- `Authorization` is valid only when final/usable and not expired; set `authorization_valid` accordingly.
- `Confidentiality Statement` is valid only when final/usable and not draft/expired; set `confidentiality_valid` accordingly.
- Labs are current within 30 days before the requested start date.
- Infection screen is current within 14 days before the requested start date.
- If labs or infection screen are otherwise usable/final but outside the freshness window, put the item in `stale_items`, not `missing_packet_items`.
- Sort packet item names exactly as the prompt enumerates them or alphabetically if no order is specified.

Capacity and routing:

- Map requested chair availability:
  - `chair held` or `chair available, not held` -> `start_compatibility: compatible`.
  - `capacity review` -> `capacity_review`.
  - `waitlist` -> `waitlist`.
- `decision: hold_missing_packet` if any missing or stale packet item exists, including authorization/confidentiality problems.
- `decision: hold_capacity` if packet is usable but start compatibility is `capacity_review` or `waitlist`.
- `decision: accept` only when packet, authorization, confidentiality, and start compatibility are usable.
- `route_owner` precedence:
  - `referring_facility` for missing/stale packet items or invalid authorization/confidentiality.
  - `capacity_coordinator` for capacity review or waitlist when packet is usable.
  - `chart_prep` when packet and capacity pass but chart prep is not complete/ready.
  - `intake_complete` when the transfer is accepted and chart prep is complete/ready.

## Orthopedic Referral Scheduling

Inspect `/referrals/{referral_id}` and any linked referral IDs or duplicate hints.

Coding checks:

- `chapter_valid`: true for supported musculoskeletal diagnoses, usually ICD-10 `M...` or an explicitly orthopedic injury code such as `S...`; false for non-orthopedic codes such as endocrine diagnoses.
- `narrative_match`: true only when the diagnosis narrative matches the code and service family.
- `laterality_match`: true when laterality in the code/narrative/field agrees. Spine/non-lateral conditions may use `n/a`.

Issue codes:

- `invalid_chapter`: code/service family is not supported for orthopedics.
- `diagnosis_mismatch`: code and narrative/service family do not agree.
- `laterality_mismatch`: right/left/n/a conflicts across code, narrative, or laterality field.
- `missing_records`: records not received.
- `missing_imaging`: imaging not received when required for the orthopedic condition.
- `authorization_gap`: authorization is missing or pending when required; `approved` and `not required` are usable.
- `duplicate_referral`: linked referral IDs or duplicate hints indicate same patient/condition duplicate review, especially same condition within a recent window.

Readiness status precedence:

1. `coding_clarification` for any coding, narrative, or laterality issue.
2. `duplicate_review` for duplicate issues when coding is otherwise usable.
3. `pending_records` for missing clinical records or imaging.
4. `authorization_followup` for authorization gaps only.
5. `ready_to_schedule` when no issue codes remain.

Other fields:

- `duplicate_linked_referral_ids`: use the linked IDs from the detail page, sorted. Do not invent IDs from vague hints.
- `priority_tier`: use `schedule` for ready referrals; otherwise map urgency as `stat review` -> `tier_1`, `urgent` -> `tier_2`, `routine` -> `tier_3`.
- `follow_up_practice`: practice name for any non-ready referral; `null` for ready referrals.
- `follow_up_practices`: sorted unique non-null follow-up practice names.

## Chart Onboarding Readiness

Inspect `/charts/{patient_id}` and use `/patients/{patient_id}` only for corroborating patient context.

Missing section rules:

- `chart_not_created`: `Chart Created` is no.
- `demographics`: `Demographics Complete` is no.
- `history`: `History Complete` is no.
- `problems`: `Problems Complete` is no or required active problems are absent/incomplete.
- `vitals`: vitals are missing or `Vitals.Current` is no.
- `care_plan_or_instructions`: care plan/instructions are missing, draft, pending nurse edit, or otherwise incomplete. `documented`, `sent`, and `not needed` are usable as shown by the portal context.
- `orientation_message`: orientation is missing, not sent, draft, or otherwise not queued/sent.

Field rules:

- `chart_ready` is true only when `missing_sections` is empty.
- `problem_list_complete` mirrors the portal's `Problems Complete` after applying any visible active-problem requirement.
- `orientation_state`: map `sent` -> `sent`, `queued` -> `queued`, `not sent`/blank -> `missing`, `draft` -> `draft`.
- `bmi_class`: use displayed BMI if present. If only height and weight are present, compute adult BMI; `<25` -> `normal`, `25.0-29.9` -> `overweight`, `>=30` -> `obese`. If BMI/height/weight are not visible, use `not_available`.
- `next_owner` precedence:
  - `registration_desk` for chart not created or demographics missing.
  - `clinical_intake` for history, problems, vitals, or care plan/instructions gaps.
  - `patient_communications` when only orientation communication is missing/draft.
  - `ready` when no gaps remain.

## Chronic-Care Enrollment

Inspect `/programs/{patient_id}` first, then linked patient/chart pages if diagnosis or clinical support is unclear. Use the task's review/as-of date for recency.

Required checks:

- `proposed_program`: copy exactly from the program detail.
- `diagnosis_support`: proposed program must be supported by active diagnoses or explicit renal flag:
  - Diabetes/cardiometabolic pathways require Type 2 diabetes and/or hypertension support as named by the program.
  - Hypertension pathways require hypertension support.
  - Renal risk monitoring can be supported by chronic kidney disease or `Renal Flag: yes`, depending on portal wording.
- `recent_hba1c_or_bp`: diabetes needs a recent HbA1c; hypertension/renal risk needs recent BP. Use visible `Last Visit` and value presence; blank values or stale context are missing.
- `consent_signed`: only `Consent Status: signed` passes. `not obtained` and `verbal pending signature` map to `not_obtained`; `declined` maps to `declined`.
- `program_form_complete`: only `Program Form Status: complete` passes.
- Copy `coordinator` and `telehealth_preference` exactly from the program detail.

Enrollment decision precedence:

1. `clinical_review` for declined consent, unsupported diagnosis/program mismatch, missing clinical support, or safety concerns that need clinician judgment.
2. `hold_missing_consent` when consent is not obtained or only verbal/pending signature.
3. `hold_missing_form` when the program form is incomplete/not started and higher-priority clinical/consent issues do not apply.
4. `enroll_with_nurse_escalation` when all required items pass but renal risk, poor/variable adherence, or high-risk metrics require nurse involvement.
5. `enroll` when all requirements pass without escalation.

Follow-up cadence:

- `weekly_nurse_call` for renal risk/escalation, poor adherence, severe uncontrolled HbA1c/BP, or clinician-review risk.
- `biweekly_checkin` for moderate elevation, variable adherence, or administrative holds needing active follow-up.
- `monthly_checkin` for stable, complete, non-escalated enrollment.

Coordinator queue:

- Include patients needing coordinator action: any hold, clinical review, or nurse escalation. Sort IDs ascending.
- `escalation_count` should count rows with explicit nurse escalation unless the prompt defines it differently.

## Common Pitfalls

- Do not let a stale card image override portal-verified eligibility.
- Do not treat list-page badges as complete evidence when the detail page has newer or more specific status fields.
- Do not mark a document usable just because it has a date; status and freshness both matter.
- Do not include stale labs/infection screens in both `missing_packet_items` and `stale_items`.
- Do not infer duplicate linked IDs from text hints; only list actual linked IDs.
- Do not treat `not needed` as missing for clinical instructions when the portal uses it as a valid state.
- Do not omit rows because a record is blocked; every requested ID needs a complete row.
