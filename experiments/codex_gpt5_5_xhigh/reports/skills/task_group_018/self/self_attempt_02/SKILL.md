# ClerkOps Packet Reconciliation

Use this skill for Clerk Operations tasks that combine a local court packet with the shared API. The usual deliverable is a single JSON object matching `input/payloads/answer_template.json`.

## Core Workflow

1. Read the prompt, local packet, and answer template first. Extract the required top-level keys, row ordering, enum values, date/currency precision, null rules, and aggregate fields before doing calculations.
2. Identify the target records from the packet. Include only records the prompt asks for: skip stale-export lookalikes, name-similar records, informational rows, and `review_needed: false` items unless the template explicitly asks for them.
3. Query the live API for every target record:
   - `GET /api/cases/<case_number>` for live identity, matter type, status, charges, representation, sentence, restitution, and tags.
   - `GET /api/citations/<citation_number>` for traffic identity, live citation plan fields, and violation details. If no case number exists, use the citation number as the account reference.
   - `GET /api/financial-obligations?case_number=<id>` for live principal, fee components, restitution, amount paid, balance, and plan state.
   - `GET /api/docket?case_number=<id>` for live docket history.
   - `GET /api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>` for authoritative fee rows.
   - `GET /api/payment-policies?county=<county>` for installment policy, unknown placeholders, and unsupported charge/fee codes.
   - `GET /api/stale-exports?county=<county>&name=<export>` only as a conflict warning, not as authority.
   - Use `/api/search?q=<text>` or `/api/hearings?...` only to locate ambiguous records.
4. Reconcile each row, then recompute aggregates from your final rows. Do not copy aggregate hints from stale exports or draft imports.

## Source Precedence

The answer template controls schema, enum spelling, sort order, precision, and whether unknown values are `null` or a placeholder.

Current bench minutes, hearing notes, judge orders, counsel confirmations, and review packets control new plea, disposition, sentence, recall, probation, license, service, petition, and counsel outcomes for the event being processed.

The live API controls stable identity, current ledger credits/balances, docket history, fee schedules, payment policies, and existing approved plan dates or amounts.

Stale exports, old worklists, draft finance imports, queue snapshots, and candidate workpaper codes are conflict signals only. Never let them override live records or the current packet.

For just-held hearings, the live case may still show `pending`, `open`, or `warrant`; use the current packet to resolve the outcome, while using live data for identity and existing ledger context.

## Fees And Financials

Always select fee rows with the county, matter type, and the relevant order/disposition date. Do not use today’s fee row for an old order, and do not use an obsolete row for a new order.

Apply mandatory fee rows when their `applies_when` trigger is satisfied. Apply optional rows only when the order supports them, such as probation ordered, restitution ordered, treatment ordered, traffic school elected, late fee ordered, or speed over limit. Exclude candidate codes that are unsupported by policy, not active on the effective date, or not ordered.

Recompute corrected principal from approved fee components plus restitution when restitution belongs in principal. If the template has a separate restitution field, keep it separate there; if it only has `fee_components`, include a `RESTITUTION` component only when the packet/schema convention supports it.

Use live `amount_paid` as the ledger credit unless the packet includes a receipt or cashier log that is explicitly not on the live ledger. Corrected balance is normally corrected principal minus recognized credits. Missing financial obligations mean current live principal/balance is `0.00` when the template says so; do not drop the case.

For financial deltas, follow the template sign convention. Marion-style `financial_delta` is `corrected_assessment_total - current_ledger_principal`. Wasco-style `correction_amount` is positive when it reduces the live balance.

## Payment Plans

Read the county policy before building any plan. Use approved packet or live monthly amounts when the notes say they were approved; otherwise use the requested amount clamped to policy minimum/maximum, or the policy minimum when the judge approved the lowest allowed amount.

Use the live first due date when the packet says an existing approved plan date is already recorded. Otherwise set first due date from the order/review date plus `first_due_days_after_order`.

Calculate installments from the plan basis named by the template, usually original principal or current corrected balance. When smaller final payments are allowed, use full monthly installments plus one smaller final installment for any remainder. When no plan applies, use the template’s null/zero convention.

Final due dates advance in monthly installments from the first due date, not from packet creation date.

## Output Conventions

Return only the completed JSON object. No Markdown, comments, explanations, or extra keys.

Use exact enum values from the template. Do not invent statuses such as `satisfied` if the template only allows `paid`, `closed`, `current`, and similar controlled values.

Use ISO `YYYY-MM-DD` dates and `HH:MM` times. Currency values are JSON numbers rounded to two decimals; count, month, and installment fields are integers. Community service remaining hours may require one decimal.

Sort rows exactly as directed: commonly by `case_number` or `citation_number` ascending; charges by `charge_id`; fee codes and excluded codes alphabetically unless the template says to preserve application order.

For Gloucester-style missing identity fields, use the payment policy/template placeholder, usually `TBD from case file`, instead of guessing driver license, phone, or probation officer data.

## Common Field Choices

Discrepancy and conflict fields should describe the actual conflict source: attorney mismatch, status/warrant conflict, financial schedule/import conflict, combined conflicts, identity/lookalike conflict, live ledger versus packet receipt, petition changing a payment plan, or packet service shortfall.

Docket actions should be based on what still needs entry: plea/disposition, sentence, warrant recall, attorney update, financial replacement/adjustment, supervisor review, return-to-court notice, plan approval, post-credit close, or community-service follow-up.

For compliance packets, include only records requiring review. Community service status comes from ordered hours versus provider-verified completed hours; restitution status comes from live restitution plus trust/disbursement notices; payment plan action comes from live status plus any approved or withdrawn ability-to-pay petition.

## Pitfalls

Do not merge nearby citation numbers, similar names, or same-county stale export records into the target packet.

Do not assume candidate fee codes are assessed. Examples of common false candidates are unsupported charge codes, late fees not ordered now, traffic school fees when school was not elected, and public-defender quick-pick rows not in the active schedule.

Do not trust draft import totals, stale principal hints, stale counsel type, or old status rosters when live API and current packet disagree.

Do not use filing date, packet date, or current date as the fee effective date unless the prompt/template specifically says to; most tasks use the disposition/order/review date.

Do not forget to recompute batch totals, mismatch lists, included-case counts, plan counts, final-payment totals, and aggregate balances from the final emitted rows.
