# Portal Data Model

The Intake Coordination Portal is backed by a relational store you can read
through per-resource endpoints and (when offered) a read-only SQL query
endpoint. Table/field names below are the ones the portal exposes; confirm them
at test time with `SELECT name, sql FROM sqlite_master` (or the equivalent
schema listing) since a given task only needs a subset.

## Core tables and the fields that matter

- **patients** — `patient_id`, `first_name`/`last_name`, `dob`, `phone`,
  `email`, `language`, `address`, `existing_chart` (0/1), `preferred_contact`
  (`phone`/`email`/`sms`/`portal`), `emergency_contact_present` (0/1).

- **coverage** (medical insurance) — `patient_id`, `payer`, `policy_number`,
  `group_number`, `effective_date`, `termination_date`, `network_status`,
  `service_lines` (comma-separated list of covered service lines), `status`
  (`active`/`expired`/`pending`).

- **pbm** (pharmacy benefit) — `patient_id`, `payer`, `policy_number`, `active`
  (0/1), `formulary_status` (`covered`/`review`/`not_found`), `specialty_required`
  (0/1), `status` (`approved`/`pending`/`rejected`).

- **patient_pharmacy** + **pharmacies** — preference-ranked pharmacies per
  patient (`preference_rank`, rank 1 = primary) joined to `pharmacies`
  (`network_status` `in_network`/`out_of_network`).

- **lifestyle** — `smoking_status` (`Current`/`Former`/`Never`), `alcohol_use`
  (`Heavy`/`Moderate`/`Occasional`/`None`), `exercise_frequency`
  (`None`/`1-2`/`3-4`/`5+`/null), `sleep_hours` (real).

- **clinical_history** — `chronic_conditions` (comma-separated, e.g. `ckd`,
  `diabetes`, `hypertension`, `copd`), `medication_count`, `allergy_count`,
  `recent_hospitalization` (0/1), `risk_flags` (comma-separated, e.g.
  `recent_ed_visit`, `fall_risk`, `complex_medication_reconciliation`).

- **referrals** — `referral_id`, `batch_id`, `service_line`, `patient_id`,
  `payer`, `insurance_id`, `icd10_code`, `diagnosis_description`,
  `referral_reason`, `urgency` (`urgent`/`routine`), `records_received` (0/1),
  `imaging_received` (0/1), `auth_required` (0/1), `auth_status`
  (`approved`/`pending`/`denied`/`not_submitted`), `appointment_scheduled` (0/1),
  `appointment_date`, `notes` (watch for markers like `possible duplicate`).

- **icd_codes** — `code`, `description`, `chapter` (ICD chapter range),
  `service_family` (the clinical service the code belongs to, e.g.
  `orthopedics`, `pulmonary`, `cardiology`, `chronic_care`, `dialysis`),
  `laterality` (`left`/`right`/null). This table is how you check whether a
  referral's code fits its service line.

- **transfer_requests** — `transfer_id`, `batch_id`, `patient_id`,
  `referring_facility`, `requested_start_date`, `requested_end_date`, `modality`
  (e.g. `in_center_hemodialysis`), `days_requested`, `chair_window`,
  `transportation` (e.g. `family`/`ride_share`/`medical_transport`/null),
  `status_note`.

- **documents** — `document_id`, `patient_id`, `referral_id`, `transfer_id`,
  `doc_type`, `status`, `finalized` (0/1), `received_date`, `service_date`,
  `content_tag`, `notes`. Packet/records completeness is judged on **finalized**
  documents of the required `doc_type`s.

- **facility_capacity** — `location_id`, `date`, `modality`, `open_chairs`.
  Availability on a date = sum of `open_chairs` over locations for that modality;
  **no row for a date = closed that day (zero)**.

- **program_candidates** — `program_code`, `patient_id`, `candidate_date`,
  `source`, `consent_status` (`signed`/`declined`/`missing`), `preferred_outreach`,
  `adherence_score` (int), `target_condition`. The program's candidate endpoint
  returns the authoritative candidate list (plus joined demographics).

- **chart_artifacts** — `patient_id`, `artifact_type` (`active_problems`,
  `vitals`, `labs`, `medications`, `consent`, `care_plan`, `demographics`,
  `allergies`, `outreach_preference`), `status` (`current`/`stale`/`draft`),
  `last_updated`, `value_summary`. `value_summary` is generic filler — do not try
  to parse clinical content from it; use `artifact_type` + `status`.

- **intake_rosters** — `roster_id`, `patient_id`, `requested_service_date`,
  `service_line`, `source_note`. Source of the requested date and service line
  for access-verification rosters.

## Data hygiene notes

- A resource's convenience endpoint (e.g. a per-patient bundle) returns joined
  sub-objects but does **not** pre-compute any derived status — you apply the
  rules yourself.
- Booleans arrive as `0`/`1`. Comma-separated fields need splitting.
- The same `insurance_id` appearing on multiple referrals is meaningful (shared
  insurance); the same `patient_id` appearing twice in a batch is a duplicate.
- `existing_chart` (a flag) and the presence of `chart_artifacts` rows can
  disagree; decide per task which one the template's "chart record / chart
  active" field is keyed to, and apply it consistently.
