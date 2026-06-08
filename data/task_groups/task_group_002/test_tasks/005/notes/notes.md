# test_005 Notes

## English

This task belongs to source scenario `SCN_002_crm_b2b_quote_account_response` and the milestone engagement-response family in `task_group_002`. It is the fifth test task and asks solvers to audit a multi-phase NGO portal rollout using the shared MedBridge Sales Ops API plus the task-local account handoff. Solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`; the expected response is `output/answer.json`.

The business case is opportunity `OPP-TE-SUNRISE` for `CUST-SUNRISE` / Sunrise Relief Network, with Priya Raman as the routing contact for this audit. The opportunity is won for USD 120,000.00 and must equal the sum of three phases: `MS1` USD 40,000.00, `MS2` USD 35,000.00, and `MS3` USD 45,000.00. `MS1` is paid and recognized, `MS2` is paid but missing its revenue journal, and `MS3` is unpaid, not yet due on 2026-06-01, and due on 2026-07-01. The total paid amount is USD 75,000.00 and the outstanding balance is USD 45,000.00.

The required primary accounting action is `RECORD_REVENUE_MS2`, due on 2026-06-01, for USD 35,000.00. It should debit `DEFERRED_REVENUE` and credit `IMPLEMENTATION_SERVICES_REVENUE`. The collection action for `MS3` is `MONITOR_UNPAID_NOT_DUE`, not an overdue collection notice. The training event is `EVT-SUNRISE-TRAINING`, live on 2026-06-20, and voucher `SUNRISESTAFF100` has discount 100 and 25 maximum uses. The training invite task is due on 2026-06-10 and must link the customer, opportunity, contact, event, and voucher.

The evaluator has twelve scoring points with the requested raw weights: phase sum and opportunity total (2), paid/unpaid invoice state (3), missing revenue-recognition action (3), outstanding balance (2), training event/voucher facts (2), CRM follow-up task routing (2), collection versus accounting action enum (2), four reconciliation control conventions (3 each), and contact linkage (1). Currency is compared at cent precision. Enums and IDs are normalized for casing and whitespace, but the expected business decisions are exact.

Likely pitfalls include treating the paid `MS2` invoice as fully reconciled even though revenue recognition is missing, issuing a collection notice for `MS3` before it is due, omitting the 2026-06-10 training invite due date, confusing the accounting action with the collection action, or failing to carry Priya Raman through all CRM-linked tasks.

Construction record: authored by Codex on 2026-06-01 for task-builder assignment `test_005`. Initial construction created the prompt, answer template, standard answer, evaluator, and notes under the assigned write scope.

