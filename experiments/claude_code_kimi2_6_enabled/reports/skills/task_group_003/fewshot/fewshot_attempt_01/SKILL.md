# Task Group 003 – CRM Service Ticket & Case Resolution SOP

## 1. Input / Output Conventions
- The solver receives one or more payload files plus an `answer_template.json`. **Use the template schema exactly**; do not add or remove fields.
- **Preserve order**: arrays of decisions must follow the ascending order of `case_id` or `ticket_id` as they appear in the input payload, unless the template explicitly says otherwise.
- **Empty / default values**:
  - String fields that are not applicable → `""`
  - Numeric fields that are not applicable → `0.0`
  - Boolean fields that are not applicable → `false`
- **Summary blocks** (e.g., `batch_summary`, `queue_summary`, `worklist_summary`) must be derived directly from the decision array. Counts must be exact integers and keys must match the enums/status values defined in the template.
- **Enum casing**: use the exact uppercase, underscore-separated values shown in the template (e.g., `PENDING_ACTION`, `TIER2_SUPPORT`, `DEVICE_SETTING_FIX`).

## 2. Remote API Endpoints to Inspect
The environment exposes the following endpoints. Query them when the payload does not supply the needed state, or when the task explicitly requires live data.

| Method | Endpoint | Typical Use |
|--------|----------|-------------|
| GET | `/api/v1/outages/active` | Determine if a ticket is blocked by an active outage. |
| GET | `/api/v1/accounts/{account_id}/status` | Check holds, suspensions, or eligibility issues. |
| GET | `/api/v1/diagnostics/{ticket_id}` | Obtain latency, stability, bandwidth, or other diagnostic flags. |
| GET | `/api/v1/queue/snapshot` | Retrieve the full case queue when the provided payload is partial. |
| POST | `/api/v1/tickets/{ticket_id}/resolve` | Confirm auto-troubleshooting resolution. |
| POST | `/api/v1/tickets/{ticket_id}/escalate` | Submit escalation with target team. |
| POST | `/api/v1/cases/{case_id}/refuel` | Execute data refuel for depleted plans. |
| POST | `/api/v1/cases/{case_id}/update_roaming` | Enable roaming on a line. |
| GET | `/api/v1/cases/{case_id}/carrier_sync` | Verify whether a carrier re-sync is required. |
| GET | `/api/v1/alerts?channel={channel_name}` | Pull contributing alert issues for incident reports. |
| GET | `/api/v1/users/{user_id}/permissions` | Look up user permissions for share lists. |
| POST | `/api/v1/incidents/{incident_id}/report` | Submit formal incident reports. |

**Caution**: Do not perform exhaustive brute-force scans. Prefer the endpoints named above and only call what the current sub-task requires.

## 3. Decision Rules by Sub-Task Type

### 3.1 Internet / Video Ticket Batch (ticket_decisions + batch_summary)
1. **Account status gate** – If the account is on hold, suspended, or otherwise ineligible, set `final_resolution_status` to `FAILED`, `resolution_route` to `INELIGIBLE_ACCOUNT`, all issue flags to `false`, and `diagnostic_needed` to `false`.
2. **Outage check** – If an active outage matches the service type / region, set `final_resolution_status` to `PENDING_ACTION`, `resolution_route` to `OUTAGE_WAIT`, populate `outage_id`, and set all issue flags / `diagnostic_needed` to `false`.
3. **Diagnostics** – For remaining tickets, call `/api/v1/diagnostics/{ticket_id}`. If latency, stability, or bandwidth issues are reported, set the corresponding boolean flags to `true` and `diagnostic_needed` to `true`.
4. **Resolution vs. Escalation**:
   - Resolvable issues → `RESOLVED`, `resolution_route`: `AUTO_TROUBLESHOOTING`.
   - Physical line work / field issues → `ESCALATED`, `escalation_team`: `FIELD_OPS`.
   - Network capacity limits → `ESCALATED`, `escalation_team`: `NETWORK_ENGINEERING`.
   - Provisioning stale data → `ESCALATED`, `escalation_team`: `TIER2_SUPPORT`.
5. `diagnostic_needed` is `true` for `RESOLVED` and `ESCALATED`, `false` for `FAILED` and `PENDING_ACTION`.

### 3.2 Queue Snapshot Ticket Routing (ticket_decisions + queue_summary)
- `key_blocker` and `route_team` are determined by the same hierarchy as §3.1, but expressed as blockers:
  - `ACTIVE_OUTAGE` → `PENDING_ACTION`
  - `INVALID_ACCOUNT` or `AUTH_FAILED` → `FAILED` (`route_team`: `NONE`)
  - `OVERDUE_SUSPENSION` or `FRAUD_SUSPENSION` → `FAILED` (`route_team`: `ACCOUNTS_PAYABLE`)
  - `NETWORK_CAPACITY` → `ESCALATED` (`route_team`: `NETWORK_ENGINEERING`)
  - `PROVISIONING_STALE` → `ESCALATED` (`route_team`: `TIER2_SUPPORT`)
  - `PHYSICAL_LINE_FAULT` → `ESCALATED` (`route_team`: `FIELD_OPS`)
  - `BILLING_DISPUTE` → `FAILED` (`route_team`: `NONE`) unless overridden by account status.
  - `NONE` → `RESOLVED` (`route_team`: `NONE`)
- `diagnostic_required` follows the same rule: `true` for `RESOLVED` and `ESCALATED`, otherwise `false`.
- Summary counts must include every enum value listed in the template (e.g., `FAILED`, `PENDING_ACTION`, `RESOLVED`, `ESCALATED`, plus each `route_team` count).

