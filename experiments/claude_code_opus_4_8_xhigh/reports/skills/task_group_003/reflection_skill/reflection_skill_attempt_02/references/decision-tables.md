# Decision Tables & Field Definitions

Lookup reference for the three task families. Use it while filling
`answer_template.json`. Always defer to the actual template's enum spellings and
field names for the task in front of you — templates vary (e.g. one task names
the team field `escalation_team`, another `route_team`; one uses
`diagnostic_needed`, another `diagnostic_required`). The semantics below are
stable; the field names are not.

## Contents
1. Endpoints quick map
2. SOP A — ticket triage: gating order, status/route/team/blocker maps
3. SOP B — mobile case: symptom → action → route map
4. SOP C — enterprise package: field provenance, naming, permissions

---

## 1. Endpoints quick map (base URL from the environment doc)

| Need | Endpoint |
|---|---|
| Health / catalog | `GET /health`, `GET /api/catalog` |
| Account state, service_area, auth | `GET /api/accounts/<id>` |
| Ticket service_type / service_area | `GET /api/tickets/<id>` |
| Active outages for an area | `GET /api/outages?service_area=<area>` |
| Diagnostics / troubleshooting | `GET /api/diagnostics/<ticket_id>`, `GET /api/troubleshooting/<ticket_id>` |
| Customer / line / device / plan / bill | `GET /api/customers`, `/api/lines/<id>`, `/api/devices/<id>`, `/api/plans/<id>`, `/api/bills` |
| Cases | `GET /api/cases/<id>` |
| Enterprise | `/api/enterprise/incidents/<id>`, `/api/enterprise/accounts/<id>`, `/api/enterprise/export-runs?incident_id=<id>`, `/api/enterprise/messages?query=<text>`, `/api/enterprise/sla/<account_id>` |
| Find everything touching an id | `GET /api/search?q=<text>` |

`/api/bills` is unfiltered — match by `customer_id` and look for `status`
`Overdue`/`Issued`. `/api/outages?service_area=` returns a list; an outage
counts only when `active: true` AND `service_types` includes the ticket's
`service_type`.

---

## 2. SOP A — ticket triage

### Gating order (stop at first match)

1. Account not found → INVALID_ACCOUNT
2. Auth recovery FAILURE / last_login FAILURE → AUTH_FAILED
3. Account `status == "Suspended"` → suspension (billing vs fraud vs generic)
4. Active outage matching service_type → ACTIVE_OUTAGE
5. Active account, no outage → run diagnostics → RESOLVED or ESCALATED

Account-state blockers (1-3) are checked BEFORE any technical work because a
blocked account cannot be fixed by troubleshooting in this batch.

### Status map

| Situation | final_resolution_status |
|---|---|
| Invalid account | `FAILED` |
| Auth failure | `FAILED` |
| Suspended (any reason — overdue, hold, fraud) | `FAILED`  ← NOT PENDING_ACTION |
| Active outage on ticket's service_type | `PENDING_ACTION` (only "customer wait" case) |
| Diagnostics cleared the issue | `RESOLVED` |
| Physical/capacity/provisioning fault remains | `ESCALATED` |

### Route / blocker / team map

| Blocker | route enum | team | diagnostic |
|---|---|---|---|
| INVALID_ACCOUNT | `INVALID_ACCOUNT` | `NONE` | false |
| AUTH_FAILED | `AUTH_FAILED` | `NONE` | false |
| Suspended, note = billing/"overdue" → `OVERDUE_SUSPENSION` | `INELIGIBLE_ACCOUNT` (if present) | `ACCOUNTS_PAYABLE` | false |
| Suspended, note = fraud → `FRAUD_SUSPENSION` | `INELIGIBLE_ACCOUNT` | (per policy) | false |
| Suspended, generic "account hold" | `INELIGIBLE_ACCOUNT` | `NONE` | false |
| ACTIVE_OUTAGE | `OUTAGE_WAIT` | `NONE` | false (set `outage_id`) |
| Resolved by troubleshooting | `AUTO_TROUBLESHOOTING` | `NONE` (blocker NONE) | true |
| Physical line fault (`PHYSICAL_LINE_FAULT`) | `ESCALATION` | `FIELD_OPS` | true |
| Backbone / capacity (`NETWORK_CAPACITY`) | `ESCALATION` | `NETWORK_ENGINEERING` | true |
| Provisioning-stale / config to human (`PROVISIONING_STALE`) | `ESCALATION` | `TIER2_SUPPORT` | true |

`route_team`/status are independent — a `FAILED` suspended ticket can still name
`ACCOUNTS_PAYABLE` as the team to pursue billing.

### Issue flags (`latency_issue`/`stability_issue`/`bandwidth_issue`) + diagnostic boolean

- Paths 1-4 (blocked / outage): all issue flags `false`, diagnostic `false` —
  the route, not the diagnostic record, decided the outcome.
- Path 5 (ran diagnostics): diagnostic `true`; each issue flag is `true` when
  that metric (latency / jitter→stability / bandwidth) was measured as degraded.
  Both RESOLVED and ESCALATED diagnostic tickets can carry true flags (the
  RESOLVED ticket had real issues that troubleshooting then fixed).
- No published numeric thresholds. Anchor on root cause + whether POST metrics
  improved into a healthy range; do not hardcode a cutoff.

### Summary

- Per-status counts = tally of your rows.
- Per-team counts = tally of `route_team` values.
- `tickets_requiring_customer_wait` = ACTIVE_OUTAGE / OUTAGE_WAIT rows ONLY.
- Recount after any row change.

---

## 3. SOP B — mobile case: symptom → action → route

