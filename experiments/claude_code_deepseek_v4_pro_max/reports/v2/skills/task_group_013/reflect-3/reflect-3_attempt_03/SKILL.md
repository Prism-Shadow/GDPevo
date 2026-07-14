# Northstar Care Intake Portal — Solver Skill

This skill covers five intake-audit workflows in the Northstar Care Intake Portal. Each workflow reviews structured portal records and returns a JSON answer matching a provided template. All workflows share a common portal, authentication, and general navigation pattern.

## Portal Access

- The portal is a server-rendered HTML web application. Use HTTP GET to navigate pages and POST for the login form.
- **Authentication**: POST `email` and `password` as form-encoded fields to `/login`. The server sets a `northstar_session` cookie on success (303 redirect to `/dashboard`). Carry this cookie on all subsequent requests.
- **Credentials** (provided per task): `intake.admin@northstar.example` / `Northstar-Intake-2026!`
- **Navigation bar** links to: `/patients`, `/benefits`, `/pharmacies`, `/transfers`, `/referrals`, `/charts`, `/programs`, `/queue`, `/documents`, `/policies`.

## General Solver Patterns

1. **Read the prompt carefully** — each task lists the specific record IDs and the sections of the portal you must inspect.
2. **Always read the `/policies` page** — it contains numbered policy statements (e.g. `POL-REG-01`) that define the business rules for each workflow.
3. **Navigate to each record's detail page** — individual records live at `/<section>/<id>`. For patient registration tasks you must also check `/benefits/<patient_id>` for insurance/PBM/pharmacy data.
4. **Match the answer template exactly** — use only the enum strings shown in the template. Sort arrays (patient IDs, transfer IDs, referral IDs) in ascending order.
5. **Use sorted arrays for sets** — e.g. `blocked_reasons`, `missing_packet_items`, `stale_items`, `issue_codes`, `missing_sections` must be sorted alphabetically.
6. **Do not include narrative evidence or extra keys** in the final JSON.

---

## Workflow 1: New-Patient Registration Audit (NSP-*)

**Policy reference**: `POL-REG-01` — Registration gates.

**Records to inspect**: Patient detail (`/patients/<id>`), Benefits (`/benefits/<id>`).

### Gate Rules

| Gate | Pass condition | Block condition |
|---|---|---|
| `medical_insurance` | Coverage Status = `active` AND Network Status = `in network` on the review date | Coverage `inactive` or `terminated` (termination date before review date), or Network `out of network` |
| `pbm` | PBM Status = `active` | PBM Status = `not located` (equivalent to inactive). **Not required** if patient is not medication-managed — check `Medication Managed` on patient detail. |
| `pharmacy` | Pharmacy Network Status = `in network` | Pharmacy Network Status = `out of network`. **Not required** if patient is not medication-managed. |
| `demographics` | All of Address Complete, Consent Signed, Identity Verified, Phone Verified = `yes` | Any of Identity Verified or Phone Verified = `no`. Emergency Contact = `no` also blocks. |
| `risk` | — | Evaluated separately as `low`, `moderate`, or `high` based on clinical/lifestyle indicators |

### Clinical Risk Assessment

Risk factors that elevate the risk level:
- **Daily alcohol** use
- **Current smoking** (the portal uses "current" as a smoking status — this is a risk factor, not a positive)
- **Vaccination declined** or **due for seasonal**
- **Polypharmacy** (3+ medications, often displayed with a "hot" badge in the portal)
- Multiple chronic conditions (Type 2 diabetes, asthma, hyperlipidemia, CKD, heart failure)
- Exercise `<60 min/week`
- Age > 65 combined with other factors

A single risk factor typically produces `low` or `moderate`. Multiple co-occurring risk factors — especially daily alcohol, current smoking, vaccination declined, AND polypharmacy together — drive risk to `high`.

### Decision Logic

