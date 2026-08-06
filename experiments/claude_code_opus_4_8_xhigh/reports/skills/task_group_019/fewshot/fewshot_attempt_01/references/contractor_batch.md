# Contractor batch eligibility review

Output: `application_decisions` (one per target id, ascending by `application_id`) +
`summary`. Each decision = `determination` (APPROVE/HOLD/DENY), `deficiency_codes`,
`required_actions`, `risk_tier` (low/medium/high), `policy_impacted` (bool).
**Code names vary per template — read `allowed_values` and map the conditions below
onto them.** Sort every code list ascending; use `[]` when clean.

## Step 1 — pull each target's records (SQL, filtered by id)

For the batch prefix (e.g. `C-TR1`, `C-TR4`) pull from SQL:
`contractor_applications`, `contractor_bonds`, `contractor_insurance`,
`contractor_violations` (join `related_application_id`),
`contractor_correspondence` (join `related_application_id`),
`contractor_inspections` (join `related_application_id`), and
`contractor_license_history WHERE license_id LIKE 'CL-C<PREFIX-without-dash>%'`
(join each application's `prior_license_id`). Also `GET /api/policies`.

**Review date** = the date in the prompt ("use YYYY-MM-DD as the review date"). If the
prompt gives none, use the latest `submitted_date` among the target applications. Used
only to judge whether coverage is current.

## Step 2 — pick the governing policy per application

Match `(trade, requested_class)` to the contractor policy in `/api/policies`
(family `contractor`), e.g. Electrical+Class A → `CON-ELE-ClassA`, Plumbing+Class B →
`CON-PLU-ClassB`, HVAC+Class B → `CON-HVA-ClassB`, General Building+Class A →
`CON-GEN-ClassA`, Roofing+Limited → `CON-ROO-Limited`, Solar+Specialty →
`CON-SOL-Specialty`. Parse its `details_json` for `minimum_bond`,
`minimum_insurance`, `minimum_years_experience`, `required_endorsement`,
`serious_open_violation_blocks`. Also read the legacy baseline `CON-LEGACY`
(`details_json`: `minimum_bond_reduction`, `endorsement_required_for_specialty`,
`use_for_prior_rule_comparison`) — used only for `policy_impacted`.

## Step 3 — detect deficiencies (each → one code + its paired action)

Use the target's own rows only. "Active bond" = the bond row with `status == "active"`
(pick its `amount`); "active insurance" = insurance row with `status == "active"`.

| Condition | Deficiency (semantic) | Paired action (semantic) |
|---|---|---|
| No active bond (all bond rows cancelled/expired) | no active bond / bond cancelled | file / obtain a current bond |
| Active bond `amount` < `minimum_bond` | bond shortfall | increase bond amount |
| Active insurance `expiration_date` < review date | insurance expired/not current | provide / renew current insurance |
| Only a `pending` insurance row (no active) | insurance pending / not current | verify binding / provide current insurance |
| Active insurance `amount` < `minimum_insurance` | insurance shortfall | increase insurance amount |
| `endorsement_status` ∈ {missing, pending} **and** policy `required_endorsement` ≠ null | endorsement missing (if "missing") / pending (if "pending") — some templates use one "endorsement not verified" code for both | obtain / verify the endorsement |
| `years_experience` < `minimum_years_experience` | experience shortfall | submit / document experience |
| A violation for this app with `severity=="serious"` and `status=="open"` | open serious violation / unresolved serious complaint | resolve complaint (+ board review) |
| A violation with `severity=="minor"` and `status=="open"` | open minor violation *(only if the template has such a code)* | resolve minor violation / review |
| `prior_license_id`'s license-history `status=="suspended"` | active suspension | clear suspension / board review (+ board review) |
| Inspection with `result != "pass"` (conditional/fail) and `finding_code=="DOC_GAP"` | inspection doc gap *(only if template has it)* | clear document gap |
| Inspection with `result != "pass"` and `finding_code=="SAFETY_RECHECK"` | inspection safety recheck *(only if template has it)* | complete safety recheck |

Notes:
- `endorsement_status` of `verified` or `not_required` → no endorsement deficiency
  (Roofing/Limited has `required_endorsement: null` → never an endorsement deficiency).
- Violations that are `resolved` or `dismissed` → ignored. Only `open` matters.
- Inspections with `result == "pass"` create **no** code regardless of finding; findings
  `NONE`/`UNVERIFIED_SITE` never create a code.
- **Some templates have no inspection codes at all** (their `deficiency` `allowed_values`
  omit inspection ones). In that case ignore inspections for deficiencies entirely —
  they do not block or downgrade the application.
- Emit `required_actions` only for the codes the template's action `allowed_values`
  support; `active_suspension` and `unresolved_serious_complaint` add a board-review
  action *in addition to* their specific action when the template offers `board_review`.

## Step 4 — determination & risk

- **DENY** if there is an active suspension **or** an open serious violation
  (`serious_open_violation_blocks` is true). Else **APPROVE** if there are no deficiency
  codes at all. Else **HOLD**.
- **risk_tier**: `high` for the DENY triggers (active suspension or open serious
  violation); `low` when APPROVE (no deficiencies); `medium` otherwise (HOLD).

## Step 5 — `policy_impacted`

True when the current governing policy creates a deficiency/flag the prior baseline
(`CON-LEGACY`, `use_for_prior_rule_comparison`) would not have. Set True if **any**:
- **Bond**: a bond shortfall where the active bond meets the legacy-reduced minimum but
  not the current one — i.e. `(minimum_bond − minimum_bond_reduction) ≤ active_amount <
  minimum_bond`.
- **Endorsement**: an endorsement deficiency whose requirement is newer than the prior
  baseline — the class is `Specialty` (legacy `endorsement_required_for_specialty=false`)
  **or** the governing policy is from the later 2025 standards wave. Determine the wave
  from `/api/policies`: contractor policies fall on two `effective_date`s; the later one
  (the most recent effective_date among the contractor policies, e.g. `2025-03-15`) is
  the "new standard." An endorsement deficiency under an earlier-wave policy that is not
  Specialty is **not** policy-impacting.
- **Open serious violation**: present (current policies set
  `serious_open_violation_blocks=true`, absent from the legacy baseline).

Otherwise False (insurance and experience shortfalls, no-active-bond, suspensions, and
inspection gaps are not, by themselves, policy-impacting).

## Step 6 — summary

- `approve_count`/`hold_count`/`deny_count` = tallies of your determinations.
- `high_risk_application_ids` = ids with `risk_tier=="high"`, ascending.
- `policy_impacted_application_ids` = ids with `policy_impacted==true`, ascending.
- `stale_or_unverified_correspondence_ids` = correspondence rows (of target apps) where
  `verified_by_agency == 0` **or** the `notes` indicate a stale/unconfirmed record
  (e.g. contains "predates"/"stale", or "Applicant copy only; no agency confirmation").
  List ids ascending. Include `-DIS-` correspondence ids when their
  `related_application_id` is a target.
