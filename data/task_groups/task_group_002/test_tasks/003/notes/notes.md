# test_003 Hidden Notes

## English

### Data lineage and task definition

This task belongs to `task_group_002`, scenario `SCN_002_crm_b2b_quote_account_response`, and uses the milestone engagement response family. It targets opportunity `OPP-TE-POLARIS` for customer `CUST-POLARIS` / Polaris Cold Chain and is a test analogue to the training milestone reconciliation tasks. The solver-visible files are English-only; this notes file is bilingual as requested.

The task uses the shared MedBridge Sales Ops API described in `task_factory/scratch/env_blueprint.md`. The prompt asks the solver to use the runner-provided `API_BASE_URL` and reconcile opportunity, invoice, payment, revenue journal, event, and voucher records. It also gives controller-confirmed review facts for the Polaris account contact and overdue phase-2 due date so the test remains aligned to the task-builder assignment.

### Scenario fit and material map

This is a CRM/account-management reconciliation workflow, not a quote calculation. The expected work is to confirm the won opportunity value, tie the value to two phased invoices, distinguish paid/recognized phase 1 from unpaid/overdue phase 2, verify revenue recognition only for paid milestones, and create CRM follow-up work for collection and event invitation.

Relevant shared API entry points include `/api/opportunities`, `/api/customers`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, `/api/vouchers`, `/api/policies`, and `/api/search?q=Polaris`. `input/prompt.txt` provides the realistic account request and review overrides. `input/payloads/answer_template.json` defines the exact output shape, stable IDs, controlled enums, and money/date formats. `output/answer.json` is the canonical answer. `eval/eval.py` implements eight weighted exact-match scoring points, and `eval/eval.sh` is the entry point that accepts an optional candidate path.

### Solution and evaluation basis

Canonical facts: opportunity `OPP-TE-POLARIS` belongs to `CUST-POLARIS` / Polaris Cold Chain, is stage `WON`, and has won amount `120000.00`. Phase `POL-P1` / invoice `INV-POLARIS-P1` totals `62000.00`, is paid, has `62000.00` paid and `0.00` unpaid, is not overdue, and is recognized. Phase `POL-P2` / invoice `INV-POLARIS-P2` totals `58000.00`, is unpaid, has `0.00` paid and `58000.00` unpaid, is overdue as of `2026-06-01`, and has due date `2026-05-20`. The outstanding balance is `58000.00`, and the milestone total matches the won amount.

Revenue recognition status is `COMPLETE_FOR_PAID_MILESTONES`; recognized milestones are `["MS1"]` using the reporting label; there are no missing required recognized milestones; recognized amount is `62000.00`. The event is `EVT-POLARIS-GALA`, event date `2026-06-18`, status `LIVE`, voucher `POLARIS100VIP`, discount `100.00`, and max uses `3`.

The collection follow-up task is type `COLLECTION`, action `ESCALATE_COLLECTION`, linked to customer `CUST-POLARIS`, opportunity `OPP-TE-POLARIS`, contact Amara Singh, milestone `POL-P2`, amount due `58000.00`, and due date `2026-06-01`. The invitation follow-up task is type `EVENT_INVITATION`, action `SEND_EVENT_INVITATION`, linked to the same customer/opportunity/contact, event `EVT-POLARIS-GALA`, voucher `POLARIS100VIP`, and due date `2026-06-10`.

Scoring points and raw weights: opportunity/account identity (1), reporting milestone labels with source phase IDs and phase totals (3), payment/outstanding balance (2), paid-milestone due-date nulling and collection convention (10), revenue recognition state (3), event/voucher action (2), CRM follow-up actions and due dates (2), and contact linkage (1). The evaluator normalizes by total raw weight `24`, compares currency at cent precision, normalizes enum casing, and requires stable IDs for milestones, source phases, invoices, event, voucher, customer, and opportunity.

Likely pitfalls include using stale account metadata instead of Amara Singh, using an unconfirmed phase-2 due date, treating the won opportunity as fully settled, recognizing revenue for the unpaid milestone, missing the escalation action, or omitting the event/voucher from the invitation follow-up.

### Transfer design

This test checks whether solvers transfer milestone engagement conventions from the train tasks: opportunity value should equal milestone invoice totals; unpaid overdue milestones drive collection escalation; paid completed milestones require revenue recognition verification; unpaid milestones should not be recognized yet; event and voucher facts should become CRM invitation work; and follow-up tasks must be linked to customer, opportunity, contact, and stable business records.

### Construction record

Author: Codex main agent. Created: 2026-06-01. Updated: 2026-06-01. Major changes: created the `test_003` prompt, answer template, canonical answer, notes, and exact-match evaluator within the assigned write scope.

