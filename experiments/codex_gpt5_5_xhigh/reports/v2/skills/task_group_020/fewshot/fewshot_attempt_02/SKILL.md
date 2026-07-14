---
name: aster-deal-desk-ma-sop
description: Use for Aster Legal Deal Desk M&A transaction contract review and negotiation tasks.
---

# Aster Deal Desk M&A SOP

Use the shared Aster Legal Deal Desk web/API service named in the task. Do not use local environment source files or unrelated deal data.

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Treat the prompt as the task objective and the template as the output contract.
2. Identify the requested `deal_id`, client side, transaction structure, requested review mode, and required top-level JSON keys.
3. Query the Deal Desk service, replacing `<TASK_ENV_BASE_URL>` with the URL from the task/environment access note.
4. Build a source map before drafting: deal profile, active documents, latest client instructions, active draft/counterparty paper, policy/playbook, clause comparison records, schedules, and any required benchmarks.
5. Populate or review only the requested deal. Ignore similarly named deals and all records for other deal IDs.
6. Calculate all economic fields independently, then tie them back to the template and sources before returning JSON.

Useful API habits:

```bash
BASE="<TASK_ENV_BASE_URL>"
DEAL="D-..."
curl -sS "$BASE/api/health"
curl -sS "$BASE/api/deals/$DEAL"
curl -sS "$BASE/api/clauses?deal_id=$DEAL"
curl -sS "$BASE/api/policies/$POLICY_ID"
curl -sS "$BASE/api/documents/$DOC_ID"
curl -sS "$BASE/api/benchmarks?industry=$INDUSTRY"
```

Prefer `GET /api/deals/{deal_id}` as the starting point; it commonly includes the deal profile, documents, clause records, benchmarks, policy-linked context, active/stale document lists, parties, economics, schedules, and record links. Use direct document, policy, clause, and benchmark endpoints to verify details. If an API route is missing, use the web pages and their "Raw ... JSON" panels.

Many document `sections[].text` values contain JSON strings. Parse those as structured data when they start with `{` or `[`, rather than relying on prose snippets.

## Source Precedence

Use this precedence unless the prompt or template says otherwise:

1. The answer template controls shape, allowed enum values, precision, nullability, and ordering.
2. The requested deal profile and active deal records control parties, dates, structure, headline/equity value, policy ID, industry, and status.
3. Active/current deal documents control over stale, template, imported, or older records.
4. Latest written client instructions and active client positions control over generic playbook language when they conflict.
5. Active cap table or active allocation schedule controls seller allocations over stale cap table exports.
6. Current client playbook/policy controls policy thresholds, approval owners, recommended positions, and escalation triggers.
7. Active clause comparison records identify draft/playbook deviations. Ignore stale/template clause records with the same label unless the task asks for superseded records or overrides.
8. Benchmarks support committee or market analysis only when relevant by topic, industry, year/currentness, and prompt. Do not let benchmarks override current policy or deal-specific instructions.
9. Counsel/regulatory memo or current regulatory status controls HSR and other approvals. If the memo is missing or unclear, use the template's unclear/escalation enum rather than inventing a conclusion.

Record override rationale only in fields designed for it, such as source IDs, override codes, policy checks, or risk memo override fields.

## Output Rules

- Return one valid JSON object only. Do not include markdown, prose, comments, citations outside JSON fields, or trailing text.
- Follow the requested shape, not the descriptive metadata in the template. Do not copy schema helper keys such as `response_rule`, `top_level_required_keys`, or `item_schema` unless the template explicitly requires them as output fields.
- Include required keys and only fields allowed by the template. Use exact enum spelling and casing.
- Use exact names and IDs from the Deal Desk for parties, sellers, employees, contracts, policies, clauses, documents, committees, and approvals.
- Use `null` for numeric fields that do not apply or cannot be calculated under the template; do not substitute `0` unless the value is actually zero.
- Omit non-issues in issue-register outputs unless the template explicitly asks for all checks or `NO_ISSUE` rows.
- Include concise source IDs for auditability when requested. If the template does not specify source ID ordering, prefer a practical evidence order: deal/client document IDs, clause IDs, policy IDs, then benchmark IDs.

## Normalization

