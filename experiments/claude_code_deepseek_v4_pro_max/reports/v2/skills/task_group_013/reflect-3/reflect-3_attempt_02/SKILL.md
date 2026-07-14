# Northstar Care Intake Portal — Audit & Review Skill

## Environment

A single remote web portal serves all task data. No local filesystem, no API beyond standard GET requests to HTML pages. All records are accessed through the portal UI at the base URL provided in the task prompt (overridden by `environment_access.md` if present).

**Credentials:** `intake.admin@northstar.example` / `Northstar-Intake-2026!`

**Session:** The portal uses cookie-based sessions (`northstar_session`). Login via `POST /login` with form data `email` and `password`, then carry the session cookie on all subsequent requests.

**Key principle:** Every record has a detail page. There are no sub-routes like `/patients/{id}/benefits` — use `/benefits/{id}`, `/charts/{id}`, `/programs/{id}`, `/transfers/{id}`, `/referrals/{id}` directly. All data is rendered as HTML `<dl>` definition lists with `<dt>` (field name) and `<dd>` (value). Badge CSS classes (`good`, `warn`, `hot`, `neutral`) carry semantic meaning but are presentation hints only — read the actual text values.

**Document detail pages return "Not found"** — document summaries appear only on the `/documents` listing page. Policy content is in `/policies` listing. No individual policy or document detail pages exist.

## Portal Navigation Map

| Section | List Page | Detail Page Pattern | Key Fields |
|---|---|---|---|
| Patients | `/patients` | `/patients/{id}` | Demographics (5 boolean fields), Clinical (7 fields), DOB, Language, Service Line, Requested Service, Medication Managed, Registration Links |
| Benefits | `/benefits` | `/benefits/{id}` | Coverage Status, Network Status, PBM Name/Status, Pharmacy Network Status, Preferred Pharmacy, Payer, Effective/Termination Dates, Authorization Required, Special Handling |
| Pharmacies | `/pharmacies` | (none) | 8 pharmacies: 5 retail, 3 specialty (one mail-order). All in-network except Harbor Mail Order (mail order only) |
| Transfers | `/transfers` | `/transfers/{id}` | Requested Start, Chair Availability, Chart Prep Status, 9 document types each with Date/Source/Status |
| Referrals | `/referrals` | `/referrals/{id}` | ICD-10, Narrative, Laterality, Auth Status, Duplicate Hints, Linked Referral IDs, Urgency, Imaging/Records Received, Practice, Physician |
| Charts | `/charts` | `/charts/{id}` | Active Problem Codes, Care Plan, Clinical Instructions, Vitals (BP/Pulse/Current/Recorded Date), Demographics/History/Problems Complete, Orientation Message, Patient Portal Status |
| Programs | `/programs` | `/programs/{id}` | Active Diagnoses, HbA1c, BP, Renal Flag, Consent Status, Program Form Status, Proposed Program, Coordinator, Telehealth Preference, Last Visit, Medication Adherence |
| Policies | `/policies` | (none) | 5 policies (POL-REG-01 through POL-CCP-05) — these ARE the business rules |
| Queue | `/queue` | `/queue/{id}` | Queue items by family/urgency, linked to specific records |

## Business Rules (from `/policies`)

### POL-REG-01 — Registration Gates
- Medical insurance must be **active on the review date** AND **in network**. A stale card image never overrides verified portal status.
- **Medication-managed intake** additionally requires **active PBM** AND an **in-network preferred pharmacy**.
- Demographics must be complete: all 5 fields (Address Complete, Consent Signed, Emergency Contact, Identity Verified, Phone Verified) must be `yes`.
- Gate statuses: `pass` = meets requirement, `block` = fails. PBM and Pharmacy gates use `not_required` when the patient is not medication-managed.

### POL-REN-02 — Dialysis Transfer Freshness
- Labs must be current **within 30 days** of the requested start date.
- Infection screening must be current **within 14 days** of the requested start date.
- Dialysis prescription must be `final`.
- All 9 items are **required**: labs, infection screen, dialysis prescription, medication list, allergy list, authorization, confidentiality statement, referring contact, transport note.
- Items with status `missing`, `draft`, `expired`, or otherwise not final/usable → **missing_packet_items**.
- Items that are **usable** (final/received) but **outside the freshness window** → **stale_items**. An item that is expired/draft/missing is NOT stale — it goes in missing_packet_items only.

