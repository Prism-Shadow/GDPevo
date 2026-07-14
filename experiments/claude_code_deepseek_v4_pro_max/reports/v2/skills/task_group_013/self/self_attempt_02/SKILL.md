# Northstar Care Intake Portal — Solver Skill

## Environment

| Item | Value |
|------|-------|
| Portal base URL | `http://34.46.77.124:9013` |
| Login email | `intake.admin@northstar.example` |
| Login password | `Northstar-Intake-2026!` |
| Login endpoint | `POST /login` (form: `email`, `password`) |
| Session handling | Standard cookie-based; capture with `curl -c/-b` |
| Review date (default) | `2026-07-07` unless a task overrides it |

Always authenticate first, then navigate. Every page requires the session cookie.

**Override rule**: The environment access file overrides any local URL in task text. Never use localhost.

## Portal Navigation Map

| Section | Path | Used by task types |
|---------|------|--------------------|
| Dashboard | `/dashboard` | Overview, priority queue |
| Patients | `/patients` | All (patient demographics, clinical risk) |
| Benefits | `/benefits` | train_001 (insurance/PBM/pharmacy eligibility) |
| Pharmacies | `/pharmacies` | train_001 (network verification) |
| Transfers | `/transfers` | train_002 (dialysis transfer packet) |
| Referrals | `/referrals` | train_003 (orthopedic referral triage) |
| Charts | `/charts` | train_004, train_005 (chart readiness, linked data) |
| Programs | `/programs` | train_005 (chronic-care enrollment) |
| Queue | `/queue` | Cross-cutting (linked work items) |
| Documents | `/documents` | Reference (checklist summaries) |
| Policies | `/policies` | All (business rules — ALWAYS review before deciding) |

**Key pattern**: Detail pages link to related sections. A patient page has links to `/benefits/{id}`, `/charts/{id}`, `/programs/{id}`. Always follow these links when a task requires cross-domain data.

## Credential and Session SOP

```
# Login and capture session:
curl -c /tmp/cookies.txt -b /tmp/cookies.txt -L \
  -d "email=intake.admin@northstar.example&password=Northstar-Intake-2026!" \
  http://34.46.77.124:9013/login

# All subsequent requests:
curl -s -b /tmp/cookies.txt http://34.46.77.124:9013/PATH
```

The session cookie persists; re-login only if you get a redirect to /login.

## How to Read the Portal

### Data presentation conventions

- **`<dl>` definition lists**: All detail pages render data as `<dt>` (field name) / `<dd>` (value) pairs. Parse `<dt>` text exactly — field names use dot notation like `Clinical.Alcohol` or `Documents.Labs.Date`.
- **Badge classes**: Values are often wrapped in `<span class="badge ...">`:
  - `badge good` (green) → positive/ready/active/in-network
  - `badge warn` (amber) → problem/inactive/missing/out-of-network
  - `badge hot` (red) → urgent/stat/critical
  - `badge neutral` (grey) → informational/default
- **Table columns on list pages**: The list page headers tell you which fields exist on detail pages. Use them as a schema hint.
- **Bare values**: Some `<dd>` elements have no badge wrapper (e.g., "yes", "no") — these are still authoritative.

### ID prefix conventions

| Prefix | Entity | List page | Detail page |
|--------|--------|-----------|-------------|
| NSP- | New patient registration | /patients | /patients/NSP-XXXX |
| TR- | Dialysis transfer | /transfers | /transfers/TR-XXXX |
| REF- | Orthopedic referral | /referrals | /referrals/REF-XXXX |
| CHR- | Chart record | /charts | /charts/CHR-XXXX |
| CCP- | Chronic-care program | /programs | /programs/CCP-XXXX |
| NDT- | Dialysis transfer patient | /patients | /patients/NDT-XXXX |
| NOR- | Orthopedic referral patient | /patients | /patients/NOR-XXXX |

Transfers and referrals have their own patient population (NDT/NOR) — the patient ID on the transfer/referral page is the authoritative link.

---

## Task Type 1: New Patient Registration Audit

