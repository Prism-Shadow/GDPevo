---
name: wealth-advisory-json
description: Solve private-wealth advisory tasks that require querying the harness advisory API and returning one JSON object for client planning memos, especially Roth conversion and RMD summaries, ILIT Crummey funding checks, GRAT versus CRAT comparisons, and estate liquidity plans. Use this whenever the prompt mentions a client ID, `API_BASE`, source documents, custodian exports, tax policy constants, RMD factors, or an answer template for a structured advisory memo.
---

# Wealth Advisory JSON

Use this skill for the staged advisory bundle. The job is to find the controlling facts, compute the requested values, and return the exact JSON object the template asks for. Do not write prose outside the JSON.

## Workflow

1. Read the prompt, request memo, and answer template together. Treat the template as the schema contract.
2. Query `API_BASE` for the client record and the relevant advisory tables:
   - `/api/clients/{client_id}`
   - `/api/source-documents`
   - `/api/retirement-accounts`
   - `/api/life-insurance`
   - `/api/trust-candidates`
   - `/api/policies/tax`
   - `/api/rmd-factors`
   - `/portal/client/{client_id}` when a readable summary helps resolve a conflict
3. Resolve conflicting records by source quality, not by recency alone.
4. Compute every requested field from the controlling sources.
5. Assemble one JSON object only.
6. Check the output against the template one last time: required keys present, enums exact, money rounded to cents, dates ISO, no prose.

## Source Resolution

When the template asks for `source_resolution`, point each field at the source that actually controlled that domain. Do not collapse different domains into one winner if the template separates them.

- Prefer `SIGNED_PROFILE` for client intent, beneficiaries, and personal planning inputs.
- Prefer `ATTORNEY_MEMO` for legal structure, goals, and asset-transfer intent when it is the controlling document.
- Prefer `CUSTODIAN_EXPORT` for balances, holdings, account metadata, and other book-of-record data.
- Prefer `CRM_NOTE` only when no signed profile, attorney memo, or custodian export settles the question.
- Treat `STALE_MARKETING_INTAKE` as the weakest source and use it only when nothing better exists.

Do not average conflicting records unless the task explicitly asks for reconciliation. Pick the controlling source and continue.

## Domain Patterns

### Roth conversion / RMD

- Use retirement-account balances, tax-policy tables, and RMD factors to project the requested horizon.
- Prefer `STAGED_ROTH_CONVERSION` when there is pre-RMD room to move income into better brackets and the projected tax savings justify the conversion tax.
- Use `DEFER` or `NO_CONVERSION` when the RMD window is too short, liquidity is tight, or the conversion worsens the tax picture.
- Keep the conversion schedule, RMD comparison, and legacy projection on the same timeline.
- Keep the recommendation aligned with the risk flag: tax-bracket management for planned conversions, liquidity constraint when cash flow is tight, and RMD near term when the window is too short.

### ILIT Crummey funding

- Use the beneficiary count and annual exclusion figures to compute funding capacity and the premium gap.
- Derive notice and withdrawal dates from the policy or memo. Do not invent a generic schedule if the environment already gives one.
- Use the low-risk formalities path when the premium fits and the paperwork supports it.
- Tie the estate result to whether the policy is implemented cleanly.

### GRAT versus CRAT

- Use the client goal and asset facts to decide between transfer to heirs and philanthropy.
- Pick `GRAT` when transfer is primary and estate-tax reduction matters.
- Pick `CRAT` when the charitable remainder is the point or the transfer fit is weak.
- Preserve extra context fields such as planning year, exemption used, or liquid assets when the memo or template makes them explicit.

### Estate liquidity action plan

- Combine insurance and transfer planning when both liquidity and estate reduction matter.
- Sort `action_set` alphabetically exactly as requested.
- Sequence the steps so the funding or legal prerequisite comes first, then the trust decision.
- Keep the output factual and narrow: liquidity gap, outside-estate value, trust comparison fields, and the action set are the center of gravity.

## Field Discipline

- Match field names exactly, including nested paths.
- Use JSON numbers for money and counts.
- Round currency to cents.
- Use ISO `YYYY-MM-DD` for dates.
- Keep `task_id` and `client_id` verbatim from the prompt or memo.
- If the template includes extra factual context fields beyond the required top-level keys, preserve them when they are supported by the memo or API data.
- Return a single JSON object only. No markdown fences, commentary, or explanations.