### POL-REF-03 — Orthopedics Referral Scheduling
- Scheduling requires an **M-code or supported musculoskeletal diagnosis**.
- **Agreement** between narrative text and laterality field.
- Required: clinical records AND imaging.
- Payer authorization when required (status `approved` or `not required` = OK; `missing` or `pending` = gap).
- Duplicate checks use patient demographics and condition.
- **Referral-specific field conventions:**
  - `chapter_valid`: `true` when the ICD-10 code chapter is appropriate for the service line (M-codes like M17, M25, M54, S83 for orthopedics). Non-orthopedic codes (E11 for diabetes) make this `false`.
  - `narrative_match`: `true` when the diagnosis narrative text aligns with the ICD-10 code description.
  - `laterality_match`: `true` when narrative laterality (e.g., "right knee") matches the laterality field. `n/a` matches `n/a`.
  - `duplicate_linked_referral_ids`: include only the IDs explicitly listed in the referral's "Linked Referral Ids" field. The "Duplicate Hints" text is advisory — it informs issue codes but does NOT populate linked IDs unless actual IDs are listed.
  - `follow_up_practice`: the referring practice name when follow-up is needed; `null` when the referral is ready.
  - Priority tier maps from urgency: `routine` → `tier_2`, `stat review` or `urgent` → `tier_1`. Use `schedule` only for referrals that are truly `ready_to_schedule`.

### POL-CHR-04 — Chart Readiness
- A chart is **ready** only when ALL of these are complete: demographics, history, applicable active problems, **current** vitals, onboarding care plan or clinical instructions, and orientation communication.
- **"Current" vitals** means vitals recorded recently and `Vitals.Current` = `yes`. Old vitals (`Vitals.Current` = `no`) do not satisfy the requirement even if recorded.
- `Care Plan` = `missing` or `draft` → section incomplete.
- `Clinical Instructions` = `not needed` is acceptable (not a gap). `pending nurse edit` is a gap.
- `Orientation Message` = `sent` is complete; `queued` or `not sent` is incomplete.
- `Problems Complete` = `no` means the problems section is incomplete (required only when applicable active problems exist).
- **BMI class**: `not_available` when height/weight data is absent from all patient and chart pages. The portal does not expose BMI directly.
- **Next owner**: `ready` when chart is fully ready; `clinical_intake` when clinical sections (care plan, problems, vitals) need work; `patient_communications` when only orientation message is missing; `registration_desk` when demographics are incomplete.

