# Family A — Contractor batch eligibility

Goal: for each target `C-…` application produce a `determination`
(APPROVE / HOLD / DENY), `deficiency_codes`, `required_actions`, `risk_tier`,
and `policy_impacted`, plus a consistent `summary`. Order `application_decisions`
ascending by `application_id`, and include exactly the target set.

**Bind every finding to the current template's `allowed_values`.** The same fact
maps to different codes across tasks (e.g. an inactive bond is `bond_cancelled`
in one template, `no_active_bond` in another; "insurance not current" may be
`insurance_expired` or `insurance_not_current`). Read the template first.

## Per-application evaluation

Use the review date from the prompt (if given) to judge whether coverage is
"current." Match the application to its governing policy by `trade` +
`requested_class` and read that policy's `details_json` for thresholds.

1. **Applicable policy.** Find the contractor rule whose `rule_code` matches the
   trade+class. If none exists, only universal checks apply and there is no
   trade-specific threshold. Pull `minimum_bond`, `minimum_insurance`,
   `minimum_years_experience`, `required_endorsement`,
   `serious_open_violation_blocks`.
2. **Bond.** Needs an `active` bond (not `cancelled`/`expired`, `cancel_date`
   not in effect as of the review date) with `amount >= minimum_bond`.
   - No active bond → deficiency in the "inactive/cancelled bond" slot; action
     "obtain/file current bond."
   - Active but under the minimum → "bond shortfall"; action "increase bond."
3. **Insurance.** Needs `active` insurance, not `expired`/`pending`, not past
   `expiration_date` at the review date, `amount >= minimum_insurance`.
   - Expired/lapsed/not current → "insurance expired / not current"; action
     "provide current / renew insurance."
   - Pending/unverified binding → "insurance pending"; action "verify binding /
     provide current insurance."
   - Under the minimum → "insurance shortfall"; action "increase insurance."
4. **Experience.** `years_experience < minimum_years_experience` →
   "experience shortfall"; action "submit/document experience evidence."
   Only credit an experience increase from correspondence if it is
   agency-verified.
5. **Endorsement.** If the policy `required_endorsement` is non-null and
   `endorsement_status` is not `verified` → endorsement deficiency
   (`missing` vs `pending` picks the corresponding code); action "obtain / verify
   endorsement." A correspondence claim that the registry was corrected only
   counts if `verified_by_agency = 1`.
6. **Violations.** Join by `license_id` (via `prior_license_id`) and
   `related_application_id`.
   - An **open serious** violation with `serious_open_violation_blocks = true`
     is a hard block → contributes to DENY; action "resolve serious violation".
   - Open minor/medium violations → "open minor violation" style code; action
     "resolve minor violation / review."
   - `resolved`/`dismissed` violations do not block.
7. **Suspension / discipline.** A suspended or disciplined `license_history`
   status → "active suspension" deficiency and board review; typically a hard
   block until cleared.
8. **Inspections.** `finding_code = DOC_GAP` → document-gap deficiency, action
   "clear document gap." `SAFETY_RECHECK` → safety-recheck deficiency, action
   "complete safety recheck." `result` fail / no access reinforces a HOLD.
9. **Correspondence trust.** Any correspondence with `verified_by_agency = 0`,
   or an `assertion_value` like "conflicts with registry" / "superseded by later
   source" / "unverified applicant note," is stale/unverified — do not rely on
   it, and record its `correspondence_id` in
   `summary.stale_or_unverified_correspondence_ids`.

## Determination

- **DENY** — an unwaivable block: open serious violation (when the policy blocks)
  or an unresolved active suspension.
- **HOLD** — fixable deficiencies present (missing/pending/short coverage,
  unverified endorsement, experience shortfall, open minor violation, inspection
  gap) but no hard block.
- **APPROVE** — all applicable standards met, no open blocking issues.

`required_actions` = the remediation code (from the template's action vocabulary)
for each deficiency you raised. Sort deficiency and action lists as the template
says (usually ascending/lexical) and dedupe.

## risk_tier

- **high** — hard block (serious open violation, active suspension) or a stack of
  serious deficiencies.
- **medium** — one or more fixable deficiencies.
- **low** — clean / approvable.

## policy_impacted

`true` when a **current** 2025 policy standard creates a deficiency or material
flag that would **not** apply under the legacy baseline (`CON-LEGACY`). Compare
the two `details_json` sets. Typical cases: an endorsement is now required for a
specialty that the legacy baseline exempted
(`endorsement_required_for_specialty = false`), or the current
`minimum_bond`/`minimum_insurance` exceeds the legacy-reduced amount
(`minimum_bond_reduction`) enough to flip a bond/insurance from adequate to
short. If the applicant would fare identically under both, it is `false`.

## Summary consistency

- `approve_count` / `hold_count` / `deny_count` = tallies of the determinations
  (they must sum to the target count).
- `high_risk_application_ids` = every app with `risk_tier = high`, sorted.
- `policy_impacted_application_ids` = every app with `policy_impacted = true`,
  sorted.
- `stale_or_unverified_correspondence_ids` = the correspondence IDs flagged in
  step 9, sorted.
