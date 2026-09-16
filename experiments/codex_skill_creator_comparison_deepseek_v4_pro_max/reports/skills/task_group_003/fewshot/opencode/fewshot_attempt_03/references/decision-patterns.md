# Decision Patterns

Reusable decision rules for each telecom support domain. These patterns map API evidence to the fields and enums in task answer templates. Apply them per-item and then aggregate the summaries.

---

## Domain 1: Service Ticket Resolution

Applies to tasks with ticket batches (CSV or similar) and answer templates containing `ticket_decisions` with fields like `final_resolution_status`, `diagnostic_needed`, `latency_issue`, `stability_issue`, `bandwidth_issue`, `outage_id`, `escalation_team`, `resolution_route`, and `batch_summary`.

### Decision Order

For each ticket, evaluate in this sequence. Stop at the first rule that produces a final determination.

#### 1. Account Eligibility Gate

Look up the account via `/api/accounts/{account_id}` from the ticket.

- **404 or account doesn't exist:** The ticket is FAILED, resolution_route = INELIGIBLE_ACCOUNT or INVALID_ACCOUNT (choose the enum value present in the template). escalation_team = NONE. Skip all further checks.
- **Account exists but `authentication.last_login_status` is FAILED or LOCKED:** The ticket is FAILED, resolution_route = AUTH_FAILED. escalation_team = NONE. Skip further checks.
- **Account `status` is "Suspended" or "Hold":** The ticket is FAILED, resolution_route = INELIGIBLE_ACCOUNT. escalation_team = ACCOUNTS_PAYABLE (if the template includes team routing). Skip further checks.

#### 2. Outage Matching

Compare the ticket's `service_area` and `service_type` against the active outages list from `/api/outages`.

- **Match found (same service_area AND ticket's service_type is in outage's service_types array AND outage is active):** The ticket is PENDING_ACTION, resolution_route = OUTAGE_WAIT. outage_id = the matched outage's ID. escalation_team = NONE. All issue flags (latency, stability, bandwidth) = false. diagnostic_needed = false. Stop here.
- **No match:** Continue to step 3.

#### 3. Diagnostics and Escalation

For internet and video tickets, fetch `/api/diagnostics/{ticket_id}`.

- **If diagnostics record exists:** Set issue flags from thresholds:
  - `latency_issue` = true if `latency_ms` > 100
  - `stability_issue` = true if `jitter_ms` > 30
  - `bandwidth_issue` = true if `bandwidth_mbps` < 0.8 * `subscribed_mbps`
  - `diagnostic_needed` = true

- Then check `/api/troubleshooting/{ticket_id}`:
  - **Troubleshooting exists AND post-repair metrics are healthy** (post_latency < 100, post_jitter < 30, post_bandwidth >= 80% subscribed): RESOLVED, resolution_route = AUTO_TROUBLESHOOTING. escalation_team = NONE.
  - **Troubleshooting exists but post-repair metrics are still degraded:** ESCALATED based on root cause (see escalation mapping below).
  - **No troubleshooting record:** ESCALATED based on root cause from diagnostics.

#### 4. Escalation Mapping from Root Causes

Map diagnostic `root_causes` values to escalation teams:

- `CONFIGURATION_DRIFT` -> TIER2_SUPPORT (auto-troubleshooting usually handles this; escalate only if troubleshooting failed)
- `PHYSICAL_LINE_FAULT` -> FIELD_OPS
- `NETWORK_CAPACITY` -> NETWORK_ENGINEERING
- `PROVISIONING_STALE` -> TIER2_SUPPORT

For queue-quality tasks that use `key_blocker` instead of root causes directly, map:
- `CONFIGURATION_DRIFT` -> NONE (troubleshooting resolves it)
- `PHYSICAL_LINE_FAULT` -> PHYSICAL_LINE_FAULT
- `NETWORK_CAPACITY` -> NETWORK_CAPACITY
- `PROVISIONING_STALE` -> PROVISIONING_STALE
- Account issues map to INVALID_ACCOUNT, AUTH_FAILED, OVERDUE_SUSPENSION, or FRAUD_SUSPENSION

---

## Domain 2: Contact-Center Case Routing

Applies to tasks with case queues and answer templates containing `case_decisions` with `primary_action`, `secondary_action`, `permission`, `bill_id`, `charge_amount_usd`, `final_route`, and `queue_summary`.

### Decision Order

For each case, resolve the full entity chain first (case -> customer -> line -> device -> plan -> bills), then determine the action.

#### Case Types and Primary Decision Paths

**Case where the issue involves no service and the device shows `sim_status: "missing"`:**
- primary_action = RESEAT_SIM
- secondary_action = NO_ACTION
- final_route = SELF_SERVICE

