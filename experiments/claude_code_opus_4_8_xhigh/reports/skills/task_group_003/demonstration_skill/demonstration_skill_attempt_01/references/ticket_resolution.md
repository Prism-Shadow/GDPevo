# Service-Ticket Resolution & Queue Classification

Covers two closely-related families that both iterate over `tickets` in the
`ACC-*` account domain:

- **Batch resolution** — output `ticket_decisions[]` with diagnostic booleans
  (`diagnostic_needed`, `latency_issue`, `stability_issue`, `bandwidth_issue`),
  `outage_id`, `escalation_team`, `resolution_route`, plus `batch_summary`.
- **Queue classification** — output `ticket_decisions[]` with `key_blocker`,
  `route_team`, `diagnostic_required`, plus `queue_summary`.

They share one decision pipeline. The differences are only in which fields each
template asks you to report; the *logic* is identical. Always read the template
to see which keys are required and emit exactly those.

## Records you need per ticket

For each ticket (preserve payload order):

1. `GET /api/tickets/<ticket_id>` → `account_id`, `service_type`
   (internet/video/voice), `service_area` (e.g. `SA-17`), `subscribed_mbps`.
2. `GET /api/accounts/<account_id>` → `status` (Active/Suspended), and
   `authentication.account_recovery_status` /
   `authentication.last_login_status`. A `{"error":"not_found"}` here means the
   account id is invalid.
3. `GET /api/outages?service_area=<service_area>` → list of outages.
4. `GET /api/diagnostics/<ticket_id>` → `latency_ms`, `jitter_ms`,
   `bandwidth_mbps`, `root_causes[]` (only fetch/apply once gates pass).
5. `GET /api/troubleshooting/<ticket_id>` → `post_*` metrics and `steps[]`
   (auto-remediation result; used to confirm an auto-fix path).

## The ordered decision pipeline (gates first, then diagnose)

Evaluate gates **in this order**. The first one that matches sets the outcome,
and you STOP — do not run diagnostics, so the diagnostic booleans stay `false`
and `diagnostic_needed`/`diagnostic_required` is `false`.

1. **Invalid account** — account lookup returns not_found (or the ticket's
   `account_id` does not match the `ACC-*` pattern / has no record).
   → status `FAILED`, route `INVALID_ACCOUNT`, blocker `INVALID_ACCOUNT`,
   team `NONE`.

2. **Auth failure** — account `authentication.account_recovery_status` is
   `FAILURE` (or login status indicates an unrecovered authentication failure).
   → status `FAILED`, route `AUTH_FAILED`, blocker `AUTH_FAILED`, team `NONE`.

3. **Account ineligible / suspended** — account `status` is `Suspended` (or
   otherwise not Active).
   → status `FAILED`.
   - If the ticket note/issue indicates an **overdue/billing** suspension →
     route `INELIGIBLE_ACCOUNT`, blocker `OVERDUE_SUSPENSION`, team
     `ACCOUNTS_PAYABLE` (billing can clear it).
   - If the note indicates a **fraud** suspension → blocker `FRAUD_SUSPENSION`,
     team `NONE` (not recoverable by billing).
   - When the template only has the coarse `resolution_route` enum, use
     `INELIGIBLE_ACCOUNT`. The blocker/route_team granularity is the
     classification family's job.

4. **Active outage** — an outage exists for this `service_area` with
   `active == true` AND the ticket's `service_type` is in the outage's
   `service_types[]`. (Ignore outages that are inactive or for a different
   service type — those are decoys.)
   → status `PENDING_ACTION`, route `OUTAGE_WAIT`, blocker `ACTIVE_OUTAGE`,
   team `NONE`, and record the matching `outage_id`. This ticket counts toward
   `tickets_requiring_customer_wait`.

5. **Diagnostics** — only reached when all gates pass (account Active, no auth
   failure, no matching active outage). Run/read the diagnostic record. From
   here `diagnostic_needed`/`diagnostic_required` is `true`. Compute the
   diagnostic flags (see below) from the **pre-remediation diagnostic** numbers
   (`/api/diagnostics`), NOT the post-troubleshooting numbers. Then route by
   `root_causes[]` (see routing table).

## Diagnostic flag thresholds ("support conventions")

Use the diagnostic record's measured values:

- `latency_issue` = `latency_ms > 100`
- `stability_issue` = `jitter_ms > 30`
- `bandwidth_issue` = `bandwidth_mbps < bandwidth_floor`, where
  **`bandwidth_floor = 0.70 × subscribed_mbps`** (the SLA floor is 70% of the
  subscribed rate). E.g. subscribed 300 → floor 210; subscribed 500 → floor 350.

These flags are reported only in the batch-resolution family. They describe the
diagnostic reading; they do not by themselves decide RESOLVED vs ESCALATED —
the `root_causes[]` do that.

## Root-cause → routing table

`root_causes[]` carries the real fault signal. **`GENERATED_NOISE` is filler /
synthetic noise — it is NOT a real fault; ignore it for routing.** A ticket
whose only root cause is `GENERATED_NOISE` is treated as having no escalating
fault: if it passed the gates, it is an auto-remediation success → `RESOLVED`.

