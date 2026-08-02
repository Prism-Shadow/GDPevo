# Cedar Ridge portal — data model & endpoints

The portal is a **read-only** view over a SQLite database. You can read it two ways:

- **REST** (convenience views): `GET /patients`, `GET /patients/{id}`, `GET /referrals`,
  `GET /referrals/{id}`, `GET /transfers`, `GET /transfers/{id}`, `GET /documents`,
  `GET /chart/{patient_id}`, `GET /programs/{program_code}/candidates`, `GET /icd/{code}`,
  `GET /pharmacies`. List endpoints accept filters (`batch_id`, `service_line`, `q`, `limit`)
  and return `{"count": N, "<name>": [...]}`. `GET /icd/{code}` returns `{"icd": {...}}`;
  `GET /chart/{id}` returns artifacts grouped by type plus a flat `chart_artifacts` list.
- **SQL** (authoritative, preferred for reconciliation): `POST /query` with body
  `{"sql": "SELECT ..."}`. SELECT-only. Returns `{"columns", "row_count", "rows", "truncated"}`.
  `GET /health` returns per-table `record_counts` — a quick sanity check.

Always confirm the exact base URL from `environment_access.md` (`GDPEVO_ENV_BASE_URL`).
The allowed endpoint list there is authoritative.

## Tables (columns that matter)

**patients** — `patient_id` PK, `first_name`, `last_name`, `dob`, `phone`, `email`,
`language`, `address`, `existing_chart` (0/1), `preferred_contact`
(phone|email|sms|portal), `emergency_contact_present` (0/1).

**coverage** — medical insurance. `patient_id`, `payer`, `policy_number`, `group_number`,
`effective_date`, `termination_date`, `network_status` (in_network|out_of_network),
`service_lines` (comma-joined list, e.g. `"primary_care,cardiology"`),
`status` (active|expired|pending).

**pbm** — pharmacy benefit / prescription coverage. `patient_id`, `payer`, `policy_number`,
`active` (0/1), `formulary_status` (covered|review|not_found), `specialty_required` (0/1),
`status` (approved|pending|rejected).

**patient_pharmacy** — `patient_id`, `pharmacy_id`, `preference_rank` (1 = preferred).
**pharmacies** — `pharmacy_id` PK, `name`, `address`, `phone`, `network_status`
(in_network|out_of_network).

**lifestyle** — `patient_id` PK, `smoking_status` (Current|Former|Never), `alcohol_use`
(None|Occasional|Moderate|Heavy), `exercise_frequency` (None|1-2|3-4|5+ or null),
`sleep_hours` (real).

**clinical_history** — `patient_id` PK, `chronic_conditions` (comma-joined, e.g.
`"ckd,diabetes,hypertension"`), `surgeries`, `medication_count` (int),
`allergy_count` (int), `recent_hospitalization` (0/1), `risk_flags` (comma-joined, e.g.
`"recent_ed_visit"`, `"complex_medication_reconciliation"`, or empty).

**chart_artifacts** — one row per artifact. `patient_id`, `artifact_type`
(demographics|active_problems|medications|allergies|vitals|labs|consent|care_plan|…),
`status` (current|stale), `last_updated`, `value_summary`. Freshness is **pre-computed**
in `status` — read it, don't recompute.

**intake_rosters** — `roster_id`, `patient_id`, `requested_service_date`, `service_line`,
`source_note`. PK (roster_id, patient_id). Source of a roster's date + service line.

**referrals** — `referral_id` PK, `batch_id`, `service_line`, `date_received`, `patient_id`,
`payer`, `insurance_id`, `referring_physician/practice/phone/fax`, `icd10_code`,
`diagnosis_description`, `referral_reason`, `urgency` (urgent|routine), `records_received`
(0/1), `imaging_received` (0/1), `auth_required` (0/1), `auth_status`
(approved|pending|denied|not_submitted), `appointment_scheduled` (0/1), `appointment_date`,
`assigned_physician`, `notes`.

**icd_codes** — `code` PK, `description`, `chapter` (e.g. `M00-M99`, `S00-T88`, `J00-J99`,
`I00-I99`), `service_family` (orthopedics|pulmonary|cardiology|chronic_care|dialysis),
`laterality` (left|right|null). Note: a code's `service_family` and its `chapter` can
disagree (e.g. `S83.512A` is service_family=orthopedics but chapter=`S00-T88`).

**documents** — `document_id` PK, `patient_id`, `referral_id`, `transfer_id`, `doc_type`,
`status` (final|draft), `finalized` (0/1), `received_date`, `service_date`, `content_tag`,
`notes`. A document counts as "present" only when `finalized = 1`.

**transfer_requests** — `transfer_id` PK, `batch_id`, `patient_id`, `referring_facility`,
`requested_start_date`, `requested_end_date`, `modality` (in_center_hemodialysis),
`days_requested`, `chair_window`, `transportation` (family|ride_share|medical_transport|null),
`status_note`.

**facility_capacity** — `location_id`, `date`, `modality`, `open_chairs` (int). PK
(location_id, date, modality). A date **absent** from this table = 0 open chairs that day.

**program_candidates** — `program_code`, `patient_id`, `candidate_date`, `source`,
`consent_status` (signed|declined|missing), `preferred_outreach` (phone|portal|sms|email),
`adherence_score` (int, may be null), `target_condition` (e.g. diabetes_hypertension, copd).
PK (program_code, patient_id).

## Service-line ↔ ICD chapter reference

Derived from `icd_codes`; use it to judge coding discrepancies. The "expected" chapter for a
referral batch is the canonical chapter of its service line:

| service line | canonical chapter | example codes |
|---|---|---|
| orthopedics | `M00-M99` | M25.561, M25.562, M54.16 (injury codes like `S83.512A` sit in `S00-T88`) |
| pulmonary   | `J00-J99` | J44.9, J45.40 (symptom code `R06.02` sits in `R00-R99` but is service_family=pulmonary) |
| cardiology  | `I00-I99` | I25.10, I48.91 |
| chronic_care| `E00-E89` / `I00-I99` / `N00-N99` | E11.9, I10, N18.32 |
| dialysis    | `Z00-Z99` | Z99.2 |

Look codes up live (`icd_codes` / `GET /icd/{code}`) rather than hard-coding — the reference
set can change between tasks.
