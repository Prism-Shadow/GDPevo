---
name: portfolio-review
description: Portfolio review, SLA aging audit, and release readiness assessment for engineering work-item environments. Use when the task involves (1) closed-work portfolio-mix review with target-comparison and gap analysis, (2) SLA compliance audit with overdue detection, aging distribution, and breach-rate calculation, or (3) release readiness assessment with ship/no-ship decisions, milestone completion, blocker analysis, and dependency-chain traversal.
license: MIT
compatibility: designed for deepagents-code
---

# Portfolio Review

## Overview

This skill covers three review workflows against a shared engineering work-item
environment accessed via REST endpoints and a restricted SQL query endpoint.
Every workflow requires fetching data from the environment, filtering primary
work from duplicates and cancelled items, ignoring stale mirror/export fields,
and computing answers to strict rounding and sorting conventions.

## Universal Rules

These rules apply across all three workflows:

- **Use the helper script** [scripts/query.py](scripts/query.py) for all HTTP
  calls. Set `TASK_ENV_BASE_URL` to the value supplied in the task prompt before
  invoking it. All GET endpoints are public; `POST /api/query` requires header
  `X-Env-Token: portfolio-readonly`.
- **Ignore mirror fields**. Never use `mirror_status`, `mirror_category`, or any
  mirror/export field for status or classification. Always use the authoritative
  `status`, `category`, `type`, `labels`, and `title` fields.
- **Exclude duplicates**. Any work item where `duplicate_of` is non-null is a
  duplicate. Do not count it in primary populations. Report duplicates in the
  exclusion/cluster sections the answer schema requires.
- **Exclude cancelled items**. Any work item where `status` is `cancelled` must
  be excluded from primary counts and reported separately.
- **Category resolution**. When type, labels, and title conflict, the `category`
  field is authoritative, then `type`, then `labels`, then `title`.

## Workflow Reference Files

Each workflow has its own detailed procedure. Read the relevant file when the
task matches that domain:

- **Portfolio mix review** -- [references/portfolio-mix.md](references/portfolio-mix.md)
- **SLA aging audit** -- [references/sla-aging.md](references/sla-aging.md)
- **Release readiness** -- [references/release-readiness.md](references/release-readiness.md)

For endpoint and field documentation, see [references/environment.md](references/environment.md).

## Precision Rules

| Measure | Rounding | Example |
|---------|----------|---------|
| Percentages (completion, mix, gap) | **1 decimal place** | `66.7` |
| Rates and scores (breach rate, readiness score) | **3 decimal places** | `0.545` |
| Integer counts | Exact integer | `4` |

## Sorting Conventions

- Work item IDs: lexicographic ascending.
- Team arrays: alphabetical.
- Category rows (`gap_table`, `mix_table`): fixed order NewFeature, TechDebt,
  Reliability, Security.
- Under-invested categories: most negative gap first.
- Milestone completion: by `milestone_id` ascending.
- Duplicate clusters: by `primary_id` ascending, with `duplicate_ids`
  lexicographically ascending within each cluster.
- Escalation queues: severity descending (S1 first), then age descending.
