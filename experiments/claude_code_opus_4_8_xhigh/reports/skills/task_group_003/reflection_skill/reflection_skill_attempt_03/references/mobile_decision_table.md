# Mobile Case / Data-Recovery Decision Table

Read this for mobile support-queue and data-recovery worklist tasks. Expands SKILL.md
section 3.

## Records to fetch per case

| Endpoint | Fields that drive the decision |
|---|---|
| `/api/cases/<case_id>` | `issue_type`, `summary`, `customer_location`, `line_id`, `device_id`, `customer_id` |
| `/api/lines/<line_id>` | `status`, `suspension_reason`, `roaming_enabled`, `data_used_gb`, `plan_id` |
| `/api/devices/<device_id>` | the device flags below |
| `/api/bills` (filter by `customer_id`) | `bill_id`, `amount_due_usd`, `status` (Overdue) |
| `/api/plans/<plan_id>` | `data_limit_gb`, `data_refueling_price_per_gb` |

## Device flags cheat sheet

| Field | Meaning / when it's the culprit |
|---|---|
| `sim_status == "missing"` | SIM dropped out → `RESEAT_SIM` |
| `mobile_data_enabled == false` | data switched off → `TOGGLE_MOBILE_DATA` |
| `phone_roaming_enabled == false` | DEVICE-side roaming off → `TOGGLE_ROAMING` (self-service) |
| `data_saver_mode == true` | throttling data → `TOGGLE_DATA_SAVER` |
| `network_mode_preference == "3g_only"` | stuck on old/slow network → `SET_NETWORK_MODE` |
| `vpn_connected == true` | VPN slowing data → `DISCONNECT_VPN` |
| `can_send_mms == false` | check `messaging_permissions` → `GRANT_MESSAGING_PERMISSION` |
| `airplane_mode == true` | radios off → `TOGGLE_AIRPLANE_MODE` |
| `wifi_calling_enabled` | toggle for call-over-wifi issues → `TOGGLE_WIFI_CALLING` |

## Line flags cheat sheet

| Field | Meaning |
|---|---|
| `status == "Suspended"` + `suspension_reason == "OVERDUE_BILL"` | billing block → payment flow |
| `roaming_enabled == false` | LINE/CARRIER-side roaming off → `ENABLE_LINE_ROAMING` (carrier update) |
| `data_used_gb >= plan.data_limit_gb` | data cap hit → `REFUEL_DATA` |

## The two-layer roaming rule (common trap)

A traveler with "no data abroad" can have the toggle off on EITHER layer. Check both and
fix the one that is `false`:

| device.phone_roaming_enabled | line.roaming_enabled | action | carrier_update | route |
|---|---|---|---|---|
| false | true | `TOGGLE_ROAMING` | false | `SELF_SERVICE` / `DEVICE_SETTING_FIX` |
| true | false | `ENABLE_LINE_ROAMING` | true | `CARRIER_UPDATE` |

Do not default every "abroad" case to the same action.

## Billing-recovery flow (suspended for overdue bill)

- primary `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT` (resume the line after
  payment clears), `bill_id` = the Overdue bill's id, `charge_amount_usd` =
  `bill.amount_due_usd`, route `BILLING_RECOVERY`.

## Data refuel charge

`charge = refuel_gb * plan.data_refueling_price_per_gb`. Use `accepted_refuel_gb` from
`customer_preferences` when present (refuel exactly what the customer agreed to; respect
`does_not_want_plan_change`). `data_refuel_gb` one decimal; `charge_amount_usd` two
decimals; `0.0`/`0.00` when N/A.

## MMS permission

`permission` = which `messaging_permissions` flag is `false`: photos→`storage`, texts→`sms`,
both→`sms_and_storage`, none missing→`NONE`. Enum values are lowercase.

## Route enums and summaries

- Case-queue task routes: `SELF_SERVICE | BILLING_RECOVERY | CARRIER_UPDATE | HUMAN_TRANSFER`.
  Summary: `self_service_fixes`, `billing_recoveries`, `carrier_updates`, `human_transfers`.
- Worklist task routes: `DATA_RECOVERY | CARRIER_UPDATE | DEVICE_SETTING_FIX | HUMAN_TRANSFER`.
  Summary: `data_refuel_cases`, `carrier_updates`, `device_setting_fixes`, `human_transfers`,
  `total_estimated_customer_charge_usd` (sum of charges).
- Note `TOGGLE_MOBILE_DATA` / `TOGGLE_DATA_SAVER` / `SET_NETWORK_MODE` are
  `DEVICE_SETTING_FIX`, not `DATA_RECOVERY`. `DATA_RECOVERY` is the refuel path.
  Recount each summary bucket from your finished rows.