**ID prefix**: NSP-
**Key pages**: Patient detail (`/patients/{id}`), Benefits detail (`/benefits/{id}`), Pharmacy list (`/pharmacies`)

### Policy POL-REG-01 (from /policies)

- Use the **latest portal-verified eligibility snapshot** — never rely on card image status.
- Medical insurance must be **active** on the review date AND **in network**.
- A stale card image never overrides verified portal status.
- **Medication-managed intake** (check `Medication Managed` on the patient page) also requires: **active PBM** AND an **in-network preferred pharmacy**.

### Gate logic

| Gate | Blocked when |
|------|-------------|
| `medical_insurance` | Coverage Status is NOT `active` (e.g., inactive, terminated, pending COB) OR Network Status is NOT `in network` |
| `pbm` | Patient is medication-managed AND Pbm Status is NOT `active`. Mark `not_required` if patient is NOT medication-managed. |
| `pharmacy` | Patient is medication-managed AND Pharmacy Network Status is NOT `in network`. Mark `not_required` if patient is NOT medication-managed. |
| `demographics` | Any of: Address Complete != yes, Consent Signed != yes, Emergency Contact != yes, Identity Verified != yes, Phone Verified != yes |
| `risk` | Based on clinical indicators (see below) |

### Risk assessment

Derive risk from the patient page's `Clinical.*` fields:

- **high**: Multiple chronic conditions + poor lifestyle indicators (smoking, alcohol daily, <60 min exercise) + vaccination declined/due
- **moderate**: One chronic condition or mixed lifestyle indicators
- **low**: No chronic conditions, exercise adequate, vaccinations current, no smoking

Risk calibration: err toward moderate as the default; reserve high for clear multi-factor cases.

### Blocked reasons (sorted array)

Use only these enum values:
- `insurance_inactive` — Coverage Status is not active
- `insurance_out_of_network` — Network Status is not in network
- `pbm_inactive` — medication-managed + PBM not active
- `pharmacy_out_of_network` — medication-managed + pharmacy not in network
- `demographics_incomplete` — any demographics field is "no"
- `clinical_review_required` — risk is high or moderate with concerning patterns

### Overall decision

- `ready`: All gates pass, risk low, no blocked reasons
- `manual_review`: Risk moderate, or has blockable issues that need human judgment
- `blocked`: Any hard gate failure (insurance inactive, out of network, demographics incomplete)

### Pharmacy network status

Read from Benefits page `Pharmacy Network Status` field: `in_network`, `out_of_network`, or `not_required` (when patient is NOT medication-managed).

### Benefits page field reference

| Field | Relevant values |
|-------|----------------|
| Coverage Status | active, inactive, terminated, pending COB |
| Network Status | in network, out of network, network exception needed |
| Pbm Status | active, inactive, not located, pending |
| Pharmacy Network Status | in network, out of network |
| Source Label | Must be "portal-verified eligibility" — this is the authoritative source |
| Card Image Status | present/matches portal snapshot/not present — DO NOT use for gate decisions |

---

## Task Type 2: Dialysis Transfer Readiness

**ID prefix**: TR-
**Key page**: Transfer detail (`/transfers/{id}`)

### Policy POL-REN-02 (from /policies)

- **Labs**: current within **30 days** of requested start date
- **Infection screening**: current within **14 days** of requested start date
- **Dialysis prescription**: must be **final**
- **Required items** (all 9): labs, infection screen, dialysis prescription, medication list, allergy list, authorization, confidentiality statement, referring contact, transport note

### Document statuses and their meaning

| Status | Meaning | Action |
|--------|---------|--------|
| `final` | Complete, usable | Include if within freshness window |
| `received` | Received but not final | Consider usable if in freshness window |
| `draft` | Incomplete | → missing_packet_items |
| `missing` | Not received | → missing_packet_items |
| `expired` | Was final but lapsed | → missing_packet_items |

### Freshness check

For each document with a Date field:
1. Parse the date (YYYY-MM-DD)
2. Compute days between document date and requested start date
3. For labs: date must be ≤ 30 days before start
4. For infection screen: date must be ≤ 14 days before start
5. For other items: no strict freshness window (just status matters)

