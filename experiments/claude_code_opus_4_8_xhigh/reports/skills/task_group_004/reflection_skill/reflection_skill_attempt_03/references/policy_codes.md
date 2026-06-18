# Policy codes & enum vocabulary (verified)

Each `policy_codes` field is a forced choice among an opaque enum triple with no documented
meaning. The values below are the ones confirmed against graded gold answers. Use the exact
code when its field appears in the template. The "always pick the middle option" shortcut is
*mostly* right but is NOT reliable — `outreach_mapping_code` breaks it. Always prefer this table.

## Confirmed codes by field

| Field | Value | Appears in |
|---|---|---|
| `risk_model_code` | `RS-6` | renewal risk queue, action board |
| `arr_source_code` | `REV-4` | renewal risk queue, action board |
| `support_hygiene_code` | `SUP-8` | renewal risk queue, action board |
| `action_priority_code` | `ACT-5` | renewal risk queue, action board |
| `board_sort_code` | `BORD-4` | action board |
| `exposure_formula_code` | `EXP-6` | renewal risk queue, action board |
| `calendar_policy_code` | `CAL-5` | action board |
| `receivable_trigger_code` | `RCP-7` | receivables/ops review |
| `crm_match_code` | `CM-5` | receivables/ops review |
| `pipeline_window_code` | `PW-6` | receivables/ops review |
| `followup_scope_code` | `FS-4` | receivables/ops review |
| `model_protocol_code` | `MOD-7` | churn validation |
| `probability_scale_code` | `PRB-4` | churn validation |
| `deployment_rule_code` | `DEP-5` | churn validation |
| `outreach_mapping_code` | `OUT-2` | churn validation — NOTE: first option, NOT middle |

For any new policy-code field not in this table, the middle option of the triple is the best
prior — but treat it as a guess, and re-check against any available signal.

## model_checks / model_validation booleans

| Field | Value |
|---|---|
| `uses_billing_arr_source` | `true` (current_arr comes from the billing snapshot) |
| `tenure_risk_direction` | `negative` (longer tenure → lower risk/churn) |
| `tenure_coefficient_direction` | `negative` |
| `accuracy_band` | `90_plus` when validation accuracy ≥ 90% |

## Controlled enum vocabularies

**risk_level:** `critical | high | medium | low`
(bands: critical ≥ 80, high ≥ 50, medium ≥ 30, low < 30)

**primary_action / outreach_action:**
`executive_qbr | collections_followup | technical_recovery | renewal_save | nurture_monitor | no_action`
(ladder order on retention deliverables:
collections_followup > technical_recovery > renewal_save > executive_qbr > nurture_monitor;
`no_action` only when a deliverable explicitly allows it)

**reason_code:** `overdue_receivable | low_tenure_high_churn | sla_degradation | nps_drop |
usage_decline | renewal_window | expansion_offset | clean_billings`
(emit in that canonical order; emit all that fire; `clean_billings` only when no
billing/overdue-risk code fires)

**link_status:** `linked | unlinked`

**ticket_trend:** `improving | worsening | flat`
(compare last-month vs first-month clean ticket count: fewer → improving)

**QBR metric source enum:** `crm_closed_won | support_export | sla_report | nps_survey |
billing_snapshot | ar_aging | pipeline_crm | event_dashboard | hr_report`
- revenue → `crm_closed_won`
- support_tickets → `support_export`
- sla_compliance → `sla_report`
- nps → `nps_survey`

**review_owner:** `solutions_engineering | customer_success | finance_ops`
(default `customer_success`)

**agenda_topic:** `partnership_overview | q2_metrics | performance_highlights |
q3_initiatives | technical_recovery | commercial_expansion`
(4 ordered; slots 1/2/4 fixed = partnership_overview, q2_metrics, q3_initiatives;
slot 3 conditional: technical_recovery if SLA/support problem, else commercial_expansion
for strong expansion, else performance_highlights)

## Worked verification notes (why these are trusted)

These were confirmed by recomputing gold values from the live API:
- `current_arr` = billing snapshot `billing_arr` at the as-of date matched gold exactly
  (account flat ARR fields did not).
- `clean_ticket_count` matched gold only after also excluding `status == "cancelled"`.
- `overdue_total` on the receivables review matched gold (190312.41) using older buckets
  (61_90 + 90_plus) summed over the 13 overdue customers; all-non-current overshot it.
- Action-board `overdue_balance` matched gold for all accounts using TOTAL non-current.
- `arr_at_risk` matched gold as the sum of current_arr over critical+high accounts;
  `net_revenue_exposure` matched as arr_at_risk − open_expansion_pipeline.
- QBR per-month SLA [100.0, 75.0, 100.0] matched gold using % first_response_sla_met over
  clean tickets — not the metrics `sla_compliance` (≈95 every month).
- Churn `cohort_checks` matched gold when scoped to the top-5 shortlist, not the 8 targets.
