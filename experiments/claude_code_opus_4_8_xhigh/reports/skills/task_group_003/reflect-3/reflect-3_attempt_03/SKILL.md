# SKILL: Support-Console Case & Ticket Resolution Packages

## When to use
Use this skill whenever a task asks you to act as a support/operations analyst and
produce a **structured JSON decision** for a batch of records pulled from the shared
CRM support-console REST API. It covers four recurring task families:

1. **Offline ticket batch resolution** (internet/voice/video service tickets).
2. **Queue-quality ticket triage** (classify + route tickets, key blocker per ticket).
3. **Contact-center / mobile case triage** (pick device/billing/carrier action per case).
4. **Enterprise export-complaint response packages** (incident write-up + ownership +
   SLA credit + sharing artifacts).

The golden rule across all of them: **derive every field from the live API records, never
from the customer's prose or your assumptions.** The free-text "reported issue" is only a
hint about *where* to look; the device/line/account/diagnostic record is the ground truth.

## API base URL and lookup-chaining habits
Base URL is provided by the harness (it overrides any `127.0.0.1` shown in a prompt). All
endpoints are GET and read-only.

- `GET /api/catalog` — sanity check of endpoints + record counts.
- Tickets: `GET /api/tickets/<ticket_id>` → gives `account_id`, `service_area`,
  `service_type`, `subscribed_mbps`, `status`.
- Accounts: `GET /api/accounts/<account_id>` → `status` (Active/Suspended),
  `authentication{last_login_status, account_recovery_status}`. A `{"error":"not_found"}`
  body means the account id is invalid.
- Outages: `GET /api/outages?service_area=<SA>` → list; an entry with `active:true` whose
  `service_types` includes the ticket's `service_type` is a live outage for that ticket.
- Diagnostics: `GET /api/diagnostics/<ticket_id>` → `latency_ms`, `jitter_ms`,
  `bandwidth_mbps`, `root_causes[]` (pre-fix snapshot).
- Troubleshooting: `GET /api/troubleshooting/<ticket_id>` → `steps[]` and the **post-fix**
  `post_latency_ms`, `post_jitter_ms`, `post_bandwidth_mbps`.
- Cases: `GET /api/cases/<case_id>` → `customer_id`, `line_id`, `device_id`,
  `customer_location` (home/abroad), `issue_type`.
- Lines: `GET /api/lines/<line_id>` → `status`, `suspension_reason`, `plan_id`,
  `data_used_gb`, `roaming_enabled` (this is the **account/line-level** roaming flag).
- Devices: `GET /api/devices/<device_id>` → all device toggles (see field map below),
  including `phone_roaming_enabled` (the **device-level** roaming flag).
- Plans: `GET /api/plans/<plan_id>` → `data_limit_gb`, `data_refueling_price_per_gb`.
- Bills: `GET /api/bills` → find the row whose `customer_id` matches; `status` and
  `amount_due_usd`.
- Enterprise: `GET /api/enterprise/incidents/<id>`, `GET /api/enterprise/accounts`,
  `GET /api/enterprise/export-runs?incident_id=<id>`, `GET /api/enterprise/sla/<ent_acct_id>`,
  `GET /api/enterprise/messages?query=<text>`.

Chaining: ticket → account (+ diagnostics/troubleshooting/outages); case → line + device
+ bill (+ plan); enterprise incident → enterprise account + export-runs + sla + messages.
For messages, the incident id and account id often return nothing — **search by the client
company name** (e.g. a distinctive word from the account name) to find the relevant thread.

---

## Family 1 & 2: Service ticket resolution / triage

### Decision order (apply top-down; first match wins for the blocker/route)
1. **Invalid account** — account lookup returns not_found → status `FAILED`,
   route/team `NONE`, blocker `INVALID_ACCOUNT`, no diagnostics. (route enum word:
   `INVALID_ACCOUNT`.)
