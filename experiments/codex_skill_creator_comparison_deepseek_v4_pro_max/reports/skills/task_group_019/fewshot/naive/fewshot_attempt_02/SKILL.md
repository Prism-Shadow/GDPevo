---
name: licensing-review
description: Solve state licensing board review tasks by calling business-record APIs, applying policy rules, and producing structured JSON decisions for contractor eligibility batches, restricted liquor license transfers, and alcohol license renewal queues.
---

# Licensing Review Skill

Solve structured licensing-board review tasks. The task prompt identifies the
task variant, the target application/license IDs, and the `answer_template.json`
in `input/payloads/`. Use the environment's business-record APIs to pull the
records, apply the rules distilled below, and return one JSON object that
exactly matches the template.

## The three task families

| Family | Typical prompt cues | API surface |
|---|---|---|
| Contractor batch eligibility | "Senior Licensing Examiner", "contractor", application batch like `C-xxxx-xxx`, `answer_template.json` with `application_decisions` / `summary` | `/api/policies`, `/api/contractor/*`, `/api/sql` |
| Restricted liquor license transfer | "staff review package", "restricted liquor license transfer", single `L-xxxx-xxx`, location `LOC-xxxx`, `recommended_posture` | `/api/policies`, `/api/liquor/*`, `/api/sql` when listed |
| Alcohol renewal manual-review queue | "Alcohol Renewal Unit", "ranked manual-review queue", `AL-xxxx-xxx`, release boundary date, `queue` / `summary` | `/api/alcohol/licensees`, `/api/alcohol/violations`, `/api/renewal/rules`, `/api/sql` |

Identify the family from the prompt before pulling records.

## General workflow (every task)

1. Read the prompt to find the task family, target IDs, answer-template path,
   and any special instructions (review date, boundary date, domain focus).
2. Read the `answer_template.json` from `input/payloads/` to understand the
   required output shape, allowed enum values, and ordering rules.
3. Call `GET /api/policies` first. Policies define current standards that affect
   deficiency detection and `policy_impacted` decisions.
4. Call every relevant API endpoint listed in the prompt. Use `POST /api/sql`
   with header `X-Task-Token: licensing-review-019` only when relationships
   cannot be resolved from the REST endpoints or the prompt explicitly lists it.
5. Cross-reference records: match applications/licensees to bonds, insurance,
   violations, inspections, incidents, site-evidence, privileges, settlements,
   correspondence, and license-history by shared identifiers.
6. Apply the family-specific decision rules (below).
7. Build the JSON output. Use the enum values from the answer template exactly.
   Sort arrays as the template directs. Use empty arrays (`[]`) when no codes
   apply. Do not add prose, markdown, citations, or extra keys.

## Contractor batch eligibility rules

Contractor tasks use the endpoints under `/api/contractor/` plus `/api/policies`
and optionally `/api/sql`.

### Reading the records

Pull and cross-reference these per application:

| Endpoint | What to look for |
|---|---|
| `/api/contractor/applications` | Application status, endorsement requirements, experience claims |
| `/api/contractor/bonds` | Bond amount, status (active/cancelled), effective dates |
| `/api/contractor/insurance` | Coverage amount, status (current/expired/pending), expiry dates |
| `/api/contractor/license-history` | Active suspensions, prior license statuses |
| `/api/contractor/violations` | Open violations, severity (minor/serious), status |
| `/api/contractor/correspondence` | Stale or unverified items (status = `unverified`, or dates outside expected windows) |
| `/api/contractor/inspections` | Documentation gaps, safety recheck status |

### Determination logic

**DENY** when any of these is present:
- `active_suspension` in license-history
- `open_serious_violation` or `unresolved_serious_complaint` in violations
- Multiple high-severity deficiencies that the policy treats as disqualifying

**HOLD** when deficiencies exist but none of the DENY triggers apply:
- Bond issues (cancelled, shortfall, missing)
- Insurance issues (expired, not current, pending, shortfall)
- Endorsement issues (missing, pending, not verified)
- Experience shortfall
- Inspection gaps (doc gap, safety recheck needed)
- Open minor violations

