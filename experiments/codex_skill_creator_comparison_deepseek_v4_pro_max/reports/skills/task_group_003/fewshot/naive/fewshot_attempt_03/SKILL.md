---
name: support-console-analyst
description: Resolve support-console tickets, cases, and enterprise incidents by calling the shared API and applying structured decision rules. Covers ticket triage, mobile-case handling, enterprise export complaints, queue quality, and mobile data recovery.
---

# Support Console Analyst Skill

When a task prompt references a shared support console API at `<TASK_ENV_BASE_URL>`, use the catalog at `GET /api/catalog` to discover available endpoints and record counts. The console provides structured JSON responses for all `GET` calls; there are no mutation endpoints. Follow the decision flows below for each task domain.

## General Workflow

1. Read the task prompt and every file in `payloads/`.
2. If the prompt mentions `<TASK_ENV_BASE_URL>`, substitute it with the actual base URL provided in the task environment.
3. Call `GET /api/catalog` to confirm the available endpoints and understand the record counts. This helps scope parallel lookups.
4. Identify the task domain from the prompt and payload structure, then follow the domain-specific decision flow.
5. Construct the answer JSON to match exactly the `answer_template.json` provided in the payloads. Preserve payload ordering (e.g., ascending `ticket_id` or `case_id` order as encountered in the input).
6. Validate that every enum value, summary count, and calculated numeric field is consistent with the API evidence collected.

## Task Domain: Ticket Batch / Queue Quality (Internet, Voice, Video)

These tasks use a CSV payload listing tickets by `ticket_id` and `account_id`, plus a `reported_service_type` and a free-text `customer_report` or `queue_note`.

### API Surface

For each ticket, collect evidence in parallel from these endpoints:

| Endpoint | What it provides | Wait for |
|---|---|---|
| `GET /api/tickets/<ticket_id>` | `account_id`, `service_area`, `service_type`, `status`, `subscribed_mbps` | Always |
| `GET /api/accounts/<account_id>` | `name`, `status` (Active/Suspended), `authentication.last_login_status`, `authentication.account_recovery_status`, `service_area` | Always |
| `GET /api/diagnostics/<ticket_id>` | `bandwidth_mbps`, `latency_ms`, `jitter_ms`, `root_causes` | Account is Active and ticket is OPEN |
| `GET /api/troubleshooting/<ticket_id>` | `steps`, pre/post metrics | After diagnostics |
| `GET /api/outages` | All outages: `outage_id`, `active`, `service_area`, `service_types`, `eta_hours`, `impact_score` | Always (can be fetched once for all tickets) |

### Account Status Gate

Look up the account first. The status determines the entire downstream flow:

| Account status | Resolution | Route | Key blocker |
|---|---|---|---|
| `Suspended` | `FAILED` | `INELIGIBLE_ACCOUNT` (or `ACCOUNTS_PAYABLE` for overdue) | `OVERDUE_SUSPENSION` (check suspension context) |
| Account not found (API returns `{"error": "not_found"}`) | `FAILED` | `INVALID_ACCOUNT` | `INVALID_ACCOUNT` |
| `Active` but `authentication.last_login_status` is `FAILURE` or `account_recovery_status` is `FAILURE` | `FAILED` | `AUTH_FAILED` | `AUTH_FAILED` |
| `Active` with normal auth | Continue to outage and diagnostic checks | — | — |

### Outage Check

Before running diagnostics, cross-reference the ticket's `service_area` and `service_type` against the outages list. An active outage (`active: true`) that covers the ticket's `service_area` **and** lists the ticket's `service_type` in its `service_types` array takes priority:

- Resolution: `PENDING_ACTION`
- Route: `OUTAGE_WAIT`
- Key blocker: `ACTIVE_OUTAGE`
- Set `outage_id` to the matching outage. Do not run diagnostics when an outage applies.

### Diagnostic Thresholds

When the account is active and no outage applies, run diagnostics. Classify issues by comparing diagnostic results against these thresholds:

- **Latency issue** (`latency_issue: true`): `latency_ms > 100`
- **Stability issue** (`stability_issue: true`): `jitter_ms > 30`
- **Bandwidth issue** (`bandwidth_issue: true`): `bandwidth_mbps < (subscribed_mbps * 0.85)`

Then apply this escalation logic:

| Root cause(s) in diagnostics | Resolution | Escalation team | Route |
|---|---|---|---|
| `FIBER_DROP_DAMAGE` or `SIGNAL_LOSS` | `ESCALATED` | `FIELD_OPS` | `ESCALATION` |
| `BACKBONE_CAPACITY` or similar capacity errors | `ESCALATED` | `NETWORK_ENGINEERING` | `ESCALATION` |
| `PROVISIONING_STALE` or provisioning/drift issues | `ESCALATED` | `TIER2_SUPPORT` | `ESCALATION` |
| `CONFIGURATION_DRIFT` or fixable issues (troubleshooting completes) | `RESOLVED` | `NONE` | `AUTO_TROUBLESHOOTING` |
| Any diagnostic issue that does not match an escalation category above | `RESOLVED` | `NONE` | `AUTO_TROUBLESHOOTING` |

When `RESOLVED` / `AUTO_TROUBLESHOOTING`, set `diagnostic_needed: true` (the diagnostic itself is the resolution mechanism). When an outage or account failure applies, set `diagnostic_needed: false` (no diagnostic was or should be run).

### Summary Counts

Compute batch / queue summary counts by tallying the per-ticket decisions:
- Count each `final_resolution_status` into the `RESOLVED`, `PENDING_ACTION`, `ESCALATED`, `FAILED` buckets.
- For ticket-batch tasks, `tickets_requiring_customer_wait` counts tickets where `PENDING_ACTION` (outage wait).
- For queue-quality tasks, also count each `route_team` into its respective bucket.

---

## Task Domain: Mobile Case Queue (Contact Center)

These tasks provide a JSON case list (`payloads/case_queue.json` or similar) with `case_id` and `reported_issue` for each case.

### API Surface

For each case, collect evidence in parallel from:

| Endpoint | What it provides |
|---|---|
| `GET /api/cases/<case_id>` | `customer_id`, `line_id`, `device_id`, `issue_type` |
| `GET /api/customers/<customer_id>` | `name`, `phone_number`, `status` |
| `GET /api/lines/<line_id>` | `status`, `suspension_reason`, `roaming_enabled`, `data_used_gb`, `plan_id`, `device_id` |
| `GET /api/devices/<device_id>` | `sim_status`, `airplane_mode`, `mobile_data_enabled`, `phone_roaming_enabled`, `data_saver_mode`, `vpn_connected`, `network_mode_preference`, `messaging_permissions`, `signal_strength`, `wifi_calling_enabled`, `mmsc_url_present`, `can_send_mms` |
| `GET /api/plans/<plan_id>` | `data_limit_gb`, `data_refueling_price_per_gb`, `monthly_price_usd` |
| `GET /api/bills` (filter by `customer_id`) | `bill_id`, `amount_due_usd`, `status`, `due_date` |

### Issue-to-Action Mapping

Match the `reported_issue` text against these patterns (case-insensitive keyword matching) and then validate with API evidence:

| Keywords in reported_issue | Evidence to verify | Primary action | Secondary action | Final route | Permission | bill_id / charge |
|---|---|---|---|---|---|---|
| "no service" after commute/travel | Device `sim_status: "missing"` or `signal_strength: "none"` with `sim_status: "missing"` | `RESEAT_SIM` | `NO_ACTION` | `SELF_SERVICE` | `NONE` | — |
| "suspended" + "overdue" / "pay" / "clear" | Line `status: "Suspended"` + `suspension_reason: "OVERDUE_BILL"`; bill `status: "Overdue"` | `SEND_PAYMENT_REQUEST` | `RESUME_LINE_REBOOT` | `BILLING_RECOVERY` | `NONE` | bill_id and amount from overdue bill |
| "traveling" / "abroad" + "no data" | Line `roaming_enabled: true`; roaming-related data issue | `TOGGLE_ROAMING` | `NO_ACTION` | `SELF_SERVICE` | `NONE` | — |
| "messaging" / "photos" / "mms" / "send" | Device `can_send_mms: false`; check `messaging_permissions.storage` | `GRANT_MESSAGING_PERMISSION` | `NO_ACTION` | `SELF_SERVICE` | `storage` (the missing permission) | — |
| "slow" + data | Check device `vpn_connected`, `data_saver_mode`, `network_mode_preference` | `DISCONNECT_VPN` if VPN connected, else `TOGGLE_DATA_SAVER` if data saver on, else `SET_NETWORK_MODE` | `NO_ACTION` | `SELF_SERVICE` | `NONE` | — |

When a case does not clearly match any pattern after collecting API evidence, route to `TRANSFER_HUMAN` / `HUMAN_TRANSFER`.

---

## Task Domain: Mobile Data Recovery

These tasks use `payloads/mobile_data_worklist.json` with case entries and may include `customer_preferences`.

### API Surface

Same endpoints as Mobile Case Queue: `GET /api/cases/<case_id>`, then `GET /api/lines/<line_id>`, `GET /api/devices/<device_id>`, `GET /api/plans/<plan_id>`.

### Decision Flow

For each case, match the `reported_issue` keyword pattern and verify with API evidence:

| Keywords | Evidence | Primary action | Final route | carrier_update_required | data_refuel_gb / charge |
|---|---|---|---|---|---|
| "data stopped" / "usage limit" | `line.data_used_gb >= plan.data_limit_gb` | `REFUEL_DATA` | `DATA_RECOVERY` | `false` | GB from `customer_preferences.accepted_refuel_gb`; charge = GB × `plan.data_refueling_price_per_gb` |
| "roaming" + "no data" | `line.roaming_enabled: true` but device may need carrier-side change | `ENABLE_LINE_ROAMING` | `CARRIER_UPDATE` | `true` | 0.0 / 0.0 |
| "slow" + "data-saver" | Device `data_saver_mode: true` | `TOGGLE_DATA_SAVER` | `DEVICE_SETTING_FIX` | `false` | 0.0 / 0.0 |
| "slow" + "older network" | Device `network_mode_preference` is below 4g/5g | `SET_NETWORK_MODE` | `DEVICE_SETTING_FIX` | `false` | 0.0 / 0.0 |
| "no data" + "settings change" | Device `mobile_data_enabled: false` | `TOGGLE_MOBILE_DATA` | `DEVICE_SETTING_FIX` | `false` | 0.0 / 0.0 |

Secondary action defaults to `NO_ACTION` unless specified otherwise in the template.

---

## Task Domain: Enterprise Export Complaint

These tasks provide a client complaint email and response requirements. The goal is to produce a structured incident response package.

### API Surface

| Endpoint | What it provides |
|---|---|
| `GET /api/enterprise/accounts` | List all enterprise accounts; find the matching account by name or by searching for the account referenced in the complaint |
| `GET /api/enterprise/incidents` | List all incidents; find the matching incident by ID or product + account |
| `GET /api/enterprise/incidents/<incident_id>` | `engineering_owner`, `account_owner`, `severity`, `product`, `enterprise_account_id`, `summary` |
| `GET /api/enterprise/accounts/<account_id>` | `account_owner`, `finance_owner`, `name`, `tier` |
| `GET /api/enterprise/export-runs` | All export runs; filter by `enterprise_account_id` and `incident_id` to find the failure window |
| `GET /api/enterprise/messages` | All messages; filter for the incident/account to extract root cause and SLA context |
| `GET /api/enterprise/sla/<account_id>` | `credit_trigger`, `monthly_export_credit_percent` (or similar field), `executive_contact` |