- Currency fields: integer U.S. dollars, no commas or symbols.
- Percent fields: decimal percentage points, not fractions. Use `10.0` or `10.00` as the template precision requires, never `0.10` for 10%.
- Month fields: integer months.
- Date fields: `YYYY-MM-DD`.
- Boolean fields: true JSON booleans, not strings.
- Lists: apply the template ordering. Common patterns are issue IDs alphabetically, seller allocations by `seller_name` or `seller_id`, contracts by contract name, code lists alphabetically, source doc IDs ascending, and employees by displayed name.
- Seller IDs, when required but not supplied, should be stable uppercase snake case derived from the displayed seller name.

## Calculations And Checks

Pick the base from the template, policy, clause `calculation_base`, or field label:

- Escrow, indemnity cap, basket, de minimis thresholds, and many APA economics often use headline value.
- RTF, break fees, public-merger exposures, and committee packets may use equity value or the exposure basis stated in the template.
- Working-capital collar percent usually equals `collar / equity_value * 100` when the output asks for percent of equity value.
- Price per as-converted ownership point equals `headline_or_equity_value / 100`.
- Per-share price is calculable only when the active cap table provides a share count; otherwise use the template's no-share-count enum/null convention.

Allocation checks:

- Seller gross proceeds = ownership percent / 100 * applicable headline/equity value.
- If the template splits consideration, allocate each component by ownership percent and verify each seller's component sum equals total proceeds.
- Verify ownership percentages sum to 100.00, subject to displayed rounding.
- Tie seller allocation totals back to headline value or total consideration. Adjust only for rounding if necessary and keep the result consistent with the Deal Desk record.

Economic issue checks:

- Amount from percent = `base * percent / 100`, rounded to whole dollars.
- Deviation percent = draft percent minus policy threshold percent when the issue is "above threshold"; use the inverse only when the policy flags being below a minimum.
- Policy excess dollars = `base * deviation_percent / 100` when percentage-based. For uncapped or prohibited post-closing exposure, use the exposure basis the template provides.
- Aggregate exposure totals should sum the included quantified exposure fields and exclude `null` values.
- Aggregate issue counts and driver lists must match the issue rows actually included.

Timing checks:

- `deadline_days_after_signing` is calendar days from signing date to outside/draft closing date.
- Compare deadline length to the policy or client minimum before setting escalation flags.

Before final output, check:

- The JSON parses.
- All enum values are valid.
- Required lists are sorted as specified.
- Dollar and percent totals tie.
- HSR/consent/employment/TSA/IP/non-compete flags match both active deal facts and current policy.

## Review Modes

For buyer-side first-draft or term-population tasks:

- Populate the drafting-ready business terms from the active deal record, active term sheet, current draft instructions, active cap table/allocation schedule, financial schedule, material contracts, regulatory status, and policy.
- Include policy checks where requested, with `WITHIN_POLICY`, `APPROVAL_REQUIRED`, `OVERRIDE_APPLIED`, or conditional escalation statuses driven by current policy and client instructions.
- Treat active client instructions as a permitted override when the schema has override fields; identify superseded stale/template documents only in override fields.

For seller-side APA counterparty-paper review:

- Compare the active buyer/counterparty draft against current seller instructions and the seller APA playbook.
- Include each material deviation once, using the controlled issue ID and recommended action.
- Seller-side red flags commonly include financing/lender diligence conditions, inadequate buyer assumed-liability covenants, working-capital resets, broad restrictive covenants, excessive escrow or survival, employee transfer gaps, TSA/service continuity gaps, retained IP/trademark issues, missing material-consent treatment, and closing deadlines that do not fit transition needs.

For committee escalation packets:

- Include terms requiring committee routing or recommendation, not every policy topic.
- Use committee records for member names and route. Use policy rules and clause IDs for source references.
- Quantify only where the Deal Desk supports a base and threshold. Use non-quantified legal risk where the issue is qualitative.
- Set aggregate risk tier, final action, primary drivers, exposure totals, and benchmark-memo flags from the included term rows and strategic context.

## Common Exclusions

- Do not use stale cap tables, stale clauses, old templates, imported generic provisions, or older benchmark samples when a current active source exists.
- Do not include non-material consents as closing conditions unless the active schedule/policy says they are required; keep post-closing notices separate when the template has a separate field.
- Do not invent HSR filing conditions when current regulatory analysis says thresholds are not met; use cooperation-only or no-condition enums when available.
- Do not include broad affiliate-wide or worldwide restrictive covenants if the policy requires a target/divested-business/product-and-territory scope.
- Do not include transition services, IP transition rights, founder employment agreements, or non-competes unless active schedules, draft terms, policy, or client instructions support them.
- Do not add narrative issue explanations when the schema asks for structured corrected values and source IDs only.
