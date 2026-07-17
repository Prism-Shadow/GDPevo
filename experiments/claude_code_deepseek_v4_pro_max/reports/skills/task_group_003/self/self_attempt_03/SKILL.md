# Support Console — Operations Analyst SKILL

## Base URL

Always read `environment_access.md` first. It overrides any `localhost` or `127.0.0.1` text in task prompts. The canonical base is the `GDPEVO_ENV_BASE_URL` from that file.

## API Catalog & Error Convention

**Catalog**: `GET /api/catalog` lists all endpoints and record counts. Use for discovery.

**Error convention**: Missing/invalid records return `{"error": "not_found"}` with HTTP 200 — never a 404. Always check for the `"error"` key, not the HTTP status code.

**Key endpoints**:

| Endpoint | Description |
|---|---|
| `/api/accounts/<id>` | Account status, auth, service_area, tier |
| `/api/tickets/<id>` | Ticket details incl. service_area, service_type, subscribed_mbps |
| `/api/diagnostics/<ticket_id>` | Pre-TS metrics, root_causes array |
| `/api/troubleshooting/<ticket_id>` | Post-TS metrics, steps taken |
| `/api/outages?service_area=<area>` | Active outages for a service area (empty `[]` if none) |
| `/api/cases/<id>` | Case metadata: customer_id, line_id, device_id, issue_type, customer_location |
| `/api/lines/<id>` | Line status, roaming, plan, suspension, data_used_gb |
| `/api/devices/<id>` | Device state: toggles, permissions, signal, SIM, VPN, network_mode |
| `/api/plans/<id>` | data_limit_gb, data_refueling_price_per_gb, monthly_price_usd |
| `/api/bills` | Full bill list; filter by customer_id match |
| `/api/customers` | Full customer list |
| `/api/enterprise/incidents/<id>` | Incident severity, owners, status, product |
| `/api/enterprise/export-runs?incident_id=<id>` | Export run history with failure_code and status |
| `/api/enterprise/messages?query=<text>` | Channel messages with author, body, channel |
| `/api/enterprise/sla/<ent_account_id>` | SLA credit triggers and percentages |
| `/api/enterprise/accounts` | Enterprise account owners and tiers |

## Data Model Relationships

```
Ticket  →  Account (via account_id)
Ticket  →  Diagnostics (via ticket_id)  →  root_causes[]
Ticket  →  Troubleshooting (via ticket_id)  →  post_* metrics
Ticket  →  Outages (via service_area match)

Case    →  Line (via line_id)
Case    →  Device (via device_id)
Case    →  Customer (via customer_id)
Line    →  Plan (via plan_id)
Line    →  Bill (via customer_id match in /api/bills)

Incident → Enterprise Account (via enterprise_account_id)
Incident → Export Runs (via incident_id query)
Incident → Messages (via text query)
Incident → SLA (via enterprise_account_id)
```

## Task Type 1: Ticket Batch Resolution

**Input**: CSV of ticket_ids with account_ids, service_type, customer_report.
**Key question**: For each ticket, determine resolution status, whether diagnostics are needed, which issues are present, and the resolution route.

### Decision SOP

1. **Fetch account** by `account_id`.
   - `{"error": "not_found"}` → `FAILED`, `INVALID_ACCOUNT`, key_blocker=`INVALID_ACCOUNT`
   - `status: "Suspended"` → `PENDING_ACTION`, `ACCOUNTS_PAYABLE`, route=`INELIGIBLE_ACCOUNT`, key_blocker=`OVERDUE_SUSPENSION`
   - `auth.last_login_status: "FAILURE"` or `auth.account_recovery_status: "FAILURE"` → `FAILED`, key_blocker=`AUTH_FAILED`
   - `status: "Active"` and auth OK → continue

2. **Fetch ticket** by `ticket_id` for service_area and subscribed_mbps.

3. **Check outages** at `/api/outages?service_area=<service_area>`.
   - Active outage matching the ticket's service_type → `PENDING_ACTION`, route=`OUTAGE_WAIT`, key_blocker=`ACTIVE_OUTAGE`, escalation_team=`NONE`. Record the `outage_id`.

