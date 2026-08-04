 # Cedar Ridge Intake Coordination — Skill

 ## Purpose

 Solve healthcare intake-coordination tasks against the Cedar Ridge shared data portal. Every task involves reading a prompt, exploring the portal's data through REST and read-only SQL, mapping findings into a strict JSON answer template, and submitting the most accurate answer possible.

 ## Portal access

 The base URL is provided through a `<TASK_ENV_BASE_URL>` placeholder or an equivalent environment variable. All examples below use that same base.

 ### REST endpoints (all GET, read-only)

 | Endpoint | Description |
 |---|---|
 | `/` | Portal landing page |
 | `/patients?q=&limit=` | Search patients by name or id |
 | `/patients/{patient_id}` | Full patient profile (chart, coverage, pbm, pharmacy, rosters, referrals, transfers, documents, lifestyle, clinical history, program candidates) |
 | `/referrals?batch_id=&service_line=&limit=` | Search referrals |
 | `/referrals/{referral_id}` | Single referral detail |
 | `/transfers?batch_id=&limit=` | Search transfer requests |
 | `/transfers/{transfer_id}` | Single transfer detail |
 | `/documents` | Document index |
 | `/chart/{patient_id}` | Patient chart artifacts |
 | `/programs/{program_code}/candidates` | Program candidate list with patient demographics |
 | `/icd/{code}` | ICD-10 code metadata (description, chapter, service_family, laterality) |
 | `/pharmacies` | Pharmacy directory with network status |

 ### SQL endpoint

 `POST /query` with JSON body `{"sql": "<string>", "params": ["<value>"]}`.

 This is the primary exploration tool. Always start by listing tables:

 ```sql
 SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name
 ```

 Then inspect schemas:

 ```sql
 SELECT sql FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name
 ```

 Use parameterized queries for values, but bare string interpolation for column/table names when the SQL endpoint requires it. Prefer `SELECT *` with targeted WHERE clauses over complex JOINs unless cross-table reconciliation is needed.

 ## Core data model

 Key tables (see `schema_reference.md` for full DDL):

 - **patients** — demographics, contact info, existing_chart flag, emergency_contact_present
 - **coverage** — insurance policies per patient: payer, policy_number, status (active/expired/pending), service_lines covered, network_status, termination_date
 - **pbm** — pharmacy benefit manager records: active flag, formulary_status, policy_number (must match coverage), specialty_required, status
 - **patient_pharmacy** + **pharmacies** — preferred pharmacies per patient with network_status
 - **lifestyle** — smoking_status, alcohol_use, exercise_frequency, sleep_hours
 - **clinical_history** — chronic_conditions, medication_count, allergy_count, recent_hospitalization, risk_flags
 - **referrals** — referral_id, batch_id, service_line, patient_id, icd10_code, diagnosis_description, referral_reason, urgency, records_received, imaging_received, auth_required, auth_status, appointment_scheduled, insurance_id, assigned_physician, notes
 - **transfer_requests** — transfer_id, batch_id, patient_id, referring_facility, requested_start_date, modality, days_requested, chair_window, transportation
 - **documents** — document_id, patient_id, referral_id/transfer_id, doc_type, status, finalized, received_date
 - **icd_codes** — code, description, chapter, service_family, laterality
 - **intake_rosters** — roster_id, patient_id, requested_service_date, service_line
 - **facility_capacity** — location_id, date, modality, open_chairs
 - **program_candidates** — program_code, patient_id, consent_status, target_condition, adherence_score, preferred_outreach
 - **chart_artifacts** — patient_id, artifact_type, status, last_updated

 ## General workflow

 ### 1. Read the prompt and answer template

 Every task provides:
 - `input/prompt.txt` — natural-language description of what to produce
 - `input/payloads/answer_template.json` — exact JSON shape with allowed enum values, required keys, ordering rules, and precision notes
 - Optionally `input/payloads/target_roster.json` or similar — lookup data (batch ids, patient lists)

 Read the template first. It defines the exact contract: every key, every allowed value, ordering rules, and numeric precision. The template is authoritative.

 ### 2. Explore the data

 Use the SQL endpoint to pull all relevant records in bulk:
 - Filter by the batch/roster/program id from the prompt
 - Pull patient profiles, coverage, pbm, pharmacies, lifestyle, and clinical history for every relevant patient
 - Pull document records for every relevant referral or transfer
 - Pull ICD metadata for every code that appears
 - Pull facility capacity for relevant dates when applicable

 The per-patient REST endpoint (`/patients/{id}`) can serve as a cross-check because it aggregates patient + coverage + pbm + pharmacy + rosters + referrals + transfers + documents + lifestyle + clinical_history + chart_artifacts in one call.

 ### 3. Map data to template fields

 For each field in the template:
 - Identify which data column(s) drive the value
 - Apply the decision rule consistently across all entities
 - Use only the allowed enum values — never invent new ones
 - Respect ordering rules (ascending by id, alphabetical, unordered set)

 #### Common mapping patterns

 **Insurance / coverage status:**
 - `valid` — coverage exists, status is `active`, and the coverage's `service_lines` column contains the target service line
 - `invalid` — coverage exists but status is `expired`, or service_lines does not contain the target service line
 - `missing` — no coverage record exists, or status is `pending`

 **Prescription / PBM status:**
 - `valid` — pbm record exists, `active = 1`, `status = 'approved'`, and `policy_number` matches the coverage policy
 - `invalid` — pbm exists but has mismatched policy, inactive, rejected, or pending
 - `missing` — no pbm record exists

 **Pharmacy network status:**
 - Use the patient's rank-1 preferred pharmacy from `patient_pharmacy` joined with `pharmacies`
 - `in_network` or `out_of_network` per the pharmacy record; `unknown` if no pharmacy assigned

 **Readiness/registration status:**
 - `ready` / `approved` — no blocking issues; all required records, imaging, and authorizations are in order
 - `blocked` / `hold` — fixable issues exist (missing records, pending auth, missing documents)
 - `under_review` / `clinical_review` — requires human judgment (duplicates, clinical discrepancies, high risk)
 - `rejected` / `admin_followup` — hard blockers (declined consent, wrong condition, expired coverage with no alternatives, already-scheduled conflicts)

 **ICD / clinical code discrepancies:**
 - Compare `icd_codes.service_family` against the referral's `service_line`
 - A mismatch (e.g., cardiology code on a pulmonary referral) is a `clinical_code_discrepancy` / `icd_chapter_mismatch`
 - Symptom codes (R00-R99 chapter) used as primary diagnosis on a specialty referral may also be flagged

 **Duplicate detection:**
 - Same patient appearing multiple times in the same batch with same or similar ICD → duplicate
 - Same insurance_id on referrals for different patients → shared insurance anomaly
 - Notes field containing "duplicate" or unusual assigned_physician text → flag for review

 **Document completeness & staleness:**
 - A document is "missing" if no record exists for that doc_type on the entity, or if `finalized = 0`
 - Staleness: compare `received_date` to a reference date (requested start, service date, or current date) against freshness limits. Typical limits: 30 days for labs and infectious disease screens, 365 days for physicals and vaccines
 - The set of required document types is task-specific; consult the template's allowed values

 **Capacity / feasibility:**
 - Query `facility_capacity` for the target modality on the requested date
 - If no capacity record exists for that exact date, check the nearest date or treat as unavailable (0 chairs)
 - Feasibility combines packet completeness with capacity availability

 **Program eligibility:**
 - `eligible` is driven by `program_candidates.target_condition` matching the program's target condition
 - Enrollment status (`enroll`/`hold`/`reject`) additionally considers consent_status, existing_chart, chart artifact freshness, and clinical flags

 **Risk scoring (lifestyle / overall):**
 - Derive from lifestyle table fields (smoking, alcohol, exercise, sleep) combined with clinical_history risk_flags, recent_hospitalization, chronic_conditions
 - Current smoking, heavy alcohol use, no exercise, and sleep < 6h all elevate risk
 - `overall_risk_high` is typically a blocker code

 ### 4. Compute cohort summaries

 After every patient/entity row is decided, compute aggregate counts:
 - Count patients by each registration/readiness/enrollment status
 - Count by risk levels, follow-up cadences, outreach channels, monitoring packages
 - Verify that row counts sum to total and that cross-tabulations are consistent with individual decisions

 ### 5. Validate before submitting

 - Every required top-level key is present
 - Every patient/entity id appears exactly once in the ordered list
 - All enum values are from the template's allowed lists
 - All integer counts are exact (not floats)
 - All date strings use YYYY-MM-DD format
 - Lists with "unordered set" ordering have no meaningful order requirement
 - Lists with "ascending" ordering are sorted accordingly

 ## Iterative refinement

 Each task allows a fixed number of judge-feedback rounds. Use each round purposefully:
 - **Round 1** — submit your best initial answer based on thorough data exploration
 - **Round 2** — adjust based on the score change: if score decreased, revert toward round 1; if increased, continue in that direction
 - **Round 3** — make targeted, high-confidence changes only; avoid changing fields that didn't affect the score in prior rounds

 The judge returns only a score and a correct boolean. Treat the score as a signal: larger changes in score indicate you've touched fields that matter. Fields that don't change the score across rounds are likely already near-optimal or irrelevant to scoring.

 ## Common pitfalls

 - **Assuming eligibility = consent + chart**: Eligibility is typically determined by matching criteria (target condition, service line) independently of consent or chart status. Consent and chart determine enrollment/registration status, not eligibility.
 - **Over-flagging ICD discrepancies**: Not every symptom code or generic description is a discrepancy. Focus on service_family mismatches between ICD and referral service_line.
 - **Missing the notes field**: The `notes` column on referrals often contains flags like "possible duplicate" or unusual assigned_physician values that signal data quality issues.
 - **Staleness thresholds**: Don't assume universal freshness limits. The correct thresholds are domain-specific (dialysis, primary care, chronic care all differ). Start with conservative estimates and adjust based on feedback.
 - **Transportation as a document vs field**: The `transportation` field on transfer_requests is a transport mode, not a required document. Only treat it as a document if the template explicitly lists "transportation" as a document type.
 - **Capacity on non-dialysis days**: Facility capacity may only be recorded on operating days (e.g., M/W/F for dialysis). Dates without entries should be treated as unavailable unless the task context suggests otherwise.
 - **Draft documents**: Documents with `finalized = 0` (draft) are incomplete regardless of `status`; treat them as missing.
 - **Preferred contact availability**: If a patient's `preferred_contact` is "email" but `email` is null, or "sms"/"phone" but `phone` is null, the contact method is unavailable — flag with `preferred_contact_unavailable`.
