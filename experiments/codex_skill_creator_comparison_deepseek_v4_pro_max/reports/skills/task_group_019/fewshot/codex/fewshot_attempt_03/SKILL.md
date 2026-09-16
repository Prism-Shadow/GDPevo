---
name: licensing-review
description: Multi-track government licensing review workflows for contractor applications, restricted liquor licenses, and alcohol renewal manual-review queues. Use when a prompt presents batch eligibility screening (APPROVE/HOLD/DENY determinations with deficiency codes, required actions, risk tiers, and policy-impact flags), restricted liquor-license staff packages (issuance posture, same-premises basis, covered risks, verification gaps, standard vs location-specific controls, 90-day monitoring plans, escalation triggers), or alcohol renewal manual-review queue rankings (license-to-violation matching, recency/count scoring, match confidence, next-step routing, boundary-date filtering). All three tracks depend on REST API data sources accessed via GET endpoints plus optional POST /api/sql with an X-Task-Token header, and produce structured JSON conforming to an answer template.
---

# Licensing Review

## Overview

This skill supports three separate licensing review workflows. Each requires fetching data from a shared task-environment REST service, cross-referencing records against the current policy baseline, and producing a structured JSON decision. The workflows share common API access conventions but differ in domain logic and output shape.

## Common Setup

Every review task uses endpoints under `<TASK_ENV_BASE_URL>`, supplied directly in the prompt. Before touching domain data, always fetch the policy baseline:

```bash
curl -s <TASK_ENV_BASE_URL>/api/policies
```

The policy response defines the current regulatory baseline. All subsequent decisions are evaluated against this baseline. When a deficiency would not have existed under the prior baseline, mark `policy_impacted` as `true`.

SQL queries require the header `X-Task-Token`. The token value is supplied in the environment-access instructions for the task. Use it with:

```bash
curl -s -X POST <TASK_ENV_BASE_URL>/api/sql   -H 'Content-Type: application/json'   -H 'X-Task-Token: <token>'   -d '"query": "<sql>"}'
```

Use SQL when a single GET endpoint cannot answer a cross-domain question (e.g., joining violations to licensees, checking policy-baseline thresholds, or resolving ambiguous record references).

All task output must be valid JSON matching the schema defined in the answer template provided in the input. Do not include prose, markdown, comments, or keys outside the template.

## Track A: Contractor Batch Eligibility

This track screens a batch of contractor applications and returns an APPROVE, HOLD, or DENY determination for each one, with deficiency codes, required actions, risk tier, and policy-impact flags.

### Data Sources

Fetch all of these, then cross-reference each application:

| Endpoint | Use |
|---|---|
| `GET /api/policies` | Current regulatory baseline |
| `GET /api/contractor/applications` | Target applications with endorsements and experience claims |
| `GET /api/contractor/bonds` | Bond status, coverage amount, effective dates |
| `GET /api/contractor/insurance` | Insurance status, coverage limits, expiry dates |
| `GET /api/contractor/license-history` | Prior licenses, suspensions, endorsements verified |
| `GET /api/contractor/violations` | Open complaints or violations (severity matters) |
| `GET /api/contractor/correspondence` | Stale or unverified correspondence IDs for the summary |
| `GET /api/contractor/inspections` | Document gaps, safety recheck requirements |
| `POST /api/sql` | Optional, for complex joins or threshold checks |

### Determination Logic

Work through each application methodically:

1. **Start from the application record.** Note the claimed endorsements, experience, and review date.

2. **Check for blocking conditions** (any single one forces DENY):
   - Active license suspension in the license-history
   - Open serious violation or unresolved serious complaint
   - Inspection result requiring safety recheck

3. **Check bond.** A cancelled or absent bond is a deficiency but alone does not force DENY unless it compounds with a blocking condition. A bond whose coverage falls below the policy-required minimum is a shortfall.

4. **Check insurance.** Expired or not-current policy = deficiency. Coverage below the policy threshold = shortfall. A pending (not yet bound) policy = pending flag, not an expired flag.

5. **Check endorsements.** Each endorsement required by the application class must be verified or at least pending. Unverified endorsements = deficiency. Pending endorsements = pending flag (less severe).

6. **Check experience.** If the claimed experience years fall below the policy minimum for the application class, flag as experience shortfall.

