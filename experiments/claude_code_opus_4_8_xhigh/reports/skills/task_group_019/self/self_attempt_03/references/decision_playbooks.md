# Decision playbooks

Reasoned operating procedures for each observed sub-family. These encode the
*method* (which records to read, how to map findings to the template's codes, how
to keep the summary consistent) — **not** memorized answers. Two tasks in the same
sub-family often use **different enum vocabularies**; always map the underlying
finding to whichever code name *this task's* `answer_template.json` allows. When a
threshold or flag matters, read it live from `/api/policies` or `/api/renewal/rules`.

The three-way ladders below (determination / posture / risk) are the recommended,
policy-grounded default interpretation. The gold answers are not shipped with the
training data, so apply the ladder **consistently across the batch** and make the
summary counts exactly match the per-item decisions — internal consistency is
worth more than any single borderline call.

---

## A. Contractor batch eligibility review
(train_001, train_004 — persona: Senior Licensing Examiner; output:
`application_decisions[]` + `summary`.)

**Per application:**
1. Fetch the application row → note `requested_class`/`trade`, `endorsement_status`,
   `years_experience`, `applicant_name`, `prior_license_id`.
2. Select its **policy** from `/api/policies` by class/trade; parse `details_json`
   for `minimum_bond`, `minimum_insurance`, `minimum_years_experience`,
   `required_endorsement`, `serious_open_violation_blocks`.