**Stale vs missing**:
- Item is `final` or `received` but date is OUTSIDE the freshness window → goes in `stale_items`
- Item is `draft`, `missing`, or `expired` → goes in `missing_packet_items`
- Only labs and infection screens can be stale; other items go only to missing_packet_items

### Decision logic

| Decision | Condition |
|----------|-----------|
| `accept` | All 9 items present/usable, dialysis prescription final, auth valid, confidentiality valid, chair held, chart prep complete |
| `hold_missing_packet` | Any item is missing/draft/expired, OR auth/confidentiality invalid, OR dialysis prescription not final |
| `hold_capacity` | Chair availability is NOT "chair held" (i.e., "capacity review", "chair available, not held", "waitlist") |

### Start compatibility

| Value | Chair status |
|-------|-------------|
| `compatible` | Chair is "chair held" AND chart prep is "complete" |
| `capacity_review` | Chair is "capacity review" |
| `waitlist` | Chair is "waitlist" or "chair available, not held" |

### Route owner

| Value | When to assign |
|-------|---------------|
| `referring_facility` | missing_packet_items is non-empty (referring facility needs to send) |
| `capacity_coordinator` | Chair is not held (capacity/waitlist issue) |
| `chart_prep` | Chart prep status is "not started" or "in progress" |
| `intake_complete` | Everything is resolved (decision = accept) |

### Authorization and confidentiality

- `authorization_valid`: true only if Documents.Authorization.Status is `final` (received may also count in some cases; use judgment)
- `confidentiality_valid`: true only if Documents.Confidentiality Statement.Status is `final` or `received` (draft/expired/missing = false)

### Transfer page field reference

| Field | Purpose |
|-------|---------|
| Transfer Id | Record identifier |
| Patient Id | Links to /patients/{id} |
| Requested Start Date | Freshness window anchor |
| Requested Chair Availability | capacity review, chair held, chair available not held, waitlist |
| Chart Prep Status | not started, in progress, ready pending documents, complete |
| Documents.{Item}.Date | Document date for freshness calc |
| Documents.{Item}.Status | final, received, draft, missing, expired |
| Dialysis Modality | in-center hemodialysis, home hemodialysis, peritoneal dialysis |
| Referring Facility | Source facility name |

---

## Task Type 3: Orthopedic Referral Scheduling

**ID prefix**: REF-
**Key page**: Referral detail (`/referrals/{id}`)
**Also check**: `/policies` (POL-REF-03)

### Policy POL-REF-03 (from /policies)

- Scheduling requires an **M-code or supported musculoskeletal diagnosis**
- **Agreement** between narrative and laterality
- Required **clinical records and imaging**
- **Payer authorization** when required
- Duplicate checks use **patient demographics and condition**

### ICD-10 coding conventions

Musculoskeletal codes (M00-M99): valid chapter for orthopedics
- M17.11 = unilateral primary osteoarthritis, right knee → `chapter_valid: true`
- M25.562 = knee pain, left → `chapter_valid: true`
- M54.50 = low back pain, spine → `chapter_valid: true`
- S83.241A = knee sprain, right → `chapter_valid: true`

Non-musculoskeletal codes:
- E11.9 = type 2 diabetes mellitus → `chapter_valid: false` → issue: `invalid_chapter`

### Coding checks

| Field | Condition for true |
|-------|-------------------|
| `chapter_valid` | ICD-10 code starts with M or S (musculoskeletal/injury) |
| `narrative_match` | Diagnosis narrative text aligns with ICD-10 code description |
| `laterality_match` | Laterality field matches what the narrative describes (e.g., "right knee" ↔ laterality "right") |

Common mismatch: E11.9 has laterality "n/a" and is an endocrine code — chapter_valid is false regardless of narrative.

### Issue codes

| Code | When |
|------|------|
| `invalid_chapter` | ICD-10 not M/S coded (e.g., E11.9 for orthopedics) |
| `diagnosis_mismatch` | Narrative doesn't match ICD-10 description |
| `laterality_mismatch` | Laterality field contradicts narrative |
| `missing_records` | Records Received = no |
| `missing_imaging` | Imaging Received = no |
| `authorization_gap` | Authorization Status is "missing" when insurance requires it (most do); "not required" and "approved" are OK |
| `duplicate_referral` | Linked Referral Ids is non-empty OR Duplicate Hints suggests a duplicate |

