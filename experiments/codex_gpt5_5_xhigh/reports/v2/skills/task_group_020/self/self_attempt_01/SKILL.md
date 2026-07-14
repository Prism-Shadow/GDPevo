---
name: aster-deal-desk-ma-sop
description: Use for Aster Legal Deal Desk M&A transaction contract review and negotiation tasks.
---

# Aster Deal Desk M&A SOP

## Start With Scope

- Read the task prompt and `input/payloads/answer_template.json` first. The template controls required keys, allowed enums, sorting, precision, nullability, and whether to omit non-issues.
- Work only the requested `deal_id`. Ignore unrelated deals surfaced by search, policy linkage, or index pages unless the prompt expressly asks for comparison.
- Use the remote base URL supplied in the prompt or `environment_access.md` for `<TASK_ENV_BASE_URL>`.

## API Habits

- Health check: `curl -sS "$BASE/api/health"`.
- Primary bundle: `curl -sS "$BASE/api/deals/$DEAL_ID" | jq .`.
  This returns `deal`, `documents`, `clauses`, `policy`, and `benchmarks` in one payload.
- Useful focused endpoints:
  - `GET /api/documents/{doc_id}` for full document sections.
  - `GET /api/policies/{policy_id}` for controlling rule details.
  - `GET /api/benchmarks?industry=...` only when benchmark support is needed.
  - Web pages such as `/deals/{deal_id}`, `/documents/{doc_id}`, `/policies/{policy_id}`, and `/clauses/compare?deal_id=...` are good visual fallbacks.
- Prefer structured JSON from the API. Some document section `text` values are embedded JSON strings or arrays; parse them as data instead of relying on prose.
- Filter active records explicitly:
  - `documents[] | select(.version_status == "ACTIVE")`
  - `clauses[] | select(.version_status == "ACTIVE")`

## Source Precedence

1. Prompt and answer template for scope and output contract.
2. Target deal API bundle for the current deal record and linked active artifacts.
3. Latest active written client instructions/email for client-specific positions, overrides, fallbacks, and escalation triggers.
4. Active current draft and active clause records for what the paper currently says.
5. Active deal schedules for exact economics, cap/allocation data, material consents, regulatory status, employment/TSA/IP details, and committee membership.
6. Controlling linked policy/playbook for thresholds, preferred positions, approval owners, and rule IDs.
7. Benchmarks only as supplemental support where requested; choose matching topic, industry, year/currentness, and definition.
8. Stale/template records only to identify superseded material or override codes when the output schema asks for that.

When sources conflict, prefer latest active deal documents and latest written client instructions over term-sheet summaries, stale schedules, template provisions, or generic benchmarks. Use active client policy over generic standard forms.

## Field Conventions

- Preserve exact party, employee, contract, committee member, document, policy, rule, and clause IDs.
- Normalize enums exactly as the template allows. Convert display/prose values to enum form only when clear, e.g. lowercase `deductible` to `DEDUCTIBLE`, `closing` to `CLOSING`.
- Currency fields are integer U.S. dollars with no commas or symbols.
- Percent fields are percentage points, not fractions. Use the template precision, usually two decimals.
- Dates are `YYYY-MM-DD`; month fields are integers.
- Use booleans as JSON `true`/`false`. Use `null` only where the template allows it; otherwise use the appropriate enum, empty list, or explicit status.
- Sort every list as instructed. Common sort keys are `issue_id`, `term_id`, `seller_id`, `seller_name`, `contract_name`, source doc ID, and alphabetical code lists.
- For issue registers, include each material issue once. Omit non-issues when instructed. In `corrected_value`, include only fields relevant to that issue.
- `source_ids` and source doc fields are audit IDs only, not prose evidence memos.

## Calculations And Checks

- Always respect the clause `calculation_base` and policy rule base: headline value, equity value, full uncapped value, revenue concentration, or another stated base.
- Consideration check: `cash_at_close + seller_note + rollover_equity + earnout` should equal the stated total/headline consideration unless the deal record explicitly says otherwise.
- Seller proceeds: use the active cap table or active allocation schedule. Allocate each requested consideration component by ownership percentage when no component-specific allocation is provided; round to whole dollars and reconcile totals.
- Per-share price is calculable only if the active cap/allocation source supplies share count. Otherwise use the template's null/no-share-count convention.
- Price per 1.00 ownership percentage point is `applicable value / 100`, rounded as required.
- Escrow, cap, basket, reverse fee, and break fee dollars are `base_value * percent / 100`, rounded to integer dollars.
- Aggregate escrow is general plus tax escrow when the schema asks for it. Tax escrow is tracked separately from general indemnity escrow unless the template says otherwise.
- Working capital collar percent is `collar / equity_value * 100` when the schema asks for percent of equity value.
- Deadline calculations use calendar days from signing date to outside/closing deadline.
- Policy deviation percent is `draft_percent - threshold_percent`; policy excess dollars are `positive deviation_percent * base / 100`.
- Aggregate risk totals should sum only quantified dollar exposure/excess fields included in the answer. Do not add non-quantified legal risk.
- For HSR/regulatory outputs, rely on the active regulatory or counsel memo/status. Do not infer solely from deal size when the environment supplies a memo, override, or missing-memo status.

## Common Exclusions

- Exclude `STALE`, `TEMPLATE`, and generic standard-form records from controlling analysis unless the requested schema asks for superseded IDs or override codes.
- Exclude stale cap tables when an active cap table/allocation schedule exists.
- Exclude stale duplicate clause rows with the same clause code when an active row exists.
- Exclude unrelated deal records returned from index, policy, or search pages.
- Exclude benchmarks with mismatched topic/industry/definition, obvious distractor notes, or stale years unless the prompt asks to discuss them.
- Do not include narrative memo text, Markdown, citations outside JSON, comments, or explanatory prose when the prompt asks for JSON only.
- Do not invent missing facts. Use allowed `null`, empty arrays, or controlled `UNCLEAR`/`COUNSEL_MEMO_MISSING`/`NOT_APPLICABLE` style enums when supported.

## Task Patterns

- First-draft/term-population packages: collect deal profile, active term sheet/current instructions, economics, active cap/allocation schedule, financial schedule, material contracts/regulatory status, disclosure/transition schedules, and policy checks. Drafting positions should follow active facts plus latest client instructions.
- Seller-side counterparty paper review: compare active counterparty draft and active clause rows against latest client instructions and seller APA playbook. Quantify corrected economic values, pick approval owner/action from policy, and list only material deviations.
- Committee escalation packages: include only terms requiring committee routing or recommendation. Use active committee records for member names, active clause and policy IDs for source fields, and benchmarks only where the schema requests benchmark metadata.
- Transition-term packages: derive employee transfer, TSA/service continuity, restrictive covenant, IP transition, escrow, and deadline flags from the active draft, disclosure schedules, latest instructions, and playbook. Sort priority issues and code lists exactly as required.

## Final Validation

- Validate JSON syntax with `jq` before final output.
- Recheck top-level keys and every enum against `answer_template.json`.
- Recompute all dollar and percent fields after rounding; verify totals and issue counts.
- Confirm no stale/template source was used as controlling authority.
- Return exactly one JSON object and nothing else when requested.