4. **Fetch diagnostics** by `ticket_id`.
   - `diagnostic_needed`: `true` if diagnostics record exists, `false` otherwise.
   - **latency_issue**: `true` when `latency_ms > 100` (approximate threshold).
   - **bandwidth_issue**: `true` when `bandwidth_mbps < 0.80 * subscribed_mbps`.
   - **stability_issue**: `true` when `jitter_ms > 35` or root_causes includes `SIGNAL_LOSS`.

5. **Fetch troubleshooting** by `ticket_id`.
   - Compare `post_*` metrics to pre-TS diagnostics.
   - **RESOLVED**: Post-TS metrics show significant improvement toward subscribed levels (typically bandwidth ≥ 80% of subscribed, latency < 100ms) AND root cause is addressable by auto-TS (CONFIGURATION_DRIFT, VOICE_PROFILE_STALE).
   - **ESCALATED** otherwise, with escalation team determined by root cause.

6. **Root cause → escalation mapping**:
   | Root Cause | Key Blocker | Escalation Team |
   |---|---|---|
   | `FIBER_DROP_DAMAGE` | `PHYSICAL_LINE_FAULT` | `FIELD_OPS` |
   | `BACKBONE_CAPACITY` | `NETWORK_CAPACITY` | `NETWORK_ENGINEERING` |
   | `PROVISIONING_STALE` | `PROVISIONING_STALE` | `TIER2_SUPPORT` |
   | `CONFIGURATION_DRIFT` (auto-resolved) | `NONE` | `NONE` |
   | `VOICE_PROFILE_STALE` (auto-resolved) | `NONE` | `NONE` |
   | `SIGNAL_LOSS` (+ FIBER_DROP_DAMAGE) | `PHYSICAL_LINE_FAULT` | `FIELD_OPS` |
   | `GENERATED_NOISE` (varies — check TS outcome) | `NONE` or escalate by metrics | `NETWORK_ENGINEERING` if bandwidth badly degraded |

7. **Batch summary** counts: RESOLVED, PENDING_ACTION, ESCALATED, FAILED, and `tickets_requiring_customer_wait` = count of PENDING_ACTION tickets.

## Task Type 2: Mobile Contact-Center Queue

**Input**: JSON case queue with case_ids and reported_issues.
**Key question**: For each case, choose primary/secondary actions based on device, line, and bill state.

### Decision SOP

1. **Fetch case** → get customer_id, line_id, device_id, issue_type, customer_location.

2. **Fetch line** → check status, roaming_enabled, plan_id, data_used_gb, suspension_reason.

3. **Fetch device** → check all toggles: sim_status, airplane_mode, mobile_data_enabled, data_saver_mode, phone_roaming_enabled, vpn_connected, network_mode_preference, can_send_mms, messaging_permissions, mmsc_url_present.

4. **Fetch bill** matching customer_id → check status (Paid vs Overdue), amount_due_usd.