**Case where the line is suspended (`status: "Suspended"`, `suspension_reason: "OVERDUE_BILL"`):**
- primary_action = SEND_PAYMENT_REQUEST
- secondary_action = RESUME_LINE_REBOOT
- Find the customer's overdue bill to populate `bill_id` and `charge_amount_usd`
- final_route = BILLING_RECOVERY

**Case where the customer is abroad and can't use mobile data:**
- Check device: if `phone_roaming_enabled` is false but the line has `roaming_enabled: true`, primary_action = TOGGLE_ROAMING (device-side fix, self-service)
- If the line has `roaming_enabled: false`, primary_action = ENABLE_LINE_ROAMING (carrier-side, requires carrier update)
- final_route = SELF_SERVICE (device toggle) or CARRIER_UPDATE (line enable)

**Case where MMS/photos can't be sent:**
- Check device `messaging_permissions.storage`: if false, primary_action = GRANT_MESSAGING_PERMISSION, permission = "storage"
- If `can_send_mms` is false or `mmsc_url_present` is false, the issue is carrier-level -> TRANSFER_HUMAN
- final_route = SELF_SERVICE (permission grant) or HUMAN_TRANSFER

**Case where mobile data is slow:**
- Check device in order:
  - `vpn_connected: true` -> DISCONNECT_VPN
  - `data_saver_mode: true` -> TOGGLE_DATA_SAVER
  - `network_mode_preference` set to older mode (e.g., "3g_only") -> SET_NETWORK_MODE
  - `mobile_data_enabled: false` -> TOGGLE_MOBILE_DATA
  - `airplane_mode: true` -> TOGGLE_AIRPLANE_MODE
- final_route = SELF_SERVICE

**Fallback:** If no clear device/line signal matches, use TRANSFER_HUMAN.

#### Permission Field

Set `permission` only when the action requires it:
- GRANT_MESSAGING_PERMISSION -> set `permission` to the specific permission needed ("sms", "storage", or "sms_and_storage")
- All other actions -> "NONE"

---

## Domain 3: Enterprise Export Incident Response

Applies to tasks with a complaint email/requirements and answer templates containing fields like `incident_id`, `enterprise_account_id`, `root_cause_category`, `contributing_alert_issue`, `failure_window`, `backfill_days`, `sla_credit_percent`, `severity`, `engineering_owner`, `account_owner`, `channel_name`, `evidence_folder`, `report_title`, `share_permissions`, `response_status`.

### Evidence Gathering Order

1. Fetch incident via `/api/enterprise/incidents/{incident_id}` to get severity, owners, account reference
2. Fetch enterprise account via `/api/enterprise/accounts/{enterprise_account_id}` to get name, finance_owner
3. Fetch export runs (filter by account and incident) to determine failure window and root cause
4. Fetch messages (filter by incident-related channels/authors) for root cause narrative and alert context
5. Fetch SLA contract via `/api/enterprise/sla/{enterprise_account_id}` for credit percent

### Determining Each Field

**`root_cause_category`:** Derived from export-run `failure_code` values combined with message context:
- `STALE_CREDENTIAL` -> "stale credential after rotation" or similar credential-based description
- `BUCKET_QUOTA` -> "bucket quota exceeded" or similar quota-based description

**`contributing_alert_issue`:** Check messages for any in `export-alerts-archive` channel:
- If messages exist in that channel that relate to the incident -> ARCHIVED_ALERT_ROUTE
- Otherwise -> NONE

**`failure_window`:**
- Sort failed export runs by `run_date`
- `start_date` = earliest failed run date
- `end_date` = latest failed run date
- `failed_days` = count of consecutive failing days (if there are gaps, count only the contiguous failing block)

**`backfill_days`:** Equal to `failed_days` when a succeeding run exists after the failure window. If no success follows, backfill may not be available.

**`sla_credit_percent`:** From the SLA endpoint's `monthly_export_credit_percent`. Use the value as-is.

**`severity`:** From the incident record directly.

**`engineering_owner` / `account_owner`:** From the incident record directly.

**`channel_name`:** When naming conventions say "lowercase hyphen channel": take the account name, lowercase it, replace spaces with hyphens.

**`evidence_folder`:** When naming conventions say "client-date investigation folder": "{Account Name} {Month Year} Investigation".

**`report_title`:** When naming conventions say "client export failure report title": "{Account Name} Export Failure - Resolution Report".

**`share_permissions`:**
- Include every user listed in the task's permission_users_to_include
- Assign permissions: typically the finance owner gets "view", others may get "edit" or "view" depending on their relationship to the response
- Order by user as listed in the requirements