- Any administrative gate = `block` → `overall_decision` = `blocked`, `blocked_reasons` lists the specific gate failures
- All administrative gates = `pass` AND risk = `high` → `overall_decision` = `manual_review`, `blocked_reasons` includes `clinical_review_required`
- All administrative gates = `pass` AND risk = `low` or `moderate` → `overall_decision` = `ready`
- Do NOT include `clinical_review_required` in `blocked_reasons` when administrative gates are already blocked — it only applies when risk alone drives manual review

### Blocked Reasons (sorted alphabetically)

Use only from: `insurance_inactive`, `insurance_out_of_network`, `pbm_inactive`, `pharmacy_out_of_network`, `demographics_incomplete`, `clinical_review_required`

### Aggregate Fields

- `ready_count`: count of patients with `overall_decision` = `ready`
- `highest_risk_patient_id`: the patient ID with the highest risk level (`high` > `moderate` > `low`). If tie, pick the first by ID order.
- `manual_review_patient_ids`: sorted list of patients with `overall_decision` = `manual_review`
- `pharmacy_network_statuses`: one entry per patient with the pharmacy network status from benefits. Use `in_network`, `out_of_network`, or `not_required` (when pharmacy gate is not required).

---

## Workflow 2: Dialysis Transfer Readiness (TR-*)

**Policy reference**: `POL-REN-02` — Dialysis transfer freshness.

**Records to inspect**: Transfer detail (`/transfers/<id>`).

### Document Classification

Each document under `Documents.<Name>.Status` can be one of:
- `final` — valid and current
- `received` — usable but check freshness
- `draft` — not final → goes in `missing_packet_items`
- `expired` — not usable → goes in `missing_packet_items`
- `missing` — not present → goes in `missing_packet_items`

### Freshness Windows (from POL-REN-02)

- **Labs**: current within **30 days** of requested start date. If a lab is `received` or `final` but its date is more than 30 days before the requested start, it goes in `stale_items`.
- **Infection screen**: current within **14 days** of requested start date. Same rule: `received` or `final` but > 14 days before start → `stale_items`.
- **Dialysis prescription**: must be `final`. If `draft`, `expired`, or `missing` → `missing_packet_items`.
- All other items (medication list, allergy list, authorization, confidentiality statement, referring contact, transport note): must be in a usable state. `draft`, `expired`, `missing` → `missing_packet_items`.

**Important**: Stale items are ONLY those that are otherwise usable (`received` or `final`) but out of the freshness window. Items that are `draft`, `expired`, or `missing` go in `missing_packet_items`, not `stale_items`.

### Packet Item Names (sorted alphabetically in arrays)

`allergy list`, `authorization`, `confidentiality statement`, `dialysis prescription`, `infection screen`, `labs`, `medication list`, `referring contact`, `transport note`

### Decision, Start Compatibility, Route Owner

- **decision**: `accept` if all items are present (final/received) and within freshness windows and chair is held. `hold_missing_packet` if any packet items are missing/draft/expired. `hold_capacity` if packet is complete but chair is not held (waitlist or capacity review without a held chair).
- **start_compatibility**: Map chair availability to enums:
  - `chair held` → `compatible`
  - `chair available, not held` → `compatible` (chair exists but not reserved)
  - `capacity review` → `capacity_review`
  - `waitlist` → `waitlist`
- **route_owner**: `referring_facility` when packet items are missing (they need to send documents). `capacity_coordinator` for capacity issues. `chart_prep` when chart prep is not started. `intake_complete` when everything is resolved.

### Authorization and Confidentiality Validity

- `authorization_valid`: `true` ONLY if Authorization status = `final`
- `confidentiality_valid`: `true` ONLY if Confidentiality Statement status = `final`

### Aggregate Fields

- `accepted_count`: count of transfers with decision = `accept`
- `authorization_problem_transfers`: sorted list of transfer IDs where authorization is NOT valid
- `confidentiality_problem_transfers`: sorted list of transfer IDs where confidentiality is NOT valid

---

## Workflow 3: Orthopedic Referral Scheduling (REF-*)

