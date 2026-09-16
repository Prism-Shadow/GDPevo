---
name: northstar-payer-ops
description: Complete structured authorization, appeals, claim-repricing, peer-to-peer, and margin-analysis tasks for Northstar Health Plan payer operations. Use when the task references the Northstar payer-operations environment, involves prior authorization cases, pharmacy appeals, payment integrity corrections, P2P summaries, or UM margin-queue analysis, requires the bearer token pa-review-token-014, uses SQL /sql/query or REST business endpoints, and asks for a structured JSON determination matching an answer template.
---

# Northstar Payer Operations

Completes structured payer-operations tasks against the shared Northstar payer
environment. Every task follows the same four-phase workflow: collect records
from the environment, evaluate business criteria, compute the structured
determination, and build a source-precedence audit trail.

## Environment Access

The environment is reachable at the URL provided in the task, typically through
a `<TASK_ENV_BASE_URL>` reference in the task context. Use the environment
exclusively for records; do not inspect filesystem databases or construction
scripts.

**SQL access.** Use `POST /sql/query` on the environment base URL with the
header `Authorization: Bearer pa-review-token-014`. The request body is a JSON
object with a `"query"` string field containing the SQL statement. All business
records live in the environment database. Collect every record referenced by
the task context before evaluating criteria.

**REST endpoints.** The environment may expose business endpoints that return
structured JSON. Available endpoints are listed in the environment access
instructions for the specific task or can be discovered via `GET /` or
`GET /portal`. Prefer REST endpoints when the exact record is available through
them; fall back to SQL for cross-record queries, filtered collections, and ad
hoc lookups.

**Bearer token.** The same token `pa-review-token-014` works for both the SQL
endpoint and all REST business endpoints on this environment.

## Four-Phase Workflow

Execute these phases in order, completing each before moving to the next.

### Phase 1: Collect Records

Read the task prompt, task context payload, and answer template. Identify every
entity type the task touches: cases, policies, clinical documents, appeals,
claims, claim lines, rate schedules, margin rows, P2P events, assistance
programs, drug trials, or authorization records.

Query the environment for every relevant record. Join related records through
the environment API (SQL JOINs or REST relationships). Collect field-level
values needed to evaluate criteria, compute numeric results, and populate the
answer template. Pay attention to version fields, effective dates, plan
modifiers, and record staleness indicators, since these drive source-precedence
decisions later.

### Phase 2: Evaluate Criteria

Each task domain has a specific set of criterion IDs. Read the domain guide at
[references/domains.md](references/domains.md) for the criteria associated with
the task's service domain. For each criterion:

- Check whether the collected records satisfy the criterion's intent.
- Assign one of `met`, `not_met`, `not_applicable`, `unclear`, or `partial`
  following the domain definitions.
- When multiple records address the same criterion, prefer current records over
  stale ones, plan-effective records over expired ones, and patient-specific
  records over generic ones.

**Resolution order when records conflict:**
1. The most recent effective-dated record that matches the plan, modifier, and
   service date.
2. Clinical records with a valid author and signing date over unsigned or
   undated records.
3. Payer-side records (appeals, authorizations) over manufacturer or
   third-party records for the same question.
4. Records explicitly referenced by the case or appeal over ambient records
   from general tables.

### Phase 3: Compute Determination

Translate the criteria results into the structured determination. Populate every
required top-level field from the answer template. Follow the template's enum
choices, ordering rules, and precision requirements exactly.

**Numeric precision.** Dollar amounts round to two decimal places. Ratios round
to four decimal places. Service units are integers.

**Ordering rules.** Follow the ordering specified in the answer template for
each list field: ascending identifier, alphabetical, claim-line order, or
operational precedence order as defined. Do not impose a different ordering.

**Null values.** Use `null` (JSON null) for absent modifiers, inapplicable
deadlines, and fields the template explicitly allows to be null. Do not use
empty strings.

**Boolean fields.** Use JSON `true` or `false`. Default to `false` when the
condition is not met unless the template defines a different default.

### Phase 4: Build Audit Trail

Every task requires a `basis_audit` object with four required keys. Follow the
construction rules in [references/audit.md](references/audit.md). The
source-precedence value selects the dominant decision rule for the task
domain. The controlling and exception record IDs document which environment
records drove the result and which were excluded, stale, or gapped.

## Output Rules

- Return exactly one JSON object with no surrounding markdown, prose, or
  commentary.
- Match the answer template's shape: include every required top-level key,
  respect the enum choices for every constrained field, and do not add fields
  the template marks as disallowed.
- Produce the output as a single file (the agent writes it to disk if needed
  by the caller, but the determination itself is the JSON content).

## Domain-Specific Guidance

When the task domain is not obvious from the prompt, inspect the
`task_context.json` payload: the `service_domain`, `work_type`, or
`requester_role` fields signal the domain. Then read the matching section in
[references/domains.md](references/domains.md), which contains the criteria
definitions, source-precedence rule, enum choices, and domain-specific workflow
notes for each of the five supported domains.

## Quick Reference

| Domain | Signal | Criteria Prefix | Precedence Rule |
|---|---|---|---|
| UM clinical review | `service_domain: "physical_therapy"` or UM nurse | `PT-*` | `current_clinical_records_over_stale_export` |
| Pharmacy appeals | `work_type` references appeal/manufacturer | `DRUG-*` | `payer_appeal_before_manufacturer_assistance` |
| Payment integrity | claim repricing, benchmark | per-line CPT | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer | P2P, peer-to-peer, cardiac PET | `PET-*` | `new_patient_specific_p2p_information` |
| Margin analysis | margin queue, revenue/cost | per-row ratio | `margin_threshold_then_charge_sensitivity` |
