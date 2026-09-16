---
name: private-wealth-advisory
description: Produce structured private-wealth advisory planning outputs (Roth conversion and RMD projections, ILIT Crummey funding cycles, GRAT versus CRAT trust comparisons, and estate liquidity action plans) by querying a task-group advisory REST API. Use when the task prompt mentions a private wealth advisory team, an advisory API base URL (API_BASE), client IDs like CLT-XXXX, and a request memo paired with an answer template JSON.
---

# Private Wealth Advisory

Query the advisory REST API at `$API_BASE` (or the URL the harness provides) to
fetch client records, source documents, retirement accounts, life-insurance
policies, trust candidates, tax policy constants, and RMD factors.  Resolve
conflicting source data, compute key financial projections, and return a single
JSON object that matches the answer template supplied in the task payload.

## Quick Start

1. Read the request memo in the task payload for the client ID, engagement
   type, and any horizon year.
2. Read the answer template (`answer_template.json`) to understand every
   required key and its type.
3. Fetch all relevant API data for the client.  Every list endpoint returns an
   array; filter by `client_id`.  Global endpoints (`/api/policies/tax`,
   `/api/rmd-factors`) return single objects used across all clients.
4. Resolve conflicting source documents following
   [Source Resolution](references/source_resolution.md).
5. Route to the analysis procedure that matches the `analysis_type` in the
   template: see [Analysis Types](references/analysis_types.md).
6. Build the JSON response using resolved values and computed numbers.  Return
   only the JSON object; no prose outside it.

## API Reference

Every endpoint except the portal is JSON.  See
[API Reference](references/api_reference.md) for full response shapes, field
meanings, and filtering patterns.

- `GET /api/clients` — List all clients.
- `GET /api/clients/{client_id}` — Single client record.
- `GET /api/source-documents` — All source documents (CRM notes, attorney
  memos, signed profiles).  Filter by `client_id`.
- `GET /api/retirement-accounts` — All IRA/retirement account records.
  Filter by `client_id`.
- `GET /api/life-insurance` — All life-insurance policies.  Filter by
  `client_id`.
- `GET /api/trust-candidates` — All trust candidate cases.  Filter by
  `client_id`.
- `GET /api/policies/tax` — Global tax-policy constants (one object).
  Always fetch this.
- `GET /api/rmd-factors` — Global RMD life-expectancy factor table (one
  object keyed by age as string).  Always fetch this.

## Source Resolution

The advisory environment may deliver conflicting facts for the same client
because records were imported from different systems at different times.
**Always** resolve conflicts before computing.  See the detailed hierarchy
in [Source Resolution](references/source_resolution.md).

**Quick rule:** Among source documents, prefer `SIGNED_PROFILE` (most
recent, signed by the client), then `ATTORNEY_MEMO`, then `CRM_NOTE`
(= stale marketing import).  For account balances, `CUSTODIAN_EXPORT` is
authoritative.  Where the analysis asks for a *controlling source* field,
record the source type that actually supplied the dominant facts.

## Analysis Types

Four analysis types appear in the evidence.  Each has its own calculations
and output shape.  Follow [Analysis Types](references/analysis_types.md):

- **roth_conversion_rmd** — Staged Roth conversion plan with RMD tax
  projections and legacy balance estimates.
- **ilit_crummey_implementation** — ILIT funding-cycle check covering
  gift-tax exclusion capacity, Crummey notice timing, and estate-inclusion
  risk.
- **trust_comparison** — GRAT versus CRAT numerical comparison with
  estate-context and a client-specific recommendation.
- **estate_liquidity_action_plan** — Combined ILIT plus trust-transfer
  plan with action-set sequencing and liquidity-gap analysis.
