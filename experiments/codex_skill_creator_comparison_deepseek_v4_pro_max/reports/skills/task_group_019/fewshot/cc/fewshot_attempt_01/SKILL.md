---
name: licensing-review
description: >-
  Guide for producing structured licensing-review decisions from a regulatory
  data environment. Use when the task asks for contractor application batch
  decisions, restricted liquor-license staff packages, or alcohol renewal
  manual-review queues. Also use when the prompt mentions licensing boards,
  contractor eligibility, liquor transfer reviews, renewal screening, or any
  kind of structured regulatory determination that pulls data from a licensing
  API.
---

# Licensing Review

Systematic workflow for producing licensing decisions from a regulatory
environment. Every task follows the same core loop:

1. Read the answer template to lock in the required output shape.
2. Identify the domain — contractor, liquor, or alcohol renewal.
3. Fetch **all** relevant API data before drawing conclusions.
4. Cross-reference data sources and apply domain-specific rules.
5. Emit one JSON object matching the template exactly.

## Domain detection

| Pattern in prompt or template | Domain |
|---|---|
| `contractor/applications`, `contractor/bonds`, `endorsement`, `experience_shortfall` | **contractor** |
| `liquor/applications`, `liquor/privileges`, `recommended_posture`, `same_premises_basis` | **liquor** |
| `alcohol/licensees`, `alcohol/violations`, `renewal/rules`, `match_confidence`, `queue` | **renewal** |

## Environment

Every task references a base URL (typically presented as `<TASK_ENV_BASE_URL>`).
If an `environment_access.md` file appears in the workspace, read it for the
exact URL, credential header, and endpoint list. The most common endpoints are
summarized below.

### Common endpoints

| Endpoint | What it returns |
|---|---|
| `GET /api/policies` | Current and historical policy baselines with effective dates |
| `GET /api/contractor/applications` | Contractor applications with status, class, endorsements, experience |
| `GET /api/contractor/bonds` | Bond records: amount, status, effective dates |
| `GET /api/contractor/insurance` | Insurance policies: coverage, status, expiration |
| `GET /api/contractor/license-history` | Prior licenses, suspensions, revocations |
| `GET /api/contractor/violations` | Violations: severity, status, dates |
| `GET /api/contractor/correspondence` | Letters and notices: status, dates, verification state |
| `GET /api/contractor/inspections` | Inspection reports: findings, safety rechecks, doc gaps |
| `GET /api/liquor/applications` | Liquor applications with class, location, business details |
| `GET /api/liquor/settlements` | Settlement agreements: covered risks, controls, obligations |
| `GET /api/liquor/privileges` | Historical privileges, same-premises lineage |
| `GET /api/liquor/incidents` | Police/community incidents at the location |
| `GET /api/liquor/site-evidence` | Photos, floor plans, signage, police memos |
| `GET /api/alcohol/licensees` | Licensee records with facility names and addresses |
| `GET /api/alcohol/violations` | Violations with license_no, dates, violation types |
| `GET /api/renewal/rules` | Renewal rule definitions and thresholds |
| `POST /api/sql` | Raw SQL queries when direct endpoint data is insufficient |

Credentials: If the task provides an `X-Task-Token` header value, include it on
every request. Some environments require it for `POST /api/sql`.

---

## Contractor batch review

Use when the answer template contains `application_decisions` and the prompt
targets contractor application IDs.

### Decision framework

For every application in the batch, evaluate these dimensions:

1. **Bond**: Is it active? Does the amount meet the required minimum? If the
   bond is cancelled or the amount falls short, the application is deficient.

2. **Insurance**: Is coverage current as of the review date? If the policy has
   expired or coverage is below the required limit, the application is
   deficient. If the policy status is pending/binding, treat it as a gap.

3. **Endorsements**: Are specialty endorsements verified? If the endorsement
   status is `pending` or `missing`, the application is deficient. A `pending`
   endorsement is different from a `missing` one — pending means it's in
   process and a follow-up may suffice; missing means the applicant must obtain
   it before proceeding.

4. **Experience**: Does documented experience meet the class minimum? A
   shortfall means the applicant must submit further evidence.

5. **License history**: Is there an **active suspension**? An active suspension
   is a hard blocker that forces DENY regardless of other factors. Historical
   suspensions that are resolved are not blocking but may elevate risk.

