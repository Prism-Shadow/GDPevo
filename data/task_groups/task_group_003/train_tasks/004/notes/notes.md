# train_004 Notes

## English

Data lineage: This task is based on `SCN_003_crm_service_ticket_resolution` and combines source examples `E001` and `E002`. The visible payload is a seven-ticket queue snapshot; support-console API records supply account, outage, diagnostics, and troubleshooting evidence.

Task definition: The solver must classify each queue ticket by final status, route team, key blocker, and diagnostic requirement, then produce queue counts.

Scenario fit: This is CRM service-queue quality control. It uses the same lifecycle as offline resolution but emphasizes mixed-case routing and aggregate handoff counts.

Material map: `queue_snapshot.csv` lists target tickets. The relevant API endpoints are `/api/tickets/<id>`, `/api/accounts/<id>`, `/api/outages?service_area=...`, `/api/diagnostics/<id>`, and `/api/troubleshooting/<id>`.

Solution and evaluation basis: The queue includes one outage hold, one resolved voice profile refresh, three failed tickets, one network engineering escalation, and one tier-2 provisioning escalation. There are 9 exact-match scoring points.

Transfer design: As a train task, it reinforces status vocabulary, account/authentication failure gates, outage handling, escalation team mapping, and rollup conventions that later test tasks reuse.
