# Northstar Care Intake Portal — Solver SOP

## Environment

- **Base URL:** `http://34.46.77.124:9013` (always this remote; never localhost)
- **Credentials:** `intake.admin@northstar.example` / `Northstar-Intake-2026!`
- **Auth mechanism:** Session cookie (`northstar_session`) obtained by POST to `/login` with `email` and `password` fields (form-encoded). All subsequent requests must carry the cookie via `-b cookies.txt`.
- **Login command pattern:**
  ```bash
  touch /tmp/ncookies.txt
  curl -s -c /tmp/ncookies.txt -b /tmp/ncookies.txt \
    -X POST -d "email=intake.admin@northstar.example&password=Northstar-Intake-2026!" \
    http://34.46.77.124:9013/login
  ```
  The cookie is set on the 303 redirect; `-c` captures it. Use `-b /tmp/ncookies.txt` on every subsequent GET.
- If you get redirected back to the login page, the session expired — re-login.

## Portal Sections

| Path | Content |
|------|---------|
| `/dashboard` | Summary metrics, priority queue |
| `/patients` | List — patient ID, name, DOB, service line, requested service |
| `/patients/<ID>` | Detail — demographics, clinical flags, registration links |
| `/benefits` | List — coverage, medical network, PBM, pharmacy network |
| `/benefits/<ID>` | Detail — payer, effective date, network, PBM, pharmacy, card image, review date |
| `/pharmacies` | List of PH-001 through PH-008 with network status |
| `/transfers` | List — transfer ID, patient, start date, chair, chart prep |
| `/transfers/<ID>` | Detail — documents, chair availability, chart prep, modality |
| `/referrals` | List — referral ID, patient, ICD-10, laterality, urgency, auth |
| `/referrals/<ID>` | Detail — diagnosis narrative, records, imaging, duplicate hints, practice |
| `/charts` | List — created, demographics, history, problems, orientation |
| `/charts/<ID>` | Detail — care plan, clinical instructions, vitals, problem codes |
| `/programs` | List — diagnoses, HbA1c, BP, renal flag, consent, form |
| `/programs/<ID>` | Detail — proposed program, coordinator, telehealth, last visit |
| `/queue` | Cross-domain work items linked to specific records |
| `/documents` | Reference documents per domain |
| `/policies` | Policy blurbs per domain (see below) |

Every patient detail page cross-links to `/benefits/<ID>`, `/charts/<ID>`, and `/programs/<ID>`. Use these links to gather a complete picture.

## Badge-to-Status Mapping

The portal uses CSS badge classes to convey status. Learn this mapping:

| Badge class | Meaning | Typical evaluation |
|-------------|---------|--------------------|
| `badge good` | green — pass/approved/complete/signed/sent/current | Gate PASS |
| `badge warn` | amber — missing/inactive/expired/draft/pending/declined/not started | Gate BLOCK or NOT_REQUIRED |
| `badge hot` | red — urgent/stat/polypharmacy flag | Escalation signal |
| `badge neutral` | grey — informational/neutral/data-only | No gate decision by itself |

**Critical pitfall:** `badge neutral` on "smoking: current" or "alcohol: daily" is NOT a pass/fail — it's data. You must interpret it against policy rules. Similarly, `badge good` on `smoking: current` is a data label, not a "good health" judgment — it means the field is populated.

## Domain-Specific Business Rules

### 1. Patient Registration (NSP prefix)

**Policy POL-REG-01:** Use the portal-verified eligibility snapshot. Medical insurance must be active on the review date and in network. A stale card image never overrides verified portal status. Medication-managed intake also requires active PBM and an in-network preferred pharmacy.

**Gates and how to determine them:**

- **medical_insurance (pass/block):** Read `/benefits/<ID>`. `Coverage: active` AND `Network: in network` → pass. `inactive`, `terminated`, `pending COB`, `out of network`, `network exception needed` → block.
- **pbm (pass/block/not_required):** Read `/benefits/<ID>`. If patient is NOT medication-managed (`Medication Managed: no` on patient detail) → `not_required`. If medication-managed AND `PBM: active` → pass. If `PBM: not located`, `inactive`, or `pending` → block.
- **pharmacy (pass/block/not_required):** Read `/benefits/<ID>`. Same medication-managed rule applies. If not required → `not_required`. If required AND `Pharmacy network: in network` → pass. `out of network` → block.
- **demographics (pass/block):** On patient detail, ALL five must be `yes`: Address Complete, Consent Signed, Emergency Contact, Identity Verified, Phone Verified. Any `no` → block.
- **risk (low/moderate/high):** Assess clinical indicators: polypharmacy (3+ medications flagged with badge hot), daily alcohol, current smoking, vaccination declined, exercise <60 min/week, chronic conditions. Rough heuristic: 0-1 flags → low, 2-3 → moderate, 4+ or polypharmacy → high. Err toward moderate unless clearly extreme.

