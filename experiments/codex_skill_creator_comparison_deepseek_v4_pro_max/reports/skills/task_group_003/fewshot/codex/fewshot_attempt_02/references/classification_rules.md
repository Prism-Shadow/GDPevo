# Classification Rules

Rules for mapping API evidence to template enum values. Apply in the order listed. Treat the API response fields as the ground truth for every classification.

## Ticket Resolution Status

| API Evidence | Status | Resolution Route |
|---|---|---|
| Ticket account resolves and diagnostics confirm fixable issues | RESOLVED | AUTO_TROUBLESHOOTING |
| Ticket account resolves but an active outage covers the reported service | PENDING_ACTION | OUTAGE_WAIT |
| Ticket account resolves, diagnostics show issues beyond auto-fix, requires field/physical work | ESCALATED | ESCALATION |
| Ticket account is missing, suspended, or authentication fails | FAILED | INELIGIBLE_ACCOUNT, INVALID_ACCOUNT, or AUTH_FAILED |

## Ticket Escalation Routing

| Condition | Escalation Team |
|---|---|
| Auto-troubleshooting resolved or outage pending | NONE |
| Physical line work or field dispatch required | FIELD_OPS |
| Backbone or network capacity problems | NETWORK_ENGINEERING |
| Stale provisioning or tier-2 config issues | TIER2_SUPPORT |
| Billing, overdue, or fraud hold | ACCOUNTS_PAYABLE |

## Ticket Diagnostic Flags

Set diagnostic_needed to true when diagnostics show measurable issues (latency, stability, bandwidth). Set the individual boolean flags (latency_issue, stability_issue, bandwidth_issue) based on the diagnostics response fields. When the ticket is blocked by an outage, invalid account, or auth failure, diagnostics are typically not needed — set all to false.

## Ticket Key Blockers (Queue Quality Reviews)

| Queue Note Pattern | Key Blocker |
|---|---|
| outage, service interruption, neighborhood | ACTIVE_OUTAGE |
| no matching account, invalid, bad account id | INVALID_ACCOUNT |
| authentication, auth, never recovered | AUTH_FAILED |
| overdue, suspended after, hold notice | OVERDUE_SUSPENSION |
| fraud, fraud suspension | FRAUD_SUSPENSION |
| capacity, backbone | NETWORK_CAPACITY |
| provisioning, stale, mismatch after move | PROVISIONING_STALE |
| drops calls, physical line, fault | PHYSICAL_LINE_FAULT |
| None of the above | NONE |

## Mobile Case Actions

Map the reported_issue and line/device records to actions:

| Reported Issue | API Evidence | Primary Action |
|---|---|---|
| no service after commute or movement | Line shows active, device OK | RESEAT_SIM |
| Line suspended, customer ready to pay | Bill shows overdue amount | SEND_PAYMENT_REQUEST |
| Traveling abroad, no mobile data | Phone roaming on but line roaming off | ENABLE_LINE_ROAMING |
| Traveling abroad, roaming data toggle off | Line roaming enabled, phone roaming off | TOGGLE_ROAMING |
| Messaging app cannot send photos | Messaging permissions missing | GRANT_MESSAGING_PERMISSION |
| Mobile data works but is slow | VPN connected | DISCONNECT_VPN |
| Slow data, data-saver icon visible | data_saver_on is true | TOGGLE_DATA_SAVER |
| Slow data on older network mode | network_mode set to older standard | SET_NETWORK_MODE |
| No data after settings change | mobile_data_on is false | TOGGLE_MOBILE_DATA |
| Data stopped after usage limit | Plan data cap reached | REFUEL_DATA |
| Wi-Fi calling issues | wifi_calling_on mismatch | TOGGLE_WIFI_CALLING |
| APN issues | apn_configured is false | RESET_APN_REBOOT |
| Line suspended, non-billing reason | Line status suspended, bill current | RESUME_LINE_REBOOT |
| Issue cannot be determined from records | Records show no anomalies | TRANSFER_HUMAN |
| No action needed | Self-resolving or informational | NO_ACTION |

**Secondary action:** Use NO_ACTION unless the primary action requires a follow-up. Common follow-ups:
- After SEND_PAYMENT_REQUEST, use RESUME_LINE_REBOOT as secondary (bill paid then resume line).
- When primary action resolves the issue completely, secondary is NO_ACTION.

## Mobile Permissions

Set permission based on which app permissions are needed:
- GRANT_MESSAGING_PERMISSION typically needs storage (for photo attachments).
- Most other actions need NONE.

## Mobile Route Assignment

| Scenario | Final Route |
|---|---|
| Any self-service action (SIM, toggle, setting, permission) | SELF_SERVICE |
| Billing-related (payment request, overdue) | BILLING_RECOVERY |
| Carrier-side change (line roaming enable) | CARRIER_UPDATE |
| Records show no actionable issue or complex problem | HUMAN_TRANSFER |

## Mobile-Data Recovery (Worklist)

Same action mapping as Mobile Case Actions, with additional data-specific rules:

- For REFUEL_DATA: use customer_preferences.accepted_refuel_gb for data_refuel_gb. Compute charge_amount_usd as refuel_gb times plan.refuel_cost_per_gb. Set final_route to DATA_RECOVERY.
- For ENABLE_LINE_ROAMING: set carrier_update_required to true, final_route to CARRIER_UPDATE.
- For device-side toggles (data saver, network mode, mobile data toggle, VPN disconnect): set final_route to DEVICE_SETTING_FIX.
- For cases that cannot be resolved from records: set final_route to HUMAN_TRANSFER.

## Enterprise Response Package

### Root Cause

Read the incident linked export-run failure reason and cross-reference with enterprise messages. Synthesize a concise category, e.g. stale credential after rotation, scheduler outage, disk capacity exceeded.

### Contributing Alert Issue

Check if any enterprise messages reference an alert that was archived or misrouted:
- If a relevant alert was archived/misrouted: ARCHIVED_ALERT_ROUTE
- If no alert evidence found: NONE
- If evidence is ambiguous: UNKNOWN

### Failure Window

Derive from export-run records linked to the incident. Look for consecutive failing runs. Include start_date, end_date (YYYY-MM-DD), and failed_days count.

### Backfill Days

Equal to failed_days unless the incident evidence indicates partial recovery or data loss beyond the window.

### SLA Credit Percent

Read from /api/enterprise/sla/{account_id}. Use the credit percentage tied to the incident severity tier.

### Severity

Read from the incident record severity field. Map to the enum: Critical, High, Medium, Low.

### Owners

- engineering_owner: from the incident record.
- account_owner: from the enterprise account record.

### Channel Name

Derive from the enterprise account channel_name field. Apply the naming style from response requirements (typically lowercase hyphen format).

### Evidence Folder and Report Title

Apply the naming conventions from response_requirements.naming_style:
- Evidence folder: client + date + Investigation
- Report title: client + Export Failure - Resolution Report

### Share Permissions

Use response_requirements.permission_users_to_include ordering. Default to view for the first user, edit for the second unless requirements specify otherwise.

### Response Status

| Condition | Status |
|---|---|
| SLA credit requires finance approval | NEEDS_FINANCE_REVIEW |
| Root cause uncertain or needs engineering sign-off | NEEDS_ENGINEERING_REVIEW |
| All evidence complete and reviewable | READY_TO_SEND |
| Evidence incomplete | UNDER_INVESTIGATION |
