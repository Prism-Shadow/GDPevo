## Skill: Support Console Operations

This skill covers how to resolve service-desk tasks using the shared support-console
API. It applies to roles such as ticket analyst, contact-center lead, enterprise
support lead, queue-quality analyst, and mobile-data recovery analyst.

### General workflow

1.  Read the prompt, the supplied payloads, and the answer template to understand
    what you are being asked to produce and which entities you must process.
2.  For every entity in the payload, query the support-console API to gather all
    relevant records — never guess from the customer-facing summary alone.
3.  Cross-reference the evidence from across endpoints (tickets, accounts,
    diagnostics, outages, troubleshooting, cases, customers, lines, devices, plans,
    bills, enterprise incidents, export runs, messages, SLA records) to reach a
    single conclusion per entity.
4.  Populate the answer template exactly in schema and payload order. Fill every
    required field; use empty strings, 0.0, or "NONE" / "NO_ACTION" when a field
    does not apply. Derive summary counts from the per-entity decisions.

### API reference

The shared console runs at the base URL provided in the prompt. All endpoints are
read-only GET; use the path variables exactly as shown.

| Endpoint | Returns |
|---|---|
| `/api/tickets/{ticket_id}` | service_area, service_type, subscribed_mbps |
| `/api/accounts/{account_id}` | account status, tier, auth success/failure |
| `/api/diagnostics/{ticket_id}` | bandwidth_mbps, latency_ms, jitter_ms, root_causes |
| `/api/troubleshooting/{ticket_id}` | steps taken, post-resolution metrics |
| `/api/outages` | list of active/inactive outages with service_area and service_types |
| `/api/cases/{case_id}` | customer_id, line_id, device_id, issue_type, location |
| `/api/customers/{customer_id}` | phone_number, status |
| `/api/lines/{line_id}` | plan_id, status, data_used_gb, roaming_enabled, suspension_reason |
| `/api/devices/{device_id}` | full device-state snapshot (see device-state guide below) |
| `/api/plans` | data_limit_gb, data_refueling_price_per_gb, monthly_price_usd |
| `/api/bills` | amount_due_usd, status (Paid / Overdue / Issued) |
| `/api/enterprise/incidents/{incident_id}` | enterprise_account_id, owners, severity, product |
| `/api/enterprise/accounts` | finance_owner, tier, name |
| `/api/enterprise/export-runs` | run_date, status, failure_code per incident |
| `/api/enterprise/messages` | channel, author, body (root-cause narratives and SLA terms) |
| `/api/enterprise/sla/{account_id}` | credit_percent, credit_trigger |
| `/api/contact-center/cases/{case_id}` | same shape as /api/cases (use /api/cases if 404) |

### Device-state fields and their implications

Always query the device for contact-center and mobile-data cases. The device
snapshot reveals the direct cause of many reported symptoms:

| Field | When it matters |
|---|---|
| `sim_status: "missing"` | No-service reports — reseat SIM |
| `mobile_data_enabled: false` | "No data after settings change" — toggle mobile data |
| `phone_roaming_enabled: false` | Traveler abroad with data failure — toggle roaming on device |
| `roaming_enabled: false` (on line) | Traveler abroad — enable line roaming (carrier update) |
| `data_saver_mode: true` | "Slow data with data-saver icon" — toggle data saver |
| `network_mode_preference: "3g_only"` | "Slow data on older network" — set 4G/5G preferred |
| `vpn_connected: true` | "Data works but slow" — disconnect VPN |
| `messaging_permissions.storage: false` | "Cannot send photos" — grant storage permission |
| `can_send_mms: false` | MMS failures — check mmsc_url + storage permission |
| `signal_strength: "none"` | No connectivity — check SIM, airplane mode, line suspension |

### Ticket decision rules

When classifying a ticket's resolution, check conditions in this order:

1.  **Account ineligible** — If `/api/accounts/{id}` returns 404 the account is
    invalid; mark FAILED / INVALID_ACCOUNT. If the account status is "Suspended"
    and suspension_reason is overdue, mark FAILED (or ESCALATED to
    ACCOUNTS_PAYABLE) / OVERDUE_SUSPENSION. If auth shows FAILURE, mark FAILED /
    AUTH_FAILED.
2.  **Active outage** — Check `/api/outages` for an active outage whose
    `service_area` and `service_types` match the ticket. If found, the ticket is
    PENDING_ACTION / OUTAGE_WAIT with the outage_id filled in.
3.  **Diagnostic root cause** — Query `/api/diagnostics/{ticket_id}`. Map the
    listed root causes to escalation teams and blockers:
    - `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS` — FIELD_OPS / PHYSICAL_LINE_FAULT
    - `BACKBONE_CAPACITY` — NETWORK_ENGINEERING / NETWORK_CAPACITY
    - `PROVISIONING_STALE`, `VOICE_PROFILE_STALE`, `CONFIGURATION_DRIFT` —
      TIER2_SUPPORT / PROVISIONING_STALE
4.  **Auto-troubleshooting outcome** — If `/api/troubleshooting/{ticket_id}`
    shows steps were applied and post-resolution metrics improved, the ticket may
    be RESOLVED via AUTO_TROUBLESHOOTING.

### Enterprise incident response

When preparing a structured response for an enterprise export complaint:

- Use `/api/enterprise/incidents/{incident_id}` for account linkage, severity, and
  owner assignments.
- Use `/api/enterprise/export-runs` filtered to the incident's
  `enterprise_account_id` to identify the consecutive failure window (start/end
  dates and count of failed days) and the failure code shared across them.
- Use `/api/enterprise/messages` filtered to the incident to find the root-cause
  narrative (engineering message), the SLA credit term (account-owner message),
  and the channel where the alert was posted.
- Use `/api/enterprise/sla/{account_id}` for the formal credit percentage.
- Use `/api/enterprise/accounts` for the finance owner and any additional
  permission users required by the response.
- Assemble channel, evidence folder, and report title following the naming
  conventions supplied in the response requirements.

### Summary counts

Every answer template ending in a `_summary` block expects counts that are
derived directly from the per-entity decisions. Count each entity exactly once in
the appropriate bucket; verify that the sum of per-status counts equals the total
number of entities and that per-team counts are consistent with escalated tickets.
For monetary totals, sum the `charge_amount_usd` across all cases, formatted to
two decimal places.