### Decision Flow

1. **Identify the incident**: Use the incident reference from the complaint (e.g., "INC-XXXX") to call `GET /api/enterprise/incidents/<incident_id>`. This gives `enterprise_account_id`.

2. **Get enterprise account details**: `GET /api/enterprise/accounts/<account_id>` for `account_owner` and `finance_owner`.

3. **Build the failure window**: Pull all export runs, filter by `enterprise_account_id` and `incident_id`. Find consecutive runs with `status: "FAILED"`, sorted by `run_date`. The failure window `start_date` is the earliest failed run date; `end_date` is the latest failed run date; `failed_days` is the count of distinct failed run dates.

4. **Determine root cause category**: From the failed export runs, collect `failure_code` values. From messages, search for messages by the engineering owner that describe the cause. Derive a concise category:
   - `STALE_CREDENTIAL` → "stale credential after rotation"
   - `STAGING_STORAGE_QUOTA` → "staging storage quota exceeded"
   - Map other failure codes to readable categories

5. **Check contributing alert**: If messages reference an `export-alerts-archive` channel (suggesting alerts were archived rather than routed), set `contributing_alert_issue` to `ARCHIVED_ALERT_ROUTE`. Otherwise `NONE` or `UNKNOWN`.

6. **SLA credit**: From `GET /api/enterprise/sla/<account_id>`, use `monthly_export_credit_percent` (or similar field) as `sla_credit_percent`. Map the field name to the percent value — different SLA contracts may use different field names.

7. **Backfill days**: Equal to `failed_days` (the number of consecutive failed runs that need re-export).

8. **Severity**: From the incident record's `severity` field.

9. **Engineering owner and account owner**: From the incident and account records respectively.

10. **Naming conventions**: Follow the `naming_style` string in the response requirements:
    - Channel name: lowercase-hyphen client name (e.g., "client-name-channel")
    - Evidence folder: "{Client Name} {Month Year} Investigation" (e.g., "{Client Name} {Month Year} Investigation")
    - Report title: "{Client Name} Export Failure - Resolution Report"

11. **Share permissions**: Match users from `permission_users_to_include` in the order listed. Default permission is `view` unless the user is `finance_owner`, in which case `edit`.

12. **Response status**: If SLA credit applies and needs finance approval, use `NEEDS_FINANCE_REVIEW`. If root cause is unclear, `NEEDS_ENGINEERING_REVIEW`. If investigation is ongoing, `UNDER_INVESTIGATION`. Otherwise `READY_TO_SEND`.

---

## Validation Checklist

Before returning the answer JSON:

- Every `ticket_id`, `case_id`, or `incident_id` in the output must match the input payload (order and values preserved).
- Every enum value must be exactly one of the permitted values in the answer template.
- Summary counts must be tallied from the per-item decisions (not hard-coded).
- Numeric fields (`charge_amount_usd`, `data_refuel_gb`) must be verified from the API: charge = unit price × quantity, rounded to 2 decimal places; GB to 1 decimal place.
- Fields that are not applicable (`""` for strings, `false` for booleans, `0` or `0.0` for numbers) must use the exact zero-value type shown in the answer template.
- Do not guess values. Every field must be traceable to an API response or a payload input.

---

## Parallel API Calls

The support console API can handle many parallel `GET` requests. Always batch independent lookups:

- For ticket tasks: fetch all tickets, accounts, outages, and applicable diagnostics in parallel per ticket.
- For case tasks: fetch all cases, then fetch lines, devices, plans, and bills per case in parallel.
- For enterprise tasks: fetch incident, account, SLA, export runs, and messages in parallel.

Use the catalog's `record_counts` to decide whether to fetch a full collection (e.g., all outages, all bills) once and filter locally, or to fetch individual records by ID. Prefer fetching a full collection once when the collection is small (< 100 records) and you need to cross-reference across multiple items.
