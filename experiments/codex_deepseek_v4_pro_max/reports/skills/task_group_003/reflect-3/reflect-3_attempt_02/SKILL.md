 # Support Console Resolution Skill

 ## Overview
 Resolve structured support-console tasks by querying a REST API, cross-referencing records across domains (accounts, tickets, diagnostics, outages, lines, devices, plans, bills, enterprise data), and producing JSON answers that conform to a provided answer template.

 ## Core Workflow
 1. Read all supplied payloads (CSV, JSON, text) and the answer template.
 2. Replace `<TASK_ENV_BASE_URL>` with the environment base URL and query every relevant API endpoint for each entity in the payload.
 3. Cross-reference records: for every ticket/case/incident, pull its account, diagnostics, line, device, plan, bill, outage, export-run, message, and SLA data.
 4. Classify each entity using the decision rules below, then populate the answer template fields exactly as specified.
 5. Compute aggregate summaries from the per-entity decisions.

 ## API Endpoints Reference
 Always query endpoints in parallel where possible. The catalog at `/api/catalog` lists available endpoints and record counts.

 ### Ticket-domain endpoints
 - `GET /api/tickets/{ticket_id}` — ticket details including account_id, service_area, service_type, subscribed_mbps, status.
 - `GET /api/accounts/{account_id}` — account status (Active / Suspended), authentication info, tier.
 - `GET /api/diagnostics/{ticket_id}` — bandwidth_mbps, latency_ms, jitter_ms, root_causes list.
 - `GET /api/troubleshooting/{ticket_id}` — post-troubleshooting metrics, steps taken, completion status.
 - `GET /api/outages` — list of outages; filter by service_area and active=true.

 ### Case-domain endpoints
 - `GET /api/cases/{case_id}` — case details including customer_id, line_id, device_id, issue_type.
 - `GET /api/lines/{line_id}` — line status, roaming_enabled, data_used_gb, plan_id, suspension_reason.
 - `GET /api/devices/{device_id}` — device state: sim_status, mobile_data_enabled, data_saver_mode, network_mode_preference, phone_roaming_enabled, vpn_connected, airplane_mode, messaging_permissions, can_send_mms, signal_strength, speed_test.
 - `GET /api/plans/{plan_id}` — data_limit_gb, data_refueling_price_per_gb, monthly_price_usd.
 - `GET /api/bills` — filter by customer_id for amount_due_usd, status (Paid / Overdue).
 - `GET /api/customers/{customer_id}` — customer status.

 ### Enterprise-domain endpoints
 - `GET /api/enterprise/incidents/{incident_id}` — severity, status, product, engineering_owner, account_owner, enterprise_account_id.
 - `GET /api/enterprise/accounts/{account_id}` — name, tier, account_owner, finance_owner.
 - `GET /api/enterprise/export-runs` — filter by enterprise_account_id or incident_id; collect run_date, status (FAILED / SUCCEEDED), failure_code.
 - `GET /api/enterprise/messages` — filter by incident reference in body or message_id; extract author, channel, body.
 - `GET /api/enterprise/sla/{enterprise_account_id}` — credit_trigger, credit_percent.

 ## Decision Rules: Tickets

 ### final_resolution_status
 Determine by priority:
 1. If account is Suspended → FAILED.
 2. If account not found (404) → FAILED.
 3. If an active outage covers the ticket's service_area and service_type → PENDING_ACTION.
 4. If diagnostics show a physical root cause (FIBER_DROP_DAMAGE, SIGNAL_LOSS, PHYSICAL_LINE_FAULT) → ESCALATED.
 5. If diagnostics show BACKBONE_CAPACITY → ESCALATED.
 6. If diagnostics show PROVISIONING_STALE or VOICE_PROFILE_STALE → ESCALATED.
 7. If diagnostics show CONFIGURATION_DRIFT and troubleshooting completed with improved metrics → RESOLVED.
 8. If account authentication shows FAILURE → FAILED.
 9. Otherwise → evaluate based on available evidence.

 ### resolution_route (or final_route)
 - AUTO_TROUBLESHOOTING: diagnostics show a software-config issue with successful troubleshooting.
 - OUTAGE_WAIT: an active outage covers the service area and service type.
 - ESCALATION: a physical or capacity issue requiring a specialized team.
 - INELIGIBLE_ACCOUNT: account is Suspended.
 - AUTH_FAILED: account authentication failure.
 - INVALID_ACCOUNT: account ID returns 404.

 ### escalation_team (or route_team)
 - FIELD_OPS: FIBER_DROP_DAMAGE, SIGNAL_LOSS, PHYSICAL_LINE_FAULT.
 - NETWORK_ENGINEERING: BACKBONE_CAPACITY, NETWORK_CAPACITY.
 - TIER2_SUPPORT: PROVISIONING_STALE, VOICE_PROFILE_STALE, CONFIGURATION_DRIFT.
 - ACCOUNTS_PAYABLE: OVERDUE_SUSPENSION, suspended accounts with overdue bills.
 - NONE: when no escalation applies (outage wait, auto-resolved, invalid account, auth failed).

 ### key_blocker (queue-quality tasks)
 Map diagnostic root causes and account state to the blocker enum:
 - ACTIVE_OUTAGE: active outage in service area.
 - INVALID_ACCOUNT: account 404.
 - AUTH_FAILED: account authentication failure.
 - OVERDUE_SUSPENSION: account Suspended with overdue bill.
 - NETWORK_CAPACITY: BACKBONE_CAPACITY root cause.
 - PROVISIONING_STALE: PROVISIONING_STALE or VOICE_PROFILE_STALE root cause.
 - PHYSICAL_LINE_FAULT: FIBER_DROP_DAMAGE or SIGNAL_LOSS root cause.
 - NONE: no clear blocker identified.

 ### diagnostic_needed / diagnostic_required
 Set true when diagnostics reveal a non-generated root cause (i.e., not GENERATED_NOISE) that informs the resolution. Set false when the blocker is obvious without diagnostics (active outage, invalid account, auth failure, account suspension).

 ### Issue flags (latency_issue, bandwidth_issue, stability_issue)
 - latency_issue: true when latency_ms exceeds ~100ms.
 - bandwidth_issue: true when bandwidth_mbps is materially below subscribed_mbps (roughly < 75%).
 - stability_issue: true when root causes indicate intermittent faults, packet loss, or physical line damage.

 ## Decision Rules: Mobile Cases

 ### Primary action selection
 Inspect device state in this priority order:
 1. sim_status = "missing" → RESEAT_SIM.
 2. Line status = "Suspended" + bill Overdue → SEND_PAYMENT_REQUEST.
 3. mobile_data_enabled = false → TOGGLE_MOBILE_DATA.
 4. Customer abroad + line roaming_enabled = false → ENABLE_LINE_ROAMING.
 5. Customer abroad + phone_roaming_enabled = false → TOGGLE_ROAMING.
 6. data_used_gb > plan data_limit_gb → REFUEL_DATA (use customer_preferences for GB amount).
 7. data_saver_mode = true → TOGGLE_DATA_SAVER.
 8. network_mode_preference is a slow mode (e.g., "3g_only") → SET_NETWORK_MODE.
 9. vpn_connected = true + slow data → DISCONNECT_VPN.
 10. can_send_mms = false or storage permission missing → GRANT_MESSAGING_PERMISSION.
 11. airplane_mode = true → TOGGLE_AIRPLANE_MODE.

 ### Secondary action
 After the primary action, determine if a follow-up is needed:
 - After RESEAT_SIM → TOGGLE_AIRPLANE_MODE (re-register on network).
 - After SEND_PAYMENT_REQUEST → RESUME_LINE_REBOOT.
 - Otherwise → NO_ACTION unless another device issue is present.

 ### Route determination (final_route)
 - DATA_RECOVERY: REFUEL_DATA action.
 - CARRIER_UPDATE: ENABLE_LINE_ROAMING or any action requiring carrier-side change.
 - DEVICE_SETTING_FIX: TOGGLE_MOBILE_DATA, TOGGLE_ROAMING, TOGGLE_DATA_SAVER, SET_NETWORK_MODE, DISCONNECT_VPN.
 - BILLING_RECOVERY: SEND_PAYMENT_REQUEST.
 - SELF_SERVICE: RESEAT_SIM, TOGGLE_AIRPLANE_MODE, GRANT_MESSAGING_PERMISSION.
 - HUMAN_TRANSFER: when no automated action applies.

 ### Permission
 - "storage": when messaging_permissions.storage is false and MMS is required.
 - "sms": when messaging_permissions.sms is false.
 - "sms_and_storage": when both are missing.
 - "NONE": otherwise.

 ### Charge calculation
 - For REFUEL_DATA: charge = data_refuel_gb × plan's data_refueling_price_per_gb.
 - For SEND_PAYMENT_REQUEST: charge = bill's amount_due_usd.
 - Otherwise: 0.00.

 ## Decision Rules: Enterprise Incidents

 ### Root cause
 Concatenate the failure_code from failed export runs with message body context. Use a concise category like "stale credential", "quota exceeded", "pipeline timeout".

 ### Failure window
 From export runs: collect all FAILED run_dates. start_date = earliest, end_date = latest, failed_days = count of distinct failed dates.

 ### Backfill days
 Equal to the number of distinct failed dates (failed_days).

 ### SLA credit
 From `/api/enterprise/sla/{enterprise_account_id}`. Look for the relevant product credit_percent.

 ### Contributing alert issue
 - ARCHIVED_ALERT_ROUTE: when the diagnostic message's channel name contains "archive".
 - NONE: when no alert routing issue is evident.
 - UNKNOWN: when evidence is insufficient but an alert issue is suspected.

 ### Owners
 - engineering_owner: from incident record.
 - account_owner: from incident or enterprise account record.

 ### Channel / evidence / report naming
 Follow the naming convention described in the task requirements:
 - Channel: the channel where the root-cause message was posted (lowercase-hyphen format).
 - Evidence folder: `{client-name-lowercase}-{start-date}-investigation`.
 - Report title: `{Client Name} Export Failure Report` in title case.

 ### Share permissions
 Include each user listed in requirements. Default permission is "view" unless the user is a finance owner requiring "edit". Order by the listing in requirements.

 ### Response status
 - READY_TO_SEND: all evidence gathered, SLA credit known, owners identified.
 - NEEDS_FINANCE_REVIEW: SLA credit requires finance sign-off.
 - UNDER_INVESTIGATION: incident status is still open.

 ## Summary Aggregation
 - Count each unique value in the per-entity decisions to populate summary objects.
 - For monetary totals, sum all charge_amount_usd across all entities.
 - Ensure summary counts match the per-entity classifications exactly.
 - Preserve payload order for entity arrays in the output.

 ## Important Constraints
 - Never invent data; derive every value from API responses or supplied payloads.
 - When an API returns GENERATED_NOISE as a root cause, treat it as non-diagnostic (no actionable root cause identified).
 - Handle 404 responses gracefully: an account not found means INVALID_ACCOUNT / FAILED.
 - All string values in the answer must match the exact enum values from the answer template.
 - All numeric values must use the precision specified in the template (e.g., two decimals for USD, one decimal for GB).
 - Answer only with the populated JSON template; no explanatory text.