**Blocked reasons** — include each concrete failing gate: `insurance_inactive`, `insurance_out_of_network`, `pbm_inactive`, `pharmacy_out_of_network`, `demographics_incomplete`, `clinical_review_required` (for high risk).

**Overall decision:**
- All gates pass AND risk != high → `ready`
- All gates pass BUT risk = high → `manual_review`
- Any gate blocks → `blocked`

**Output fields:**
- `pharmacy_network_status`: one per patient — `in_network`, `out_of_network`, or `not_required`
- `ready_count`: count where overall_decision == `ready`
- `highest_risk_patient_id`: single patient ID with highest risk level (low < moderate < high); break ties by patient ID sort
- `manual_review_patient_ids`: sorted list of patients with risk = high or decision = manual_review

### 2. Dialysis Transfer Readiness (TR prefix)

**Policy POL-REN-02:** Labs current within 30 days of requested start. Infection screen current within 14 days. Dialysis prescription must be final. Nine required packet items: labs, infection screen, dialysis prescription, medication list, allergy list, authorization, confidentiality statement, referring contact, transport note.

**Evaluating each transfer:**
1. Read `/transfers/<ID>` for the document checklist. Each document has Date, Source, and Status.
2. For each of the 9 items, check Status:
   - `missing`, `draft`, `expired` → put in `missing_packet_items`
   - `received` or `final`: check freshness against requested start date
     - Labs: document date must be within 30 days of requested start → if outside 30-day window, put in `stale_items`
     - Infection screen: document date must be within 14 days of requested start → if outside 14-day window, put in `stale_items`
     - All other items: `received` or `final` is sufficient; no staleness check
3. **Decision:**
   - `accept`: all 9 items present+valid+fresh, chair held, chart prep complete
   - `hold_missing_packet`: any missing/draft/expired items (check missing_packet_items)
   - `hold_capacity`: packet is complete but chair is not held (capacity_review, waitlist, chair available not held)
4. **Start compatibility:**
   - `compatible`: chair held, chart prep complete, all documents in order
   - `capacity_review`: chair is "capacity review" or "chair available, not held"
   - `waitlist`: chair is "waitlist"
5. **Route owner:**
   - `referring_facility`: items missing or stale coming from the referring facility
   - `capacity_coordinator`: chair capacity issues
   - `chart_prep`: chart prep not complete
   - `intake_complete`: everything ready
6. **authorization_valid / confidentiality_valid:**
   - `true` if document Status is `final` or `received` (not missing/draft/expired)
   - `false` otherwise

**Output fields:**
- `accepted_count`: count of `accept` decisions
- `authorization_problem_transfers`: IDs where authorization_valid is false
- `confidentiality_problem_transfers`: IDs where confidentiality_valid is false

### 3. Orthopedic Referral Scheduling (REF prefix)

**Policy POL-REF-03:** Requires an M-code or supported musculoskeletal diagnosis, narrative-laterality agreement, required clinical records and imaging, and payer authorization when required. Duplicate checks use patient demographics and condition.

**Evaluating each referral:**
1. Read `/referrals/<ID>` detail page and the referrals index.
2. **ICD-10 code check:**
   - M-codes (M00-M99) → musculoskeletal, valid chapter
   - S-codes (e.g., S83.241A) → injury codes, valid for orthopedics
   - E-codes (e.g., E11.9) → endocrine/metabolic, NOT valid for orthopedics
   - `chapter_valid`: true for M-codes and S-codes (musculoskeletal); false for E-codes and other non-MSK chapters
3. **Narrative match:** Does the Diagnosis Narrative match the ICD-10 code description?
   - M17.11 → "unilateral primary osteoarthritis, right knee" — match
   - M25.562 → should describe knee pain — match if consistent
   - E11.9 → "type 2 diabetes without complications" — matches the code but NOT an orthopedic diagnosis (chapter issue)
