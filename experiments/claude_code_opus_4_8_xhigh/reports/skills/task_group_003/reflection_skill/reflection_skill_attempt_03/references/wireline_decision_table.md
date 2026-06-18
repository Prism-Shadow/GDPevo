# Wireline Ticket Decision Table

Read this when resolving internet / video / voice service tickets (ticket-batch and
queue-classification tasks). It expands SKILL.md section 2.

## Records to fetch per ticket

| Step | Endpoint | What you use |
|---|---|---|
| 1 | `/api/tickets/<ticket_id>` | `account_id`, `service_type`, `service_area`, `subscribed_mbps` |
| 2 | `/api/accounts/<account_id>` | `status`, `authentication.*` (gates) |
| 3 | `/api/outages?service_area=<area>` | active outage list for the area |
| 4 | `/api/diagnostics/<ticket_id>` | pre-fix `latency_ms`,`jitter_ms`,`bandwidth_mbps`,`root_causes` |
| 5 | `/api/troubleshooting/<ticket_id>` | `steps`, `post_latency_ms`,`post_jitter_ms`,`post_bandwidth_mbps` |

## Gating order (stop at the first that fires)

1. Account not found / malformed id → `FAILED` / `INVALID_ACCOUNT`
2. `authentication` FAILURE → `FAILED` / `AUTH_FAILED`
3. Account `Suspended` → **`FAILED`** + remediation route `ACCOUNTS_PAYABLE`,
   blocker `OVERDUE_SUSPENSION` (or `FRAUD_SUSPENSION`)
4. Active outage whose `service_types` includes the ticket's `service_type` →
   `PENDING_ACTION` / `OUTAGE_WAIT`, fill `outage_id`
5. Else diagnose + troubleshoot → `RESOLVED` or `ESCALATED`

> The #1 mistake is treating a suspended account as ESCALATED because it gets routed to a
> team. Status and route are independent. Account-level blockers (gates 1–3) are always
> `FAILED`. Outage is always `PENDING_ACTION`. `ESCALATED` is reserved for gate 5 where the
> service is technically deliverable but an automated fix did not work.

## RESOLVED vs ESCALATED (gate 5)

Health check on POST-fix troubleshooting metrics:
`post_latency_ms <= 100` AND `post_jitter_ms <= 30` → healthy → `RESOLVED`.
Bandwidth slightly below subscribed is tolerated if latency/jitter are healthy.

If not healthy (or a physical/structural cause an automated step can't repair) → `ESCALATED`:

| Root cause family | Team | key_blocker |
|---|---|---|
| `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, physical line damage | `FIELD_OPS` | `PHYSICAL_LINE_FAULT` |
| `BACKBONE_CAPACITY`, congestion/capacity | `NETWORK_ENGINEERING` | `NETWORK_CAPACITY` |
| `PROVISIONING_STALE`, provisioning mismatch | `TIER2_SUPPORT` | `PROVISIONING_STALE` |
| Auto-fixable (e.g. `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE`) and metrics now healthy | `NONE` | `NONE` (RESOLVED) |

`resolution_route` enum (batch task): `AUTO_TROUBLESHOOTING` (resolved via fix),
`OUTAGE_WAIT`, `ESCALATION`, `INELIGIBLE_ACCOUNT` (suspended), `AUTH_FAILED`,
`INVALID_ACCOUNT`.

## Issue flags (from PRE-fix diagnostics only)

| Flag | Rule |
|---|---|
| `latency_issue` | `diagnostics.latency_ms > 100` |
| `stability_issue` | `diagnostics.jitter_ms > 30` |
| `bandwidth_issue` | `diagnostics.bandwidth_mbps < ticket.subscribed_mbps` |

- Tickets gated at 1–4: all flags `false`, `diagnostic_needed/required` `false`.
- Filler diagnostics (`root_causes == ["GENERATED_NOISE"]`, steps `["GENERATED_CHECK"]`):
  ignore the numbers, flags `false`.

## Summary block

Recount from your finished rows. Typical keys: status counts
(`RESOLVED`/`PENDING_ACTION`/`ESCALATED`/`FAILED`), team counts
(`TIER2_SUPPORT`/`FIELD_OPS`/`NETWORK_ENGINEERING`/`ACCOUNTS_PAYABLE`), and a
`tickets_requiring_customer_wait` = count of outage (`PENDING_ACTION`/`OUTAGE_WAIT`) rows.
Each count must equal the number of rows in that bucket; status counts sum to the row total.
