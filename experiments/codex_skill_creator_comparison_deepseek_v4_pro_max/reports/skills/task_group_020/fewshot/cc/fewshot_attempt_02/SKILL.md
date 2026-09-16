---
name: deal-workbench
description: Use the M&A deal workbench REST API to review acquisition agreements, produce structured legal deliverables (issue registers, closing-package analyses, committee escalation memos, transition reviews, deviation matrices), and cross-reference draft terms against party playbooks or policy thresholds. Use this skill whenever the user needs to analyze a deal on the workbench, prepare seller-side or buyer-side M&A deliverables, compare agreement terms against a playbook, calculate economic exposure from term deviations, build structured deal-data JSON outputs, or work with the `<TASK_ENV_BASE_URL>` deal platform. Trigger even when the user does not explicitly name the workbench but describes M&A deal review, APA/SPA term analysis, or structured legal outputs tied to a deal ID and a playbook or policy.
compatibility: This skill assumes a running M&A deal workbench server. The base URL can be provided explicitly or through the `<TASK_ENV_BASE_URL>` sentinel. No local tooling is required beyond an HTTP client (curl or equivalent).
---

# M&A Deal Workbench Analysis

Use the running deal-workbench REST API to gather deal records, draft terms, playbook rules, policy thresholds, and ancillary data (risk estimates, consents, employee records, regulatory facts, benchmarks, material contracts, diligence findings, cap tables, documents, and notes). Cross-reference findings to produce the structured JSON deliverable the user requests.

## API Surface

The workbench base URL appears as `<TASK_ENV_BASE_URL>` in the prompt or is provided directly. Start every data-gathering pass by fetching at least these resources for the deal:

- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>` — deal header (headline value, parties, structure, dates)
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/terms` — current draft terms
- Applicable playbook: `<TASK_ENV_BASE_URL>/api/playbooks/<playbook_id>/rules` (seller or buyer, as directed)
- Applicable policy: `<TASK_ENV_BASE_URL>/api/policies/<policy_id>/thresholds` (when the task calls for policy-level comparison)

Then pull conditionally relevant records:

- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/risk-estimates`
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/employees`
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/consents`
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/regulatory`
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/benchmarks`
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/material-contracts`
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/diligence-findings`
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/cap-table`
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/documents`
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/notes`

Read-only SQL cross-checks: `POST <TASK_ENV_BASE_URL>/api/query` with JSON body `{"token": "deal-workbench-readonly", "sql": "<single SELECT or WITH statement>"}`. Use this sparingly — only when cross-table consistency checks are needed beyond what the single-resource endpoints provide.

No web UI interaction is required; all the structured data is accessible through the REST API.

## General Workflow

1. **Read the prompt and the answer template jointly.** The template defines every field name, enum value, unit constraint, and the expected root shape. Treat it as the authoritative schema. Do not add, rename, or omit fields.

2. **Pull the full deal data.** Fetch all relevant endpoints **in parallel** when requests are independent (for example, `/deals/<id>`, `/deals/<id>/terms`, `/playbooks/<id>/rules` can all be fetched simultaneously). Use curl with `--parallel` or launch parallel requests.

3. **Match terms to playbook rules or policy thresholds.** For each draft term, locate the corresponding rule in the playbook or threshold in the policy. A term that appears in the draft but is absent from the playbook is not inherently a problem — it is only an issue when it contradicts an affirmative seller/buyer position. Conversely, a playbook rule with no matching draft term is a **missing required term** when the surrounding deal data shows the need for it.

4. **Calculate dollar amounts from headline purchase price** unless a source (term, finding, risk estimate) explicitly states a different basis. The headline value lives on the deal object (`/api/deals/<id>`).

5. **Populate only the fields the template requires.** Use `null` for truly inapplicable fields (not `0` or `""`), and use empty arrays `[]` only when the schema explicitly asks for them (for example, `source_term_ids: []` for missing terms). Treat the template's enums as exhaustive closed sets.

6. **Return only valid JSON** — no markdown fences, no explanatory text. The answer should be parseable by any JSON parser directly.

## Numeric Conventions

- **Dollar amounts**: integer USD (no cents, no `$` sign). If a percent-based calculation produces a fractional result, round to the nearest integer.
- **Percentages (percent points)**: decimal number, typically to two decimal places (e.g., `14.0`, not `14%` or `0.14`). If the template specifies one decimal place, honor that exactly.
- **Months**: integer months.
- **Fully diluted percentages**: four decimal places when in holder-allocation tables.
- **Dates**: `YYYY-MM-DD` strings.

When the template says "percent" but specifies "whole percent points" for certain fields, match the template, not the default rule.

## Playbook Comparison Logic

Playbook rules carry a **preferred** and a **fallback** position. Interpret them as follows:

- **preferred**: what the party ideally wants. Use as the starting negotiating position.
- **fallback**: the walk-away floor. Crossing this line turns a MEDIUM issue into HIGH.

A draft term can be in one of these states relative to a playbook:

| Status                   | Meaning                                                                 |
|--------------------------|-------------------------------------------------------------------------|
| `in_policy`              | Draft matches or exceeds the party's position. No action needed.        |
| `out_of_policy`          | Draft conflicts with an explicit playbook rule.                         |
| `missing_required_term`  | Playbook requires this term; the draft is silent.                       |
| `draft_exceeds_playbook` | Seller sees buyer draft going past what seller will accept.             |
| `draft_below_playbook`   | Buyer sees seller draft falling below what buyer requires.              |

