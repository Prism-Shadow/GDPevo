# Contractor Batch Eligibility Rules

## Deficiency Codes and Required Actions

Each deficiency code maps to the action the applicant must take. Always use exactly one action per deficiency.

### Track A Primary Codes (train 001 schema)

| Deficiency Code | Required Action | Meaning |
|---|---|---|
| `active_suspension` | `board_review_suspension` | License currently suspended; needs board-level review |
| `bond_cancelled` | `obtain_current_bond` | Bond has been cancelled; must file a new one |
| `bond_shortfall` | `increase_bond_amount` | Bond coverage below policy minimum |
| `endorsement_missing` | `obtain_required_endorsement` | Required endorsement not on file |
| `endorsement_pending` | `verify_pending_endorsement` | Endorsement application in progress, not yet confirmed |
| `experience_shortfall` | `submit_experience_evidence` | Claimed experience below class minimum |
| `inspection_doc_gap` | `clear_document_gap` | Inspection flagged missing documentation |
| `inspection_safety_recheck` | `complete_safety_recheck` | Failed safety inspection; must re-inspect |
| `insurance_expired` | `provide_current_insurance` | Insurance policy lapsed |
| `insurance_pending` | `verify_insurance_binding` | Insurance application in progress |
| `insurance_shortfall` | `increase_insurance_amount` | Coverage below policy minimum |
| `open_minor_violation` | `resolve_minor_violation_review` | Minor unresolved violation |
| `open_serious_violation` | `resolve_serious_violation` | Serious unresolved violation |

### Track A Variant Codes (train 004 schema)

| Deficiency Code | Required Action | Meaning |
|---|---|---|
| `no_active_bond` | `file_active_bond` | No bond on file |
| `bond_shortfall` | `increase_bond` | Bond below policy minimum |
| `insurance_not_current` | `provide_current_insurance` | Insurance not active on review date |
| `insurance_expired` | `renew_insurance` | Insurance policy has expired |
| `insurance_shortfall` | `increase_insurance` | Coverage below policy minimum |
| `endorsement_not_verified` | `verify_endorsement` | Required endorsement not confirmed |
| `experience_shortfall` | `document_experience` | Experience below class minimum |
| `active_suspension` | `clear_suspension` | Active license suspension; also add `board_review` |
| `unresolved_serious_complaint` | `resolve_complaint` | Serious complaint unresolved; also add `board_review` |

Always use the code set from the answer template. If the template uses the primary codes, use those. If the template uses the variant codes, use those. Never mix code sets between tasks.

## Blocking Conditions → DENY

These findings independently force DENY regardless of other status:

1. **Active license suspension** in license-history records
2. **Open serious violation** (must read violation records for severity classification)
3. **Unresolved serious complaint** (in Track A variant schema, add `board_review` action alongside the primary action)
4. **Inspection safety recheck required** (inspection record indicates failed safety check)

When any blocking condition is present, the determination is DENY, risk tier is `high`, and the summary deny_count increments.

## Risk Tier Assignment

| Conditions | Risk Tier |
|---|---|
| Any blocking condition present | `high` |
| Multiple serious deficiencies (3+) without blocking condition | `high` |
| 1-2 deficiencies, no blocking condition | `medium` |
| No deficiencies | `low` |

## Policy Impact Detection

The policies endpoint returns both a `current` and `prior` baseline. Compare each threshold:

1. **Bond minimum:** If the prior baseline required a lower bond amount and the application's bond met the prior minimum but not the current one, `policy_impacted` = `true` for `bond_shortfall`.
2. **Insurance minimum:** Same comparison for insurance thresholds.
3. **Endorsement requirements:** If the current baseline requires an endorsement class that the prior baseline did not, and the application lacks that endorsement, `policy_impacted` = `true`.
4. **Experience years:** If the current baseline raised the minimum experience years and the applicant met the old threshold but not the new one, `policy_impacted` = `true`.

When any single deficiency for an application is policy-impacted, flag the application-level `policy_impacted` as `true` and include the application ID in the summary's `policy_impacted_application_ids`.

## Stale/Unverified Correspondence

From the correspondence endpoint response, collect IDs where:
- Status includes "stale", "unverified", "unconfirmed", "pending", or equivalent
- Timestamp is older than a reasonable threshold relative to the review date

Include all such IDs in `stale_or_unverified_correspondence_ids`, sorted ascending.

## Sorting Rules

- `application_decisions`: sort by `application_id` ascending (lexical)
- `deficiency_codes`: sort alphabetically within each application
- `required_actions`: sort alphabetically within each application
- All summary ID lists: sort ascending

## Empty Values

Use `[]` empty arrays when no codes, actions, or IDs apply for a field. Never use `null` or omit the field.
