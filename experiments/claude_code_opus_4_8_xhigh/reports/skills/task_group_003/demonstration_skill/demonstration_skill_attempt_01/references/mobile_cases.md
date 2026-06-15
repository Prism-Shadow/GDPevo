# Mobile Cases & Mobile-Data Recovery

Covers two families that iterate over `cases` in the `CUST-*` / `LINE-*` /
`DEV-*` mobile domain:

- **Contact-center cases** — output `case_decisions[]` with `customer_id`,
  `line_id`, `primary_action`, `secondary_action`, `permission`, `bill_id`,
  `charge_amount_usd`, `final_route`, plus `queue_summary`.
- **Mobile-data recovery worklist** — output `case_decisions[]` with
  `primary_action`, `secondary_action`, `data_refuel_gb`,
  `charge_amount_usd`, `carrier_update_required`, `final_route`, plus
  `worklist_summary`.

Both decide an action from the **device/line/bill/plan state**, not the prose
complaint. Read the answer_template to see which keys are required.

## Records you need per case

1. `GET /api/cases/<case_id>` → `customer_id`, `line_id`, `device_id`,
   `issue_type` (NO_SERVICE / MOBILE_DATA / MMS / SLOW_DATA), `customer_location`
   (home / abroad).
2. `GET /api/lines/<line_id>` → `status` (Active/Suspended), `suspension_reason`
   (e.g. `OVERDUE_BILL`, `CONTRACT_ENDED`), `roaming_enabled` (line-side
   roaming), `plan_id`, `data_used_gb`, `device_id`.
3. `GET /api/devices/<device_id>` → device toggles (see signal map below).
4. `GET /api/plans/<plan_id>` → `data_limit_gb`, `data_refueling_price_per_gb`
   (needed for over-limit detection and refuel charge).
5. `GET /api/bills` → find the customer's bill; an `Overdue` bill drives a
   payment request. Bills are keyed by `customer_id` (not account/line).
6. Worklist payloads may include a `customer_preferences` block keyed by
   `case_id` (e.g. `accepted_refuel_gb`, `does_not_want_plan_change`) — honor it.

## Device signal → fix map (the heart of the decision)

Read the device record and key on the concrete field, in roughly this priority
order for the reported issue:

| Observed state (field)                              | Action |
|-----------------------------------------------------|--------|
| `sim_status == "missing"` (no SIM / signal none)    | `RESEAT_SIM` |
| `sim_status == "locked_pin"` (SIM PIN-locked)       | needs a human → `TRANSFER_HUMAN` |
| `airplane_mode == true`                             | `TOGGLE_AIRPLANE_MODE` |
| `mobile_data_enabled == false`                      | `TOGGLE_MOBILE_DATA` |
| abroad + device roaming on but `line.roaming_enabled == false` | `ENABLE_LINE_ROAMING` (carrier-side) |
| abroad + `device.phone_roaming_enabled == false`    | `TOGGLE_ROAMING` (device-side) |
| `data_saver_mode == true` (slow data)               | `TOGGLE_DATA_SAVER` |
| `network_mode_preference` is a legacy mode (e.g. `3g_only`) on slow data | `SET_NETWORK_MODE` |
| `vpn_connected == true` (slow data)                 | `DISCONNECT_VPN` |
| MMS issue: `messaging_permissions.storage == false` or `.sms == false` | `GRANT_MESSAGING_PERMISSION` (set `permission`) |
| MMS issue: `mmsc_url_present == false` / APN broken  | `RESET_APN_REBOOT` |
| over data limit (`line.data_used_gb > plan.data_limit_gb`) | `REFUEL_DATA` |
| line Suspended, `suspension_reason == "OVERDUE_BILL"`, Overdue bill exists | `SEND_PAYMENT_REQUEST` (+ secondary resume) |
| line Suspended for a non-billing reason (e.g. `CONTRACT_ENDED`) | needs a human → `TRANSFER_HUMAN` |
| nothing actionable / out of scope                    | `NO_ACTION` or `TRANSFER_HUMAN` per template |

Always confirm the field rather than trusting the complaint text — e.g. a
traveler may say "roaming is on" but the **line** has `roaming_enabled=false`,
which is the real blocker (`ENABLE_LINE_ROAMING`, a carrier update).

## Secondary action