### Readiness status

| Status | Condition |
|--------|-----------|
| `ready_to_schedule` | All checks pass: coding OK, records/imaging received, auth OK, no duplicates |
| `pending_records` | Missing records or imaging (can co-exist with other issues) |
| `coding_clarification` | chapter_valid = false, or narrative_match = false, or laterality_match = false |
| `authorization_followup` | Authorization Status is "missing" or "pending" (and auth is required) |
| `duplicate_review` | Linked Referral Ids non-empty or duplicate hints present |

**Tie-breaking for readiness_status**: when multiple issues exist, pick the most actionable. Prefer `coding_clarification` over `pending_records` (coding blocks scheduling), `authorization_followup` over `duplicate_review` (auth is a hard block). If everything passes, it's `ready_to_schedule`.

### Priority tier

| Tier | Mapping |
|------|---------|
| `schedule` | readiness_status = ready_to_schedule AND urgency = routine |
| `tier_1` | readiness_status = ready_to_schedule AND urgency = urgent/stat review |
| `tier_2` | NOT ready_to_schedule AND urgency = urgent/stat review |
| `tier_3` | NOT ready_to_schedule AND urgency = routine |

### Follow-up practice

If readiness is NOT ready_to_schedule, return the Practice name from the referral page as `follow_up_practice`. If ready, use `null`.

### Duplicate checks

- If `Linked Referral Ids` is non-empty, list those IDs in `duplicate_linked_referral_ids`
- `Duplicate Hints` field gives context (e.g., "same physician only", "similar name same DOB", "same condition within 30 days") — use this to confirm or dismiss the duplicate concern

---

## Task Type 4: Chart Onboarding Readiness

**ID prefix**: CHR-
**Key page**: Chart detail (`/charts/{id}`)
**Also check**: Patient page (`/patients/{id}`) for demographic/clinical context

### Policy POL-CHR-04 (from /policies)

A chart is **ready** only when ALL of these are complete:
1. **Demographics** complete
2. **History** complete
3. Applicable **active problems** complete
4. **Current vitals**
5. Onboarding **care plan or clinical instructions** complete
6. **Orientation communication** complete

### Missing sections enum and mapping

| Enum value | Chart field condition |
|------------|----------------------|
| `chart_not_created` | Chart Created != yes (rare but possible) |
| `demographics` | Demographics Complete != yes |
| `history` | History Complete != yes |
| `problems` | Problems Complete != yes |
| `vitals` | Vitals.Current != yes |
| `care_plan_or_instructions` | Care Plan is "missing" OR Clinical Instructions is in a non-ready state (but "not needed" = OK) |
| `orientation_message` | Orientation Message is not "sent" |

**Note on care_plan_or_instructions**: If Care Plan is "documented" AND Clinical Instructions is "not needed", this section is satisfied (not missing). If Care Plan is "missing" or "draft" AND Clinical Instructions is not final, add to missing. Use judgment: "not needed" for Clinical Instructions counts as satisfied.

### BMI class

When height/weight data is available on the chart or patient page, compute BMI. When absent:
- Use `not_available` (most common case)

If BMI data IS present:
- < 18.5 → not in enum, use clinical judgment
- 18.5-24.9 → `normal`
- 25-29.9 → `overweight`
- ≥ 30 → `obese`

Typically, chart pages in this portal do NOT expose height/weight — so `not_available` is the default.

### Orientation state

| State | Orientation Message value |
|-------|--------------------------|
| `sent` | "sent" |
| `queued` | "queued" |
| `missing` | "not sent" |
| `draft` | (if the portal shows "draft" explicitly) |

### Next owner

| Owner | When |
|-------|------|
| `registration_desk` | demographics or history missing |
| `clinical_intake` | problems incomplete, vitals not current, or care_plan_or_instructions missing |
| `patient_communications` | orientation_message not sent |
| `ready` | chart_ready = true (all sections complete) |

