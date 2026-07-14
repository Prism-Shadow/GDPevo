# Northstar Care Intake Portal — Solver Skill

## Environment

- **Base URL**: `http://34.46.77.124:9013`
- **Override rule**: Ignore any localhost/127.0.0.1 or `<TASK_ENV_BASE_URL>` references in task prompts. Always use the base URL above.
- **Credentials**: `intake.admin@northstar.example` / `Northstar-Intake-2026!`
- **Auth**: The portal uses session-based authentication. Begin every solve by authenticating (POST to `/login` or equivalent with the credentials above) and retain the session cookie for all subsequent requests.

## Portal API Exploration Strategy

The portal exposes RESTful JSON endpoints. On first contact with a new task type, explore:

1. **List endpoints** — Try `GET /patients`, `GET /transfers`, `GET /referrals`, `GET /charts`, `GET /programs`, or similar plural resource paths to discover available records.
2. **Detail endpoints** — Once you have an ID prefix (e.g., `NSP-1008`), fetch the individual record: `GET /patients/NSP-1008` or `GET /patients/1008`. Try both the full ID and the numeric portion.
3. **Related sub-resources** — Many records have nested detail pages. Check paths like `/{resource}/{id}/demographics`, `/{resource}/{id}/insurance`, `/{resource}/{id}/documents`, `/{resource}/{id}/coding`, etc. Walk every link or reference returned in the parent record.
4. **Policy/config pages** — Some task prompts mention "policy/context pages." These are shared reference endpoints (e.g., `/policies/freshness`, `/policies/chapters`) that define rules applied across all records. Always check for these when the task mentions freshness windows, chapter validity, or network definitions.

## General API Interaction Habits

- Use `curl` with `-s` (silent) and pipe through `jq` for readable output. Always include `-c` or `-b` for cookie jar/session persistence.
- The portal returns JSON. Field names are `snake_case`.
- IDs are strings, not integers. Always quote them in JSON output.
- When a record references another entity by ID, follow that link — the referenced record often contains gate/status data you need.

## Task Type Reference

The portal handles five distinct workflows. Each has its own record prefix, endpoints, and decision logic.

### 1. Patient Intake Registration (prefix: `NSP-`)

**What to inspect per patient:**
- Demographics completeness (name, DOB, address, contact)
- Medical insurance status (active/inactive, in-network/out-of-network)
- PBM / prescription benefit status
- Preferred pharmacy network status
- Clinical risk indicators and lifestyle risk flags

**Gate logic:**
| Gate | Pass condition | Block condition |
|---|---|---|
| `medical_insurance` | Active AND in-network | Inactive OR out-of-network |
| `pbm` | Active | Inactive; use `not_required` when no PBM applies |
| `pharmacy` | In-network preferred pharmacy | Out-of-network; use `not_required` when no pharmacy applies |
| `demographics` | All required fields present and valid | Missing or invalid fields |
| `risk` | `low` / `moderate` / `high` — always populated; not a pass/block gate per se |

**Decision rules:**
- **`overall_decision` = `ready`**: ALL of medical_insurance, pbm, pharmacy, demographics are `pass`, and risk is NOT `high`.
- **`overall_decision` = `blocked`**: Any gate is `block`, OR risk is `high` (which adds `clinical_review_required` to blocked_reasons).
- **`overall_decision` = `manual_review`**: This value exists in the template enum but did not appear in any train example. Use it only when the portal record itself indicates a manual-review disposition or when the record's state doesn't cleanly fit the `ready`/`blocked` binary (e.g., soft warnings without hard blocks). Do not invent it — the portal record or its status fields should signal when it applies.

**Blocked reasons mapping:**
- `insurance_inactive` ↔ medical_insurance block (inactivity)
- `insurance_out_of_network` ↔ medical_insurance block (network)
- `pbm_inactive` ↔ pbm block
- `pharmacy_out_of_network` ↔ pharmacy block
- `demographics_incomplete` ↔ demographics block
- `clinical_review_required` ↔ risk = `high`

