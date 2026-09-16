# Support Console API Reference

Base URL: `<TASK_ENV_BASE_URL>` (provided in the prompt)

## Endpoint Catalog

### Accounts

`GET /api/accounts` — list all accounts
`GET /api/accounts/<account_id>` — single account

**Account shape:**

| Field | Type | Notes |
|---|---|---|
| account_id | string | e.g. `ACC-5107` |
| name | string | Account holder name |
| service_area | string | e.g. `SA-17` |
| status | string | `Active` or `Suspended` |
| tier | string | `standard`, `Enterprise`, `Strategic` |
| authentication.last_login_status | string | `SUCCESS` or error description |
| authentication.account_recovery_status | string | Empty when normal |

**Relevance:** Account status (`Suspended`) blocks resolution. Authentication
failures (`last_login_status` ≠ `SUCCESS`) indicate auth problems. Accounts with
non-standard prefixes (e.g. `BAD-5403`) yield 404 or error responses.

---

### Tickets

`GET /api/tickets` — list all tickets
`GET /api/tickets/<ticket_id>` — single ticket

**Ticket shape:**

| Field | Type | Notes |
|---|---|---|
| ticket_id | string | e.g. `TCK-5107` |
| account_id | string | Links to `/api/accounts/<account_id>` |
| service_area | string | Used for outage matching |
| service_type | string | `internet`, `voice`, `video` |
| status | string | Ticket lifecycle state |
| subscribed_mbps | integer | Plan bandwidth |
| issue_summary | string | Short description |
| created_at | datetime | ISO 8601 |

---

### Diagnostics

`GET /api/diagnostics/<ticket_id>` — diagnostic run for a ticket

**Shape:**

| Field | Type | Notes |
|---|---|---|
| ticket_id | string | |
| bandwidth_mbps | float | Measured bandwidth |
| latency_ms | float | Measured latency |
| jitter_ms | float | Measured jitter |
| root_causes | array of string | e.g. `["CONFIGURATION_DRIFT"]`, `["FIBER_DROP_DAMAGE", "SIGNAL_LOSS"]`, `["GENERATED_NOISE"]` |
| started_at | datetime | |
| completed_at | datetime | |

**Interpretation:** If bandwidth is well below `subscribed_mbps` and latency/jitter
are elevated, a network performance issue exists. `root_causes` drive escalation
routing:

| Root Cause | Implies |
|---|---|
| `CONFIGURATION_DRIFT` | Resolvable via auto-troubleshooting |
| `FIBER_DROP_DAMAGE` / `SIGNAL_LOSS` | Physical line fault — escalate to FIELD_OPS |
| `NETWORK_CAPACITY` / backbone-related | Escalate to NETWORK_ENGINEERING |
| `PROVISIONING_STALE` / provisioning mismatch | Escalate to TIER2_SUPPORT |
| `GENERATED_NOISE` | Ignore; an artifact, not a real root cause |

---

### Troubleshooting

`GET /api/troubleshooting/<ticket_id>` — automated troubleshooting run

**Shape:**

| Field | Type | Notes |
|---|---|---|
| ticket_id | string | |
| steps | array of string | e.g. `["PROFILE_REFRESH", "PROVISIONING_SYNC"]` |
| post_bandwidth_mbps | float | Bandwidth after steps |
| post_latency_ms | float | Latency after steps |
| post_jitter_ms | float | Jitter after steps |
| started_at | datetime | |
| completed_at | datetime | |

**Interpretation:** If `post_bandwidth_mbps` is near `subscribed_mbps` and
`post_latency_ms`/`post_jitter_ms` are within acceptable ranges, the ticket was
resolved by auto-troubleshooting.

---

### Outages

`GET /api/outages` — list all outages

**Shape:**

| Field | Type | Notes |
|---|---|---|
| outage_id | string | e.g. `OUT-9102` |
| service_area | string | Must match ticket's `service_area` |
| service_types | array of string | Must include ticket's `service_type` |
| active | boolean | Only active outages matter |
| impact_score | float | 0–1 |
| eta_hours | integer | Estimated time to resolution |
| started_at | datetime | |

**Matching rule:** An outage applies to a ticket when (1) outage is `active`,
(2) `service_area` matches the ticket's `service_area`, and (3) the ticket's
`service_type` is in the outage's `service_types` list.

---

### Customers (Contact Center)

`GET /api/customers` — list all customers
`GET /api/customers/<customer_id>` — single customer

**Shape:**

| Field | Type |
|---|---|
| customer_id | string |
| name | string |
| phone_number | string |
| status | string |

---

### Cases (Contact Center)

`GET /api/cases` — list all cases

**Shape:**

| Field | Type | Notes |
|---|---|---|
| case_id | string | e.g. `CASE-2101` |
| customer_id | string | Links to `/api/customers/<customer_id>` |
| line_id | string | Links to `/api/lines/<line_id>` |
| device_id | string | Links to `/api/devices/<device_id>` |
| issue_type | string | `NO_SERVICE`, `MOBILE_DATA`, `MMS`, `SLOW_DATA` |
| customer_location | string | `home`, `abroad` |
| summary | string | |

---

### Lines

`GET /api/lines` — list all lines
`GET /api/lines/<line_id>` — single line

**Shape:**

