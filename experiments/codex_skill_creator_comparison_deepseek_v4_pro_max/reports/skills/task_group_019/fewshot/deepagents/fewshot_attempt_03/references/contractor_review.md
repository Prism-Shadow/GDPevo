# Contractor Batch Eligibility Review

## Data Sources

Fetch all records before making determinations:

1. `GET /api/policies` — current policy baseline (thresholds, requirements)
2. `GET /api/contractor/applications` — application details, classification, experience, endorsements
3. `GET /api/contractor/bonds` — surety bond status per application
4. `GET /api/contractor/insurance` — liability insurance status per application
5. `GET /api/contractor/license-history` — prior licenses, suspensions, disciplinary actions
6. `GET /api/contractor/violations` — open and resolved violations
7. `GET /api/contractor/correspondence` — staff correspondence records, stale/unverified flags
8. `GET /api/contractor/inspections` — inspection results, safety checks, document gaps
9. `POST /api/sql` — additional cross-record queries when needed

Use `POST /api/sql` with header `X-Task-Token` set to the credential from the prompt or environment instructions. Write standard SQL queries against the licensing database tables.

## Determination Logic

### DENY criteria

Any of these triggers a DENY:

- **Active suspension** in license history: `license-history` records with `status: suspended` (not resolved/reinstated)
- **Unresolved serious violation/complaint**: violations with `severity: serious` and `status: open` or `status: unresolved`
- **Safety inspection failure requiring recheck**: inspectors flagged a safety hazard and re-inspection is not complete
- **Multiple concurrent high-severity deficiencies**: typically three or more separate deficiency categories including at least one financial (bond/insurance) and one qualification (experience/endorsement) gap

### HOLD criteria

HOLD when deficiencies exist but are resolvable by the applicant:

- **Bond issues**: cancelled bond, bond amount below policy threshold
- **Insurance issues**: expired policy, coverage below policy threshold, pending binding verification
- **Endorsement issues**: missing or pending-verification endorsements
- **Experience shortfall**: documented experience below classification requirement
- **Inspection document gaps**: missing paperwork from inspection process
- **Open minor violations**: non-serious violations still under review

### APPROVE criteria

APPROVE when:

- No active suspension
- No open serious violations
- Bond is active and meets current policy thresholds
- Insurance is current and meets policy thresholds
- All required endorsements are verified
- Experience meets classification requirements
- All inspections are complete with no unresolved gaps
- No unresolved serious complaints

## Deficiency Codes to Required Actions Mapping

Map each deficiency observed in the data to the matching code from the answer template, then to the corresponding required action:

| Deficiency | Required Action |
|---|---|
| `active_suspension` | `board_review_suspension` |
| `bond_cancelled` | `obtain_current_bond` |
| `bond_shortfall` | `increase_bond_amount` |
| `endorsement_missing` | `obtain_required_endorsement` |
| `endorsement_pending` | `verify_pending_endorsement` |
| `experience_shortfall` | `submit_experience_evidence` |
| `inspection_doc_gap` | `clear_document_gap` |
| `inspection_safety_recheck` | `complete_safety_recheck` |
| `insurance_expired` | `provide_current_insurance` |
| `insurance_pending` | `verify_insurance_binding` |
| `insurance_shortfall` | `increase_insurance_amount` |
| `open_minor_violation` | `resolve_minor_violation_review` |
| `open_serious_violation` | `resolve_serious_violation` |

For the alternate code set (train_004 style):

| Deficiency | Required Action |
|---|---|
| `no_active_bond` | `file_active_bond` |
| `bond_shortfall` | `increase_bond` |
| `insurance_not_current` | `provide_current_insurance` |
| `insurance_expired` | `renew_insurance` |
| `insurance_shortfall` | `increase_insurance` |
| `endorsement_not_verified` | `verify_endorsement` |
| `experience_shortfall` | `document_experience` |
| `active_suspension` | `clear_suspension` and `board_review` |
| `unresolved_serious_complaint` | `resolve_complaint` and `board_review` |

Always use only the codes present in the answer template for the current task. Different tasks may use different code sets.

## Risk Tier Assignment

- **high**: DENY determination, or HOLD with active suspension history, serious violations, multiple financial gaps, or safety inspection failures
- **medium**: HOLD determination with any deficiency not qualifying as high
- **low**: APPROVE determination only

## Policy Impact

A deficiency is `policy_impacted: true` when the current policy's thresholds or requirements would flag an issue that a prior baseline would not. Common indicators from the policy endpoint:

- Updated bond or insurance minimums that exceed the applicant's current coverage
- New endorsement requirements added in the current policy era
- Stricter experience requirements under current policy
- New inspection documentation requirements

## Summary Construction

After completing all application decisions, build the summary:

- `approve_count`, `hold_count`, `deny_count`: count each determination
- `high_risk_application_ids`: all applications with `risk_tier: high`, sorted ascending
- `policy_impacted_application_ids`: all applications with `policy_impacted: true`, sorted ascending
- `stale_or_unverified_correspondence_ids`: correspondence records with status `stale` or `unverified` that relate to the reviewed applications, sorted ascending by ID

Include only correspondence IDs that actually relate to the target applications. Not all correspondence in the system needs to be listed.
