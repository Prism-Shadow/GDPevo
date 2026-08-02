# Archetype C — Dialysis transfer review (packet completeness + capacity)

**Recognize it by:** a transfer `batch_id` (e.g. `DIAL-…`) and an `answer_template.json` with
per-transfer `packet_completeness_status`, `missing_required_documents`, `stale_documents`,
`requested_start` (capacity/feasibility), `final_intake_decision`, `next_contact_owner`,
`next_contact_route`, plus a `cohort_summary`.

Pull the batch: `SELECT * FROM transfer_requests WHERE batch_id=? ORDER BY transfer_id`. For each
transfer join `documents` (by patient_id / transfer_id) and `facility_capacity`. One output object
per transfer; echo `batch_id`.

## missing_required_documents & packet_completeness_status
The required packet items = the full `allowed_values` list in the template. Of those, all are
document `doc_type` codes **except `transportation`**, which comes from
`transfer_requests.transportation`.
- A document code is **satisfied** iff a `documents` row exists for that patient/transfer with that
  `doc_type` AND `finalized=1` (equivalently `status='final'`). Absent, or only draft
  (`finalized=0`), counts as **missing**.
- `transportation` is missing iff `transfer_requests.transportation IS NULL`.
- `missing_required_documents` = all missing codes, **alphabetical**.
- `packet_completeness_status = "complete"` iff that list is empty, else `"incomplete"`.

## stale_documents
Only these doc types are freshness-checked, with fixed limits:

| doc_type | freshness_limit_days |
|---|---|
| hbsag | 30 |
| monthly_labs | 30 |
| ppd_or_cxr | 30 |
| history_physical | 365 |
| hep_b_antibody_core | 365 (inferred; never exercised) |

**As-of date for freshness = the transfer's `requested_start_date`** (NOT today). For each
freshness-checked doc that is present (`finalized=1`):
`(requested_start_date − received_date) in days > freshness_limit_days` ⇒ stale.
Each entry: `{doc_type, received_date, freshness_limit_days}`; list ordered **alphabetically by
doc_type**.

## requested_start (capacity & feasibility)
- `date` = `requested_start_date`.
- `open_chairs_total` = `SUM(facility_capacity.open_chairs)` over all Cedar Ridge in-center HD
  locations (`CRIC-MAIN`, `CRIC-NORTH`) where `date = requested_start_date` and
  `modality = transfer_requests.modality` (`in_center_hemodialysis`); 0 if no rows.
- `capacity_status` = `available` iff `open_chairs_total > 0`, else `unavailable`.
- `feasibility` from two booleans — `packet_ready` = (no missing docs) **and** (no stale docs);
  `capacity_available` = open_chairs_total > 0:

| packet_ready | capacity_available | feasibility |
|---|---|---|
| true | true | ready_on_requested_start |
| true | false | capacity_unavailable |
| false | true | packet_not_ready_capacity_available |
| false | false | packet_not_ready_capacity_unavailable |

A packet that is `complete` but has any stale doc is **not** ready.

## final_intake_decision / next_contact_owner / next_contact_route
Decision tree, first match wins (only the stale branch is confirmed by training data; the rest is
the principled extrapolation consistent with the enums):

1. Any stale document → `clinical_review` / `clinical_nurse` / `fax_referring_facility`.
   *(confirmed — stale clinical/lab/immunization records need a nurse to obtain refreshed records)*
2. else missing required documents → `hold` / `intake_coordinator` / `phone_patient`. *(inferred)*
3. else (complete & fresh):
   - capacity available → `accept` / `none` / `none`. *(inferred)*
   - capacity unavailable → `hold` / `scheduling_coordinator` / `internal_queue`. *(inferred)*

Owner↔route pairing: clinical_nurse↔fax_referring_facility, intake_coordinator↔phone_patient,
scheduling_coordinator↔internal_queue, none↔none.

## cohort_summary
- `total_transfers`.
- `complete_documents_count` = #`packet_completeness_status='complete'`.
- `missing_document_patient_count` = #incomplete (missing list non-empty).
- `stale_document_patient_count` = #with any stale doc.
- `capacity_available_count` = #`capacity_status='available'`.
- `requested_start_ready_count` = #`feasibility='ready_on_requested_start'`.
- `decision_counts` over {accept, hold, clinical_review}.
- `next_contact_owner_counts` over {clinical_nurse, intake_coordinator, scheduling_coordinator, none}.

## Ordering
`patients` ascending by `transfer_id`; `missing_required_documents` alphabetical by code;
`stale_documents` alphabetical by doc_type.
