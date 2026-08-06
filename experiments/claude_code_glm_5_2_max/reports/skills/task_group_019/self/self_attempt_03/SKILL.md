# Licensing Examination Skill

## Overview

This skill handles structured licensing examination tasks for a State Licensing Board environment. It covers three domains — **Contractor Licensing**, **Liquor Licensing**, and **Alcohol Renewal** — using a shared HTTP API data service. The output is always a single JSON object conforming to a provided answer template; no narrative prose, markdown, or citations are included outside the JSON.

## Environment Access

- **Base URL**: Use the `<TASK_ENV_BASE_URL>` placeholder from the prompt (resolved at task time; typically `http://task-env:9019/`).
- **Auth token**: POST `/api/sql` requires header `X-Task-Token: licensing-review-019`.
- **Only call endpoints explicitly listed** in the prompt. Never guess or invent paths.

## Domain 1 — Contractor Batch Eligibility Review

### When to use
Prompt names contractor application IDs (e.g. `C-TR1-001 … C-TR1-008`, `C-TR4-001 … C-TR4-007`) and asks for a batch eligibility determination.

### Data endpoints to call
| Endpoint | Purpose |
|---|---|
| `GET /api/policies` | Current policy baseline; determines `policy_impacted` flag |
| `GET /api/contractor/applications` | Application details, specialty, experience |
| `GET /api/contractor/bonds` | Bond status, amount, cancellation |
| `GET /api/contractor/insurance` | Insurance currency, coverage amount, expiry |
| `GET /api/contractor/license-history` | Prior licenses, suspensions |
| `GET /api/contractor/violations` | Open/closed violations, severity |
| `GET /api/contractor/correspondence` | Letters, notices; check for stale/unverified items |
| `GET /api/contractor/inspections` | Doc gaps, safety rechecks |
| `POST /api/sql` | Ad-hoc joins when cross-referencing across endpoints |

### Decision logic
1. **Determination** — `APPROVE`, `HOLD`, or `DENY` per application:
   - **DENY** if: active suspension on record, or unresolved serious violation/complaint.
   - **HOLD** if: any deficiency exists that can be remediated (e.g., bond shortfall, insurance pending/expired, endorsement pending, experience shortfall, minor violation open, inspection gap).
   - **APPROVE** if: no deficiencies found and all financial coverage is current.
2. **Deficiency codes** — Assign all applicable codes from the allowed enum. Sort alphabetically within each application.
3. **Required actions** — Map each deficiency to its remediation action. Sort alphabetically.
4. **Risk tier** — `low` for APPROVE with no flags; `medium` for HOLD with minor issues; `high` for DENY or HOLD with serious/suspension issues.
5. **Policy impacted** — `true` when a 2025 policy standard creates a deficiency or flag that would not have existed under the prior baseline. Compare `/api/policies` effective dates against application filing context.
6. **Review date** — Some prompts specify an explicit review date (e.g. `2025-07-18`) for evaluating whether financial coverage is current. Use it when given.

### Financial coverage checks
- **Bond**: Must be active, not cancelled, and meet the required amount. Flag `bond_cancelled` / `no_active_bond` / `bond_shortfall`.
- **Insurance**: Must not be expired relative to the review date. Must meet coverage minimum. Flag `insurance_expired` / `insurance_not_current` / `insurance_pending` / `insurance_shortfall`.

### Correspondence analysis
- Identify correspondence that is stale (old, unresponded) or unverified. Collect their IDs for the `stale_or_unverified_correspondence_ids` summary field. Sort ascending.

### Summary fields
- Count applications by determination.
- List high-risk application IDs (ascending).
- List policy-impacted application IDs (ascending).
- List stale/unverified correspondence IDs (ascending).

## Domain 2 — Restricted Liquor License Staff Package

### When to use
Prompt names a single liquor application ID (e.g. `L-TR2-001`, `L-TR5-001`) and asks for a staff review package.

### Data endpoints to call
| Endpoint | Purpose |
|---|---|
| `GET /api/policies` | Policy rules for liquor restrictions |
| `GET /api/liquor/applications` | Application details, license class |
| `GET /api/liquor/settlements` | Prior settlements or agreements |
| `GET /api/liquor/privileges` | Existing privileges, same-premises basis |
| `GET /api/liquor/incidents` | Reported incidents at or near the premises |
| `GET /api/liquor/site-evidence` | Photos, floor plans, signage, camera evidence |
| `POST /api/sql` | Ad-hoc queries for cross-referencing |

### Decision logic
1. **Recommended posture** — `issue_restricted`, `request_follow_up`, or `deny`:
   - `deny` if: unresolved serious incidents, unresolvable conflicts.
   - `request_follow_up` if: verification gaps exist but are remediable (missing signage, stale floor plan, missing photos).
   - `issue_restricted` if: all verification gaps addressable by conditions/obligations, controls in place.
2. **Same-premises basis** — `true` if the applicant holds an existing license at the same physical premises and the transfer/restriction inherits that basis. Check `/api/liquor/privileges`.
3. **Covered risk codes** — Enumerate risk categories that existing controls or site evidence already address. Draw from incident types, settlement terms, privilege conditions. Sort ascending, deduplicate.
4. **Verification gap codes** — Enumerate gaps where evidence is missing, conflicting, or stale (missing photos, conflicting floor plans, missing signage, missing neighbor notice, missing tax clearance, conflicting police memo, open incident follow-up). Sort ascending, deduplicate.
5. **Standard obligation codes** — Obligations that apply to this license class generally (CCTV, HOURS, ID_CHECK, SECURITY, FOOD_SERVICE, NOISE, PATIO, DELIVERY). Sort ascending.
6. **Location-specific control codes** — Subset of obligation codes that are specifically tied to the target location's conditions. Sort ascending.
7. **First 90-day plan** — Schedule monitoring checks across three windows (`first_30_days`, `days_31_60`, `days_61_90`). Assign `check_code` / `timing` pairs. Prioritize the highest-risk items (open incidents, gap remediation) to the first 30 days. Sort or sequence per template instructions.
8. **Escalation trigger codes** — Events that immediately escalate the file (after-hours violation, major incident, unresolved minor sale, tax hold reopened, board order conflict, signage/control not verified, CCTV failure). Sort ascending, deduplicate.

