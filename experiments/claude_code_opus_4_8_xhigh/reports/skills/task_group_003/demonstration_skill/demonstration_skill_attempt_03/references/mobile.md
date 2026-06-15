# Mobile Case Triage — Families C & D

Covers the mobile **case queue** (C) and the mobile-data **worklist** (D). Both
pick the next support operation by reading device + line (+ bill + plan) records
and matching them against the case `issue_type` / reported symptom. They share an
action vocabulary but differ in output fields, routes, and (importantly) how
roaming is handled.

## Records to fetch per case

- `/api/cases/<case_id>` → `customer_id`, `line_id`, `device_id`,
  `issue_type` (NO_SERVICE, MOBILE_DATA, SLOW_DATA, MMS, ...), `customer_location`
  (home / abroad), `summary`.
- `/api/lines/<line_id>` → `status`, `suspension_reason`, `roaming_enabled`
  (the **line/carrier-side** roaming entitlement), `plan_id`, `data_used_gb`.
- `/api/devices/<device_id>` → device toggles: `sim_status`, `signal_strength`,
  `mobile_data_enabled`, `phone_roaming_enabled` (the **device-side** roaming
  toggle), `data_saver_mode`, `network_mode_preference`, `vpn_connected`,
  `can_send_mms`, `messaging_permissions.{sms,storage}`, `airplane_mode`.
- `/api/plans/<plan_id>` → `data_limit_gb`, `data_refueling_price_per_gb`.
- `/api/bills` (filter by `customer_id`) → `bill_id`, `amount_due_usd`, `status`
  (needed only for billing/suspension cases).

## Diagnosis principle

Find the single field that explains the reported symptom, and choose the action
that flips exactly that field. Prefer the cheapest self-service / device-setting
fix that addresses the offending field. Order of inspection roughly follows the
issue_type; the tables below give the field→action mapping.

## The roaming distinction (read carefully — easy to get backwards)

There are two roaming fields and two different actions:

- **`device.phone_roaming_enabled` is false** (line `roaming_enabled` is true):
  the entitlement exists but the handset toggle is off → **TOGGLE_ROAMING**
  (a device-side self-service fix, no carrier work, no charge).
- **`line.roaming_enabled` is false** (device `phone_roaming_enabled` is true):
  the carrier line is not provisioned for roaming → **ENABLE_LINE_ROAMING**, which
  is a carrier-side change → set `carrier_update_required = true` and route
  CARRIER_UPDATE (family D).

Mnemonic: fix it on the *phone* = TOGGLE_ROAMING (self-service); fix it on the
*line/carrier* = ENABLE_LINE_ROAMING (carrier update).

## Action selection by symptom

| Symptom / issue_type | Offending field | Primary action |
|---|---|---|
| NO_SERVICE | `sim_status` missing/inactive | RESEAT_SIM |
| NO_SERVICE | `airplane_mode` true | TOGGLE_AIRPLANE_MODE |
| NO_SERVICE | line `status` Suspended, `suspension_reason` OVERDUE_BILL | SEND_PAYMENT_REQUEST (+ secondary RESUME_LINE_REBOOT) |
| MOBILE_DATA | `mobile_data_enabled` false | TOGGLE_MOBILE_DATA |
| MOBILE_DATA (abroad) | device roaming off | TOGGLE_ROAMING |
| MOBILE_DATA (abroad) | line roaming off | ENABLE_LINE_ROAMING (carrier update) |
| MOBILE_DATA | `data_used_gb >= plan.data_limit_gb` (over cap) | REFUEL_DATA |
| SLOW_DATA | `data_saver_mode` true | TOGGLE_DATA_SAVER |
| SLOW_DATA | `network_mode_preference` not modern (e.g. `3g_only`) | SET_NETWORK_MODE |
| SLOW_DATA | `vpn_connected` true | DISCONNECT_VPN |
| MMS | `can_send_mms` false / `messaging_permissions.storage` false | GRANT_MESSAGING_PERMISSION (set `permission`) |
| nothing in records explains it / needs a human | — | TRANSFER_HUMAN |

`secondary_action` is NO_ACTION unless a follow-up is genuinely required (e.g.
after a payment request, RESUME_LINE_REBOOT brings the line back).

## Permissions (family C)

When the fix is GRANT_MESSAGING_PERMISSION, set `permission` to whichever of the
messaging permissions is missing on the device:

- `messaging_permissions.storage` false (can't attach photos/MMS) → `storage`
- `messaging_permissions.sms` false → `sms`
- both missing → `sms_and_storage`
- otherwise / non-messaging actions → `NONE`

## Charge & refuel math

- **Billing recovery (family C).** For a line suspended for an overdue bill, the
  primary action is SEND_PAYMENT_REQUEST; set `bill_id` to the customer's overdue
  bill and `charge_amount_usd` to that bill's `amount_due_usd` (two decimals).
  Secondary RESUME_LINE_REBOOT, route BILLING_RECOVERY.
- **Data refuel (families C & D).** When over the data cap:
  `data_refuel_gb` = the customer's accepted top-up. Read it from the
  `customer_preferences` payload (e.g. `accepted_refuel_gb`); respect
  `does_not_want_plan_change` (refuel, don't upsell a plan).
  `charge_amount_usd` = `data_refuel_gb * plan.data_refueling_price_per_gb`
  (two decimals). Route DATA_RECOVERY.
- Device-setting / self-service fixes carry `charge_amount_usd = 0.0`,
  `data_refuel_gb = 0.0`, `carrier_update_required = false`.

## Output field reference

### Family C — `case_decisions[]` (ascending case_id order)

`case_id`, `customer_id`, `line_id`, `primary_action`, `secondary_action`,
`permission`, `bill_id` (empty `""` unless billing), `charge_amount_usd`,
`final_route`:

| Route | When |
|---|---|
| SELF_SERVICE | a device/line toggle resolves it, no charge |
| BILLING_RECOVERY | overdue-bill payment request |
| CARRIER_UPDATE | carrier-side change required |
| HUMAN_TRANSFER | TRANSFER_HUMAN |

`queue_summary`: `self_service_fixes`, `billing_recoveries`, `carrier_updates`,
`human_transfers` — count decisions by `final_route`.

### Family D — `case_decisions[]` (ascending case_id order)

`case_id`, `primary_action`, `secondary_action`, `data_refuel_gb` (one decimal),
`charge_amount_usd` (two decimals), `carrier_update_required`, `final_route`:

| Route | When |
|---|---|
| DATA_RECOVERY | REFUEL_DATA (over-cap top-up) |
| CARRIER_UPDATE | ENABLE_LINE_ROAMING / carrier-side change |
| DEVICE_SETTING_FIX | a device toggle (TOGGLE_MOBILE_DATA, TOGGLE_DATA_SAVER, SET_NETWORK_MODE, TOGGLE_ROAMING, DISCONNECT_VPN, ...) |
| HUMAN_TRANSFER | TRANSFER_HUMAN |

`worklist_summary`: `data_refuel_cases`, `carrier_updates`,
`device_setting_fixes`, `human_transfers`, and
`total_estimated_customer_charge_usd` = sum of all `charge_amount_usd`
(two decimals). Recount from your decisions.