| root_cause                        | meaning                  | outcome | route / team |
|-----------------------------------|--------------------------|---------|--------------|
| `CONFIGURATION_DRIFT`             | config fixable in-band   | RESOLVED | `AUTO_TROUBLESHOOTING`, team `NONE` |
| `VOICE_PROFILE_STALE`             | voice profile refresh    | RESOLVED | `AUTO_TROUBLESHOOTING`, team `NONE` |
| `GENERATED_NOISE` (only)          | noise / no real fault    | RESOLVED | `AUTO_TROUBLESHOOTING`, team `NONE` |
| `FIBER_DROP_DAMAGE` / `SIGNAL_LOSS` | physical line fault    | ESCALATED | `ESCALATION`, team `FIELD_OPS`, blocker `PHYSICAL_LINE_FAULT` |
| `BACKBONE_CAPACITY`               | network capacity         | ESCALATED | `ESCALATION`, team `NETWORK_ENGINEERING`, blocker `NETWORK_CAPACITY` |
| `PROVISIONING_STALE`              | provisioning mismatch    | ESCALATED | `ESCALATION`, team `TIER2_SUPPORT`, blocker `PROVISIONING_STALE` |

Notes:
- The auto-fix outcomes (CONFIGURATION_DRIFT, VOICE_PROFILE_STALE, noise) are
  the ones the troubleshooting step remediates (`steps` like `PROFILE_REFRESH`,
  `PROVISIONING_SYNC`, `VOICE_PROFILE_REFRESH`, `GENERATED_CHECK`); they resolve
  in-band → `RESOLVED`, escalation team `NONE`.
- Physical/capacity/provisioning faults need a human team → `ESCALATED`.
- For escalated tickets, `diagnostic_needed/diagnostic_required` is still `true`
  (a diagnostic was run; it just surfaced a fault that must be escalated).
- If a ticket has multiple real root causes, escalate to the most specialized
  team implied (physical line fault → FIELD_OPS dominates).

## Field definitions (batch-resolution family)

- `final_resolution_status` ∈ {RESOLVED, PENDING_ACTION, ESCALATED, FAILED}.
- `diagnostic_needed` — `true` only if you reached step 5 and ran diagnostics.
- `latency_issue/stability_issue/bandwidth_issue` — per thresholds; all `false`
  when gated out before diagnostics.
- `outage_id` — the matching active outage's id, else `""` (empty string).
- `escalation_team` ∈ {NONE, TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING,
  ACCOUNTS_PAYABLE}.
- `resolution_route` ∈ {AUTO_TROUBLESHOOTING, OUTAGE_WAIT, ESCALATION,
  INELIGIBLE_ACCOUNT, AUTH_FAILED, INVALID_ACCOUNT}.

## Field definitions (queue-classification family)

- `final_resolution_status` — same enum. Mapping from the pipeline:
  PENDING_ACTION (active outage), RESOLVED (auto-fix), ESCALATED (real fault),
  FAILED (invalid/auth/suspended).
- `route_team` ∈ {NONE, TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING,
  ACCOUNTS_PAYABLE}. Note: overdue-suspension routes to `ACCOUNTS_PAYABLE` even
  though the status is `FAILED`.
- `key_blocker` ∈ {NONE, ACTIVE_OUTAGE, INVALID_ACCOUNT, AUTH_FAILED,
  OVERDUE_SUSPENSION, FRAUD_SUSPENSION, NETWORK_CAPACITY, PROVISIONING_STALE,
  PHYSICAL_LINE_FAULT}. A clean RESOLVED ticket has blocker `NONE`.
- `diagnostic_required` — `true` only for tickets that reached diagnostics
  (RESOLVED-by-diagnostic and ESCALATED tickets); `false` for every gated
  outcome (outage, invalid, auth, suspension).

## Summaries

- Batch: `RESOLVED`, `PENDING_ACTION`, `ESCALATED`, `FAILED` are counts of those
  statuses; `tickets_requiring_customer_wait` = count of PENDING_ACTION
  (outage-wait) tickets. The four status counts sum to the ticket count.
- Queue: status counts plus team counts (`TIER2_SUPPORT`, `FIELD_OPS`,
  `NETWORK_ENGINEERING`, `ACCOUNTS_PAYABLE`) — each team count equals the number
  of tickets routed to that team. Teams with no tickets are `0`, not omitted.

## Common misjudgments (exclusion rules)

- **Don't run diagnostics on gated tickets.** If an active outage matches or the
  account is suspended/invalid/auth-failed, all diagnostic booleans are `false`.
  (A suspended account may still have a populated diagnostics record — it is a
  decoy; do not use it.)
- **Don't treat `GENERATED_NOISE` as a fault.** It never escalates.
- **Don't escalate on the diagnostic flags alone.** High latency/jitter/low
  bandwidth with an auto-fixable root cause is still `RESOLVED`.
- **Outage matching is three-way**: active + same service_area + service_type in the
  outage's `service_types`. An inactive outage, or one not covering this
  service type, does not gate.
- **Use pre-remediation diagnostics for the flags**, not the post-troubleshoot
  numbers.
- **Empty string, not null,** for `outage_id` when none applies.