4. **Laterality match:** ICD-10 code laterality indicator (last digit) must match the Laterality field. M17.11 → right knee, laterality must be "right". If code has no laterality (like some E codes) and laterality is "n/a" → match. If code implies laterality but field disagrees → mismatch.
5. **Records/Imaging:** Records Received and Imaging Received must both be "yes" (or imaging "no" when not applicable).
6. **Authorization:** Check Authorization Status. `approved` → good. `missing` → authorization gap. `pending` → authorization follow-up. `not required` → no issue.
7. **Duplicate hints:** If Duplicate Hints is not "none" AND Linked Referral IDs are not empty → `duplicate_review` status applies.
8. **Referring practice contact:** If Practice name and phone/fax are both present, practice is reachable. Check that Phone and Fax fields exist.

**Readiness status:**
- `ready_to_schedule`: all checks pass
- `pending_records`: records or imaging missing
- `coding_clarification`: chapter invalid, narrative mismatch, or laterality mismatch
- `authorization_followup`: authorization missing or pending
- `duplicate_review`: duplicate hints active

**Issue codes** — collect all that apply:
- `invalid_chapter`: code not musculoskeletal
- `diagnosis_mismatch`: narrative doesn't match code
- `laterality_mismatch`: laterality field doesn't match code
- `missing_records`: Records Received = no
- `missing_imaging`: Imaging Received = no
- `authorization_gap`: Authorization = missing or pending
- `duplicate_referral`: Duplicate Hints is active

**Priority tier:**
- `schedule`: ready_to_schedule
- `tier_1`: one minor issue (e.g., only authorization pending)
- `tier_2`: multiple issues
- `tier_3`: duplicate review or invalid chapter

**Output fields:**
- `ready_count`: count of `ready_to_schedule`
- `follow_up_practices`: deduplicated sorted list of practice names that need follow-up (where readiness != ready_to_schedule)
- `follow_up_practice`: per referral, the practice name or null if ready_to_schedule

### 4. Chart Onboarding Readiness (CHR prefix)

**Policy POL-CHR-04:** Chart is ready only when demographics, history, applicable active problems, current vitals, onboarding care plan or clinical instructions, and orientation communication are complete.

**Evaluating each chart:**
1. Read `/charts/<ID>` detail page AND `/patients/<ID>` for demographics.
2. **Chart created:** `Chart Created: yes` — if "no", chart not created is a missing section.
3. **Missing sections** — collect from:
   - `chart_not_created`: Chart Created = no
   - `demographics`: Demographics Complete = no (chart page) OR any patient demographics = no
   - `history`: History Complete = no
   - `problems`: Problems Complete = no
   - `vitals`: Vitals.Current = no OR Vitals.Recorded Date > 90 days old
   - `care_plan_or_instructions`: Care Plan = missing/draft AND Clinical Instructions = not needed/missing/pending (i.e., neither care plan nor instructions are finalized)
   - `orientation_message`: Orientation Message != sent (queued, draft, missing, or "not sent")
4. **BMI class:** Compute from Vitals (if weight/height available — otherwise from BP context)
   - `not_available`: insufficient data
   - `normal`: BMI 18.5-24.9
   - `overweight`: BMI 25-29.9
   - `obese`: BMI ≥ 30
   - Note: The portal gives BP and pulse, not weight/height. BMI may need clinical inference from available data or defaults to `not_available` when weight/height are absent.
   - **Pragmatic rule:** When weight/height are not present in vitals, use `not_available` unless the patient conditions (e.g., Type 2 diabetes, hypertension) and BP readings strongly suggest a class. For this portal, BP alone is not enough — use `not_available`.
5. **Orientation state:**
   - `sent`: Orientation Message = sent
   - `queued`: Orientation Message = queued
   - `draft`: Orientation Message = draft
   - `missing`: Orientation Message = missing or empty
6. **Chart ready:** `true` when missing_sections is empty.
7. **Next owner:**
   - `registration_desk`: demographics incomplete
   - `clinical_intake`: history, problems, vitals, or care plan issues
   - `patient_communications`: orientation not sent
   - `ready`: chart_ready = true

**Output fields:**
- `ready_count`: count where chart_ready = true
- `problem_list_complete`: Problems Complete from chart detail

### 5. Chronic-Care Program Enrollment (CCP prefix)

**Policy POL-CCP-05:** Diabetes and hypertension pathways require active diagnosis, recent labs or vitals, consent, and a complete program form. Renal risk changes cadence and may require nurse escalation.

