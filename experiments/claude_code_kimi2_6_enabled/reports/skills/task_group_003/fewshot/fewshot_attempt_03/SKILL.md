# CRM Service-Ticket Processing SOP

## 1. Output Schema Conventions

### General Rules
- **Preserve payload order** for ticket decisions unless the template explicitly says "preserve ascending case_id order".
- Use **exact enum values** in UPPERCASE as defined in the answer template. Do not invent new enum strings.
- Empty strings (`""`) are used for fields that do not apply; do not use `null`.
- Numbers: follow the template's decimal precision (one or two decimals). Use `0.0` when a numeric field is not applicable.
- Booleans: use JSON `true`/`false`.

### Summary Counts
- Every answer includes a summary object that counts occurrences of each status/route.
- Counts must be **exact integers** derived from the decisions array.
- Verify that summary keys match the template exactly; missing or extra keys will fail validation.

---

## 2. Ticket Routing & Resolution (train_001 / train_004 patterns)

### Resolution Status Enum
`RESOLVED | PENDING_ACTION | ESCALATED | FAILED`

### Route / Escalation Team Enum
`NONE | TIER2_SUPPORT | FIELD_OPS | NETWORK_ENGINEERING | ACCOUNTS_PAYABLE`

### Decision Rules (inferred from gold answers)
1. **Outage / Service Interruption** → `PENDING_ACTION`, route `NONE`, key blocker `ACTIVE_OUTAGE` (or `OUTAGE_WAIT`), no diagnostic.
2. **Profile / Config Fixable** (e.g., voice profile drops, intermittent speed) → `RESOLVED`, route `NONE`, blocker `NONE`, diagnostic required.
3. **Invalid / Missing Account** → `FAILED`, route `NONE`, blocker `INVALID_ACCOUNT`.
4. **Authentication Failure** → `FAILED`, route `NONE`, blocker `AUTH_FAILED`.
5. **Overdue / Suspended Account** → `FAILED`, route `ACCOUNTS_PAYABLE`, blocker `OVERDUE_SUSPENSION`.
6. **Network Capacity / Backbone Errors** → `ESCALATED`, route `NETWORK_ENGINEERING`, blocker `NETWORK_CAPACITY`, diagnostic required.
7. **Provisioning Stale / Mismatch** → `ESCALATED`, route `TIER2_SUPPORT`, blocker `PROVISIONING_STALE`, diagnostic required.
8. **Physical Line Fault** → `ESCALATED`, route `FIELD_OPS`, blocker `PHYSICAL_LINE_FAULT`, diagnostic required.
9. **Fraud Suspension** → `FAILED`, route `NONE`, blocker `FRAUD_SUSPENSION`.

### Diagnostic Flag
- Set `diagnostic_needed` / `diagnostic_required` to `true` when the issue requires technical troubleshooting (latency, packet loss, profile drops, capacity, provisioning).
- Set to `false` for pure account/blocker issues (outage wait, invalid account, auth failed, suspension).

### Issue-Type Booleans (train_001 only)
- `latency_issue`, `stability_issue`, `bandwidth_issue`: map from customer report keywords.
  - "intermittent" / "poor speed" / "latency" / "packet loss" → all three true.
  - Outage / video unavailable → all false.
  - Account hold / cannot connect → all false.

---

## 3. Case Queue Processing (train_002 / train_005 patterns)

### Primary Action Enum
`TOGGLE_AIRPLANE_MODE | RESEAT_SIM | RESET_APN_REBOOT | SEND_PAYMENT_REQUEST | RESUME_LINE_REBOOT | TRANSFER_HUMAN | TOGGLE_MOBILE_DATA | TOGGLE_ROAMING | ENABLE_LINE_ROAMING | REFUEL_DATA | TOGGLE_DATA_SAVER | SET_NETWORK_MODE | DISCONNECT_VPN | GRANT_MESSAGING_PERMISSION | TOGGLE_WIFI_CALLING | NO_ACTION`

### Final Route Enum
`SELF_SERVICE | BILLING_RECOVERY | CARRIER_UPDATE | DEVICE_SETTING_FIX | DATA_RECOVERY | HUMAN_TRANSFER`

