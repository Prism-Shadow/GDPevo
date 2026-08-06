# Contractor eligibility decision rules

For each target application (ordered by `application_id` ascending), produce a decision
record with `determination`, `deficiency_codes`, `required_actions`, `risk_tier`, and
`policy_impacted`, plus a batch `summary`. Use **the code names that the task's
`answer_template.json` lists** — they are not identical across tasks, so read the template
every time.

## 1. Select the governing policy

Match `(trade, requested_class)` to a contractor policy row and parse its `details_json`:

| trade              | class     | rule_code          |
|--------------------|-----------|--------------------|
| Electrical         | Class A   | CON-ELE-ClassA     |
| Plumbing           | Class B   | CON-PLU-ClassB     |
| HVAC               | Class B   | CON-HVA-ClassB     |
| General Building   | Class A   | CON-GEN-ClassA     |
| Roofing            | Limited   | CON-ROO-Limited    |
| Solar              | Specialty | CON-SOL-Specialty  |

Read `minimum_bond`, `minimum_insurance`, `minimum_years_experience`,
`required_endorsement` (may be `null`), and `serious_open_violation_blocks`.

## 2. Derive deficiencies (use the template's own code names)

For each condition, add the matching deficiency code **and** its required-action code. The
mapping below is the logic; the exact strings come from the template.

- **Experience**: `years_experience < minimum_years_experience` → experience shortfall.
- **Endorsement**: if the policy `required_endorsement` is non-null:
  - `endorsement_status == "missing"` → endorsement-missing and an action to obtain it,
  - `endorsement_status == "pending"` → endorsement-pending and an action to verify it,
  - `verified`/`not_required` → no deficiency.
  - (When `required_endorsement` is null, e.g. Roofing, endorsement never applies.)
- **Bond**: take the bond row with `status == "active"` (most recent by `source_date`).
  - No active bond (all rows `cancelled`/`expired`, or none) → "no active bond" /
    "bond cancelled"-style code + action to file/obtain a current bond.
  - Active bond `amount < minimum_bond` → bond shortfall + increase bond.
- **Insurance**: take the active insurance with `expiration_date >= review_date`.
  - No record at all, or no active non-expired policy → "insurance not current"/"insurance
    expired"-style code + provide/renew insurance.
  - Only a `pending` policy and no active one → "insurance pending"/"insurance not current"
    + verify binding.
  - Active policy `amount < minimum_insurance` → insurance shortfall + increase insurance.
  - Use the **review date from the prompt** as "today" (read it explicitly — tasks vary).
- **Open violations**: among violations with `status == "open"` and
  `related_application_id == application_id`:
  - a `serious` open violation → an "open serious violation"/"unresolved serious complaint"
    code + resolve it (this is a **block**, see step 3),
  - a `minor` open violation → an "open minor violation" code + a review/resolve action.
  - Ignore `resolved`/`dismissed` violations for blocking (they may still be informational).
- **License history**: if the prior license is `suspended` → an "active suspension" code +
  a clear-suspension / board-review action (this is a **block**, see step 3).
- **Inspections**: take the most recent *non-distractor* inspection for the application
  (see `distractors.md`). When `result != "pass"`:
  - `finding_code == "DOC_GAP"` → inspection document-gap code + clear-document-gap action,
  - `finding_code == "SAFETY_RECHECK"` → inspection safety-recheck code +
    complete-safety-recheck action.
  - If the task's template has no inspection codes (some contractor schemas omit them),
  do **not** invent one — skip inspection-driven deficiency codes for that task.

## 3. Determine the determination

- **DENY** when there is a block: an open **serious** violation **or** an active
  **suspension** of the prior license. (`serious_open_violation_blocks: true`.)
- **HOLD** when there are any remediable deficiencies but no block.
- **APPROVE** when there are no deficiencies (and not policy-blocked).

## 4. Risk tier

- **high** for any DENY (block present).
- For HOLD/standard: follow the template's risk definition. As a working default, a HOLD
  with a block-adjacent flag (open serious history, suspension history) is `high`; a HOLD
  with several deficiencies may be `medium` or `high`. Reconcile to the template; when the
  template gives no explicit rule, prefer `medium` for ordinary HOLDs and reserve `high` for
  block-level severity. (Risk-tier calibration is one of the harder fields to get exactly
  right without per-field feedback — keep it defensible and consistent.)
- **low** for APPROVE.

## 5. policy_impacted

`true` when a **current 2025 policy** creates a deficiency or material flag that **would
not** have applied under the prior baseline (`CON-LEGACY`):
- The legacy baseline sets `endorsement_required_for_specialty: false`, so a **specialty
  (Solar)** endorsement deficiency that the old baseline would not have required is
  policy-impacted.
- The legacy baseline reduces the minimum bond by `minimum_bond_reduction`. A bond
  **shortfall** is policy-impacted only when the bond amount **would have met the legacy
  (reduced) minimum** — i.e. the shortfall exists solely because the 2025 standard raised
  the bar. If the bond fails even the legacy threshold, it is not a policy-driven gap.
- Insurance/experience standards are unchanged by the legacy baseline, so their shortfalls
  are generally not policy-impacted.

## 6. summary

Counts must be consistent with the decisions:
- `approve_count`, `hold_count`, `deny_count` (sum = number of target applications).
- `high_risk_application_ids` — sorted ascending.
- `policy_impacted_application_ids` — sorted ascending.
- `stale_or_unverified_correspondence_ids` — correspondence whose `verified_by_agency == 0`
  **or** `received_date` is before the application's `submitted_date` (stale attachment).
  Whether distractor (`*-DIS-*`) correspondence rows belong in this list is
  **task-specific**: include the rows that genuinely relate to the target applications and
  are unverified/stale; do not pad with unrelated distractors. Sort ascending.

## Cross-checks before submitting

- Every `application_id` in the target list appears exactly once, in order.
- An application with a block has `DENY`/`high`; do not mark a blocked app `HOLD`.
- Each deficiency code has a matching required action (and vice versa) per the template's
  allowed lists.
- Summary counts equal the per-item tallies.
