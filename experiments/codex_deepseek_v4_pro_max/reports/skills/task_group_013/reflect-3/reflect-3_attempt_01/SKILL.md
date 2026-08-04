## Cedar Ridge Intake Coordination — Reusable Skill

### Environment Use
- The environment exposes a read-only HTTP API and a read-only SQL endpoint at a shared base URL.
- Always start by listing available database tables through the SQL endpoint: `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`.
- Use the SQL endpoint for flexible cross-table queries; use the REST endpoints (`/patients`, `/referrals`, `/transfers`, `/documents`, `/chart/{id}`, `/programs/{code}/candidates`, `/icd/{code}`, `/pharmacies`) for quick single-entity lookups.
- Expect payer, insurance_id, policy_number, and coverage fields to sometimes be inconsistent across referral and coverage records—always cross-reference both tables.

### Data Architecture
| Table | Purpose |
|---|---|
| `patients` | Demographics, contact preferences, existing_chart flag |
| `coverage` | Insurance coverage per patient (payer, policy_number, status, network_status, service_lines) |
| `pbm` | Pharmacy benefit manager records (active, status, policy_number match vs coverage) |
| `patient_pharmacy` | Patient-to-pharmacy assignments with preference_rank |
| `pharmacies` | Pharmacy directory with network_status |
| `lifestyle` | Smoking, alcohol, exercise, sleep data per patient |
| `intake_rosters` | New-patient intake batches (roster_id, patient_id, requested_service_date, service_line) |
| `referrals` | Referral records with clinical, insurance, document, and authorization fields |
| `transfer_requests` | Dialysis transfer batches with modality, chair_window, days_requested |
| `documents` | Patient documents keyed by transfer_id or referral_id; check `finalized` (1/0) and `received_date` |
| `facility_capacity` | Open chairs per location/date/modality |
| `icd_codes` | ICD-10 metadata (chapter, service_family, laterality, description) |
| `chart_artifacts` | Per-patient chart components (artifact_type, status, last_updated) |
| `clinical_history` | Chronic conditions, surgeries, medication_count, risk_flags, recent_hospitalization |
| `program_candidates` | Program enrollment candidates with consent_status, adherence_score, target_condition |

### Coverage & Insurance Rules
- **Coverage validity**: coverage is `valid` when status=`active`, network_status=`in_network`, and `service_lines` includes the target service line. Mark `invalid` when status is `expired` or `pending`, or when the needed service line is absent (`excluded_service_line`). Mark `missing` when no coverage record exists.
- **PBM validity**: valid when `active`=1, `status`=`approved`, and `policy_number` matches the coverage policy. A `policy_number` mismatch is `pbm_policy_mismatch`; a rejected or inactive PBM is `pbm_invalid`; a missing record is `pbm_missing`.
- **Pharmacy network**: look up the patient's rank-1 pharmacy in `pharmacies`; `in_network` or `out_of_network` based on the pharmacy's `network_status`. No pharmacy record means `unknown`.

### Document Completeness & Freshness
- A document is **present** if a row exists in the `documents` table for the given transfer/referral and doc_type, regardless of `finalized` status. A document is **finalized** only if `finalized`=1.
- **Staleness** applies to these document types only: `hbsag`, `hep_b_antibody_core`, `history_physical`, `monthly_labs`, `ppd_or_cxr`. Freshness is measured from the evaluation date against type-specific limits (e.g., 30 days for labs, 90 days for serologies and physicals, 365 days for PPD/CXR). A received_date further in the past than the limit means the document is stale.
- Documents with `finalized`=0 (draft) should be treated as present but not finalized; they may still block readiness depending on the intake type.

### ICD & Clinical Code Validation
- Every referral ICD code must be validated against the `icd_codes` table. A **clinical code discrepancy** exists when the ICD's `service_family` does not match the referral's `service_line`.
- `icd_chapter_mismatch`: the ICD chapter does not belong to the expected service family.
- `narrative_mismatch`: the `diagnosis_description` or `referral_reason` is inconsistent with the ICD code (e.g., "previsit clearance" paired with an acute-injury code).
- `laterality_mismatch`: the ICD code specifies a laterality (e.g., "left") but the narrative description is generic and does not confirm it.

### Duplicate Detection
- Two referrals are duplicates when they share the same **patient_id** and the same **icd10_code** within the same batch. The referral with the earlier `referral_id` (lexicographically) is the primary.
- Referrals flagged with notes like "possible duplicate" but with no matching patient+ICD in the batch should be treated as needing duplicate review, not as confirmed duplicates.

### Shared Insurance Anomalies
- When two referrals for **different patients** share the same `insurance_id`, this is a shared insurance anomaly requiring verification (`verify_distinct_patient_policy_id`).
- When two referrals for the **same patient** share the same `insurance_id`, this is expected and legitimate (`legitimate_duplicate_same_patient`).
- Also scan the `coverage` table: when two different patients share the same `policy_number` with different payers, flag as a shared insurance anomaly.

### Authorization Blockers
- A referral is authorization-blocked when `auth_required`=1 and `auth_status` is `denied` or `pending` (or `not_submitted`).
- An already-scheduled appointment (`appointment_scheduled`=1) before clearance is a blocker (`already_scheduled` / `scheduled_before_clearance`).

### Chart Artifact Evaluation
- Required chart artifacts for a complete chart typically include: `demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`, `consent`. The exact required set depends on the workflow.
- An artifact is **missing** if no row exists in `chart_artifacts` for that patient and artifact_type. An artifact is **stale** if its `status`=`stale` or if `last_updated` is older than typical clinical freshness windows (e.g., >12 months).
- `chart_action` for ready referrals: `create_chart` when `existing_chart`=0, `update_chart` when the chart exists but artifacts are stale or missing, `no_chart_action` otherwise.

### Program Enrollment Rules
- A candidate is **eligible** when `target_condition` matches the program's condition (e.g., `diabetes_hypertension` for DMHTN), confirmed by the `clinical_history.chronic_conditions`.
- **Consent**: `signed` = eligible to enroll, `declined` = reject, `missing` = hold pending consent.
- **High-touch triggers**: `recent_hospitalization`=1, `adherence_score` < 50, `risk_flags` containing `recent_ed_visit`.
- **CKD monitoring**: when chronic_conditions includes `ckd` (chronic kidney disease), consider biweekly monitoring.
- **Chart readiness**: candidates with `existing_chart`=0 or only stale artifacts need chart creation/update before enrollment.

### Facility Capacity
- Query `facility_capacity` for the target modality and date range. Sum `open_chairs` across locations to get total open chairs. A date with 0 total open chairs is `capacity_status: unavailable`.
- For transfer feasibility: only mark `ready_on_requested_start` when the packet is complete, all documents are fresh/finalized, AND capacity is available on the requested start date.

### General Heuristics
- When a value isn't directly in the expected reference table (e.g., a date missing from facility capacity), do not fabricate; mark status conservatively (e.g., `unavailable`).
- Always sort lists by the field specified in the answer template (typically ascending by ID).
- Use the exact enum values from the answer template; do not invent new codes.
- Cross-validate payer names between referral and coverage tables; mismatches may indicate data-quality issues but are not automatically blocker codes unless they affect insurance coverage validity.
