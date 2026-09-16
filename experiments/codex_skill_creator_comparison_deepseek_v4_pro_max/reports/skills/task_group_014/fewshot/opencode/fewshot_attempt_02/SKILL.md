---
name: payer-ops-review
description: Review and adjudicate health-plan payer operations cases using a shared payer environment. Use this skill whenever the user asks you to review a prior-authorization case, prepare an appeal disposition, reprice a claim, summarize a peer-to-peer discussion, analyze a therapy margin queue, or perform any structured payer-operations determination that involves querying a Northstar or similar payer environment, pulling case/policy/clinical/document records, and returning a structured JSON answer with a basis audit trail. Also use this skill when the user provides an answer_template.json and task_context.json for a payer domain workflow, or mentions payer operations, utilization management, pharmacy appeals, payment integrity, peer-to-peer review, or therapy margin analysis.
---

# Payer Operations Review

Follow this general workflow for any payer-operations review task.

## Step 1: Orient to the task

Read the user's prompt, the payload answer template, and any task context payload. The task context gives you the target business ID, reporting date, and domain notes. The answer template defines the exact JSON shape.

Identify:
- The root business record type (case, claim, appeal, P2P, queue)
- The payer domain (utilization management, pharmacy, payment integrity, finance)
- Template enums that constrain your choices

## Step 2: Discover the environment schema

The environment runs at the base URL from the prompt. The SQL endpoint is `POST /sql/query` and uses the bearer token provided. Read [references/environment-interaction.md](references/environment-interaction.md) for endpoint details and interaction patterns.

Start by listing all tables:

```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
```

Follow with a schema inspection of each table and spot-checks of sample rows. Also use REST endpoints to pull records by known IDs.

## Step 3: Pull every record that could matter

Once you know the schema, retrieve all records linked to the target business ID. Use both SQL and REST endpoints as appropriate.

Cover these record types as they appear in the schema:
- **Case records** -- member, plan, provider, request lines, status
- **Policy/criteria records** -- criteria definitions for the service domain
- **Clinical documents** -- evaluation findings, trial results, P2P transcripts
- **Authorization records** -- auth numbers, approved units, dates, CPT codes
- **Rate schedules / benchmarks** -- rate rows for relevant CPT codes and dates; check which is current versus stale
- **Appeal records** -- status, deadline, packet requirements
- **Drug trial / formulary records** -- documented failure rows for the target drug
- **Queue rows** -- only the rows listed in the task context
- **Claim lines** -- line-level paid amounts, units, modifiers

Pull broadly, then narrow. Do not stop at the first record you find.

## Step 4: Evaluate against policy criteria

For each applicable criterion from the policy records:

1. Read the criterion definition
2. Check whether clinical documents satisfy it
3. Classify each criterion as `met`, `not_met`, `unclear`, or `not_applicable`

**When all criteria are met:** the default is approve.

**When any criterion is not met or unclear:** escalate or deny according to the policy. Document which criteria failed and what gap each represents.

**Appeal tasks:** separate documented failures (drugs with clear trial records) from undocumented or insufficient failures (drugs mentioned but without adequate trial documentation).

**Payment integrity:** compare rate-schedule versions and effective dates. Use the current schedule; reject the stale one. Apply unit-level pricing to each claim line.

**P2P tasks:** the central question is whether the P2P discussion introduced new patient-specific information that materially changed the review. If it did not, pre-P2P criteria evaluation controls the result. Flag any PET-specific factors that remain unsupported.

**Finance queue tasks:** compute `total_cost = variable_cost + fixed_cost_allocated`, `margin = revenue - total_cost`, and `revenue_to_cost_ratio = revenue / total_cost`. Flag rows below the revenue-to-cost threshold and rows marked as charge sensitive.

## Step 5: Construct the basis audit

Every answer must include a `basis_audit` with four required keys: `source_precedence`, `controlling_record_ids`, `exception_record_ids`, and `precedence_record_order`.

Read [references/basis-audit.md](references/basis-audit.md) for the full specification, including the six precedence rules, how to select the correct one, and the construction rules for each audit field.

## Step 6: Produce the JSON answer

Follow the answer template exactly:

- **Date format**: `YYYY-MM-DD`. Use `null` only when the template allows it for date fields.
- **Currency**: JSON numbers in USD, rounded to two decimal places. No currency symbols.
- **Modifiers**: Use `null` (not empty string) for absent modifiers.
- **List ordering**: Follow the ordering rule in the template for each list field. When not specified, default to ascending alphabetical or ascending ID order.
- **Enums**: Use exactly one allowed choice. Do not invent variants.
- **Nested objects**: Match every required key. Do not omit required keys even if their value is an empty list.
- **No extra fields**: The answer template defines the allowed surface. Do not add keys beyond what the template specifies.

## Step 7: Validate before returning

Before returning, check:

1. Every required top-level key from the template is present
2. Every enum value is one of the allowed choices
3. List fields follow their stated ordering rule
4. Currency values are numbers (not strings) rounded to two decimals
5. No extra fields beyond the template's allowance
6. The `basis_audit` has all four required keys with the correct precedence rule
7. Controlling and exception records are properly separated -- nothing appears in both lists

Return only the JSON object. Do not wrap it in markdown, add prose, or include commentary.
