# Connectivity Ticket Resolution & Queue Triage

Covers both ticket families:
- **Resolution** template fields: `final_resolution_status`, `diagnostic_needed`,
  `latency_issue`, `stability_issue`, `bandwidth_issue`, `outage_id`,
  `escalation_team`, `resolution_route` (+ a `batch_summary`).
- **Triage/classify** template fields: `final_resolution_status`, `route_team`,
  `key_blocker`, `diagnostic_required` (+ a `queue_summary`).

They run the SAME gating engine. The only difference is the vocabulary the
template exposes (e.g. resolution uses `resolution_route`
INELIGIBLE_ACCOUNT/AUTH_FAILED/INVALID_ACCOUNT/OUTAGE_WAIT/AUTO_TROUBLESHOOTING/
ESCALATION; triage uses `key_blocker` ACTIVE_OUTAGE/INVALID_ACCOUNT/AUTH_FAILED/
OVERDUE_SUSPENSION/FRAUD_SUSPENSION/NETWORK_CAPACITY/PROVISIONING_STALE/
PHYSICAL_LINE_FAULT/NONE). Always map to the values the current template lists.

## Records to pull per ticket

- `GET /api/tickets/<ticket_id>` → `account_id`, `service_type`, `service_area`,
  `subscribed_mbps`, `issue_summary`.
- `GET /api/accounts/<account_id>` → `status` (Active/Suspended), and
  `authentication.{last_login_status, account_recovery_status}`. A 404 /
  `{"error":"not_found"}` means the account does not exist.
- `GET /api/outages?service_area=<service_area>` → list; an outage counts only
  if `active: true` AND the ticket's `service_type` is in its `service_types`.
- `GET /api/diagnostics/<ticket_id>` → `latency_ms`, `jitter_ms`,
  `bandwidth_mbps`, `root_causes`.
- `GET /api/troubleshooting/<ticket_id>` → `post_latency_ms`, `post_jitter_ms`,
  `post_bandwidth_mbps`, `steps`.

## Gating ORDER (evaluate top-down; the first match decides the ticket)

Stop at the first gate that fires. When a gate fires, the ticket does NOT run
diagnostics: all diagnostic booleans (`diagnostic_needed`/`diagnostic_required`,
`latency_issue`, `stability_issue`, `bandwidth_issue`) are `false`, and
`outage_id` is `""` unless the outage gate itself fired.

1. **Invalid account.** Account lookup fails / id is not a real account.
   → status `FAILED`; blocker/route = INVALID_ACCOUNT; team NONE.

2. **Authentication failure.** Account exists but
   `authentication.last_login_status == "FAILURE"` (and/or
   `account_recovery_status == "FAILURE"`).
   → status `FAILED`; blocker/route = AUTH_FAILED; team NONE.

3. **Suspended account.** `status == "Suspended"`.
   → status `FAILED`. Determine the suspension reason from the ticket
   `issue_summary` / queue note / any related record (e.g. an Overdue bill or a
   line `suspension_reason`):
   - overdue / billing language → blocker = OVERDUE_SUSPENSION,
     team = ACCOUNTS_PAYABLE (if the template offers that team).
   - fraud / security language → blocker = FRAUD_SUSPENSION, team per template.
   - If the template has no suspension-specific blocker (e.g. the resolution
     template), use route = INELIGIBLE_ACCOUNT and team = NONE.

4. **Active covering outage.** An outage in the ticket's `service_area` is
   `active: true` and covers the ticket's `service_type`.
   → status `PENDING_ACTION`; route = OUTAGE_WAIT (resolution) /
   blocker = ACTIVE_OUTAGE (triage); team NONE; set `outage_id` to that
   outage's id (resolution template). This ticket "requires customer wait".

5. **Diagnostics + troubleshooting.** Account is Active, authenticated, not
   suspended, and no covering outage. Now `diagnostic_needed`/
   `diagnostic_required` is `true`. Compute the flags, then decide RESOLVED vs
   ESCALATED from the post-troubleshooting metrics (below).

## Diagnostic flags (support conventions)

Computed from the diagnostics record. These are the threshold conventions
inferred from the data; treat the boundary as "issue when the metric is worse
than the limit":

