---
name: licensing-batch-review
description: Solve State licensing-board review tasks (contractor application eligibility, restricted liquor-license staff packages, alcohol renewal manual-review queues) against a shared licensing data environment. Use at the start of any task that reads a licensing/regulatory environment and returns a structured JSON decision package conforming to a provided answer template.
---

# Licensing Batch Review

This skill is a **method for entering** licensing-review tasks. It is not tied to any
specific batch of applications, locations, or license numbers. When a task gives you a
licensing/regulatory environment plus an `answer_template.json`, apply this method
end-to-end and emit only the conforming JSON.

The tasks come in three families that share one data environment:

1. **Contractor application eligibility** — a batch of contractor applications decided
   APPROVE / HOLD / DENY with deficiency codes, required actions, risk tier, and a
   policy-impact flag, plus a batch summary.
2. **Restricted liquor-license staff package** — a single license/location: issuance
   posture, same-premises basis, covered risks, verification gaps, standard vs.
   location-specific controls, a 90-day plan, and escalation triggers.
3. **Alcohol renewal manual-review queue** — a ranked queue of licenses matched to
   pre-boundary violations, with match confidence, risk tier, next-step label, and a
   release summary.

## Step 0 — Read the template before touching data

The `answer_template.json` is the contract. Two tasks can look identical and score
differently because the **allowed enum vocabulary differs**. Before producing any
output:

- List every required top-level key and every field's `allowed_values`.
- Note the exact **enum vocabulary** for each list field — e.g. one contractor task uses
  `endorsement_missing` / `endorsement_pending`; another uses `endorsement_not_verified`.
  Use only the codes the template lists. Never invent or carry codes across tasks.
- Note every **ordering requirement** (ascending by id, by date, by code, by rank with no
  gaps, "any order accepted") and apply it exactly.
