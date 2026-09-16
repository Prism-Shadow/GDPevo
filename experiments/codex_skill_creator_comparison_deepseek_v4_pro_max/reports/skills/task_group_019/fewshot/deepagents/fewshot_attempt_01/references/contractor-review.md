# Contractor Batch Eligibility Review

## Endpoints

| Endpoint | What It Supplies |
|----------|-----------------|
| GET /api/policies | Regulatory thresholds per trade/class |
| GET /api/contractor/applications | Applicant identity, trade, class, years_experience, endorsement_status |
| GET /api/contractor/bonds | Bond amount, status, effective/cancel dates |
| GET /api/contractor/insurance | Insurance amount, status, expiration_dates |
| GET /api/contractor/license-history | Prior license status (active, expired, suspended) |
| GET /api/contractor/violations | Open/resolved violations with severity |
| GET /api/contractor/correspondence | Applicant filings and agency verification flags |
| GET /api/contractor/inspections | Field inspection findings and results |
| POST /api/sql | Targeted queries (use X-Task-Token header) |

## Policy Cross-Reference

Policies carry a `details_json` string field. Parse it to extract thresholds:

- `minimum_bond` -- required bond amount in dollars
- `minimum_insurance` -- required insurance amount in dollars
- `minimum_years_experience` -- required years of trade experience
- `required_endorsement` -- the endorsement code required (null when none required)
- `serious_open_violation_blocks` -- when true, any open serious violation is a hard block

Match each application to its governing policy by combining the application's
`trade` and `requested_class` fields. If the task provides a review date, use
it to determine which policy version was effective at that time.

When the task asks whether `policy_impacted` is true, compare the current
2025 policy to `POL-CON-LEGACY` (the prior baseline). If a deficiency exists
only under the current policy and the legacy policy would not have flagged
it, mark `policy_impacted: true`.

## Bond Checks

For each application, look at all bonds. Consider only bonds with
`status: "active"` -- cancelled bonds are historical. Compare the active
bond `amount` against the policy `minimum_bond`.

- No active bond -> `bond_cancelled` / `no_active_bond` (obtain_current_bond / file_active_bond)
- Active bond amount < policy minimum -> `bond_shortfall` (increase_bond_amount / increase_bond)

## Insurance Checks

For each application, examine the most recent insurance record (by
`verified_date` descending). Check `status` and `expiration_date` against
the review date.

- No active insurance -> `insurance_pending` / `insurance_not_current` (verify_insurance_binding / provide_current_insurance)
- `status: "expired"` or expiration_date before review date -> `insurance_expired` (provide_current_insurance / renew_insurance)
- Active insurance `amount` < policy `minimum_insurance` -> `insurance_shortfall` (increase_insurance_amount / increase_insurance)
- `status: "pending"` -> `insurance_pending` (verify_insurance_binding)

## Endorsement Checks

From the application record, read `endorsement_status`:

- `"missing"` -> `endorsement_missing` / `endorsement_not_verified` (obtain_required_endorsement / verify_endorsement)
- `"pending"` -> `endorsement_pending` (verify_pending_endorsement / verify_endorsement)

When the policy's `required_endorsement` is null (not_required), do not flag
endorsement even if the application shows missing.  This is a policy-impacted
scenario when a 2025 policy adds an endorsement requirement that the legacy
baseline did not have.

## Experience Checks

Compare `years_experience` from the application against the policy's
`minimum_years_experience`. Shortfall -> `experience_shortfall`
(submit_experience_evidence / document_experience).

## License History Checks

Match the application's record in /api/contractor/license-history by
`license_id` (which may appear as `prior_license_id` in the application).
If `status: "suspended"` -> `active_suspension`
(board_review_suspension / clear_suspension).

## Violation Checks

Match violations by `related_application_id` or `license_id`. An open
violation with `severity: "serious"` -> `open_serious_violation` /
`unresolved_serious_complaint` (resolve_serious_violation / resolve_complaint).
An open violation with `severity: "minor"` -> `open_minor_violation`
(resolve_minor_violation_review).

## Inspection Checks

Match inspections by `related_application_id`:

- `finding_code: "DOC_GAP"` -> `inspection_doc_gap` (clear_document_gap)
- `finding_code: "SAFETY_RECHECK"` -> `inspection_safety_recheck` (complete_safety_recheck)

## Correspondence

Mark as stale or unverified any record with `verified_by_agency: 0`.
Include these `correspondence_id` values in the summary's
`stale_or_unverified_correspondence_ids` list, sorted ascending.

## Determination Logic

Rule priority, applied in order:

1. `active_suspension` -> DENY (risk_tier: high)
2. `open_serious_violation` / `unresolved_serious_complaint` -> DENY (risk_tier: high)
3. Any other deficiency code -> HOLD
4. No deficiencies -> APPROVE (risk_tier: low)

For HOLD, risk_tier is `medium` unless multiple deficiencies span financial
and experience categories (then consider `high`).

## Deficiency Code -> Required Action Pairs (V1 schema)

| Deficiency Code | Required Action |
|----------------|----------------|
| active_suspension | board_review_suspension |
| bond_cancelled | obtain_current_bond |
| bond_shortfall | increase_bond_amount |
| endorsement_missing | obtain_required_endorsement |
| endorsement_pending | verify_pending_endorsement |
| experience_shortfall | submit_experience_evidence |
| inspection_doc_gap | clear_document_gap |
| inspection_safety_recheck | complete_safety_recheck |
| insurance_expired | provide_current_insurance |
| insurance_pending | verify_insurance_binding |
| insurance_shortfall | increase_insurance_amount |
| open_minor_violation | resolve_minor_violation_review |
| open_serious_violation | resolve_serious_violation |

## Deficiency Code -> Required Action Pairs (V2 schema)

| Deficiency Code | Required Action |
|----------------|----------------|
| active_suspension | clear_suspension, board_review |
| bond_shortfall | increase_bond |
| endorsement_not_verified | verify_endorsement |
| experience_shortfall | document_experience |
| insurance_expired | renew_insurance |
| insurance_not_current | provide_current_insurance |
| insurance_shortfall | increase_insurance |
| no_active_bond | file_active_bond |
| unresolved_serious_complaint | resolve_complaint, board_review |

Note: The task's answer template defines which code set to use. Read the
template's `allowed_values` to select the correct mapping.

## Summary Construction

After all application decisions are complete:

- Count APPROVE / HOLD / DENY
- Collect application_ids where risk_tier is "high"
- Collect application_ids where policy_impacted is true
- Collect correspondence_ids where verified_by_agency is 0
- Sort all ID lists ascending