| Field | Type | Notes |
|---|---|---|
| line_id | string | |
| customer_id | string | |
| device_id | string | |
| plan_id | string | Links to `/api/plans/<plan_id>` |
| status | string | `Active` or `Suspended` |
| suspension_reason | string | `OVERDUE_BILL` when suspended due to payment |
| roaming_enabled | boolean | Carrier-side roaming toggle |
| data_used_gb | float | Current billing cycle data usage |
| phone_number | string | |
| contract_end_date | date | |

**Key rule:** When `data_used_gb` exceeds the plan's `data_limit_gb`, the
customer needs a data refuel. The charge is `refuel_gb × plan.data_refueling_price_per_gb`.

---

### Bills

`GET /api/bills` — list all bills

**Shape:**

| Field | Type | Notes |
|---|---|---|
| bill_id | string | |
| customer_id | string | |
| amount_due_usd | float | Outstanding amount |
| due_date | date | |
| status | string | `Paid` or `Overdue` |

**Key rule:** When a line is suspended with `OVERDUE_BILL`, find the customer's
overdue bill. The `amount_due_usd` from that bill is the payment request amount.

---

### Plans

`GET /api/plans` — list all plans
`GET /api/plans/<plan_id>` — single plan

**Shape:**

| Field | Type |
|---|---|
| plan_id | string |
| name | string |
| data_limit_gb | float |
| data_refueling_price_per_gb | float |
| monthly_price_usd | float |

---

### Devices

`GET /api/devices` — list all devices
`GET /api/devices/<device_id>` — single device

**Shape:**

| Field | Type | Notes |
|---|---|---|
| device_id | string | |
| sim_status | string | `active` or `missing` |
| signal_strength | string | `good`, `none`, etc. |
| speed_test | string | `no_connection` or speed description |
| phone_roaming_enabled | boolean | Device-side roaming toggle |
| mobile_data_enabled | boolean | Device-side mobile data toggle |
| data_saver_mode | boolean | When true, throttles data |
| vpn_connected | boolean | When true, VPN may impact speed |
| network_mode_preference | string | e.g. `4g_5g_preferred` |
| can_send_mms | boolean | MMS capability |
| mmsc_url_present | boolean | MMSC configuration |
| messaging_permissions.sms | boolean | SMS permission |
| messaging_permissions.storage | boolean | Storage permission for attachments |
| airplane_mode | boolean | |
| wifi_calling_enabled | boolean | |

**Action mapping from device state:**

| Device State | Primary Action |
|---|---|
| `sim_status: "missing"` with `signal_strength: "none"` | `RESEAT_SIM` |
| `phone_roaming_enabled: false` while abroad | `TOGGLE_ROAMING` |
| `data_saver_mode: true` with slow data | `TOGGLE_DATA_SAVER` |
| `vpn_connected: true` with slow data | `DISCONNECT_VPN` |
| `mobile_data_enabled: false` with no data | `TOGGLE_MOBILE_DATA` |
| `can_send_mms: false` with MMS issue | `GRANT_MESSAGING_PERMISSION` |
| Network mode outdated for device | `SET_NETWORK_MODE` |

**Permission derivation for MMS:** Check `messaging_permissions`. If `storage`
is already `true` but `can_send_mms` is `false`, set `permission: "storage"`.
The `permission` field mirrors which permission is missing.

---

### Enterprise Accounts

`GET /api/enterprise/accounts` — list all enterprise accounts
`GET /api/enterprise/accounts/<account_id>` — single account

**Shape:**

| Field | Type |
|---|---|
| enterprise_account_id | string |
| name | string |
| tier | string |
| account_owner | string (user id) |
| finance_owner | string (user id) |

---

### Enterprise Incidents

`GET /api/enterprise/incidents` — list all incidents
`GET /api/enterprise/incidents/<incident_id>` — single incident

**Shape:**

| Field | Type |
|---|---|
| incident_id | string |
| enterprise_account_id | string |
| product | string |
| severity | string (`Critical`, `High`, `Medium`, `Low`) |
| status | string |
| summary | string |
| engineering_owner | string (user id) |
| account_owner | string (user id) |
| received_at | datetime |

---

### Enterprise Export Runs

`GET /api/enterprise/export-runs` — list all export runs

**Shape:**

| Field | Type |
|---|---|
| run_id | string |
| incident_id | string |
| enterprise_account_id | string |
| run_date | date (`YYYY-MM-DD`) |
| status | string (`FAILED` or `SUCCEEDED`) |
| failure_code | string (empty when succeeded) |
| exported_record_count | integer |

**Interpretation:** Filter by `enterprise_account_id` for the target account.
Count consecutive `FAILED` runs to determine the failure window. The `failure_code`
across failed runs gives the root cause category. A successful run after the
failure window indicates backfill occurred; count the successful backfill runs.

---

### Enterprise Messages

`GET /api/enterprise/messages` — list all messages

**Shape:**

| Field | Type |
|---|---|
| message_id | string |
| author | string (user id) |
| body | string |
| channel | string |
| created_at | datetime |

**Interpretation:** Read messages authored by incident principals (engineering
owner, account owner) to find root cause explanations, SLA credit mentions,
and alert routing evidence. If a message about the root cause appears in a
channel with "archive" in the name, that is `ARCHIVED_ALERT_ROUTE`.

---

### Enterprise SLA

`GET /api/enterprise/sla/<enterprise_account_id>` — SLA contract

**Shape:**

| Field | Type |
|---|---|
| enterprise_account_id | string |
| credit_trigger | string |
| monthly_export_credit_percent | integer |
| executive_contact | string |
