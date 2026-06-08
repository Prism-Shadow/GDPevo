# train_003 Notes

## English

Data lineage: This task is derived from `SCN_003_crm_service_ticket_resolution`, especially enterprise escalation example `E003`. The visible files are the Asteri complaint email, response requirements, and answer template. The shared API supplies enterprise accounts, incidents, export runs, internal messages, and SLA contracts.

Task definition: The solver must prepare structured response-package fields for `INC-7301`: root cause, contributing alert issue, failed export window, backfill scope, SLA credit, owners, artifact names, permissions, and response status.

Scenario fit: This mirrors an enterprise client complaint workflow where support must connect technical failure evidence with account/SLA obligations and internal response artifacts.

Material map: `/api/enterprise/incidents/INC-7301` identifies the incident. `/api/enterprise/export-runs?incident_id=INC-7301` gives failed run dates. `/api/enterprise/messages?query=Asteri` and `/api/enterprise/sla/ENT-3001` provide root cause, alert issue, owners, and credit terms.

Solution and evaluation basis: The root cause is stale credentials after rotation, with archived alert routing as a contributing issue. The failed window is 2026-05-12 to 2026-05-14, with 3 backfill days and a 15 percent SLA credit. There are 8 exact-match scoring points.

Transfer design: As a train task, it teaches by comparison how enterprise service complaints should combine export run evidence, message evidence, SLA terms, owner mapping, artifact naming, and differentiated sharing permissions.

Construction record: Created by Codex on 2026-06-01. Major change: initial task construction for `task_group_003`.

