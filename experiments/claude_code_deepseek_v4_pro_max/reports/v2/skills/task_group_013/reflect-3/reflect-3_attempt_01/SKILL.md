# Northstar Care Intake Portal — Transferable Solver Skill

## Environment

- **Portal URL**: use the environment base URL set in `GDPEVO_ENV_BASE_URL` or equivalent; do not use `localhost`/`127.0.0.1`
- **Login**: `intake.admin@northstar.example` / `Northstar-Intake-2026!`
- The portal is a server-rendered HTML application (no JSON API for data access); read the HTML `dl` definitions and table rows
- Authenticate via POST `/login` with form-encoded `email`+`password`; capture the `northstar_session` cookie; follow the 303 redirect to `/dashboard`
- All detail pages live at `/<resource>/<id>` (e.g., `/patients/NSP-1008`, `/benefits/BEN-NSP-1008`, `/transfers/TR-2604`, `/referrals/REF-3106`, `/charts/CHR-2040`, `/programs/CCP-4107`)
- Navigate by reading index pages first (`/patients`, `/benefits`, `/transfers`, `/referrals`, `/charts`, `/programs`) for summary tables, then fetch individual detail pages for each record under review
- The `/policies` page links to SOP documents relevant to each domain — fetch these when a task references "policies" or "SOP"
- The `/documents` index lists document packets by patient/transfer; individual document pages show status/date/source fields

## Output conventions (all tasks)

- Keep array entries sorted by ascending ID (patient_id, transfer_id, referral_id)
- Use exactly the enum strings from the answer template; no invented values
- Do not include narrative evidence, source citations, or extra keys in the final JSON
- Empty arrays must be `[]`, not omitted
- Sorted arrays within a record: blocked_reasons, missing_packet_items, stale_items, issue_codes, missing_sections, missing_items — sort lexicographically

---

## Task 1: Patient Registration Audit (NSP-*)

### Data sources
1. **Patient detail page** (`/patients/<id>`) — demographics, clinical/lifestyle risk indicators, registration links
2. **Benefits page** (`/benefits/<id>`) — insurance coverage, PBM, pharmacy network, authorization requirements
3. **Pharmacy detail** (`/pharmacies/<id>`) — may return 404; fall back to the Pharmacy Network Status field on the benefits page

### Gate rules