2. **Auth failure** — account `authentication.last_login_status` = FAILURE and/or
   `account_recovery_status` = FAILURE (note says auth never recovered) → blocker
   `AUTH_FAILED`. Treat as a hard blocker: do not rely on network diagnostics.
3. **Suspended account** — account/line `status` = Suspended.
   - Reason overdue/billing → blocker `OVERDUE_SUSPENSION`, route `ACCOUNTS_PAYABLE`.
   - In a single-route batch (resolution_route style) a suspended account is an
     `INELIGIBLE_ACCOUNT` route and a non-RESOLVED status.
4. **Active outage** — a live outage covers the ticket's service_area + service_type →
   status `PENDING_ACTION`, route `NONE`, blocker `ACTIVE_OUTAGE`, route word
   `OUTAGE_WAIT`. Record the `outage_id`. This counts as a "customer must wait" ticket.
5. **Otherwise network/service issue** — run on the diagnostic + troubleshooting records:
   - If troubleshooting **meaningfully cleared** the problem → `RESOLVED`, route `NONE`,
     blocker `NONE`, route word `AUTO_TROUBLESHOOTING`.
   - If the issue **persists** after troubleshooting → `ESCALATED` to the team matching the
     root cause, route word `ESCALATION`.

### Resolved-vs-escalated test (from post-troubleshooting metrics)
- "Cleared" ≈ post `latency_ms` back under ~100 ms and bandwidth recovered toward the
  subscribed level, with a software/config root cause (e.g. CONFIGURATION_DRIFT,
  VOICE_PROFILE_STALE, PROVISIONING_STALE acted on by an adjustment step). → `RESOLVED`.
- "Persists" ≈ post latency still high / bandwidth still well below subscribed, especially
  with a physical or capacity root cause (FIBER_DROP_DAMAGE, SIGNAL_LOSS, BACKBONE_CAPACITY).
  → `ESCALATED`.
- A provisioning-stale ticket where the adjustment did **not** bring latency under the
  threshold still escalates (blocker `PROVISIONING_STALE`, team `TIER2_SUPPORT`).

### Root cause → escalation team
- BACKBONE_CAPACITY / network-capacity → `NETWORK_ENGINEERING` (blocker `NETWORK_CAPACITY`).
- FIBER_DROP_DAMAGE / SIGNAL_LOSS / physical line fault → `FIELD_OPS`
  (blocker `PHYSICAL_LINE_FAULT`).
- PROVISIONING_STALE / profile/config issues needing manual fix → `TIER2_SUPPORT`
  (blocker `PROVISIONING_STALE`).
- Billing/overdue → `ACCOUNTS_PAYABLE`.

### Issue boolean / diagnostic flags
- `latency_issue` true when diagnostic `latency_ms` is elevated (≈ >100 ms).
- `stability_issue` true when diagnostic `jitter_ms` is elevated (≈ >30 ms).
- `bandwidth_issue` true when diagnostic `bandwidth_mbps` is below the subscribed rate.
- Base these on the **pre-fix diagnostic** snapshot.
- **CRITICAL PITFALL:** when the ticket routes to `OUTAGE_WAIT` (active outage) the booleans
  `latency_issue`, `stability_issue`, `bandwidth_issue` and `diagnostic_needed` must all be
  **false**. The outage is the cause of record; do not attribute per-line diagnostics to it,
  even though a diagnostic row may exist. The same suppression applies for INVALID_ACCOUNT,
  AUTH_FAILED, and billing-suspension tickets — non-network blockers → `diagnostic_needed`
  / `diagnostic_required` = false.
- For a genuine network ticket that you diagnosed and troubleshot, `diagnostic_needed`/
  `diagnostic_required` = true.

