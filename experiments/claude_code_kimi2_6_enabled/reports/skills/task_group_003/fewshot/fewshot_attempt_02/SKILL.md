# Skill: CRM Service-Ticket Routing & Resolution (task_group_003)

## Environment
- Base URL: `http://34.46.77.124:8003` (from `environment_access.md`).
- Do **not** start local env containers or read `env/` source.
- If a task prompt mentions a local URL, override it with the remote base URL above.

## General Output Convention
- Produce a single JSON file named `answer.json`.
- Preserve the exact top-level keys and nested structure shown in the task’s `answer_template.json`.
- Preserve the original order of items (e.g., ascending `ticket_id` / `case_id`) unless the prompt explicitly requests a sort.
- Use empty string `""` for absent string fields, `0.0` for absent numeric fields, and `false` for absent booleans rather than omitting the key.

---

## 1. Ticket-Batch Routing (train_001 pattern)

### Input
- CSV or JSON list of tickets with fields such as `ticket_id`, `account_id`, `reported_service_type`, `customer_report`.

### Per-Ticket Decision Schema
```json
{
  "ticket_id": "...",
  "account_id": "...",
  "final_resolution_status": "RESOLVED | PENDING_ACTION | ESCALATED | FAILED",
  "diagnostic_needed": true | false,
  "latency_issue": true | false,
  "stability_issue": true | false,
  "bandwidth_issue": true | false,
  "outage_id": "OUT-XXXX or empty string",
  "escalation_team": "NONE | FIELD_OPS | TIER2_SUPPORT | NETWORK_ENGINEERING | ACCOUNTS_PAYABLE",
  "resolution_route": "AUTO_TROUBLESHOOTING | OUTAGE_WAIT | ESCALATION | INELIGIBLE_ACCOUNT"
}
```

### Routing Rules (inferred from gold answer)
1. **General connectivity / speed complaints** (latency, packet loss, intermittent) → `diagnostic_needed: true`, all issue flags (`latency_issue`, `stability_issue`, `bandwidth_issue`) set to `true`, `final_resolution_status: RESOLVED`, `resolution_route: AUTO_TROUBLESHOOTING`, `escalation_team: NONE`.
2. **Active outage mention** → `final_resolution_status: PENDING_ACTION`, `resolution_route: OUTAGE_WAIT`, populate `outage_id`, no diagnostics, no issue flags.
3. **Line-work / physical damage / capacity errors** → `final_resolution_status: ESCALATED`, `resolution_route: ESCALATION`, set `escalation_team` (e.g., `FIELD_OPS`), `diagnostic_needed: true`, all issue flags `true`.
4. **Account hold / bad account / authentication failure** → `final_resolution_status: FAILED`, `resolution_route: INELIGIBLE_ACCOUNT`, no diagnostics, no issue flags, no outage.

### Batch Summary Schema
```json
{
  "RESOLVED": <int>,
  "PENDING_ACTION": <int>,
  "ESCALATED": <int>,
  "FAILED": <int>,
  "tickets_requiring_customer_wait": <int>
}
```
- Count `tickets_requiring_customer_wait` as the subset of tickets where the customer must wait (e.g., outage-wait or pending-action tickets).

---

## 2. Case-Queue Self-Service vs Billing vs Transfer (train_002 pattern)

### Input
- JSON list of cases with `case_id` and a short `reported_issue` description.

### Per-Case Decision Schema
```json
{
  "case_id": "...",
  "customer_id": "CUST-XXXX",
  "line_id": "LINE-XXXX",
  "primary_action": "RESEAT_SIM | SEND_PAYMENT_REQUEST | TOGGLE_ROAMING | GRANT_MESSAGING_PERMISSION | DISCONNECT_VPN | ...",
  "secondary_action": "NO_ACTION | RESUME_LINE_REBOOT | ...",
  "permission": "NONE | storage | ...",
  "bill_id": "BILL-XXXX or empty string",
  "charge_amount_usd": 0.00,
  "final_route": "SELF_SERVICE | BILLING_RECOVERY | CARRIER_UPDATE | HUMAN_TRANSFER"
}
```

