---
name: licensing-review
description: "Structured eligibility decisions for state licensing board tasks involving contractor applications, liquor license reviews, and alcohol renewal queues. Use when the task requires cross-referencing REST endpoint data against policy thresholds, identifying deficiency codes and required actions from live records, and producing JSON outputs that conform to a supplied answer template. Triggers on licensing examiner, contractor board, liquor license, alcohol renewal, batch eligibility, or staff review package phrasing."
license: MIT
compatibility: designed for deepagents-code
---

# Licensing Review

## Overview

This skill covers three licensing review workflows seen in state board tasks:
contractor batch eligibility, restricted-liquor staff packages, and alcohol
renewal manual-review queues.  Every workflow follows the same core pattern:
gather all endpoint data, cross-reference against regulatory policies,
flag deficiencies, and assemble a structured JSON output that matches the
supplied answer template.

**Always read the task prompt carefully.**  It supplies target application or
license identifiers, the review date boundary (when relevant), the required
answer template, and the available REST endpoints.

## Core Gathering Pattern

Every workflow starts by fetching all listed GET endpoints for the domain.
Do this in parallel when possible.  Do not skip an endpoint because the task
seems simple — later records often surface a hidden deficiency.

If `POST /api/sql` is listed and the environment provides a credential,
use it for targeted queries that the GET endpoints do not directly answer
(e.g. cross-filtering by date range, joining across entities, or checking
stale records).  The header is `X-Task-Token` with the credential value
from the environment instructions.

## Domain Workflows

### 1. Contractor Batch Eligibility

Use when the task lists contractor application IDs (e.g. C-TR*-*, C-DIS-*)
and references `/api/contractor/*` endpoints.  The output is a batch
`application_decisions` array with a `summary` object.

Detailed reference: [references/contractor-review.md](references/contractor-review.md)

### 2. Restricted-Liquor Staff Package

Use when the task names a single liquor application (e.g. L-TR*-*, L-DIS-*)
and a location ID (LOC-*), with `/api/liquor/*` endpoints.  The output is
a staff package with posture, risk codes, obligations, a 90-day plan, and
escalation triggers.

Detailed reference: [references/liquor-review.md](references/liquor-review.md)

### 3. Alcohol Renewal Queue

Use when the task lists alcohol license numbers (AL-TR*-*, AL-DIS-*)
with a release boundary date and references `/api/alcohol/*` and
`/api/renewal/rules` endpoints.  The output is a ranked `queue` array
with a `summary` object.

Detailed reference: [references/renewal-review.md](references/renewal-review.md)

## Output Discipline

- Return only the JSON object.  No prose, markdown, comments, or extra keys.
- Match every field name and nesting level in the answer template exactly.
- Use empty arrays `[]` when no codes or IDs apply to a field, never `null`
  or omitted keys.
- Sort enumerations as the answer template prescribes (usually ascending
  lexical or by a date/id ordering).
- Keep summary fields consistent with the per-application decisions they
  summarize.