**`response_status`:**
- If `sla_credit_percent` > 0 -> NEEDS_FINANCE_REVIEW
- If root cause uncertain -> UNDER_INVESTIGATION
- If engineering analysis needed -> NEEDS_ENGINEERING_REVIEW
- If all clear -> READY_TO_SEND

---

## Domain 4: Queue-Quality Classification

Applies to tasks with queue snapshots (CSV) and answer templates containing `ticket_decisions` with `final_resolution_status`, `route_team`, `key_blocker`, `diagnostic_required`, and `queue_summary` broken down by resolution status and route teams.

### Decision Order

For each ticket, the logic follows Domain 1 but uses `key_blocker` and `route_team` instead of `resolution_route` and `escalation_team`.

#### Account Validation

- **Account doesn't exist (404 or bogus account_id):** FAILED, key_blocker = INVALID_ACCOUNT, route_team = NONE
- **Account authentication failed:** FAILED, key_blocker = AUTH_FAILED, route_team = NONE
- **Account suspended:** FAILED, key_blocker = OVERDUE_SUSPENSION (or FRAUD_SUSPENSION), route_team = ACCOUNTS_PAYABLE

#### Outage Match

- **Active outage matches ticket's service_area + service_type:** PENDING_ACTION, key_blocker = ACTIVE_OUTAGE, route_team = NONE

#### Diagnostics and Escalation

- **Ticket has diagnostics record:** Set `diagnostic_required = true` for internet/video tickets
- **Troubleshooting resolves the issue:** RESOLVED, key_blocker = NONE, route_team = NONE
- **Root cause requires escalation:** Map root cause to key_blocker and route_team (see escalation mapping in Domain 1)

#### Summary Aggregation

Count each status and route team across all tickets for the `queue_summary`.

---

## Domain 5: Mobile-Data Recovery

Applies to tasks with worklists (JSON) and answer templates containing `case_decisions` with `primary_action`, `secondary_action`, `data_refuel_gb`, `charge_amount_usd`, `carrier_update_required`, `final_route`, and `worklist_summary`.

### Decision Logic

For each case, fetch the line, device, and plan records from the API. Then evaluate:

**Data stopped after usage limit:**
- Compare `data_used_gb` on the line to `data_limit_gb` on the plan
- If usage exceeds or meets the limit: primary_action = REFUEL_DATA
- Determine `data_refuel_gb` from customer preferences if provided; otherwise use the amount needed to cover the gap
- `charge_amount_usd` = `data_refuel_gb` * `data_refueling_price_per_gb`
- final_route = DATA_RECOVERY

**Traveler has roaming on phone but no data:**
- Check line `roaming_enabled`: if false, primary_action = ENABLE_LINE_ROAMING, carrier_update_required = true, final_route = CARRIER_UPDATE
- If line roaming is on but device `phone_roaming_enabled` is off: primary_action = TOGGLE_ROAMING, final_route = DEVICE_SETTING_FIX

**Data slow and data-saver icon visible:**
- primary_action = TOGGLE_DATA_SAVER, final_route = DEVICE_SETTING_FIX

**Data slow on older network mode:**
- primary_action = SET_NETWORK_MODE, final_route = DEVICE_SETTING_FIX

**No data after settings change:**
- Check device: if `mobile_data_enabled` is false -> TOGGLE_MOBILE_DATA, final_route = DEVICE_SETTING_FIX
- If device settings look normal but data still stopped -> check VPN, airplane mode, signal strength in order; escalate to TRANSFER_HUMAN if nothing matches

### Charge Calculation

Only non-zero for REFUEL_DATA actions:
- `charge_amount_usd` = `data_refuel_gb` * plan's `data_refueling_price_per_gb`
- Round to two decimal places

---

## Cross-Cutting Rules

### API Call Order

Always fetch collections first when parallel resolution is more efficient (e.g., fetch all outages once for all tickets). For individual lookups, use the item's entity ID chain rather than scanning full collection responses.

### Parallel Lookups

When processing a batch, parallelize independent API calls:
- All individual ticket/case/incident records can be fetched in parallel
- Outages and plans collections can be fetched once and cached for all items
- After entity IDs are known, account/customer/line/device lookups can be parallelized per item

### Numeric Precision

- `charge_amount_usd`: always two decimal places (e.g., 4.00 not 4.0)
- `data_refuel_gb`: one decimal place (e.g., 2.0 not 2)
- Percentages: integer (e.g., 15, not 15%)

### Default Values

When a field is not applicable:
- String fields: empty string `""`
- Boolean fields: `false`
- Numeric fields: `0` or `0.0` as appropriate
- Enum fields: use the template's `NONE` variant when available

### Summary Calculations

After resolving all individual items, compute the summary by counting each outcome category across all items. The summary must be internally consistent with the individual decisions (e.g., the sum of per-status counts in the summary must equal the total number of items).