6. **Violations**: Are there open serious violations? An open serious violation
   is a hard blocker. Open minor violations create a HOLD.

7. **Inspections**: Are there unresolved safety rechecks or documentation gaps?
   These create HOLD conditions.

### Determination logic

- **DENY** when: active suspension, open serious violation, or an unresolvable
  combination where the applicant cannot remedy core requirements within the
  review window.
- **HOLD** when: any fixable deficiency exists (bond, insurance, endorsement,
  experience, inspection, minor violation) but no hard blocker.
- **APPROVE** when: no deficiencies are found across all dimensions.

### Deficiency and action code meanings

The answer template defines the allowed code vocabulary. Use the codes listed in
the template — not codes from a different task. Common code meanings across
contractor tasks:

| Deficiency code | Meaning |
|---|---|
| `active_suspension` / `no_active_bond` | Hard blocker — license suspended or bond absent |
| `bond_cancelled` / `bond_shortfall` | Bond is cancelled or amount too low |
| `insurance_expired` / `insurance_not_current` / `insurance_pending` / `insurance_shortfall` | Coverage issue |
| `endorsement_missing` / `endorsement_not_verified` / `endorsement_pending` | Specialty endorsement gap |
| `experience_shortfall` | Insufficient documented experience |
| `inspection_doc_gap` / `inspection_safety_recheck` | Inspection finding |
| `open_minor_violation` / `open_serious_violation` / `unresolved_serious_complaint` | Violation/complaint issue |

Required actions map 1:1 to deficiencies. Use the action that addresses the
specific gap — for example, `bond_shortfall` → `increase_bond_amount` (or
`increase_bond`); `insurance_expired` → `provide_current_insurance` (or
`renew_insurance`); `endorsement_missing` → `obtain_required_endorsement` (or
`verify_endorsement`). Always use the exact action codes from the current
task's template.

### Risk tier

- **high**: any DENY application, or any HOLD with a severe combination (open
  violations plus other deficiencies, board-review triggers).
- **medium**: HOLD applications with fixable, non-severe deficiencies.
- **low**: APPROVE applications with no deficiencies.

### Policy impacted

Check the `/api/policies` response for a current policy baseline. If a
deficiency flag is **newly triggered** by the current policy standard and would
not have been triggered under the prior baseline, mark `policy_impacted: true`.
Otherwise `false`.

### Correspondence

Review `/api/contractor/correspondence`. Any correspondence that is overdue
for response, has a stale status, or shows an unverified delivery state should
be collected in `stale_or_unverified_correspondence_ids` in the summary.

### Summary

- `approve_count`, `hold_count`, `deny_count`: counts from application_decisions.
- `high_risk_application_ids`: ascending list of IDs with `high` risk tier.
- `policy_impacted_application_ids`: ascending list of IDs with `policy_impacted: true`.
- `stale_or_unverified_correspondence_ids`: ascending list of correspondence IDs.

---

## Liquor staff package (single application + location)

Use when the answer template contains `recommended_posture` and
`same_premises_basis_applies`.

### Evaluation dimensions

1. **Same-premises basis**: Check `/api/liquor/privileges` for prior liquor
   activity at the same address. Also check `/api/liquor/site-evidence` for
   police memos referencing the premises. If there is a documented same-premises
   lineage, `same_premises_basis_applies` is `true`. If the application
   represents a genuinely new location with no prior privilege record, it is
   `false`.

2. **Covered risks**: Review `/api/liquor/settlements` for active settlement
   agreements that cover specific risk categories. Each risk category with an
   active settlement control is a covered risk. Also review incident records for
   risks that the settlement explicitly addresses.

3. **Verification gaps**: Review `/api/liquor/site-evidence` and
   `/api/liquor/incidents` for missing, conflicting, or stale evidence. Gaps
   include missing site photos, conflicting floor plans, stale or missing
   control signage, missing neighbor notices, open incident follow-ups,
   conflicting police memos, or missing tax clearances.

4. **Standard obligations**: These are the default obligations that apply to the
   license class regardless of location. Derive them from the application's
   license class and from policy definitions at `/api/policies`.

5. **Location-specific controls**: These are controls tied to the specific
   location, derived from settlements and site-evidence. They are a subset of
   the full obligation vocabulary that has active site-level enforcement.

