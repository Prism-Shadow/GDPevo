# test_005 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by all five train tasks. The visible payload lists proposed CRM updates across service tickets, contact-center cases, and enterprise incidents.

Task definition: The solver audits each proposed update, accepts correct ones, corrects wrong statuses, actions, teams, refuel amounts, or credit percentages using structured reason codes, and fills QA evidence/package-review fields required by the template.

Scenario fit: QA review is a realistic CRM operations workflow: support leaders often check proposed case updates before they affect customer communications, escalation queues, or SLA credits.

Material map: `proposed_updates.json` lists candidate changes. Service ticket evidence comes from `/api/tickets`, `/api/outages`, `/api/diagnostics`, and `/api/troubleshooting`. Contact-case evidence comes from `/api/cases`, `/api/lines`, and `/api/devices`. Enterprise evidence comes from `/api/enterprise/incidents`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, and `/api/enterprise/sla`.

Solution and evaluation basis: The proposal set covers service gates, escalation-team corrections, mobile-device and plan-usage corrections, enterprise credit review, and authentication failure. There are 10 exact-match scoring points focused on business accept/reject decisions, corrected fields, defect breakdown, target service metrics, contact refuel evidence, enterprise credit evidence, and package-review permissions.

Transfer design: This task requires broad transfer. The solver must apply offline ticket status and metric rules from `train_001`/`train_004`, mobile action and refuel rules from `train_002`/`train_005`, and enterprise SLA-credit plus response-package conventions from `train_003`. The audit form and mixed proposal set are task-specific.
