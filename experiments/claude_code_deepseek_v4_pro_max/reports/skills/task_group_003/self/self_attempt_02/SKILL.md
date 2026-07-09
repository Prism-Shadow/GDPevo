# Support Console API — Solver Skill

## Overview

This is a **telecom/ISP support console** with three domains connected by shared identifiers:
- **Residential/Business ISP** — tickets, accounts, outages, diagnostics, troubleshooting
- **Mobile** — cases, customers, lines, devices, plans, bills
- **Enterprise** — enterprise accounts, incidents, export runs, messages, SLA contracts

Base URL: read `environment_access.md` — it overrides any localhost references in task text.

## Quick SOP: Diagnose Any Issue

1. Read the task prompt. Identify which domain(s) are involved.
2. Pull the primary record (ticket, case, incident) from its list or detail endpoint.
3. Follow foreign keys through related records.
4. Cross-reference: check outages for the service area, bills for the customer, SLA for the enterprise account.
5. Return **all relevant field values** that explain the root cause — don't stop at the first anomaly.

---

## API Reference

### Base

| Endpoint | Returns |
|---|---|
| `GET /health` | `{"ok": true, "service": "..."}` |
| `GET /api/catalog` | All endpoints, record counts, no seed data |

### ISP / Business Support

| Endpoint | Key Fields |
|---|---|
| `GET /api/accounts` | account_id, name, service_area, status, tier, authentication{last_login_status, last_login_at, account_recovery_status} |
| `GET /api/accounts/<id>` | Same as list + detail. Returns `{"error":"not_found"}` for bad IDs. |
| `GET /api/tickets` | ticket_id, account_id, service_area, service_type, status, subscribed_mbps, issue_summary, created_at |
| `GET /api/tickets/<id>` | Same as list. |
| `GET /api/outages` | All outages (no filter). outage_id, service_area, active, eta_hours, impact_score, service_types[], started_at |
| `GET /api/outages?service_area=<area>` | Filtered by area. Returns `[]` if none. |
| `GET /api/diagnostics/<ticket_id>` | ticket_id, bandwidth_mbps, latency_ms, jitter_ms, root_causes[], started_at, completed_at. **Returns `{}` when absent — NOT a 404.** |
| `GET /api/troubleshooting/<ticket_id>` | ticket_id, steps[], post_bandwidth_mbps, post_latency_ms, post_jitter_ms, started_at, completed_at. **Returns `{}` when absent — NOT a 404.** |

### Mobile Support

| Endpoint | Key Fields |
|---|---|
| `GET /api/cases` | case_id, customer_id, customer_location, device_id, issue_type, line_id, opened_at, summary |
| `GET /api/cases/<id>` | Same detail. `not_found` on miss. |
| `GET /api/customers` | customer_id, name, phone_number, status |
| `GET /api/lines/<id>` | line_id, customer_id, device_id, phone_number, plan_id, status, contract_end_date, data_used_gb, roaming_enabled, suspension_reason |
| `GET /api/devices/<id>` | device_id, model, sim_status, signal_strength, speed_test, mobile_data_enabled, airplane_mode, data_saver_mode, can_send_mms, messaging_permissions{sms,storage}, mmsc_url_present, network_mode_preference, phone_roaming_enabled, vpn_connected, wifi_calling_enabled |
| `GET /api/plans` | plan_id, name, data_limit_gb, monthly_price_usd, data_refueling_price_per_gb |
| `GET /api/plans/<id>` | Same detail. `not_found` on miss. |
| `GET /api/bills` | bill_id, customer_id, amount_due_usd, due_date, status |

### Enterprise

| Endpoint | Key Fields |
|---|---|
| `GET /api/enterprise/accounts` | enterprise_account_id, name, account_owner, finance_owner, tier |
| `GET /api/enterprise/incidents` | incident_id, enterprise_account_id, product, severity, status, summary, received_at, account_owner, engineering_owner |
| `GET /api/enterprise/incidents/<id>` | Same detail. |
| `GET /api/enterprise/export-runs?incident_id=<id>` | run_id, incident_id, enterprise_account_id, run_date, status, exported_record_count, failure_code |
| `GET /api/enterprise/messages?query=<text>` | message_id, author, body, channel, created_at. Substring search on body. |
| `GET /api/enterprise/sla/<enterprise_account_id>` | enterprise_account_id, credit_trigger, monthly_export_credit_percent, executive_contact |

