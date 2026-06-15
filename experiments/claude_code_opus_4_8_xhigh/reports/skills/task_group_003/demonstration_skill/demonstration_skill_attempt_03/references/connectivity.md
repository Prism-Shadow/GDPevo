# Connectivity Ticket Triage — Families A & B

Covers ticket-batch resolution (A) and queue classification (B). Both triage
service tickets (internet / voice / video) and share the same gate order and the
same diagnostic math; they differ only in output field names and enum vocabulary.

## Records to fetch per ticket

- `/api/tickets/<ticket_id>` → `account_id`, `service_area`, `service_type`,
  `subscribed_mbps`, `issue_summary`.
- `/api/accounts/<account_id>` → `status`, `authentication.last_login_status`,
  `authentication.account_recovery_status`. (404 / `{"error":"not_found"}` means
  the account is invalid — note the input may use a non-`ACC-` id like `BAD-####`.)
- `/api/outages?service_area=<service_area>` → list; check `active` and
  `service_types`.
- `/api/diagnostics/<ticket_id>` → pre-fix `latency_ms`, `jitter_ms`,
  `bandwidth_mbps`, `root_causes[]`.
- `/api/troubleshooting/<ticket_id>` → post-fix `post_latency_ms`,
  `post_jitter_ms`, `post_bandwidth_mbps`, `steps[]`.

## Gate order (stop at first match) — see SKILL.md for the full description

1. account not found → FAILED / INVALID_ACCOUNT
2. auth failure (`last_login_status == "FAILURE"` or
   `account_recovery_status == "FAILURE"`) → FAILED / AUTH_FAILED
3. `status != "Active"` (Suspended/etc.) → FAILED. Sub-reason from ticket text:
   "overdue" → OVERDUE_SUSPENSION → team/route ACCOUNTS_PAYABLE;
   "fraud" → FRAUD_SUSPENSION. (Family A: route INELIGIBLE_ACCOUNT, team NONE.)
4. active matching outage → PENDING_ACTION / ACTIVE_OUTAGE / OUTAGE_WAIT,
   set `outage_id`. Matching = `active == true` AND ticket `service_type` in
   the outage's `service_types`.
5. otherwise → run diagnostics logic below.

Only tickets that reach step 5 have `diagnostic_needed` / `diagnostic_required`
true. Gated tickets (steps 1–4) have it false and carry no issue flags.

## Diagnostic flag thresholds ("support conventions")

Compute these from the **pre-fix** `/api/diagnostics/<id>` values. A flag is true
when the metric is out of spec:

| Flag | Condition |
|---|---|
| `latency_issue` | `latency_ms > 100` |
| `stability_issue` | `jitter_ms > 30` (jitter is the stability proxy) |
| `bandwidth_issue` | `bandwidth_mbps < 0.80 * subscribed_mbps` (the **bandwidth floor** is 80% of the subscribed plan speed) |

These same three checks define "out of spec." A ticket is **healthy** only if all
three are within spec.

## RESOLVED vs ESCALATED

After diagnostics, troubleshooting steps run automatically and write post-fix
metrics. Re-apply the SAME three threshold checks to the **post-fix**
troubleshooting numbers (`post_latency_ms`, `post_jitter_ms`,
`post_bandwidth_mbps`, against the same `0.80 * subscribed_mbps` floor):

- **All three within spec after the fix → RESOLVED.** Route AUTO_TROUBLESHOOTING,
  team NONE, no escalation.
- **Any metric still out of spec after the fix → ESCALATED.** Troubleshooting did
  not clear the fault, so route to a human team based on the diagnostic
  `root_causes` (see routing table). Route ESCALATION.

This is why the *pre-fix* numbers set the issue flags but the *post-fix* numbers
decide resolved-vs-escalated: the flags describe the reported problem, the
post-fix numbers describe whether the automated remediation worked.

## Escalation-team / blocker routing (by diagnostic root cause)

| Root cause in diagnostics | Family A `escalation_team` | Family B `route_team` | Family B `key_blocker` |
|---|---|---|---|
| `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS` (physical line) | FIELD_OPS | FIELD_OPS | PHYSICAL_LINE_FAULT |
| `BACKBONE_CAPACITY` (network capacity) | NETWORK_ENGINEERING | NETWORK_ENGINEERING | NETWORK_CAPACITY |
| `PROVISIONING_STALE` (provisioning / config) | TIER2_SUPPORT | TIER2_SUPPORT | PROVISIONING_STALE |
| `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE` and similar soft faults | usually fixed by troubleshooting → RESOLVED (team NONE) | NONE | NONE |

