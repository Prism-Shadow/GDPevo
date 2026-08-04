 # Support Console Analyst Skill

 ## Overview
 Solve support-console triage and resolution tasks by querying a REST API and producing structured JSON answers. The API exposes accounts, tickets, cases, diagnostics, troubleshooting records, outages, device state, line state, billing, enterprise incidents, export runs, messages, and SLAs. Every task supplies an answer-template JSON schema and a payload (CSV/JSON) listing the entities to process.

 ## General Workflow

 1. Read the prompt (role + goal), the answer-template schema, and every payload file.
 2. Query `/api/catalog` to confirm available endpoints and record counts.
 3. For each entity in the payload, fetch its primary record and all related records from cross-referenced endpoints.
 4. Derive decisions from evidence in the API responses, never from assumptions or the customer report alone.
 5. Produce a single JSON object that conforms exactly to the provided answer template, preserving field order, enum values, and data types.

 ## API Exploration Pattern

 - Start broad: retrieve the catalog, then the collection endpoint for the entity type (e.g., `/api/outages`, `/api/bills`, `/api/enterprise/messages`).
 - Drill down: for each specific ID in the payload, fetch the detail endpoint (e.g., `/api/tickets/{id}`, `/api/accounts/{id}`, `/api/cases/{id}`).
 - Cross-reference: follow foreign keys (account_id, customer_id, line_id, device_id, plan_id, incident_id) to their respective detail endpoints.
 - For tickets: always check `/api/diagnostics/{ticket_id}` and `/api/troubleshooting/{ticket_id}`.
 - For cases: always check `/api/lines/{line_id}`, `/api/devices/{device_id}`, `/api/plans/{plan_id}`, and `/api/bills` filtered by customer_id.
 - For enterprise incidents: check `/api/enterprise/incidents/{id}`, `/api/enterprise/export-runs` (filter by enterprise_account_id), `/api/enterprise/messages` (filter by incident or account), `/api/enterprise/sla/{account_id}`, and `/api/enterprise/accounts/{id}`.
 - Use `/api/search?q=` for fuzzy discovery when direct paths are unclear.

 ## Ticket Triage Decision Logic

 Evaluate each ticket in this priority order:

 1. **Account validity**: If `GET /api/accounts/{account_id}` returns 404 or error, mark FAILED / INVALID_ACCOUNT.
 2. **Account authentication**: If `authentication.last_login_status` is FAILURE, mark FAILED / AUTH_FAILED.
 3. **Account suspension**: If `status` is Suspended with suspension_reason OVERDUE_BILL, mark FAILED or PENDING_ACTION / OVERDUE_SUSPENSION.
 4. **Active outage**: Check `/api/outages` for an *active* outage in the ticket's `service_area` whose `service_types` includes the ticket's `service_type`. If found, mark PENDING_ACTION / ACTIVE_OUTAGE; set `outage_id` to the matching outage.
 5. **Diagnostic root cause**: Examine `/api/diagnostics/{ticket_id}`. Map root_cause values to key_blocker enums (e.g., BACKBONE_CAPACITY → NETWORK_CAPACITY, PROVISIONING_STALE → PROVISIONING_STALE, FIBER_DROP_DAMAGE → PHYSICAL_LINE_FAULT).
 6. **Troubleshooting effectiveness**: If troubleshooting steps produced meaningful improvement (latency down, bandwidth closer to subscribed), mark RESOLVED. If improvement is marginal and the root cause requires physical/carrier intervention, mark ESCALATED to the appropriate team.
 7. **Escalation routing**: FIBER_DROP_DAMAGE / SIGNAL_LOSS → FIELD_OPS; BACKBONE_CAPACITY → NETWORK_ENGINEERING; OVERDUE_SUSPENSION → ACCOUNTS_PAYABLE; AUTH_FAILED → TIER2_SUPPORT; PROVISIONING_STALE → TIER2_SUPPORT.

 ## Mobile Case Decision Logic

 Evaluate each case by cross-referencing line state, device state, plan limits, and billing:

 - **SIM missing** (`sim_status: "missing"`) → RESEAT_SIM, SELF_SERVICE.
 - **Line suspended / overdue bill** → SEND_PAYMENT_REQUEST then RESUME_LINE_REBOOT; find the bill by customer_id for `bill_id` and `charge_amount_usd`; route BILLING_RECOVERY.
 - **Roaming abroad, no data**: Compare `line.roaming_enabled` vs `device.phone_roaming_enabled`. If line roaming is off → ENABLE_LINE_ROAMING (CARRIER_UPDATE, `carrier_update_required: true`). If phone roaming is off but line is on → TOGGLE_ROAMING (DEVICE_SETTING_FIX).
 - **Cannot send MMS/photos**: Check `device.messaging_permissions.storage`. If false → GRANT_MESSAGING_PERMISSION with permission `storage`, SELF_SERVICE.
 - **Slow data with VPN** (`vpn_connected: true`) → DISCONNECT_VPN, DEVICE_SETTING_FIX.
 - **Data saver visible** (`data_saver_mode: true`) → TOGGLE_DATA_SAVER, DEVICE_SETTING_FIX.
 - **Older network mode** (`network_mode_preference: "3g_only"`) → SET_NETWORK_MODE, DEVICE_SETTING_FIX.
 - **Mobile data off** (`mobile_data_enabled: false`) → TOGGLE_MOBILE_DATA, DEVICE_SETTING_FIX.
 - **Over plan limit** (`data_used_gb > plan.data_limit_gb`) → REFUEL_DATA; calculate `charge_amount_usd = refuel_gb × plan.data_refueling_price_per_gb`; `carrier_update_required: true`; route DATA_RECOVERY.

 ## Enterprise Export Response Logic

 When building an export-failure response package:

 - Identify the incident from the complaint reference and `/api/enterprise/incidents`.
 - Pull export runs from `/api/enterprise/export-runs`; the failure window runs from the first FAILED run date to the last FAILED run date. Count failed runs for `failed_days` and `backfill_days`.
 - Extract root cause from `failure_code` values in the failed export runs and from message bodies in `/api/enterprise/messages`. Use a concise, human-readable category (e.g., "Stale Credential", not "STALE_CREDENTIAL").
 - Determine `contributing_alert_issue` by checking whether the relevant alert message channel is an archive channel; if the channel name contains "archive", use ARCHIVED_ALERT_ROUTE.
 - SLA credit comes from `/api/enterprise/sla/{account_id}` → `monthly_export_credit_percent` formatted as "X%".
 - Severity, engineering_owner, account_owner come directly from the incident record.
 - For `channel_name`, use the channel from the most relevant message (the one describing the root cause), following a lowercase-hyphen convention.
 - Naming conventions (evidence_folder, report_title) follow patterns: `{client-name-lowercase-hyphen}-{start-date}-investigation` for folders; `{Client Name} Export Failure Report` for titles.
 - `share_permissions` lists users in the order given by requirements, assigning the most permissive role to the most relevant stakeholder (finance owner → edit, others → view).
 - Set `response_status` to READY_TO_SEND when all evidence is gathered and the answer is complete.

 ## Common Pitfalls

 - Do not skip cross-referencing: a ticket may show normal diagnostics but be in an outage area; always check outages.
 - Account status trumps diagnostic findings: a suspended or invalid account cannot be resolved by troubleshooting.
 - Distinguish line-level vs device-level settings: roaming requires both line roaming enabled (carrier) AND phone roaming toggled on (device).
 - When calculating charges, verify the plan's pricing model via `/api/plans/{plan_id}`.
 - Preserve the exact payload order in output arrays. Use the enum values exactly as specified in the answer template.
 - Count summary totals from the decisions array, not from assumptions.
