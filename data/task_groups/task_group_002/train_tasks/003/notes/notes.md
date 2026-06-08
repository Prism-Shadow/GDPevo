# train_003 Hidden Notes

## English

### Data lineage and task definition

This task belongs to `task_group_002`, scenario `SCN_002_crm_b2b_quote_account_response`, and is anchored most directly in source example `E003` plus the milestone engagement response family described in `task_factory/scratch/task_group_design.md`. It uses the shared MedBridge Sales Ops API described in `task_factory/scratch/env_blueprint.md`; no task-local business data payload is provided other than `input/payloads/answer_template.json`.

The solver-visible prompt asks for an account-ready reconciliation for Helios Health Alliance using opportunity `OPP-TR-HELIOS`, customer `CUST-HELIOS`, and contact Mara Okafor. The expected work is to pull CRM opportunity/customer/contact records, invoice and payment records, revenue journal records, event records, and voucher records from the shared API, then return the structured JSON required by the template.

### Scenario fit and material map

This is a CRM/account-management reconciliation workflow rather than a quote calculation. It connects the won opportunity, phased milestone invoices, payment state, revenue recognition, and customer engagement event into account follow-up tasks. The relevant shared API entry points are `/api/opportunities`, `/api/customers`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, `/api/vouchers`, `/api/policies`, and `/api/search?q=Helios`.

`input/prompt.txt` provides the realistic account request and target IDs without exposing the final amounts or task due dates. `input/payloads/answer_template.json` defines the exact output shape, money precision, dates, stable IDs, and controlled enum values. `output/answer.json` records the canonical reconciliation. `eval/eval.py` implements exact-match scoring for the eight business results; `eval/eval.sh` is the entry point and accepts an optional candidate path.

### Solution and evaluation basis

Canonical facts: opportunity `OPP-TR-HELIOS` for customer `CUST-HELIOS` / Helios Health Alliance is stage `WON` with amount `120000.00`. Milestone `MS1` totals `50000.00`, is paid, has `50000.00` paid and `0.00` unpaid, and has revenue recognized. Milestone `MS2` totals `70000.00`, is unpaid, has due date `2026-07-10`, and creates the outstanding balance of `70000.00`. Revenue recognition status is `COMPLETE_FOR_PAID_MILESTONES`, recognized milestones are `["MS1"]`, missing required milestones are empty, and recognized amount is `50000.00`.

The event facts are `EVT-HELIOS-CELEBRATION` on `2026-07-22`, voucher `HELIOSVIP100`, discount value `100.00`, and max uses `4`. The collection follow-up task is due `2026-07-10`, tied to `MS2`, amount due `70000.00`, contact Mara Okafor, customer `CUST-HELIOS`, opportunity `OPP-TR-HELIOS`, and action `COLLECT_UNPAID_MILESTONE`. The invitation follow-up task is due `2026-07-01`, tied to the same customer/opportunity/contact plus the event and voucher, and action `SEND_EVENT_INVITATION`.

Scoring points and raw weights: CRM opportunity total/stage (2), milestone invoice totals (2), paid/unpaid balance (3), revenue recognition entry status (2), event/voucher facts (2), collection task fields (2), invite task fields (1), contact linkage (1). The evaluator normalizes by total raw weight `15`. Currency comparisons are cent-tolerant. Lists are normalized by stable IDs where applicable. Free-form wording is not scored except controlled task titles are present but not required by the evaluator.

Likely pitfalls include treating the won opportunity as complete and missing the unpaid second milestone, recognizing revenue for an unpaid milestone, summing only paid invoices instead of all milestone invoices, omitting the event/voucher from CRM tasks, or linking the task to the customer but not the opportunity/contact.

### Transfer design

As a train task, this should teach reusable conventions for the milestone engagement family: opportunity value should match the sum of milestone invoice totals; collection work follows unpaid or due milestones, not paid milestones; revenue recognition is separate from payment receipt and applies to completed paid milestones; customer engagement events and vouchers must feed CRM invitation tasks; and account follow-ups need stable linkage to customer, opportunity, and contact. These conventions transfer to later milestone reconciliation test tasks without making them simple copies, because those tasks vary phase counts, overdue states, missing journals, and event/voucher conditions.

### Construction record

Author: Codex main agent. Created: 2026-06-01. Updated: 2026-06-01. Major changes: created the train_003 prompt, answer template, canonical answer, notes, and exact-match evaluator within the assigned write scope.

