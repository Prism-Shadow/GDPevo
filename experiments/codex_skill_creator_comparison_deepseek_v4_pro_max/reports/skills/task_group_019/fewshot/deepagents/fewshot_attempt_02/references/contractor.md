# Contractor Application Batch Eligibility Review

## Data Sources

Fetch these endpoints (use fetch_data.py --domain contractor, or call each
endpoint individually):

- `/api/policies` - Current policy baseline; used to flag whether 2025 standards
  create deficiencies that did not exist under a prior baseline.
- `/api/contractor/applications` - Application records keyed by application_id.
- `/api/contractor/bonds` - Bond coverage records keyed by application_id.
- `/api/contractor/insurance` - Insurance coverage records keyed by
  application_id.
- `/api/contractor/license-history` - Prior license records keyed by
  application_id or principal_id.
- `/api/contractor/violations` - Violation records keyed by application_id or
  license_id.
- `/api/contractor/correspondence` - Correspondence records; stale or
  unverified items must be flagged in the summary.
- `/api/contractor/inspections` - Inspection records keyed by application_id.

Use `POST /api/sql` when the REST endpoints do not return records in a
directly joinable format. Send the SQL as a JSON body with a `query` key and
`Content-Type: application/json`. Use the credential from environment_access.md.

## Eligibility Determination

For each application in the target batch, examine every data source and assign
one of three determinations:

### APPROVE

No material deficiency across any data source. Bond is active and sufficient,
insurance is current and sufficient, all required endorsements are verified,
experience meets the minimum, no active suspension, no open serious violations
or unresolved complaints, and inspections are clear.

### HOLD

One or more correctable deficiencies exist that are not immediate statutory
barriers. Examples: bond shortfall (but bond exists), insurance expired (but
can be renewed), endorsement pending or missing (but can be obtained),
experience shortfall (but can be supplemented), open minor violation,
inspection document gap.

### DENY

One or more blocking conditions: active suspension, open serious violation,
unresolved serious complaint, or multiple concurrent deficiencies that together
make approval impossible without board-level action.

## Deficiency-to-Action Mapping

### Bond

- `no_active_bond`: No bond record or bond explicitly cancelled/revoked.
  Action: `file_active_bond` or `obtain_current_bond`.
- `bond_cancelled`: Bond record shows cancelled status.
  Action: `obtain_current_bond`.
- `bond_shortfall`: Bond amount below policy minimum.
  Action: `increase_bond_amount` or `increase_bond`.

### Insurance

- `insurance_not_current`: Policy is active but does not cover the review date.
  Action: `provide_current_insurance`.
- `insurance_expired`: Policy end date is before the review date.
  Action: `provide_current_insurance` or `renew_insurance`.
- `insurance_shortfall`: Coverage amount below policy minimum.
  Action: `increase_insurance_amount` or `increase_insurance`.
- `insurance_pending`: Insurance record is in a pending/under-review state.
  Action: `verify_insurance_binding`.

### Endorsement

- `endorsement_missing`: No endorsement record exists.
  Action: `obtain_required_endorsement`.
- `endorsement_not_verified`: Endorsement present but unverified.
  Action: `verify_endorsement`.
- `endorsement_pending`: Endorsement application is pending.
  Action: `verify_pending_endorsement`.

### Experience

- `experience_shortfall`: Below required experience threshold.
  Action: `submit_experience_evidence` or `document_experience`.

### Violations

- `open_minor_violation`: Minor violation unresolved.
  Action: `resolve_minor_violation_review`.
- `open_serious_violation`: Serious violation unresolved.
  Action: `resolve_serious_violation`.
- `unresolved_serious_complaint`: Complaint with serious classification.
  Action: `resolve_complaint`.

When an unresolved serious violation or complaint exists AND the determination
is DENY, also include `board_review` in required_actions.

### Suspension

- `active_suspension`: License is under active suspension.
  Action: `board_review_suspension` or `clear_suspension`.
  Also include `board_review` in required_actions when active suspension leads
  to DENY.

### Inspection

- `inspection_doc_gap`: Inspection documentation incomplete.
  Action: `clear_document_gap`.
- `inspection_safety_recheck`: Safety inspection requires re-check.
  Action: `complete_safety_recheck`.

## Risk Tier Assignment

- **low**: APPROVE determination, no deficiencies, all coverage current and
  sufficient.
- **medium**: HOLD determination, correctable deficiencies only.
- **high**: DENY determination; OR `active_suspension`; OR
  `open_serious_violation`; OR `unresolved_serious_complaint`; OR any
  combination that requires board-level review.

## Policy Impact

Set `policy_impacted` to `true` when the 2025 policy baseline (read from
`/api/policies`) creates a deficiency that would not have existed under the
prior baseline. Examples: a bond minimum that was recently raised, a new
endorsement requirement, or a coverage threshold that increased since the
application was filed. When the deficiency exists under any baseline, the flag
is `false`.

## Summary Construction

After processing all applications, compute:

- `approve_count`, `hold_count`, `deny_count`: Counts by determination.
- `high_risk_application_ids`: Every application_id with risk_tier `high`.
- `policy_impacted_application_ids`: Every application_id where `policy_impacted`
  is `true`.
- `stale_or_unverified_correspondence_ids`: Every correspondence record ID that
  is marked stale, unverified, or has a status indicating it requires follow-up.
  Read the correspondence endpoint and collect IDs matching those conditions.

## Output Ordering

- `application_decisions` ordered by application_id ascending (lexical).
- All code lists within each decision sorted alphabetically.
- All ID lists in the summary sorted lexically ascending.
- Use empty arrays (`[]`) when no codes or IDs apply to an item.
- Dates in YYYY-MM-DD format when used in any unscored fields.

## Code Set Compatibility

Deficiency codes and required actions differ between task instances. Always
consult the `answer_template.json` provided in the task payloads for the exact
allowed values for the current task. The codes listed above are common
patterns; the template is authoritative for the allowed set.