3. Evaluate each requirement against the **current** record (use SQL filtered by
   `application_id` so no row is truncated away):
   - **Bond**: is there a bond with `status=active` and `amount >= minimum_bond`?
     - no active bond / current bond cancelled → *bond-cancelled / no-active-bond* deficiency.
     - active but `amount < minimum_bond` → *bond-shortfall*.
   - **Insurance** (evaluate "current" as of the prompt's review date, if given):
     - none active / expired (`expiration_date < review_date` or `status=expired`)
       → *insurance-expired / insurance-not-current*.
     - `status=pending` → *insurance-pending* (verify binding).
     - active but `amount < minimum_insurance` → *insurance-shortfall*.
   - **Experience**: `years_experience < minimum_years_experience` → *experience-shortfall*.
   - **Endorsement**: policy `required_endorsement` non-null and
     `endorsement_status != verified`:
     - `missing` → *endorsement-missing / endorsement-not-verified*.
     - `pending` → *endorsement-pending* (verify).
   - **Suspension/discipline**: join license history by `prior_license_id` /
     `applicant_name`; `status in (suspended, revoked)` → *active-suspension* (hard flag).
   - **Violations**: open violations on the applicant's license:
     - `serious`+`open` → *open-serious-violation* (policy hard block).
     - `minor/medium`+`open` → *open-minor-violation*.
   - **Inspections** (if in scope): `finding_code=DOC_GAP` → *inspection-doc-gap*;
     `finding_code=SAFETY_RECHECK` or `result=fail` → *inspection-safety-recheck*.
   - **Correspondence**: a claim only "verified" by an unverified/stale letter
     (`verified_by_agency=0`) does **not** clear a requirement, and that
     `correspondence_id` goes into `stale_or_unverified_correspondence_ids`.
4. **Map each deficiency to its paired required action** using the template's
   `required_actions` vocabulary (names differ per task). Typical pairing by concept:
   | deficiency concept        | required-action concept                    |
   |---------------------------|--------------------------------------------|
   | no active / cancelled bond| obtain / file active bond                  |
   | bond shortfall            | increase bond amount                       |
   | insurance expired/not-current | provide / renew current insurance      |
   | insurance pending         | verify insurance binding                   |
   | insurance shortfall       | increase insurance amount                  |
   | endorsement missing       | obtain required endorsement / verify       |
   | endorsement pending       | verify pending endorsement                 |
   | experience shortfall      | submit / document experience evidence      |
   | active suspension         | board review / clear suspension            |
   | open serious violation    | resolve serious violation (± board review) |
   | open minor violation      | resolve minor violation review             |
   | inspection doc gap        | clear document gap                         |
   | inspection safety recheck | complete safety recheck                    |
5. **Determination ladder** (recommended default):
   - **DENY** — a policy hard block is present and unresolvable in-cycle: open
     *serious* violation while `serious_open_violation_blocks=true`, or an active
     `suspended`/`revoked` license.
   - **HOLD** — one or more curable deficiencies (bond/insurance/endorsement/
     experience/doc-gap/minor violation) that a required action can fix.
   - **APPROVE** — every requirement met, no live deficiencies.
6. **Risk tier**: `high` for hard blocks or a stack of serious deficiencies;
   `medium` for one or a few curable gaps; `low` when clean/minor.
7. **`policy_impacted`**: `true` when a **current 2025 standard** creates a
   deficiency/flag that the **prior baseline** (`CON-LEGACY`) would not have — e.g.
   the class now needs an endorsement but legacy `endorsement_required_for_specialty=false`,
   or the bond falls short of the current minimum but would clear
   `minimum_bond - minimum_bond_reduction` (10000). Verify against `CON-LEGACY`
   `details_json` live.

**Summary must be consistent:** `approve_count`/`hold_count`/`deny_count` equal the
tallies of the decisions; `high_risk_application_ids` = every app with `risk_tier=high`;
`policy_impacted_application_ids` = every app with `policy_impacted=true`;
`stale_or_unverified_correspondence_ids` = all unverified/stale correspondence ids
across the batch. Sort every list as the template says (usually ascending lexical).

---

## B. Restricted liquor-license staff package
(train_002, train_005 — one application + one location; output is a flat object of
code arrays + a `first_90_day_plan`.)

1. Fetch the application → `license_class`, `location_id` (confirm they match the
   prompt's target application/location).
2. **`standard_obligation_codes`**: from `liquor_privileges` where
   `license_class=<class>` and `standard_required=1`. These are the ordinary
   obligations of the class — kept **separate** from location controls.
3. **`location_specific_control_codes`**: parse `controls_json` of settlements at
   the location; include controls only from settlements with `active:true` and not
   expired. These are the location-tied active controls.
4. **`covered_risk_codes`**: risks at the location (from incidents/settlement bases)
   that the current active controls actually address. Only include a risk you can
   justify as *covered by a current control*.
5. **`verification_gap_codes`**: every site-evidence item that is not `verified`
   (missing/stale/conflicting) maps to the matching gap code; plus open incident
   follow-ups, missing tax clearance / neighbor notice, conflicting floor plan or
   police memo, etc. Match the underlying evidence problem to the template's gap enum.
6. **`same_premises_basis_applies`**: `true` when a `SAME_PREMISES` settlement basis
   / same-premises history supports it (policy `same_premises_history_matters`);
   otherwise `false`.
7. **`recommended_posture`** (`issue_restricted` / `request_follow_up` / `deny`):
   - `deny` — a major/high open incident or fundamental disqualifier.
   - `request_follow_up` — verification gaps remain (missing camera/food-service
     evidence, unresolved tax hold, conflicting evidence) that must be closed first.
   - `issue_restricted` — controls cover the risks and evidence is sufficient;
     issue with the restricted controls in place.
8. **`first_90_day_plan`**: ordered `{check_code, timing}` objects
   (`first_30_days` / `days_31_60` / `days_61_90`). Prioritize the highest-risk
   / gap-closing checks earliest (camera export test, food-service check,
   late-night/after-hours visit, control-signage review, tax clearance, incident-log
   review). Use only the template's `check_code` enum; dedupe per the template's
   ordering rule.
9. **`escalation_trigger_codes`**: field triggers implied by the residual risks and
   uncovered gaps (footage not produced, food service unavailable, after-hours
   service, open tax hold, unreported violent incident, minor sale, etc.), from the
   template's enum.

Emphasis for hotel-lounge / late-night cases: camera coverage & footage export,
food-service evidence, and late-night/after-hours monitoring dominate the gaps,
plan, and triggers.

---

## C. Alcohol renewal manual-review queue
(train_003 — build a ranked queue of the target licenses; output `queue[]` + `summary`.)

1. Read `/api/renewal/rules`; pick the rule whose `release_boundary` == the prompt's
   boundary. From its `details_json`: violations **on or before** the boundary count;
   violations **after** it are distractors → collect their ids into
   `post_boundary_violation_ids_excluded`. Note `alert_flag_requires_manual_review`
   and `unpaid_fines_require_hold`.
2. For each target license (`AL-...`): pull its identity from `alcohol_licensees`
   (`facility_name`, `address`, `successor_to`).
3. **Match violations** in `alcohol_violations` to the license:
   - exact `license_no` match → `match_confidence = exact`.
   - no exact match but same `address` → `close_address`.
   - matched only through a `successor_to` chain → `uncertain`.
   Keep only matched violations dated **on/before the boundary**.
4. Per license compute: `violation_count` (pre-boundary matched),
   `most_recent_violation_date` (latest matched date), and `matched_violation_ids`
   sorted **by violation date ascending, then violation_id ascending**.
5. **`risk_tier`** and **`next_step_label`** from the signals:
   - `alert_flag=1` → manual ALERT check; unpaid `fine_balance>0` → fine check /
     hold; serious/board-level pattern → `board_review`; thin/uncertain evidence →
     `additional_record_check`. Use only the template's enums.
6. **Rank** the queue (typically all target licenses appear, since target queue size
   equals the target count): order by severity/exposure — more pre-boundary
   violations, higher risk tier, more recent activity, alert/unpaid-fine flags rank
   higher. Assign integer ranks 1..N with **no gaps**, output ordered by rank.
7. **Summary**: `queue_size` = queue length; `boundary_date` = the boundary;
   `post_boundary_violation_ids_excluded` sorted by id; 
   `close_or_uncertain_match_license_numbers` = licenses with non-`exact` confidence
   (sorted); `board_review_license_numbers` = licenses with `next_step_label=board_review`
   (sorted).

---

## Cross-cutting reminders
- The prompt's target ids/location and the template's enums are the contract —
  ignore everything else in the tables.
- Prefer filtered SQL over raw GET for the big tables (GET caps at 200 rows).
- Empty array, never a placeholder, when nothing applies.
- Sort and dedupe exactly as each field's `ordering` note says.
- Summaries are derived views of the item decisions — recompute them from your
  final items so they can't disagree.
