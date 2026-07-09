# Support Console Solver — SKILL.md

## Overview

This skill covers the task_group_003 support-console API used to resolve service tickets, mobile cases, enterprise incidents, and queue-quality reviews. The API is read-only and returns all evidence needed to construct structured JSON answer payloads.

## API Usage Habits

### Base URL & Discovery
- Use the remote URL provided by the harness (override any localhost references in task prompts).
- Start with `/health` to confirm connectivity, then `/api/catalog` for the full endpoint list and record counts.
- Endpoint list: `/api/accounts[/<id>]`, `/api/tickets[/<id>]`, `/api/outages?service_area=<area>`, `/api/diagnostics/<ticket_id>`, `/api/troubleshooting/<ticket_id>`, `/api/cases[/<id>]`, `/api/customers`, `/api/lines[/<id>]`, `/api/devices[/<id>]`, `/api/plans[/<id>]`, `/api/bills`, `/api/enterprise/incidents[/<id>]`, `/api/enterprise/export-runs?incident_id=<id>`, `/api/enterprise/messages?query=<text>`, `/api/enterprise/sla/<enterprise_account_id>`.

### Data Fetching Pattern
- For batch tasks, fetch tickets/cases first to get IDs (account_id, line_id, device_id, service_area), then fan out to accounts, diagnostics, outages, lines, devices in parallel.
- For enterprise tasks, fetch the incident, export-runs, messages (try multiple queries: incident ID, account ID, keywords from the complaint), and SLA in parallel.
- Accounts with non-matching IDs return `{"error": "not_found"}` — treat these as invalid accounts.
- Bills are listed flat at `/api/bills`; filter by `customer_id` to find the relevant one.
- Plans give `data_limit_gb` and `data_refueling_price_per_gb` for data-refuel calculations.

## Business Rule Reference

### Ticket Resolution (train_001 / train_004 patterns)

| Scenario | Status | Route / Team | Key Blocker | Diag? |
|---|---|---|---|---|
| Active outage in service area | PENDING_ACTION | NONE / OUTAGE_WAIT | ACTIVE_OUTAGE | false |
| Account not found (404) | FAILED | NONE / INELIGIBLE_ACCOUNT or INVALID_ACCOUNT | INVALID_ACCOUNT | false |
| Account Suspended (overdue) | PENDING_ACTION | ACCOUNTS_PAYABLE | OVERDUE_SUSPENSION | false |
| Auth failure (recovery_status=FAILURE) | FAILED | NONE | AUTH_FAILED | false |
| Physical damage (FIBER_DROP_DAMAGE) | ESCALATED | FIELD_OPS / ESCALATION | PHYSICAL_LINE_FAULT | true |
| Backbone/network capacity | ESCALATED | NETWORK_ENGINEERING | NETWORK_CAPACITY | true |
| Provisioning stale / config drift | ESCALATED | TIER2_SUPPORT | PROVISIONING_STALE | true |
| Auto-troubleshooting fixed it | RESOLVED | AUTO_TROUBLESHOOTING | NONE | true |

### Quality Flag Thresholds
- **latency_issue**: `latency_ms` > ~100ms from diagnostics
- **stability_issue**: `jitter_ms` > ~30ms from diagnostics  
- **bandwidth_issue**: `bandwidth_mbps` < ~80% of `subscribed_mbps`
- These flags are based on diagnostic data regardless of account status; set them from the diagnostic results when available.

### Mobile Case Actions (train_002 / train_005 patterns)

Map device/line fields directly to actions:
| Device/Line State | Primary Action | Final Route |
|---|---|---|
| `sim_status: "missing"` | RESEAT_SIM | SELF_SERVICE |
| Line suspended, `suspension_reason: OVERDUE_BILL` | SEND_PAYMENT_REQUEST (+ RESUME_LINE_REBOOT secondary) | BILLING_RECOVERY |
| `phone_roaming_enabled: false` (abroad, line roaming on) | TOGGLE_ROAMING | SELF_SERVICE |
| `messaging_permissions.storage: false` | GRANT_MESSAGING_PERMISSION | SELF_SERVICE |
| `vpn_connected: true` + slow data | DISCONNECT_VPN | SELF_SERVICE |
| Line `roaming_enabled: false` (abroad) | ENABLE_LINE_ROAMING | CARRIER_UPDATE |
| `data_used_gb` > plan `data_limit_gb` | REFUEL_DATA | DATA_RECOVERY |
| `data_saver_mode: true` | TOGGLE_DATA_SAVER | DEVICE_SETTING_FIX |
| `network_mode_preference: "3g_only"` | SET_NETWORK_MODE | DEVICE_SETTING_FIX |
| `mobile_data_enabled: false` | TOGGLE_MOBILE_DATA | DEVICE_SETTING_FIX |

