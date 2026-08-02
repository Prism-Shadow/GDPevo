# Per-domain field derivation

Map every derived finding onto the current template's `allowed_values` — the
code names below are illustrative of the *concepts*, not fixed spellings.

---

## A. Contractor application-batch eligibility

Records typically available: applications, bonds, insurance, license-history,
violations, correspondence, inspections. Policy row per `(trade, requested_class)`
carries `minimum_bond`, `minimum_insurance`, `minimum_years_experience`,
`required_endorsement`, `serious_open_violation_blocks`. A legacy/prior baseline
policy carries `minimum_bond_reduction` and `endorsement_required_for_specialty`.

**Per application, derive deficiencies (each → one remedy action):**

- **Bond.** Find the *current* bond: `status` active, `effective_date` ≤ review
  date, and not cancelled by the review date. If none → *no-active-bond /
  bond-cancelled* (→ obtain/file bond). If current bond `amount` < `minimum_bond`
  → *bond-shortfall* (→ increase bond).
- **Insurance.** Current = active and `expiration_date` > review date.
  - current but `amount` < `minimum_insurance` → *insurance-shortfall* (→ increase).
  - active status but `expiration_date` ≤ review date → *insurance-expired*
    (→ renew).
  - only pending / no active coverage → *insurance-not-current / pending*
    (→ provide current / verify binding).
- **Experience.** `years_experience` < `minimum_years_experience` →
  *experience-shortfall* (→ document experience).
- **Endorsement.** Only if the class `required_endorsement` is non-null and the
  application's endorsement status isn't `verified`: emit the code the template
  provides — a single *endorsement-not-verified*, or split *missing* vs *pending*
  by the status (→ obtain / verify).
- **Inspections** (only if the template has inspection codes). Use `finding_code`
  as authoritative regardless of `result`/`notes`: e.g. `DOC_GAP` → *doc-gap*
  (→ clear document gap), `SAFETY_RECHECK` → *safety-recheck* (→ complete
  recheck). Codes like `NONE`/`UNVERIFIED_SITE`/`WRONG_TRADE` map to nothing.
  (A `SAFETY_RECHECK` finding still counts even when `result` = pass.)
- **Suspension.** License-history `status` = suspended → *active-suspension*
  (→ clear suspension / board review).
- **Open violations.** Only `status` = open. serious → *open-serious /
  unresolved-serious-complaint* (→ resolve); minor/medium → *open-minor* if the
  template has it (→ minor review). Resolved/dismissed = distractors.

**Determination precedence:** open serious violation (policy
`serious_open_violation_blocks`) → **DENY**; else any deficiency → **HOLD**; else
**APPROVE**. Active suspension → **HOLD** (board review), *not* DENY.

**Risk tier:** high for DENY / open-serious / active-suspension; medium for any
other deficiency (including no-active-bond); low when clean.

**policy_impacted (compare to the legacy baseline):** TRUE only when the *current*
standard creates a deficiency the prior baseline would not have:
- bond-shortfall where the current bond still ≥ `minimum_bond − minimum_bond_reduction`
  (short under current rule, fine under legacy); or
- a **Specialty**-class endorsement deficiency (legacy `endorsement_required_for_specialty`
  is false, so legacy required no specialty endorsement).
Otherwise FALSE. (Deficiencies that exist under both baselines — e.g. a shortfall
below even the legacy floor, or a non-specialty endorsement gap — are not impacted.)