---

## Error Handling Conventions

| Scenario | Response |
|---|---|
| Missing record (accounts, cases, lines, devices, plans, tickets) | `{"error": "not_found"}` (HTTP 200) |
| Missing diagnostics or troubleshooting | `{}` (empty object — **NOT** an error) |
| Missing enterprise incident, SLA, message | `{"error": "not_found"}` |
| Outages with no matching service area | `[]` |
| Export runs with no matching incident | `[]` |

**Critical distinction**: `{}` on diagnostics/troubleshooting means "no data exists." Do not treat it as an error — just means that ticket has no diagnostic/troubleshooting record.

---

## Entity Relationships

```
Ticket ──account_id──▶ Account ──service_area──▶ Outages
Ticket ──service_area──▶ Outages (use ?service_area= filter)
Ticket ──ticket_id──▶ Diagnostics, Troubleshooting

Case ──line_id──▶ Line ──plan_id──▶ Plan
Case ──device_id──▶ Device
Case ──customer_id──▶ Customer ──customer_id──▶ Bill
Line ──device_id──▶ Device
Line ──customer_id──▶ Customer

EnterpriseIncident ──enterprise_account_id──▶ EnterpriseAccount ──enterprise_account_id──▶ SLA
EnterpriseIncident ──incident_id──▶ ExportRuns
Enterprise Messages searchable by query (cross-cutting)
```

---

## ISP Ticket Root Cause → Resolution Map

### Canonical (non-generated) patterns:

| Diagnostic root_cause | Ticket context clue | Troubleshooting step | Expected outcome |
|---|---|---|---|
| `CONFIGURATION_DRIFT` | "intermittent internet", bandwidth below subscribed | `PROFILE_REFRESH` + `PROVISIONING_SYNC` | post_bandwidth improves toward subscribed |
| `BACKBONE_CAPACITY` | "backbone capacity errors", high latency (>200ms) | `BACKBONE_REROUTE_ATTEMPT` | marginal improvement, capacity issue persists |
| `PROVISIONING_STALE` | "provisioning mismatch after move" | `PROVISIONING_ADJUSTMENT` | bandwidth improves |
| `VOICE_PROFILE_STALE` | "voice quality degraded", low bandwidth for voice | `VOICE_PROFILE_REFRESH` | post_bandwidth improves |
| `FIBER_DROP_DAMAGE` | "fiber drop damage suspected" | `SIGNAL_REFRESH` + `LINE_TEST` | physical repair needed, marginal metric improvement |
| `GENERATED_NOISE` | "Generated support ticket" or noise tickets | `GENERATED_CHECK` | random — ignore for deterministic reasoning |

### Key diagnostic thresholds:
- Normal latency: <80ms
- Degraded latency: 80–150ms
- Bad latency: >150ms (especially with high jitter)
- Voice service with bandwidth <100 Mbps is under-provisioned
- Jitter >30ms indicates line quality issues

---

## Mobile Case Diagnostic Decision Tree

### Issue type: `NO_SERVICE`
1. Check `line.status`:
   - `"Suspended"` → read `suspension_reason`:
     - `"OVERDUE_BILL"` → check bill: `GET /api/bills`, find customer's bill with `status: "Overdue"`
     - `"CONTRACT_ENDED"` → check `line.contract_end_date` (is it past?)
   - `"Active"` → check `device`:
2. Check `device.sim_status`:
   - `"missing"` → SIM not detected
   - `"locked_pin"` → SIM PIN locked
   - `"active"` but `signal_strength: "none"` → area outage or hardware

### Issue type: `MOBILE_DATA`
1. If `customer_location: "abroad"`:
   - Check `device.phone_roaming_enabled` (must be `true`)
   - Check `line.roaming_enabled` (must be `true`)
   - Both must be true simultaneously. If either is false, that's the blocker.
