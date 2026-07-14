# Northstar Care Intake Portal — Solver Skill

## Environment

- **Base URL**: `http://34.46.77.124:9013` (GDEV_EVO_ENV_BASE_URL). The task prompt contains a `<TASK_ENV_BASE_URL>` placeholder — substitute this URL.
- **Login credentials**: `intake.admin@northstar.example` / `Northstar-Intake-2026!`
- **Credentials are shared across all task types** — registration audit, transfer review, referral scheduling, chart onboarding, and chronic-care enrollment.

## Portal Interaction Habits

### Authentication
Navigate to the base URL. Look for a login form or sign-in link. Enter the email and password above. The portal should present a dashboard or navigation menu after login.

### Record Lookup
Every task provides a list of record IDs (e.g., `NSP-1008`, `TR-2604`, `REF-3106`, `CHR-2040`, `CCP-4107`). Use the portal's search or record-lookup feature to pull up each record individually.

### Information Gathering
Once on a record's detail page, inspect all visible tabs, sections, and linked sub-pages. Key areas to check:

- **Patient/record header**: demographics, ID, name, DOB, contact info, referring practice/provider
- **Insurance/PBM/Pharmacy panels**: status, network, effective dates, group/plan IDs
- **Clinical sections**: diagnosis codes, laterality markers, vitals (height, weight, BP, BMI), problem list, history
- **Documents/packet section**: uploaded items and their statuses (final, draft, expired, missing), dates
- **Authorization/consent panels**: signed status, valid-through dates, authorization numbers
- **Program/chart details**: program name, enrollment form status, orientation message state
- **Risk indicators**: any flagged clinical or lifestyle risk categories

### Dates and Freshness
Some items have effective dates or collection dates. Labs and infection screens are time-sensitive — compare their dates against the relevant reference date (requested start date, review date, or current date from the prompt). Items collected too long ago to be "current" are **stale** — still usable content but outside the freshness window.

## Business Rules by Task Domain

### 1. Patient Registration Audit (NSP-*)

**Gates**: Five gates must be assessed per patient:

| Gate | Values | What to check |
|------|--------|---------------|
| `medical_insurance` | `pass`, `block` | Insurance status active/inactive, in-network status |
| `pbm` | `pass`, `block`, `not_required` | Prescription benefit manager status active/inactive; `not_required` when the patient has no prescription benefits |
| `pharmacy` | `pass`, `block`, `not_required` | Preferred pharmacy in/out of network; `not_required` when no pharmacy gate applies |
| `demographics` | `pass`, `block` | All required demographic fields complete |
| `risk` | `low`, `moderate`, `high` | Clinical/lifestyle risk indicators shown on the record |

**Blocked reasons** (`insurance_inactive`, `insurance_out_of_network`, `pbm_inactive`, `pharmacy_out_of_network`, `demographics_incomplete`, `clinical_review_required`):
- Map gate failures to reasons:
  - `medical_insurance=block` → `insurance_inactive` or `insurance_out_of_network` (check which applies)
  - `pbm=block` → `pbm_inactive`
  - `pharmacy=block` → `pharmacy_out_of_network`
  - `demographics=block` → `demographics_incomplete`
  - `risk=high` → add `clinical_review_required` (this reason fires when risk is high, regardless of whether other gates are blocked or passing)
- `risk=moderate` or `risk=low` does NOT add `clinical_review_required` on its own.

**Overall decision**:
- `blocked` — any gate is `block` OR risk is `high` (risk=high alone forces blocked)
- `manual_review` — some borderline situation where no gate is explicitly blocked but something needs review (not seen in train_001 but in the enum; reserved for unclear cases)
- `ready` — all gates pass and risk is low or moderate

**Pharmacy network status** (`in_network`, `out_of_network`, `not_required`):
- `in_network` when pharmacy=pass
- `out_of_network` when pharmacy=block
- `not_required` when pharmacy=not_required or pbm=not_required

**Highest risk patient**: When multiple patients share the highest risk level, pick the one with the lexicographically greatest patient ID (last in sort order). If only one patient is `high`, that patient is the answer.

**Manual review patients**: Patients whose `overall_decision` is `manual_review`.

### 2. Dialysis Transfer Readiness (TR-*)

