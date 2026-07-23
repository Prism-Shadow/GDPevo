# Task-Type Playbooks

Each playbook describes the decision logic for one task type. The logic is stated as rules to apply to the records you fetch — it does not predetermine any specific decision. Always map findings to the EXACT allowed codes in THIS task's `answer_template.json`; code names vary between tasks of the same type.

## Type A — Contractor batch eligibility review

**Inputs:** a batch of application IDs (e.g., 7–8 IDs); an optional review date for currency decisions.
**Endpoints:** `/api/policies`, `/api/contractor/{applications,bonds,insurance,license-history,violations,correspondence,inspections}`, `POST /api/sql`.

For each application, evaluate each domain against the policy baseline, then decide.

**Evidence → deficiency mapping (map each finding to the template's allowed code):**

- **Bond.** An active bond must exist and its amount must meet the policy-required amount for the license class/endorsement. No active bond → a "no active / cancelled bond" code. Amount below required → a "bond shortfall" code.
- **Insurance.** Coverage must be current on the review date and meet the required amount. Lapsed before the review date → an "expired / not current" code. Below required → an "insurance shortfall" code. Submitted but not yet bound → an "insurance pending" code.
- **Endorsement.** If the class requires a specialty endorsement, it must be present and verified. Missing or not verified → a "missing / not-verified endorsement" code. Submitted but pending verification → an "endorsement pending" code.
- **Experience.** Documented experience must meet the class requirement. Below → an "experience shortfall" code.
- **Inspections.** Inspection documentation must be complete and current. Missing or stale docs → an "inspection document gap" code. A failed safety item needing recheck → an "inspection safety recheck" code.
- **Violations / suspension.** An active suspension on license history → an "active suspension" code (disqualifying). An open serious violation or unresolved serious complaint → a "serious violation / complaint" code (disqualifying). An open minor violation → a "minor violation" code (remediable).

**Determination:**

- `DENY` if any disqualifying condition is present (active suspension, open serious violation/complaint).
- Else `HOLD` if any remediable deficiency is present.
- Else `APPROVE`.

**risk_tier:** `high` when denied or any high-severity condition is present; `medium` for a hold with moderate deficiencies; `low` for approve.

**policy_impacted:** `true` when a deficiency or material review flag exists solely because the CURRENT policy baseline applies and the PRIOR baseline would not have created it (compare the two in `/api/policies`). Otherwise `false`.

**required_actions:** emit the remediation action that corresponds to each deficiency code, mapped to the template's allowed action codes (e.g., a bond shortfall → an "increase bond" action; a missing endorsement → an "obtain/verify endorsement" action; an active suspension → a "board review / clear suspension" action). One action per deficiency where the pairing is 1:1.

**Summary:** `approve_count` / `hold_count` / `deny_count` (must sum to the batch size); `high_risk_application_ids` (risk_tier == high, ascending); `policy_impacted_application_ids` (policy_impacted == true, ascending); `stale_or_unverified_correspondence_ids` (correspondence records flagged stale or unverified for any application in the batch, ascending).

**Ordering:** `application_decisions` by `application_id` ascending; `deficiency_codes` and `required_actions` ascending lexical within each application; all summary id lists ascending lexical.

## Type B — Restricted liquor-license staff package

**Inputs:** one application ID + one location ID. The prompt may name focus areas (e.g., hotel-lounge controls, camera/food-service evidence, late-night monitoring) — weight those areas when reading evidence.
**Endpoints:** `/api/policies`, `/api/liquor/{applications,settlements,privileges,incidents,site-evidence}`, `POST /api/sql`.

Derive each field from the records:

- **recommended_posture:** `issue_restricted` when current controls cover the risks and only minor or no verification gaps remain; `request_follow_up` when there are resolvable verification gaps field staff can close (missing/conflicting signage, stale or conflicting floor plan, pending or conflicting police memo, missing neighbor notice, missing site photo, missing camera/food-service evidence, late-night monitoring needed); `deny` when a blocking condition exists (unresolved tax hold, serious or unreported incident, same-premises basis no longer applicable).
- **same_premises_basis_applies:** from applications/settlements history — whether the transfer still relies on the same-premises basis.
- **covered_risk_codes:** risks that current controls (privileges already in place) cover. `covered_risk_codes` and `verification_gap_codes` are complementary.
- **verification_gap_codes:** gaps remaining from site-evidence/incidents/settlements. Map each gap to the template's allowed code.
- **standard_obligation_codes:** the ordinary obligations of the license CLASS from policy (the baseline duties every holder of this class owes), mapped to the template's allowed codes.
- **location_specific_control_codes:** the controls tied specifically to THIS location (from privileges/site-evidence), distinct from the standard class obligations.
- **first_90_day_plan:** a sequence of `{check_code, timing}` monitoring checks across `first_30_days` / `days_31_60` / `days_61_90`, ordered to close the verification gaps — front-load the urgent gaps in the first 30 days, follow up in 31–60 and 61–90. Use only `check_code` and `timing` values from the template.
- **escalation_trigger_codes:** the conditions that should escalate to field staff or the board (after-hours service, noise/patio breach, minor sale, unresolved tax hold, unreported or serious incident, control-verification failure, camera/footage failure), each mapped to the template's allowed escalation code.

**Ordering:** read each field's `ordering` in the template — some require ascending sort plus dedup, others accept any order with each code used at most once; `first_90_day_plan` is returned in operational sequence.

## Type C — Alcohol renewal manual-review queue

**Inputs:** a set of license IDs and a release-boundary date; a target queue size N (e.g., 10).
**Endpoints:** `/api/alcohol/{licensees,violations}`, `/api/renewal/rules`, `POST /api/sql`.

**Match violations to licenses:**

- Direct `license_no` match → `exact`.
- Violation tied to a prior/old license number at the same facility address → `close_address` (use SQL to join licensees↔violations by facility address).
- Ambiguous → `uncertain`.
- A license's `match_confidence` reflects the weakest match among its violations, or the rule in `/api/renewal/rules`.

**Boundary:** include only pre-boundary violations (date on or before the boundary date — confirm inclusive vs exclusive semantics from `/api/renewal/rules`). Violations after the boundary are excluded and listed in `post_boundary_violation_ids_excluded` (sorted by `violation_id` ascending).

**Per-license fields:**

- `violation_count` = number of pre-boundary matched violations.
- `most_recent_violation_date` = latest matched violation date (YYYY-MM-DD).
- `matched_violation_ids` sorted by violation date ascending, then `violation_id` ascending.
- `risk_tier` and `next_step_label` from `/api/renewal/rules` based on the matched violation categories. The allowed `next_step_label` values (from the template) denote severity tiers — e.g., a board-level review label for serious/board-level violations, a fine-level label for fine-level violations, and an ALERT-system label for ALERT-flagged violations.

**Ranking (ranks 1..N, no gaps):** sort by `next_step_label` severity tier (board-level > fine-level > ALERT-level), then `most_recent_violation_date` descending, then `violation_count` descending, then `license_no` ascending. Confirm the tier precedence from `/api/renewal/rules`.

**Summary:** `queue_size` (N); `boundary_date` (YYYY-MM-DD); `post_boundary_violation_ids_excluded` (ascending by `violation_id`); `close_or_uncertain_match_license_numbers` (licenses whose `match_confidence` is `close_address` or `uncertain`, ascending); `board_review_license_numbers` (licenses whose `next_step_label` is the board-level review label, ascending).

**Ordering:** `queue` by ascending rank (1..N, no gaps); `matched_violation_ids` by date asc then id asc; summary lists as specified above.