2. If `customer_location: "home"`:
   - Check `device.mobile_data_enabled` (must be `true`)
   - Check `line.data_used_gb` vs `plan.data_limit_gb`:
     - Premium plan (PLAN-PREMIUM): limit = 15 GB
     - Family plan (PLAN-FAMILY): limit = 25 GB (shared)
     - If used > limit → over cap
   - Check `device.speed_test: "no_connection"` despite good signal → plan/line issue

### Issue type: `SLOW_DATA`
1. Check `device.data_saver_mode` → if `true`, that throttles data
2. Check `device.network_mode_preference`:
   - `"3g_only"` → limited to 3G speeds
   - `"4g_5g_preferred"` → should be fine, look elsewhere
3. Check `device.vpn_connected` → if `true`, VPN overhead may slow speeds

### Issue type: `MMS`
1. Check `device.can_send_mms`:
   - If `false`:
     - Check `device.messaging_permissions.storage` → must be `true`
     - Check `device.mmsc_url_present` → must be `true` (if false, APN config issue)
   - If `true` but MMS still fails → check `messaging_permissions.sms`

---

## Enterprise Incident SOP

1. Read the incident: `GET /api/enterprise/incidents/<id>`
2. Pull export runs: `GET /api/enterprise/export-runs?incident_id=<id>`
   - Count consecutive `FAILED` runs. Note `failure_code` patterns.
3. Pull messages: `GET /api/enterprise/messages?query=<keyword>` (try product name, "export", "SLA", "credit", account owner name)
4. Pull SLA: `GET /api/enterprise/sla/<enterprise_account_id>`
   - Check if `credit_trigger` condition is met (e.g., "3 consecutive failed export runs")
   - If met, `monthly_export_credit_percent` is the owed credit

### Failure code meanings:
| failure_code | Meaning |
|---|---|
| `STALE_CREDENTIAL` | Credential rotation happened but scheduler not updated |
| `STAGING_STORAGE_QUOTA` | Storage bucket out of quota |
| `TIMEOUT` | Run timed out (still may show SUCCEEDED status) |
| `RATE_LIMIT` | API rate limiting (still may show SUCCEEDED status) |
| `""` (empty) | No failure — clean run |

**Important**: A run can have both `status: "SUCCEEDED"` and a non-empty `failure_code`. The failure_code records what transient error was encountered but overcome. Only `status: "FAILED"` runs with `exported_record_count: 0` count toward SLA triggers.

---

## Common Pitfalls

1. **Empty `{}` on diagnostics/troubleshooting is NOT an error.** It means no record exists. Don't retry or treat as not_found. Generated tickets above ~TCK-8039 typically have no diagnostics.

2. **Account ID mismatch**: Tickets like `TCK-5403` reference `BAD-5403` as account_id. This account doesn't exist — the ticket itself is the anomaly.

3. **Dual roaming check for abroad cases**: BOTH `device.phone_roaming_enabled` AND `line.roaming_enabled` must be `true`. Check both independently — cases often have one true and one false.

4. **SLA triggers are about consecutive FAILED runs**, not total failures. Count the streak of `FAILED` status runs. SUCCEEDED runs with failure_codes do NOT break the streak — only a SUCCEEDED run (with records exported) resets it.

5. **Service type-specific diagnostics**: Voice tickets have different root causes (VOICE_PROFILE_STALE) than internet (CONFIGURATION_DRIFT, BACKBONE_CAPACITY) or video (PROVISIONING_STALE).

6. **Outage overlap**: Always check `/api/outages?service_area=<area>` for tickets. An active outage with the ticket's service_type in its service_types[] is the likely root cause.

7. **Suspended accounts**: Account `status: "Suspended"` is distinct from line `status: "Suspended"`. The former blocks ISP services; the latter blocks mobile service.

8. **Plan IDs use human-readable keys**: `PLAN-PREMIUM`, `PLAN-BASIC`, `PLAN-PLUS`, `PLAN-FAMILY`, not numeric IDs. Generated plans use `PLAN-G0` through `PLAN-G7`.

