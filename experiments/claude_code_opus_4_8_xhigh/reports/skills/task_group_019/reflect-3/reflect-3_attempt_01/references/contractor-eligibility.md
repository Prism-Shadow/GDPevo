# Contractor batch eligibility review

Decide a `determination`, deficiency/action codes, `risk_tier`, and `policy_impacted` for each target
application, plus a batch `summary`. The exact deficiency/action vocabulary varies by template
(a fine-grained variant and a coarser variant both appear) — always bind to the enums in *this*
task's `answer_template.json`. The logic below is the same; only the code strings differ.

## Datasets (contractor family)

- `policies` (family `contractor`): each row's `details_json` gives `minimum_bond`,
  `minimum_insurance`, `minimum_years_experience`, `required_endorsement` (null if none),
  `serious_open_violation_blocks`. A **legacy/prior baseline** policy row (e.g. rule code containing
  `LEGACY`) carries `minimum_bond_reduction` and `endorsement_required_for_specialty` — used only for
  the policy-impacted comparison.
- `contractor_applications`: `application_id`, `trade`, `requested_class`, `years_experience`,
  `endorsement_status` (`missing`/`pending`/`verified`/`not_required`), `prior_license_id`,
  `self_disclosed_issue`, `submitted_date`.
- `contractor_bonds`: `application_id`, `amount`, `status` (`active`/`cancelled`/`expired`),
  `effective_date`, `cancel_date`.
- `contractor_insurance`: `application_id`, `amount`, `status` (`active`/`pending`/`expired`),
  `expiration_date`, `verified_date`.
- `contractor_license_history`: keyed by `license_id`; `status` (`active`/`expired`/`suspended`).
- `contractor_violations`: `related_application_id`, `license_id`, `severity`
  (`minor`/`medium`/`serious`), `status` (`open`/`resolved`/`dismissed`), dates.
- `contractor_correspondence`: `related_application_id`, `verified_by_agency` (0/1), `received_date`,
  `notes`, `assertion_*`.
- `contractor_inspections`: `related_application_id`, `finding_code`
  (`DOC_GAP`/`SAFETY_RECHECK`/`NONE`/`UNVERIFIED_SITE`), `result` (`pass`/`fail`/`conditional`).

## Step 1 — find each application's governing policy

Map `(trade, requested_class)` to the policy whose `rule_code` encodes that trade+class, and read its
`details_json` thresholds. (Trade → short prefix, class → suffix like `ClassA`/`ClassB`/`Limited`/
`Specialty`.)

## Step 2 — detect deficiencies (per application)

- **Bond:** if the application has no `active` bond → *no-active-bond / bond-cancelled* code. Else if
  the best active `amount < minimum_bond` → *bond-shortfall*.
- **Insurance:** use the current record (active/pending; the latest verified). Amount `< minimum_insurance`
  while current → *insurance-shortfall*. If a review date is given and an `active` policy's
  `expiration_date < review_date` → treat as expired (*insurance-expired*, action = renew). A
  `pending` (unverified) policy → *insurance-not-current / insurance-pending* (action = provide/verify
  current). A record whose status is `expired` → *insurance-expired*. Each application gets at most one
  insurance code.
- **Endorsement:** only if the policy's `required_endorsement` is non-null. `endorsement_status`
  `missing` or `pending` → an endorsement deficiency (the fine-grained template splits
  missing vs pending; the coarse one uses a single "not verified" code). `verified`/`not_required` → none.
- **Experience:** `years_experience < minimum_years_experience` → *experience-shortfall*.
- **Active suspension:** if `prior_license_id` maps to a `contractor_license_history` row with
  `status = suspended` → *active-suspension*.
- **Open violations:** among violations with `related_application_id` = the app (and, for `-DIS-`
  rows, `license_id` matching the app's prior license) that are `status = open`: `serious` →
  *open-serious-violation / unresolved-serious-complaint*; `minor` → *open-minor-violation* (only in
  templates that have that code). Resolved/dismissed rows never count.
- **Inspections** (only in templates that include inspection codes): a `finding_code` of `DOC_GAP` or
  `SAFETY_RECHECK` produces the matching code **only when the inspection `result` is not `pass`**
  (i.e. `fail`/`conditional`). `NONE`/`UNVERIFIED_SITE` never produce a code; a `pass` suppresses.

## Step 3 — determination

- **DENY** if a hard blocker is present: an open **serious** violation (`serious_open_violation_blocks`)
  or an **active suspension**.
- else **HOLD** if any deficiency exists.
- else **APPROVE** (clean applications do occur — do not invent deficiencies).

## Step 4 — required actions

Map each deficiency code 1:1 to its action code (e.g. shortfalls → increase amount, no-active-bond →
file/obtain bond, expired insurance → renew, pending/not-current insurance → provide/verify current,
endorsement → obtain/verify endorsement, experience → submit/document experience, open serious →
resolve complaint, suspension → clear suspension). Sort as the template requires. In templates that
include a standalone `board_review` action, add it to the actions of DENY/blocker applications
(suspension or unresolved serious).

## Step 5 — risk tier

Count-based worked best: **high** if a blocker is present **or** the application has **3 or more**
deficiency codes; **medium** for 1–2 deficiencies; **low** for none. (A severity-only model that
keyed high solely off coverage gaps scored worse — prefer the count rule.)

## Step 6 — policy_impacted

True when the *current* policy creates a deficiency that the legacy baseline would not:
- a **bond-shortfall** whose active amount is `>= minimum_bond - minimum_bond_reduction` (legacy would
  have passed), or
- a **Specialty**-class application with an endorsement deficiency (legacy did not require a specialty
  endorsement).
Otherwise false. Insurance/experience deficiencies are not policy-impacted (legacy did not change them).

## Step 7 — summary

- `approve_count` / `hold_count` / `deny_count` from the determinations.
- `high_risk_application_ids` = apps with risk `high`; `policy_impacted_application_ids` = apps with
  `policy_impacted` true; both sorted ascending.
- `stale_or_unverified_correspondence_ids` = correspondence rows with `verified_by_agency == 0`
  (the flag is the signal even when the note text conflicts), plus any row whose note explicitly says
  it is stale / predates the application. **Include `-DIS-` correspondence rows here** if they are
  unverified — they belong in this field. Sort ascending.

## Judgment areas (verify against the template, keep minimal)

- Whether an active suspension is DENY vs HOLD-for-board, and the exact risk-tier cutoffs, are the
  softest calls; the rules above are the best-fitting defaults observed. Do not over-flag.
