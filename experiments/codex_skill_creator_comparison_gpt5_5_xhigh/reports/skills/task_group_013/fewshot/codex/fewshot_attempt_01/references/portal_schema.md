# Cedar Ridge Portal Schema

Use this reference when the extraction helper does not cover the needed join. The read-only SQL endpoint accepts:

```json
{"sql": "select ..."}
```

## Main Endpoints

- `GET /patients` and `GET /patients/{patient_id}`
- `GET /referrals` and `GET /referrals/{referral_id}`
- `GET /transfers` and `GET /transfers/{transfer_id}`
- `GET /documents`
- `GET /chart/{patient_id}`
- `GET /programs/{program_code}/candidates`
- `GET /icd/{code}`
- `GET /pharmacies`
- `POST /query`

Many list endpoints accept filters such as `batch_id`, `service_line`, `q`, and `limit`; SQL is more reliable for precise task-scoped joins.

## Tables

- `patients`: `patient_id`, name, DOB, `phone`, `email`, `language`, `address`, `existing_chart`, `preferred_contact`, `emergency_contact_present`.
- `intake_rosters`: `roster_id`, `patient_id`, `requested_service_date`, `service_line`, `source_note`.
- `coverage`: `patient_id`, payer/policy fields, `effective_date`, `termination_date`, `network_status`, comma-separated `service_lines`, `status`.
- `pbm`: `patient_id`, payer/policy fields, `active`, `formulary_status`, `specialty_required`, `status`.
- `patient_pharmacy`: `patient_id`, `pharmacy_id`, `preference_rank`.
- `pharmacies`: `pharmacy_id`, `network_status`, name/contact fields.
- `lifestyle`: `patient_id`, `smoking_status`, `alcohol_use`, `exercise_frequency`, `sleep_hours`.
- `referrals`: `referral_id`, `batch_id`, `service_line`, `date_received`, `patient_id`, payer/insurance, referring contact, `icd10_code`, `diagnosis_description`, `referral_reason`, `urgency`, `records_received`, `imaging_received`, `auth_required`, `auth_status`, `appointment_scheduled`, `appointment_date`, `assigned_physician`, `notes`.
- `icd_codes`: `code`, `description`, `chapter`, `service_family`, `laterality`.
- `documents`: `document_id`, `patient_id`, `referral_id`, `transfer_id`, `doc_type`, `status`, `finalized`, `received_date`, `service_date`, `content_tag`, `notes`.
- `transfer_requests`: `transfer_id`, `batch_id`, `patient_id`, referring facility, requested dates, `modality`, requested days/window, `transportation`, `status_note`.
- `facility_capacity`: `location_id`, `date`, `modality`, `open_chairs`.
- `program_candidates`: `program_code`, `patient_id`, `candidate_date`, `source`, `consent_status`, `preferred_outreach`, `adherence_score`, `target_condition`.
- `clinical_history`: `patient_id`, comma-separated `chronic_conditions`, `surgeries`, `medication_count`, `allergy_count`, `recent_hospitalization`, comma-separated `risk_flags`.
- `chart_artifacts`: `patient_id`, `artifact_type`, `status`, `last_updated`, `value_summary`.

## Query Patterns

Roster access verification:

```sql
select r.*, p.address, p.phone, p.email, p.preferred_contact, p.emergency_contact_present,
       c.status as coverage_status, c.effective_date, c.termination_date, c.network_status as coverage_network,
       c.service_lines, pbm.active as pbm_active, pbm.formulary_status, pbm.specialty_required,
       pbm.status as pbm_status, pp.pharmacy_id, ph.network_status as pharmacy_network,
       l.smoking_status, l.alcohol_use, l.exercise_frequency, l.sleep_hours
from intake_rosters r
left join patients p on p.patient_id = r.patient_id
left join coverage c on c.patient_id = r.patient_id
left join pbm on pbm.patient_id = r.patient_id
left join patient_pharmacy pp on pp.patient_id = r.patient_id and pp.preference_rank = 1
left join pharmacies ph on ph.pharmacy_id = pp.pharmacy_id
left join lifestyle l on l.patient_id = r.patient_id
where r.roster_id = '<ROSTER_ID>'
order by r.patient_id;
```

Referral batch with ICD metadata:

```sql
select r.*, i.description as icd_description, i.chapter as icd_chapter,
       i.service_family as icd_service_family, i.laterality as icd_laterality
from referrals r
left join icd_codes i on i.code = r.icd10_code
where r.batch_id = '<BATCH_ID>'
order by r.referral_id;
```

Transfer packet context:

```sql
select * from transfer_requests
where batch_id = '<BATCH_ID>'
order by transfer_id;

select d.* from documents d
where d.transfer_id in (select transfer_id from transfer_requests where batch_id = '<BATCH_ID>')
order by d.transfer_id, d.doc_type, d.received_date;
```

Program panel context:

```sql
select pc.*, p.phone, p.email, p.existing_chart, p.preferred_contact,
       ch.chronic_conditions, ch.medication_count, ch.recent_hospitalization, ch.risk_flags
from program_candidates pc
left join patients p on p.patient_id = pc.patient_id
left join clinical_history ch on ch.patient_id = pc.patient_id
where pc.program_code = '<PROGRAM_CODE>'
order by pc.patient_id;
```