### 3.3 Mobile Support Case Decisions (case_decisions + queue_summary)
Map the reported issue text to the action pair:
- **No service after commute / physical SIM issue** → primary: `RESEAT_SIM`, final_route: `SELF_SERVICE`.
- **Suspended line with overdue bill** → primary: `SEND_PAYMENT_REQUEST`, secondary: `RESUME_LINE_REBOOT`, `bill_id` from account, `charge_amount_usd` from bill total, final_route: `BILLING_RECOVERY`.
- **Traveling abroad, no data** → primary: `TOGGLE_ROAMING`, final_route: `SELF_SERVICE`.
- **Messaging app cannot send media** → primary: `GRANT_MESSAGING_PERMISSION`, `permission`: `storage` (or `sms_and_storage` if both are missing), final_route: `SELF_SERVICE`.
- **Slow data with VPN suspected** → primary: `DISCONNECT_VPN`, final_route: `SELF_SERVICE`.
- `secondary_action` is `NO_ACTION` unless the template or billing flow demands a secondary step.
- `charge_amount_usd` is `0.0` except for billing-recovery cases.

### 3.4 Mobile Data Worklist (case_decisions + worklist_summary)
Use the structured fields in the worklist JSON plus `customer_preferences`:
- **Data depleted** (`data_usage_mb` ≥ `plan_allowance_mb`) and customer accepted refuel → primary: `REFUEL_DATA`, `data_refuel_gb`: accepted value (one decimal), `charge_amount_usd`: `data_refuel_gb × 2.00`, `carrier_update_required`: `false`, final_route: `DATA_RECOVERY`.
- **Roaming enabled but no data** → primary: `ENABLE_LINE_ROAMING`, `carrier_update_required`: `true`, final_route: `CARRIER_UPDATE`.
- **Data-saver icon visible / slow data** → primary: `TOGGLE_DATA_SAVER`, final_route: `DEVICE_SETTING_FIX`.
- **Older network mode** → primary: `SET_NETWORK_MODE`, final_route: `DEVICE_SETTING_FIX`.
- **Mobile data toggled off** → primary: `TOGGLE_MOBILE_DATA`, final_route: `DEVICE_SETTING_FIX`.
- `secondary_action` is normally `NO_ACTION`.
- `carrier_update_required` is `true` only for carrier/roaming sync issues.
- Summary totals:
  - `data_refuel_cases` = count of `DATA_RECOVERY`
  - `carrier_updates` = count of `CARRIER_UPDATE`
  - `device_setting_fixes` = count of `DEVICE_SETTING_FIX`
  - `human_transfers` = count of `HUMAN_TRANSFER`
  - `total_estimated_customer_charge_usd` = sum of all `charge_amount_usd` (two-decimal numeric).

### 3.5 Enterprise Incident Report (single structured JSON)
- Extract `incident_id` from the email subject/body (pattern `INC-####`).
- `enterprise_account_id` and owner names (`engineering_owner`, `account_owner`) come from the account record or API (`/api/v1/accounts/{id}`).
- `root_cause_category` and `contributing_alert_issue` come from alert/diagnostic APIs (`/api/v1/alerts?channel={channel_name}`).
- `failure_window`:
  - `start_date` and `end_date` are inclusive ISO dates.
  - `failed_days` = inclusive count (e.g., 2026-05-12 to 2026-05-14 → `3`).
- `backfill_days` = `failed_days`.
- `sla_credit_percent` follows the enterprise SLA table (e.g., 15 for a 3-day multi-day outage).
- `severity` for multi-day blocked enterprise exports is `Critical`.
- `channel_name`: lowercase, hyphenated version of the client name (e.g., `Asteri Retail Inc.` → `asteri-retail-inc`).
- `evidence_folder`: `{Client Name} {Month} {Year} Investigation`.
- `report_title`: `{Client Name} Export Failure - Resolution Report` (adapt noun if the product differs).
- `share_permissions`: include every user listed in `response_requirements.json` with the specified permission level (`view` or `edit`).
- `response_status`: `NEEDS_FINANCE_REVIEW` whenever an SLA credit is applied.

## 4. Sorting & Rounding
- **Ordering**: Keep the natural ascending order of IDs as provided in the input payload. Do not reorder by priority score or timestamp unless explicitly instructed.
- **Numbers**:
  - `data_refuel_gb` → numeric, typically one decimal (e.g., `2.0`, `0.0`).
  - `charge_amount_usd` → numeric, two-decimal precision in business terms (e.g., `4.0` or `86.4` are acceptable JSON numbers; compute precisely and let JSON serialization handle trailing zeros).
  - Summary counts → plain integers.
- **Dates**: Use ISO-8601 calendar dates (`YYYY-MM-DD`) for report windows; use full ISO timestamps only when the template requests them.

## 5. Common Pitfalls
- **Guessing file names**: Only read the files that are explicitly provided in the attempt directory. Do not invent alternate paths.
- **Incomplete payloads**: If the provided queue snapshot or worklist appears to have fewer records than expected, fetch the live source via `/api/v1/queue/snapshot` or the relevant case endpoint rather than hallucinating missing rows.
- **Mismatching summary counts**: Always re-derive summary objects from the decision array in a final pass. A manual count that drifts from the array will fail validation.
- **Escalation team leakage**: For `FAILED` and `PENDING_ACTION` tickets, keep `route_team` as `NONE` unless a specific payable / collections team is required (e.g., `ACCOUNTS_PAYABLE` for overdue suspension).
- **Enum drift**: Copy enum values verbatim from the template. Typos such as `Pending_Action` or `Tier2_Support` will be rejected.
