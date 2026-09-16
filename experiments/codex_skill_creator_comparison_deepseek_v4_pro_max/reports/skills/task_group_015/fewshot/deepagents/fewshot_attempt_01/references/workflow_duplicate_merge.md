## Duplicate-chart merge readiness

### Objective

Produce a normalized merge readiness packet for a duplicate candidate. The output identifies canonical target/source, merge disposition, active clinical key unions, identity signals, evidence, and packet contact.

### Step-by-step

#### 1. Fetch the duplicate candidate

`GET /api/duplicates/{candidate_id}`

Extract from the response:
- `primaryPatient` and `duplicatePatient` references
- `matchSignals` and `conflictSignals` arrays
- `conditionUnion`, `medicationUnion`, `allergyUnion` preview lists
- `evidenceDocumentIds` and `evidenceAuditIds`
- `status` field

#### 2. Fetch both patients

`GET /api/patients/{primary_id}` and `GET /api/patients/{duplicate_id}`

Extract demographics: `name`, `birthDate`, `gender`, `telecom`, `address`, `generalPractitioner`, `identifier` (for enterprise MRN).

#### 3. Fetch active clinical lists for both patients

For each patient, fetch:
- `GET /api/patients/{id}/conditions`
- `GET /api/patients/{id}/medications`
- `GET /api/patients/{id}/allergies`

Filter each list to `status = "active"` (conditions), `status = "active"` (medications), `clinicalStatus = "active"` (allergies). Collect `normalized_key` values.

#### 4. Fetch audit logs and documents

Fetch all audit logs: `GET /api/audit-logs` and filter by `evidenceAuditIds` from the candidate.

For each `evidenceDocumentIds`, fetch the document to confirm type and status. The API may return documents via patient endpoints: `GET /api/patients/{id}/documents`.

#### 5. Determine merge target and source

Target = the patient whose record is the active canonical one (the `primaryPatient` or the one with more complete data as indicated by the candidate fields).

Source = the patient marked as the duplicate to be absorbed into the target.

If the duplicate candidate's status is "confirmed_duplicate" and it already points one patient to the other, follow that direction.

#### 6. Union active clinical keys

Collect `normalized_key` values from both patients' active lists. Deduplicate (the same condition across both patients appears once). Sort alphabetically.

#### 7. Reconcile candidate preview vs. patient endpoints

The duplicate candidate includes preview clinical list unions. Compare these to the patient endpoint lists. If a key exists in the patient endpoints but not in the candidate preview, add it to `active_key_unions` and record it as a reconciliation addition with `authoritative_source = "patient_active_list_endpoints_over_duplicate_preview"`.

#### 8. Classify identity signals

From demographics comparison and candidate signals:

**Match signals** derive from: same DOB, same phone, same insurance ID, same PCP, same sex, shared external specialist documents, name variants (fuzzy match on given/family).

**Conflict signals** derive from: different addresses, different given names, different phones.

Also split into `demographic_matches` and `demographic_conflicts` using more granular field-level labels.

#### 9. Identify specialist contact

If one of the evidence documents is an external continuity document from a specialist (e.g., cardiology), look up that provider via `GET /api/providers/{provider_id}`.

The `packet_contact.specialist_provider` should include: provider_id, name, role, service_line, facility, phone, fax, and contact_reason.

The `packet_contact.primary_care_provider` should reference the patient's PCP from `generalPractitioner`.

#### 10. Evaluate packet readiness

The packet is `ready` when:
- A clear merge target and source are identified
- No blocking conflicts exist
- All required evidence documents are available
- Active clinical unions are complete

Add `required_review_notes` only when a blocking issue exists. For example, if the duplicate candidate status is "needs_review" rather than "confirmed_duplicate", or if there are meaningful demographic conflicts.

#### 11. Exclude distractors

Identify and exclude:
- Inactive condition/medication keys not part of the active union
- Documents that are chart_summary type or unrelated identifiers
- Audit logs not directly linked to the candidate

#### 12. Document selection policy

Set `packet_document_basis` to `"identity_or_external_continuity_documents_only"` to exclude chart summaries and unrelated clinical notes. List excluded document types.

### Output shape

Check the answer template for the exact JSON schema. Key sections: `merge`, `merge_decision`, `active_key_unions`, `active_list_reconciliation`, `identity_signals`, `evidence`, `excluded_distractors`, `document_selection_policy`, `packet_readiness`, `packet_contact`.