**`pharmacy_network_status`** is reported per patient independently of the pharmacy gate. It reflects whether the patient's preferred pharmacy is `in_network` or `out_of_network`. Use `not_required` if the patient has no pharmacy benefit.

**Summary fields:**
- `ready_count`: count of patients with `overall_decision == "ready"`
- `highest_risk_patient_id`: single patient ID with the highest risk level. If tied, use the highest (lexicographically last) patient ID among those tied.
- `manual_review_patient_ids`: sorted list of patient IDs with `overall_decision == "manual_review"`
- `pharmacy_network_statuses`: array of `{patient_id, status}` for every patient, sorted by patient_id

### 2. Dialysis Transfer (prefix: `TR-`)

**Document packet items** (the full universe of possible items):
`labs`, `infection screen`, `dialysis prescription`, `medication list`, `allergy list`, `authorization`, `confidentiality statement`, `referring contact`, `transport note`

**Stale vs. missing:**
- **`missing_packet_items`**: Items that are entirely missing, in draft status, expired, or otherwise not final/usable. Exclude items that exist but are stale (those go in `stale_items` instead).
- **`stale_items`**: Labs or infection screens that ARE present and usable in structure but fall outside the **freshness window** relative to the requested start date. Only these two item types can be stale; all other items are either present-and-valid or missing. Check a policy/freshness endpoint or the transfer detail page for the window duration.

**Other per-transfer fields:**
- **`authorization_valid`**: boolean — is the authorization document present, signed, and current?
- **`confidentiality_valid`**: boolean — is the confidentiality statement present, signed, and current?
- **`start_compatibility`**: Evaluated against chair availability on the requested start date:
  - `compatible` — chairs available
  - `capacity_review` — limited availability, coordinator must review
  - `waitlist` — no chairs available on that date
- **`route_owner`**: Who currently owns the next action:
  - `referring_facility` — missing packet items need action from the referrer
  - `capacity_coordinator` — capacity issue needs resolution
  - `chart_prep` — chart preparation is pending
  - `intake_complete` — nothing left to do (terminal state)

**Decision logic:**
- `accept` — packet complete, start compatible, auth and confidentiality both valid
- `hold_missing_packet` — one or more missing or stale packet items
- `hold_capacity` — packet is fine but start is not compatible (capacity_review or waitlist)

When both packet issues AND capacity issues exist, `hold_missing_packet` takes precedence (the packet must be resolved before capacity matters).

**Summary fields:**
- `accepted_count`: count of transfers with decision `accept`
- `authorization_problem_transfers`: sorted list of transfer IDs where `authorization_valid == false`
- `confidentiality_problem_transfers`: sorted list of transfer IDs where `confidentiality_valid == false`

### 3. Orthopedic Referral (prefix: `REF-`)

**What to inspect per referral:**
- Coding chapter validity (procedure codes map to correct ICD-10 chapter for orthopedics)
- Narrative-to-diagnosis match (does the clinical narrative support the coded diagnosis?)
- Laterality consistency (left/right/bilateral matches throughout the record)
- Records and imaging status (are required priors and images attached?)
- Authorization status (is prior auth on file and current?)
- Duplicate check (does this referral duplicate an existing one?)
- Urgency / priority indicators
- Referring practice contact information

**Coding validation:**
- `chapter_valid`: The procedure chapter code belongs to the orthopedic/musculoskeletal chapter range. Check against a chapter policy endpoint or reference table in the portal.
- `narrative_match`: The free-text clinical narrative describes a condition consistent with the coded diagnosis.
- `laterality_match`: The laterality modifier on the procedure code matches the laterality in the narrative and imaging.

**`readiness_status` decision tree:**
- `ready_to_schedule` — no issues at all
- `pending_records` — missing records or missing imaging (with or without other issues)
- `coding_clarification` — chapter invalid, diagnosis mismatch, or laterality mismatch (any coding issue), and no missing records/imaging
- `authorization_followup` — only an authorization gap (no coding or records issues)
- `duplicate_review` — duplicate flag is set, regardless of other issues

