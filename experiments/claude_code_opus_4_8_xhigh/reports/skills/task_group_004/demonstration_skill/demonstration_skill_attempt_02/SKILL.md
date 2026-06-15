---
name: apexcloud-retention-ops
description: >-
  Operating procedure for the ApexCloud Retention Operations API (http://127.0.0.1:8074). Use this
  skill WHENEVER a task asks you to build, score, or summarize anything in the ApexCloud retention /
  customer-success / revenue-ops domain: renewal risk queues, retention action boards, QBR metric
  packets, receivables + pipeline operations reviews, churn-model validation, outreach rankings, or
  board/leadership summaries. Trigger it even when the request only mentions pieces of this world
  (current ARR, "clean" ticket counts, latest NPS, overdue/A-R aging buckets, risk_score / risk_level,
  primary_action, reason_codes, expansion pipeline, win rate, policy_codes like RS-6 / REV-4 / SUP-8 /
  ACT-5 / RCP-7 / CM-5 / MOD-7, or account ids like acct_*). These tasks share fixed business
  conventions that are easy to get wrong from intuition; this skill encodes the exact, verified rules.
---

# ApexCloud Retention Operations SOP

This skill captures the **business conventions** for the ApexCloud Retention Operations environment.
The data is realistic but full of traps (decoy CRM lookalikes, spam/cancelled tickets, retracted NPS,
multiple revenue sources, several aging buckets). The grader checks exact numbers, controlled enum
labels, sort order, and fixed `policy_codes`. Reproduce the **rules**, never guess.

All data comes from the read-only HTTP API. Do not read local files. Health/base:

```
GET http://127.0.0.1:8074/api/health      # row counts + seed, good sanity check
```

## How to approach any task

1. **Identify the task family** (decides output shape, enums, and which `policy_codes` to emit):
   - Renewal Risk Queue / Retention Action Board -> the **risk model** (RS/REV/SUP/ACT, + board extras)
   - QBR Metrics Packet -> per-month metric packet (sources/agenda enums, no risk score)
   - Receivables & Pipeline Operations Review -> A/R + CRM linking + pipeline + HR/event context (RCP/CM/PW/FS)
   - Churn Model Validation & Outreach Ranking -> CSV exports + logistic model (MOD/PRB/DEP/OUT)
2. **Pull the canonical fields** using the verified definitions below (current ARR, clean tickets,
   latest NPS, overdue balance). These four are reused everywhere and are the most common source of error.
3. **Apply the family-specific procedure** (see `references/playbook.md` for full step-by-step recipes,
   formulas, and the per-family `policy_codes`).
4. **Match output exactly**: only the keys in the answer template, controlled enums verbatim, currency
   2 decimals, percentages 1 decimal, counts and risk scores as integers. Respect the requested sort.

`references/playbook.md` is the detailed companion — read it for the family you are working on. It also
contains the worked rule-derivations and edge cases. The four canonical definitions below are the heart
of the system, so they live here.

## The four canonical field definitions (memorize these)

### 1. Current ARR -> latest POSTED billing snapshot (NOT the account record, NOT CRM)
`GET /api/billing/snapshots?account_id=<id>` returns quarterly snapshots. **current_arr =
`billing_arr` of the snapshot with the greatest `as_of` date that is `posted == true` AND
`as_of <= assessment/as-of date`.**

- Do NOT use `account.billing_arr_current` (a rounded headline number) and never use `account.crm_arr`.
- Example: assessment 2026-06-30 -> use the `2026-06-30` (Q2) snapshot, e.g. 1416439.47, not the
  account's 1425000.0 and not the later Q3/Q4 snapshots.
- The QBR task is the one exception for *monthly* revenue: it uses `recognized_revenue` from the
  metrics endpoint, but still labels the source enum `crm_closed_won` (see playbook).

### 2. Clean support ticket count -> count tickets minus hygiene exclusions
`GET /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`. **clean_ticket_count = tickets where
NONE of these hold: `is_spam == true`, `is_duplicate == true`, `status == "cancelled"`.**

- Do NOT use `metrics.support_ticket_count` — it is a different (unfiltered) number.
- Per-month QBR ticket counts also use this cleaned set, bucketed by `created_date[:7]`.

### 3. Latest NPS -> latest *valid* monthly reading, with detractor/recovery logic for `nps_drop`
The latest NPS value to report is the last valid monthly reading. Use `metrics[].nps_score` in month
order, treating `null` AND the sentinel `-1` AND any retracted response as **missing**; take the last
non-missing month. (The `/nps` endpoint corroborates this; exclude `retracted == true` and `score < 0`.)

- `nps_drop` reason code fires when: `latest_valid_monthly_nps < 50` **AND**
  (every valid monthly reading was `< 50` **OR** the latest month is not a recovery, i.e.
  `latest <= previous valid reading`). A score that dipped below 50 but rose at the end (e.g. 51->44->46)
  does NOT count as a drop; a series stuck in the detractor band (e.g. 17->39, or 28->29) does.
- If no valid reading exists, report `null` and do not fire `nps_drop`.

### 4. Overdue balance -> ONLY the older aging buckets
`GET /api/finance/ar-aging?as_of=YYYY-MM-DD`. Each row has `current, 1_30, 31_60, 61_90, 90_plus`.
**overdue_balance = `61_90` + `90_plus`** (the "older aging buckets"). Do NOT include `current`,
`1_30`, or `31_60`. A client is "overdue" only when `61_90 + 90_plus > 0`.

- A/R rows have NO `account_id`; they key on `customer_name`. Link to CRM by **exact `legal_name`
  match** to an account — never fuzzy-match aliases (lookalikes like "Globex North Subsidiary LLC" or
  "North Star Finance Services" are deliberate decoys and stay `unlinked`).

## Retention risk model (one model, two output families)

Used by the Renewal Risk Queue and the Retention Action Board. Compute boolean risk factors, sum
weighted points (cap 100), bucket into a level, map to an action, and emit the reason codes that fired.
This reproduces every train score exactly; full point table and edge cases are in the playbook.

**Risk factors (and the reason code each one emits):**
- `renewal_window`: renewal_date is in the future within 90 days, i.e. `0 <= (renewal_date - as_of) <= 90`.
- `overdue_receivable`: overdue_balance (`61_90 + 90_plus`) > 0.
- `nps_drop`: see canonical definition #3 above.
- `sla_degradation`: ANY clean ticket has `first_response_sla_met == false` OR `resolution_sla_met == false`.
- `usage_decline`: latest-month `product_usage < first-month` AND latest-month `product_usage < ~62`
  (a low-usage floor; steep declines that stay above the floor do NOT count).
- `low_tenure_high_churn`: `contract_tenure_months < 18`.
- `expansion_offset`: account has open expansion pipeline whose opp `close_date` is inside the window
  (`state == "open"` and close_date in [window_start, window_end]); emits as an offsetting reason.
- `clean_billings`: overdue_balance == 0. (Informational; included as a reason ONLY in the Renewal Risk
  Queue family, never in the Action Board family.)

**risk_score** = segment base + factor points, capped at 100:
`renewal_window +25, overdue_receivable +15, nps_drop +15, sla_degradation +15, usage_decline +10,
low_tenure_high_churn +10`; segment base: Strategic +20, Enterprise +5, Mid-Market / SMB +0.
(`expansion_offset` and `clean_billings` add 0 points; they surface as reasons only.)

**risk_level thresholds:** `critical >= 80`, `high 50-79`, `medium 30-49`, `low < 30`.

**primary_action priority ladder:**
1. In the Action Board family ONLY: if `risk_level == low` -> `no_action`.
2. Else if overdue_balance > 0 -> `collections_followup`.
3. Else if a *significant* SLA problem exists (any first-response miss, OR any SLA miss on a
   P1/P2/P3 ticket) -> `technical_recovery`.
4. Else if in renewal window (only minor SLA issues, e.g. a lone P4/resolution-only miss) -> `renewal_save`.
5. Else -> `nurture_monitor`.
(`executive_qbr` exists in the enum for high-touch strategic escalations but did not fire in training.)

**Sort / tie-break:** order by `risk_score` descending, then `current_arr` descending. The Renewal Risk
Queue returns the top 5; the Action Board returns all requested accounts in this same order.

**reason_codes order** (apply consistently): `renewal_window, overdue_receivable, nps_drop,
sla_degradation, usage_decline, low_tenure_high_churn, expansion_offset, clean_billings`.

## Fixed policy_codes (always emit these exact values for the matching family)

These are constants, not computed — emit them verbatim when the answer template asks for them.

| Family | policy_codes |
|---|---|
| Renewal Risk Queue | `risk_model_code=RS-6, arr_source_code=REV-4, support_hygiene_code=SUP-8, action_priority_code=ACT-5` |
| Retention Action Board | the four above **plus** `board_sort_code=BORD-4, exposure_formula_code=EXP-6, calendar_policy_code=CAL-5` |
| Receivables & Pipeline Review | `receivable_trigger_code=RCP-7, crm_match_code=CM-5, pipeline_window_code=PW-6, followup_scope_code=FS-4` |
| Churn Validation & Ranking | `model_protocol_code=MOD-7, probability_scale_code=PRB-4, deployment_rule_code=DEP-5, outreach_mapping_code=OUT-2` |
| QBR Metrics Packet | (no policy_codes block) |

## Common pitfalls (these cost exact-match points)

- Using `account.billing_arr_current` / `crm_arr` instead of the latest posted billing snapshot.
- Counting all tickets (or `metrics.support_ticket_count`) instead of cleaned tickets.
- Summing ALL overdue buckets instead of just `61_90 + 90_plus`.
- Fuzzy-linking A/R lookalikes to CRM accounts (only exact `legal_name` links).
- Treating NPS `-1` / `null` / retracted as real, or using a flat NPS threshold without the recovery rule.
- Computing SLA compliance from `metrics.sla_compliance` (QBR SLA% is derived from clean tickets'
  first-response SLA — see playbook).
- Emitting `clean_billings` in the Action Board family, or `no_action` in the Renewal Risk Queue family.
- Forgetting the `current_arr` descending tie-break, or returning more/fewer rows than requested.
- Inventing policy_codes instead of using the fixed values above.

Always read `references/playbook.md` for the exact recipe of the family you are solving, including the
QBR, receivables/pipeline, and churn procedures and their precision rules.