### Chart ready determination

`chart_ready` = true when `missing_sections` is an empty array. Otherwise false.

### Problem list complete

Direct map from `Problems Complete` field: "yes" → true, "no" → false.

### Chart page field reference

| Field | Type | Notes |
|-------|------|-------|
| Chart Created | yes/no | Almost always yes |
| Demographics Complete | yes/no | |
| History Complete | yes/no | |
| Problems Complete | yes/no | |
| Care Plan | documented/draft/missing | |
| Clinical Instructions | not needed/pending nurse edit | "not needed" = satisfied |
| Orientation Message | sent/queued/not sent | |
| Vitals.Bp | e.g., "153/65" | |
| Vitals.Current | yes/no | |
| Vitals.Pulse | number | |
| Vitals.Recorded Date | YYYY-MM-DD | |
| Active Problem Codes | comma-separated ICD-10 | |

---

## Task Type 5: Chronic-Care Program Enrollment

**ID prefix**: CCP-
**Key pages**: Program detail (`/programs/{id}`)
**Also check**: Patient page (`/patients/{id}`) for clinical context, Chart page (`/charts/{id}`) for vitals context

### Policy POL-CCP-05 (from /policies)

- Diabetes and hypertension pathways require: **active diagnosis**, **recent labs or vitals**, **consent**, and **complete program form**
- **Renal risk** changes cadence and may require nurse escalation

### Program page field reference

| Field | Type | Notes |
|-------|------|-------|
| Patient Id | CCP-XXXX | Links to /patients/{id} |
| Proposed Program | string | e.g., "Cardiometabolic Combo", "Renal Risk Monitoring", "Hypertension Pathway" |
| Active Diagnoses | string | Comma-separated conditions |
| Recent Hba1C | number or empty | Blank if not available |
| Bp | "systolic/diastolic" | |
| Consent Status | signed/not obtained/declined/verbal pending signature | |
| Program Form Status | complete/incomplete/not started | |
| Renal Flag | yes/no | |
| Coordinator | name | |
| Last Visit | YYYY-MM-DD | |
| Medication Adherence | string | variable/poor/unknown |
| Telehealth Preference | string | phone/video/in-person |

### Enrollment decision logic

| Decision | Condition |
|----------|-----------|
| `enroll` | Diagnosis matches program, labs/vitals present and recent, consent signed, form complete |
| `enroll_with_nurse_escalation` | Renal flag = yes AND one or more risk factors (high BP, poor adherence, high HbA1c, old last visit) |
| `hold_missing_consent` | Consent Status is NOT "signed" (i.e., not obtained, verbal pending signature, declined) |
| `hold_missing_form` | Program Form Status is NOT "complete" |
| `clinical_review` | No matching active diagnosis for the proposed program, OR missing labs/vitals when program requires them |

**Decision tie-breaking**: Check in order: consent → form → diagnosis/labs → enrollment. First blocking condition wins.

### Missing items

| Item | When to include |
|------|----------------|
| `diagnosis_support` | Active Diagnoses don't match the proposed program's target condition |
| `recent_hba1c_or_bp` | HbA1c is blank/empty AND BP doesn't constitute recent vitals |
| `consent_signed` | Consent Status is not "signed" |
| `program_form_complete` | Program Form Status is not "complete" |

### Follow-up cadence

| Cadence | When |
|---------|------|
| `weekly_nurse_call` | Renal flag = yes AND (poor adherence OR high risk BP/HbA1c OR old last visit) |
| `biweekly_checkin` | Renal flag = yes but stable, OR moderate risk factors |
| `monthly_checkin` | Renal flag = no, stable indicators, enrollment decision = enroll |

### Consent outcome

| Outcome | Consent Status value |
|---------|---------------------|
| `signed` | "signed" |
| `not_obtained` | "not obtained" or "verbal pending signature" |
| `declined` | "declined" |

### Coordinator

Copy the Coordinator field value from the program page (e.g., "M. Okafor", "R. Alvarez", "S. Lin"). Use empty string `""` if no coordinator assigned.

### Coordinator queue