**APPROVE** when no deficiencies are found across all record checks.

### Deficiency code matching

Map record conditions to deficiency codes using the answer template's
`allowed_values`. Common mappings:

| Record condition | Typical deficiency code |
|---|---|
| Bond cancelled or absent | `bond_cancelled` / `no_active_bond` |
| Bond amount < policy minimum | `bond_shortfall` |
| Insurance expired | `insurance_expired` |
| Insurance not current (lapsed, no record) | `insurance_not_current` |
| Insurance binding pending | `insurance_pending` |
| Insurance amount < minimum | `insurance_shortfall` |
| Required endorsement not on file | `endorsement_missing` / `endorsement_not_verified` |
| Endorsement in process, not confirmed | `endorsement_pending` |
| Documented experience < threshold | `experience_shortfall` |
| Inspection has doc gap | `inspection_doc_gap` |
| Safety recheck not completed | `inspection_safety_recheck` |
| Open minor violation | `open_minor_violation` |
| Open serious violation | `open_serious_violation` / `unresolved_serious_complaint` |
| Active suspension in history | `active_suspension` |

### Required action mapping

Each deficiency maps to one or more actions. Use the answer template's
`allowed_values` for `required_actions`. Common mappings:

- Bond cancelled -> `obtain_current_bond` / `file_active_bond`
- Bond shortfall -> `increase_bond_amount` / `increase_bond`
- Insurance expired/not current -> `provide_current_insurance`
- Insurance pending -> `verify_insurance_binding`
- Insurance shortfall -> `increase_insurance_amount` / `increase_insurance`
- Endorsement missing -> `obtain_required_endorsement` / `verify_endorsement`
- Endorsement pending -> `verify_pending_endorsement`
- Experience shortfall -> `submit_experience_evidence` / `document_experience`
- Inspection doc gap -> `clear_document_gap`
- Safety recheck -> `complete_safety_recheck`
- Open minor violation -> `resolve_minor_violation_review`
- Open serious violation -> `resolve_serious_violation` / `resolve_complaint`
- Active suspension -> `board_review_suspension` / `clear_suspension` + `board_review`

Always include `board_review` as an action when the determination is DENY or
when the deficiency involves suspension or serious violations.

### Risk tier

- `high`: Active suspension, open serious violation, unresolved serious
  complaint, or three or more serious deficiencies.
- `medium`: One or more deficiencies but no DENY-level triggers.
- `low`: No deficiencies (APPROVE).

### Policy impact

`policy_impacted` is `true` when the current policy baseline (read from
`/api/policies`) creates or changes a deficiency that would not have existed
under a prior baseline. Compare policy effective dates against application
timelines. A policy change that introduces a new minimum bond amount or new
endorsement requirement mid-cycle is the canonical case.

### Summary

- `approve_count`, `hold_count`, `deny_count`: count determinations.
- `high_risk_application_ids`: application IDs with `risk_tier: "high"`.
- `policy_impacted_application_ids`: IDs where `policy_impacted` is true.
- `stale_or_unverified_correspondence_ids`: correspondence IDs with status
  `unverified` or dates indicating staleness.

## Restricted liquor license transfer rules

Liquor tasks use `/api/liquor/*` plus `/api/policies` and optionally `/api/sql`.

### Reading the records

| Endpoint | What to look for |
|---|---|
| `/api/liquor/applications` | Application details, license class, premises |
| `/api/liquor/settlements` | Any settlement agreements or tax holds |
| `/api/liquor/privileges` | Current privileges tied to the license |
| `/api/liquor/incidents` | Reported incidents, follow-ups needed |
| `/api/liquor/site-evidence` | Photos, floor plans, control signage, police memos, neighbor notices |

### recommended_posture

- `issue_restricted`: All evidence verified, risks covered, obligations clear.
- `request_follow_up`: Verification gaps remain; license can proceed after
  follow-up items are cleared.
- `deny`: Unresolvable issues (e.g., serious incidents, unresolvable tax holds,
  police memo conflicts that cannot be cleared).

