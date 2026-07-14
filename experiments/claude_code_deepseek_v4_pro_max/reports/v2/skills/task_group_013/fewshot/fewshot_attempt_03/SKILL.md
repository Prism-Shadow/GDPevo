# Northstar Care Intake Portal — Solver Skill

## Environment

- **Base URL:** `http://34.46.77.124:9013`
- **Login email:** `intake.admin@northstar.example`
- **Login password:** `Northstar-Intake-2026!`
- Do not use localhost, 127.0.0.1, or run any env/setup scripts. The remote URL above is the only entrypoint.

## Credential & Session Habits

- The portal uses a single shared admin account across all task types. Login once per session; the session cookie persists across requests.
- If the portal redirects to a login page, POST the credentials to the login endpoint and capture the session cookie before proceeding to task pages.

## Portal Navigation Conventions

- Patient/transfer/referral/chart/program records are accessed by their ID through the portal UI. Each ID prefix maps to a distinct module:
  - `NSP-XXXX` — new patient registration records
  - `TR-XXXX` — seasonal dialysis transfer records
  - `REF-XXXX` — orthopedic referral records
  - `CHR-XXXX` — patient chart onboarding records
  - `CCP-XXXX` — chronic-care program enrollment records
- The portal typically presents a list/dashboard view and a detail view per record. Navigate to the detail page for each ID listed in the task prompt.
- When a record page has tabs or sections (demographics, insurance, pharmacy, clinical, documents, etc.), inspect every visible section — gates and statuses may span multiple tabs.

## Output Schema Rules (All Task Types)

### Structure
- Match the answer template exactly: no extra keys, no missing keys.
- Return only the JSON object — no markdown fences, no narrative, no evidence notes.
- Use only the enum string values listed in the template's pipe-delimited alternatives. Do not invent new values.

### Array Ordering
- Patient/transfer/referral rows: **sort by the record ID ascending** (e.g., `NSP-1008` before `NSP-1014`).
- String arrays within a row (e.g., `blocked_reasons`, `missing_packet_items`, `issue_codes`, `missing_sections`, `missing_items`): **sort alphabetically**.
- Top-level ID arrays (e.g., `manual_review_patient_ids`, `authorization_problem_transfers`, `coordinator_queue`): **sort ascending by ID**.
- Top-level string arrays (e.g., `follow_up_practices`): **sort alphabetically, deduplicated**.

### Aggregation Fields
- `ready_count` / `accepted_count`: integer count of records where the primary decision is the positive outcome (`ready`, `ready_to_schedule`, `accept`, chart `chart_ready: true`).
- `escalation_count`: count of records with `enroll_with_nurse_escalation` decision.
- `highest_risk_patient_id`: when multiple patients share the same highest risk level, **return the highest (lexicographically last) patient ID** among them.
- `manual_review_patient_ids`: include every patient whose `overall_decision` is `manual_review` (empty array if none).
- `authorization_problem_transfers` / `confidentiality_problem_transfers`: include every transfer where the corresponding boolean is `false`.

### Null vs Empty
- `follow_up_practice`: use the practice name string when follow-up is needed; otherwise use `null` (not the empty string).
- Empty arrays use `[]`, never `null`.

## Task-Specific Business Rules

### Task Type A: Patient Registration Audit (NSP-XXXX)

**Gate evaluation.** Each patient has five gates. Read the portal record to determine each gate's status:
| Gate | `pass` conditions | `block` conditions |
|---|---|---|
| `medical_insurance` | Active, in-network coverage | Inactive policy, or out-of-network |
| `pbm` | Active PBM (prescription benefit) | Inactive PBM; use `not_required` only when the record explicitly states no PBM applies |
| `pharmacy` | Preferred pharmacy in network | Pharmacy out of network; `not_required` when no pharmacy linkage exists |
| `demographics` | All required demographic fields complete | Missing or incomplete fields |
| `risk` | — | Risk is `low`, `moderate`, or `high` (not pass/block — this is a level, not a binary gate) |

**Blocked reasons derivation.** Map gate failures to reason codes:
- `medical_insurance: block` → `insurance_inactive` (if policy is inactive) or `insurance_out_of_network` (if active but out-of-network)
- `pbm: block` → `pbm_inactive`
- `pharmacy: block` → `pharmacy_out_of_network`
- `demographics: block` → `demographics_incomplete`
- `risk: high` → `clinical_review_required` (always added when risk is high, regardless of other gates)
- `risk: moderate` or `risk: low` → no reason code by itself

**Overall decision:**
- Any gate is `block` → `blocked`
- All gates `pass`, risk is `low` or `moderate` → `ready`
- All gates `pass`, risk is `high` → `manual_review` (inference: clinical concern without an administrative block)

**Pharmacy network status** mirrors the pharmacy gate: if pharmacy is `pass`, status is `in_network`; if `block`, status is `out_of_network`; if `not_required`, status is `not_required`.

