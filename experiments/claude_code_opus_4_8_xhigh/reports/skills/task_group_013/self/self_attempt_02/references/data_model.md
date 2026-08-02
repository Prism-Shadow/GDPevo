# Cedar Ridge portal — data model & access reference

Read-only SQLite behind the portal. `POST /query {"sql": "SELECT …"}` (only
`SELECT`/read-only `PRAGMA`; writes are rejected). REST GET endpoints mirror the
tables. `GET /health` returns `record_counts` per table. Discover the live
schema at runtime with:

```sql
SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;
SELECT sql  FROM sqlite_master WHERE type='table' AND name = ?;
```

## Tables (columns → observed value domains)

**intake_rosters** (`roster_id`,`patient_id` PK) — one row per roster member.
`requested_service_date` (YYYY-MM-DD), `service_line` (e.g. `primary_care`),
`source_note`. This is the authoritative member list + service date/line for
archetype A.

**patients** (`patient_id` PK) — `first_name`,`last_name`,`dob`,`phone`,`email`,
`language`,`address`,`existing_chart` (0/1),`preferred_contact`
(`portal`|`email`|`phone`|`sms`|`mail`…),`emergency_contact_present` (0/1).
Any of `phone`/`email`/`address` may be NULL.

**coverage** (`coverage_id` PK) — medical insurance. `patient_id`,`payer`,
`policy_number`,`group_number`,`effective_date`,`termination_date` (nullable),
`network_status` (`in_network`|`out_of_network`),
`service_lines` (comma-joined list, e.g. `"primary_care,cardiology,dialysis"`),
`status` (`active`|`expired`|`pending`).

**pbm** (`pbm_id` PK) — pharmacy benefit. `patient_id`,`payer`,`policy_number`,
`active` (0/1),`formulary_status` (`covered`|`review`|`not_found`),
`specialty_required` (0/1),`status` (`approved`|`pending`|`rejected`).
Observed pairing: covered↔approved, review↔pending, not_found↔rejected.

**patient_pharmacy** (`patient_id`,`pharmacy_id` PK) — `preference_rank`
(1 = most preferred). Join to **pharmacies** (`pharmacy_id` PK: `name`,`address`,
`phone`,`network_status` `in_network`|`out_of_network`) for network status of
the top-ranked pharmacy.

**lifestyle** (`patient_id` PK) — `smoking_status`
(`Never`|`Former`|`Current`),`alcohol_use` (`None`|`Occasional`|`Moderate`|
`Heavy`),`exercise_frequency` (`None`|`1-2`|`3-4`|`5+`|NULL),`sleep_hours` (REAL).

**referrals** (`referral_id` PK) — `batch_id`,`service_line`,`date_received`,
`patient_id`,`payer`,`insurance_id`,`referring_*`,`icd10_code`,
`diagnosis_description`,`referral_reason`
(`pain evaluation`|`previsit clearance`|`worsening symptoms`|`transfer of care`),
`urgency` (`urgent`|`routine`),`records_received` (0/1),`imaging_received` (0/1),
`auth_required` (0/1),`auth_status` (`approved`|`pending`|`denied`),
`appointment_scheduled` (0/1),`appointment_date` (nullable),`assigned_physician`,
`notes`.

**icd_codes** (`code` PK) — `description`,`chapter` (ICD-10 block, e.g.
`M00-M99`, `S00-T88`, `J00-J99`, `I00-I99`, `E00-E89`, `N00-N99`, `R00-R99`,
`Z00-Z99`),`service_family` (`orthopedics`|`pulmonary`|`cardiology`|
`chronic_care`|`dialysis`),`laterality` (`left`|`right`|NULL). The code's
`service_family` is the expected specialty; `laterality` is embedded in the
description (e.g. "…left knee").

**documents** (`document_id` PK) — `patient_id`,`referral_id` (nullable),
`transfer_id` (nullable),`doc_type`,`status` (`final`|`draft`),`finalized`
(0/1),`received_date`,`service_date`,`content_tag` (e.g. `transfer_packet`),
`notes`. A packet item counts as present only when `finalized=1`/`status=final`;
`draft`/`finalized=0` counts as not-yet-complete.

**transfer_requests** (`transfer_id` PK) — `batch_id`,`patient_id`,
`referring_facility`,`requested_start_date`,`requested_end_date`,`modality`
(`in_center_hemodialysis`),`days_requested` (e.g. `Mon/Wed/Fri`),`chair_window`
(`morning`|`midday`|`evening`),`transportation` (e.g. `family`|`ride_share`|
NULL),`status_note`.

**facility_capacity** (`location_id`,`date`,`modality` PK) — `open_chairs`
(int). Locations e.g. `CRIC-MAIN`, `CRIC-NORTH`. Sum `open_chairs` across
locations for a given `date`+`modality` to get chairs open that day.

**program_candidates** (`program_code`,`patient_id` PK) — `candidate_date`,
`source` (`registry`|`payer_file`|`provider_panel`),`consent_status`
(`signed`|`declined`|`missing`),`preferred_outreach`
(`phone`|`portal`|`email`|`sms`…, nullable),`adherence_score` (0–100, nullable),
`target_condition` (e.g. `diabetes_hypertension`|`copd`). This is the
authoritative candidate list for archetype D.

**chart_artifacts** (`artifact_id` PK) — `patient_id`,`artifact_type`
(`demographics`|`active_problems`|`vitals`|`labs`|`medications`|`allergies`|
`consent`|`care_plan`|`outreach_preference`),`status`
(`current`|`stale`|`draft`),`last_updated`,`value_summary`. Absence of a row
for an artifact_type = that artifact is missing; `stale`/`draft` = present but
not current.

**clinical_history** (`patient_id` PK) — `chronic_conditions` (comma list, e.g.
`ckd,diabetes,hypertension`),`surgeries`,`medication_count` (int),
`allergy_count` (int),`recent_hospitalization` (0/1),`risk_flags` (comma list,
may be empty; e.g. `recent_ed_visit`).

## Endpoint shapes worth knowing

- `GET /chart/{patient_id}` bundles `patient`, `clinical_history`,
  `chart_artifacts` (all), plus convenience groupings (`active_problems`,
  `recent_vitals_labs`, `meds_allergies`). One call per candidate covers
  archetype D's per-patient needs.
- `GET /referrals?batch_id=…` returns `{count, referrals:[…]}`;
  `GET /transfers?batch_id=…` returns `{count, transfers:[…]}`;
  `GET /programs/{code}/candidates` returns the candidate rows.
- `GET /icd/{code}` returns `{icd:{…}}`.

## Known work-unit ids (the family generalizes — do not hardcode)

Rosters: `NPI-JUN-01`, `NPI-JUL-02`. Referral batches: `ORTHO-JUN-01`,
`ORTHO-JUL-04`, `PULM-JUN-02`, `CARD-JUL-03`, `GEN-JUN-A`, `GEN-JUL-B`,
`COMMUNITY-Q3`, `ADMIN-REWORK`. Transfer batches: `DIAL-WINTER-01`,
`DIAL-SUMMER-02`, `DIAL-FALL-03`, `DIAL-MISC-01`. Programs: `DMHTN-2026A`,
`RENAL-DM-2026B`, `COPD-2026C`, `CAD-2026D`. A test task may name any of these
(or a new one) — always read the id from the prompt/template and query for it.