6. **First 90-day plan**: Build a monitoring plan that addresses verification
   gaps and risk areas. More urgent gaps go in `first_30_days`; moderate gaps in
   `days_31_60`; longer-term monitoring in `days_61_90`. Use only the check_code
   and timing values from the template.

7. **Escalation triggers**: Conditions that should cause field staff to escalate
   the license for review. Include triggers for risks that are not covered,
   verification gaps that could allow violations, and monitoring failure modes.

### Posture logic

- **issue_restricted**: all covered risks have controls, verification gaps are
  minor or can be resolved by the monitoring plan.
- **request_follow_up**: significant verification gaps remain that require
  applicant action before issuance.
- **deny**: unfixable conditions or risks that cannot be controlled.

### Code reference

See [liquor-codes.md](references/liquor-codes.md) for the full code
vocabularies used across liquor staff package tasks. The answer template always
defines the allowed values — consult the template first, then use the reference
to understand code meanings.

---

## Alcohol renewal manual-review queue

Use when the answer template contains a `queue` array with `license_no`,
`violation_count`, and `match_confidence`.

### Building the queue

1. **Fetch all data**: `/api/alcohol/licensees` for the target license list;
   `/api/alcohol/violations` for the full violation history;
   `/api/renewal/rules` for severity thresholds and ranking criteria.

2. **Match violations to licensees**: For each target license, find violations
   whose `license_no` matches the target license number exactly, or whose
   facility name/address closely matches the licensee record.

3. **Exclude post-boundary violations**: The prompt provides a release boundary
   date. Only violations on or before that date count. Collect all excluded
   post-boundary violation IDs for the summary.

4. **Rank**: Order licensees by a compound score. The renewal rules from
   `/api/renewal/rules` define the ranking formula. In general, rank by
   violation count (descending), recency (most recent first), and severity.
   Assign ranks 1 through N with no gaps.

5. **Match confidence**:
   - `exact`: violation license_no matches the target license_no directly.
   - `close_address`: violation record references the same facility through
     name or address similarity but a different or legacy license number.
   - `uncertain`: weaker circumstantial match; include only when the rules
     require it and note the uncertainty in the summary.

6. **Risk tier**:
   - `high`: multiple violations, recent dates, or board-review criteria.
   - `medium`: fewer or older violations.
   - `low`: minimal history.

7. **Next step label**: The renewal rules define thresholds that map into:
   - `board_review`: severe or pattern violations meeting board escalation
     criteria.
   - `manual_fine_check`: violations involving fines that need manual
     verification.
   - `manual_ALERT_check`: licensees flagged by ALERT system rules.
   - `additional_record_check`: cases where data sources conflict or match
     confidence is uncertain.

### Violation ordering in matched_violation_ids

Sort matched violations by violation date ascending, then by violation ID
ascending. This is a stable secondary sort.

### Summary

- `queue_size`: number of queue entries (must match the target queue size).
- `boundary_date`: the release boundary date from the prompt.
- `post_boundary_violation_ids_excluded`: ascending list of violation IDs with
  dates after the boundary.
- `close_or_uncertain_match_license_numbers`: ascending list of license numbers
  where match confidence is not `exact`.
- `board_review_license_numbers`: ascending list of license numbers with
  `board_review` next step.

---

## Output rules

These apply across all domains.

- Emit **only** the JSON object. No prose, markdown, citations, or keys not in
  the template.
- Order all arrays as instructed by the template (typically ascending by ID or
  code).
- Use empty arrays (`[]`) when no codes, actions, or IDs apply — never `null` or
  omit the key.
- Dates use `YYYY-MM-DD` format.
- Read the answer template carefully. Every allowed value, ordering rule, and
  required key is defined there. Never invent codes or keys that are not in the
  template's enum lists.

## Working with the API

- Call `GET` endpoints directly. For `POST /api/sql`, send a JSON body with a
  `query` field and the `X-Task-Token` header.
- Fetch all relevant endpoints **before** making determinations. Data from one
  endpoint often informs interpretation of another.
- The `/api/policies` endpoint returns policy baselines with effective dates
  that determine whether a given standard is "current." Use these dates to
  decide `policy_impacted` in contractor tasks and to understand which
  obligation codes are active in liquor tasks.
