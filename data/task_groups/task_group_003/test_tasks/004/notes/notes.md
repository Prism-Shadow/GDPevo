# test_004 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by `train_001`, `train_003`, and `train_004`. The visible payload lists service tickets and enterprise incidents for an executive priority board.

Task definition: The solver must rank the three highest-risk accounts, list enterprise credit-review accounts, notify owners, and summarize service and enterprise queue states.

Scenario fit: The task is a CRM executive escalation board. It combines service-ticket final states, escalation teams, enterprise severity, SLA credit exposure, and owner coordination.

Material map: `escalation_board_request.json` lists candidate records. `/api/tickets/<id>`, `/api/diagnostics/<id>`, and `/api/troubleshooting/<id>` support ticket status reconstruction. `/api/enterprise/incidents/<id>`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, and `/api/enterprise/sla/<id>` support incident risk and credit review.

Solution and evaluation basis: The highest-risk records combine current critical enterprise credit exposure and unresolved service escalations according to the visible score policy. The evaluator has 6 exact-match points over ranking, the visible score policy, credit review, owner notifications, summaries, and candidate/environment audits.

Transfer design: This test requires transfer across families. Service status and team mapping come from `train_001`/`train_004`; enterprise SLA-credit and owner conventions come from `train_003`. The ranking output is new, so task-specific aggregation is still required.