#### medical_insurance (pass|block)
- `block` if Coverage Status is **inactive** or **terminated** (check the termination date — if it's in the past, insurance is inactive)
- `pass` if Coverage Status is **active**
- Reason: `insurance_inactive` when blocked; when also out-of-network, add `insurance_out_of_network`

#### pbm (pass|block|not_required)
- `block` if PBM Status is **not located** or **inactive**
- `pass` if PBM Status is **active**
- `not_required` when no PBM applies (rare — usually when no pharmacy benefit exists)
- Reason: `pbm_inactive` when blocked

#### pharmacy (pass|block|not_required)
- `pass` when Pharmacy Network Status is **in network**
- `block` when Pharmacy Network Status is **out of network**
- `not_required` when there is no pharmacy record and no medication-managed service
- Reason: `pharmacy_out_of_network` when blocked

#### demographics (pass|block)
- `pass` only when ALL of these are **yes**: Address Complete, Consent Signed, Emergency Contact, Identity Verified, Phone Verified
- `block` when ANY is **no**
- Reason: `demographics_incomplete`

#### risk (low|moderate|high)
Assess from the Clinical fields on the patient page:

| Factor | Low contribution | Moderate contribution | High contribution |
|---|---|---|---|
| Alcohol | never/unknown | weekly | daily |
| Smoking | never/unknown | — | current (badge "good" = smoker) |
| Exercise | ≥150 min/week | <60 or 60-149 min/week | unknown |
| Vaccination | current | due for seasonal | declined |
| Chronic conditions | 0-1 mild | 1-2 managed | 2+ or unmanaged |
| Medications (hot badge) | none/mild | — | 3+ or with "hot" class |

- The `.badge.hot` CSS class on medications is a risk signal
- **moderate** is the default when 1–3 moderate factors are present
- **high** when multiple high-contribution factors combine (e.g., daily alcohol + current smoking + declined vaccination + multiple chronic conditions)
- Do not over-assign `high` — err toward `moderate` unless there is clear multi-factor elevation

### overall_decision (ready|manual_review|blocked)
- `blocked` when any gate is `block`
- `ready` when all gates pass AND risk is `low` or `moderate`
- `manual_review` when risk is `high` even with all gates passing

### Summary fields
- `ready_count`: count of patients with overall_decision = `ready`
- `highest_risk_patient_id`: patient with the highest risk level (if tie, first by ID sort)
- `manual_review_patient_ids`: sorted array of patient IDs with overall_decision = `manual_review`
- `pharmacy_network_statuses`: one entry per patient, sorted by patient_id, using status from the benefits page

---

## Task 2: Dialysis Transfer Readiness (TR-*)

### Data source
- Transfer detail page (`/transfers/<id>`) — all document statuses, chair availability, chart prep, facility info

### Document packet items (9 standard items)
`labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, `transport note`

### missing_packet_items
Include any item whose status is **missing**, **draft**, or **expired**:
- `missing` → the document was never received
- `draft` → document exists but is not final/usable
- `expired` → document was once valid but the validity period has lapsed
- Items with status **received** or **final** are NOT missing (unless stale — see below)

### stale_items (labs and infection screen only)
- Only labs and infection screens can be stale
- "Stale" means status is **received** or **final** (i.e., otherwise usable) but the document date is outside the freshness window relative to the requested start date
- Freshness window for dialysis transfer labs and infection screens: **14 days** before the requested start date
- Example: infection screen dated 2026-07-08 for a start of 2026-07-26 → 18 days gap → stale
- If the item is already missing/draft/expired, it goes in `missing_packet_items`, not `stale_items`

### start_compatibility (compatible|capacity_review|waitlist)
Map from Requested Chair Availability:
- `chair held` → `compatible`
- `chair available, not held` → `compatible`
- `capacity review` → `capacity_review`
- `waitlist` → `waitlist`

### authorization_valid (boolean)
- `true` only when Authorization status is **final** AND the authorization date is on or before the requested start date
- `false` for missing, draft, expired, or future-dated authorization

### confidentiality_valid (boolean)
- `true` only when Confidentiality Statement status is **final**
- `false` for missing, draft, or expired

### decision (accept|hold_missing_packet|hold_capacity)
- `accept`: all 9 packet items usable (final/received and not stale), authorization valid, confidentiality valid, chair compatible
- `hold_missing_packet`: any document is missing/draft/expired/stale
- `hold_capacity`: all documents OK but chair is waitlist or capacity review with no available slot
- If both conditions apply (docs missing AND capacity issue), prefer `hold_missing_packet`

### route_owner (referring_facility|capacity_coordinator|chart_prep|intake_complete)
- `referring_facility`: documents are missing and need to come from the referring facility
- `capacity_coordinator`: documents are complete but chair capacity needs resolution
- `chart_prep`: chart prep status is "not started" or "in progress" and that is the primary blocker
- `intake_complete`: decision is `accept` — all clear
- When chart prep is "not started" and documents are also missing, the route owner depends on which is the primary bottleneck: if chart prep hasn't even started, use `chart_prep`; if chart prep is ready/waiting on documents, use `referring_facility`

### Summary fields
- `accepted_count`: count of `accept` decisions
- `authorization_problem_transfers`: transfer IDs where authorization_valid is `false`, sorted
- `confidentiality_problem_transfers`: transfer IDs where confidentiality_valid is `false`, sorted

---

## Task 3: Orthopedic Referral Scheduling (REF-*)

### Data source
- Referral detail page (`/referrals/<id>`)

### Coding validation
- **chapter_valid**: the ICD-10 code's chapter must match the service family. M codes (Chapter XIII, Musculoskeletal) → orthopedics. E codes (Chapter IV, Endocrine) → endocrinology. Check the first letter of the ICD-10 code against the expected chapter for the service family.
- **narrative_match**: the Diagnosis Narrative text should describe the condition coded by the ICD-10. M17.11 → "unilateral primary osteoarthritis, right knee" is a match. E11.9 → "type 2 diabetes without complications" is a match.
- **laterality_match**: the Laterality field must align with the ICD-10 code and narrative. M17.11 (right knee) → laterality "right" is a match. Codes with laterality "n/a" always match. Spine codes (M54.50) → laterality "spine" is a match.

### readiness_status (ready_to_schedule|pending_records|coding_clarification|authorization_followup|duplicate_review)
Decision priority:
1. If duplicate hints present OR linked referral IDs exist → `duplicate_review`
2. If coding issues (invalid chapter, mismatch, laterality conflict) → `coding_clarification`
3. If authorization is missing or pending → `authorization_followup` (unless duplicate or coding issue takes priority)
4. If records or imaging not received → `pending_records`
5. If none of the above → `ready_to_schedule`

### issue_codes
Based on concrete findings, use any of:
- `invalid_chapter` — ICD-10 chapter doesn't match service family
- `diagnosis_mismatch` — narrative doesn't match ICD-10 code
- `laterality_mismatch` — laterality conflicts with code/narrative
- `missing_records` — Records Received = "no"
- `missing_imaging` — Imaging Received = "no"
- `authorization_gap` — Authorization Status is "missing" or "pending"
- `duplicate_referral` — duplicate hints are present or linked referral IDs exist

### duplicate_linked_referral_ids
- Array of referral IDs from the "Linked Referral Ids" field
- If the field is empty/blank, use `[]`
- Duplicate hints (e.g., "same condition within 30 days", "similar name same DOB") signal possible duplication even without explicit links

### priority_tier (schedule|tier_1|tier_2|tier_3)
- `schedule`: readiness_status is `ready_to_schedule`
- `tier_1`: urgency is "stat review" or "urgent"
- `tier_2`: urgency is "routine"
- `tier_3`: reserved for low-priority follow-ups (not observed in train data)

### follow_up_practice
- The practice name from the Practice field, or `null` if ready_to_schedule
- Only include practices that need follow-up (not the ready ones)

### Summary fields
- `ready_count`: count of `ready_to_schedule` referrals
- `follow_up_practices`: unique sorted list of practice names that need follow-up (excluding nulls)

---

## Task 4: Chart Onboarding Readiness (CHR-*)

### Data source
- Chart detail page (`/charts/<id>`)
- Patient detail page (`/patients/<id>`) — for medication-managed flag and demographics cross-reference

### chart_ready (boolean)
- `true` only when ALL of: chart created, demographics complete, history complete, problems complete, vitals current, care plan present (not missing/draft), clinical instructions not blocking, orientation message sent

### missing_sections
From the controlled enum: `chart_not_created`, `demographics`, `history`, `problems`, `vitals`, `care_plan_or_instructions`, `orientation_message`

Rules for each:
- `chart_not_created`: Chart Created = "no" (this supersedes all other checks — if chart doesn't exist, this is the only section that matters)
- `demographics`: Demographics Complete = "no" (cross-check patient page)
- `history`: History Complete = "no"
- `problems`: Problems Complete = "no"
- `vitals`: Vitals.Current = "no" — the vitals are not current/up-to-date
- `care_plan_or_instructions`: Care Plan is "missing" or "draft", OR Clinical Instructions is "pending nurse edit" (anything that blocks care delivery)
  - "not needed" for Clinical Instructions is NOT a missing section — it means the field is intentionally empty
- `orientation_message`: Orientation Message status is **not** "sent" (i.e., "queued", "missing", or "draft"). When orientation is "queued" or "draft" (not yet sent), add to missing_sections. When orientation is "not sent" but the page shows it as an explicit state, it can be tracked via orientation_state rather than missing_sections.

### bmi_class (not_available|normal|overweight|obese)
- Calculate from Vitals fields if height/weight are present; otherwise `not_available`
- The chart page does not include height/weight in these train tasks, so default to `not_available`

### orientation_state (sent|queued|missing|draft)
- Direct mapping from the Orientation Message field on the chart page
- "queued" = `queued` (scheduled but not yet delivered)
- "sent" = `sent`
- "not sent" on the index page maps to a state — check the detail page for the exact status

### next_owner (registration_desk|clinical_intake|patient_communications|ready)
- `ready`: chart_ready is `true`
- `patient_communications`: primary issue is orientation message not sent/queued
- `clinical_intake`: issues are clinical (problems, care plan, vitals, history)
- `registration_desk`: issues are administrative (demographics incomplete, chart not created)

### problem_list_complete (boolean)
- Direct mapping from Problems Complete on the chart page

### Summary fields
- `ready_count`: count of patients with chart_ready = `true`

---

## Task 5: Chronic-Care Program Enrollment (CCP-*)

### Data source
- Program detail page (`/programs/<id>`)
- Chart page (`/charts/<id>`) for cross-reference on vitals and problem list
- Patient page (`/patients/<id>`) for demographics

### proposed_program
- Directly from the Proposed Program field

### enrollment_decision (enroll|enroll_with_nurse_escalation|hold_missing_consent|hold_missing_form|clinical_review)
Decision logic:
1. If consent is not obtained or declined → `hold_missing_consent`
2. If program form is not started or incomplete → `hold_missing_form`
3. If both consent AND form issues exist → `hold_missing_consent` (consent is the primary gate)
4. If diagnosis doesn't obviously support the proposed program OR key clinical indicators are missing → `clinical_review`
5. If all gates pass but HbA1c ≥ 8.0 or BP ≥ 140/90 → `enroll_with_nurse_escalation`
6. If all gates pass and no escalation triggers → `enroll`

### missing_items
From the enum: `diagnosis_support`, `recent_hba1c_or_bp`, `consent_signed`, `program_form_complete`

- `consent_signed`: consent not obtained or declined
- `program_form_complete`: form status is "not started" or "incomplete"
- `diagnosis_support`: active diagnoses don't clearly match the proposed program's target conditions (e.g., CKD patient proposed for "Hypertension Pathway" with no hypertension diagnosis)
- `recent_hba1c_or_bp`: HbA1c or BP readings are missing or stale (for programs that need them)

### follow_up_cadence (weekly_nurse_call|biweekly_checkin|monthly_checkin)
- `weekly_nurse_call`: high-risk indicators present (HbA1c ≥ 8.0, BP ≥ 140/90, multiple uncontrolled conditions), or enrollment decision involves nurse escalation
- `biweekly_checkin`: moderate risk, controlled conditions, form or consent pending
- `monthly_checkin`: stable, all clear, routine monitoring

### coordinator
- Directly from the Coordinator field on the program page (e.g., "M. Okafor", "R. Alvarez", "S. Lin")

### consent_outcome (signed|not_obtained|declined)
- `signed`: Consent Status is "signed"
- `not_obtained`: Consent Status is "not obtained" or "verbal pending signature"
- `declined`: Consent Status is "declined"

### telehealth_preference
- Directly from the Telehealth Preference field (e.g., "phone", "video", "in-person")

### Summary fields
- `coordinator_queue`: unique sorted list of all coordinator names from the reviewed patients
- `escalation_count`: count of patients with `enroll_with_nurse_escalation`

---

## Common pitfalls

1. **Risk over-assignment in patient registration**: daily alcohol alone doesn't make risk "high" — need multiple reinforcing factors (smoking + declined vaccination + multiple conditions). The `.badge.hot` CSS class on medications is a meaningful signal.

2. **Stale vs missing in transfers**: an item that is expired/draft/missing never goes in `stale_items`, even if its date is old. `stale_items` is exclusively for items that are technically usable (final/received) but outside the 14-day freshness window for the requested start date.

3. **Route owner in transfers**: chart prep "not started" with missing documents means `chart_prep`, not `referring_facility`. Chart prep must start before docs can be requested. When chart prep is "ready pending documents" or "in progress", missing docs route to `referring_facility`.

4. **Coding validation in referrals**: the ICD-10 chapter letter (M, E, S, etc.) must match the service family's expected chapter. M17.11 is Chapter XIII (musculoskeletal) → orthopedics is correct. E11.9 is Chapter IV (endocrine) → endocrinology is correct. The diagnosis narrative must describe the condition coded by the ICD-10. Laterality must be consistent with a lateralized code (right/left for M17.11, n/a for E11.9, spine for M54.50).

5. **Confidentiality vs Authorization validity**: authorization is valid when status is "final" AND the date is on or before the requested start. Confidentiality is valid ONLY when status is "final" — date doesn't matter.

6. **Missing sections in charts**: the `orientation_message` missing section means orientation is not yet sent. Don't confuse "orientation_state=queued" with the missing_section flag — a chart can have orientation queued (not yet sent) and still be otherwise ready. Use the missing_sections array to capture what's actually blocking readiness.

7. **Consent vs form priority in programs**: when both consent and form are missing, consent takes priority as the enrollment_decision. Consent is the primary gate; forms are secondary.

8. **Portal data is in HTML dl/dt/dd tags**: extract values from the `dd` elements following their `dt` labels. The CSS badge classes (`.good`, `.warn`, `.hot`, `.neutral`) carry semantic meaning for risk and status assessment.

9. **ID sort ordering**: all patient/transfer/referral IDs use lexicographic sort within arrays.
