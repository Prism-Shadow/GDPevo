# train_001 Notes

## English

Data lineage: This task is derived from `SCN_003_crm_service_ticket_resolution`, mainly source example `E001`, with telecom escalation flavor from `E002`. The visible payload is `input/payloads/ticket_batch.csv`; the shared environment records are under the support-console API, especially tickets, accounts, outages, diagnostics, and troubleshooting records.

Task definition: The solver must resolve four offline service tickets. The expected JSON records the final status, whether diagnostics are needed, diagnostic issue flags, outage ID, escalation team, and a batch summary.

Scenario fit: This is a direct CRM service-ticket lifecycle task: account state and authentication gate the workflow, outages can hold the case, diagnostics and post-troubleshooting metrics decide resolved versus escalated outcomes.

Material map: `ticket_batch.csv` identifies the target tickets. `/api/tickets/<id>` gives ticket metadata, `/api/accounts/<id>` gives account and authentication state, `/api/outages?service_area=...` gives outage candidates, `/api/diagnostics/<id>` and `/api/troubleshooting/<id>` provide metric evidence.

Solution and evaluation basis: The answer uses outage `OUT-9102` for `TCK-5131`, diagnostic thresholds for `TCK-5107` and `TCK-5184`, and account ineligibility for `TCK-5202`. The evaluator has 8 exact-match scoring points with raw weights 1-3.

Transfer design: As a train task, it lets the agent infer the offline support status vocabulary, outage short-circuit convention, diagnostics thresholds, post-troubleshooting success rule, and field escalation mapping.
