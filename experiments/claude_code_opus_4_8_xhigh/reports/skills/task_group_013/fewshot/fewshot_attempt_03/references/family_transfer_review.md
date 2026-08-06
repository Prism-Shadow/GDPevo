# Family C — Dialysis Transfer Review

**Recognize it by:** prompt asks to review a *dialysis transfer batch*
(e.g. `DIAL-WINTER-01`) for packet completeness/freshness, chair capacity
feasibility, intake decision, next-contact owner/route. Template top-level keys:
`batch_id, patients, cohort_summary`.

**Scope:** `transfer_requests WHERE batch_id=<batch>`, ordered ascending
`transfer_id`. For each, patient = `transfer_requests.patient_id`. Pull that
patient's `documents` and the relevant `facility_capacity` rows.

## Required-document set (14 docs + 1 field)
Required codes (all 15 in the template):
`allergy_list, face_sheet, flu_vaccine, hbsag, hep_b_antibody_core,
history_physical, insurance_proof, medication_list, monthly_labs,
physician_orders, pneumonia_vaccine, ppd_or_cxr, treatment_flowsheets,
vascular_access_report` — each backed by a `documents.doc_type` (identical
snake_case string). **`transportation`** is NOT a document: present iff
`transfer_requests.transportation` is non-null/non-empty.

**A document code is "present"** iff there is ≥1 `documents` row for the patient
with that `doc_type` AND `finalized==1` AND `status=='final'`. Drafts do not
count. `doc_type='imaging_report'` is not a required code — ignore it.

- `missing_required_documents` = required codes with no present document (and
  `transportation` if that field is null), sorted **alphabetically by code**.
- `packet_completeness_status` = `complete` iff that list is empty, else
  `incomplete`. **Staleness does NOT affect completeness.**

## stale_documents (alphabetical by doc_type)
Only these doc_types are freshness-checked, with `freshness_limit_days`:
`hbsag`=30, `monthly_labs`=30, `ppd_or_cxr`=30, `history_physical`=365,
`hep_b_antibody_core`=365 (INFERRED — annual serology; not exercised).

For each freshness-eligible doc_type the patient **actually has present**, take
its `received_date`; it is **stale** iff
`(reference_date − received_date) > freshness_limit_days` (strict, whole days).

**Reference date = that transfer's `requested_start_date`** — NOT today, NOT a
global date. (Proven: labs dated after the run date but ≤ limit before the
Dec start are correctly fresh.) Emit `{doc_type, received_date (from the doc),
freshness_limit_days}`. Absent/draft docs are never evaluated for staleness.

## requested_start object
- `date` = `transfer_requests.requested_start_date`.
- `open_chairs_total` = `SUM(facility_capacity.open_chairs)` over rows WHERE
  `date == requested_start_date` AND `modality == <transfer.modality>`
  (in-center hemodialysis) AND `location_id LIKE 'CRIC-%'` (Cedar Ridge in-center
  locations: CRIC-MAIN, CRIC-NORTH). **No matching rows ⇒ 0.**
- `capacity_status` = `available` iff `open_chairs_total > 0` else `unavailable`.
- `feasibility` — packet-ready (= `complete` AND `stale_documents` empty) × capacity:
  | | capacity available | capacity unavailable |
  |---|---|---|
  | packet ready | `ready_on_requested_start` | `capacity_unavailable` (INFERRED) |
  | not ready | `packet_not_ready_capacity_available` | `packet_not_ready_capacity_unavailable` |

## final_intake_decision  {accept, hold, clinical_review}  (precedence)
1. `clinical_review` if `stale_documents` non-empty (stale clinical/serology/labs
   need nurse review). — drives all observed rows.
2. else `hold` if `missing_required_documents` non-empty. — INFERRED.
3. else (complete + fresh): `accept` if `feasibility=='ready_on_requested_start'`,
   else `hold` (capacity unavailable). — INFERRED.

## next_contact_owner / next_contact_route (keyed on decision)
- `clinical_review` → `clinical_nurse` + `fax_referring_facility` (observed).
- `hold` (missing docs) → `intake_coordinator` + `fax_referring_facility` (INFERRED).
- `accept` → `scheduling_coordinator` + `internal_queue`, or `none`+`none` (INFERRED).

## cohort_summary
- `total_transfers` = count.
- `complete_documents_count` = # with `packet_completeness_status=='complete'`.
- `missing_document_patient_count` = # with non-empty `missing_required_documents`.
- `stale_document_patient_count` = # with non-empty `stale_documents`.
- `capacity_available_count` = # with `capacity_status=='available'`.
- `requested_start_ready_count` = # with `feasibility=='ready_on_requested_start'`.
- `decision_counts` = tally over {accept, hold, clinical_review}.
- `next_contact_owner_counts` = tally over {clinical_nurse, intake_coordinator,
  scheduling_coordinator, none}.