**Issue codes** — include ALL that apply:
- `invalid_chapter` ↔ `chapter_valid == false`
- `diagnosis_mismatch` ↔ `narrative_match == false`
- `laterality_mismatch` ↔ `laterality_match == false`
- `missing_records` ↔ required prior records not attached
- `missing_imaging` ↔ required imaging not attached
- `authorization_gap` ↔ authorization missing, expired, or insufficient
- `duplicate_referral` ↔ referral is flagged as a duplicate

**`duplicate_linked_referral_ids`**: When `duplicate_referral` is present, list the referral IDs that this one duplicates. Empty array otherwise.

**Priority tier assignment:**
- `schedule` — `ready_to_schedule`
- `tier_1` — highest urgency (combines clinical urgency + blocked status)
- `tier_2` — medium urgency
- `tier_3` — lowest urgency

Priority is derived from a combination of the readiness_status severity and any urgency markers in the referral. When in doubt, check the referral detail for an explicit priority or urgency field.

**`follow_up_practice`**: The name of the referring practice that needs to be contacted. Use the exact practice name string from the portal. Set to `null` (JSON null, not the string "null") when no follow-up is needed (e.g., `ready_to_schedule`).

**Summary fields:**
- `ready_count`: count of referrals with `readiness_status == "ready_to_schedule"`
- `follow_up_practices`: deduplicated, alphabetically sorted list of non-null practice names across all referrals

### 4. Chart Onboarding (prefix: `CHR-`)

**Chart sections that can be missing:**
`chart_not_created`, `demographics`, `history`, `problems`, `vitals`, `care_plan_or_instructions`, `orientation_message`

A chart can exist (have a record) without being ready. `chart_not_created` means the chart record itself doesn't exist yet.

**Key fields:**
- **`chart_ready`**: `true` only when `missing_sections` is empty AND all required data is present and valid.
- **`problem_list_complete`**: Independent boolean — a chart can have the problems section present but incomplete. Check specifically whether the problem list has active diagnoses populated.
- **`bmi_class`**: `not_available` when vitals are missing or height/weight aren't recorded; otherwise `normal`, `overweight`, or `obese` based on standard BMI thresholds.
- **`orientation_state`**: Status of the patient orientation/welcome communication:
  - `sent` — delivered to patient
  - `queued` — queued for delivery but not yet sent
  - `draft` — created but not finalized
  - `missing` — no orientation communication exists
- **`next_owner`**: Who owns the next action:
  - `registration_desk` — demographics or basic info missing
  - `clinical_intake` — clinical sections (history, problems, vitals, care plan) incomplete
  - `patient_communications` — orientation message is missing or draft (and clinical is fine)
  - `ready` — chart is complete and orientation is sent

**Summary field:**
- `ready_count`: count of patients with `chart_ready == true`

### 5. Chronic-Care Program Enrollment (prefix: `CCP-`)

**What to inspect per patient:**
- Proposed program name (free text from the record)
- Consent form status (signed, not obtained, declined)
- Program enrollment form completeness
- Clinical support: diagnosis documentation, recent HbA1c or BP readings
- Telehealth preference
- Assigned coordinator

**Decision rules:**
- `enroll` — all items present, consent signed, clinical support adequate
- `enroll_with_nurse_escalation` — all items present and consent signed, but clinical values (HbA1c, BP) are outside target range and need nurse follow-up. This counts toward `escalation_count`.
- `hold_missing_consent` — consent is `not_obtained` or `declined`. In both cases, `consent_signed` goes in `missing_items` because a signed consent form is required regardless of the reason it's absent. The `consent_outcome` field captures the distinction between "never obtained" and "actively declined."
- `hold_missing_form` — program form is incomplete; `program_form_complete` goes in `missing_items`
- `clinical_review` — clinical support is insufficient (`diagnosis_support` or `recent_hba1c_or_bp` missing or inadequate). This takes precedence over consent/form issues when clinical necessity is unproven.