When the task uses **policies** (committee-level thresholds) instead of playbooks, the comparison is simpler: is the draft value above or below the threshold? Policy thresholds are typically hard caps or minimums, without preferred/fallback tiers. Adapt the status labels accordingly.

## Risk Rating

Assign `HIGH`, `MEDIUM`, or `LOW` based on the gap between the draft and the party's position, considering:

- **HIGH**: dollar exposure or closing-certainty impact is substantial, the term falls outside the fallback, or fundamental protections are missing.
- **MEDIUM**: the deviation is real but manageable through negotiation; the fallback position can be reached.
- **LOW**: cosmetic or easily resolved items.

Use risk-estimate data from `/api/deals/<id>/risk-estimates` to inform ratings when available.

## Recommended Actions

Pick from the available actions (the template's `allowed_enums` dictate the exact values). Common actions include:

- `delete` — remove a buyer term the seller will not accept (e.g., financing condition).
- `revise` — redline the existing draft term toward the playbook position.
- `add` — insert a missing required term.
- `accept` — take the draft as-is (in-policy or close enough).
- `escalate` — push to committee/business lead when the decision exceeds counsel's remit.

## Priority Ordering

When the template asks for `priority_order`, sort issues from highest to lowest negotiation priority. The ordering logic:

1. Closing-certainty issues (financing conditions, regulatory clearance, required consents that could kill the deal).
2. High-dollar economic exposure (escrow size, indemnity caps, break fees).
3. Employee and transition protection (continuity, service credit, PTO liability, TSA scope).
4. Restrictive covenants, survival periods, baskets, and other indemnity mechanics.
5. Tax allocation, governing law, and other structural terms.

Within a tie, larger delta-to-fallback amounts win.

## Exposure and Delta Calculations

- **delta_to_fallback**: the absolute difference between the draft and the fallback position. For a draft that exceeds the fallback in the wrong direction, this is `draft - fallback` (when the draft is too high from seller's perspective) or `fallback - draft` (when the draft is too low from buyer's perspective). Always a positive integer.
- **shortfall_dollars**: when the draft provides $0 of something the party needs, the total dollar gap is the fallback amount.
- **quantified exposure**: use the risk-estimate endpoints to ground dollar ranges (low/high) rather than inventing numbers.
- **headline_value**: always pull from the deal record. For a percentage-based calculation, multiply `headline_value * (percent / 100)`.

## Deliverable Types

The five training patterns cover these recurring deliverables. Read the appropriate reference for step-by-step detail when the prompt matches one of these shapes:

- **Issue Register** — seller-side term-by-term analysis with priority ordering and summary metrics ([references/issue-register.md](references/issue-register.md))
- **Closing & Economics Package** — buyer-side SPA economic breakdown including holder allocation, indemnity, escrow, NWC, consents, employment, restrictive covenants, D&O tail, regulatory, and closing readiness ([references/closing-package.md](references/closing-package.md))
- **Committee Escalation Memo** — policy-level threshold comparison with benchmark support and aggregate committee summary ([references/committee-escalation.md](references/committee-escalation.md))
- **Transition Review** — carveout APA transition/separation terms: IP, domains, TSA, tax allocation, employee continuity, outside-date protection, governing law ([references/transition-review.md](references/transition-review.md))
- **Deviation Matrix** — buyer-side position mapping across indemnity, survival, materiality scrape, escrow, consents, HSR, and material contracts with closing blocker enumeration ([references/deviation-matrix.md](references/deviation-matrix.md))

Read the reference file only when the deliverable type matches. If the prompt does not fit any of these five patterns, apply the general workflow above using the answer template as your guide.

## Edge Cases

- **Missing term records**: when a playbook rule exists but no corresponding draft term is found, mark `source_term_ids` as `[]` and status as `missing_required_term`. Only do this when the surrounding data (employee counts, consent records, regulatory flags) confirms the term is actually needed.
- **Stale data**: if the prompt says to ignore in-policy or stale terms, cross-check every term against the playbook/policy and exclude those that pass.
- **Multiple documents with similar IDs**: always confirm the deal_id prefix matches. A consent from `PRJ_ALPHA` does not apply to `PRJ_BETA`, even if the numeric suffix is the same.
- **Basket not found**: if the template asks about basket treatment but the playbook and terms contain no basket data, report status as `not_found_in_current_records` rather than inventing a position.
- **Knowledge qualifier not found**: same pattern — report `not_found_in_current_records` when the data is absent.
- **Escrow agent and release terms missing**: report `not_found_in_current_records` for both when the draft and ancillary records are silent.
- **Hell-or-high-water**: when the regulatory record or playbook says HSR applies but the draft lacks a hell-or-high-water covenant, record `hell_or_high_water_required: false` or the equivalent from that record rather than assuming.

## Output Discipline

- Never include markdown code fences around the JSON.
- Never add prose commentary outside the JSON structure.
- Validate the output against the template's `required_*_fields` and `allowed_enums` before returning.
- Use stable IDs from the workbench (term IDs, consent IDs, employee IDs, finding IDs) — do not invent IDs.
- When the template provides `stable_issue_ids` or `stable_redline_ids`, use only those values.
