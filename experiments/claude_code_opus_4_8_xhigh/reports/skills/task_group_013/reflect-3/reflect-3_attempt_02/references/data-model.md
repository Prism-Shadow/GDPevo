# Portal data model

The intake portal exposes a set of read-only clinical record types. The fields
below are the ones that drive audit outputs; treat this as the join map when you
reconcile a cohort. (Only the decision-relevant columns are listed.)

## People and identity
- **patients** — `patient_id`, `first_name`, `last_name`, `dob`, `phone`,
  `email`, `language`, `address`, `existing_chart` (0/1), `preferred_contact`
  (`portal`|`phone`|`email`|`sms`), `emergency_contact_present` (0/1).
- **clinical_history** — one row per patient: `chronic_conditions`
  (comma list, e.g. `ckd,diabetes,hypertension`), `surgeries`,
  `medication_count`, `allergy_count`, `recent_hospitalization` (0/1),
  `risk_flags` (comma list; e.g. `recent_ed_visit`, `complex_medication_reconciliation`).
- **lifestyle** — `smoking_status` (`Current`/`Former`/`Never`), `alcohol_use`
  (`Heavy`/`Moderate`/`Occasional`/`None`), `exercise_frequency`
  (`None`/`1-2`/`3-4`/`5+`/null), `sleep_hours` (real).

## Coverage / benefits
- **coverage** — `patient_id`, `payer`, `policy_number`, `effective_date`,
  `termination_date`, `network_status` (`in_network`/`out_of_network`),
  `service_lines` (comma list of covered lines, e.g.
  `primary_care,cardiology`), `status` (`active`/`expired`/`pending`/…).
- **pbm** (pharmacy benefit) — `patient_id`, `payer`, `policy_number`, `active`
  (0/1), `formulary_status` (`covered`/`review`/`not_found`), `specialty_required`
  (0/1), `status` (`approved`/`pending`/`rejected`).
- **patient_pharmacy** — `patient_id`, `pharmacy_id`, `preference_rank`
  (1 = preferred).
- **pharmacies** — `pharmacy_id`, `network_status` (`in_network`/`out_of_network`).

## Referrals and coding
- **referrals** — `referral_id`, `batch_id`, `service_line`, `date_received`,
  `patient_id`, `payer`, `insurance_id`, referring practice/phone/fax,
  `icd10_code`, `diagnosis_description`, `referral_reason`, `urgency`
  (`urgent`/`routine`), `records_received` (0/1), `imaging_received` (0/1),
  `auth_required` (0/1), `auth_status` (`approved`/`pending`/`denied`/`not_submitted`),
  `appointment_scheduled` (0/1), `appointment_date`, `assigned_physician`,
  `notes`. (Patients can also have *distractor* referrals in other batches —
  scope to the target `batch_id`.)
- **icd_codes** — `code`, `description`, `chapter` (e.g. `M00-M99`, `J00-J99`,
  `S00-T88`), `service_family` (e.g. `orthopedics`, `pulmonary`, `cardiology`),
  `laterality` (`left`/`right`/null).

## Transfers / dialysis
- **transfer_requests** — `transfer_id`, `batch_id`, `patient_id`,
  `referring_facility`, `requested_start_date`, `requested_end_date`, `modality`
  (e.g. `in_center_hemodialysis`), `days_requested`, `chair_window`,
  `transportation` (arrangement or null), `status_note`.
- **facility_capacity** — `location_id`, `date`, `modality`, `open_chairs`.
  Not every date has rows; an absent (location,date,modality) row = 0 open chairs.

## Documents and charts
- **documents** — `document_id`, `patient_id`, `referral_id`, `transfer_id`,
  `doc_type`, `status` (`final`/`draft`/…), `finalized` (0/1), `received_date`,
  `service_date`, `content_tag`, `notes`.
- **chart_artifacts** — `patient_id`, `artifact_type` (`active_problems`,
  `vitals`, `labs`, `medications`, `allergies`, `consent`, `demographics`,
  `care_plan`, `outreach_preference`), `status` (`current`/`stale`/`draft`),
  `last_updated`, `value_summary`.

## Programs
- **program_candidates** — `program_code`, `patient_id`, `candidate_date`,
  `source`, `consent_status` (`signed`/`declined`/`missing`), `preferred_outreach`
  (`portal`/`phone`/`email`), `adherence_score` (int), `target_condition`
  (e.g. `diabetes_hypertension`, `copd`).
- **intake_rosters** — `roster_id`, `patient_id`, `requested_service_date`,
  `service_line`, `source_note`.

## Join tips
- Cohort membership: filter `intake_rosters` by `roster_id`; `referrals` /
  `transfer_requests` by `batch_id`; `program_candidates` by `program_code`.
- The roster/transfer/candidate row carries the cohort-level reference values
  (`requested_service_date`, `service_line`, `requested_start_date`,
  `target_condition`) — read them from the data, not the prompt.
- "Preferred X" almost always means the row with the lowest `preference_rank`.
- A code's specialty is `icd_codes.service_family`; its chapter is
  `icd_codes.chapter`. The batch's expected chapter is the dominant chapter among
  codes whose `service_family` equals the batch's service line.