### Decision Rules (inferred from gold answer)
| Reported Issue | Primary Action | Secondary Action | `bill_id` | `charge_amount_usd` | `final_route` |
|---|---|---|---|---|---|
| No service after commute / physical jostle | `RESEAT_SIM` | `NO_ACTION` | `""` | `0.0` | `SELF_SERVICE` |
| Line suspended, customer ready to pay overdue | `SEND_PAYMENT_REQUEST` | `RESUME_LINE_REBOOT` | `BILL-XXXX` | amount from account | `BILLING_RECOVERY` |
| Traveling abroad, no mobile data | `TOGGLE_ROAMING` | `NO_ACTION` | `""` | `0.0` | `SELF_SERVICE` |
| Messaging app cannot send photos | `GRANT_MESSAGING_PERMISSION` | `NO_ACTION` | `""` | `0.0` | `SELF_SERVICE` |
| Mobile data works but slow | `DISCONNECT_VPN` | `NO_ACTION` | `""` | `0.0` | `SELF_SERVICE` |

- Map `case_id` → `customer_id` and `line_id` by replacing the prefix (`CASE-` → `CUST-` and `CASE-` → `LINE-`).
- `charge_amount_usd` uses **two decimal places**.
- `permission` is `"NONE"` unless the issue explicitly involves a missing app permission (e.g., messaging storage).

### Queue Summary Schema
```json
{
  "self_service_fixes": <int>,
  "billing_recoveries": <int>,
  "carrier_updates": <int>,
  "human_transfers": <int>
}
```

---

## 3. Enterprise Complaint Response (train_003 pattern)

### Input
- Free-text email (`client_complaint_email.txt`) plus a `response_requirements.json` specifying required fields and naming style.

### Output Schema
```json
{
  "incident_id": "INC-XXXX",
  "enterprise_account_id": "ENT-XXXX",
  "root_cause_category": "<free-text description of root cause>",
  "contributing_alert_issue": "ARCHIVED_ALERT_ROUTE | ...",
  "failure_window": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "failed_days": <int>
  },
  "backfill_days": <int>,
  "sla_credit_percent": <int>,
  "severity": "Critical | High | Medium | Low",
  "engineering_owner": "<username>",
  "account_owner": "<username>",
  "channel_name": "<lowercase-hyphen-channel>",
  "evidence_folder": "<Client Name> <Month> <Year> Investigation",
  "report_title": "<Client Name> Export Failure - Resolution Report",
  "share_permissions": [
    {"user": "...", "permission": "view | edit"}
  ],
  "response_status": "NEEDS_FINANCE_REVIEW | ..."
}
```

### Extraction Rules
1. **Incident & Account IDs** – parse from the email subject/body (`INC-7301`, `ENT-3001`).
2. **Root cause** – derive from body clues (e.g., “stale credential after rotation”).
3. **Failure window** – count consecutive failed days; `failed_days` = inclusive count (`end_date - start_date + 1`).
4. **Backfill days** – set equal to `failed_days` unless the prompt states otherwise.
5. **SLA credit** – use integer percent (e.g., `15`).
6. **Severity** – map keywords: “Critical” for multi-day executive-blocking failures.
7. **Owners** – extract from the email signature or body (e.g., `delana.rao`, `stephany.lo`).
8. **Channel name** – lowercase-hyphen style derived from client name (`Asteri Retail Inc.` → `asteri-retail-inc`).
9. **Evidence folder** – follow `response_requirements.json` naming style: `<Client> <Month> <Year> Investigation`.
10. **Report title** – `<Client> Export Failure - Resolution Report`.
11. **Share permissions** – include every user listed in `response_requirements.json` `permission_users_to_include`; assign `view` or `edit` based on role hints in the email (engineering/account roles often get `edit`, others `view`).
12. **Response status** – `NEEDS_FINANCE_REVIEW` when SLA credits are involved.

---

## 4. Queue-Snapshot Routing (train_004 pattern)

### Input
- CSV with columns: `ticket_id`, `account_id`, `reported_service_type`, `queue_note`.

### Per-Ticket Decision Schema
```json
{
  "ticket_id": "...",
  "final_resolution_status": "RESOLVED | PENDING_ACTION | FAILED | ESCALATED",
  "route_team": "NONE | ACCOUNTS_PAYABLE | NETWORK_ENGINEERING | TIER2_SUPPORT | FIELD_OPS",
  "key_blocker": "NONE | ACTIVE_OUTAGE | INVALID_ACCOUNT | AUTH_FAILED | OVERDUE_SUSPENSION | NETWORK_CAPACITY | PROVISIONING_STALE",
  "diagnostic_required": true | false
}
```