**When multiple issues exist**, the decision hierarchy is: `clinical_review` > `hold_missing_consent` > `hold_missing_form`. Report ALL missing_items regardless of which decision was chosen.

**`missing_items`** (sorted alphabetically):
- `diagnosis_support` — no supporting diagnosis documentation
- `recent_hba1c_or_bp` — HbA1c or BP readings are missing or too old
- `consent_signed` — consent not obtained (only when `consent_outcome == "not_obtained"`)
- `program_form_complete` — program enrollment form is incomplete or missing

**Other per-patient fields:**
- `follow_up_cadence`: derived from clinical urgency and program type. Check the record for an explicit cadence recommendation.
- `coordinator`: The assigned coordinator's name exactly as shown in the portal (e.g., "M. Okafor", "R. Alvarez", "S. Lin").
- `consent_outcome`: `signed`, `not_obtained`, or `declined`
- `telehealth_preference`: `phone`, `video`, or `in-person`

**Summary fields:**
- `coordinator_queue`: sorted list of ALL patient IDs that have an assigned coordinator (i.e., the `coordinator` field is non-empty). Include every patient regardless of decision.
- `escalation_count`: count of patients with `enrollment_decision == "enroll_with_nurse_escalation"`

## Output Format Conventions (All Tasks)

1. **Sort order**: All record arrays sorted ascending by the primary ID field (`patient_id`, `transfer_id`, `referral_id`). All string arrays sorted alphabetically.
2. **Enums**: Use EXACTLY the enum strings from the answer template. No variations in capitalization, spelling, or underscores.
3. **Empty collections**: Use `[]` (empty array), never `null`, for fields that are arrays with no entries.
4. **Null vs. empty**: `follow_up_practice` uses JSON `null` when there is no practice to contact. Most other fields use empty arrays or empty strings as specified in the template.
5. **No narrative**: The final answer JSON must contain no prose explanations, evidence notes, or extra keys beyond what the template defines.
6. **Date format**: `YYYY-MM-DD` throughout.
7. **String values**: Always match the portal's exact display strings for names (practices, coordinators, programs). Don't normalize or abbreviate.
8. **task_id**: Always match the task_id from the answer template. Don't change it.

## Common Pitfalls

- **Not following sub-resources**: A patient record often links to `/demographics`, `/insurance`, `/documents` etc. You must fetch each linked sub-resource to get the full picture. Don't rely solely on the top-level record.
- **Stale vs. missing confusion**: A lab result that exists but is outside the freshness window is `stale_items`, not `missing_packet_items`. Only the infection screen and labs can be stale; all other document types are either present or missing.
- **Authorization and confidentiality are independent**: A transfer can have valid authorization but invalid confidentiality, or vice versa. Check both independently.
- **Consent declined vs. not obtained**: Both `declined` and `not_obtained` mean the consent form is unsigned, so `consent_signed` goes in `missing_items` either way. The `consent_outcome` field captures the distinction.
- **Overcounting ready_count**: Only count records that have NO issues whatsoever. A single missing item or block makes a record not-ready.
- **duplicate_linked_referral_ids**: Only populate when `duplicate_referral` is in `issue_codes`. The linked IDs come from the portal's duplicate detection — look for a `duplicates` or `linked_referrals` field.
- **highest_risk_patient_id tiebreaker**: When multiple patients share the highest risk level, pick the lexicographically last patient ID (not the first).
- **follow_up_practices dedup**: The list should contain each unique practice name exactly once, sorted alphabetically. Omit null entries.
- **pharmacy_network_statuses must include ALL patients**: Even patients whose pharmacy gate is `not_required` still need an entry with `status: "not_required"`.
- **Session expiry**: The portal session may expire. If you start getting redirects or empty responses, re-authenticate.
- **Template field order**: The answer template shows the expected key order. Maintain that order in your output for consistency.