7. **Check violations.** Open minor violations increase scrutiny but do not independently force DENY. Open serious violations force DENY.

8. **Assign determination:**
   - Any blocking condition = **DENY**, risk tier `high`
   - No blocking conditions, one or more deficiencies = **HOLD**, risk tier `medium` (unless multiple serious-looking items push to `high`)
   - No blocking conditions, no deficiencies = **APPROVE**, risk tier `low`

9. **Assign policy_impacted.** Set `true` when a current-policy standard (higher bond minimum, new endorsement requirement, or changed insurance threshold) is the direct cause of a deficiency that would not have existed under the prior baseline. Compare the application data against both the current and prior policy values from the policies endpoint.

10. **Derive required_actions** from each deficiency code. See the mappings in [contractor_rules.md](references/contractor_rules.md).

11. **Stale/unverified correspondence.** From `GET /api/contractor/correspondence`, collect IDs with a status indicating stale, unverified, or unconfirmed. Include these in the summary under `stale_or_unverified_correspondence_ids`. The bundled script [scripts/correspondence_filter.py](scripts/correspondence_filter.py) can help extract stale IDs from a correspondence JSON array.

The full deficiency-code-to-action mapping and risk-tier escalation table is in [contractor_rules.md](references/contractor_rules.md).

## Track B: Restricted Liquor License Staff Package

This track produces a structured staff review package for a single liquor-license application. The output includes the issuance posture, same-premises analysis, risk coverage, verification gaps, standard vs location-specific controls, a 90-day monitoring plan, and escalation triggers.

### Data Sources

| Endpoint | Use |
|---|---|
| `GET /api/policies` | Current policy baseline |
| `GET /api/liquor/applications` | Application class, location, requested privileges |
| `GET /api/liquor/settlements` | Tax-hold status, settlement history |
| `GET /api/liquor/privileges` | Existing privileges at the premises (same-premises basis) |
| `GET /api/liquor/incidents` | Police incidents, assaults, minor sales, noise complaints |
| `GET /api/liquor/site-evidence` | Floor plans, control signage, site photos, police memos, camera evidence, food-service evidence |
| `POST /api/sql` | Optional cross-domain lookups |

### Analysis Steps

1. **Same-premises basis.** Check the privileges endpoint for any existing license or privilege record tied to the same location. If a prior privilege record references the same premises, `same_premises_basis_applies` is `true`.

2. **Covered risk codes.** Identify which risks from the application's risk profile are already mitigated by current controls. Look at existing CCTV requirements, security detail, operating-hours restrictions, and incident history patterns. Only list risks that are demonstrably covered by existing controls.

3. **Verification gap codes.** Compare site evidence against requirements:
   - Missing or conflicting control signage = `CONTROL_SIGNAGE_*`
   - Stale or conflicting floor plans = `FLOOR_PLAN_*`
   - Missing site photos = `SITE_PHOTO_MISSING`
   - Open incident requiring follow-up = `OPEN_INCIDENT_FOLLOW_UP`
   - Conflicting police memo = `POLICE_MEMO_CONFLICTING`
   - Missing neighbor notice = `NEIGHBOR_NOTICE_MISSING`
   - Unresolved tax clearance = `TAX_CLEARANCE_MISSING`

4. **Standard obligations.** List the ordinary obligations that apply to this license class regardless of location. These are class-default requirements like ID_CHECK, HOURS, FOOD_SERVICE.

5. **Location-specific controls.** List the active controls currently imposed at this specific location, drawn from privilege conditions and site-evidence records. These differ from standard obligations: they are location-tied, not class-tied.

6. **Recommended posture.** Assign based on gap severity:
   - Clean or minor gaps only, all critical evidence present = `issue_restricted`
   - Moderate gaps, evidence missing but addressable = `request_follow_up`
   - Critical gaps, serious incident history, unresolved tax holds = `deny`

7. **90-day plan.** Build a sequence of monitoring checks based on the verification gaps. Each check has a `check_code` and a `timing` (first_30_days, days_31_60, days_61_90). Order checks so urgent items (signage, camera, police memo) come earliest.

8. **Escalation triggers.** Define what events on this license would trigger escalation to board review or enforcement. Align triggers with uncovered risks and verification gaps.

The full code sets and mapping guidance are in [liquor_rules.md](references/liquor_rules.md).

## Track C: Alcohol Renewal Manual-Review Queue

