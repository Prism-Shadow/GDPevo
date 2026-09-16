# Support Console Map

## Discovery

Use `/api/search?q=...` when the prompt mentions a name, incident code, ticket code, customer, or symptom without an obvious direct endpoint.

## Endpoint Map

| Family | Endpoints | Use For |
| --- | --- | --- |
| Service tickets | `/api/tickets/<ticket_id>`, `/api/accounts/<account_id>`, `/api/outages`, `/api/diagnostics/<ticket_id>`, `/api/troubleshooting/<ticket_id>` | Match service area and service type, verify account state, compare diagnostics with post-troubleshooting results, and detect active outages. |
| Consumer cases | `/api/cases/<case_id>`, `/api/customers/<customer_id>`, `/api/lines/<line_id>`, `/api/devices/<device_id>`, `/api/bills/<bill_id>`, `/api/plans/<plan_id>` | Determine the next action, billing status, roaming state, device settings, and whether a carrier update is needed. |
| Enterprise export | `/api/enterprise/incidents/<incident_id>`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, `/api/enterprise/accounts/<enterprise_account_id>`, `/api/enterprise/sla/<enterprise_account_id>` | Identify the failed run window, root-cause category, owners, contract credit, and response artifacts. |

## Field Cues

- `tickets`: `service_area`, `service_type`, `issue_summary`, `subscribed_mbps`, `status`.
- `accounts`: `status`, `tier`, `service_area`, `authentication`.
- `outages`: `active`, `service_area`, `service_types`, `eta_hours`, `impact_score`.
- `diagnostics`: `root_causes`, `latency_ms`, `bandwidth_mbps`, `jitter_ms`.
- `troubleshooting`: `steps`, `post_latency_ms`, `post_bandwidth_mbps`, `post_jitter_ms`.
- `cases`: `issue_type`, `summary`, `line_id`, `device_id`, `customer_id`.
- `customers`: identity and status only; use for linkage, not actions.
- `lines`: `status`, `suspension_reason`, `roaming_enabled`, `plan_id`, `device_id`, `data_used_gb`.
- `devices`: `mobile_data_enabled`, `phone_roaming_enabled`, `data_saver_mode`, `network_mode_preference`, `vpn_connected`, `messaging_permissions`, `can_send_mms`, `sim_status`, `airplane_mode`, `signal_strength`.
- `bills`: `amount_due_usd`, `status`, `due_date`.
- `plans`: `monthly_price_usd`, `data_limit_gb`, `data_refueling_price_per_gb`.
- `enterprise_incidents`: incident identity, severity, status, owners, summary.
- `export_runs`: consecutive failed dates define the failure window; `failure_code` usually points at the root-cause category.
- `messages`: use for evidence text, artifact naming, and permission ordering when the prompt asks for them.
- `sla_contracts` and `enterprise/sla`: use for credit percentage and executive contact.

## Decision Rules

- Preserve the input row order unless the template says otherwise.
- Compute summary counts from the final rows.
- Use exact enum spellings from the active template, not from other task families.
- Set numeric outputs to the requested precision.
- Use `0`, `0.0`, or empty string only when the template allows a missing value.
- For refuel tasks, compute charge from the plan's refuel price per GB and the refuel amount.
- For enterprise exports, use the failed run dates plus message evidence to determine the incident window and backfill span.