**pharmacy_network_statuses** top-level array: one entry per patient, sorted by patient_id ascending, with the `status` field for each.

### Task Type B: Dialysis Transfer Readiness (TR-XXXX)

**Packet items.** The nine defined document names are the universe for both `missing_packet_items` and `stale_items`:
`labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, `transport note`.

**missing_packet_items:** Include any document that is absent, in draft state, expired, or otherwise not finalized/usable. Do NOT include items that are present and valid but merely stale — those go in `stale_items`.

**stale_items:** Restricted to `labs` and `infection screen` only. If a lab result or infection screen is present and otherwise usable but its date falls outside the freshness window relative to the requested start date, list it here. Other stale documents (e.g., old medication list) are not classified as "stale" — if expired, they go in `missing_packet_items`.

**Decision logic:**
- All packet items present and valid, no stale concerns, chair available on requested date → `accept`
- Any missing packet items → `hold_missing_packet`
- Packet complete but no chair capacity → `hold_capacity`

**start_compatibility:**
- Chair available on the requested start date → `compatible`
- Chair availability uncertain or needs coordinator check → `capacity_review`
- No availability, patient must wait → `waitlist`

**route_owner:**
- `referring_facility` — when information or documents are still needed from the referring facility (missing packet items, invalid authorization/confidentiality)
- `capacity_coordinator` — when start compatibility is `capacity_review` or `waitlist` and packet is otherwise complete
- `chart_prep` — when packet is complete and start is compatible but chart preparation is pending
- `intake_complete` — when decision is `accept`

**authorization_valid / confidentiality_valid:** Booleans read directly from the portal record. These drive the top-level `authorization_problem_transfers` and `confidentiality_problem_transfers` arrays.

### Task Type C: Orthopedic Referral Scheduling (REF-XXXX)

**Coding validation:**
- `chapter_valid`: the diagnosis code's chapter matches the referral's clinical area (orthopedics). `false` when the code belongs to a different ICD chapter.
- `narrative_match`: the clinical narrative text supports the coded diagnosis. `false` when the description contradicts or is unrelated to the code.
- `laterality_match`: the laterality (left/right/bilateral) in the referral matches the laterality in the diagnosis coding. `false` on mismatch.

**Issue codes** are derived from inspection findings:
- `invalid_chapter` — chapter_valid is false
- `diagnosis_mismatch` — narrative_match is false
- `laterality_mismatch` — laterality_match is false
- `missing_records` — required prior records not present
- `missing_imaging` — required imaging studies not present
- `authorization_gap` — authorization is missing, expired, or insufficient
- `duplicate_referral` — portal flags this as a duplicate of another referral

**readiness_status** is the top-level status that best characterizes the referral's blocker:
- Any coding problem (`invalid_chapter`, `diagnosis_mismatch`, `laterality_mismatch`) → `coding_clarification`
- `duplicate_referral` present → `duplicate_review`
- `authorization_gap` present (without coding or duplicate issues) → `authorization_followup`
- `missing_records` or `missing_imaging` present (without coding/duplicate) → `pending_records`
- No issues → `ready_to_schedule`
- When multiple issue categories apply, use the most severe/blocking: duplicate > coding > authorization > records. (From examples: REF-3118 has authorization_gap + missing_records → pending_records, suggesting records takes priority over auth; but REF-3106 has only authorization_gap → authorization_followup. The hierarchy appears to be: duplicate_review takes precedence when duplicate_referral is present; otherwise prioritize by the issue that blocks scheduling most directly.)

**priority_tier:**
- `schedule` — ready_to_schedule referrals
- `tier_1` — highest urgency non-ready referrals (e.g., missing imaging, duplicate requiring immediate resolution)
- `tier_2` — moderate urgency (e.g., authorization follow-up, missing records)
- `tier_3` — lower urgency

**duplicate_linked_referral_ids:** Populate with the IDs of any referrals the portal links as duplicates. Empty array if none.

**follow_up_practice:** The referring practice name if the referral needs follow-up (any status other than `ready_to_schedule`). Use `null` if ready to schedule with no follow-up needed.

**follow_up_practices top-level:** Sorted unique list of all practice names from referrals that have a non-null `follow_up_practice`.

### Task Type D: Chart Onboarding (CHR-XXXX)

**chart_ready:** `true` only when `missing_sections` is empty and all required sections are complete.

**missing_sections:** Sorted array of section identifiers drawn from: `chart_not_created`, `demographics`, `history`, `problems`, `vitals`, `care_plan_or_instructions`, `orientation_message`. A chart that doesn't exist yet should have `chart_not_created` as its only missing section (or alongside other missing sections if the record exists but chart creation is incomplete).

**bmi_class:** `not_available` when vitals are missing or BMI cannot be computed. Otherwise: `normal` (18.5–24.9), `overweight` (25–29.9), `obese` (≥30).

**orientation_state:**
- `sent` — orientation materials have been sent to the patient
- `queued` — materials queued but not yet sent
- `draft` — materials in draft, not finalized
- `missing` — no orientation communication exists

**next_owner:**
- `registration_desk` — demographics or basic registration incomplete
- `clinical_intake` — clinical sections (history, problems, vitals, care plan) incomplete
- `patient_communications` — orientation_message missing or orientation not sent
- `ready` — chart is fully ready for onboarding

**problem_list_complete:** Boolean from portal indicating whether the problem list section is fully populated.

### Task Type E: Chronic-Care Program Enrollment (CCP-XXXX)

**Fields read from portal:**
- `proposed_program`: The program name shown on the patient's record (e.g., "Cardiometabolic Combo", "Hypertension Pathway", "Renal Risk Monitoring").
- `coordinator`: The assigned care coordinator's name as displayed (e.g., "M. Okafor", "R. Alvarez").
- `telehealth_preference`: The patient's stated preference — `phone`, `video`, or `in-person`.

**enrollment_decision:**
- All required items present, consent signed, no clinical flags → `enroll`
- All items present, consent signed, but a clinical flag (e.g., borderline labs) requires nurse attention → `enroll_with_nurse_escalation`
- Consent not obtained or declined → `hold_missing_consent`
- Program form incomplete → `hold_missing_form`
- Diagnosis support or clinical data insufficient → `clinical_review`
- When multiple blockers exist, the more severe condition takes precedence. From examples: missing consent + missing form → `hold_missing_consent`. Missing diagnosis support + missing form → `clinical_review`.

**missing_items:** Drawn from: `diagnosis_support`, `recent_hba1c_or_bp`, `consent_signed`, `program_form_complete`. Only list items that are actually missing or insufficient. Sorted alphabetically.

**follow_up_cadence:**
- `weekly_nurse_call` — highest acuity (clinical flags, escalations)
- `biweekly_checkin` — moderate need (consent follow-up, form completion)
- `monthly_checkin` — stable, routine monitoring

**consent_outcome:**
- `signed` — consent form is signed and on file
- `not_obtained` — consent has been requested but not yet returned
- `declined` — patient has explicitly declined to sign

**coordinator_queue:** Include every patient ID from the review (regardless of decision). Sort ascending.

**escalation_count:** Number of patients with `enroll_with_nurse_escalation`.

## General Portal Interaction Habits

1. **Login first.** Before fetching any record, authenticate. The portal may show a login page or return a 302 redirect.
2. **Fetch each record individually.** Navigate to each patient/transfer/referral/chart/program ID's detail page. Do not assume data from the list view is complete — the detail view often contains additional sections.
3. **Inspect all tabs/sections.** Clinical data, documents, authorizations, and communications may be on separate sub-pages. Follow links/tabs within a record to ensure no section is missed.
4. **Dates are local.** The portal displays dates in `YYYY-MM-DD` format. Compare item dates against the requested start date or review date (given in the prompt) to determine staleness.
5. **Presence vs validity.** A document may be listed (present) but in draft or expired state — treat it as missing. Check status indicators, not just the document name appearing in a list.
6. **Boolean flags.** Authorization and confidentiality validity are typically shown as status badges or checkmarks. Read the actual status, don't infer from document presence alone.
7. **Duplicate detection.** The portal may display a "duplicate of" link or badge. Capture the linked referral ID from that indicator.

## Pitfalls

- **Don't infer pass from absence of block.** A gate may have a third state (`not_required` for pbm/pharmacy). Read the explicit status from the portal.
- **Don't mix stale and missing.** A stale lab is still present and readable — it belongs in `stale_items`, not `missing_packet_items`. A missing lab (never submitted) goes in `missing_packet_items`.
- **Don't omit empty arrays.** If a patient has no blocked reasons, use `[]`, not `null` and not omitting the key.
- **Sort consistently.** Alphanumeric/lexicographic sort for IDs and enum strings. Do not use natural sort or case-insensitive sort unless the IDs are mixed-case (they aren't — all IDs use uppercase prefix + digits).
- **risk is not pass/block.** The `risk` gate uses `low|moderate|high`, not `pass|block`. It's the only gate that uses severity levels instead of binary status.
- **Authorization/confidentiality are separate concerns.** A transfer can have `authorization_valid: true` but `confidentiality_valid: false`. Check both independently.
- **ready_count counts the positive decision.** For patient registration it's `overall_decision: ready`. For charts it's `chart_ready: true`. For transfers it's `decision: accept`. For referrals it's `readiness_status: ready_to_schedule`. For chronic-care it's `enrollment_decision: enroll` (not enroll_with_nurse_escalation).
- **Don't fabricate practice names.** Read the referring practice name from the portal record exactly as displayed. If none is shown, use `null`.
- **coordinator_queue includes all reviewed patients** in the chronic-care task, not only those with issues.
- **BMI class requires vitals.** If the vitals section is missing, bmi_class must be `not_available`.
