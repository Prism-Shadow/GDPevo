---
name: ma-deal-workbench-analysis
description: Produce a structured JSON analysis (issue register, deviation matrix, committee memo, or closing package) for an M&A deal on the deal workbench API. Use when a task names a deal_id (e.g. PRJ_XXX), states a client side (buyer/seller), and points at a per-task answer_template.json describing the required JSON shape. Covers gathering the deal record, draft terms, playbook/policy rules, consents, material contracts, employees, regulatory, benchmarks, risk estimates, diligence findings, and notes; comparing the draft against the applicable playbook or committee policy; quantifying dollar/percent/month values; and returning only conforming JSON.
---

# M&A Deal Workbench Analysis

## What this skill does

Deal-workbench tasks give you a **deal_id**, a **client side** (buyer or seller), and a **per-task answer template** (`input/payloads/answer_template.json`). Your job is to query the running M&A workbench for that one deal, analyze the draft deal terms against the applicable **playbook** or **committee policy**, quantify every dollar/percent/month value, and return **one JSON object** that conforms exactly to the template. Return only JSON — no narrative.

## Entry checklist (do these in order)

1. **Read the task prompt and the answer template together.** The template defines every required field, every allowed enum, and every stable ID list. Treat it as a strict schema — do not add fields, do not invent enum values, do not rename keys. The template's prose fields (e.g. `"string"`, `"stable holder name from cap table"`) are rubrics telling you what kind of value to put there.
2. **Confirm the exact `deal_id`** from the prompt and use **only that deal**. The workbench contains many deals with similar names (e.g. "Project Juniper" vs "Project Junia", "Project Meridian" vs "Project Meridian North"). Similarly-named projects do **not** apply. Never mix data across deal_ids even when fields look identical.
3. **Confirm the client side and which reference the prompt tells you to compare against**: a **playbook** (`PB_SELLER_A` or `PB_BUYER_A`) or a **committee policy** (`POL_MA_2025_A` / `POL_MA_2025_B`). The comparison basis determines every "in policy / out of policy / missing / exceeds / below" classification.
4. **Gather all deal resources** before classifying anything (route map below). An issue is only "missing required term" if the surrounding deal data shows the term is needed; absent terms are not automatically issues.
5. **Quantify before classifying.** Compute the dollar/percent/month numbers first, then derive status, risk, and recommendation from the numbers + playbook/policy thresholds.

## Workbench route map