### Routing Rules (inferred from gold answer)
| Queue Note | Status | Route Team | Key Blocker | Diagnostic |
|---|---|---|---|---|
| Neighborhood service interruption | `PENDING_ACTION` | `NONE` | `ACTIVE_OUTAGE` | `false` |
| Voice profile drops calls | `RESOLVED` | `NONE` | `NONE` | `true` |
| No matching account in intake | `FAILED` | `NONE` | `INVALID_ACCOUNT` | `false` |
| Authentication never recovered | `FAILED` | `NONE` | `AUTH_FAILED` | `false` |
| Suspended after overdue notice | `FAILED` | `ACCOUNTS_PAYABLE` | `OVERDUE_SUSPENSION` | `false` |
| Backbone capacity errors | `ESCALATED` | `NETWORK_ENGINEERING` | `NETWORK_CAPACITY` | `true` |
| Provisioning mismatch after move | `ESCALATED` | `TIER2_SUPPORT` | `PROVISIONING_STALE` | `true` |

### Queue Summary Schema
```json
{
  "FAILED": <int>,
  "PENDING_ACTION": <int>,
  "RESOLVED": <int>,
  "ESCALATED": <int>,
  "TIER2_SUPPORT": <int>,
  "FIELD_OPS": <int>,
  "NETWORK_ENGINEERING": <int>,
  "ACCOUNTS_PAYABLE": <int>
}
```
- Count each status and each route team independently.

---

## 5. Mobile-Data Worklist (train_005 pattern)

### Input
- JSON with `cases` array (`case_id`, `reported_issue`) and optional `customer_preferences` per case.

### Per-Case Decision Schema
```json
{
  "case_id": "...",
  "primary_action": "REFUEL_DATA | ENABLE_LINE_ROAMING | TOGGLE_DATA_SAVER | SET_NETWORK_MODE | TOGGLE_MOBILE_DATA | ...",
  "secondary_action": "NO_ACTION | ...",
  "data_refuel_gb": 0.0,
  "charge_amount_usd": 0.00,
  "carrier_update_required": true | false,
  "final_route": "DATA_RECOVERY | CARRIER_UPDATE | DEVICE_SETTING_FIX | HUMAN_TRANSFER"
}
```

### Decision Rules (inferred from gold answer)
| Reported Issue | Primary Action | `data_refuel_gb` | `charge_amount_usd` | `carrier_update_required` | `final_route` |
|---|---|---|---|---|---|
| Data stopped after usage limit | `REFUEL_DATA` | from `customer_preferences.accepted_refuel_gb` | `data_refuel_gb × 2.0` | `false` | `DATA_RECOVERY` |
| Traveler has roaming on phone but no data | `ENABLE_LINE_ROAMING` | `0.0` | `0.0` | `true` | `CARRIER_UPDATE` |
| Slow data and data-saver icon visible | `TOGGLE_DATA_SAVER` | `0.0` | `0.0` | `false` | `DEVICE_SETTING_FIX` |
| Slow data on older network mode | `SET_NETWORK_MODE` | `0.0` | `0.0` | `false` | `DEVICE_SETTING_FIX` |
| No data after settings change | `TOGGLE_MOBILE_DATA` | `0.0` | `0.0` | `false` | `DEVICE_SETTING_FIX` |

- `charge_amount_usd` for refuel = `accepted_refuel_gb × 2.0` (e.g., `2.0 GB × 2.0 = 4.0 USD`).
- `data_refuel_gb` uses **one decimal place**; `charge_amount_usd` uses **two decimal places**.

### Worklist Summary Schema
```json
{
  "data_refuel_cases": <int>,
  "carrier_updates": <int>,
  "device_setting_fixes": <int>,
  "human_transfers": <int>,
  "total_estimated_customer_charge_usd": <float two decimals>
}
```
- Sum all `charge_amount_usd` values for the total charge field.

---

## Common Pitfalls
1. **Do not omit keys** – even when a value is empty/zero/false; the template expects every key present.
2. **Decimal precision** – respect the template’s stated precision (one decimal for GB, two for USD).
3. **Preserve input order** – output tickets/cases in the same ascending ID order as the input unless instructed otherwise.
4. **String enums** – match exact casing (`RESOLVED`, not `Resolved`; `NONE`, not `None`).
5. **No external API calls during skill generation** – this skill is for offline inference from provided payloads; during an actual solve run, query the remote API endpoints mentioned in the task prompt (e.g., `/tickets`, `/cases`, `/diagnostics`) using the base URL above.