**Document packet items** (9 possible items): `labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, `transport note`.

Each item in the portal will have a status. Interpret as follows:
- **Missing/packet gap** (→ `missing_packet_items`): item is absent, marked draft, expired, or otherwise not final/usable.
- **Stale** (→ `stale_items`): item exists and is otherwise usable, but its collection date is outside the freshness window relative to the requested start date. Only `labs` and `infection screen` can appear in stale_items — these are the time-sensitive items. Other item types do not go here even if dated.
- **Complete**: item present, final, and current.

**Authorization and confidentiality** are special items that also get boolean flags:
- `authorization_valid`: `true` if the authorization item is present, final, and current; `false` otherwise (missing, draft, expired, or stale).
- `confidentiality_valid`: `true` if the confidentiality statement is present, final, and current; `false` otherwise.

**Decision** (hierarchical — check in this order):
1. `hold_missing_packet` — any missing_packet_items are present. This takes precedence over capacity concerns.
2. `hold_capacity` — packet is complete but start_compatibility is not `compatible` (i.e., `capacity_review` or `waitlist`).
3. `accept` — packet complete AND start_compatibility is `compatible`.

**Start compatibility** (`compatible`, `capacity_review`, `waitlist`):
- Derived from chair availability and requested start date shown on the transfer record.
- `compatible` — start date works with available capacity.
- `capacity_review` — may work but needs coordinator review.
- `waitlist` — no capacity at requested time.

**Route owner** (`referring_facility`, `capacity_coordinator`, `chart_prep`, `intake_complete`):
- `referring_facility` — when there are missing packet items (the referring facility must complete them).
- `capacity_coordinator` — packet is complete but start compatibility is not `compatible`.
- `chart_prep` — packet complete, start compatible, but chart prep not yet done.
- `intake_complete` — everything fully resolved.

**Authorization/confidentiality problem transfers**: List transfer IDs where the corresponding boolean is `false`. Sort ascending.

### 3. Orthopedic Referral Scheduling (REF-*)

**Coding checks** (three booleans):
- `chapter_valid`: the diagnosis code chapter is appropriate for orthopedics (check against the coding policy page in the portal if available).
- `narrative_match`: the clinical narrative text matches the coded diagnosis.
- `laterality_match`: the laterality (left/right/bilateral) in the diagnosis code matches what the narrative describes. If no laterality applies, this can be `true`.

**Issue codes** (any that apply):
- `invalid_chapter` — chapter_valid is false
- `diagnosis_mismatch` — narrative_match is false
- `laterality_mismatch` — laterality_match is false
- `missing_records` — required records not uploaded
- `missing_imaging` — required imaging not uploaded
- `authorization_gap` — authorization is missing, expired, or insufficient
- `duplicate_referral` — a duplicate link to another referral exists

**Readiness status** (pick the most actionable category):
- `duplicate_review` — when `duplicate_referral` is in issue_codes. This takes highest priority.
- `pending_records` — when `missing_records` or `missing_imaging` is present (and no duplicate).
- `coding_clarification` — when coding issues exist (`invalid_chapter`, `diagnosis_mismatch`, `laterality_mismatch`) and no higher-priority issue.
- `authorization_followup` — when `authorization_gap` is present and no higher-priority issue.
- `ready_to_schedule` — no issues at all.

**Priority tier** (depends on severity and urgency as displayed in the portal):
- `tier_1` — missing records/imaging, duplicates, or multiple serious issues. Highest urgency.
- `tier_2` — standalone authorization gaps with moderate urgency.
- `tier_3` — lower-urgency issues (e.g., simpler authorization follow-ups).
- `schedule` — ready to schedule (no issues).

The tier is influenced by the portal's urgency indicator, the number/type of issues, and any clinical priority flags.

**Duplicate linked referral IDs**: The referral ID(s) shown in the portal as duplicates of this record. Empty array if no duplicates.

**Follow-up practice**: The name of the referring practice that needs to be contacted (shown in the referral's referring provider/contact section). Use `null` if no follow-up is needed (e.g., ready_to_schedule).

### 4. Chart Onboarding (CHR-*)

**Missing sections**: Check these chart sections — `chart_not_created`, `demographics`, `history`, `problems`, `vitals`, `care_plan_or_instructions`, `orientation_message`. Any section that is absent, empty, or incomplete goes into `missing_sections`. Use `chart_not_created` only when the entire chart doesn't exist yet.

**Chart ready** (`true`/`false`): `true` when `missing_sections` is empty AND `problem_list_complete` is `true`. Any missing section or incomplete problem list → `false`.

**BMI class** (`not_available`, `normal`, `overweight`, `obese`):
- `not_available` — vitals are missing or height/weight data is absent.
- Otherwise, compute from height and weight shown in the vitals section and classify per standard BMI ranges.

**Orientation state** (`sent`, `queued`, `missing`, `draft`):
- Check the orientation communication status in the chart. This is a message/communication sent to the patient.
- `sent` — successfully delivered.
- `queued` — pending delivery.
- `draft` — created but not yet queued.
- `missing` — no orientation message exists.

**Next owner** (`registration_desk`, `clinical_intake`, `patient_communications`, `ready`):
- `registration_desk` — demographics are missing or incomplete.
- `clinical_intake` — clinical sections are missing (vitals, problems, history, care plan).
- `patient_communications` — orientation message is missing, draft, or queued (and no higher-priority clinical/registration issue).
- `ready` — chart is ready (no missing sections, problem list complete).

**Problem list complete** (`true`/`false`): Check whether the problem list section is fully populated vs. empty/incomplete.

### 5. Chronic-Care Program Enrollment (CCP-*)

**Proposed program**: The program name shown on the patient's chronic-care record (e.g., "Cardiometabolic Combo", "Hypertension Pathway", "Renal Risk Monitoring").

**Enrollment decision** (hierarchical — check in this order):
1. `hold_missing_consent` — consent is `not_obtained` or `declined` (regardless of what else is missing). Consent issues block everything.
2. `clinical_review` — consent is `signed` but clinical data items are missing (`diagnosis_support` or `recent_hba1c_or_bp`).
3. `hold_missing_form` — consent signed, clinical data present, but `program_form_complete` is missing.
4. `enroll_with_nurse_escalation` — everything complete but the patient has clinical flags requiring nurse oversight.
5. `enroll` — everything complete, no escalations needed.

**Missing items** (enum values: `diagnosis_support`, `recent_hba1c_or_bp`, `consent_signed`, `program_form_complete`):
- Map gaps found in the record to these item codes.
- `diagnosis_support` — supporting diagnosis documentation missing/inadequate.
- `recent_hba1c_or_bp` — recent lab values (HbA1c or blood pressure readings) not available.
- `consent_signed` — consent form not signed.
- `program_form_complete` — program enrollment form incomplete or missing.

**Follow-up cadence** (`weekly_nurse_call`, `biweekly_checkin`, `monthly_checkin`):
- Determined by the patient's risk level and program requirements shown in the portal.
- `weekly_nurse_call` — highest intensity (clinical risk flags, recent abnormal labs, nurse escalation).
- `biweekly_checkin` — moderate intensity.
- `monthly_checkin` — lowest intensity (stable patients).

**Consent outcome** (`signed`, `not_obtained`, `declined`):
- `signed` — consent form is signed and on file.
- `not_obtained` — consent hasn't been attempted/collected yet (different from declined).
- `declined` — patient actively declined consent.

**Coordinator**: The staff member name assigned to this patient's enrollment (e.g., "M. Okafor", "R. Alvarez", "S. Lin"). Shown in the portal record.

**Telehealth preference** (`phone`, `video`, `in-person`): The patient's stated preference for telehealth visits, as shown in the record.

**Coordinator queue**: All patient IDs that appear in the review, regardless of enrollment decision. Sorted ascending.

**Escalation count**: Number of patients with `enrollment_decision` = `enroll_with_nurse_escalation`.

## Output Conventions (All Task Types)

1. **Sorting**: Patient/transfer/referral rows sorted by their ID ascending (lexicographic). Within rows, string arrays (like `blocked_reasons`, `missing_packet_items`, `issue_codes`, `missing_items`) sorted alphabetically. ID arrays sorted ascending.

2. **Enums only**: Use exactly the enum string values shown in each task's answer template. Do not invent new values or use near-matches.

3. **No narrative**: The final JSON must contain only the keys in the answer template. Do not include evidence, reasoning, or extra fields.

4. **Empty arrays**: Use `[]` (not `null` or omitted) when no items apply to a list field.

5. **Null vs empty**: Fields like `follow_up_practice` use `null` when not applicable (the template uses `"practice name or null"`).

6. **Count fields**: `ready_count`, `accepted_count`, `escalation_count` are integer counts derived from the records. They are not subjective — count the records that meet the stated condition.

7. **Date fields**: `review_date` and similar date fields use the date from the task prompt in `YYYY-MM-DD` format.

8. **task_id**: Copy the `task_id` from the provided answer template. Do not change it.

## Pitfalls

- **Do not assume a record exists just because it has an ID** — always verify in the portal. A `chart_not_created` missing_section may apply.
- **Authorization gaps are common** — always check authorization validity dates against the reference date (review date or requested start date).
- **Consent has three states**, not two: signed, not_obtained (not yet collected), and declined (patient said no). They drive different decisions.
- **Stale ≠ missing** — a stale lab result is usable content but outside the freshness window. Missing means not present at all.
- **Risk=high alone can trigger blocked** in registration audits, even if all other gates pass. The `clinical_review_required` reason fires whenever risk is high.
- **Decision hierarchy matters** — in transfers, missing packet beats capacity; in enrollment, consent gaps beat clinical data gaps.
- **Laterality is independent of chapter/narrative validity** — a referral can have a valid chapter and matching narrative but still have a laterality mismatch.
- **Pharmacy and PBM are separate** — PBM is the prescription benefit manager (drug coverage), pharmacy is the preferred pharmacy network. A patient can pass one and block the other.
- **Follow-up practice names** are free-text from the portal, not from a controlled enum. Match them exactly as displayed.
- **Coordinator names** are free-text from the portal. Match them exactly as displayed.
- **Telehealth preference** is a free-text field from the portal patient record. Use the exact string shown (`phone`, `video`, `in-person`).
