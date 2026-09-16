# Dialysis Transfer Review

## Trigger

Prompt mentions a transfer batch ID (e.g. DIAL-WINTER-01), dialysis, packet completeness, chair capacity, or transfer review.

## Data Gathering

### 1. Fetch transfers in the batch

```sql
SELECT * FROM transfer_requests WHERE batch_id = 'BATCH-ID' ORDER BY transfer_id
```

### 2. Fetch documents for all transfer patients

```sql
SELECT * FROM documents WHERE transfer_id IN ('TR0001','TR0002',...)
```

Or batch by patient:
```sql
SELECT * FROM documents WHERE patient_id IN ('P014','P015',...) AND content_tag = 'transfer_packet'
```

### 3. Fetch facility capacity for requested dates

```sql
SELECT * FROM facility_capacity WHERE date IN ('2026-12-08','2026-12-10',...) AND modality = 'in_center_hemodialysis'
```

## Required Documents

Each transfer packet requires these documents:

| Document Code | Description |
|---|---|
| allergy_list | Allergy list |
| face_sheet | Patient face sheet |
| flu_vaccine | Flu vaccine record |
| hbsag | Hepatitis B surface antigen |
| hep_b_antibody_core | Hep B core antibody |
| history_physical | History and physical |
| insurance_proof | Proof of insurance |
| medication_list | Medication list |
| monthly_labs | Monthly lab results |
| physician_orders | Physician orders |
| pneumonia_vaccine | Pneumonia vaccine record |
| ppd_or_cxr | PPD or chest X-ray |
| transportation | Transportation plan |
| treatment_flowsheets | Treatment flowsheets |
| vascular_access_report | Vascular access report |

## Freshness Rules

Documents stale based on time since `received_date` relative to the current date (as_of_date from the task prompt, typically the task date):

| Document Type | Freshness Limit |
|---|---|
| hbsag | 30 days |
| hep_b_antibody_core | 365 days |
| history_physical | 365 days |
| monthly_labs | 30 days |
| ppd_or_cxr | 30 days |

A document is stale if `received_date + freshness_limit_days < as_of_date`.

A document is also stale if its `status` is not 'final' or `finalized` is 0.

For each patient, check every document of the types above that exists. The `stale_documents` list includes each stale doc with doc_type, received_date, and freshness_limit_days. Sort alphabetically by doc_type.

## Business Rules

### packet_completeness_status

Compare the set of existing document types (where status='final' AND finalized=1) against the full required document list. `patient.transportation` being null (from transfer_requests) adds `transportation` to missing.

| Condition | Value |
|---|---|
| All 15 required doc types present (finalized) | complete |
| Any missing | incomplete |

### missing_required_documents

List doc_type codes that are absent (alphabetical order). Include `transportation` if the transfer record has null transportation.

### requested_start feasibility

For each transfer's `requested_start_date`, look up `facility_capacity` for that date and modality:

| Condition | feasibility |
|---|---|
| Packet complete AND capacity available AND open_chairs > 0 | ready_on_requested_start |
| Packet NOT complete AND capacity available | packet_not_ready_capacity_available |
| Packet NOT complete AND capacity unavailable | packet_not_ready_capacity_unavailable |
| Packet complete AND capacity unavailable | capacity_unavailable |

`capacity_status` = 'available' if open_chairs > 0, else 'unavailable'.
`open_chairs_total` = sum of open_chairs across all locations for that date/modality.

### final_intake_decision

| Condition | Decision |
|---|---|
| packet_complete AND requested_start ready | accept |
| No data / unclear | hold |
| All other cases (any packet issue or capacity issue) | clinical_review |

### next_contact_owner and route

| Condition | Owner | Route |
|---|---|---|
| Any stale or missing document | clinical_nurse | fax_referring_facility |
| Packet complete but capacity unavailable | scheduling_coordinator | internal_queue |
| Packet complete and capacity available | intake_coordinator | phone_patient |
| No issues at all | none | none |

### Cohort Summary

- `total_transfers`: count
- `complete_documents_count`: count where packet_completeness_status = 'complete'
- `missing_document_patient_count`: count where missing_required_documents is non-empty
- `stale_document_patient_count`: count where stale_documents is non-empty
- `capacity_available_count`: count where capacity_status = 'available'
- `requested_start_ready_count`: count where feasibility = 'ready_on_requested_start'
- `decision_counts`: count per decision type
- `next_contact_owner_counts`: count per owner type

## Output Shape

Follow `input/payloads/answer_template.json` exactly. Required top-level keys: batch_id, patients (sorted ascending by transfer_id), cohort_summary.
