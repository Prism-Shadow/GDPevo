# test_003 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by `train_003`. The visible files are the Quanta complaint email, response requirements, and answer template. The shared API provides incidents, export runs, messages, enterprise accounts, and SLA contracts.

Task definition: The solver must produce a structured enterprise response package for the target incident, including root cause, failed export window, backfill days, SLA credit, owner assignments, artifact names, share permissions, and response status.

Scenario fit: This is an enterprise CRM complaint investigation task. It combines technical export evidence with SLA and account-management response duties, matching the source example's end-to-end complaint closure.

Material map: `/api/enterprise/incidents/<id>` identifies the incident. `/api/enterprise/export-runs?incident_id=<id>` gives failure dates. `/api/enterprise/messages` and `/api/enterprise/sla/<enterprise_account_id>` provide root-cause context and credit terms.

Solution and evaluation basis: The expected response is derived from failed export runs, internal messages, the enterprise account record, and the SLA contract. There are 7 scoring points focused on the response package, export-run/message evidence, and enterprise consistency audits.

Transfer design: This task transfers response-package conventions from `train_003`: synthesize export runs, messages, and SLA terms; produce channel/folder/report names; assign owners and permissions. The client, root cause, failure length, and credit percent change.
