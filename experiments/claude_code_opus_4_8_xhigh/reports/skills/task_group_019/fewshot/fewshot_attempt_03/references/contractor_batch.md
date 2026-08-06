# Contractor batch eligibility review

Output: `application_decisions` (one item per target `application_id`, ordered by
id) + `summary`. Each decision item has `determination`, `deficiency_codes`,
`required_actions`, `risk_tier`, `policy_impacted`. Emit only codes present in the
template's `allowed_values`; the code *names* vary between templates (see the
mapping note at the end), but the conditions below are constant.

## Data to pull (filtered SQL, by the batch's application ids)

`contractor_applications`, `contractor_bonds`, `contractor_insurance`,
`contractor_violations` (`related_application_id`),
`contractor_inspections` (`related_application_id`),
`contractor_correspondence` (`related_application_id`),
`contractor_license_history` (join on `prior_license_id`), and `policies`.

For each application, look up its governing policy by
`CON-<TRADE3>-<CLASS>` and parse `details_json` for the minimums and required
endorsement. Use the prompt's review/as-of date for currency; if none is given,
use the current date.

## Detect deficiencies (per application)

**Bond** — consider that application's bonds:
- If an **active** bond exists (`status == "active"`) and its amount `< minimum_bond`
  → *bond shortfall*.
- If **no** active bond exists (all cancelled/expired, or none on file)
  → *no active bond* (some templates call this `bond_cancelled`, others
  `no_active_bond`). If the template has no such code, omit.

**Insurance** — consider that application's insurance rows; pick the current one:
- Effective row `status == "pending"` → *insurance pending / not current*.
- Effective row `status == "active"` but `expiration_date < review_date`
  → *insurance expired*.
- Effective row active & current but amount `< minimum_insurance`
  → *insurance shortfall*.
- Active, current, amount ≥ minimum → no insurance deficiency.
  (Priority: pending → expired → shortfall; emit at most one insurance code.)

**Experience** — `years_experience < minimum_years_experience` → *experience shortfall*.

**Endorsement** — only if the policy's `required_endorsement` is non-null:
- `endorsement_status == "missing"` → *endorsement missing* (or
  `endorsement_not_verified`).
- `endorsement_status == "pending"` → *endorsement pending* (or
  `endorsement_not_verified`).
- `verified` / `not_required` → no deficiency.

**Suspension** — the joined `contractor_license_history` row (by
`prior_license_id`) has `status == "suspended"` → *active suspension*.

**Violations** — a `contractor_violations` row for the application with
`status == "open"`:
- `severity == "serious"` → *open serious violation* (or
  `unresolved_serious_complaint`).
- `severity == "minor"` → *open minor violation* (if the template has the code).
- Resolved / dismissed violations are ignored. `severity == "medium"` has no code
  in the observed vocabularies — ignore unless the template lists one.

**Inspections** — only if the template has inspection codes. For each inspection
whose `result != "pass"` (i.e. `conditional` or `fail`):
- `finding_code == "DOC_GAP"` → *inspection doc gap*.
- `finding_code == "SAFETY_RECHECK"` → *inspection safety recheck*.
- Other finding codes (`NONE`, `UNVERIFIED_SITE`) and any `result == "pass"`
  inspection → no code.

Keep only the detected conditions that map to a code in this template. That mapped
set is the application's `deficiency_codes` (sorted per the template, usually
ascending lexical).

## required_actions

One action per emitted deficiency code, using the template's action vocabulary.
Typical correspondences (adapt to the template's `allowed_values`):

| Deficiency | Action |
| --- | --- |
| bond shortfall | increase bond amount |
| no active bond / bond cancelled | obtain current bond / file active bond |
| insurance shortfall | increase insurance amount |
| insurance expired / not current | provide current insurance / renew insurance |
| insurance pending | verify insurance binding |
| experience shortfall | submit / document experience |
| endorsement missing | obtain required endorsement / verify endorsement |
| endorsement pending | verify pending endorsement / verify endorsement |
| active suspension | board review (suspension) / clear suspension |
| open serious violation | resolve serious violation (+ board review) |
| open minor violation | resolve minor violation review |
| inspection doc gap | clear document gap |
| inspection safety recheck | complete safety recheck |

Some templates (e.g. serious/suspension cases) also add a generic `board_review`
action. Sort actions per the template (usually ascending lexical).

## determination & risk_tier

Compute from the **template-representable** deficiency set (ignore conditions that
have no code in this template):
- **DENY** / risk **high** — if *active suspension* or *open serious violation*
  is present.
- **APPROVE** / risk **low** — if there are no deficiency codes.
- **HOLD** / risk **medium** — otherwise.

## policy_impacted (boolean)

True when a current 2025 standard creates a deficiency that would not exist under
the prior baseline (`CON-LEGACY`: bond minimum reduced by
`minimum_bond_reduction`, and specialty endorsements not required; the legacy
baseline also does not block on serious open violations). Set `policy_impacted =
true` if **any** of:

1. A **bond shortfall** where the active bond amount is within the legacy bond
   reduction of the minimum, i.e. `active_bond ≥ minimum_bond − minimum_bond_reduction`
   (the shortfall disappears under the lower prior minimum). A *no active bond*
   condition is **not** policy-impacted.
2. An **endorsement** deficiency on a **Specialty** class (prior baseline did not
   require specialty endorsements).
3. An **open serious violation** deficiency (prior baseline did not block on it).
4. The governing policy's `effective_date` is on/after the current-update date
   (observed `2025-03-15`) **and** the application has any minimum-threshold
   *shortfall* deficiency (endorsement missing/pending, bond shortfall, insurance
   shortfall, or experience shortfall). Note: currency/status issues
   (insurance expired/pending, no active bond, suspension, violations, inspection
   gaps) do **not** by themselves make an application policy-impacted.

Otherwise `false`.

## summary

- `approve_count` / `hold_count` / `deny_count` — counts of the determinations.
- `high_risk_application_ids` — ids with `risk_tier == "high"`, sorted ascending.
- `policy_impacted_application_ids` — ids with `policy_impacted == true`, sorted.
- `stale_or_unverified_correspondence_ids` — over `contractor_correspondence`
  rows whose `related_application_id` is one of the target applications
  (this **includes** generically-named distractor rows such as `COR-DIS-*` that
  still reference a target application), include a `correspondence_id` when
  `verified_by_agency == 0` **or** its `notes` indicate the record is stale
  (e.g. "Stale attachment predates application"). Verified rows (`verified_by_agency
  == 1`) with ordinary notes are excluded. Sort ascending.