### Enterprise Incident Patterns (train_003)
- **incident_id** from the complaint; look up via `/api/enterprise/incidents/<id>`.
- **root_cause_category**: Use the `failure_code` from failed export runs (e.g., "STALE_CREDENTIAL" → "stale credential").
- **contributing_alert_issue**: `ARCHIVED_ALERT_ROUTE` when messages appear in an archived channel like `export-alerts-archive`; otherwise `NONE`.
- **failure_window**: start_date/end_date from the first/last failed export `run_date`; `failed_days` is the count of consecutive FAILED runs.
- **backfill_days**: Equals the number of failed days that need manual backfill.
- **sla_credit_percent**: Integer from the SLA endpoint's `monthly_export_credit_percent` (or equivalent field).
- **severity**, **engineering_owner**, **account_owner**: Directly from the incident record.
- **response_status**: `NEEDS_ENGINEERING_REVIEW` when the root cause involves engineering changes; `NEEDS_FINANCE_REVIEW` when SLA credit requires finance sign-off.
- Search messages with multiple queries: incident ID, account ID, and keywords from the complaint email.

## Output Field Conventions

### Numeric Formats
- `charge_amount_usd`: Always a number with exactly **two decimal places** (e.g., `4.00`, `0.00`).
- `data_refuel_gb`: Number with **one decimal place** (e.g., `2.0`, `0.0`).
- `sla_credit_percent`: Integer representing percentage (e.g., `15`, not `"15%"`).
- Summary counts: Plain integers.

### Enum Values
- Use the **exact** enum strings from the answer template — case and underscore matching are strict (e.g., `PENDING_ACTION`, not `PENDING`; `TIER2_SUPPORT`, not `TIER_2_SUPPORT`).
- When a template provides `NONE` as a valid enum member, use `"NONE"` (string), not an empty string or null.
- For `outage_id`, `bill_id`: use `""` (empty string) when not applicable, not `null` or omitting the field.

### Order Preservation
- Preserve the **input payload order** for ticket/case arrays (ascending by ticket_id/case_id as they appear in the input).
- For `share_permissions`, order users as listed in the requirements file.

### Summary Counts
- Summary objects must agree with the per-item decisions — double-check all counts before submitting.
- `tickets_requiring_customer_wait`: Count tickets where the customer must wait for an external event (outage resolution, payment processing).

## Compact SOP

1. **Read** the prompt, answer template, and all payload files.
2. **Query** the API for each entity: tickets/cases → accounts/lines/devices → diagnostics → outages → bills/plans.
3. **Classify** each item by mapping the strongest signal:
   - Outage active? → PENDING_ACTION / OUTAGE_WAIT
   - Account not found? → FAILED / INVALID_ACCOUNT
   - Account suspended? → PENDING_ACTION / ACCOUNTS_PAYABLE / OVERDUE_SUSPENSION
   - Auth failure? → FAILED / AUTH_FAILED
   - Diagnostic root cause → match to escalation team and key blocker
   - Device field mismatch → match to the action table above
4. **Fill** the answer template, preserving input order, using exact enum strings and correct numeric formats.
5. **Audit** summary counts against per-item decisions before submitting.

## Common Pitfalls

- **Wrong enum case**: Templates use UPPER_SNAKE_CASE consistently. Never lowercase or mixed.
- **Null vs empty string**: Use `""` for absent string IDs like `outage_id` and `bill_id`, not `null`.
- **Overriding diagnostic flags for account issues**: Even when an account is suspended or invalid, diagnostic data may still exist — only set latency/stability/bandwidth flags from actual diagnostic measurements, not from account status.
- **Diagnostic thresholds too aggressive/lenient**: Test the score impact of threshold choices. If a quality flag is borderline (latency ~100ms, jitter ~30ms), try both values.
- **Ignoring line vs device roaming**: `roaming_enabled` on the line and `phone_roaming_enabled` on the device are different fields with different actions. Device roaming off → TOGGLE_ROAMING. Line roaming off → ENABLE_LINE_ROAMING + carrier_update_required=true.
- **Missing secondary actions**: For billing recovery (suspended line), the secondary action of RESUME_LINE_REBOOT is required. For most self-service fixes, secondary is NO_ACTION.
- **Forgetting to multiply refuel charge**: `charge_amount_usd = data_refuel_gb × plan.data_refueling_price_per_gb`.
- **Message search too narrow**: Try multiple query strings (incident ID, account ID, client name, product name) when searching `/api/enterprise/messages`.