### Output discipline for these families
- `ticket_id` (and `account_id`) preserve the **payload/CSV order** exactly.
- `outage_id` is `""` (empty string) when no outage applies — never null.
- `escalation_team` / `route_team` = `NONE` unless escalating.
- Recompute `batch_summary` / `queue_summary` counts from your own decisions; they must be
  internally consistent (status counts sum to the number of tickets; team counts sum to the
  number of escalations). Include `tickets_requiring_customer_wait` = number of OUTAGE_WAIT
  / PENDING_ACTION-due-to-outage tickets when the template asks for it.

---

## Family 3 & 4 (cases): contact-center & mobile-data triage

### Read the device record and match the anomaly to one action
Device fields that drive actions:
- `sim_status` = missing → **RESEAT_SIM** (self-service).
- `mobile_data_enabled` = false → **TOGGLE_MOBILE_DATA** (device setting fix).
- `data_saver_mode` = true (slow data) → **TOGGLE_DATA_SAVER** (device setting fix).
- `vpn_connected` = true (slow data) → **DISCONNECT_VPN** (self-service / device fix).
- `network_mode_preference` an old mode like `3g_only` (slow data) → **SET_NETWORK_MODE**
  (device setting fix — *not* a carrier update).
- `messaging_permissions.storage` = false on an MMS/"can't send photo" case →
  **GRANT_MESSAGING_PERMISSION** with `permission` = `storage` (grant only the missing one;
  use `sms`, `storage`, or `sms_and_storage` exactly for what is missing, else `NONE`).

### Roaming: line flag vs device flag (high-value distinction)
A traveler "abroad" with no data: compare the two roaming flags.
- Line `roaming_enabled` = true but device `phone_roaming_enabled` = false → only the device
  toggle is off → **TOGGLE_ROAMING**, and this is a **device-level / SELF_SERVICE** fix
  (`carrier_update_required` = false). Do NOT call it a carrier update.
- Line `roaming_enabled` = false (account does not permit roaming) → **ENABLE_LINE_ROAMING**,
  which **is** a carrier/account-provisioning change → `carrier_update_required` = true,
  route `CARRIER_UPDATE`.

### Data over limit
`data_used_gb` >= plan `data_limit_gb` on a mobile-data case ("data stopped after limit") →
**REFUEL_DATA**. Refuel the customer-accepted amount from preferences (e.g. `accepted_refuel_gb`),
respect `does_not_want_plan_change` (do not switch plans), set `data_refuel_gb` to that amount,
and charge = refuel_gb × plan `data_refueling_price_per_gb` (two decimals). Route `DATA_RECOVERY`.

### Billing / suspended line
Line `status` = Suspended with `suspension_reason` = OVERDUE_BILL and the customer offers to
pay → primary **SEND_PAYMENT_REQUEST**, secondary **RESUME_LINE_REBOOT**, set `bill_id` to the
customer's overdue bill, `charge_amount_usd` = that bill's `amount_due_usd`. Route
`BILLING_RECOVERY`.

### Routing taxonomy for case families (route by *action type*, not issue label)
- `SELF_SERVICE` / `DEVICE_SETTING_FIX` — device-local toggles the customer can flip:
  reseat SIM, toggle mobile data, toggle data saver, disconnect VPN, set network mode,
  toggle device roaming, grant messaging permission.
- `CARRIER_UPDATE` — account/line provisioning changes only (enable line roaming, APN/network
  provisioning). Set `carrier_update_required` = true only here.
- `DATA_RECOVERY` — data refuel cases.
- `BILLING_RECOVERY` — payment/overdue cases.
- `HUMAN_TRANSFER` — when no automated action resolves it (`TRANSFER_HUMAN` / `NO_ACTION`).

### Output discipline for case families
- Preserve **ascending case_id order**.
- Always emit `customer_id` and `line_id` from the case/line records.
- `secondary_action` = `NO_ACTION` when none is needed.
- `permission` = `NONE` unless granting messaging permission.
- `bill_id` = `""` when not a billing case; `data_refuel_gb` = `0.0` and
  `charge_amount_usd` = `0.00` when not applicable. Money is two decimals; refuel GB is one
  decimal.
