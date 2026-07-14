---
name: aster-deal-desk-ma-sop
description: Use for Aster Legal Deal Desk M&A transaction contract review and negotiation tasks.
---

# Aster Deal Desk M&A SOP

## Start Every Task

Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the contract for top-level keys, nested field names, enum spellings, nullability, precision, and ordering.

Use the shared Deal Desk Web/API environment named in the prompt or `environment_access.md`. Do not look for or rely on local environment source files.

Set:

```bash
BASE="<TASK_ENV_BASE_URL>"
DEAL_ID="<requested deal id>"
```

Prefer the JSON API for extraction and the web UI for quick cross-checking:

```bash
curl -sS "$BASE/api/health" | jq .
curl -sS "$BASE/api/deals/$DEAL_ID" | jq .
curl -sS "$BASE/api/clauses?deal_id=$DEAL_ID" | jq .
curl -sS "$BASE/api/documents/<DOC_ID>" | jq .
curl -sS "$BASE/api/policies/<POLICY_ID>" | jq .
curl -sS "$BASE/api/benchmarks?industry=<INDUSTRY>" | jq .
curl -sS "$BASE/api/search?q=<term>" | jq .
```

The full deal endpoint usually bundles `deal`, `documents`, `clauses`, `policy`, and `benchmarks`; start there before making narrower calls.

## Source Precedence

Apply sources in this order:

1. The user prompt and answer template for requested task scope and output shape.
2. Deal-specific records for the requested `DEAL_ID` only.
3. `version_status: "ACTIVE"` documents and clause records listed in `deal.active_documents`.
4. Latest written client instructions, committee records, active term sheet, active draft, active cap table/allocation schedule, financial schedule, material-contract matrix, and disclosure schedules, according to the field being populated.
5. The current client playbook/policy for preferred positions, thresholds, fallback authority, approval owner, severity, and escalation route.
6. Benchmarks only when the task asks for market support, committee context, or a benchmark identifier/count. Do not let benchmarks override client instructions or the playbook.

Treat `STALE`, `TEMPLATE`, stale cap tables, generic provisions, and imported form clauses as distractors unless the answer explicitly asks for superseded sources or override codes. When active client instructions conflict with template material, use the active client instructions and record the override only if the schema has an override field.

Use the active cap table or active allocation schedule for seller allocations. Do not use stale ownership exports when an active schedule exists.

## Task Analysis

For draft review and issue-register tasks, compare each active draft clause's `draft_value` against the playbook/client position and threshold. Include each material deviation once. Omit non-issues unless the template explicitly requires a status for every check.

For first-draft or term-population tasks, populate the drafting-ready client-preferred position using active deal economics, active schedules, and the playbook. Include policy checks or flags for exceptions, conditional escalations, and overrides only where the schema asks.

For committee-escalation tasks, include terms requiring committee-level escalation or recommendation. Route through the committee/approval record when present; otherwise use the policy rule's approval category and threshold.

For transition/carve-out tasks, separately check employee transfer, WARN/severance allocation, TSA/service continuity, IP transition and retained-IP boundaries, restrictive covenants, escrow/cap/basket, NWC mechanics, material consents, HSR/regulatory approvals, and outside closing date.

## Field Conventions

Use exact names from the Deal Desk for parties, targets, sellers, contracts, employees, committee members, approval names, policies, document IDs, clause IDs, and benchmark IDs.

Emit integer U.S. dollars with no commas or symbols. Emit percentages as percentage points, not fractions: use `10`, `10.0`, or `10.00` for ten percent according to the template precision, never `0.10`. JSON numbers do not need trailing zeros.

Use `YYYY-MM-DD` dates. Use integer month counts and exact calendar-day counts when the template asks for days after signing.

Use controlled enum values exactly as listed in the template. Normalize prose to the closest enum only after confirming the source basis. Use `null` for non-applicable numeric fields when the template says number-or-null; use `[]` for empty lists.

Follow template ordering rules exactly. Common patterns:

- Sort issue lists by `issue_id`, escalation lists by `term_id`, and policy checks by `check_id`.
- Sort seller allocations by `seller_name` or `seller_id` as specified.
- Sort contract lists by `contract_name` and code lists alphabetically.
- Sort employee lists by displayed employee name only when the template says so.
- Preserve committee-member order as shown in the committee record unless the template says to sort.
- For evidence lists without an explicit sort rule, use a stable audit order: active source documents, active clause IDs, policy IDs, then benchmark IDs.

## Calculations

Recalculate economics instead of copying prose when numeric fields are requested.

Use these checks:

- `amount_usd = round(base_usd * percent / 100)` as whole dollars.
- `percent = amount_usd / base_usd * 100`, rounded to the requested precision.
- `price_per_as_converted_percent_point_usd = equity_or_headline_value / 100`.
- `per_share_price_usd = equity_or_headline_value / share_count` only when the active cap table provides a share count; otherwise use the template's no-share-count/null convention.
- `nwc_collar_percent_of_equity_value = nwc_collar_usd / equity_value_usd * 100`.
- `basket_amount_usd`, escrow amounts, indemnity caps, break fees, reverse termination fees, and excess amounts must use the base named by the template or clause (`headline value`, `equity value`, or policy threshold).
- Seller proceeds must reconcile to the stated consideration/equity total. Allocate each component by active ownership percentage when the task asks for component-level proceeds.
- Aggregate exposure fields should sum the non-null exposure/excess fields required by the schema and avoid double counting unless the schema defines separate totals.

Before finalizing, verify:

- Component consideration totals equal total consideration/headline value where applicable.
- Seller allocation totals equal the relevant value, allowing only unavoidable whole-dollar rounding.
- Escrow/cap/basket percentages match their dollar amounts.
- Required material consents and post-closing notices are not mixed.
- HSR status, HSR condition, and basis code match the current regulatory memo, not generic template language.

## Common Deal Conclusions

Use the playbook and active records, but these mappings recur:

- Seller-side APA: financing conditions are usually delete/escalate items; buyer assumed-liability covenants, employee transfer, WARN/severance, TSA, IP transition, restrictive covenant scope, escrow/cap/basket, and working-capital resets often drive issues.
- Buyer-side SPA: material top-customer consents are usually closing conditions; non-material notices may be post-closing covenants; no-HSR memo facts can support cooperation-only language.
- Public-company merger: reverse termination fee thresholds, fiduciary out/termination rights, MAE carveouts, regulatory covenants, break fees, and post-closing R&W survival are committee-route candidates.
- Carve-out transactions: TSA duration/services, employee offer standards, retained-IP boundaries, trademark phaseout, operational consents, and minimum outside-date runway are central.

Do not hard-code these conclusions. Confirm each one against the active deal records and policy.

## Answer Shaping

Return exactly one JSON object and no Markdown, memo prose, comments, or citations outside JSON fields. Do not include schema descriptions from the template in the answer.

Include only fields permitted or required by the template. For issue objects, put only relevant `corrected_value` fields; do not fill unrelated allowed fields with guesses.

Include source IDs when the schema asks for auditability, but keep them as IDs only. Do not write evidence narratives unless the template has a prose field.

Validate the completed JSON before returning, for example by piping it through `jq`:

```bash
jq . <completed-output.json> >/dev/null
```

Then scan the final object against the template for missing required keys, enum typos, ordering, numeric precision, and accidental use of stale/template records.