**Policy reference**: `POL-REF-03` — Orthopedics referral scheduling.

**Records to inspect**: Referral detail (`/referrals/<id>`).

### Coding Validity

- **chapter_valid**: `true` if the ICD-10 code is in chapter 13 (M-codes, e.g. M17.11, M25.562, M54.50, S83.241A). `false` for codes in other chapters (e.g. E11.9 is chapter 4, endocrine).
- **narrative_match**: `true` if the Diagnosis Narrative text describes a condition consistent with the ICD-10 code. E.g. "unilateral primary osteoarthritis, right knee" matches M17.11. "type 2 diabetes without complications" does NOT match M17.11 (it matches E11.9).
- **laterality_match**: `true` if the Laterality field is consistent with the ICD-10 code and narrative. For codes like E11.9 where laterality is `n/a`, this is typically `true` (the code itself has no laterality concept). For M-codes with a specific joint, the laterality should match the narrative.

### Issue Codes

Determine issues from the referral data:
- `invalid_chapter` — ICD-10 is not an M-code or supported musculoskeletal diagnosis
- `diagnosis_mismatch` — narrative doesn't match the ICD-10 code
- `laterality_mismatch` — laterality doesn't match between code and narrative
- `missing_records` — Records Received = `no`
- `missing_imaging` — Imaging Received = `no`
- `authorization_gap` — Authorization Status = `missing` or `pending`
- `duplicate_referral` — Duplicate Hints field contains a substantive flag (not "none" or "same physician only"). "same condition within 30 days" and "similar name same DOB" are both substantive duplicate flags.

### Authorization Gap vs. Not Required

Authorization Status can be `approved`, `pending`, `missing`, or `not required`. Only `missing` and `pending` are `authorization_gap`. `not required` means the payer does not require authorization — this is NOT an issue.

### Readiness Status

Determined by the most blocking issue:
- `ready_to_schedule` — no issues, coding valid, records/imaging present, auth approved or not required
- `pending_records` — records or imaging missing (takes priority over authorization issues)
- `authorization_followup` — authorization missing or pending (and records/imaging are present)
- `coding_clarification` — ICD-10 code chapter invalid or diagnosis mismatch
- `duplicate_review` — duplicate flag present (even alongside other issues, when duplicate is the primary concern)

When multiple issues exist, `pending_records` takes precedence over `authorization_followup`. `coding_clarification` takes precedence over both (if the code is wrong, nothing else matters). `duplicate_review` is used when a duplicate flag exists alongside other issues for urgent/stat referrals.

### Priority Tier

- `schedule` — ready to schedule (no issues)
- `tier_1` — highest follow-up priority (stat review, urgent)
- `tier_2` — routine priority
- `tier_3` — lowest priority

### Duplicate Linked Referrals

- `duplicate_linked_referral_ids` — if the `Linked Referral Ids` field on the referral detail page contains referral IDs, list them here sorted. Otherwise empty array `[]`.

### Follow-up Practice

- `follow_up_practice` — the Practice name from the referral detail, or `null` if no follow-up is needed (ready_to_schedule with no issues).

### Aggregate Fields

- `ready_count`: count of referrals with readiness_status = `ready_to_schedule`
- `follow_up_practices`: sorted unique list of practice names that need follow-up (from referrals not ready to schedule). Exclude `null` values.

---

## Workflow 4: Chart Onboarding Readiness (CHR-*)

**Policy reference**: `POL-CHR-04` — Chart readiness.

**Records to inspect**: Chart detail (`/charts/<id>`).

### Chart Readiness

A chart is ready (`chart_ready = true`) ONLY when ALL of these are complete:
- Chart Created = `yes`
- Demographics Complete = `yes`
- History Complete = `yes`
- Problems Complete = `yes`
- Vitals are current (Vitals.Current = `yes`)
- Care Plan is `documented` (NOT `missing` or `draft`)
- Clinical Instructions are not missing (either present or explicitly `not needed`)
- Orientation Message is `sent`