Base URL is the running workbench (the task's `<TASK_ENV_BASE_URL>`). All routes are GET unless noted. JSON lives under `/api/...`; the bare `/`, `/workspace`, `/deals/<id>`, `/playbooks`, `/policies` routes return the HTML web UI — use the `/api/` JSON routes for structured data.

Per-deal resources (replace `<deal_id>`):
- `GET /api/deals` — list of all deals (use only to confirm a deal_id exists; many similarly-named distractors)
- `GET /api/deals/<deal_id>` — deal record: client/counterparty, **headline_value**, upfront_cash, stock_value, milestone_value, client_side, **playbook_id**, **policy_id**, signing_date, meeting_date, transaction_type, strategic_context
- `GET /api/deals/<deal_id>/terms` — the **current draft terms** (the thing you're reviewing). Each term has `term_id`, `category`, `clause_ref`, `draft_value`, `numeric_value`, `unit`, `basis`, `staleness_flag`, `source_document`.
- `GET /api/playbooks/<playbook_id>/rules` — preferred + fallback positions, limit_value/limit_unit, risk_default (PB_SELLER_A, PB_BUYER_A)
- `GET /api/policies` and `GET /api/policies/<policy_id>/thresholds` — committee policy thresholds: policy_standard, threshold_value, threshold_unit, restricted_flag, approval_required
- `GET /api/deals/<deal_id>/consents` — third-party consents: required_for_closing, risk_rating, amount_at_risk
- `GET /api/deals/<deal_id>/material-contracts` — material contracts: consent_required, change_of_control, anti_assignment, annual_revenue
- `GET /api/deals/<deal_id>/employees` — employee groups: count, pto_liability, service_credit_required, warn_risk
- `GET /api/deals/<deal_id>/regulatory` — hsr_required, hell_or_high_water_required, regulatory_approval, threshold_basis
- `GET /api/deals/<deal_id>/benchmarks` — median/mean/upper_quartile/sample_size for positioning
- `GET /api/deals/<deal_id>/risk-estimates` — exposure_low/exposure_high by category (closing certainty, indemnity leakage, transition disruption)
- `GET /api/deals/<deal_id>/diligence-findings` — findings with `amount`, `severity`, `topic`, `finding_id`
- `GET /api/deals/<deal_id>/notes` — negotiation posture / counterparty rationale notes
- `GET /api/deals/<deal_id>/cap-table` — holders, security_class, **fully_diluted_pct**, as_converted_shares
- `GET /api/deals/<deal_id>/documents`, `/cap-table`, `/diligence-findings` — supporting

A read-only SQL endpoint exists at `POST /api/query` (token `deal-workbench-readonly`) for cross-table checks; the per-resource GETs above are sufficient for most tasks.

## How to classify each draft term

For every category the template asks about, compare the **draft term** to the **playbook/policy** reference:

- **Playbook comparison (PB_SELLER_A / PB_BUYER_A):** each rule has a `preferred_position`, a `fallback_position`, a `limit_value`/`limit_unit`, and a `risk_default`. Map to issue_status:
  - draft equals preferred → `in_policy`
  - draft meets fallback but not preferred → `in_policy` (fallback is acceptable)
  - draft is worse than fallback toward the counterparty → `out_of_policy`
  - draft is silent and the seller/buyer position requires an affirmative provision (shown by surrounding data) → `missing_required_term`
  - draft is numerically beyond the playbook ceiling (e.g. a cap or escrow % higher than the seller wants, or a survival longer than wanted) → `draft_exceeds_playbook`
  - draft is numerically short of the buyer's floor (e.g. a cap % lower than the buyer's preferred/fallback) → `draft_below_playbook`
- **Policy comparison (committee escalation):** compare draft `numeric_value` against the policy `threshold_value` on the same `basis`/`unit`. Only escalate terms that are **restricted_flag = yes** for the relevant approval body (usually M&A Committee); a General-Counsel-only or `restricted_flag = no` threshold is **not** a committee escalation. **Exclude stale terms** (`staleness_flag: "stale"`) and terms that are within policy — they are distractors.

Risk rating comes from the playbook `risk_default` (Low/Medium/High) or, for policy items, from the magnitude of the breach and any matching risk estimate. Recommended action follows the playbook `required_action` wording (escalate / revise / add / accept).

## Quantification rules (apply uniformly)

- **Currency = integer USD.** Round to the nearest dollar. No decimals, no cents.
- **Percent points are numbers**, rounded as the template says (two decimals for some tasks, one decimal for others — read the template's `units` block).
- **Months are integers.**
- **Calculate dollar amounts from the deal's headline purchase price unless a source explicitly states a different basis.** Watch the basis field on each term/rule/policy: a reverse-break-fee or termination-fee rule may be stated "of equity value," an indemnity cap "of purchase price," an escrow "of purchase price." Use the **basis the rule/term/policy actually states**, and verify against any in-text dollar figure — when a draft term gives both a percent and a dollar ("X% of equity value, equal to $Y"), recover the implied base as `Y / (X/100)` and use **that** recovered base consistently for the draft amount, the threshold amount, and the delta. The deal record's `headline_value` is total deal value; `stock_value` is the equity portion; an APA may have `stock_value: 0`, meaning the "equity value" basis a draft refers to is usually the headline value.
- **cap-table `fully_diluted_pct` is a fraction (0.092), not a percent (9.2)** despite the field name. The four holders' values sum to 1.0. Use these fractions directly (to the precision the template requests) and allocate cash/stock consideration pro-rata by them.
- **Stable IDs must come verbatim from the workbench** (term_id, consent_id, contract_id, employee_id, finding_id, estimate_id). Use empty arrays `[]` for missing terms. Do not invent IDs except where a template explicitly authorizes a synthetic regulatory/closing-blocker ID.
- **Risk-estimate exposure**: sum `exposure_low` and `exposure_high` across the categories the template says to include; some templates include all categories, some exclude "transition disruption."
- **Benchmarks**: position the draft against `median_value`/`upper_quartile` using the categories `at_or_below_median | between_median_and_upper_quartile | at_upper_quartile | above_upper_quartile | not_applicable`. Position on the metric the benchmark actually measures (e.g. position survival against **general-representation** months, not fundamental).

## Consents, material contracts, and closing blockers

- **Required closing consents** = consents with `required_for_closing: "yes"`. Sum their `amount_at_risk` for the "required consent amount at risk" totals.
- **Material contracts requiring consent** = contracts with `consent_required: "yes"` (not "notice only"). Sum their `annual_revenue` for the "material contract revenue requiring consent" totals.
- **Closing blockers** are required consents + regulatory clearances (HSR where `hsr_required: "yes"`) + material-contract consents. A blocker is `must_be_satisfied_before_closing: true`.
- `hell_or_high_water_required` is almost always "no" on these facts; do not assert a HSR hell-or-high-water covenant unless the data says so.

## Output discipline

- Return **exactly one JSON object** conforming to the template. No prose, no markdown fences, no trailing text.
- Sort arrays the way the template says (most templates say `issue_id` ascending, or by a `priority_order`/`priority_rank` you also provide).
- Use `null` (not `0` and not `""`) for fields that don't apply to an issue; use `0` only when a zero amount is the factual answer (e.g. a draft reverse-break-fee of 0%).
- When a template gives an `allowed_enums` or inline enum list, your value must be one of those strings, case-matched exactly.

## Refer to

- `references/route_map.md` — compact endpoint reference and field→answer-field mapping.
- `references/quantification.md` — the rounding, basis, and ID conventions with the worked conventions for cap-table fractions and equity-value bases.