`secondary_action` is the required follow-up after the primary fix; usually
`NO_ACTION`. The clearest case: clearing an overdue suspension is two steps —
primary `SEND_PAYMENT_REQUEST`, then secondary `RESUME_LINE_REBOOT` to bring the
line back once paid. Only emit a secondary action when the fix genuinely needs a
second operation; otherwise `NO_ACTION`.

## Permission field (contact-center family)

`permission` ∈ {NONE, sms, storage, sms_and_storage}. Set it only with
`GRANT_MESSAGING_PERMISSION`, to exactly the permission(s) the device is
missing: if `messaging_permissions.storage == false` → `storage`; if `.sms ==
false` → `sms`; if both missing → `sms_and_storage`; otherwise `NONE`.

## Charges and refuel math

- **Payment request:** `charge_amount_usd` = the matching **Overdue** bill's
  `amount_due_usd`, and `bill_id` = that bill's id. For all other actions
  `bill_id` is `""` and the charge is `0.00`.
- **Data refuel:** `data_refuel_gb` = the customer's `accepted_refuel_gb` from
  `customer_preferences` when provided. `charge_amount_usd` =
  `data_refuel_gb × plan.data_refueling_price_per_gb`. (Premium plan = $2.00/GB,
  so 2.0 GB → $4.00; always read the plan's actual per-GB price, it varies.)
  When no refuel happens, `data_refuel_gb` is `0.0` and the charge is `0.00`.
- Respect `does_not_want_plan_change`: prefer a refuel over recommending a plan
  upgrade.
- Every charge is two decimals; `data_refuel_gb` is one decimal.

## Final route

Contact-center family `final_route` ∈ {SELF_SERVICE, BILLING_RECOVERY,
CARRIER_UPDATE, HUMAN_TRANSFER}:
- device/line self-fix (reseat, toggles, grant permission, disconnect VPN,
  device-side roaming) → `SELF_SERVICE`
- overdue payment + resume → `BILLING_RECOVERY`
- carrier-side change (enable line roaming) → `CARRIER_UPDATE`
- handed to a person (SIM PIN lock, contract-ended suspension, anything not
  self-resolvable) → `HUMAN_TRANSFER`

Worklist family `final_route` ∈ {DATA_RECOVERY, CARRIER_UPDATE,
DEVICE_SETTING_FIX, HUMAN_TRANSFER}:
- `REFUEL_DATA` → `DATA_RECOVERY`
- `ENABLE_LINE_ROAMING` (carrier-side, `carrier_update_required = true`) →
  `CARRIER_UPDATE`
- device toggle fixes (`TOGGLE_MOBILE_DATA`, `TOGGLE_DATA_SAVER`,
  `SET_NETWORK_MODE`, `DISCONNECT_VPN`, `TOGGLE_ROAMING`) → `DEVICE_SETTING_FIX`
- escalation to a person → `HUMAN_TRANSFER`

`carrier_update_required` is `true` only for carrier-side operations
(enabling line roaming); device-only fixes are `false`.

## Summaries

- Contact-center `queue_summary`: `self_service_fixes`, `billing_recoveries`,
  `carrier_updates`, `human_transfers` = counts of cases by `final_route`.
- Worklist `worklist_summary`: `data_refuel_cases`, `carrier_updates`,
  `device_setting_fixes`, `human_transfers` = counts by `final_route`, plus
  `total_estimated_customer_charge_usd` = the sum of all per-case
  `charge_amount_usd` (two decimals). This must equal the sum you actually
  computed above — re-add it as a check.

## Common misjudgments (exclusion rules)

- **Decide from device/line fields, not the complaint sentence.** The narrative
  is often a near-miss; the record holds the real blocker.
- **Line-side vs device-side roaming are different fixes.** Abroad + line
  roaming disabled → `ENABLE_LINE_ROAMING` + `CARRIER_UPDATE`; abroad + device
  roaming off → `TOGGLE_ROAMING` (device self-service, not a carrier update).
- **Only an Overdue bill (and an `OVERDUE_BILL` suspension) drives a payment
  request.** A `CONTRACT_ENDED` or other non-billing suspension is a human
  transfer, not a payment request — and carries no bill_id/charge.
- **Set `permission` only when granting messaging permission**, and only the
  missing scope(s) — not a blanket value.
- **Refuel charge uses the plan's own per-GB price**, which differs across plans
  ($0.10–$5.00/GB). Don't assume a fixed rate.
- `bill_id` is `""` (empty string) and charge `0.00` for non-billing actions.
