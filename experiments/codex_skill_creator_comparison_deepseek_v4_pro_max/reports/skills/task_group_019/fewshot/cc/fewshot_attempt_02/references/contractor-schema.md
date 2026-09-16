# Contractor Batch Eligibility Reference

## Join Keys

Every record type joins on `application_id` unless noted otherwise:

| Record type | Join field | Notes |
|-------------|-----------|-------|
| applications | `application_id` | Primary key; also has `prior_license_id` |
| bonds | `application_id` | Multiple bonds per application possible |
| insurance | `application_id` | Multiple policies per application possible |
| violations | `related_application_id` | Links to the application under review |
| correspondence | `related_application_id` | Attachments and assertions from applicant |
| inspections | `related_application_id` | Field inspection results |
| license-history | `license_id` | Joins via `applications[].prior_license_id` = `license-history[].license_id` |
| policies | (trade routing) | See policy routing below |

When multiple records exist for one application (e.g., past and current
bonds), the most recent active record is the one that matters for current
eligibility. Cancelled, expired, or old records are only relevant for
identifying gaps (\"no active bond\") or for policy-impact comparison.

## Policy Routing

Match each application to its governing policy by the application's `trade`
field:

| Trade | Policy rule_code | Policy ID |
|-------|-----------------|-----------|
| Electrical | CON-ELE-ClassA | POL-CON-001 |
| Plumbing | CON-PLU-ClassB | POL-CON-002 |
| HVAC | CON-HVA-ClassB | POL-CON-003 |
| General Building | CON-GEN-ClassA | POL-CON-004 |
| Roofing | CON-ROO-Limited | POL-CON-005 |
| Solar | CON-SOL-Specialty | POL-CON-006 |

Each policy's `details_json` (parse as JSON) contains:
- `minimum_bond`: integer dollar amount
- `minimum_insurance`: integer dollar amount
- `minimum_years_experience`: integer years
- `required_endorsement`: string code or `null` if not required
- `serious_open_violation_blocks`: boolean

The legacy policy (POL-CON-LEGACY, rule_code CON-LEGACY) is used only for
policy-impact comparison. Its `details_json` contains:
- `endorsement_required_for_specialty`: boolean (false means specialties were
  exempt)
- `minimum_bond_reduction`: integer (subtract from current minimum to get
  legacy minimum)
- `use_for_prior_rule_comparison`: true

## Deficiency Detection

For each application, evaluate every possible deficiency. Only report codes
that are in the answer template's allowed `deficiency_codes` list. The two
template vocabularies (train_001 style and train_004 style) differ slightly;
always use the exact codes from the current template.

### Common deficiency checks (train_001 vocabulary)

| Deficiency code | How to detect |
|----------------|---------------|
| `active_suspension` | license-history record for `prior_license_id` has status `suspended` |
| `bond_cancelled` | No active bond exists (all bonds are cancelled/expired), or the most recent bond has status `cancelled` |
| `bond_shortfall` | An active bond exists but its `amount` < policy `minimum_bond` |
| `endorsement_missing` | `applications[].endorsement_status` is `missing` AND policy `required_endorsement` is not null |
| `endorsement_pending` | `applications[].endorsement_status` is `pending` AND policy `required_endorsement` is not null |
| `experience_shortfall` | `applications[].years_experience` < policy `minimum_years_experience` |
| `inspection_doc_gap` | An inspection record has `finding_code` = `DOC_GAP` |
| `inspection_safety_recheck` | An inspection record has `finding_code` = `SAFETY_RECHECK` |
| `insurance_expired` | The active insurance `expiration_date` is before the review date, OR active insurance has `status` = `expired` |
| `insurance_pending` | The active insurance has `status` = `pending` |
| `insurance_shortfall` | Active insurance exists and is not expired/pending, but its `amount` < policy `minimum_insurance` |
| `open_minor_violation` | A violation record has `severity` in (\"minor\", \"medium\") AND `status` = \"open\" |
| `open_serious_violation` | A violation record has `severity` = \"serious\" AND `status` = \"open\" |

### Train_004 vocabulary equivalents

| Deficiency code | Detection (same underlying check, different code name) |
|----------------|-------------------------------------------------------|
| `no_active_bond` | Same as `bond_cancelled` above |
| `bond_shortfall` | Same check |
| `insurance_not_current` | Insurance `expiration_date` < review date, even if status is \"active\" |
| `insurance_expired` | Insurance status is \"expired\" |
| `insurance_shortfall` | Same check |
| `endorsement_not_verified` | `endorsement_status` is not \"verified\" when policy requires endorsement |
| `experience_shortfall` | Same check |
| `active_suspension` | Same check |
| `unresolved_serious_complaint` | A violation has `severity` = \"serious\" AND `status` = \"open\" |

## Action Mapping

Map each deficiency to its corresponding required action(s). The template
defines the allowed action vocabulary. The mapping is:

| Deficiency | Required action |
|------------|----------------|
| `bond_shortfall` | `increase_bond_amount` (or `increase_bond` in train_004 vocab) |
| `bond_cancelled` / `no_active_bond` | `obtain_current_bond` (or `file_active_bond` in train_004 vocab) |
| `endorsement_missing` | `obtain_required_endorsement` |
| `endorsement_pending` / `endorsement_not_verified` | `verify_pending_endorsement` (or `verify_endorsement` in train_004 vocab) |
| `experience_shortfall` | `submit_experience_evidence` (or `document_experience` in train_004 vocab) |
| `insurance_expired` / `insurance_not_current` | `provide_current_insurance` (or `renew_insurance` in train_004 vocab) |
| `insurance_shortfall` | `increase_insurance_amount` (or `increase_insurance` in train_004 vocab) |
| `insurance_pending` | `verify_insurance_binding` |
| `active_suspension` | `board_review_suspension` (plus `board_review` and `clear_suspension` in train_004 vocab) |
| `inspection_doc_gap` | `clear_document_gap` |
| `inspection_safety_recheck` | `complete_safety_recheck` |
| `open_serious_violation` / `unresolved_serious_complaint` | `resolve_serious_violation` (plus `board_review` and `resolve_complaint` in train_004 vocab) |
| `open_minor_violation` | `resolve_minor_violation_review` |

Always use the exact enum values from the current answer template for both
deficiency_codes and required_actions. The train_001 and train_004 templates
use slightly different vocabularies.

## Determination Logic

Assign the `determination` field based on the deficiencies found:

- **DENY**: When `active_suspension` or `open_serious_violation` (or
  `unresolved_serious_complaint` in train_004 vocab) is present. These are
  hard blocks — even one means the application must be denied.
- **APPROVE**: Only when there are zero deficiencies of any kind. An empty
  `deficiency_codes` list = APPROVE.
- **HOLD**: Any other case — at least one deficiency exists but none of the
  denial-hard-block deficiencies are present.

## Risk Tier

- **high**: The application has `active_suspension`, `open_serious_violation`,
  or `unresolved_serious_complaint` among its deficiencies.
- **medium**: The application has at least one deficiency but none of the
  high-tier triggers.
- **low**: The application has zero deficiencies (APPROVE determination).

## Policy Impact

`policy_impacted` is `true` when the current 2025 policy creates a requirement
that the legacy policy (POL-CON-LEGACY) would not have imposed. Compare:

1. **Endorsement**: If the current policy requires an endorsement and the
   legacy policy's `endorsement_required_for_specialty` is `false` AND the
   application is for a specialty trade (Solar is the specialty trade in
   these datasets), then the endorsement requirement is policy-impacted.
   However, also check: if `endorsement_required_for_specialty` = `false`,
   then all endorsement requirements for specialty trades are new. For
   non-specialty trades, endorsement requirements existed under legacy too,
   so no impact from endorsement alone.

2. **Bond minimum**: If the legacy policy's `minimum_bond_reduction` of 10000
   means the legacy minimum was lower, and the current bond amount falls
   between the legacy minimum and the current minimum, the bond shortfall
   is policy-impacted.

3. **General rule**: If removing the current policy's extra requirements
   (endorsement for specialty, higher bond minimum, etc.) would eliminate
   at least one deficiency or change the determination, mark
   `policy_impacted` as `true`.

## Correspondence Staleness

Identify stale or unverified correspondence for the summary's
`stale_or_unverified_correspondence_ids`. Include correspondence records
that have `verified_by_agency` = 0 (applicant-supplied, not agency-confirmed)
OR have notes mentioning \"Stale attachment predates application\" or similar
staleness indicators.

For train_001-style batches, also check if the correspondence relates to
an application that received a HOLD or DENY determination — typically only
those correspondence IDs appear in the summary.

## Summary Construction

After processing all applications, build the summary:

- `approve_count`: Count of APPROVE determinations
- `hold_count`: Count of HOLD determinations
- `deny_count`: Count of DENY determinations
- `high_risk_application_ids`: All application_ids with risk_tier \"high\",
  sorted ascending
- `policy_impacted_application_ids`: All application_ids where
  policy_impacted is true, sorted ascending
- `stale_or_unverified_correspondence_ids`: All qualifying correspondence
  IDs, sorted ascending