- Note empty-value rules ("use empty arrays when none apply").
- Note the **review date** if the prompt supplies one ("use 2025-07-18 as the review date
  for deciding whether financial coverage is current"). The review date determines whether
  insurance/bonds are *current*, independent of a record's `status` field.

The template's enum lists are the source of truth. The data and policy text suggest codes;
the template decides which of those codes are valid output.

## Step 1 — Pull and scope the environment data

Fetch the endpoints the prompt names (the prompt lists exactly the relevant ones per
task). Treat the data as relational:

- **Contractor family** links by `application_id` on bonds/insurance, and by
  `related_application_id` on violations/correspondence/inspections. License-history links
  by **`applicant_name`**, not by application id — match applicant name and also use the
  application's `prior_license_id` to resolve history.
- **Liquor family** links by `location_id` on settlements/incidents/site-evidence; the
  application row carries `location_id` and `license_class`.
- **Renewal family** links violations to licenses by `license_no` directly; a licensee's
  `successor_to` points to a prior (often inactive) license whose violations may still
  attach to the successor.

For batch tasks, filter the full tables down to the target ids **before** reasoning — the
environment contains distractor records (other batches, "TE2/TE5" look-alikes, post-release
feeds) that must be excluded. Target ids always share a prefix token from the prompt
(`C-TRn-NNN`, `AL-TRn-NNN`, `L-TRn-NNN`).

Because records often arrive in multiple rows per application (current + historical "OLD"),
**keep all rows** while scoping; which row is operative is a decision made in Step 3, not
during fetch.

## Step 2 — Load the governing policies

Always fetch `/api/policies` and parse `details_json`. Policies drive most fields:

- **Contractor** `POL-CON-*` standards give, per trade + requested class, the
  `minimum_bond`, `minimum_insurance`, `minimum_years_experience`, `required_endorsement`
  (may be `null`), and `serious_open_violation_blocks`. Each is effective-dated.
- **Contractor legacy baseline** (`CON-LEGACY`) records the prior rule: endorsements were
  *not* required for specialty, and bond minimums were lower. Compare the current standard
  against this baseline to decide **policy_impacted**.
- **Liquor** `POL-LIQ-001` sets premises-control review posture
  (`current_site_evidence_required`, `same_premises_history_matters`,
  `standard_privileges_separate_from_controls`); `POL-LIQ-002` flags that major incidents
  trigger board review.
- **Renewal** `POL-REN-001` / the `/api/renewal/rules` row for the named release sets the
  **boundary date** and the rules: `use_violations_on_or_before` the boundary,
  `late_rows_are_distractors`, `unpaid_fines_require_hold`,
  `alert_flag_requires_manual_review`, `successor_match_mark_uncertain`.

Build a small trade/class → policy map (bond, insurance, experience, endorsement) up front.
Map each application to its policy by `trade` + `requested_class`.

## Step 3 — Apply the decision logic per family

### 3a. Contractor eligibility (per application)

For each application compare the **operative current** record against policy:

- **Experience**: `years_experience` < policy minimum → experience shortfall deficiency +
  experience-evidence action.
- **Endorsement**: only flag when the policy's `required_endorsement` is non-null. Map the
  raw `endorsement_status` to the template's vocabulary (missing/pending/not_verified),
  distinguishing "missing" (none filed) from "pending" (in progress). A `verified` status
  with a verified-by-agency correspondence does not produce a deficiency.
- **Bond**: an `active` bond with `amount` ≥ minimum is fine. Below minimum → bond
  shortfall (and increase-bond action). No active bond at all (only cancelled/expired, or
  no rows) → "no active bond" / bond-cancelled / obtain-current-bond depending on
  vocabulary of the *current* template. Use the right code: shortfall = bond exists but is
  short; missing/cancelled = no operative bond.
- **Insurance**: check both `status` *and* `expiration_date` against the review date. A
  record marked `active` that **expires before the review date** is not current → expired.
  `pending` status → pending/not-current. Amount below minimum → shortfall. Below minimum
  amount or not current drives the insurance deficiency + provide/renew/increase action.
- **License history**: a `suspended` prior status (especially "pending board action")
  → active-suspension deficiency + clear-suspension/board-review action and raises risk.
  `expired` history alone is not a deficiency.
- **Violations**: an **open** violation flagged `serious` (with `serious_open_violation_blocks`)
  blocks approval → serious-violation deficiency + resolve action, typically DENY. Open
  **minor** violations → minor-violation deficiency + review action (a HOLD, not a block).
  Resolved/dismissed violations do not produce deficiencies.
- **Inspections**: map the `finding_code` to the inspection deficiency the template allows
  (DOC_GAP → doc-gap, SAFETY_RECHECK → safety-recheck, UNVERIFIED_SITE → site/verification).
  Use the inspection finding to determine the inspection deficiency and matching action;
  the `result` (pass/fail/conditional) informs severity/risk but the finding code is the
  primary trigger.
- **Correspondence**: `verified_by_agency` false (or "applicant supplied" / "pending
  outside agency" without agency confirmation) on a material assertion (bond/insurance/
  endorsement/experience) marks that record unverified. Collect unverified correspondence
  ids for the summary's stale/unverified list.

**Determination logic**:
- DENY when a hard block applies: open serious violation (with block policy), or active
  suspension that the template treats as prohibitive.
- HOLD when deficiencies exist that the applicant can cure (shortfalls, pending items,
  doc gaps, open minor violations, unverified correspondence).
- APPROVE when all coverage/endorsement/experience/violation checks pass.
- Multiple deficiencies do not automatically escalate HOLD to DENY; only a hard block does.

**risk_tier**: high when there is an active suspension, an open serious violation, or many
overlapping deficiencies; medium for a curable single-area deficiency; low when clean.

**policy_impacted** = true only when a deficiency/flag arises from a **current (2025+)
policy standard that would not have applied under the legacy baseline** — most commonly a
newly required specialty endorsement, or a raised bond minimum. Pure applicant problems
(lapsed bond, open violation, experience shortfall) are NOT policy-impacted.

### 3b. Liquor staff package (single location)

- **recommended_posture**: `issue_restricted` when an active control settlement is in force
  and only minor/non-blocking gaps remain; `request_follow_up` when verification gaps or
  open incidents remain unresolved before issuance; `deny` when a hard impediment exists
  (e.g., an unresolved major incident / board-order conflict that policy says triggers
  board review).
- **same_premises_basis_applies**: per `POL-LIQ-001` (history matters), true when the
  same-premises basis is established by settlement history for this location, even if the
  same-premises settlement itself is currently inactive; the active settlement's basis may
  be a risk code (e.g., NOISE) while the same-premises basis still "remains applicable" as
  history. Default true when same-premises history exists.
- **covered_risk_codes**: risks **covered by the currently active controls** at the
  location (derived from the active settlement's `controls_json`). Keep minimal — only
  risks the active controls actually address. Historical inactive settlements' controls do
  not "cover" current risk.
- **verification_gap_codes**: from `site-evidence` statuses and open incidents —
  conflicting/missing evidence codes, stale floor plans, police-memo identity notes,
  open-incident follow-ups, unresolved tax holds, late-night-monitoring-needed when
  after-hours incidents exist. Map each evidence `evidence_code` + `status` and each open
  incident to the template's gap vocabulary.
- **standard_obligation_codes**: the obligations that are `standard_required=1` for the
  application's `license_class` in `/api/liquor/privileges` (e.g., ID_CHECK, HOURS,
  FOOD_SERVICE for Restaurant/BeerWine). These are ordinary class obligations, separate
  from location controls (`POL-LIQ-001`: standard privileges are separate from controls).
- **location_specific_control_codes**: only the controls in the **active** settlement's
  `controls` list (e.g., SECURITY, CCTV, HOURS, NOISE, PATIO). Do not include inactive
  settlements' controls.
- **first_90_day_plan**: build check_code/timing pairs that operationalize the verification
  gaps and the location's risk profile — recheck conflicting/missing signage, observe id
  checks, follow up police memos, after-hours visits, security/cctv walkthroughs, food-
  service checks, boundary checks. Sequence the timing across first_30_days / days_31_60 /
  days_61_90 so urgent gaps are early.
- **escalation_trigger_codes**: the conditions that would escalate field findings —
  unresolved referred/open incidents (minor sale, violent incident), unverified control
  signage, after-hours service, open tax hold, board-order conflicts, major-incident
  reports. Tie each trigger to a concrete open item or evidence conflict at this location.

Hotel-lounge variants emphasize camera/food-service evidence and late-night monitoring:
when the prompt calls these out, expect camera-evidence/food-service-evidence gaps and
late-night-closing/camera-export checks in the 90-day plan, and missing-camera-coverage /
after-hours-service triggers.

### 3c. Alcohol renewal manual-review queue

- **Boundary**: use the release boundary date named in the prompt (and echoed in the
  renewal rule's `use_violations_on_or_before`). Only violations with `violation_date` ≤
  boundary count toward a license. All violations dated **after** the boundary are
  excluded and collected into `post_boundary_violation_ids_excluded` (sorted by id).
- **Matching**: a violation matches a license by exact `license_no`. When a licensee has
  `successor_to`, violations under the prior license may attach to the successor — mark
  such a license's `match_confidence` as `uncertain` (or `close_address` per template
  vocab) and add its license number to the close/uncertain summary list. Distractor
  violations that merely share an address/facility name with a different license are **not**
  matches — exclude them silently.
- **matched_violation_ids**: the pre-boundary matched violations, sorted by violation date
  ascending then violation_id ascending. `violation_count` is the count of these.
  `most_recent_violation_date` is the latest matched date.
- **Ranking**: rank all target licenses into a queue of the requested size (ranks 1..N,
  no gaps). Rank by the severity-weighted volume of pre-boundary matched violations
  (serious > medium > minor), tie-broken by count then most-recent date then license id.
  The heaviest matched-history licenses rank first.
- **risk_tier**: high when matched history includes open serious violations or large fine
  balances; medium for moderate matched history; low for light history.
- **next_step_label**: map to the template's labels — `board_review` for open serious
  violations / major incidents; `manual_ALERT_check` when `alert_flag=1` on matched
  violations (rule: alert_flag requires manual review); `manual_fine_check` for large
  unpaid fine balances; `additional_record_check` otherwise. Prefer the most severe
  applicable label per license.
- **board_review_license_numbers**: all licenses whose next step is board_review, sorted.

## Step 4 — Build the summary consistently

The summary must be **derived from** the application/queue decisions, not hand-set, so it
stays consistent:

- Contractor: `approve_count` / `hold_count` / `deny_count` sum to the batch size;
  `high_risk_application_ids` = every application whose risk_tier is high, sorted;
  `policy_impacted_application_ids` = every application with policy_impacted true, sorted;
  `stale_or_unverified_correspondence_ids` = every material correspondence record lacking
  agency verification, sorted.
- Renewal: `queue_size` = N; `boundary_date` = the release boundary;
  `post_boundary_violation_ids_excluded` and the per-field id lists each sorted per the
  template.

Recount the summary after every change to a decision so the counts and id lists never drift
out of sync with the per-record payloads.

## Step 5 — Emit only the conforming JSON

- Output one JSON object matching the template exactly: only the keys the template lists,
  in the required orderings, using only the allowed enum values.
- Use empty arrays `[]` where nothing applies. Never include prose, markdown, citations,
  comments, or extra keys.
- Drop all working notes, distractor records, and out-of-batch ids from the final object.

## Output-quality checklist

- [ ] Every enum value used appears in the template's `allowed_values` for that field.
- [ ] Every list is sorted per its ordering rule (and de-duplicated where required).
- [ ] Batch summaries are recomputed from the decisions; counts sum to the batch size.
- [ ] Financial-currency checks use the **review date**, not just the record `status`.
- [ ] Endorsement deficiencies only where the policy requires an endorsement.
- [ ] `policy_impacted` reflects the legacy-baseline comparison, not applicant faults.
- [ ] Queue: only pre-boundary matches counted; post-boundary ids in the excluded list;
  successor matches flagged uncertain.
- [ ] No internal iteration artifacts, no endpoint/transport references, no narrative —
      just the conforming JSON object.