### same_premises_basis_applies

Check the policies for same-premises rules. This is `true` when the application
operates at the same premises as a prior license and the policy treats that
as relevant (which it does in the training examples).

### covered_risk_codes

Risks from incidents or site evidence that are addressed by existing controls.
For example, if a noise risk exists and the location has noise controls or patio
controls, list the risk code. Use the template's allowed values.

### verification_gap_codes

Evidence items that are missing, conflicting, or stale. Map from site-evidence
records:

- Missing signage -> `CONTROL_SIGNAGE_CURRENT_MISSING` / `control_signage_missing`
- Conflicting signage -> `CONTROL_SIGNAGE_CONFLICTING`
- Stale/conflicting floor plan -> `FLOOR_PLAN_STALE` / `FLOOR_PLAN_CONFLICTING` / `floor_plan_conflicting`
- Missing neighbor notice -> `NEIGHBOR_NOTICE_MISSING` / `neighbor_notice_missing`
- Open incident follow-up -> `OPEN_INCIDENT_FOLLOW_UP`
- Police memo conflict -> `POLICE_MEMO_CONFLICTING` / `police_memo_identity_note`
- Missing site photo -> `SITE_PHOTO_MISSING` / `site_photo_missing`
- Missing tax clearance -> `TAX_CLEARANCE_MISSING` / `tax_hold_unresolved`
- Missing camera evidence -> `camera_evidence_missing`
- Missing food service evidence -> `food_service_evidence_missing`
- Late night monitoring needed -> `late_night_monitoring_needed`

### standard_obligation_codes

Standard license-class obligations from policies. Common examples:
`ID_CHECK`, `HOURS`, `FOOD_SERVICE`, `CCTV`, `SECURITY`, `NOISE`, `PATIO`,
`DELIVERY`. Include only what the policy requires for the license class.

### location_specific_control_codes

Controls that are active at this specific location (from site-evidence,
privileges, or application records). These overlap with obligation codes but
represent location-specific active controls rather than class-wide requirements.
Use the same code vocabulary.

### first_90_day_plan

Build monitoring check items from verification gaps and risks. Each item has
a `check_code` and a `timing` (one of `first_30_days`, `days_31_60`,
`days_61_90`). Map gaps to checks:

- Signage gaps -> `control_signage_recheck` / `control_signage_review` (first_30_days)
- ID check risks -> `id_check_observation` (first_30_days)
- Police memo issues -> `police_memo_follow_up` (first_30_days)
- Camera/security gaps -> `security_cctv_walkthrough` / `camera_export_test` (first_30_days)
- After-hours risk -> `after_hours_visit` / `late_night_closing_visit` (days_31_60)
- Food service gaps -> `food_service_check` / `food_service_service_area_check` (first_30_days)
- Noise/patio issues -> `noise_patio_boundary_check` (days_61_90)
- Tax clearance -> `tax_clearance_check` / `tax_clearance_review` (first_30_days)
- Incident log -> `incident_log_review` (first_30_days)
- Noise log -> `noise_log_review` (days_31_60)
- Patio boundary -> `patio_boundary_check` (days_61_90)

Order checks in operational sequence: urgent verification first (30 days),
observation checks next (31-60), follow-up reviews last (61-90).

### escalation_trigger_codes

Conditions that should trigger escalation. Derived from the risks and gaps:

- After-hours risk -> `AFTER_HOURS_VIOLATION` / `after_hours_service`
- Signage not verified -> `CONTROL_SIGNAGE_NOT_VERIFIED`
- Major incident -> `MAJOR_INCIDENT_REPORTED` / `unreported_violent_incident`
- Minor sale unresolved -> `REFERRED_MINOR_SALE_UNRESOLVED` / `minor_sale`
- CCTV failure -> `SECURITY_CCTV_CONTROL_FAILURE` / `missing_camera_coverage` / `footage_not_produced`
- Tax hold reopened -> `TAX_HOLD_REOPENED` / `open_tax_hold_uncleared`
- Food service not available -> `food_service_not_available`
- Noise/patio breach -> `noise_or_patio_breach`
- ID check failure -> `id_check_failure`
- Board order conflict -> `BOARD_ORDER_CONFLICT`
- Patio boundary failure -> `patio_boundary_failure`