Resolve case → customer → line → device → plan → bill. Match the symptom to the
data layer that is actually wrong.

| Reported symptom | Check | primary_action | secondary | extra fields | final_route |
|---|---|---|---|---|---|
| No service after commute | device sim_status missing / no signal | `RESEAT_SIM` | `NO_ACTION` | — | SELF_SERVICE |
| Line suspended, customer ready to pay | line Suspended (OVERDUE_BILL) + Overdue bill | `SEND_PAYMENT_REQUEST` | `RESUME_LINE_REBOOT` | `bill_id` = overdue bill, `charge_amount_usd` = bill amount_due | BILLING_RECOVERY |
| Abroad, "roaming on phone but no data", line roaming OFF | line.roaming_enabled false | `ENABLE_LINE_ROAMING` | `NO_ACTION` | `carrier_update_required: true` | CARRIER_UPDATE |
| Abroad, line roaming ON but device roaming OFF | device phone_roaming_enabled false | `TOGGLE_ROAMING` | `NO_ACTION` | — | SELF_SERVICE / DEVICE_SETTING_FIX |
| MMS / photo messaging fails | device messaging_permissions; which flag false | `GRANT_MESSAGING_PERMISSION` | `NO_ACTION` | `permission` = missing cap (`sms` / `storage` / `sms_and_storage`) | SELF_SERVICE |
| Slow data, VPN connected | device vpn_connected true | `DISCONNECT_VPN` | `NO_ACTION` | — | SELF_SERVICE / DEVICE_SETTING_FIX |
| Slow data, data-saver icon | device data_saver_mode true | `TOGGLE_DATA_SAVER` | `NO_ACTION` | — | DEVICE_SETTING_FIX |
| Slow data, old network mode | device network_mode_preference 3g_only | `SET_NETWORK_MODE` | `NO_ACTION` | — | DEVICE_SETTING_FIX |
| No data after settings change | device mobile_data_enabled false | `TOGGLE_MOBILE_DATA` | `NO_ACTION` | — | DEVICE_SETTING_FIX |
| Data stopped after usage limit | line data_used > plan limit | `REFUEL_DATA` | `NO_ACTION` | `data_refuel_gb` = accepted GB, `charge_amount_usd` = accepted_GB × plan refuel $/GB | DATA_RECOVERY |
| No automatable fix | — | `TRANSFER_HUMAN` | — | — | HUMAN_TRANSFER |

Notes:
- Roaming is the classic trap: choose `ENABLE_LINE_ROAMING` (carrier update)
  vs device `TOGGLE_ROAMING` (self-service) by which layer is off.
- `permission`: grant ONLY the missing capability. If only storage is false →
  `storage`; if both sms+storage false → `sms_and_storage`; none missing →
  `NONE`.
- Refuel charge = customer-accepted GB × plan refuel price, NOT raw overage, and
  honor `does_not_want_plan_change`.
- Defaults when N/A: `secondary_action` `NO_ACTION`, `bill_id` `""`, numerics
  `0.0`, `permission` `NONE`, `carrier_update_required` `false`.
- Honor template decimal precision (e.g. charge two decimals, refuel_gb one).
- Summary: count routes; `total_estimated_customer_charge_usd` = sum of charges.

---

## 4. SOP C — enterprise package

### Field provenance

| Field | Source |
|---|---|
| incident_id | incident record (email gives approximate ref) |
| enterprise_account_id | incident → also on account |
| root_cause_category | export-run `failure_code` + engineering message; keep CONCISE |
| contributing_alert_issue | `ARCHIVED_ALERT_ROUTE` if alert message channel name contains "archive"; else `NONE`/`UNKNOWN` |
| failure_window.start_date | first FAILED export run `run_date` |
| failure_window.end_date | last FAILED export run `run_date` |
| failure_window.failed_days | count of FAILED runs |
| backfill_days | failed days to re-run (= failed_days unless evidence differs) |
| sla_credit_percent | SLA contract `*_credit_percent` |
| severity | incident `severity` |
| engineering_owner | incident `engineering_owner` |
| account_owner | incident `account_owner` |
| finance_owner (reviewer) | account `finance_owner` (NOT an owner field) |
| channel_name / evidence_folder / report_title | naming_style string, per token |
| share_permissions | requirements user order; level by role |
| response_status | package state (see below) |

### Naming (apply the style string token by token)

| Field | Convention | Example |
|---|---|---|
| channel_name | CLIENT name, lowercase-hyphen (no product token) | `asteri-retail-inc` |
| evidence_folder | full client name + Month Year + "Investigation" (Title Case, month-year, not exact day) | `Asteri Retail Inc. May 2026 Investigation` |
| report_title | full client name + "Export Failure - Resolution Report" | `Asteri Retail Inc. Export Failure - Resolution Report` |

Different fields use different casing in the same task. Do not apply one casing
everywhere.

### Share permissions

- Preserve the requirements' user order exactly.
- Level by role: reviewer/approver (finance_owner in a finance-review package) =
  `view`; working author/collaborator = `edit`; evidence-only contributor =
  `upload_only`.
- The finance_owner does NOT automatically get `edit` — in a finance-review
  package the finance_owner is the viewer and the other listed user is the
  editor. Set edit=author, view=approver, then verify against each user's role.

### response_status

| Package state | status |
|---|---|
| SLA credit needs finance sign-off / shared to finance owner | `NEEDS_FINANCE_REVIEW` |
| Engineering must confirm root cause/fix | `NEEDS_ENGINEERING_REVIEW` |
| Still investigating, no conclusion | `UNDER_INVESTIGATION` |
| Fully approved | `READY_TO_SEND` |

Pick from the package's real state, not the incident's raw `status`.
