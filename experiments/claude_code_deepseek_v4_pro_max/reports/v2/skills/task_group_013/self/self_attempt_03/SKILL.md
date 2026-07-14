# Northstar Care Intake Portal — Solver SOP

## Environment

- **Portal base URL**: Read from `environment_access.md` in the workspace root. This file is the sole authority on the remote environment URL.
- Do **not** use `localhost`, `127.0.0.1`, or any URL found in task prompt text if it conflicts with `environment_access.md`.
- Do **not** read or enter `env/`, `notes/`, `eval/`, test task directories, or prior run reports.
- Each solver attempt works inside a staged directory. The task prompt is at `input/prompt.txt`; the answer template is at `input/payloads/answer_template.json`. Write output to the path the task instructions specify.

## Authentication

All portal pages require login. Credentials (from task prompts):

- **Email**: `intake.admin@northstar.example`
- **Password**: `Northstar-Intake-2026!`

Use curl with cookie persistence:
```bash
curl -s -c /tmp/cookies.txt -b /tmp/cookies.txt \
  -d 'email=intake.admin@northstar.example&password=Northstar-Intake-2026!' \
  -L http://<BASE_URL>/login
```

The login redirects to `/dashboard`. Subsequent requests reuse the cookie jar.

## Portal Structure

| Section | URL | What it holds |
|---------|-----|---------------|
| Dashboard | `/dashboard` | Summary metrics + priority queue |
| Patients | `/patients` | 78 patient demographic + clinical records |
| Benefits | `/benefits` | Insurance, PBM, pharmacy network per patient |
| Pharmacies | `/pharmacies` | 8-pharmacy master list (network status) |
| Transfers | `/transfers` | 21 dialysis transfer records |
| Referrals | `/referrals` | 23 orthopedic/endocrine referral records |
| Charts | `/charts` | Chart readiness per patient |
| Programs | `/programs` | Chronic-care program enrollment records |
| Queue | `/queue` | 23 work items linking to business records |
| Documents | `/documents` | 4 SOP reference docs (no detail pages) |
| Policies | `/policies` | 5 policy statements (key business rules) |

**Cross-linking pattern**: Patient detail pages link to Benefits, Chart, and Program for that patient (`/benefits/<id>`, `/charts/<id>`, `/programs/<id>`). Transfers link to patients with NDT- prefix. Referrals may link to other referrals via `Linked Referral IDs`.

**ID prefix conventions**:
- `NSP-` — Northstar Patient (registration intake)
- `NDT-` — Dialysis Transfer patient
- `CHR-` — Chart record
- `CCP-` — Chronic-Care Program
- `REF-` — Referral
- `TR-` — Transfer
- `BEN-` — Benefits record (prefixed in Registration Links)
- `PBM-` / `PHR-` — PBM / Pharmacy links (no detail pages; data is on Benefits page)

## Badge Color System

The portal uses CSS badge classes as visual hints:

| Class | Color | Meaning |
|-------|-------|---------|
| `badge good` | Green | OK / active / complete / final / in-network |
| `badge warn` | Amber | Needs attention / missing / draft / expired / declined / not started |
| `badge hot` | Red | Critical / urgent (queue urgency, polypharmacy flag) |
| `badge neutral` | Gray | Informational / neutral |

