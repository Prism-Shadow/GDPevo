# Mobile Case Actions

Two related families:
- **Contact-center queue** (`case_queue.json`): choose `primary_action`,
  `secondary_action`, `permission`, `bill_id`, `charge_amount_usd`,
  `final_route` (+ `queue_summary`). Action enum is broad (includes SIM/airplane
  /payment/messaging/wifi-calling actions).
- **Mobile-data recovery** (`mobile_data_worklist.json`): choose
  `primary_action`, `secondary_action`, `data_refuel_gb`, `charge_amount_usd`,
  `carrier_update_required`, `final_route` (+ `worklist_summary`). Action enum is
  narrower and centered on data/roaming/device-setting fixes.

Use only the action enum the current template lists. Output cases in **ascending
case_id order**.

## Records to pull per case

- `GET /api/cases/<case_id>` → `customer_id`, `line_id`, `device_id`,
  `issue_type` (NO_SERVICE / MOBILE_DATA / SLOW_DATA / MMS), `customer_location`
  (home / abroad), `summary`.
- `GET /api/lines/<line_id>` → `status` (Active/Suspended), `suspension_reason`,
  `roaming_enabled` (line-level roaming), `plan_id`, `data_used_gb`.
- `GET /api/devices/<device_id>` → device flags: `mobile_data_enabled`,
  `phone_roaming_enabled` (device-level roaming), `data_saver_mode`,
  `network_mode_preference`, `vpn_connected`, `sim_status`, `signal_strength`,
  `can_send_mms`, `mmsc_url_present`, `messaging_permissions.{sms,storage}`,
  `airplane_mode`, `wifi_calling_enabled`, `speed_test`.
- `GET /api/bills` → find the customer's bill; an `Overdue` bill drives billing
  recovery and its `amount_due_usd` is the charge.
- `GET /api/plans/<plan_id>` → `data_refueling_price_per_gb`, `data_limit_gb`
  (needed for refuel charge math).

## Decision order (highest-priority blocker first)

Evaluate gates before device tweaks — a suspended line or a missing SIM
dominates whatever the device flags say.

1. **Suspended line / billing.** Line `status == "Suspended"` (e.g.
   `suspension_reason == "OVERDUE_BILL"`) or an Overdue bill:
   - `primary_action = SEND_PAYMENT_REQUEST`,
     `secondary_action = RESUME_LINE_REBOOT` (request payment, then resume the
     line), `bill_id` = the overdue bill, `charge_amount_usd` =
     bill `amount_due_usd`, `final_route = BILLING_RECOVERY`.
2. **SIM / no-service hardware.** `issue_type == NO_SERVICE` with
   `sim_status` missing/inactive (and signal `none`):
   - `primary_action = RESEAT_SIM`, route `SELF_SERVICE`. (If airplane mode is
     on, `TOGGLE_AIRPLANE_MODE` is the airplane-mode variant.)
3. **Otherwise classify by `issue_type` and the offending device/line flag**
   (see action map below).

If nothing is actionable from records, or the situation needs a human,
`primary_action = TRANSFER_HUMAN` / `NO_ACTION` with route `HUMAN_TRANSFER`.

## Action map (device-setting and connectivity fixes)

Pick the single setting that is wrong for the reported symptom:

| issue_type / symptom | offending flag | primary_action | route |
|---|---|---|---|
| MOBILE_DATA, abroad | line `roaming_enabled == false` | ENABLE_LINE_ROAMING (line-level; a carrier update) | CARRIER_UPDATE, `carrier_update_required=true` |
| MOBILE_DATA, abroad | device `phone_roaming_enabled == false` (line roaming OK) | TOGGLE_ROAMING (device toggle) | SELF_SERVICE / DEVICE_SETTING_FIX |
| MOBILE_DATA, home | device `mobile_data_enabled == false` | TOGGLE_MOBILE_DATA | DEVICE_SETTING_FIX |
| MOBILE_DATA, over data cap | `data_used_gb` > plan `data_limit_gb` | REFUEL_DATA (see charge math) | DATA_RECOVERY |
| SLOW_DATA | device `vpn_connected == true` | DISCONNECT_VPN | SELF_SERVICE / DEVICE_SETTING_FIX |
| SLOW_DATA | device `data_saver_mode == true` | TOGGLE_DATA_SAVER | DEVICE_SETTING_FIX |
| SLOW_DATA | device `network_mode_preference == "3g_only"` (older mode) | SET_NETWORK_MODE | DEVICE_SETTING_FIX |
| MMS | `can_send_mms == false` due to a `messaging_permissions` gap | GRANT_MESSAGING_PERMISSION (+ permission) | SELF_SERVICE |

Distinctions that matter:
- **Line roaming vs device roaming.** When abroad, check line `roaming_enabled`
  first. If the *line* lacks roaming → `ENABLE_LINE_ROAMING` and it is a
  **carrier update** (`carrier_update_required = true`, route CARRIER_UPDATE).
  If the line already has roaming but the *device* `phone_roaming_enabled` is
  off → `TOGGLE_ROAMING` (device, self-service, no carrier update).
- **MMS permission value.** Set `permission` to whichever messaging permission
  is missing on the device: `sms`, `storage`, `sms_and_storage`, or `NONE`. If
  only `messaging_permissions.storage == false` → `storage`; if only `sms` is
  false → `sms`; if both → `sms_and_storage`; otherwise `NONE`.
- **Secondary action** is usually `NO_ACTION` for a single-fix case; it is used
  for genuine two-step flows (e.g. payment then `RESUME_LINE_REBOOT`).

## Charge math

- **Most actions cost the customer $0.00** (`charge_amount_usd = 0.00`).
- **Billing recovery:** `charge_amount_usd` = the Overdue bill's
  `amount_due_usd`. The customer pays the overdue balance.
- **Data refuel:** `charge_amount_usd` = `data_refuel_gb` ×
  plan `data_refueling_price_per_gb`. Use the customer-accepted refuel amount
  when the payload provides one (e.g. `customer_preferences.<case>.
  accepted_refuel_gb`); set `data_refuel_gb` to that amount. Respect
  `does_not_want_plan_change` (refuel, do not upsell a plan). Example: accepted
  2.0 GB on a plan at $2.00/GB → `data_refuel_gb = 2.0`,
  `charge_amount_usd = 4.00`.
- Respect the template precision: `charge_amount_usd` two decimals,
  `data_refuel_gb` one decimal (0.0 when not applicable).

## Final route enums

- Queue family `final_route`: SELF_SERVICE | BILLING_RECOVERY | CARRIER_UPDATE |
  HUMAN_TRANSFER.
- Worklist family `final_route`: DATA_RECOVERY | CARRIER_UPDATE |
  DEVICE_SETTING_FIX | HUMAN_TRANSFER.
  - Data refuel → DATA_RECOVERY; line-roaming enable → CARRIER_UPDATE; a pure
    device toggle (mobile data, data saver, network mode, device roaming, VPN) →
    DEVICE_SETTING_FIX.

## Summary / rollup

Recount from your rows:
- Queue: `self_service_fixes`, `billing_recoveries`, `carrier_updates`,
  `human_transfers` (one bucket per row based on `final_route`).
- Worklist: `data_refuel_cases`, `carrier_updates`, `device_setting_fixes`,
  `human_transfers`, and `total_estimated_customer_charge_usd` = sum of all
  `charge_amount_usd` (two decimals).
