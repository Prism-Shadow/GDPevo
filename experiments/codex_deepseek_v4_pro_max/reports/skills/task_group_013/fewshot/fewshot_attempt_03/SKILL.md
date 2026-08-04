## Cedar Ridge Intake Coordination Portal

Use this skill whenever a task references the Cedar Ridge Intake Coordination Portal, an intake-coordination workflow (patient registration, referral audit, transfer review, chronic-care enrollment, chart activation), or any endpoint starting with `<TASK_ENV_BASE_URL>` whose shape matches the portal API described below.

### Portal Overview

The Cedar Ridge Intake Coordination Portal is a read-only REST + SQL API serving patient, referral, transfer, document, chart, ICD, pharmacy, and program-candidate data for a multi-specialty healthcare organization. All intake-coordination tasks follow the same general pattern: **collect data from the relevant API endpoints, cross-reference and reconcile records, apply business rules to classify each record, and emit a single JSON object matching the provided answer template**.

### Available API Endpoints

All endpoints are relative to the task's base URL (supplied as `<TASK_ENV_BASE_URL>` in the prompt or a payload file like `target_roster.json`).

**Patients**
- `GET /patients` — searchable list (`?q=name_or_id&limit=N`); returns patient demographics (`patient_id`, `first_name`, `last_name`, `dob`, `address`, `phone`, `email`, `language`, `emergency_contact_present`, `existing_chart`, `preferred_contact`).
- `GET /patients/{patient_id}` — aggregate view bundling `patient`, `coverage[]`, `pbm[]`, `lifestyle`, `pharmacies[]`, `referrals[]`, `transfers[]`, `documents[]`, `rosters[]`, `chart_artifacts[]`, `clinical_history`, and `program_candidates[]`.

**Referrals**
- `GET /referrals` — filter by `?batch_id=` and/or `?service_line=`; returns a `referrals[]` array. Each referral carries `referral_id`, `patient_id`, `batch_id`, `service_line`, `icd10_code`, `diagnosis_description`, `referral_reason`, `urgency`, `insurance_id`, `payer`, `auth_required`, `auth_status`, `records_received` (0/1), `imaging_received` (0/1), `appointment_scheduled` (0/1), `appointment_date`, `date_received`, `referring_physician`, `referring_practice`, `referring_phone`, `referring_fax`, `assigned_physician`, `notes`.
- `GET /referrals/{referral_id}` — single referral detail.

**Transfers**
- `GET /transfers` — filter by `?batch_id=`; returns `transfer_id`, `patient_id`, `batch_id`, `referring_facility`, `modality`, `days_requested`, `chair_window`, `requested_start_date`, `requested_end_date`, `transportation`, `status_note`.
- `GET /transfers/{transfer_id}` — single transfer.

**Documents**
- `GET /documents` — filter by `?patient_id=` or `?transfer_id=`; returns `document_id`, `patient_id`, `transfer_id`, `referral_id`, `doc_type`, `content_tag`, `received_date`, `service_date`, `status` (`draft`/`final`), `finalized` (0/1), `notes`.

**Chart**
- `GET /chart/{patient_id}` — returns `chart_artifacts[]` (each with `artifact_id`, `artifact_type`, `patient_id`, `status`, `last_updated`, `value_summary`), `active_problems[]`, `clinical_history` (`chronic_conditions`, `medication_count`, `allergy_count`, `recent_hospitalization`, `surgeries`, `risk_flags`), plus `allergies[]`, `medications[]`, `vitals[]`, `labs[]` where present.

**ICD Codes**
- `GET /icd/{code}` — returns `icd.code`, `icd.chapter`, `icd.description`, `icd.laterality`, `icd.service_family`.

**Pharmacies**
- `GET /pharmacies` — returns all pharmacy records: `pharmacy_id`, `name`, `address`, `phone`, `network_status` (`in_network`/`out_of_network`).