Patients whose `enrollment_decision` is `enroll_with_nurse_escalation` go in `coordinator_queue` (array of patient IDs). Also add if coordinator field is non-empty and there's a consent or form issue.

### Telehealth preference

Copy verbatim from the program page (`phone`, `video`, `in-person`).

### Proposed program

Copy verbatim from the program page. Common values: "Cardiometabolic Combo" (diabetes + hypertension), "Hypertension Pathway", "Renal Risk Monitoring".

---

## Cross-Cutting SOPs

### Always check /policies first

Every task type has a corresponding policy on `/policies` (POL-REG-01 through POL-CCP-05). These are the authoritative business rules. Read them before making any decisions — they often contain rules not obvious from record data alone (e.g., "card image never overrides portal status").

### Always follow cross-links

A patient page links to benefits, chart, and program. A program page's Patient Id links back to the patient. When a task says "review related registration details" or "inspect related patient/chart details", follow those links.

### Sorting convention

Every output array must be sorted by the primary ID ascending (patient_id, transfer_id, referral_id). Use lexicographic string sort. ID arrays (like `blocked_reasons`, `missing_sections`, `missing_items`) must also be sorted ascending.

### Enum discipline

Use ONLY the exact enum strings from the answer template. Never invent variations. If the template says `"in_network"`, do not write `"in-network"` or `"In Network"`. If a value doesn't map cleanly, pick the closest enum and stay within the allowed set.

### Count fields

- `ready_count`: count of records where the primary decision is "ready" / "accept" / "ready_to_schedule" / chart_ready=true / "enroll"
- `highest_risk_patient_id`: from train_001, the patient ID with the highest risk level (if tie, pick first by sort order)
- `manual_review_patient_ids`: sorted array of patient IDs where overall_decision = "manual_review"
- `accepted_count`: count of transfers with decision = "accept"
- `authorization_problem_transfers`: transfer IDs where authorization_valid = false
- `confidentiality_problem_transfers`: transfer IDs where confidentiality_valid = false
- `escalation_count`: count of patient_reviews where enrollment_decision = "enroll_with_nurse_escalation"
- `follow_up_practices`: unique sorted practice names that need follow-up

### Null vs empty

- `follow_up_practice`: use `null` (JSON null) when no follow-up needed, string otherwise
- `duplicate_linked_referral_ids`: use `[]` when no duplicates linked
- `coordinator`: use `""` when no coordinator assigned
- `missing_sections`, `missing_items`, `blocked_reasons`: use `[]` when none

### Common pitfalls

1. **Medication Managed field**: On the patient page, "Medication Managed: yes" means PBM and pharmacy gates apply. If "no", mark both as `not_required`. Don't skip checking this.
2. **stale vs missing in transfers**: Only labs and infection screens go in `stale_items`. All other missing/draft/expired documents go in `missing_packet_items`. Don't put non-lab items in stale_items.
3. **E11.9 in orthopedics**: This is a diabetes code, not musculoskeletal. chapter_valid is false when the referral is for orthopedics but the ICD-10 is E11.9.
4. **Care plan satisfaction**: "Clinical Instructions: not needed" does NOT mean the section is missing. It means instructions are not applicable, which satisfies the requirement. But "Care Plan: missing" still fails.
5. **Consent "verbal pending signature"**: This maps to `not_obtained`, NOT `signed`. Only explicit "signed" counts as signed.
6. **Source Label**: On the benefits page, always verify `Source Label` is "portal-verified eligibility". If it says something else, the data may not be authoritative.
7. **Review date**: The default review date is 2026-07-07. Use this as "today" when evaluating freshness unless a task specifies otherwise.
8. **Answer template precedence**: The answer template defines the exact output shape. If the template has a field not mentioned in the prompt, still fill it. If the prompt mentions something not in the template, don't add it.

### Output format rules

- Return ONLY valid JSON; no markdown fences, no narrative, no evidence notes
- Match the answer template structure exactly — same keys, same nesting, same types
- Arrays must be sorted ascending
- Use the controlled enum values only; no free text where an enum is specified
- Boolean fields use JSON `true`/`false`, not strings
- Empty arrays use `[]`, not `null`