Heuristic when a root cause is unfamiliar: physical/hardware faults → FIELD_OPS;
core-network / capacity faults → NETWORK_ENGINEERING; provisioning / profile /
config faults that survive troubleshooting → TIER2_SUPPORT. A RESOLVED ticket
always has team NONE and blocker NONE.

Note: `GENERATED_NOISE` / `GENERATED_*` root causes appear on filler records that
are not part of a task batch; only act on tickets actually listed in the payload.

## Output field reference

### Family A — `ticket_decisions[]` (preserve payload order)

| Field | Meaning |
|---|---|
| `ticket_id`, `account_id` | echo from payload/ticket |
| `final_resolution_status` | RESOLVED \| PENDING_ACTION \| ESCALATED \| FAILED |
| `diagnostic_needed` | true only if the ticket reached the diagnostics step (gates 1–4 all passed) |
| `latency_issue`/`stability_issue`/`bandwidth_issue` | from pre-fix thresholds; all false when no diagnostics were run (gated) |
| `outage_id` | the active outage id at gate 4, else `""` |
| `escalation_team` | NONE \| TIER2_SUPPORT \| FIELD_OPS \| NETWORK_ENGINEERING \| ACCOUNTS_PAYABLE |
| `resolution_route` | AUTO_TROUBLESHOOTING \| OUTAGE_WAIT \| ESCALATION \| INELIGIBLE_ACCOUNT \| AUTH_FAILED \| INVALID_ACCOUNT |

`batch_summary`: counts of each status across decisions, plus
`tickets_requiring_customer_wait` = number of PENDING_ACTION (outage-wait) tickets.

### Family B — `ticket_decisions[]` (preserve payload order)

| Field | Meaning |
|---|---|
| `ticket_id` | echo |
| `final_resolution_status` | RESOLVED \| PENDING_ACTION \| ESCALATED \| FAILED |
| `route_team` | NONE \| TIER2_SUPPORT \| FIELD_OPS \| NETWORK_ENGINEERING \| ACCOUNTS_PAYABLE |
| `key_blocker` | NONE \| ACTIVE_OUTAGE \| INVALID_ACCOUNT \| AUTH_FAILED \| OVERDUE_SUSPENSION \| FRAUD_SUSPENSION \| NETWORK_CAPACITY \| PROVISIONING_STALE \| PHYSICAL_LINE_FAULT |
| `diagnostic_required` | true only if the ticket reached the diagnostics step |

`queue_summary`: counts per status (FAILED / PENDING_ACTION / RESOLVED /
ESCALATED) AND per team (TIER2_SUPPORT / FIELD_OPS / NETWORK_ENGINEERING /
ACCOUNTS_PAYABLE). Count every team key the template lists, including zeros.

### Status / route correspondence

| Outcome | Status | A route | B blocker | team |
|---|---|---|---|---|
| account not found | FAILED | INVALID_ACCOUNT | INVALID_ACCOUNT | NONE |
| auth failure | FAILED | AUTH_FAILED | AUTH_FAILED | NONE |
| suspended (overdue) | FAILED | INELIGIBLE_ACCOUNT | OVERDUE_SUSPENSION | ACCOUNTS_PAYABLE |
| suspended (fraud) | FAILED | INELIGIBLE_ACCOUNT | FRAUD_SUSPENSION | (per policy) |
| active outage | PENDING_ACTION | OUTAGE_WAIT | ACTIVE_OUTAGE | NONE |
| fixed by troubleshooting | RESOLVED | AUTO_TROUBLESHOOTING | NONE | NONE |
| not fixed, physical | ESCALATED | ESCALATION | PHYSICAL_LINE_FAULT | FIELD_OPS |
| not fixed, capacity | ESCALATED | ESCALATION | NETWORK_CAPACITY | NETWORK_ENGINEERING |
| not fixed, provisioning | ESCALATED | ESCALATION | PROVISIONING_STALE | TIER2_SUPPORT |

Note the asymmetry for suspended-overdue: status is FAILED but it is still routed
to ACCOUNTS_PAYABLE (the account can be recovered by clearing the bill).
