---
name: reflect-3
description: Use this skill for ApexCloud Retention Operations-style tasks that provide a remote environment and ask for a precise JSON answer from customer/account, opportunity, retention, billing, support, NPS, churn, or event datasets. It is especially useful when the task involves staged prompts, remote API discovery, exact output schemas, account alias resolution, active/open exclusions, ARR reconciliation, pipeline rollups, renewal windows, or churn-risk style filtering.
---

# Reflect-3 Retention Operations Skill

Use this skill when a task asks you to answer a retention-operations data question from a remote environment. The work is usually more about careful data access, exact filtering, and exact JSON shape than about producing a narrative analysis.

## Core Workflow

1. Treat the task prompt as the contract.
   Read it for the requested output fields, date window, sort order, inclusion/exclusion rules, rounding, and whether the answer should be a scalar, object, or array. Do not add helpful extra fields unless the prompt explicitly asks for them.

2. Use only the provided remote environment.
   Start from the base URL or environment note supplied with the task. Do not inspect local environment source, evaluator files, hidden data folders, prior run outputs, or neighboring scratch directories.

3. Probe the public API lightly and deliberately.
   Begin with the health/status endpoint if one is available. Use it to learn the service name, seed, and advertised row counts. Then fetch only public data endpoints needed for the task. Confirm each payload's top-level key and row count before analysis.

4. Do not assume advertised filenames are routes.
   A health response may list dataset-like names for inventory, but those names may not be directly downloadable. Prefer documented or discovered API resources. If a route returns a standard `not_found` object, move on instead of spending the task budget on broad brute force.

5. Build a small local analysis table in scratch.
   Save only allowed remote responses or derived notes in the allowed working directory. Use structured parsing (`jq`, Python, Node, or a dataframe) rather than manual string scanning.

6. Normalize identifiers before joining.
   Join account-scoped tables on stable IDs when present. Use display names, legal names, and aliases only for matching user-facing names back to IDs. Preserve the display name requested by the prompt in the final answer.

7. Verify every filter by counting before and after.
   For each exclusion, record the before/after row count in scratch notes while working. This catches common mistakes such as including closed opportunities in pipeline totals or paused accounts in active-customer lists.

8. Return exactly the requested JSON.
   The final answer should usually be raw JSON with no Markdown, no commentary, no endpoint details, and no audit trail. Keep key names, casing, array order, rounding, and date formats aligned with the prompt.

## Endpoint Habits

- Check the health/status resource first. It often exposes row counts and service metadata that help detect incomplete downloads.
- Fetch canonical business resources directly when available, such as accounts and opportunities. Inspect the first record to learn fields instead of guessing.
- Treat route discovery as bounded: try obvious public resource names and query-style variants, but stop once the needed data is available or the service consistently returns `not_found`.
- Do not include environment URLs, private paths, or internal process details in the final answer.
- When a dataset listed in health is not directly exposed, state the limitation only if the user asked for an explanation. For normal evaluated outputs, silently use the accessible task data and the prompt's required schema.

## Output Field Conventions

- Use the prompt's field names exactly. If it asks for `account_id`, do not substitute `id`; if it asks for `display_name`, do not substitute `legal_name`.
- Prefer stable identifiers plus human-readable names for account rows when both are requested.
- Use ISO dates (`YYYY-MM-DD`) and compute date windows inclusively unless the prompt says otherwise.
- Round money and rates only at the final output step. Keep numeric JSON values as numbers, not strings, unless the prompt requests formatted currency or percentages.
- For ranked lists, sort by the requested metric descending, then use a deterministic tie-breaker such as `account_id` or `display_name` ascending.
- For grouped totals, return a predictable order: either prompt-specified order, descending metric order, or alphabetical keys for maps.
- Avoid umbrella summaries. A broad object with counts, rollups, and diagnostic fields can be useful while working, but evaluated answers usually need a narrow schema.

## Common Exclusion Rules

- Open pipeline: include only opportunities whose state/stage is open. Exclude closed-won and closed-lost opportunities unless the prompt asks for historical bookings or loss analysis.
- Active customer base: include active lifecycle accounts only. Exclude paused, implementation/onboarding, churned, inactive, or renewal-risk accounts when the prompt says "active customers" or "current customer base"; include renewal-risk only when risk analysis asks for it.
- Renewal windows: compute from the task's as-of date, not today's system date unless the prompt explicitly says today. Check whether endpoints use future contract dates.
- ARR reconciliation: distinguish CRM ARR from billing/current ARR. Use the specific ARR source named in the prompt and do not mix the two in totals.
- Account matching: collapse aliases to one account ID before aggregating. Do not double-count subsidiaries or alternate legal names.
- Support/NPS/churn/event datasets: filter to the requested date range, segment, region, account status, and response/ticket/event state before ranking or averaging.
- Nulls and missing values: exclude from averages unless the prompt says to treat missing as zero. For sums, missing monetary amounts should usually be treated as absent, not zero-filled, unless the data dictionary says otherwise.

## Pitfalls

- Do not answer from a generic "everything I found" payload. These tasks reward exact, prompt-shaped JSON.
- Do not trust row-count inventory as proof that each table has a direct endpoint.
- Do not infer the answer schema from a previous task. Each staged task may require a different shape.
- Do not leak work notes, endpoint secrets, private paths, or intermediate attempts into the final response.
- Do not use local forbidden folders as a shortcut. If a fact is not available through the prompt or public remote environment, treat it as unavailable.
- Do not let extra keys, Markdown fences, explanatory text, or reordered arrays creep into the final answer.
- Do not round intermediate values before grouping; rounding early can move totals just enough to fail exact checks.

## Final Answer Checklist

Before replying, confirm:

- The output is valid JSON if JSON was requested.
- It contains only the requested keys.
- All joins use stable IDs or carefully resolved aliases.
- All active/open/date-window exclusions were applied.
- Money, rates, counts, and dates use the requested formats.
- Sorting and tie-breaking are deterministic.
- No remote URL, private path, or work note appears in the answer.