### Mapping Rules (inferred from gold answers)
| Reported Issue | Primary Action | Secondary Action | Final Route | Special Fields |
|---|---|---|---|---|
| Data stopped after usage limit | `REFUEL_DATA` | `NO_ACTION` | `DATA_RECOVERY` | `data_refuel_gb` from customer preferences; charge = gb × 2.0 USD |
| Roaming on but no data (traveler) | `ENABLE_LINE_ROAMING` | `NO_ACTION` | `CARRIER_UPDATE` | `carrier_update_required: true` |
| Slow data + data-saver icon | `TOGGLE_DATA_SAVER` | `NO_ACTION` | `DEVICE_SETTING_FIX` | |
| Slow data on older network mode | `SET_NETWORK_MODE` | `NO_ACTION` | `DEVICE_SETTING_FIX` | |
| No data after settings change | `TOGGLE_MOBILE_DATA` | `NO_ACTION` | `DEVICE_SETTING_FIX` | |
| SIM / physical issue | `RESEAT_SIM` | `NO_ACTION` | `SELF_SERVICE` | |
| Payment overdue / suspended | `SEND_PAYMENT_REQUEST` | `RESUME_LINE_REBOOT` | `BILLING_RECOVERY` | `bill_id` from payload; charge from bill amount |
| Roaming toggle needed | `TOGGLE_ROAMING` | `NO_ACTION` | `SELF_SERVICE` | |
| Messaging permission denied | `GRANT_MESSAGING_PERMISSION` | `NO_ACTION` | `SELF_SERVICE` | `permission: storage` (or `sms` / `sms_and_storage` as appropriate) |
| VPN blocking connectivity | `DISCONNECT_VPN` | `NO_ACTION` | `SELF_SERVICE` | |
| Voice profile drops | `TOGGLE_WIFI_CALLING` or profile reset | `NO_ACTION` | `SELF_SERVICE` | |
| Unrecognized / unresolvable | `TRANSFER_HUMAN` | `NO_ACTION` | `HUMAN_TRANSFER` | |

### Charge Calculation
- Data refuel: charge = `data_refuel_gb × 2.0` USD (e.g., 2.0 GB → 4.0 USD).
- Billing recovery: charge = bill amount from payload (e.g., 86.4 USD).
- All self-service / device fixes: 0.0 USD.

### Permission Field (train_002)
- `NONE` for most cases.
- `storage` when granting messaging permission.
- `sms` or `sms_and_storage` when explicitly required by the issue.

---

## 4. Enterprise Incident Response (train_003 pattern)

### Required Fields
`incident_id`, `enterprise_account_id`, `root_cause_category`, `contributing_alert_issue`, `failure_window`, `backfill_days`, `sla_credit_percent`, `severity`, `engineering_owner`, `account_owner`, `channel_name`, `evidence_folder`, `report_title`, `share_permissions`, `response_status`

### Naming Conventions (from `response_requirements.json`)
- `channel_name`: lowercase, hyphenated (e.g., `asteri-retail-inc`).
- `evidence_folder`: `Client Name Month YYYY Investigation` (e.g., `Asteri Retail Inc. May 2026 Investigation`).
- `report_title`: `Client Name Export Failure - Resolution Report`.

### Share Permissions
- Include every user listed in `permission_users_to_include` from requirements.
- Preserve the **order** of users as listed in requirements.
- Permission levels: `view | edit | upload_only`.
- In the gold answer, first user gets `view`, second gets `edit` (verify against explicit instructions if present).

### Response Status Enum
`READY_TO_SEND | NEEDS_FINANCE_REVIEW | NEEDS_ENGINEERING_REVIEW | UNDER_INVESTIGATION`

### Severity Enum
`Critical | High | Medium | Low`

### Failure Window
- `start_date` and `end_date` in `YYYY-MM-DD`.
- `failed_days` is inclusive count: `(end_date − start_date) + 1`.
- `backfill_days` equals `failed_days` in the gold answer.

### SLA Credit
- Expressed as **integer percent** (e.g., `15`).

### Root Cause & Contributing Alert
- `root_cause_category`: concise phrase inferred from export-run logs and message evidence (e.g., "stale credential after rotation").
- `contributing_alert_issue`: `ARCHIVED_ALERT_ROUTE | NONE | UNKNOWN`.

---

## 5. Sorting & Ordering Rules

1. **Payload order**: unless template says otherwise, emit decisions in the exact order they appear in the input CSV / JSON array.
2. **Ascending case_id order**: when template explicitly requires it, sort by `case_id` string (alphanumeric ascending).
3. **Share permissions order**: preserve the order of `permission_users_to_include` from requirements.

---

## 6. Common Pitfalls

- **Do not omit empty fields**: use `""` for strings and `0.0` for numbers when a field does not apply.
- **Do not add extra keys** to summary objects; match the template exactly.
- **Enum case sensitivity**: all enums are UPPERCASE with underscores; never lowercase or camelCase.
- **Boolean vs. string**: use JSON `true`/`false`, not `"true"`/`"false"`.
- **Diagnostic flag inconsistency**: ensure `diagnostic_required` aligns with the resolution route (e.g., `ESCALATED` to engineering teams usually requires diagnostic).
- **Charge rounding**: use standard decimal arithmetic; do not round integer percentages or counts.
- **Date arithmetic**: `failed_days` is inclusive; verify by counting both start and end dates.

---

## 7. Remote API Habits (from environment_access.md)

- Endpoints are RESTful and expect JSON payloads.
- Authentication is typically header-based (Bearer token or API key); check `environment_access.md` for the exact header name.
- When fetching account or outage data, prefer `GET /accounts/{id}` and `GET /outages/{id}` rather than list endpoints.
- If rate-limit headers (`X-RateLimit-Remaining`) are present, respect them; do not brute-force.
- For POST / PATCH operations, always include `Content-Type: application/json`.
- Error responses may contain `error_code` and `details`; surface `details` in logs for debugging.
