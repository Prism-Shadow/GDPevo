---
name: licensing-review
description: Multi-domain licensing review for contractor eligibility, liquor license transfer packages, and alcohol renewal queues. Use when the user asks about licensing applications, license renewals, contractor eligibility review, liquor license review, alcohol renewal queues, or staff licensing packages. Also use when the user mentions licensing boards, restricted licenses, contractor batch review, or renewal manual-review queues. This skill covers the State Contractors Licensing Board, Alcohol Control Board, and Alcohol Renewal Unit workflows.
---

# Licensing Review

Workflows for structured licensing review across three domains: contractor
eligibility batches, restricted liquor-license staff packages, and alcohol
renewal manual-review queues. Every task produces a clean JSON output matching
a supplied answer template.

## Entrypoint Decision

When a task arrives, classify it into one domain by reading the prompt:

1. **Contractor batch eligibility** — mentions "State Contractors Licensing
   Board", "contractor applications", "application ids" starting with `C-`,
   contractor-specific endpoints (bonds, insurance, license-history,
   violations, inspections, correspondence), and answer-template keys like
   `application_decisions`, `deficiency_codes`, `required_actions`.

2. **Liquor license staff package** — mentions "liquor license",
   "restricted", site/location identifiers (`LOC-`), endpoints for liquor
   (applications, settlements, privileges, incidents, site-evidence), and
   answer-template keys like `recommended_posture`,
   `same_premises_basis_applies`, `covered_risk_codes`,
   `verification_gap_codes`, `first_90_day_plan`, `escalation_trigger_codes`.

3. **Alcohol renewal queue** — mentions "renewal", "manual-review queue",
   "release boundary", license numbers starting with `AL-`, endpoints
   for alcohol/licensees and alcohol/violations and renewal/rules, and
   answer-template keys like `queue` with `rank`, `violation_count`,
   `match_confidence`.

If the prompt mixes domains, treat each as a separate evaluation. But typical
tasks are single-domain.

## General Process

For any domain, follow this sequence:

### Step 1: Read the answer template

The prompt always points to `input/payloads/answer_template.json`. Read it
first. It defines:

- Required top-level keys
- Allowed enum values for every field
- Ordering rules (ascending lexical, by rank, chronological, etc.)
- Whether empty arrays are acceptable (`[]`)
- Date formats (always `YYYY-MM-DD`)

Treat the template as the authoritative output schema. Never invent keys,
values, or codes that are not in the template.

### Step 2: Fetch all relevant API records

The prompt lists the exact endpoints to use. Fetch every listed endpoint in
parallel. Use the base URL from `<TASK_ENV_BASE_URL>` or the explicitly given
URL. For the POST `/api/sql` endpoint, include the header `X-Task-Token` with
the credential value from the environment-access instructions.

Always fetch all endpoints even if some seem unnecessary — cross-referencing
across record types is the core of the review.

### Step 3: Cross-reference records by the right join keys

Each domain has its own join logic. See the reference files for details:

- [references/contractor-schema.md](references/contractor-schema.md) for
  contractor domain join keys, policy routing, deficiency rules, action
  mapping, risk-tier logic, and policy-impact logic.
- [references/liquor-schema.md](references/liquor-schema.md) for liquor domain
  join keys, posture rules, risk/gap/obligation/control derivation, 90-day
  plan construction, and escalation-trigger derivation.
- [references/renewal-schema.md](references/renewal-schema.md) for renewal
  domain join keys, boundary filtering, address-matching rules, ranking
  algorithm, risk-tier and next-step-label logic.

### Step 4: Derive determinations from data, not templates

The answer template tells you what values are allowed, but you must derive
which values to use from the actual API records. Do not guess. Every
deficiency code, risk code, gap code, and action must be traceable to a
specific record or absence of a record.

### Step 5: Build the output JSON

Use the exact keys from the answer template. Follow the template's ordering
rules. When a field has no applicable values, use an empty array `[]` (never
`null` or a missing key). When a count is zero, write `0` not `null`.

### Step 6: Return only the JSON object

Do not add commentary, markdown fences, explanations, or additional keys.

## Common Pitfalls

- **Using codes not in the template enum.** The template defines the
  closed vocabulary. If data suggests a gap not covered by any template
  enum, that gap is not reportable in the output.
- **Missing cross-references.** A deficiency often requires checking multiple
  endpoints. For example, a bond shortfall requires checking the bond amount
  against the policy minimum AND the bond status.
- **Ignoring ordering rules.** The grader checks ordering. Follow the template
  exactly: ascending lexical for strings, ascending by rank for queue entries,
  ascending by application_id for application_decisions lists.
- **Confusing active vs. inactive records.** Check `status` fields
  carefully: an `active` bond with insufficient amount is a shortfall; a
  `cancelled` bond is "no active bond". An `expired` insurance policy with a
  date before the review date is "insurance expired" or "insurance not
  current"; a `pending` policy is not yet verified.
- **Forgetting the review date.** When the prompt supplies a review date
  (like 2025-07-18), use it to decide whether financial coverage is
  current. Expired before that date = deficiency. Expiring after = still
  current if status is active.
- **Policy impact needs the legacy policy.** Check whether the current
  policy creates a flag that the legacy/prior baseline policy would not
  have generated. See the contractor reference for the comparison method.
- **Boundary date filtering.** In renewal tasks, exclude violations with
  dates after the boundary. Post-boundary violations go in the summary's
  exclusion list, not in the queue.

## Reference Files

Read the relevant domain reference when you have identified the task domain:

| Domain | Reference |
|--------|-----------|
| Contractor batch eligibility | [references/contractor-schema.md](references/contractor-schema.md) |
| Liquor license staff package | [references/liquor-schema.md](references/liquor-schema.md) |
| Alcohol renewal queue | [references/renewal-schema.md](references/renewal-schema.md) |

If a task spans multiple domains, read all relevant references.
