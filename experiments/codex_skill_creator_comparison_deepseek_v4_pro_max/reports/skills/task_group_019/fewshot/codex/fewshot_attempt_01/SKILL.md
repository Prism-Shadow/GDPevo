---
name: licensing-review
description: Structured licensing review for state regulatory boards. Covers contractor eligibility batches, restricted liquor license staff packages, and alcohol renewal manual-review queues. Use when the task involves reviewing licensing applications with determination codes, deficiency flags, risk tiers, or renewal ranking against a boundary date, especially when a JSON answer template is provided with enum vocabularies and the environment exposes GET endpoints under /api/ plus an optional POST /api/sql.
---

# Licensing Review

## Overview

This skill covers three licensing-review domains typical of state regulatory boards. Each domain pulls records from a task-specific HTTP data service, cross-references related records per application, and produces a structured JSON decision that strictly matches the provided `answer_template.json`.

## Quick-Start Workflow

1. Read `input/payloads/answer_template.json` — it defines the **exact output shape** and the **allowed enum values** for every code list.
2. Read `input/prompt.txt` — it names the target applications, the review date or boundary date, and which endpoints are available.
3. Identify the domain from the endpoints and application-id patterns:
   - **Contractor** — endpoints under `/api/contractor/`, application ids like `C-TR*-*`. See [references/contractor.md](references/contractor.md).
   - **Liquor** — endpoints under `/api/liquor/`, application ids like `L-TR*-*`. See [references/liquor.md](references/liquor.md).
   - **Alcohol renewal** — endpoints under `/api/alcohol/` and `/api/renewal/`, license ids like `AL-TR*-*`. See [references/alcohol_renewal.md](references/alcohol_renewal.md).
4. Follow the domain-specific reference to pull records, cross-reference them, assign codes from the template's allowed values, and build the output.

## Environment Setup

Every task provides `<TASK_ENV_BASE_URL>` in the prompt. Set the base URL before calling any endpoint:

- Base URL: use the value from the prompt verbatim (typically `http://task-env:9019`).
- All GET endpoints are public (no auth).
- POST `/api/sql` requires header `X-Task-Token`; use the value from `environment_access.md` (search for `X-Task-Token`).

Always pull `/api/policies` first when it is listed. Policies may change the compliance baseline and affect deficiency detection.

## Output Rules (all domains)

- Return **only** the JSON object — no markdown fences, no prose, no citations.
- Order application-level items by `application_id` or `license_no` ascending, or by `rank` ascending for queues, exactly as the template instructs.
- Sort every code list and id list in the order the template specifies (typically ascending lexical/numeric).
- Use **empty arrays** (`[]`) when no codes or ids apply — never `null` or omitted keys.
- When the template provides allowed enum values, use **only** those values. Do not invent codes.
- For dates, use `YYYY-MM-DD`.

## General Pattern: Read All Records Before Deciding

For any domain, follow this sequence:

1. GET all relevant collections (applications, bonds, insurance, violations, etc.) in parallel.
2. Optionally issue POST `/api/sql` queries for focused lookups when the GET collections are large or when the answer template asks for data not easily extracted from GET results.
3. Cross-reference records by application/license id.
4. Walk the template's allowed code list and check each condition that could trigger that code.
5. Assign determination/posture, codes, risk tier, and summary fields.