This track builds a ranked queue of licenses for pre-renewal manual review, filtered by a boundary date and ranked by risk.

### Data Sources

| Endpoint | Use |
|---|---|
| `GET /api/alcohol/licensees` | License records with facility names |
| `GET /api/alcohol/violations` | All violation records |
| `GET /api/renewal/rules` | Renewal rules including boundary date and ranking criteria |
| `POST /api/sql` | Often needed to join violations to licensees |

### Ranking Workflow

1. **Read renewal rules.** The rules endpoint defines the boundary date, match criteria, and ranking parameters.

2. **Fetch licensees.** Filter to the target license range from the prompt.

3. **Fetch violations.** Retrieve all violation records.

4. **Match violations to licenses.** Use license number as the primary key. For each violation, attempt exact match first. If the license number differs but the facility address matches closely, use `close_address` confidence. If the match is ambiguous, use `uncertain`.

5. **Exclude post-boundary violations.** Any violation with a date after the boundary date is excluded from scoring but listed in `post_boundary_violation_ids_excluded` in the summary.

6. **Rank by priority tier, then recency, then count:**
   - Primary sort: next_step_label tier. `board_review` > `manual_fine_check` > `manual_ALERT_check` > `additional_record_check`.
   - Within the same tier: sort by most recent violation date (more recent = higher rank).
   - Within the same recency: higher violation count ranks first.

7. **Assign next_step_label** based on violation profile:
   - Three or more violations where at least one is recent (within ~90 days of boundary) and the match is exact = `board_review`
   - High violation count but older violations, or close_address confidence = `board_review` (escrow for board review)
   - Moderate count with recent fines = `manual_fine_check`
   - Fewer or older violations without board-level concern = `manual_ALERT_check`
   - Lowest risk, boundary cases = `additional_record_check`

8. **Assign risk_tier.** Licenses routed to `board_review` are typically `high`. Others are `medium` unless the violation count is zero or the violations are minor/old, in which case `low`.

9. **Build queue.** Exactly the requested queue size, ranks 1 through N with no gaps.

10. **Build summary.** Include queue_size, boundary_date, post_boundary_violation_ids_excluded, close_or_uncertain_match_license_numbers, and board_review_license_numbers.

The full ranking matrix and tie-breaking rules are in [renewal_rules.md](references/renewal_rules.md).

## Answer Template Compliance

Each task provides an answer template under `input/payloads/answer_template.json`. Read it first. The template defines:
- Required top-level keys
- Allowed enum values for each field
- List ordering requirements (always ascending lexical or by a specified field)
- Required lengths for lists
- Date formats (YYYY-MM-DD)

Never invent codes, keys, or values outside the template. Use empty arrays when no codes apply. Sort all lists as the template specifies.

## Date Handling

When the prompt provides a review date (e.g., "Use 2025-07-18 as the review date"), use it to judge whether bonds, insurance, and other time-sensitive records are current. A bond or insurance policy that expires before the review date is expired. One that is active on the review date is current. If no review date is given, use the boundary date or the most recent date evident in the policy baseline.

## Policy Impact Analysis

For every deficiency identified, ask: "Would this same deficiency exist under the prior policy baseline?" Compare the current policy thresholds (bond minimums, insurance minimums, endorsement requirements) against the prior ones from the policies endpoint. If the current baseline is stricter and is the direct cause of the deficiency, mark `policy_impacted` as `true`.

## Bundled Resources

### Scripts

- **[correspondence_filter.py](scripts/correspondence_filter.py)** — Reads a JSON array of correspondence records from stdin and outputs a sorted, deduplicated list of IDs whose status indicates stale, unverified, unconfirmed, or pending. Use with: `curl -s $BASE/api/contractor/correspondence | python3 correspondence_filter.py`.

### References

- **[contractor_rules.md](references/contractor_rules.md)** — Deficiency-code-to-action mappings, blocking conditions, risk-tier assignment, and policy-impact detection for contractor batch eligibility.
- **[liquor_rules.md](references/liquor_rules.md)** — Posture decision tree, code sets, obligation/control separation, 90-day plan construction, and escalation triggers for restricted liquor license review.
- **[renewal_rules.md](references/renewal_rules.md)** — Ranking algorithm, violation matching, next-step labeling, risk-tier assignment, and summary construction for alcohol renewal queues.