**Program Candidates**
- `GET /programs/{program_code}/candidates` — returns `candidates[]` with `patient_id`, `first_name`, `last_name`, `dob`, `phone`, `email`, `program_code`, `target_condition`, `consent_status`, `adherence_score`, `preferred_outreach`, `existing_chart`, `source`, `candidate_date`.

**Read-only SQL**
- `POST /query` with `{"sql":"<SELECT only>","params":[]}` — returns `columns[]`, `rows[]`, `row_count`. The underlying SQLite database exposes these tables: `patients`, `coverage`, `pbm`, `lifestyle`, `patient_pharmacy`, `pharmacies`, `referrals`, `transfer_requests`, `documents`, `chart_artifacts`, `clinical_history`, `intake_rosters`, `icd_codes`, `facility_capacity`, `program_candidates`. Use this endpoint to reconcile records across tables, verify cross-references, and compute cohort-level counts.

### General Workflow

1. **Orient from the prompt**: Identify the workflow type (patient access, referral audit, transfer review, enrollment panel, chart activation), the batch/roster/program identifier, and the list of target entities.

2. **Read the answer template**: Every task supplies an `answer_template.json` inside `input/payloads/`. Study its `required_top_level_keys`, field schemas, `allowed_values` enums, `ordering` rules, and `required_keys` for summary sections. The template is the authoritative specification for the output shape.

3. **Collect data**: Query every relevant endpoint. Prefer fetching the full batch (e.g., `GET /referrals?batch_id=ORTHO-JUN-01`) rather than individual records; fall back to per-record fetches when per-patient detail (chart, insurance, documents) is needed. Use the SQL endpoint for cross-table joins that are awkward through the REST endpoints.

4. **Reconcile and cross-reference**: Join records across endpoints using shared keys (`patient_id`, `referral_id`, `transfer_id`, `insurance_id`). Common reconciliation patterns:
   - **ICD validation**: Compare a referral's `icd10_code` against `/icd/{code}`. Flag `icd_chapter_mismatch` when `icd.chapter` does not match the expected chapter for the referral's `service_line` (e.g., orthopedics expects `M00-M99`, not `S00-T88`). Flag `laterality_mismatch` when the ICD laterality contradicts narrative/diagnosis text. Flag `narrative_mismatch` when `diagnosis_description` does not align with the ICD code's description.
   - **Insurance reconciliation**: Cross-reference `insurance_id` across referrals. When two referrals from *different* patients share the same `insurance_id`, flag `shared_insurance_anomaly` → `verify_distinct_patient_policy_id`. When two referrals from the *same* patient share the same `insurance_id`, disposition is `legitimate_duplicate_same_patient`.
   - **Duplicate detection**: When the same patient has multiple referrals in a batch with similar ICD codes, dates, and referring physicians, identify a duplicate group. Assign a `group_id`, select a `primary_referral_id` (earliest `date_received` or lowest `referral_id`), and recommend `consolidate_to_primary`.
   - **Document/packet completeness**: Compare the received `documents[]` for a patient against the required document checklist for the workflow. A document is missing when there is no finalized (`finalized=1`, `status=final`) document of the required type. A document is stale when its `received_date` is older than the `freshness_limit_days` from the reference date (usually "today" or `as_of_date`).

