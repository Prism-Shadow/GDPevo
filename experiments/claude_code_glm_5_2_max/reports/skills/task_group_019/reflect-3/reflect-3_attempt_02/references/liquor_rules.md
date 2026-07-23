# Liquor staff-package rules

For a single target `application_id` / `location_id`, produce a structured staff package.
Two related schemas exist (a generic restricted-premises package and a hotel-lounge
variant); both share the same field logic. The exact allowed code strings come from the
task's `answer_template.json` — read it for the variant.

## application_id
Echo the target application id from the prompt verbatim.

## recommended_posture
`issue_restricted` / `request_follow_up` / `deny`.
- **deny** when there is a major, unresolved disqualifier (e.g. a serious open incident the
  risk-matrix policy sends to board review, or a total evidence breakdown).
- **request_follow_up** when there are remediable verification gaps, an open/referred
  incident, or conflicting-but-resolvable evidence — i.e. not clean enough to issue but not
  a denial. This is the common outcome when any verification gap is present.
- **issue_restricted** when active controls cover the documented risks and there are no
  open verification gaps or open incidents.

## same_premises_basis_applies
Boolean. The premise is that the restricted license rests on a "same premises" history
(settlements with `basis_code == "SAME_PREMISES"`), and policy `LIQ-SETTLEMENT-CONTROLS`
sets `same_premises_history_matters: true`.
- Prefer **true** when the application operates at the same premises with a same-premises
  settlement history, **even if that settlement is currently inactive** — the *basis*
  applies because the history matters; an old-location-name police memo or an inactive
  settlement is a verification concern, not a basis-removal.
- Use **false** only when the evidence affirmatively shows the premises identity does not
  carry over (e.g. a move to a clearly different site with no same-premises linkage). Do
  not flip to false merely because a settlement is inactive or a memo notes a name change.

## covered_risk_codes
The risks **currently mitigated by active controls/settlements** at the location. Take the
controls from settlements whose `controls_json.active == true`; map each active control and
its `basis_code` to the risks it covers (e.g. an active `HOURS` control covers
`AFTER_HOURS`; `SECURITY` covers `ASSAULT`/`PUBLIC_SAFETY`; an active `SAME_PREMISES`
settlement covers `SAME_PREMISES`; `NOISE`/`PATIO` controls cover `NOISE`/patio-related
risks). Include only risks the template's enum permits. Deduplicate.

## verification_gap_codes
Gaps surfaced by the evidence and incident records:
- For each `liquor_site_evidence` row at the location, map a conflicting/missing status to a
  gap code (e.g. `CONTROL_SIGNAGE` conflicting → a signage-conflicting gap; missing current
  signage → a signage-missing gap; a conflicting `POLICE_MEMO` → a police-memo gap; a
  conflicting/stale `FLOOR_PLAN` → a floor-plan gap).
- Each **open** or **referred** incident adds a follow-up gap (e.g. an open/referred
  `MINOR_SALE` → minor-sale follow-up; an open `TAX_HOLD` → an unresolved-tax-hold gap).
- Hotel-lounge emphasis: when the prompt calls out late-night monitoring, camera, or
  food-service evidence, add the matching late-night-monitoring gap **only if** there is no
  current evidence supporting that control. Do not add camera/food-service gap codes unless
  the evidence actually lacks that support — over-adding them is a known score trap.
Deduplicate per the template's ordering rule.

## standard_obligation_codes
The **ordinary required obligations** for the license class = every `obligation_code` in
`liquor_privileges` with `standard_required == 1` for that `license_class`. (For example,
BeerWine/Restaurant/Tavern share `ID_CHECK, HOURS, FOOD_SERVICE` as standard.) Do not list
class-standard obligations that are merely optional (`standard_required == 0`).

## location_specific_control_codes
The **current active controls tied to this location** = the union of `controls` from
settlements whose `controls_json.active == true`. Only active settlement controls count;
inactive settlements do not supply current location-specific controls (though they inform
history/risk).

## first_90_day_plan
A list of `{check_code, timing}` monitoring checks across `first_30_days` / `days_31_60` /
`days_61_90`. Build it from the verification gaps and covered risks: place the most urgent
signage/identity/id-check follow-ups in `first_30_days`, camera/security/after-hours
walkthroughs and noise/patio boundary checks in `days_31_60`, and food-service / tax /
incident-log reviews in `days_61_90`. Include only `check_code` values the template's enum
permits. If the template specifies a sort order (e.g. by `check_code`), apply it; if it says
"intended operational sequence," order checks logically early→late.

## escalation_trigger_codes
The conditions that would escalate the licensee to enforcement/board review. Derive from
the risks and gaps actually present (e.g. an unresolved referred minor sale → a
referred-minor-sale-unresolved trigger; unverified control signage → a
signage-not-verified trigger; after-hours history → an after-hours trigger; an open tax
hold → a tax-hold-reopened trigger). Include only triggers supported by the location's
risks/gaps; do not list triggers for risks that are already covered and verified.

## Consistency checks
- `recommended_posture` should be `request_follow_up` whenever `verification_gap_codes` is
  non-empty (a clean issue has no gaps).
- `covered_risk_codes` and `verification_gap_codes` should not contradict: a risk that has
  no active control belongs in gaps, not covered.
- `standard_obligation_codes` ⊆ class privileges; `location_specific_control_codes`
  ⊆ active settlement controls.
