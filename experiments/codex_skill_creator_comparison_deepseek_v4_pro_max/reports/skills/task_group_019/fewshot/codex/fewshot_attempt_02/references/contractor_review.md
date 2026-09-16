# Contractor Batch Eligibility Review

## Overview

Evaluate contractor applications by cross-referencing each application_id against bonds, insurance, license history (suspensions), endorsements, experience documentation, violations/complaints, inspections, and correspondence records. Every task has its own answer template with allowed code sets; use the template as the structural contract, not the codes shown in these examples.

## Data-Fetching Sequence

1. GET /api/policies for current financial minimums and requirements.
2. GET /api/contractor/applications for all target applications.
3. GET /api/contractor/bonds for bond/surety data.
4. GET /api/contractor/insurance for coverage data.
5. GET /api/contractor/license-history for prior suspensions and revocations.
6. GET /api/contractor/violations for open/resolved violations and complaints.
7. GET /api/contractor/inspections for inspection outcomes and gaps.
8. GET /api/contractor/correspondence for stale or unverified correspondence.

Use POST /api/sql only when direct GET endpoints lack the needed cross-entity join.

## Determination Rules

### APPROVE

Assign when none of the deficiency conditions below apply. All bond, insurance, endorsement, experience, violation, suspension, and inspection checks pass. Empty deficiency_codes and required_actions arrays.

### HOLD

Assign when fixable deficiencies exist. The applicant can resolve the issue(s) by taking the corresponding required actions. A HOLD does not indicate the application is permanently blocked.

### DENY

Assign when at least one blocking condition is present:
- Active suspension in license history (status is active/suspended).
- Unresolved/open serious violation or complaint (severity is serious, status is open/unresolved).
- A DENY may also be appropriate when multiple high-severity deficiencies converge, but the primary triggers are active suspension and unresolved serious violations.

## Deficiency-to-Action Mapping

For each application, inspect all records and map findings to codes using only the enum values from the task's answer template. The table below shows conceptual mappings; always use the exact enum strings defined in the template.

| Finding | Deficiency Code | Required Action |
|---|---|---|
| No active bond or bond cancelled | bond_cancelled, no_active_bond | obtain_current_bond, file_active_bond |
| Bond amount below policy minimum | bond_shortfall | increase_bond_amount, increase_bond |
| Insurance policy expired | insurance_expired | provide_current_insurance, renew_insurance |
| Insurance not current (lapsed) | insurance_not_current | provide_current_insurance |
| Insurance coverage below policy minimum | insurance_shortfall | increase_insurance_amount, increase_insurance |
| Insurance pending (not yet bound) | insurance_pending | verify_insurance_binding |
| Required endorsement not on file | endorsement_missing, endorsement_not_verified | obtain_required_endorsement, verify_endorsement |
| Endorsement application pending | endorsement_pending | verify_pending_endorsement |
| Experience below policy threshold | experience_shortfall | submit_experience_evidence, document_experience |
| Open minor violation | open_minor_violation | resolve_minor_violation_review |
| Open/unresolved serious violation | open_serious_violation, unresolved_serious_complaint | resolve_serious_violation, resolve_complaint, board_review |
| Active license suspension | active_suspension | board_review_suspension, clear_suspension, board_review |
| Inspection documentation gap | inspection_doc_gap | clear_document_gap |
| Safety recheck needed from inspection | inspection_safety_recheck | complete_safety_recheck |

## Risk Tier Assignment

- high: DENY determination, active suspension, unresolved serious violation/complaint, or 3+ distinct deficiency codes.
- medium: HOLD determination with 1-3 fixable deficiencies and no blocking conditions.
- low: APPROVE determination with 0 deficiencies.

## Policy Impact Assessment

Compare each deficiency's trigger against both the current policy baseline (from GET /api/policies) and the prior baseline described in the policy record. policy_impacted is true when:

- A deficiency exists only because the current policy standard is stricter than the prior baseline (e.g., higher bond minimum, higher insurance minimum, new endorsement requirement, higher experience threshold).
- The applicant would have passed under the prior baseline but fails under the current one.

policy_impacted is false when:

- The deficiency would have existed under both baselines.
- No deficiency exists.
- The deficiency is caused by a condition independent of policy standards (e.g., bond cancellation, insurance expiration, a pending endorsement not yet acted on).

## Correspondence Tracking

After processing all applications, collect correspondence IDs marked as stale, unverified, or unresolved. Include them in the summary stale_or_unverified_correspondence_ids field, sorted ascending. Exclude correspondence that is verified, current, and fully resolved.

## Summary Construction

- Count determinations: approve_count, hold_count, deny_count.
- Collect high_risk_application_ids sorted ascending.
- Collect policy_impacted_application_ids sorted ascending.
- Collect stale_or_unverified_correspondence_ids sorted ascending.
- All counts must be consistent with the application-level decisions.