### Hotel-lounge specifics (when applicable)
- Pay special attention to: camera coverage evidence, food-service evidence, late-night monitoring controls.
- Verification gaps may include `camera_evidence_missing`, `food_service_evidence_missing`, `late_night_monitoring_needed`.
- First-90-day plan may include `camera_export_test`, `late_night_closing_visit`, `food_service_service_area_check`.
- Escalation triggers may include `missing_camera_coverage`, `footage_not_produced`, `food_service_not_available`, `after_hours_service`.

## Domain 3 — Alcohol Renewal Manual Review Queue

### When to use
Prompt asks for a ranked manual-review queue for alcohol license renewals (e.g. `AL-TR3-001 … AL-TR3-010`), specifies a boundary date and target queue size.

### Data endpoints to call
| Endpoint | Purpose |
|---|---|
| `GET /api/alcohol/licensees` | Licensee details, facility names, addresses |
| `GET /api/alcohol/violations` | Violation records with dates |
| `GET /api/renewal/rules` | Rules governing renewal review thresholds |
| `POST /api/sql` | Join violations to licensees, filter by date |

### Decision logic
1. **Boundary date** — Only include violations dated **on or before** the boundary date. Exclude post-boundary violations; list their IDs in `post_boundary_violation_ids_excluded`.
2. **Match violations to licensees** — Join violation records to licensees. When the match is not an exact license-number match, use address proximity or name similarity and set `match_confidence`:
   - `exact`: license number matches directly.
   - `close_address`: address matches but license number doesn't directly.
   - `uncertain`: limited evidence; include but flag.
3. **Rank the queue** — Sort by: highest violation count first, then most recent violation date (latest first), then license number ascending as tiebreaker. Assign integer ranks 1–N (N = target queue size).
4. **Risk tier** — Based on violation count and severity: `high` for many or serious violations; `medium` for moderate; `low` for few minor.
5. **Next step label** — Determined by risk tier and violation type:
   - `board_review`: for high-risk or serious violations.
   - `manual_ALERT_check`: for flagged ALERT-type violations.
   - `manual_fine_check`: for outstanding fines.
   - `additional_record_check`: for uncertain matches needing more data.
6. **Matched violation IDs** — Sort by violation date ascending, then violation_id ascending.
7. **Summary fields**:
   - `queue_size`: equals target size.
   - `boundary_date`: from prompt.
   - `post_boundary_violation_ids_excluded`: sorted ascending by violation_id.
   - `close_or_uncertain_match_license_numbers`: sorted ascending.
   - `board_review_license_numbers`: sorted ascending.

## Cross-Domain Rules

### JSON output discipline
- Return **only** the JSON object. No prose, markdown, comments, or extra keys.
- Use **empty arrays** when no items apply — never omit a required list field.
- Sort lists as specified by the answer template (typically ascending lexical/alpha order).
- Respect exact enum values from the template; never invent new codes.

### Policy baseline check
- Always call `GET /api/policies` first.
- Compare current policy effective dates against each application's context.
- A `policy_impacted = true` flag means the current policy creates a deficiency or review flag that would not have applied under the prior baseline.

### SQL endpoint usage
- `POST /api/sql` with header `X-Task-Token: licensing-review-019`.
- Use for cross-referencing data across endpoints (e.g., joining violations to licensees, checking correspondence against applications).
- Body format: a SQL query string. Only use for read queries (SELECT).

### Common error patterns to avoid
1. **Including post-boundary violations** in alcohol renewal queues.
2. **Missing the policy-impacted flag** on contractor applications affected by a 2025 policy change.
3. **Omitting stale correspondence IDs** from the contractor summary.
4. **Not separating standard obligations from location-specific controls** in liquor packages.
5. **Ranking errors** — rank must be sequential integers 1..N with no gaps.
6. **Sorting violations by ID instead of date** in renewal queue `matched_violation_ids` (sort by date then ID).

## Step-by-step Execution Procedure

1. **Read the prompt** — Identify domain (contractor / liquor / alcohol renewal), target IDs, any explicit review date or boundary date.
2. **Fetch policy baseline** — `GET /api/policies`. Note effective dates and changes from prior baseline.
3. **Fetch all relevant data** — Call every endpoint listed in the prompt. Collect full response payloads.
4. **Cross-reference via SQL if needed** — Use `POST /api/sql` for joins or filters not achievable by inspecting individual endpoints.
5. **Evaluate each target application/license**:
   - Contractor: check bonds, insurance, license history, violations, correspondence, inspections, endorsements, experience.
   - Liquor: check incidents, site evidence, settlements, privileges, floor plans, signage, camera coverage.
   - Alcohol renewal: match violations to licensees, apply boundary date, count and rank.
6. **Determine outcome** per item (APPROVE/HOLD/DENY or posture or rank + next step).
7. **Assign codes** — deficiency, actions, risk, gaps, obligations, triggers as applicable.
8. **Build summary** — counts, ID lists, boundary-excluded IDs.
9. **Produce JSON** matching the answer template exactly. Validate enum values, list orderings, and required keys before returning.