Use badge colors as quick scan aids, but always read the actual field value — badge color can be misleading (e.g., "current" smoking may get a green badge because the data is verified, not because it's healthy).

---

# Domain 1: Patient Registration (NSP records)

**Train task**: `train_001` — audit new-patient registration readiness.
**Key policy**: POL-REG-01 on `/policies`.

## Data Collection

For each NSP patient, fetch:
1. `/patients/<id>` — demographics, clinical indicators, Medication Managed flag
2. `/benefits/<id>` — coverage, network, PBM, pharmacy network, preferred pharmacy
3. `/pharmacies` — verify preferred pharmacy is in-network (all 8 pharmacies except PH-007 Harbor Mail Order)

## Gate Rules

### medical_insurance (pass | block)
- **pass**: `Coverage Status` = `active` AND `Network Status` = `in network`
- **block**: Coverage is `inactive`, `terminated`, or `pending COB`; OR Network is `out of network` or `network exception needed`
- Per POL-REG-01: portal-verified eligibility snapshot is authoritative. A stale card image never overrides it.

### pbm (pass | block | not_required)
- **not_required**: `Medication Managed` = `no` on the patient record
- **pass**: Medication Managed = `yes` AND `Pbm Status` = `active`
- **block**: Medication Managed = `yes` AND Pbm Status is `inactive`, `not located`, or `pending`

### pharmacy (pass | block | not_required)
- **not_required**: Medication Managed = `no`
- **pass**: Medication Managed = `yes` AND `Pharmacy Network Status` = `in network`
- **block**: Medication Managed = `yes` AND Pharmacy Network Status = `out of network`

### demographics (pass | block)
Check the five patient Demographics fields: Address Complete, Consent Signed, Emergency Contact, Identity Verified, Phone Verified.
- **pass**: all five = `yes`
- **block**: any = `no`

### risk (low | moderate | high)
Assess from clinical indicators on the patient record. Risk escalators:
- **Daily alcohol** use
- **Current** smoking (note: may display with green badge — badge is about data verification, not clinical severity)
- **<60 min/week** exercise
- **Multiple chronic conditions** (especially Type 2 diabetes + another)
- **Polypharmacy**: 3+ medications, especially with `badge hot` (red)
- **Declined** or **due for seasonal** vaccination
- **Age** > 65
- **Renal Flag** = `yes` if a program record exists

Low: no chronic conditions or well-controlled single condition, good lifestyle indicators.
Moderate: one chronic condition + some lifestyle risk factors.
High: multiple chronic conditions, polypharmacy, daily alcohol, current smoking, declined vaccination.

## blocked_reasons (sorted array)

Use the enum strings from the answer template:
- `insurance_inactive` — Coverage Status is not `active`
- `insurance_out_of_network` — Network Status is not `in network`
- `pbm_inactive` — Pbm Status is not `active` (for medication-managed patients)
- `pharmacy_out_of_network` — Pharmacy Network Status is not `in network`
- `demographics_incomplete` — any demographics field = `no`
- `clinical_review_required` — risk = `high`

## overall_decision (ready | manual_review | blocked)
- **ready**: all gates pass AND risk = `low`
- **manual_review**: all gates pass but risk = `moderate`, OR a single non-critical block with moderate risk
- **blocked**: any gate is `block` (insurance inactive, out of network, demographics incomplete, PBM inactive) OR risk = `high`

## pharmacy_network_status (in_network | out_of_network | not_required)
Directly from Benefits `Pharmacy Network Status` field. Use `not_required` when Medication Managed = `no`.

## Output aggregation fields
- `ready_count`: count of patients with overall_decision = `ready`
- `highest_risk_patient_id`: patient with highest risk (high > moderate > low); if tie, pick the lower patient ID
- `manual_review_patient_ids`: sorted array of patient IDs with overall_decision = `manual_review`
- `pharmacy_network_statuses`: array of `{patient_id, status}` — sorted by patient_id ascending

---

# Domain 2: Dialysis Transfers (TR records)

**Train task**: `train_002` — audit seasonal dialysis transfer readiness.
**Key policy**: POL-REN-02 on `/policies`.

## Data Collection

For each TR transfer, fetch:
1. `/transfers/<id>` — all transfer fields including document packet
2. Optionally `/patients/<patient_id>` and `/benefits/<patient_id>` for coverage context

## Document Packet (9 items)

Every transfer detail page shows these 9 document types with Date, Source, and Status:
- `labs`
- `infection screen`
- `dialysis prescription`
- `medication list`
- `allergy list`
- `authorization`
- `confidentiality statement`
- `referring contact`
- `transport note`

## Document Status Values
- `received` — on file, usable
- `final` — finalized/approved
- `draft` — not final, not usable
- `expired` — beyond validity window, not usable
- `missing` — not present

## Freshness Windows (POL-REN-02)

Compute freshness relative to **Requested Start Date** (not today):
- **Labs**: current within **30 days** of requested start → (start_date - lab_date) ≤ 30 days
- **Infection screen**: current within **14 days** of requested start → (start_date - infection_date) ≤ 14 days
- **Dialysis prescription**: must be `final` status (not date-gated)

## Decision Logic

### missing_packet_items (sorted array)
Any document whose status is `missing`, `draft`, or `expired`. Use the document type names listed in the answer template (e.g., `labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, `transport note`).

### stale_items (sorted array)
Labs or infection screens that have status `received` or `final` BUT are dated outside their freshness window relative to the requested start date. Only labs and infection screens qualify for staleness — other document types do not.

### decision (accept | hold_missing_packet | hold_capacity)
- **accept**: zero `missing_packet_items`, zero `stale_items`, chair is `chair held` or `chair available, not held`, authorization is valid, confidentiality is valid
- **hold_missing_packet**: any missing/stale items exist (takes priority over capacity)
- **hold_capacity**: chair is `capacity review` or `waitlist`, and packet is otherwise complete

### start_compatibility (compatible | capacity_review | waitlist)
- **compatible**: chair is `chair held` or `chair available, not held` AND packet is complete
- **capacity_review**: chair is `capacity review`
- **waitlist**: chair is `waitlist`

### route_owner (referring_facility | capacity_coordinator | chart_prep | intake_complete)
- **referring_facility**: missing_packet_items exist (docs need to come from referring facility)
- **capacity_coordinator**: chair is `capacity review` or `waitlist`
- **chart_prep**: Chart Prep Status is `not started` or `in progress`
- **intake_complete**: everything ready — chart prep complete, chair available/held, all docs present

### authorization_valid (true | false)
True when the authorization document status is `final`. False when `missing`, `draft`, or `expired`.

### confidentiality_valid (true | false)
True when the confidentiality statement document status is `final`. False when `missing`, `draft`, or `expired`.

## Output aggregation fields
- `accepted_count`: count of transfers with decision = `accept`
- `authorization_problem_transfers`: sorted array of transfer IDs where authorization_valid = false
- `confidentiality_problem_transfers`: sorted array of transfer IDs where confidentiality_valid = false

---

# Domain 3: Orthopedic Referrals (REF records)

**Train task**: `train_003` — review orthopedic referral records for scheduling readiness.
**Key policy**: POL-REF-03 on `/policies`.

## Data Collection

For each REF referral, fetch:
1. `/referrals/<id>` — all referral fields
2. If `Linked Referral IDs` is non-empty, fetch those linked referrals too
3. `/policies` — POL-REF-03 for coding/duplicate rules

## Coding Checks (POL-REF-03)

Policy says: *"Scheduling requires an M-code or supported musculoskeletal diagnosis, agreement between narrative and laterality, required clinical records and imaging, and payer authorization when required."*

### chapter_valid (true | false)
Valid orthopedic chapters: **M-codes** (musculoskeletal), **S-codes** (injury/trauma).
Invalid for orthopedics: **E-codes** (endocrine/metabolic — e.g., E11.9 diabetes).

Check the first letter of the ICD-10 code.

### narrative_match (true | false)
The `Diagnosis Narrative` text should describe the same condition as the ICD-10 code. Examples:
- M17.11 ↔ "unilateral primary osteoarthritis, right knee" → true
- E11.9 ↔ "type 2 diabetes without complications" → true
- M17.11 ↔ "low back pain" → false (mismatch)

### laterality_match (true | false)
The `Laterality` field must agree with the diagnosis narrative and ICD-10 code:
- If laterality is `n/a` (for codes like E11.9 that are not side-specific), this is **true** (not a mismatch)
- If narrative mentions "right knee" but laterality is `left` → false
- If narrative mentions "bilateral" but laterality is `right` only → false
- Spine codes (M54.50) with laterality `spine` → true

## Issue Codes (sorted array)

Use these enum values:
- `invalid_chapter` — ICD-10 code not in a valid orthopedic chapter (e.g., E-code for orthopedics referral)
- `diagnosis_mismatch` — narrative_match = false
- `laterality_mismatch` — laterality_match = false
- `missing_records` — Records Received = `no`
- `missing_imaging` — Imaging Received = `no`
- `authorization_gap` — Authorization Status is `missing` or `pending` (not `approved` or `not required`)
- `duplicate_referral` — Linked Referral IDs is non-empty AND the duplicate hint is clinically meaningful

## Readiness Status

- **ready_to_schedule**: zero issue codes
- **pending_records**: issue includes `missing_records` or `missing_imaging`
- **coding_clarification**: issue includes `invalid_chapter`, `diagnosis_mismatch`, or `laterality_mismatch`
- **authorization_followup**: issue includes `authorization_gap`
- **duplicate_review**: issue includes `duplicate_referral`

If multiple issue categories apply, pick the most severe in the order: duplicate_review > coding_clarification > authorization_followup > pending_records.

## Priority Tier (schedule | tier_1 | tier_2 | tier_3)

Based on Urgency:
- `stat review` → **schedule** (highest)
- `urgent` → **tier_1**
- For `routine` readiness:
  - If ready_to_schedule → **tier_2**
  - If has issues → **tier_3**

## Follow-up Practice

If `readiness_status` is not `ready_to_schedule`, set to the practice name from the referral. If ready, set to `null`.

## Duplicate Handling

If `Linked Referral IDs` is non-empty, include those IDs in `duplicate_linked_referral_ids`. The `Duplicate Hints` field explains the match reason:
- `same physician only` — same referring physician, may or may not be a true duplicate
- `same condition within 30 days` — same ICD-10 within 30 days
- `similar name same DOB` — fuzzy name match with same date of birth
- `none` — no duplicate flag

## Output aggregation
- `ready_count`: count of referrals with readiness_status = `ready_to_schedule`
- `follow_up_practices`: sorted unique array of practice names needing follow-up (from non-ready referrals)

---

# Domain 4: Chart Onboarding (CHR records)

**Train task**: `train_004` — review chart onboarding readiness.
**Key policy**: POL-CHR-04 on `/policies`.

## Data Collection

For each CHR patient, fetch:
1. `/charts/<id>` — chart readiness fields (14 fields)
2. `/patients/<id>` — patient demographics and clinical context

## Readiness Checklist (POL-CHR-04)

Policy: *"A chart is ready only when demographics, history, applicable active problems, current vitals, onboarding care plan or clinical instructions, and orientation communication are complete."*

Six criteria, ALL must pass:

| # | Criterion | Field | Required Value |
|---|-----------|-------|----------------|
| 1 | Demographics | `Demographics Complete` | `yes` |
| 2 | History | `History Complete` | `yes` |
| 3 | Problems | `Problems Complete` | `yes` |
| 4 | Vitals | `Vitals.Current` | `yes` |
| 5 | Care Plan OR Clinical Instructions | `Care Plan` NOT missing/draft, OR `Clinical Instructions` NOT missing | Care Plan ∈ {`documented`} OR Clinical Instructions ∈ {`not needed`, `pending nurse edit`, `sent`} |
| 6 | Orientation | `Orientation Message` | `sent` |

**chart_ready** = (all 6 criteria = true)

## missing_sections (sorted array)

For each failed criterion, add the corresponding enum:
- `chart_not_created` — `Chart Created` ≠ `yes`
- `demographics` — `Demographics Complete` ≠ `yes`
- `history` — `History Complete` ≠ `yes`
- `problems` — `Problems Complete` ≠ `yes`
- `vitals` — `Vitals.Current` ≠ `yes`
- `care_plan_or_instructions` — both Care Plan is missing/draft AND Clinical Instructions is missing
- `orientation_message` — `Orientation Message` ≠ `sent`

## BMI Class

**BMI data is not directly displayed** on chart or patient detail pages (no height/weight fields). Set `bmi_class` to `not_available` for all patients unless height/weight appear in the portal data for that specific record.

If vitals data includes height/weight in a future version, compute: BMI = weight_kg / (height_m)², then classify:
- < 18.5 → underweight (not in current enum; use clinical judgment)
- 18.5–24.9 → normal
- 25–29.9 → overweight
- ≥ 30 → obese

## orientation_state (sent | queued | missing | draft)

Directly from the `Orientation Message` field on the chart detail page:
- `sent` (badge good)
- `queued` (badge neutral)
- `not sent` → map to `missing`
- Any other non-sent, non-queued value → `draft`

**Important**: The field values observed are `sent`, `queued`, and `not sent`. Map `not sent` to the template enum `missing`.

## next_owner (registration_desk | clinical_intake | patient_communications | ready)

- **registration_desk**: `demographics` is in missing_sections
- **clinical_intake**: `history`, `problems`, `vitals`, or `care_plan_or_instructions` is in missing_sections
- **patient_communications**: `orientation_message` is in missing_sections (and nothing else)
- **ready**: chart_ready = true

If multiple categories apply, use the first matching in the order above.

## problem_list_complete (true | false)

Directly from `Problems Complete` field: `yes` → true, `no` → false.

## Output aggregation
- `ready_count`: count of patients where chart_ready = true

---

# Domain 5: Chronic-Care Programs (CCP records)

**Train task**: `train_005` — review chronic-care program enrollment readiness.
**Key policy**: POL-CCP-05 on `/policies`.

## Data Collection

For each CCP patient, fetch:
1. `/programs/<id>` — all program fields
2. `/patients/<id>` — demographics, clinical context, Medication Managed
3. `/charts/<id>` — chart vitals and readiness context (optional but helpful for BP context)

## Enrollment Decision Logic (POL-CCP-05)

Policy: *"Diabetes and hypertension pathways require active diagnosis, recent labs or vitals, consent, and a complete program form. Renal risk changes cadence and may require nurse escalation."*

### Step-by-step determination:

**1. Check diagnosis support**: Active Diagnoses must include a condition matching the Proposed Program.
- `Cardiometabolic Combo` → expects Type 2 diabetes + Hypertension
- `Diabetes Pathway` → expects Type 2 diabetes
- `Hypertension Pathway` → expects Hypertension
- `Renal Risk Monitoring` → triggered by any diagnosis + Renal Flag = yes

If no matching diagnosis → `clinical_review`.

**2. Check labs/vitals**:
- Diabetes pathways require `Recent Hba1C` to have a value
- Hypertension pathways require `Bp` to be present
- If both HbA1c is empty and the diagnosis doesn't match → `clinical_review`

**3. Check consent**:
- `signed` → proceed
- `not obtained` or `verbal pending signature` → `hold_missing_consent`
- `declined` → `hold_missing_consent` (cannot proceed)

**4. Check program form**:
- `complete` → proceed
- `not started` or `incomplete` → `hold_missing_form`

**5. Check renal flag**:
- Renal Flag = `yes` AND all other gates pass → `enroll_with_nurse_escalation`
- Renal Flag = `no` AND all gates pass → `enroll`

**Priority**: consent issues > form issues > clinical_review > renal escalation > enroll. If multiple issues, report the first blocker in priority order.

### enrollment_decision values summary:
| Decision | Trigger |
|----------|---------|
| `enroll` | All gates pass, renal flag = no |
| `enroll_with_nurse_escalation` | All gates pass, renal flag = yes |
| `hold_missing_consent` | Consent not signed (not_obtained, verbal pending, declined) |
| `hold_missing_form` | Program Form is not_started or incomplete |
| `clinical_review` | Diagnosis mismatch, missing HbA1c + no BP, or insufficient clinical data |

## missing_items (sorted array)

Use these enum values:
- `diagnosis_support` — Active Diagnoses don't match Proposed Program pathway
- `recent_hba1c_or_bp` — HbA1c is empty/null (for diabetes pathways) or BP is absent
- `consent_signed` — Consent Status is not `signed`
- `program_form_complete` — Program Form Status is not `complete`

Only include items that contributed to the enrollment decision being something other than `enroll`.

## follow_up_cadence (weekly_nurse_call | biweekly_checkin | monthly_checkin)

- **weekly_nurse_call**: Renal Flag = yes AND (enrolled with nurse escalation OR medication adherence = poor OR HbA1c ≥ 9.0)
- **biweekly_checkin**: Renal Flag = yes (all other enrolled cases) OR HbA1c ≥ 8.0
- **monthly_checkin**: Standard stable enrollment (renal flag = no, HbA1c < 8.0)

If not enrolled (hold state), still determine the cadence that would apply if the hold were resolved.

## consent_outcome (signed | not_obtained | declined)

Map from the Consent Status field:
- `signed` → `signed`
- `not obtained` → `not_obtained`
- `verbal pending signature` → `not_obtained`
- `declined` → `declined`

## coordinator

Use the `Coordinator` field from the program record (e.g., "M. Okafor", "R. Alvarez").

## telehealth_preference

Use the `Telehealth Preference` field directly: `phone`, `video`, `in-person`, or `no preference`.

## Output aggregation
- `coordinator_queue`: sorted array of patient IDs where enrollment_decision is NOT `enroll` (i.e., needs coordinator attention)
- `escalation_count`: count of patients with enrollment_decision = `enroll_with_nurse_escalation`

---

# General Output Conventions

1. **Sorted arrays**: Always sort ID arrays ascending (string sort on IDs like "NSP-1008", "TR-2604").
2. **Enum values**: Use exactly the strings in the answer template. Do not invent new values or use different casing.
3. **No narrative**: Return only the JSON structure matching the answer template. Do not include explanations, evidence notes, or extra keys.
4. **Boolean fields**: Use JSON `true`/`false`, not strings.
5. **Null fields**: Use JSON `null` for absent values (e.g., follow_up_practice when ready).
6. **Empty arrays**: Use `[]` when there are no items, not `null` or omission.
7. **task_id**: Must match the task identifier from the prompt (e.g., `"train_001"`).
8. **review_date**: When the template includes a date field, use the date specified in the task prompt.

# Common Pitfalls

1. **Stale card images**: POL-REG-01 says "A stale card image never overrides verified portal status." The `Card Image Status` field on benefits is informational only — rely on `Coverage Status` and `Network Status` for gate decisions.

2. **Badge vs. value**: Badge CSS classes are visual hints, not data. Always parse the text value, not the CSS class. "Current" smoking with a green badge is still a risk factor.

3. **Freshness windows use requested start date**: For transfers, compute lab/infection screen freshness relative to the `Requested Start Date`, not the current date.

4. **Missing vs. stale**: "Missing" means not obtained. "Expired" means obtained but no longer valid. "Stale" means obtained and usable but dated outside the freshness window. Only labs and infection screens can be stale — other docs are either present/valid or missing/expired/draft.

5. **E-codes for orthopedics**: ICD-10 codes starting with 'E' are endocrine/metabolic, not musculoskeletal. For orthopedic referrals, E-codes mean `chapter_valid = false` and `invalid_chapter` issue.

6. **Laterality 'n/a' is not a mismatch**: When laterality is `n/a` (e.g., for E11.9 diabetes), `laterality_match` should be `true`, not false.

7. **Pharmacy network is on the benefits page**: There are no separate PBM/PHR detail pages. PBM and pharmacy data are embedded in the `/benefits/<id>` record.

8. **Chart care plan OR clinical instructions**: Policy POL-CHR-04 uses "care plan or clinical instructions" — only ONE needs to be complete, not both. "not needed" for clinical instructions counts as complete (it means none are required).

9. **Program form "incomplete" may show green badge**: The Program Form Status value "incomplete" sometimes renders with a green badge. Parse the text value, not the color.

10. **Consent "declined" blocks enrollment**: A declined consent is a hard block — the patient cannot be enrolled. This is different from "not obtained" which may be remediable.

11. **Demographics gate uses patient page fields**: The 5 demographics fields (Address Complete, Consent Signed, Emergency Contact, Identity Verified, Phone Verified) come from the patient detail page, not the chart's Demographics Complete field. These are two different data points.

12. **Queue items are context, not answers**: Queue items linked to your task records provide helpful context (urgency, current owner), but don't let them override what you see on the actual business record detail page.

13. **Transfer document list is exhaustive**: All 9 document types must be checked. The answer template's enum list for packet items is authoritative — use those exact names.

14. **Risk assessment is multi-factor**: Don't rely on a single clinical indicator. Weigh the combination of lifestyle factors, chronic conditions, medication burden, vaccination status, and age together.
