# Classification Quick Reference

Compact lookup tables for the closed-list judgment calls in EHR/referral quality packets.
Use alongside SKILL.md. Every value below is a schema enum/allowed-value drawn from the task
families' answer templates — no instance-specific data.

## Duplicate disposition (from candidate `status` + signals)

| candidate status / signals | candidate_status | decision | target/source |
|---|---|---|---|
| strong match, `confirmed_duplicate`, no serious conflict | confirmed_duplicate | merge | populated (active=target, duplicate=source) |
| strong match, one minor conflict (`address_abbreviation`, `name_variant`) | confirmed_duplicate | merge | populated — stays `merge_ready`, not `..._with_conflict_review` |
| `needs_review`, mixed match+conflict (incl. `opposite_laterality_problem`) | needs_review | review_hold | **both null** |
| decisive non-identity | not_duplicate | do_not_merge | null |

Canonical target = `canonical_status: active` + `canonical_patient_id: null`.
Source = `canonical_status: duplicate` (its `canonical_patient_id` → target).

## ICD-10 code validation

| condition | classification |
|---|---|
| code absent from directory | `unknown_code` (`invalid`) |
| chapter outside service line (ortho needs Musculoskeletal + Injury) | `out_of_range_chapter` (`invalid`) |
| valid, in-chapter, term present, laterality agrees | valid / match |
| valid, in-chapter, narrative laterality ≠ code laterality | `laterality_mismatch` |
| valid, in-chapter, no expected term in narrative | `narrative_mismatch` |
| valid, in-chapter, `requires_laterality` but narrative omits side for SAME condition | `missing_laterality` |
| valid, in-chapter, narrative about a DIFFERENT body region | `narrative_mismatch` only (not `missing_laterality`) |

`matches_patient_evidence` = patient's own active conditions/encounters contain that code or a
same-site condition.

## Active-list union rules
- Union = `status: active` records only, de-duplicated by `normalized_key`.
- Inactive / `legacy_import` of opposite laterality → `excluded_distractors`, not the union.
- `merge_preview` is a subset; reconcile against per-patient endpoints and record the added keys.

## Audit tiering

| tier | enum reason | who |
|---|---|---|
| Tier 1 | `urgent_coding_or_duplicate_blocker` | urgent urgency, OR duplicate-resubmission row, OR invalid/out-of-range code |
| Tier 2 | `routine_coding_auth_or_document_blocker` | routine with mismatch / auth-missing / doc blocker |
| Tier 3 | `administrative_document_completion` | routine, validated (no mismatch, approved), missing a document |

## Audit queues (keyed by referral_id, sorted ascending)
- `authorization_missing` ← `authorization_status == missing`
- `authorization_pending` ← `authorization_status == pending`
- `records_request` ← office-note document absent
- `imaging_follow_up` ← imaging document absent OR coordination note says "imaging pending"

## Anomaly vs duplicate separation
- Shared `insurance_id` across **different** patients → `shared_insurance_different_patients`,
  disposition `verify_insurance_membership_do_not_merge`.
- Same patient, >1 referral → duplicate group (`same_patient_resubmission`,
  `consolidate_under_original`); resubmission row = Tier-1 duplicate blocker, original = separate
  clinical review. Do not also list the same-patient pair as an insurance anomaly.

## Risk-flag mapping (orthopedic/perioperative, closed list)
- `cognitive_memory_loss` ← memory-loss condition (e.g. R41.3)
- `fall_risk_note_required` ← care-plan/care-transition note mentioning fall risk
- `hypertension` ← I10 active condition
- `insulin_dependent_diabetes` ← insulin med + diabetes condition
- `latex_allergy` ← latex active allergy
- `perioperative_glucose_plan_needed` ← care-plan note mentioning glucose plan + insulin/diabetes

## Readiness consistency rule
Pick the single dominant blocker from the most specific environment signal (a
`coordination_note` overrides apparent completeness). Align `overall_readiness`,
`blocking_issues[]`, and the matching `*_choice` field to that one blocker.

## Output hygiene
- One JSON object, all template-required top-level keys, no surrounding prose.
- Set arrays sorted as specified (ascending unless "newest to oldest").
- Nullable template fields → JSON `null`, not omitted.
- `YYYY-MM-DD` dates; `true`/`false` booleans.