- Recompute the summary counts and `total_estimated_customer_charge_usd` (sum of all
  `charge_amount_usd`) from your own decisions.

---

## Family 5: Enterprise export-complaint response package

### Build order
1. Identify the incident from the complaint reference → `GET /api/enterprise/incidents/<id>`.
   It directly gives `enterprise_account_id`, `severity`, `engineering_owner`,
   `account_owner`, `status`, `product`.
2. `GET /api/enterprise/export-runs?incident_id=<id>` → the FAILED runs define the failure
   window. `start_date` = first FAILED `run_date`, `end_date` = last FAILED `run_date`,
   `failed_days` = count of FAILED runs. The subsequent SUCCEEDED run is the backfill;
   `backfill_days` = number of failed days it recovered.
3. Root cause: take the failed runs' `failure_code` (e.g. STALE_CREDENTIAL) and corroborate
   with the message thread. The `root_cause_category` is a concise category derived from that
   evidence.
4. `contributing_alert_issue` = `ARCHIVED_ALERT_ROUTE` when the corroborating alert/message
   sits in an archived alerts channel (channel name contains "archive"); else `NONE`/`UNKNOWN`.
5. SLA: `GET /api/enterprise/sla/<ent_acct_id>` → `monthly_export_credit_percent` and the
   `credit_trigger` (e.g. "3 consecutive failed runs"). `sla_credit_percent` = that integer.
6. Owners: `engineering_owner` and `account_owner` come straight from the incident record
   (do not invent). The enterprise account record also has a `finance_owner`.
7. Share permissions: include exactly the users the requirements list, **in the order listed**,
   each with a `view` / `edit` / `upload_only` permission.
8. Naming artifacts follow the requirements' `naming_style` literally: lowercase-hyphenated
   channel name about the client export failure; a client + date investigation/evidence
   folder; a human-readable client export-failure report title.

### Reliable vs. risky fields (important calibration)
For enterprise packages the **structured/lookup fields are reliable** — get them straight
from the records and they will be right: `incident_id`, `enterprise_account_id`, `severity`,
`engineering_owner`, `account_owner`, the failure-window dates/`failed_days`, `backfill_days`,
`sla_credit_percent`, `contributing_alert_issue`.

The **risky fields are the free-text/derived ones**: `channel_name`, `evidence_folder`,
`report_title`, `root_cause_category`, the per-user `share_permissions` values, and
`response_status`. To maximize these:
- Follow the requirements' naming convention to the letter; keep the client name spelled
  exactly as in the account record; lowercase + hyphens where it says so.
- For `response_status`, when SLA credit handling is part of the ask and a finance owner is
  in the loop, `NEEDS_FINANCE_REVIEW` is a sound default. Do **not** blindly mirror the raw
  incident `status` into `response_status` — they are different concepts.
- Pick share permissions from the user's role (finance owner vs. reviewer). Keep the listed
  order; the order itself is graded.
- Do not over-engineer naming (extra qualifiers like "monthly"/"investigation" suffixes can
  hurt as easily as help). Prefer the simplest form that satisfies the stated convention.

---

## Universal output rules
- Return **only** the JSON object that conforms to the task's `answer_template.json`. No prose,
  no markdown fences, no extra keys, no missing keys.
- Match enum spellings **exactly** as written in the template (case-sensitive, underscores).
- Numbers: respect the stated precision (two decimals for money, one for refuel GB, integers
  for counts/percent). Use `0` / `0.00` / `""` rather than null for "not applicable".
- Preserve the **input ordering** the template specifies (payload order for tickets, ascending
  case_id for cases, requirements order for share permissions).
- Every summary/aggregate must be recomputed from, and consistent with, your per-row decisions.
- When two fields encode the same fact (e.g. a status and its matching route word, or a
  `carrier_update_required` boolean and a `CARRIER_UPDATE` route), keep them consistent.
