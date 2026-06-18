# test_001 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by train tasks `train_001` and `train_004`. The visible payload lists five new offline service tickets; the support-console API supplies accounts, outages, diagnostics, and troubleshooting.

Task definition: The solver resolves a new service-ticket batch and returns per-ticket status, diagnostic flags, outage/escalation fields, and summary counts.

Scenario fit: The task is a formal CRM service-ticket resolution task, matching the source examples' account validation, outage analysis, diagnostics, troubleshooting, and escalation workflow.

Material map: `ticket_batch.csv` identifies tickets. `/api/tickets/<id>`, `/api/accounts/<id>`, `/api/outages?service_area=...`, `/api/diagnostics/<id>`, and `/api/troubleshooting/<id>` provide the needed evidence.

Solution and evaluation basis: The batch includes outage gating, authentication gating, successful troubleshooting, and two unresolved escalation families. There are 10 scoring points focused on ticket decisions, batch counts, target-scoped metric evidence, gate-skipped diagnostics, and root-cause escalation evidence.

Transfer design: High-value points depend on transfer from train: outage short-circuit and no diagnostics from `train_001`/`train_004`, diagnostics thresholds from `train_001`, and root-cause-to-team mapping from `train_004`. The new ticket IDs, service areas, and root causes require task-specific exploration.