5. **Apply business rules**: Derive statuses and classifications from raw data:
   - **Insurance status**: Check `coverage[].status`. `active` → `valid`; `expired`/`terminated` with past `termination_date` → `invalid`/`coverage_expired`; no coverage record → `missing`.
   - **PBM (prescription benefit) status**: Check `pbm[].status` and `pbm[].active`. `approved` + `active=1` → `valid`; `denied`/`inactive` → `invalid`; no PBM record → `missing`.
   - **Pharmacy network**: Check the patient's preferred pharmacy (from `pharmacies[]` in the patient aggregate, ordered by `preference_rank`). `network_status=in_network` → `in_network`; `out_of_network` → `out_of_network`; no pharmacy → `unknown`.
   - **Lifestyle risk**: Derive from `lifestyle` fields (`smoking_status`, `alcohol_use`, `exercise_frequency`, `sleep_hours`). Current smoking + no exercise + high alcohol → `high`; one moderate risk factor → `medium`; none → `low`.
   - **Overall risk**: Combine lifestyle risk, clinical history flags (`risk_flags`, `recent_hospitalization`, chronic conditions), and insurance/PBM issues. Multiple red flags → `high`.
   - **Registration/enrollment status**: Combine all signals. `approved`/`enroll` when all checks pass; `hold`/`clinical_review` when some issues are resolvable; `rejected` when blockers are hard (e.g., `consent_declined`, `wrong_target_condition`, `coverage_expired` + `excluded_service_line`).
   - **Readiness status**: `ready` = no blockers; `blocked` = hard blockers (auth denied, missing records/imaging); `under_review` = soft issues (ICD discrepancy, duplicates); `admin_followup` = administrative issues (insurance anomaly, scheduling conflicts).
   - **Feasibility for transfers**: Cross-reference `requested_start_date` against `facility_capacity` (query via SQL). If `open_chairs > 0` on that date, capacity is `available`. Feasibility logic: packet complete + capacity available → `ready_on_requested_start`; packet incomplete + capacity available → `packet_not_ready_capacity_available`; packet incomplete + capacity unavailable → `packet_not_ready_capacity_unavailable`; packet complete + capacity unavailable → `capacity_unavailable`.

6. **Assemble the JSON output**: Build the JSON strictly following the answer template. Key rules:
   - Lists of IDs are sorted **ascending** (lexicographic for strings like `P001`, `REF0001`).
   - Reason-code and blocker-code arrays are treated as **unordered sets** — any order is acceptable, but prefer consistent ordering (alphabetical or as-listed in the template).
   - Use **exactly** the enum values from the template's `allowed_values`; do not invent new codes.
   - All patient/referral/transfer IDs must match the portal's casing (uppercase).
   - Counts in summary sections must be **integers** that sum correctly to the total.
   - Counts by status/category must cover **all** possible enum values, even when the count is zero.
   - `null` is allowed only where the template explicitly permits it (e.g., `priority_tier` when a referral has no follow-up tier, or `first_checkin_days` for `not_applicable` packages).

7. **Validate before delivering**: Verify that every required key is present, every patient/entity from the batch is included, sort orders are correct, and all enum values are from the allowed set. Run quick sanity checks on summary counts (they must sum to the cohort total).

### Workflow-Specific Guidance

