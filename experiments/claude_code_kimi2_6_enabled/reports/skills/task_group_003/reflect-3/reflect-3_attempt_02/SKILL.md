# CRM Service Ticket Processing — Task Group 003 SOP

## 1. Environment & Endpoints
- **CRM Service API base URL** is provided in `environment_access.md` (e.g., `http://host.docker.internal:8123` in Docker contexts).  
  If the host name does not resolve, fall back to the external URL discovered from the container environment (`GDPEVO_ENV_BASE_URL`).
- **Required endpoints** (inspect the OpenAPI/docs route when available, but prefer these exact paths):
  - `POST /tickets/bulk_resolve` → Ticket-batch style tasks
  - `POST /cases/bulk_prioritize` → Mobile-case-queue style tasks
  - `POST /emails/generate_reply` → Incident/complaint-report style tasks
  - `POST /queue/rebalance` or `POST /queue/enrich` → Queue-snapshot style tasks
  - `POST /cases/bulk_refuel` → Mobile-data-worklist style tasks

## 2. Input Verification Pitfall
- **Do not trust cached `Read` output for JSON/CSV files.** In this task group the Read tool returned stale/false templates for several trains.  
- **Always verify** with `cat <file>` or a small Python script before building an answer.

## 3. Answer-Template Conventions
- The answer template can be **deeply nested** (arrays of objects + summary objects). Do not assume a flat structure.
- **Preserve order strictly**:
  - `"preserve payload order"` → emit decisions in the exact order the rows appear in the CSV/JSON payload.
  - `"preserve ascending case_id order"` → sort decisions by `case_id` alphabetically before emitting.
- **Use exact enum strings** from the template schema (e.g., `RESOLVED`, `PENDING_ACTION`, `ESCALATED`, `FAILED`, `TIER2_SUPPORT`, `NETWORK_ENGINEERING`, etc.).
- **Null / not-applicable rules**:
  - Empty string `""` for optional string fields when none applies.
  - `0.0` for numeric refuel fields when not applicable.
  - Boolean fields must be literal `true` or `false` (not strings).

## 4. Per-Task Processing Rules

### 4.1 Ticket Batches (`/tickets/bulk_resolve`)
- **Input:** `ticket_batch.csv` (ticket_id, account_id, reported_service_type, customer_report).
- **Output:** `ticket_decisions` array + `batch_summary` counts.
- **Mapping hints from payload text:**
  - `"account hold notice"` / `"no matching account"` → resolution route `INELIGIBLE_ACCOUNT` or `INVALID_ACCOUNT`; escalate team `ACCOUNTS_PAYABLE`.
  - `"latency and packet loss"` / `"intermittent"` → mark `latency_issue=true`, `stability_issue=true`.
  - `"video stream unavailable"` / `"backbone capacity"` → bandwidth-related; route `NETWORK_ENGINEERING`.
  - `"provisioning mismatch"` / `"authentication never recovered"` → route `TIER2_SUPPORT`, blocker `PROVISIONING_STALE` or `AUTH_FAILED`.
  - `"neighborhood service interruption"` → blocker `ACTIVE_OUTAGE`, route `NETWORK_ENGINEERING`.
- Summary counts must **exactly match** the decision array.

### 4.2 Mobile Case Queue (`/cases/bulk_prioritize`)
- **Input:** `case_queue.json` (cases with `case_id` and `reported_issue` only).
- **Output:** `case_decisions` array (ascending `case_id`) + `queue_summary`.
- **Mapping hints:**
  - `"no service after commute"` → `TOGGLE_AIRPLANE_MODE` / `RESEAT_SIM` → `SELF_SERVICE`.
  - `"line suspended … overdue"` → `SEND_PAYMENT_REQUEST` or `RESUME_LINE_REBOOT` → `BILLING_RECOVERY`.
  - `"traveling abroad … no data"` → `TOGGLE_ROAMING` / `ENABLE_LINE_ROAMING` → `CARRIER_UPDATE`.
  - `"messaging app cannot send photos"` → `GRANT_MESSAGING_PERMISSION` + permission `storage` or `sms_and_storage` → `SELF_SERVICE`.
  - `"mobile data slow"` → `TOGGLE_DATA_SAVER` / `SET_NETWORK_MODE` → `SELF_SERVICE`.
- `bill_id` is empty string when not applicable; `charge_amount_usd` uses **two decimals**.

