# Duplicate Merge Readiness Packet

Use when the task asks for a "duplicate-chart merge readiness packet" or mentions a duplicate candidate ID and two patient IDs.

## Input Signals

- A `merge_packet_request.json` payload with `candidate_id`, `patient_ids`, and `requested_outputs`.
- The task prompt names the candidate and the two patients.

## Evidence Gathering Order

1. `GET /api/duplicates/{candidate_id}` - candidate detail, match/conflict signals, preview clinical keys, linked documents and audit logs.
2. `GET /api/patients/{target_id}`, `GET /api/patients/{source_id}` - demographics for both patients.
3. `GET /api/patients/{target_id}/conditions`, `/medications`, `/allergies`
4. `GET /api/patients/{source_id}/conditions`, `/medications`, `/allergies`
5. `GET /api/providers/{pcp_id}` for both patients' primary care providers.
6. Identify specialist from document author or external records - `GET /api/providers/{specialist_id}`.
7. `GET /api/audit-logs` - filter by entity_id matching the candidate.

## Reconciliation Rules

### Canonical Target/Source

- The target is the canonical surviving record. Evidence: which patient the duplicate candidate `primary_patient_id` points to, which has a richer clinical history, and which is marked as duplicate to the other.
- The source is the patient being merged into the target.

### Disposition

- `ready_to_merge` / `merge_ready`: duplicate is confirmed, identity signals match, active clinical lists on both sides are consistent.
- `needs_review` / `review_hold`: conflict signals present (e.g., opposite laterality, different name).
- `do_not_merge`: clearly distinct patients.

### Clinical Unions

- Take the set union of active `normalized_key` values from **both** patients' conditions, medications, and allergies.
- The patient active-list endpoints are **authoritative over the duplicate preview**. Keys present in the patient endpoints but absent from the duplicate preview go into `active_list_reconciliation.*_added_from_active_endpoints`.
- Inactive/resolved/entered-in-error records from any source are excluded from the union.

### Evidence Selection

- Include document_ids that are identity-related or external continuity documents (e.g., shared external cardiology document, merge-related audit documents).
- Exclude `chart_summary`, `care_plan`, and unrelated documents. List excluded ones in `excluded_distractors`.
- Include relevant audit_ids from the candidate's audit log entries.

### Identity Signals

- `match_signals`: from the duplicate candidate record and demographic comparison.
- `conflict_signals`: from the duplicate candidate record and demographic comparison.
- `demographic_matches` / `demographic_conflicts`: list specific fields that match or conflict.

### Packet Contact

- `specialist_provider`: the specialist whose external document appears on the source record. Include `contact_reason`.
- `primary_care_provider`: the PCP of the target patient (or shared PCP).

### Readiness

- `ready_for_merge_packet: true` when disposition is merge-ready and no blockers remain.

## Output Shape

Follow `answer_template.json` exactly. Typical keys: `task_id`, `candidate_id`, `merge`, `merge_decision`, `clinical_unions`, `active_key_unions`, `active_list_reconciliation`, `identity_signals`, `evidence`, `excluded_distractors`, `document_selection_policy`, `packet_readiness`, `packet_contact`.
