---
name: support-console
description: Resolve telecom support-console tasks using the shared support-console REST API. Use whenever the task involves support tickets, contact-center cases, enterprise export incidents, queue-quality analysis, mobile-data recovery, or any batch resolution against the support-console API. This skill applies to any prompt that references the support console, its API endpoints, or telecom operations roles like support operations analyst, contact-center lead, enterprise support lead, queue-quality analyst, or mobile-data recovery analyst.
---

# Support Console Skill

Resolve telecom support tasks by reading payloads, querying the support-console REST API, cross-referencing evidence, applying domain decision rules, and producing structured JSON output conforming to a provided answer template.

## When To Use This Skill

This skill is for any task that references the support-console API (`<TASK_ENV_BASE_URL>`) or describes a telecom operations role working a batch of tickets, cases, incidents, or worklists. The skill provides the API surface, response shapes, cross-entity lookup chains, and decision logic you need to resolve each item correctly.

## Workflow

Every task follows the same four-phase pattern, regardless of the specific domain:

### Phase 1: Read the Payload and Template

- Load the payload file (CSV batch, JSON queue, email, or worklist) and the answer template JSON.
- Identify the items to process (tickets, cases, incidents) and the output structure required.

### Phase 2: For Each Item, Build a Lookup Chain

Each item type has a standard chain of API calls needed for full evidence. Start from the item's own endpoint, then follow entity links outward.

- **Ticket** → `/api/tickets/{ticket_id}` → account via `account_id` → `/api/accounts/{account_id}` → check outages for matching service area + type → `/api/diagnostics/{ticket_id}` → `/api/troubleshooting/{ticket_id}`
- **Contact-center case** → `/api/cases/{case_id}` → `/api/customers/{customer_id}` → `/api/lines/{line_id}` → `/api/devices/{device_id}` → `/api/plans/{plan_id}` → `/api/bills` (filter by `customer_id`)
- **Enterprise incident** → `/api/enterprise/incidents/{incident_id}` → `/api/enterprise/accounts/{enterprise_account_id}` → `/api/enterprise/export-runs` (filter by `enterprise_account_id` + `incident_id`) → `/api/enterprise/messages` (filter by incident context) → `/api/enterprise/sla/{enterprise_account_id}`
- **Queue-quality ticket** → same lookup chain as a regular ticket plus deeper account-verification checks
- **Mobile-data case** → `/api/lines/{line_id}` (or find line via customer) → `/api/devices/{device_id}` → `/api/plans/{plan_id}`

### Phase 3: Apply Decision Rules

For each domain, consult the decision patterns in [references/decision-patterns.md](references/decision-patterns.md). The rules map evidence from the API lookups to the enums and fields in the answer template. The rules cover:

- Ticket resolution: outage matching, diagnostic thresholds, escalation routes, account-eligibility checks
- Contact-center routing: device-state → self-service actions, billing → recovery actions, permissions → grants
- Enterprise response: export-run failure windows, root-cause categories, SLA credit calculations, owner assignments
- Queue classification: account validation, blocker identification, team routing
- Mobile-data recovery: plan limits, refuel pricing, device settings, carrier updates

### Phase 4: Produce Structured Output

- Populate the answer template JSON for each item in payload order.
- Compute the queue/batch/worklist summary from the individual item decisions.
- Output only the filled JSON; no surrounding explanation.

## API Reference

All endpoints, response shapes, field meanings, and cross-entity linking conventions are documented in [references/api-reference.md](references/api-reference.md). Read that file when you need precise field names, enum values, or relationship paths.

## Decision Patterns

Reusable decision rules for each task domain are in [references/decision-patterns.md](references/decision-patterns.md). These encode the logic for mapping API evidence to template fields without prescribing specific answer values.

## Key Principles

**Look up, don’t assume.** Every item must be resolved from API records. Do not infer status, identity, or values from the payload text alone. The payload tells you which items to resolve; the API tells you what they mean.

**Check eligibility before proceeding.** An item can be ineligible for resolution: missing account, failed authentication, or invalid account state. Mark these as FAILED with the appropriate route rather than attempting further lookups.

**Cross-reference service area and type against outages.** When a ticket or case references an outage-like symptom, check the active outages list for a matching `service_area` and `service_types` intersection. The outage list is the authoritative source for whether an item is covered by a known incident.

**Read diagnostics for technical tickets.** Internet and video tickets often have diagnostic records that reveal the underlying issue (latency, jitter, bandwidth shortfall, root causes). Use diagnostics to decide between auto-troubleshooting and escalation.

**Preserve payload order.** The answer JSON must list items in the same order they appear in the input payload.

**Use the template exactly.** The answer template defines the required JSON structure. Fill every field; use the enums, types, and formats specified. Do not add extra fields or omit required ones.