**Summary:** approve/hold/deny counts; high-risk ids; policy-impacted ids;
stale/unverified correspondence ids = correspondence with `verified_by_agency` = 0
(plus rows whose notes clearly mark them stale / "no agency confirmation", per the
field's intent). Correspondence changes nothing else.

---

## B. Restricted liquor-license staff package (single application/location)

Records: applications, settlements (with `controls_json` = `{active, controls[],
expires, ...}` and a `basis_code`), privileges (per `license_class`, with
`standard_required`), incidents (`risk_code`, `severity`, `status`), site-evidence
(`evidence_code`, `status`, `evidence_date`, `notes`). Policies note that current
site evidence is required, same-premises history matters, and standard privileges
are separate from controls; a separate policy makes major incidents trigger board
review.

- **standard_obligation_codes** = privileges for the app's `license_class` where
  `standard_required` is true.
- **location_specific_control_codes** = **all** controls listed in **active**
  settlements (`controls_json.active` = true) for the location. Include a control
  even if it is also a standard obligation — do **not** subtract (keep the
  overlapping code).
- **same_premises_basis_applies** = TRUE if **any** settlement for the location
  has the same-premises basis, active **or** historical (history matters) —
  this holds even when the only same-premises settlement is inactive.
- **covered_risk_codes** = the risks the active controls cover — map each active
  control to its risk code in the template (e.g. noise→noise, patio→patio-boundary,
  camera/CCTV→camera-coverage, hours→after-hours, security→assault/public-safety).
- **verification_gap_codes**, from:
  - the **latest** site-evidence row *per evidence_code*: a non-`verified` latest
    status → that code's gap (missing / conflicting / stale, per the allowed set);
    a verified row carrying an identity/anomaly note can still be its own note-gap;
  - **open/referred incidents** → an open-incident follow-up gap; an open tax-hold
    incident → tax-hold-unresolved;
  - **required evidence categories that are entirely absent** → the matching
    `*_missing` gap, when that evidence is called for by the license class /
    active controls / the prompt's stated focus (e.g. camera and food-service
    evidence, late-night monitoring). Absent categories nobody requires → no gap.
- **recommended_posture:** verification gaps remain → **request_follow_up**; a
  major/high **open** incident that triggers board review → **deny**; basis applies
  with active controls and no material gaps → **issue_restricted**
  (gaps present ⇒ request_follow_up).
- **first_90_day_plan** = one `{check_code, timing}` per active control / open gap /
  key obligation, placed across the three timing windows in operational sequence
  (checks for the most urgent gaps first).
- **escalation_trigger_codes** = triggers derived from active controls, open
  incidents, and the emphasized risks (camera, food-service, late-night, noise/
  patio, open tax hold, violent incident, etc.).

---

## C. Alcohol renewal manual-review queue

Records: licensees (`license_no`, `address`, `location_id`, `successor_to`,
`active`), violations (`license_no`, `address`, `violation_date`, `severity`,
`alert_flag`, `fine_balance`, `disposition`, `violation_id`), and renewal rules.

- **Pick the governing renewal rule** by matching the prompt's release boundary
  to a rule's `release_boundary`. Honour its flags: use violations **on/before**
  the boundary only; alert flags require manual review; unpaid fines require hold;
  late rows are distractors. The related boundary policy prefers exact license
  matches and marks successor matches uncertain.
- **Match violations to each target by exact `license_no`** (the stable
  identifier). Distractors to exclude: violations under a *different* license at
  the *same address string*; ids ending in a late marker; any violation **after**
  the boundary (collect these into the excluded-ids summary).
- **Match confidence:** exact license → `exact`; matched only via the
  `successor_to` predecessor → `uncertain`; matched only by address → `close_address`.
- Per queue entry produce the fields the template lists — license/facility
  identity, matched violation ids (sorted as specified), matched count, most-recent
  matched date, confidence, risk tier, next-step label — and rank the entries
  `1..N` with no gaps.
- The **exact "which violations count" filter, the risk-tier and next-step-label
  thresholds, and the ranking key are agency-rule-driven** — read them off the
  renewal rule + policy for the specific task rather than assuming; each license's
  entry stands on its own, so getting each license's fields right matters more
  than a guessed global order.
- **Summary:** queue size; boundary date; post-boundary excluded violation ids;
  the license numbers with close/uncertain matches; the license numbers routed to
  board review. Sort each list as specified.