**Important nuance**: A chart can exist (`Chart Created = yes`) without being ready. The "Created" on the charts listing page shows "yes" for most — this is a separate concept from `chart_ready`.

### Missing Sections

Populate `missing_sections` (sorted alphabetically) with any of:
- `chart_not_created` — Chart Created = `no`
- `demographics` — Demographics Complete = `no`
- `history` — History Complete = `no`
- `problems` — Problems Complete = `no`
- `vitals` — Vitals are not current (Vitals.Current = `no`)
- `care_plan_or_instructions` — Care Plan is `missing` or `draft`, OR Clinical Instructions are missing (and needed, i.e. not `not needed`)
- `orientation_message` — Orientation Message is not `sent` (i.e. `queued`, `not sent`/`missing`, `draft`)

A chart with all sections complete but orientation queued → `orientation_message` in missing_sections.

### BMI Class

Use `not_available` unless the portal provides both height and weight to compute BMI. The chart detail page does not typically show height/weight raw values, so `not_available` is the default.

### Orientation State

Map the portal's "Orientation Message" field:
- `sent` → `sent`
- `queued` → `queued`
- `not sent` → `missing`
- `draft` → `draft`

### Next Owner

- `ready` — chart is fully ready
- `clinical_intake` — missing clinical items (care plan, instructions, problems, vitals)
- `registration_desk` — missing demographics
- `patient_communications` — orientation message is missing/queued/draft (but clinical items are complete)

When multiple sections are missing, prioritize: `registration_desk` > `patient_communications` > `clinical_intake` > `ready`.

### Problem List Complete

`true` if Problems Complete = `yes`, `false` otherwise. This is a convenience field that mirrors the problems section status.

### Aggregate Fields

- `ready_count`: count of patients with `chart_ready = true`

---

## Workflow 5: Chronic-Care Program Enrollment (CCP-*)

**Policy reference**: `POL-CCP-05` — Chronic program enrollment.

**Records to inspect**: Program detail (`/programs/<id>`). The programs listing page also provides summary data.

### Enrollment Decision

Based on program form, consent, and clinical data:

- **`enroll`** — All requirements met: active diagnosis present, recent labs/vitals available, consent signed, program form complete, no escalation triggers
- **`enroll_with_nurse_escalation`** — All requirements met BUT renal flag = `yes` AND either HbA1c ≥ 9.0 or BP elevated (systolic ≥ 140 or diastolic ≥ 90). Nurse escalation is needed for high-risk renal patients.
- **`hold_missing_consent`** — Consent is `not obtained` or `verbal pending signature`. Consent is the primary gate — if missing, this decision takes priority over missing form.
- **`hold_missing_form`** — Program form is `not started` or `incomplete`, but consent is signed.
- **`clinical_review`** — Consent was explicitly `declined` (not just missing), OR the proposed program doesn't match the active diagnoses (e.g. Hypertension Pathway for a patient with only CKD and normal BP), OR other clinical ambiguity requiring human review.

### Missing Items (sorted alphabetically)

Use from: `diagnosis_support`, `recent_hba1c_or_bp`, `consent_signed`, `program_form_complete`

- `diagnosis_support` — the proposed program requires a diagnosis that isn't present in Active Diagnoses (e.g. "Hypertension Pathway" without hypertension). Also use if the diagnosis exists but there are no recent labs/vitals to support it.
- `recent_hba1c_or_bp` — neither HbA1c nor BP readings are present for pathways that require them (diabetes pathway needs HbA1c, hypertension pathway needs BP)
- `consent_signed` — consent is `not obtained` or `verbal pending signature`
- `program_form_complete` — form is `not started` or `incomplete`

### Follow-up Cadence

- `weekly_nurse_call` — renal flag = `yes` AND enrollment is `enroll_with_nurse_escalation`
- `biweekly_checkin` — renal flag = `yes` (without nurse escalation) OR patient has multiple active conditions requiring closer monitoring
- `monthly_checkin` — renal flag = `no`, standard monitoring

