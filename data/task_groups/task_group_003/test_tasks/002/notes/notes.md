# test_002 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by `train_002` and `train_005`. The visible input is `case_queue.json`; the support-console API contains cases, customer lines, devices, plans, and bills.

Task definition: The solver triages five mobile support cases and returns action enums, final routes, reason codes, and refuel charge fields when a plan-limit case requires them.

Scenario fit: The task models CRM contact-center support across no-service, MMS, slow-data, and roaming issues, preserving the policy-driven branch selection from the source telecom example.

Material map: `/api/cases/<id>` links case IDs to line and device records. `/api/lines/<id>` reveals suspension/contract/roaming state. `/api/devices/<id>` reveals SIM, APN/MMSC, data saver, and phone roaming state.

Solution and evaluation basis: The queue includes unresolvable policy cases, MMS/APN recovery, plan-usage recovery, and carrier-side roaming recovery. There are 10 scoring points focused on business actions, route counts, refuel calculation, source-family classification, target evidence sets, and low-weight inventory/line/device consistency audits.

Transfer design: The main transfer points come from `train_002` and `train_005`: use line, device, bill, and plan records as source of truth; separate device-configuration, carrier-line, plan-allowance/data-recovery, billing-recovery, and human-handoff source families; calculate refuel amounts/prices from the plan. The target queue adds new state combinations, so the solver must inspect current evidence rather than apply memorized codes.

Construction record: Created by Codex on 2026-06-01. Major change: initial test task construction for `task_group_003`.

