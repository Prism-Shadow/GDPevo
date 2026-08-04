## Skill: Cedar Ridge Intake Coordination

This skill covers the Cedar Ridge Intake Coordination Portal, a healthcare-intake workflow system. Follow these rules to complete intake verification, referral readiness audits, transfer reviews, program enrollment panels, and referral-to-chart activation tasks.

### Operating Model

1. **Read the task prompt first.** Identify the intake workflow type, the batch/roster/program identifier, and any special instructions. Classify the workflow: patient access verification, referral readiness audit, transfer review, program enrollment panel, or referral-to-chart activation.

2. **Read `input/payloads/answer_template.json` next.** This defines the exact JSON output shape, every required key, all controlled-value enumerations, ordering rules (usually ascending by ID), and summary-count structures. The template is authoritative — never invent keys, values, or ordering that it does not specify.

3. **Use `<TASK_ENV_BASE_URL>` as the base URL.** The portal is a REST API with the following endpoints (from `environment_access.md`):
   - `GET /` — root health/description
   - `GET /patients` — list patients; `GET /patients/{patient_id}` — single patient record
   - `GET /referrals` — list referrals; `GET /referrals/{referral_id}` — single referral
   - `GET /transfers` — list transfers; `GET /transfers/{transfer_id}` — single transfer
   - `GET /documents` — document metadata index
   - `GET /chart/{patient_id}` — chart record for a patient
   - `GET /programs/{program_code}/candidates` — candidates for a program
   - `GET /icd/{code}` — ICD-10 code metadata
   - `GET /pharmacies` — pharmacy directory
   - `POST /query` — read-only SQL endpoint: JSON body `{"sql": "<string>", "params": [...]}`

4. **Gather data systematically.** Based on the workflow type, use the appropriate endpoints:
   - *Patient access verification*: `/patients/{id}`, `/chart/{patient_id}`, `/pharmacies`, plus any roster payload in `input/payloads/`.
   - *Referral readiness audit*: `/referrals`, `/referrals/{id}`, `/patients/{id}`, `/icd/{code}`, `/documents`, and `/chart/{patient_id}`.
   - *Transfer review*: `/transfers`, `/transfers/{id}`, `/patients/{id}`, `/documents`, and check capacity data.
   - *Program enrollment*: `/programs/{code}/candidates`, `/patients/{id}`, `/chart/{patient_id}`.
   - *Referral-to-chart activation*: `/referrals`, `/referrals/{id}`, `/patients/{id}`, `/chart/{patient_id}`, `/documents`, `/icd/{code}`.

5. **Use `POST /query` for reconciliation queries.** When the task requires cross-referencing records, detecting duplicates, finding missing items, or joining data across resources, prefer SQL queries. Start by listing available tables with `SELECT name FROM sqlite_master WHERE type='table'` and explore schemas with `PRAGMA table_info(...)`.

### Reconciliation and Decision Rules

Follow these patterns (exact criteria come from the answer template's controlled values):

- **Insurance**: Check coverage validity, prescription benefit (PBM) status, and preferred-pharmacy network membership. Status: `valid`, `invalid`, `missing`. Pharmacy: `in_network`, `out_of_network`, `unknown`.

- **Risk assessment**: Evaluate lifestyle risk and overall risk as `low`, `medium`, or `high` based on chart data, documented conditions, and clinical history.

- **Registration/disposition status**: Assign `approved`, `hold`, `clinical_review`, or `rejected` based on the conjunction of insurance, pharmacy, risk, and missing-data findings.

- **Referral readiness**: Assign `ready`, `blocked`, `under_review`, or `admin_followup`. Blockers include clinical-code discrepancies (ICD chapter mismatch, narrative mismatch, laterality mismatch), missing records, missing imaging, authorization issues, duplicates, and premature scheduling.

- **ICD/code validation**: For each referral, compare the referral's ICD-10 code against `/icd/{code}` to determine the expected chapter. Flag any mismatch between the code's chapter and the referral's clinical narrative or body site.

- **Duplicate detection**: Group referrals by patient ID, service date, and service line. Within each group identify the primary referral (e.g., earliest, most complete) and recommend `consolidate_to_primary` or `keep_separate`.

- **Document completeness**: Check that all documents required by the template are present. For time-sensitive documents (labs, vaccines, H&P, PPD/CXR), check received dates against freshness limits. Classify as `complete` or `incomplete`; list missing codes and stale items.

- **Authorization**: Check each referral's authorization status. If `pending`, `denied`, or `not_submitted`, flag as an auth blocker.

- **Capacity feasibility** (transfers): Compare requested start dates against available chair/open-slot counts. If capacity is insufficient on the requested date, mark `capacity_unavailable`.

- **Program eligibility** (enrollment panels): Verify the patient has an active chart, meets the program's target-condition criteria (e.g., active diagnosis codes), has recent vitals and labs, and has consent on file. Assign `enroll`, `hold`, or `reject`.

### Output Rules

1. **Return a single JSON object** matching the answer template exactly.
2. **Use only controlled values.** Never invent a reason code, status, or tier that is not in the template's `allowed_values`.
3. **Order lists as specified.** Usually ascending by patient_id, referral_id, or transfer_id. Unordered sets (reason codes, blocker codes) may appear in any order but should be alphabetically sorted for consistency.
4. **No prose outside the JSON.** The final response must be pure JSON unless the prompt explicitly says otherwise.
5. **Cohort summaries.** Every task requires summary counts. Count by status, risk tier, urgency, decision, or monitoring package as the template dictates. Use integer counts with no fractions or percentages unless the template specifies them.
6. **Use uppercase IDs** exactly as returned by the portal — do not downcase.

### Common Patterns

- **Batch/roster identifiers** appear in the prompt (e.g., `NPI-JUN-01`, `ORTHO-JUN-01`, `DIAL-WINTER-01`, `PULM-JUN-02`) or in `input/payloads/target_roster.json`.
- **Program codes** appear in the prompt path (e.g., `DMHTN-2026A`).
- **Service date and service line** may come from a roster record in the portal rather than the prompt — query the relevant endpoint when the prompt says "recorded for that roster."
- **Blocked reason codes** are tracked per patient/referral and aggregated in blocker sets — list all that apply, not just the first.
- **Priority tiers** rank follow-up items: `tier_1_immediate` (clinical safety, urgent gaps), `tier_2_short_term` (missing artifacts that can be resolved quickly), `tier_3_administrative` (paperwork, scheduling coordination).
- **Correspondence/outreach** maps to specific channels (`phone`, `portal`, `sms`, `email`, `fax_referring_facility`, `internal_queue`) and templates (`clinical_code_clarification`, `auth_records_request`, `duplicate_resolution`, `appointment_hold_notice`).

### Error Handling

- If an endpoint returns no data or a 404, treat the resource as missing and reflect that in the output (e.g., `missing_records`, `chart_not_active`).
- If the SQL endpoint returns an error, fall back to GET-endpoint-only reconciliation and note the limitation only if the template requires the SQL-derived data.
- If a patient, referral, or transfer ID from the batch/roster is not found in the portal, include it in the output with status `missing` or the nearest applicable controlled value and flag it in blocker/reason codes.