5. **Action decision tree** (check in this order):

   | Condition | Primary Action | Secondary Action | Permission | Final Route |
   |---|---|---|---|---|
   | `sim_status: "missing"` (NO_SERVICE) | `RESEAT_SIM` | `NO_ACTION` | `NONE` | `SELF_SERVICE` |
   | Line `status: "Suspended"` + bill Overdue | `SEND_PAYMENT_REQUEST` | `RESUME_LINE_REBOOT` | `NONE` | `BILLING_RECOVERY` |
   | `phone_roaming_enabled: false` + abroad + line roaming on | `TOGGLE_ROAMING` | `NO_ACTION` | `NONE` | `SELF_SERVICE` |
   | Line `roaming_enabled: false` + abroad | `ENABLE_LINE_ROAMING` | `NO_ACTION` | `NONE` | `CARRIER_UPDATE` |
   | `can_send_mms: false` + missing storage permission | `GRANT_MESSAGING_PERMISSION` | `NO_ACTION` | `storage` (or `sms` if that's missing) | `SELF_SERVICE` |
   | `vpn_connected: true` + slow data | `DISCONNECT_VPN` | `NO_ACTION` | `NONE` | `SELF_SERVICE` |
   | `data_saver_mode: true` | `TOGGLE_DATA_SAVER` | `NO_ACTION` | `NONE` | `SELF_SERVICE` |
   | `mobile_data_enabled: false` | `TOGGLE_MOBILE_DATA` | `NO_ACTION` | `NONE` | `SELF_SERVICE` |
   | `network_mode_preference: "3g_only"` | `SET_NETWORK_MODE` | `NO_ACTION` | `NONE` | `SELF_SERVICE` |
   | data_used_gb > plan limit | `REFUEL_DATA` | `NO_ACTION` | `NONE` | `DATA_RECOVERY` |
   | No self-service fix possible | `TRANSFER_HUMAN` | `NO_ACTION` | `NONE` | `HUMAN_TRANSFER` |

6. **Bill fields**: `bill_id` and `charge_amount_usd` are populated only for billing-related actions (SEND_PAYMENT_REQUEST, REFUEL_DATA). Otherwise empty string and `0.00`.

7. **Permission field**: Set to the specific missing permission (`sms`, `storage`, or `sms_and_storage`). Default `NONE`.

8. **Queue summary**: Count cases by final_route: self_service_fixes, billing_recoveries, carrier_updates, human_transfers.

## Task Type 3: Enterprise Export Incident Response

**Input**: Client complaint email + response_requirements.json.
**Key question**: Build a structured response package with root cause, SLA credit, evidence, owners, and share permissions.

### Decision SOP

1. **Extract incident_id** from the complaint email (e.g., INC-7301).

2. **Fetch incident** → get enterprise_account_id, severity, product, owners (engineering_owner, account_owner).

3. **Fetch export runs** via `/api/enterprise/export-runs?incident_id=<id>`:
   - Identify the **failure window**: consecutive FAILED runs → `start_date`, `end_date`, `failed_days`.
   - Identify **backfill**: first SUCCEEDED run after failures → `backfill_days` = count of SUCCEEDED backfill runs (not failed days).
   - Extract **root cause** from `failure_code` (e.g., `STALE_CREDENTIAL`).

4. **Fetch messages** via `/api/enterprise/messages?query=<client_name>`:
   - Find the technical root cause message (usually from engineering_owner).
   - Find the SLA/contract message (usually from account_owner, mentions credit percent).
   - `channel_name`: the message channel, lowercased with hyphens (as-is from API).
   - `contributing_alert_issue`: `ARCHIVED_ALERT_ROUTE` if channel name contains "archive", otherwise `NONE` or `UNKNOWN`.

5. **Fetch SLA** via `/api/enterprise/sla/<enterprise_account_id>` → `monthly_export_credit_percent`.

6. **Fetch enterprise account** for finance_owner and tier.

7. **Naming conventions** (from response_requirements):
   - `channel_name`: lowercase-hyphen channel name from messages.
   - `evidence_folder`: `{client-lowercase-hyphen}-{YYYY-MM}-investigation` (e.g., `asteri-retail-2026-05-investigation`).
   - `report_title`: `{client-lowercase-hyphen}-export-failure-report`.

8. **Share permissions**: Map from `permission_users_to_include`. Users matching finance_owner or account_owner typically get `view`. Order by the requirements list.

9. **Response status**:
   - `NEEDS_FINANCE_REVIEW` when SLA credit > 0% is involved.
   - `NEEDS_ENGINEERING_REVIEW` when root cause is unclear or backfill incomplete.
   - `READY_TO_SEND` when all evidence is clear, backfill confirmed, no credit issues.
   - `UNDER_INVESTIGATION` when incident status in API is unresolved and data is insufficient.

10. **root_cause_category**: Human-readable summary inferred from failure_code + message body (e.g., `STALE_CREDENTIAL` → "Stale Credential Rotation").

## Task Type 4: Queue Quality Analysis (Pre-SLA Review)

**Input**: CSV of ticket_ids with account_ids, service_type, queue_note.
**Key question**: Classify each ticket by resolution status, route team, key blocker, and diagnostic requirement.

### Decision SOP

Same initial flow as Task Type 1 (account → outage check → diagnostics → troubleshooting), but with a different answer schema focused on `key_blocker` and `route_team` rather than detailed issue flags.

**Key differences from Task Type 1**:
- When account is not found: `FAILED`, `NONE`, `INVALID_ACCOUNT`.
- When auth has failed but account Active: `FAILED`, `NONE`, `AUTH_FAILED`.
- Route team is `NONE` when no escalation is needed (outage wait, invalid account, auth fail, auto-resolved).
- Queue summary includes counts per escalation team: TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE.

## Task Type 5: Mobile Data Recovery

**Input**: JSON worklist with case_ids + customer_preferences map.
**Key question**: Select primary/secondary actions, refuel amount, charge, carrier update flag, and route.

### Decision SOP

Same device/line/bill inspection as Task Type 2, but focused on mobile data issues. Additional considerations:

1. **Data refuel**: When `data_used_gb > plan.data_limit_gb`:
   - Read `customer_preferences[case_id].accepted_refuel_gb` for the refuel amount.
   - `charge_amount_usd = accepted_refuel_gb × plan.data_refueling_price_per_gb` (rounded to 2 decimals).
   - `data_refuel_gb`: the accepted_refuel_gb value (1 decimal).
   - If `does_not_want_plan_change: true`, do not suggest a plan change; just refuel.

2. **Carrier updates**: When line-side settings need carrier action (e.g., `ENABLE_LINE_ROAMING`), `carrier_update_required: true`, route=`CARRIER_UPDATE`.

3. **Device setting fixes**: TOGGLE_MOBILE_DATA, TOGGLE_DATA_SAVER, SET_NETWORK_MODE, DISCONNECT_VPN → route=`DEVICE_SETTING_FIX`.

4. **Worklist summary**: Count per final_route plus `total_estimated_customer_charge_usd` (sum of all charge_amount_usd).

## Common Pitfalls

1. **Not checking outages first**: Always query `/api/outages?service_area=<area>` BEFORE concluding on diagnostics. An active outage overrides all other analysis — the ticket becomes `PENDING_ACTION` / `OUTAGE_WAIT`.

2. **Account status before diagnostics**: A Suspended or auth-failed account makes diagnostics irrelevant. Check account status first.

3. **Invalid account IDs in payload**: Account IDs like `BAD-XXXX` return `{"error": "not_found"}` — don't assume the account exists just because the ticket CSV lists it.

4. **Roaming mismatch**: Distinguish device-side (`phone_roaming_enabled`) from line-side (`roaming_enabled`). Device toggle → `TOGGLE_ROAMING`; line toggle → `ENABLE_LINE_ROAMING` (carrier action).

5. **MMS permissions**: MMS requires both `sms` and `storage` device permissions. Check `messaging_permissions` object, not just `can_send_mms`.

6. **Export backfill vs failure count**: `backfill_days` = number of SUCCEEDED backfill runs, NOT the number of failed days. A single successful run after 3 failures = 1 backfill day.

7. **Plan data limits**: Always fetch the plan to get `data_limit_gb` — don't assume a fixed limit. Compare `line.data_used_gb` to `plan.data_limit_gb`.

8. **Answer template order**: Preserve payload order for ticket/case arrays. Sort by ascending case_id or payload order as specified in the template comments.

9. **Numeric precision**: charge_amount_usd always 2 decimal places; data_refuel_gb always 1 decimal place.

10. **SLA credits trigger finance review**: Any non-zero SLA credit percent means `response_status` should be `NEEDS_FINANCE_REVIEW`.

## Field Value Quick Reference

### Ticket resolutions
- `RESOLVED`: Auto-TS fixed the issue (metrics improved to acceptable levels).
- `PENDING_ACTION`: Waiting on outage resolution OR customer payment/action.
- `ESCALATED`: Needs another team (FIELD_OPS, NETWORK_ENGINEERING, TIER2_SUPPORT).
- `FAILED`: Unresolvable via support (INVALID_ACCOUNT, AUTH_FAILED).

### Escalation teams
- `NONE`: No team needed (auto-resolved, outage wait, or unfixable).
- `TIER2_SUPPORT`: Configuration/provisioning issues beyond auto-TS.
- `FIELD_OPS`: Physical damage (fiber, line faults).
- `NETWORK_ENGINEERING`: Capacity/backbone issues.
- `ACCOUNTS_PAYABLE`: Billing/suspension issues.

### Mobile final routes
- `SELF_SERVICE`: User can fix on device.
- `BILLING_RECOVERY`: Overdue bill payment needed.
- `CARRIER_UPDATE`: Line-side change needed.
- `HUMAN_TRANSFER`: No self-service fix possible.
- `DATA_RECOVERY`: Data refuel/plan change.
- `DEVICE_SETTING_FIX`: Toggle or setting change on device.