**Patient Access Verification (roster-based)**
- Target patients come from the roster (listed in `target_roster.json` or the task prompt). Fetch each patient's aggregate view (`/patients/{id}`) to get coverage, PBM, pharmacy, and lifestyle data.
- The `requested_service_date` and `service_line` come from the roster record.
- Blocked reason codes apply at the patient level. Common triggers: `coverage_expired` (coverage status=expired), `coverage_pending` (status=pending), `pbm_invalid`/`pbm_missing`/`pbm_policy_mismatch`, `pharmacy_out_of_network`/`pharmacy_unknown`, `excluded_service_line` (roster's service_line not in coverage.service_lines), `missing_address`, `emergency_contact_missing`, `preferred_contact_unavailable`, `overall_risk_high`.

**Referral Audit (batch-based)**
- Fetch all referrals for the batch, then cross-reference each referral's patient against `/patients/{id}`, ICD against `/icd/{code}`, and documents against `/documents?patient_id=`.
- Derive readiness per referral, then compute the cohort's `ready_to_schedule` list, `action_plan`, and summary counts by urgency and readiness status.
- `action_codes` map directly to issue codes: `icd_chapter_mismatch` → `request_corrected_icd`; `duplicate_referral` → `consolidate_duplicate`; `shared_insurance_anomaly` → `verify_insurance_id`; `missing_records` → `request_records`; `missing_imaging` → `request_imaging`; `auth_blocker` → `resolve_authorization`; `already_scheduled` → `review_existing_appointment`.

**Transfer Review (batch-based)**
- Fetch all transfers for the batch, then each patient's documents and chart data. Document completeness is evaluated against a transfer-packet checklist (common required types: `face_sheet`, `history_physical`, `physician_orders`, `medication_list`, `allergy_list`, `insurance_proof`, `hbsag`, `hep_b_antibody_core`, `ppd_or_cxr`, `flu_vaccine`, `pneumonia_vaccine`, `monthly_labs`, `treatment_flowsheets`, `vascular_access_report`, `transportation`).
- Staleness is computed per doc type with its own `freshness_limit_days` (30 days for most labs/vaccines, 365 days for `history_physical`).
- Capacity is checked via SQL against `facility_capacity` for the requested start date. A document is stale when `received_date` is before `(reference_date - freshness_limit_days)`.

**Enrollment Panel (program-based)**
- Fetch all candidates from `/programs/{code}/candidates`, then each candidate's chart via `/chart/{id}`.
- Eligibility requires: (a) `target_condition` matches the program, (b) the patient has an active chart with the relevant diagnosis in `active_problems`, (c) consent is not declined.
- `follow_up_cadence` maps to clinical flags: `recent_hospitalization`/`recent_ed`/`low_adherence` → `weekly` (high-touch); `ckd` comorbidity → `biweekly`; standard → `monthly`; chart-deficient → `deferred`.
- `missing_chart_artifacts` are the artifact types required but absent or stale from `/chart/{id}`.
- `initial_monitoring_package` selection: high-touch patients get `high_touch_dm_htn` with full components; standard patients get `standard_dm_htn`; deferred patients get `deferred` with consent/chart-update components; ineligible/rejected patients get `not_applicable`.

**Chart Activation (referral-to-chart)**
- For referrals that are `ready`, determine what chart artifacts need to be created or updated based on the patient's `existing_chart` flag and current chart contents from `/chart/{id}`.
- `chart_action`: `create_chart` when `existing_chart=0`; `update_chart` when `existing_chart=1` but artifacts are missing; `no_chart_action` otherwise.
- `correspondence_queue` entries map non-ready referrals to the appropriate `template_type` and `reason_codes`.
- `priority_order` ranks non-ready referrals from highest to lowest tier: all `tier_1_immediate` first, then `tier_2_short_term`, then `tier_3_administrative`.

### SQL Query Patterns

Use the SQL endpoint for efficient cross-table reconciliation. Common query patterns:
- Find all referrals for a batch: `SELECT * FROM referrals WHERE batch_id = ?`
- Join referrals to ICD metadata: `SELECT r.referral_id, r.icd10_code, i.chapter, i.service_family FROM referrals r JOIN icd_codes i ON r.icd10_code = i.code WHERE r.batch_id = ?`
- Find duplicate referrals: `SELECT patient_id, COUNT(*) as cnt, GROUP_CONCAT(referral_id) as ids FROM referrals WHERE batch_id = ? GROUP BY patient_id HAVING cnt > 1`
- Find shared insurance anomalies: `SELECT insurance_id, COUNT(*) as cnt, GROUP_CONCAT(referral_id) as refs, GROUP_CONCAT(DISTINCT patient_id) as pts FROM referrals WHERE batch_id = ? AND insurance_id IS NOT NULL GROUP BY insurance_id HAVING COUNT(DISTINCT patient_id) > 1`
- Check capacity: `SELECT date, open_chairs_total FROM facility_capacity WHERE date = ?`
- Count documents by patient and type: `SELECT patient_id, doc_type, status, finalized, received_date FROM documents WHERE patient_id IN (...)`

### Output Rules (Always)

- **Only JSON** in the final response. No prose, no markdown fences, no explanations.
- Lists are ordered as specified in the template (almost always ascending by ID).
- Code arrays are unordered sets but should be listed consistently.
- Every enum field must use a value from the template's `allowed_values` list.
- Summary counts are integers. Every possible category must appear, even with a count of zero.
- Do not include extra top-level keys beyond those declared in the template.
- Use `null` only where the template explicitly permits it.