### POL-CCP-05 — Chronic Program Enrollment
- Diabetes and hypertension pathways require: active diagnosis, recent labs or vitals (HbA1c and/or BP within reasonable recency), consent, and a complete program form.
- **Renal flag** `yes` changes the follow-up cadence (typically to `weekly_nurse_call`) and may require nurse escalation.
- **Consent outcomes**: `signed` = OK, `not_obtained` = needs follow-up, `declined` = blocker requiring clinical review.
- **Enrollment decisions**: `enroll` (all clear), `enroll_with_nurse_escalation` (renal flag + elevated labs), `hold_missing_consent` (consent not obtained or declined), `hold_missing_form` (form not started/incomplete), `clinical_review` (ambiguous/complex cases where diagnosis fit is questionable).
- **Missing items enum**: `diagnosis_support` (program diagnosis not supported by patient's active conditions), `recent_hba1c_or_bp` (labs/vitals missing or too old), `consent_signed` (consent not obtained/declined), `program_form_complete` (form not started or incomplete).
- **Cadence**: `weekly_nurse_call` for renal-flagged patients; `biweekly_checkin` for diabetes/hypertension without renal flag; `monthly_checkin` for lower-acuity pathways.
- **Coordinator queue**: patients whose enrollment is not straightforward (those needing consent, form completion, or clinical review) belong in the coordinator queue. Patients who can `enroll` or `enroll_with_nurse_escalation` without additional follow-up steps may not need coordinator queue entry.

## Document Status Interpretation

For transfer packet documents, interpret statuses as follows:
- `final` — usable, complete
- `received` — usable, received (treat as complete for non-time-sensitive items)
- `draft` — not final, goes in missing_packet_items
- `expired` — no longer valid, goes in missing_packet_items
- `missing` — not present, goes in missing_packet_items

## Risk Assessment Guidelines (Registration)

Risk level (`low`, `moderate`, `high`) for patient registration is a holistic clinical assessment:

**High risk indicators** (any one may push to high, multiple confirm it):
- Daily alcohol use
- Current smoking + chronic condition
- Polypharmacy (3+ medications flagged)
- Multiple chronic conditions (3+)
- Sedentary lifestyle (<60 min/week exercise) + multiple conditions
- Vaccination declined + smoking or other risk behaviors
- Identity not verified (combined with other indicators)

**Moderate risk indicators:**
- Single chronic condition with managed lifestyle
- Weekly alcohol, no smoking
- Unknown smoking/alcohol status (incomplete picture)
- Age >75 with chronic condition

**Low risk:**
- No chronic conditions, or single well-managed condition
- Healthy lifestyle indicators (exercise, no smoking, limited alcohol)
- All preventive measures current

When risk is `high`, include `clinical_review_required` in `blocked_reasons`.

## Registration Decision Logic

- `ready` — all gates pass, risk low or moderate, no blocked reasons
- `manual_review` — all gates pass but risk is moderate with concerning indicators, or some ambiguity
- `blocked` — any gate blocks (medical, demographics, PBM for medication-managed)

The `overall_decision` for a patient with blocked gates is always `blocked`, regardless of how many gates are blocked. Only when ALL gates pass can the decision be `ready` or `manual_review`.

## Transfer Decision & Routing

- `hold_missing_packet` — any required document is missing/draft/expired
- `hold_capacity` — no missing documents but chair availability is `capacity review` or `waitlist`
- `accept` — no missing documents AND chair is available

Start compatibility maps from chair status:
- `capacity review` → `capacity_review`
- `waitlist` → `waitlist`
- `chair available, not held` or `chair held` → `compatible`

Route owner logic:
- `referring_facility` — missing/expired/draft documents need the referring facility to resend
- `capacity_coordinator` — capacity issue is the primary blocker with documents complete
- `chart_prep` — chart prep status is the active bottleneck (e.g., `in progress`, `ready pending documents` when documents are NOT the issue)
- `intake_complete` — everything done

When both documents are missing AND chart prep is incomplete, the route owner is typically `referring_facility` (documents must be resolved first before chart prep can finalize).

## Authorization & Confidentiality Validity

- `authorization_valid`: `true` only when auth document status is `final` and not expired. `missing`, `draft`, `expired`, or any non-final status → `false`.
- `confidentiality_valid`: `true` only when confidentiality statement status is `final` or `received`. `draft`, `expired`, `missing` → `false`.

The aggregate arrays (`authorization_problem_transfers`, `confidentiality_problem_transfers`) list transfer IDs where the respective item is NOT valid. Sort ascending.

## Output Schema Conventions

1. **Arrays of IDs must be sorted ascending** (patient IDs, transfer IDs, referral IDs).
2. **Arrays of string enums must be sorted alphabetically** within each record (e.g., `blocked_reasons`, `missing_packet_items`, `issue_codes`, `missing_items`).
3. **Enum values must exactly match** the template strings — no synonyms, no extra values, no capitalization variations.
4. **Empty arrays** use `[]`, not `null` or omission.
5. **Null vs empty**: `follow_up_practice` uses `null` when no follow-up is needed; empty arrays `[]` for no duplicates, no issues, no missing items.
6. **Count fields** (`ready_count`, `accepted_count`, `escalation_count`) are integers reflecting the number of records in the respective state.
7. **`highest_risk_patient_id`**: among patients with `risk: "high"`, pick one (if multiple, the one with most severe combination). If no high-risk patients, use the highest moderate-risk patient.
8. **`pharmacy_network_statuses`**: one entry per patient, matching `pharmacy_network_status` from each patient row. Same order as patients array.
9. **Date fields** use `YYYY-MM-DD` format.

## Common Pitfalls

- **Don't confuse patient ID prefixes with record types.** NSP/NOR prefixes can appear across multiple sections (patients, benefits, charts, programs). Transfer IDs (TR-xxxx) link to NDT-prefixed patient IDs, not matching numbers (TR-2604 → NDT-2601, not NDT-2604).
- **"Not located" PBM status** means the PBM record couldn't be found — treat as `pbm_inactive`/`block`.
- **Authorization "pending" for referrals** IS an `authorization_gap`. The referral cannot proceed until approved.
- **Authorization "missing" for referrals** is also `authorization_gap`. Only `approved` and `not required` are non-gap statuses.
- **Health plan coverage statuses matter independently of network status.** `inactive` or `terminated` coverage means `insurance_inactive` even if network shows `in network`.
- **Stale items are ONLY for usable documents outside freshness windows.** An expired infection screen is `missing_packet_items`, not `stale_items`, because it's not usable. Only a `final` or `received` infection screen >14 days old (or labs >30 days) qualifies as stale.
- **Don't over-infer from "Duplicate Hints."** Only populate `duplicate_linked_referral_ids` with IDs explicitly listed in the "Linked Referral Ids" field. The hints text informs `issue_codes` (`duplicate_referral`) but doesn't create phantom links.
- **`chapter_valid` for referrals differs from `narrative_match`.** An E11.9 diabetes code can have a perfectly matching narrative (`narrative_match: true`) but still be invalid for an orthopedic referral (`chapter_valid: false`). Conversely, an M17.11 knee OA code in an endocrinology-tagged referral is chapter-valid for orthopedics review even though the referral's own service family is endocrinology. Judge the code against the review context (orthopedic referral scheduling), not against the referral's own service family label.
- **Vitals.Current = "no"** means the vitals section is incomplete for chart readiness, even though vitals data exists. The policy requires CURRENT vitals.
- **"Not needed" clinical instructions** is not a gap. Only `missing`, `draft`, or `pending nurse edit` create a care_plan_or_instructions gap.
- **Orientation states map directly:** `sent` = complete, `queued` = incomplete (`orientation_message` gap), `missing` = incomplete, `draft` = incomplete. `not sent` counts as incomplete.