## Alcohol renewal queue rules

### Reading the records

| Endpoint | What to look for |
|---|---|
| `/api/alcohol/licensees` | All license records with facility names, addresses, statuses |
| `/api/alcohol/violations` | All violations with dates, license references, severity |
| `/api/renewal/rules` | Renewal criteria, ranking rules, boundary date handling |
| `/api/sql` | Use when cross-referencing requires complex joins |

### Queue construction

1. Read all licensees for the target IDs.
2. Read all violations.
3. Apply the boundary date: only violations on or before the boundary date
   count for the queue. Exclude violations after the boundary date and collect
   their IDs for `post_boundary_violation_ids_excluded`.
4. Match violations to licensees. Primary match is by license number (exact).
   If a violation references a prior/old license number or similar address, use
   `close_address`. If the match is ambiguous, use `uncertain`.
5. Rank licensees. The dominant factors in the training data:
   - Violation count (more violations -> higher rank)
   - Most recent violation date (more recent -> higher rank)
   - Match confidence (exact -> higher than close_address)
   - Violation severity matters for risk tier and next_step_label
6. Assign `risk_tier`:
   - `high`: Multiple (3+) violations or recent serious violations
   - `medium`: Fewer violations, less recent
   - `low`: No or very old violations
7. Assign `next_step_label`:
   - `board_review`: Licensees with serious patterns, many violations, or
     close_address matches that need board judgment.
   - `manual_fine_check`: Licensees with several violations that may involve
     fines requiring manual calculation.
   - `manual_ALERT_check`: Licensees with alert-triggering violation patterns.
   - `additional_record_check`: Licensees needing further record pull.
8. Sort `matched_violation_ids` by violation date ascending, then ID ascending.
9. Build the summary:
   - `queue_size`: 10 (or as specified)
   - `boundary_date`: from the prompt
   - `post_boundary_violation_ids_excluded`: all violation IDs after the
     boundary date
   - `close_or_uncertain_match_license_numbers`: licenses with non-exact matches
   - `board_review_license_numbers`: licenses with `next_step_label: board_review`

### Ranking tiebreakers

When violation counts are equal, the more recent violation date wins the higher
rank. When both are equal, exact matches rank above close_address, which ranks
above uncertain.

## SQL usage

When `POST /api/sql` is available, use it only for queries that cannot be
answered by the REST endpoints. Always include the header
`X-Task-Token: licensing-review-019`. Use `SELECT` only. Set `limit` to 1000 or
less. Typical uses: joining violations to licensees when the REST endpoints
return separate collections without shared keys, or filtering records by
complex date ranges.

## Output discipline

- Return only the JSON object matching the answer template. No prose, markdown,
  citations, or extra keys.
- Sort arrays as the template specifies (usually ascending lexical order for
  codes and IDs).
- Use empty arrays (`[]`) when no codes apply.
- Use the exact enum strings from the template's `allowed_values`. Do not invent
  new codes.
- For dates, use `YYYY-MM-DD` format.
- For the contractor family, `stale_or_unverified_correspondence_ids` collects
  correspondence record IDs (not application IDs).
- For the renewal family, `most_recent_violation_date` is the latest violation
  date used; `matched_violation_ids` sorts by date ascending then ID ascending.

## Edge cases

- If a record endpoint returns an empty array or 404, treat that record type as
  absent for all target IDs (no deficiencies from that source).
- If an application/licensee has no violations, violation_count is 0 and
  matched_violation_ids is `[]`. It should still be included if the task
  requires a fixed-length queue (use remaining slots).
- If the policy endpoint returns multiple policy versions, use the most recent
  effective policy for the review date.
- `policy_impacted` compares the current policy against the prior baseline
  mentioned in the policy records. If policies show a recent change in required
  minimums, applications that fall below the new minimum but were above the old
  minimum are `policy_impacted: true`.