### 4.3 Incident Report Generation (`/emails/generate_reply`)
- **Input:** `client_complaint_email.txt` + `response_requirements.json`.
- **Output:** A full incident-report JSON (not a free-text email).
- **Key fields to extract or infer from the email/requirements:**
  - `incident_id`, `enterprise_account_id`, `product` (e.g., `monthly_export`).
  - `failure_window` with `start_date`, `end_date` (YYYY-MM-DD), and `failed_days` (integer).
  - `backfill_days` (integer), `sla_credit_percent` (integer).
  - `severity` enum: `Critical | High | Medium | Low`.
  - `engineering_owner` and `account_owner` as user IDs.
  - `channel_name`: **lowercase-hyphen** per naming-style requirement (e.g., `asteri-retail`).
  - `evidence_folder`: **client-date investigation** format.
  - `report_title`: **client export failure report** format.
  - `share_permissions`: ordered **exactly** as listed in `permission_users_to_include` (`laura.brown`, then `jun.chen`, etc.).
  - `response_status` enum: `READY_TO_SEND | NEEDS_FINANCE_REVIEW | NEEDS_ENGINEERING_REVIEW | UNDER_INVESTIGATION`.

### 4.4 Queue Rebalance / Enrich (`/queue/rebalance` or `/queue/enrich`)
- **Input:** `queue_snapshot.csv` (ticket_id, account_id, reported_service_type, queue_note).
- **Output:** `ticket_decisions` (preserve payload order) + `queue_summary` (counts per `final_resolution_status` and `route_team`).
- **Mapping hints:**
  - `"No matching account in intake"` → `INVALID_ACCOUNT`, `FAILED`, `NONE`, `diagnostic_required: false`.
  - `"Provisioning mismatch after move"` → `PROVISIONING_STALE`, `ESCALATED`, `TIER2_SUPPORT`, `diagnostic_required: true`.
  - `"Backbone capacity errors"` → `NETWORK_CAPACITY`, `ESCALATED`, `NETWORK_ENGINEERING`.
  - `"Suspended after overdue notice"` → `OVERDUE_SUSPENSION`, `PENDING_ACTION`, `ACCOUNTS_PAYABLE`.
  - `"Authentication never recovered"` → `AUTH_FAILED`, `ESCALATED`, `TIER2_SUPPORT`.
  - `"Voice profile drops calls"` → `PROVISIONING_STALE`, `ESCALATED`, `TIER2_SUPPORT`.
  - `"Neighborhood service interruption"` → `ACTIVE_OUTAGE`, `ESCALATED` or `PENDING_ACTION`, `NETWORK_ENGINEERING`.
- Ensure `queue_summary` totals are **consistent** with the decision list.

### 4.5 Mobile Data Refuel (`/cases/bulk_refuel`)
- **Input:** `mobile_data_worklist.json` (cases + optional `customer_preferences`).
- **Output:** `case_decisions` (ascending `case_id`) + `worklist_summary`.
- **Mapping hints:**
  - `"Data stopped after usage limit"` + accepted refuel in preferences → `REFUEL_DATA`, `final_route: DATA_RECOVERY`.
  - `"Traveler … roaming … no data"` → `ENABLE_LINE_ROAMING` / `TOGGLE_ROAMING` → `CARRIER_UPDATE`.
  - `"Slow data and data-saver icon visible"` → `TOGGLE_DATA_SAVER` → `DEVICE_SETTING_FIX`.
  - `"Slow data on older network mode"` → `SET_NETWORK_MODE` → `DEVICE_SETTING_FIX`.
  - `"No data after settings change"` → likely `TOGGLE_MOBILE_DATA` or `DISCONNECT_VPN` before escalating; if ambiguous, `TRANSFER_HUMAN` / `HUMAN_TRANSFER` is a fallback.
- `data_refuel_gb`: **one decimal** (e.g., `2.0`).
- `charge_amount_usd`: **two decimals** (e.g., `10.00`).
- `carrier_update_required`: `true` when the action triggers a carrier-side change (e.g., `ENABLE_LINE_ROAMING`).
- `worklist_summary` must sum up `data_refuel_cases`, `carrier_updates`, `device_setting_fixes`, `human_transfers`, and `total_estimated_customer_charge_usd` (two decimals).

## 5. Sorting & Rounding Rules
- **Order:** ascending alphanumeric `case_id` or payload row order as explicitly required.
- **Decimals:**
  - One decimal place for `data_refuel_gb`.
  - Two decimal places for `charge_amount_usd` and `total_estimated_customer_charge_usd`.
  - Integer for all count/summary fields.
- **Dates:** Use `YYYY-MM-DD` format in incident report windows.

## 6. General Pitfalls
- **Schema mismatch:** Never hard-code a flat answer (e.g., `resolved_tickets` array) without re-reading the template; the expected schema can be nested decision objects.
- **Count mismatch:** Summary objects must always be derivable from the decision array; a manual mismatch is an automatic score penalty.
- **Missing empty fields:** If a field is not applicable, use the sentinel value (`""`, `0.0`, `false`, `NONE`) rather than omitting the key.
- **Enum case-sensitivity:** Copy enum values exactly as shown in the template (e.g., `Critical` not `critical`).
- **Email vs. structured report:** Task-003 looks like an email reply endpoint, but the answer template is a **structured incident report**. Do not return prose; return the JSON report.