---

## Effective Query Patterns

```bash
# Start broad, then narrow
curl -s $BASE/api/catalog | jq .record_counts   # understand data scale

# Cross-reference a ticket end-to-end
T=TCK-5107
curl -s $BASE/api/tickets/$T | jq .
A=$(curl -s $BASE/api/tickets/$T | jq -r .account_id)
SA=$(curl -s $BASE/api/tickets/$T | jq -r .service_area)
curl -s $BASE/api/accounts/$A | jq .
curl -s "$BASE/api/outages?service_area=$SA" | jq .
curl -s $BASE/api/diagnostics/$T | jq .
curl -s $BASE/api/troubleshooting/$T | jq .

# Cross-reference a case end-to-end
C=CASE-2101
curl -s $BASE/api/cases/$C | jq .
L=$(curl -s $BASE/api/cases/$C | jq -r .line_id)
D=$(curl -s $BASE/api/cases/$C | jq -r .device_id)
CU=$(curl -s $BASE/api/cases/$C | jq -r .customer_id)
curl -s $BASE/api/lines/$L | jq .
P=$(curl -s $BASE/api/lines/$L | jq -r .plan_id)
curl -s $BASE/api/plans/$P | jq .
curl -s $BASE/api/devices/$D | jq .
# Find bill: search list for customer_id
curl -s $BASE/api/bills | jq ".[] | select(.customer_id==\"$CU\")"

# Enterprise incident analysis
INC=INC-7301
curl -s $BASE/api/enterprise/incidents/$INC | jq .
ENT=$(curl -s $BASE/api/enterprise/incidents/$INC | jq -r .enterprise_account_id)
curl -s "$BASE/api/enterprise/export-runs?incident_id=$INC" | jq .
curl -s $BASE/api/enterprise/sla/$ENT | jq .
curl -s "$BASE/api/enterprise/messages?query=export" | jq ".[] | select(.body | contains(\"$ENT\"))" 
```

---

## Output Conventions

When answering a task:
- State the root cause clearly, referencing specific field values.
- Include the evidence chain: "Ticket TCK-5402 → Account ACC-5402 is Active → Diagnostic shows VOICE_PROFILE_STALE → Troubleshooting applied VOICE_PROFILE_REFRESH, improving bandwidth from 58→91 Mbps."
- For SLA/credit questions, show the math: "3 consecutive FAILED runs (May 25–27) trigger the SLA → 20% credit applies."
- For mobile cases, cite the specific device/line field values that explain the symptom.
- If multiple issues exist, list all of them — don't stop at the first finding.

---

## Distinguishing Canonical from Generated Data

The API contains both hand-crafted canonical records and randomly-generated noise:

**Canonical (deterministic, use for reasoning):**
- Tickets TCK-5107 through TCK-6105 (15 tickets)
- Cases CASE-2101 through CASE-3105 (15 cases)
- Enterprise incidents INC-7301, INC-8301, INC-8402
- Enterprise accounts ENT-3001, ENT-4001, ENT-4102
- Outages OUT-9102, OUT-9401, OUT-9601 (active, high-impact)
- Plans PLAN-BASIC, PLAN-PREMIUM, PLAN-PLUS, PLAN-FAMILY

**Generated (random/noise, ignore for deterministic reasoning):**
- Tickets TCK-8000+ ("Generated support ticket")
- Accounts ACC-7000+ ("Generated Customer NN")
- Enterprise accounts ENT-5000+ ("Generated Enterprise N")
- Incidents INC-9000+ ("Generated enterprise incident")
- Plans PLAN-G0 through PLAN-G7
- Bills BILL-G000+
- Customers CUST-G000+
- Outages OUT-9700+ (mostly inactive, low-impact)
- Diagnostics/troubleshooting with root_cause `GENERATED_NOISE` and step `GENERATED_CHECK`

When a task asks about a specific canonical entity, follow its FK chain through canonical records. When a generated entity is referenced, its diagnostic/troubleshooting data is noise — focus on structural relationships instead.
