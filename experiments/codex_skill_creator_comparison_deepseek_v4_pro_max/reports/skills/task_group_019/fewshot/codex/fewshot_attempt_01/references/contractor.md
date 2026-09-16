# Contractor Licensing Review

## Endpoint Catalog

| Endpoint | Returns | Key Fields |
|---|---|---|
| `GET /api/policies` | Current policy baseline | Policy effective dates, coverage thresholds, endorsement requirements |
| `GET /api/contractor/applications` | Application records | `application_id`, endorsement status, experience docs, specialty class |
| `GET /api/contractor/bonds` | Bond records | `application_id`, bond status, bond amount, required amount |
| `GET /api/contractor/insurance` | Insurance records | `application_id`, policy start/end dates, coverage amount, required amount, status |
| `GET /api/contractor/license-history` | License history | `application_id`, suspension records, status, dates |
| `GET /api/contractor/violations` | Violation records | `application_id`, violation type (minor/serious), status (open/resolved), date |
| `GET /api/contractor/correspondence` | Correspondence items | `correspondence_id`, `application_id`, date, status (stale/unverified/current) |
| `GET /api/contractor/inspections` | Inspection records | `application_id`, inspection type, findings, doc gaps, safety flags |
| `POST /api/sql` | SQL queries | Requires `X-Task-Token` header |

## Cross-Referencing Rules

Always pull `/api/policies` first. Policy changes raise `policy_impacted: true`.

### Bond Checks

- Pull bonds, filter by target `application_id`.
- **no_active_bond / bond_cancelled**: No bond record exists for the application, or bond status is `cancelled`.
- **bond_shortfall**: Bond amount < required amount.

### Insurance Checks

- Pull insurance, filter by target `application_id`. Use the review date from the prompt to judge currency.
- **insurance_not_current**: Insurance policy has expired or is not on file.
- **insurance_expired**: End date < review date.
- **insurance_pending**: Status is `pending` or `under_review`.
- **insurance_shortfall**: Coverage amount < required amount.

### License History

- Pull license-history, filter by `application_id`.
- **active_suspension**: Any suspension record with status `active` that has not ended.

### Endorsements

- From the applications payload, check endorsement fields.
- **endorsement_missing / endorsement_not_verified**: A required endorsement class is missing from the application or has not been verified.
- **endorsement_pending**: Endorsement status is `pending`.

### Experience

- From the applications payload, check experience documentation.
- **experience_shortfall**: Documented experience is below the required threshold.

### Violations / Complaints

- Pull violations, filter by `application_id`.
- **open_minor_violation**: Violation with type `minor` and status `open`.
- **open_serious_violation**: Violation with type `serious` and status `open`.
- **unresolved_serious_complaint**: Complaint record with type `serious` and status `unresolved`.

### Inspections

- Pull inspections, filter by `application_id`.
- **inspection_doc_gap**: Inspection finding flags a documentation gap.
- **inspection_safety_recheck**: Inspection result requires a safety re-inspection.

### Correspondence

- Pull correspondence, filter by target application ids plus any unattached correspondence items.
- Stale correspondence: items with dates well before the review date and no resolution.
- Include `correspondence_id` values in `stale_or_unverified_correspondence_ids` in the summary.

## Determination Rules

1. **DENY** if any of: `active_suspension`, `open_serious_violation`, `unresolved_serious_complaint`.
2. **APPROVE** if no deficiency codes trigger.
3. **HOLD** if any fixable deficiency codes trigger (bond, insurance, endorsement, experience, inspection gaps, minor violations) and no DENY condition applies.

## Risk Tier Rules

- **high**: Any DENY condition is present.
- **medium**: HOLD with one or more deficiency codes.
- **low**: APPROVE with no deficiencies.

## Policy Impact

Set `policy_impacted: true` when any deficiency code or review flag arises from a policy rule that took effect after the prior baseline. Compare policy effective dates against application submission dates. When the policies endpoint shows a 2025 policy with stricter thresholds than the prior baseline, flag any application that would have passed under the old rules but now has a deficiency.

## Summary Construction

- Count approvals, holds, denies.
- List high-risk application ids.
- List policy-impacted application ids.
- List stale/unverified correspondence ids (ascending).