- `latency_issue`  = `latency_ms` exceeds the latency limit (~**120 ms**).
- `stability_issue` = `jitter_ms` exceeds the jitter limit (~**30 ms**).
  (Jitter is the stability signal.)
- `bandwidth_issue` = `bandwidth_mbps` is below the **bandwidth floor**, where
  the floor = **0.70 × `subscribed_mbps`** (i.e. delivered throughput under 70%
  of the subscribed plan speed).

A ticket that reaches stage 5 is flagged on each metric independently; a ticket
may have any combination of the three booleans true.

## RESOLVED vs ESCALATED (stage-5 outcome)

Apply the troubleshooting steps, then re-test the SAME thresholds against the
*post* metrics (`post_latency_ms`, `post_jitter_ms`, `post_bandwidth_mbps`):

- If the post metrics clear ALL thresholds (post latency ≤ limit AND post jitter
  ≤ limit AND post bandwidth ≥ floor) → the auto-fix worked:
  status `RESOLVED`, route = AUTO_TROUBLESHOOTING, team NONE,
  blocker = NONE, diagnostic flag = true.
- If any post metric still fails → troubleshooting did not resolve it:
  status `ESCALATED`, route = ESCALATION (resolution template), and pick the
  team / `key_blocker` from the diagnostic `root_causes` (below).

## Escalation routing by root cause family

Read the diagnostics `root_causes` (the post-metric failure tells you *that* it
escalates; the root cause tells you *where*):

| root_cause signal | team | triage key_blocker |
|---|---|---|
| FIBER_DROP_DAMAGE, SIGNAL_LOSS (physical line / fiber) | FIELD_OPS | PHYSICAL_LINE_FAULT |
| BACKBONE_CAPACITY (network capacity) | NETWORK_ENGINEERING | NETWORK_CAPACITY |
| PROVISIONING_STALE, CONFIGURATION_DRIFT-style provisioning | TIER2_SUPPORT | PROVISIONING_STALE |

Notes:
- A configuration/profile drift that troubleshooting *fixed* (post metrics now
  pass) resolves via AUTO_TROUBLESHOOTING and is NOT escalated — escalation only
  happens when the post metrics still fail.
- `VOICE_PROFILE_STALE` is a profile refresh that troubleshooting clears →
  typically RESOLVED, not escalated.
- `GENERATED_NOISE` is filler/noise and is never itself a decisive escalation
  category; rely on whether post metrics pass.
- If a root cause is unfamiliar, map it to the closest family above by meaning
  (physical → FIELD_OPS/PHYSICAL_LINE_FAULT; capacity → NETWORK_ENGINEERING/
  NETWORK_CAPACITY; provisioning/config → TIER2_SUPPORT/PROVISIONING_STALE).

## Summary / rollup section

Recount from your own rows:
- Resolution `batch_summary`: count of each `final_resolution_status`
  (RESOLVED/PENDING_ACTION/ESCALATED/FAILED) plus
  `tickets_requiring_customer_wait` = number of tickets in PENDING_ACTION via
  the outage gate.
- Triage `queue_summary`: count of each status AND each `route_team`
  (TIER2_SUPPORT/FIELD_OPS/NETWORK_ENGINEERING/ACCOUNTS_PAYABLE). Teams that
  never appear are `0`.

## Worked logic examples (illustrative — recompute against live records)

- Active account, no outage, latency 142.8 / jitter 33.5 / bw 209 on a 300 Mbps
  plan → all three flags true (142.8>120, 33.5>30, 209<210). Troubleshooting
  brings latency 82 / jitter 21 / bw 272 → all clear → RESOLVED via
  AUTO_TROUBLESHOOTING.
- Active, no outage, post metrics still latency 176 / jitter 41 / bw 332 on a
  500 plan (floor 350) with root_cause FIBER_DROP_DAMAGE → ESCALATED to
  FIELD_OPS (PHYSICAL_LINE_FAULT).
- Account Suspended after an overdue notice → FAILED, OVERDUE_SUSPENSION,
  ACCOUNTS_PAYABLE; diagnostics ignored even though a record exists.
- Account lookup 404 → FAILED, INVALID_ACCOUNT; nothing else evaluated.