**Evaluating each program:**
1. Read `/programs/<ID>` detail page. Cross-reference `/benefits/<ID>`, `/charts/<ID>`, and `/patients/<ID>`.
2. **Active diagnosis check:** The program's Active Diagnoses field must support the Proposed Program.
   - "Cardiometabolic Combo" → needs diabetes AND hypertension
   - "Hypertension Pathway" → needs hypertension diagnosis
   - "Renal Risk Monitoring" → needs CKD or renal risk factor
   - "Diabetes Management" → needs Type 2 diabetes
3. **Labs/vitals:**
   - For diabetes programs: Recent HbA1c must be present (not blank)
   - For hypertension programs: BP must be present
   - `recent_hba1c_or_bp` missing item if the relevant value is absent
4. **Consent:**
   - `signed` → `consent_outcome: signed`
   - `not obtained` or `verbal pending signature` → `consent_outcome: not_obtained`
   - `declined` → `consent_outcome: declined`
5. **Program form:**
   - `complete` → good
   - `incomplete` → not sufficient (depends on program requirements)
   - `not started` → missing
6. **Enrollment decision:**
   - `enroll`: diagnosis support present, labs/vitals present, consent signed, form complete
   - `enroll_with_nurse_escalation`: all gates pass BUT renal flag = yes and HbA1c > 9.0 or BP severely elevated
   - `hold_missing_consent`: consent not signed/not obtained
   - `hold_missing_form`: form not complete/not started (and consent OK)
   - `clinical_review`: diagnosis mismatch or missing critical lab/vital
7. **Missing items** — collect:
   - `diagnosis_support`: program diagnoses don't match proposed program
   - `recent_hba1c_or_bp`: relevant lab/vital missing
   - `consent_signed`: consent not obtained
   - `program_form_complete`: form not complete
8. **Follow-up cadence:**
   - `weekly_nurse_call`: renal flag = yes AND (HbA1c > 8.5 or BP > 160/100)
   - `biweekly_checkin`: renal flag = yes (without the extreme values above) OR HbA1c > 8.0
   - `monthly_checkin`: all other cases
9. **Coordinator assignment:** Use the Coordinator field from the program detail page.
10. **Telehealth preference:** From `Telehealth Preference` on program detail.

**Output fields:**
- `coordinator_queue`: sorted list of patient IDs where coordinator is not empty/unassigned
- `escalation_count`: count of `enroll_with_nurse_escalation` decisions

## Cross-Domain Navigation Pattern

When solving any task:
1. Start at the relevant index page (e.g., `/patients`, `/transfers`)
2. Click into each specific record
3. Follow cross-links on the detail page to Benefits, Charts, Programs as needed
4. Check `/policies` for the domain policy
5. Check `/queue` for any linked queue items for the records
6. Check `/documents` for reference checklists

## Output Conventions

- **All arrays must be sorted** ascending by their ID field (patient_id, transfer_id, referral_id)
- **Use only the enum strings** shown in the answer template — never invent new values
- **No extra keys** in JSON output — match the template exactly
- **No narrative explanations** or evidence notes in the final output
- **Boolean fields** use JSON `true`/`false`, not strings
- **Null fields** use JSON `null`, not "null" or ""
- **Empty arrays** use `[]`, not null
- **Count fields** are integers, not strings

## Common Pitfalls

1. **"Medication Managed" determines PBM/Pharmacy gate applicability.** Always check this field on the patient detail page before deciding pbm/pharmacy are required.
2. **Badge class ≠ data value.** `badge good` on a smoking status does not mean "good health" — it means the field is populated. Read the actual text content.
3. **Session expiry.** The cookie times out. If pages redirect to `/login`, re-authenticate.
4. **Cross-referencing is essential.** A patient detail page alone is insufficient — always check `/benefits/<ID>`, `/charts/<ID>`, and `/programs/<ID>` for the full picture.
5. **Staleness calculations use the requested start date**, not "today." For transfers, labs must be ≤30 days before start, infection screens ≤14 days.
6. **Risk is a clinical synthesis** — there is no single "risk" field on the portal. Combine clinical indicators.
7. **Duplicate hints are ambiguous.** "Same physician only" means the same doctor referred but not necessarily a duplicate. "Same condition within 30 days" or "similar name same DOB" are stronger signals.
8. **Consent on the patient page (Demographics.Consent Signed) is different from program consent (Consent Status on /programs).** They serve different purposes.
9. **Authorization on referrals is payer auth; on transfers it's a packet document.** Don't confuse them.
10. **Empty/blank values in HbA1c or Active Problem Codes mean missing data**, not zero problems. An empty problem codes field is a problem.