### Consent Outcome

Map from the portal's Consent Status:
- `signed` → `signed`
- `not obtained` → `not_obtained`
- `verbal pending signature` → `not_obtained` (not yet final)
- `declined` → `declined`

### Coordinator Field

This is a string field indicating whether the patient belongs in the coordinator queue. Use `"yes"` or `"no"`. A patient belongs in the coordinator queue (`"yes"`) when:
- Enrollment is not `enroll` (any form of hold, review, or escalation)
- OR consent is anything other than `signed`
- OR renal flag = `yes` with elevated values

### Coordinator Queue

`coordinator_queue`: sorted list of patient IDs where coordinator = `"yes"`.

### Telehealth Preference

From the portal's "Telehealth Preference" field: `phone`, `video`, or `in-person`.

### Escalation Count

`escalation_count`: count of patients with `enrollment_decision` = `enroll_with_nurse_escalation`.

---

## Cross-Cutting Conventions

### Enum Discipline

Every field has a controlled vocabulary shown in the answer template as `value1|value2|value3`. Use ONLY these exact strings. Do not invent variants or use different casing.

### Sorted Arrays

All array fields containing IDs or enum strings must be sorted in ascending alphabetical order. This applies to: `blocked_reasons`, `missing_packet_items`, `stale_items`, `issue_codes`, `missing_sections`, `duplicate_linked_referral_ids`, `authorization_problem_transfers`, `confidentiality_problem_transfers`, `manual_review_patient_ids`, `follow_up_practices`, `coordinator_queue`, `pharmacy_network_statuses`.

### ID Ordering

Patient/transfer/referral rows must be sorted by ID ascending within their parent array. Aggregate arrays of IDs must also be sorted ascending.

### Null vs. Empty

- Use `null` for `follow_up_practice` when no practice needs follow-up (ready_to_schedule referrals).
- Use `[]` empty arrays for fields with no items (no blocked reasons, no missing items, no linked referrals).
- Use `""` empty string only when the template explicitly shows an empty string default.

### Date Handling

- The `review_date` field (when present in the template) should match the date provided in the task prompt.
- Freshness calculations for transfers use the requested start date, not the current date.
- The review date for benefits is the date on which eligibility is evaluated.

### Portal Badge Conventions

The portal uses CSS classes to indicate status:
- `badge good` / green — positive/complete/valid status (e.g. "active", "final", "signed", "sent")
- `badge warn` / amber — negative/incomplete/missing status (e.g. "inactive", "missing", "expired", "draft", "not started")
- `badge hot` / red — urgent/escalation status (e.g. "urgent", polypharmacy medications)
- `badge neutral` — informational status

Use the TEXT content of the badge, not the CSS class, for decision-making. However, the badge class can help quickly identify problematic fields during portal review (amber and red badges indicate issues).

### Medication-Managed Flag

The `Medication Managed` field on the patient detail page (`yes`/`no`) determines whether PBM and pharmacy gates are required. A `yes` means both PBM and pharmacy must pass. A `no` means these gates are `not_required`.

### Common Pitfalls

1. **Don't confuse chart "Created" with chart "Ready"** — a chart can exist but not be ready.
2. **Don't put expired/draft documents in stale_items** — stale_items is only for otherwise-usable items outside freshness windows.
3. **Don't add clinical_review_required when administrative gates are blocked** — it's redundant.
4. **Don't assume authorization is always required** — check if it's `not required` for some payers/plans.
5. **Don't assume all referrals are orthopedic** — check the service family and ICD-10 chapter.
6. **Smoking status "current" is a risk factor** — the portal may display it with a "good" CSS class, but clinically it's a negative indicator.
7. **"Verbal pending signature" for consent is NOT signed** — treat as `not_obtained` for consent outcome.
8. **Empty termination date means active coverage** — only consider coverage inactive/terminated if there's a termination date before the review date.
