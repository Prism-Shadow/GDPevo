---
name: licensing-review
description: >-
  Produce the structured JSON decision for a State licensing review task by
  reading records from the shared licensing HTTP environment. Covers three task
  families served by the same environment: (1) contractor batch eligibility
  reviews, (2) restricted liquor-license staff packages, and (3) alcohol
  renewal manual-review queues. Use whenever a prompt asks for a JSON answer
  conforming to input/payloads/answer_template.json against endpoints like
  /api/policies, /api/contractor/*, /api/liquor/*, /api/alcohol/*,
  /api/renewal/rules, or POST /api/sql.
---

# Licensing review

You are a licensing examiner. Each task gives you (a) a prompt naming target
records and endpoints, and (b) a template at `input/payloads/answer_template.json`
that defines the exact output schema and the **allowed code vocabulary**. Your
job: pull the relevant records from the environment, apply the domain rules, and
emit **only** the JSON the template describes.

There is no single answer format. The template is authoritative — its
`allowed_values` (or `enum`) lists tell you which code strings to emit, its
`ordering` rules tell you how to sort, and its key list tells you exactly which
keys to include. Never invent keys, prose, or codes the template does not list.

## Step 1 — Connect to the environment

Read `environment_access.md` (in the task's working directory). It provides:

- `GDPEVO_ENV_BASE_URL` — base URL for all requests (e.g. `http://task-env:9019/`).
- The header required for SQL: `POST /api/sql` needs `X-Task-Token: <token>`.
- The allowed endpoint list.

Do not hardcode any base URL or token — always read them from
`environment_access.md` for the current task.

`GET` endpoints return a JSON array. **They are capped at 200 rows and silently
truncated** — a full table (bonds, insurance, violations, …) can exceed 200 rows,
so a plain GET may omit records for your targets. To get complete, correct data,
use `POST /api/sql` with a `WHERE` filter that selects only your target ids. See
`references/environment.md` for the SQL interface, the table names (they mirror
the endpoints), the join keys, and the 200-row handling. **Always prefer filtered
SQL over unfiltered GETs when a table can be large.**

## Step 2 — Identify the task family

Read the prompt and the template. The endpoint set and template keys tell you
which of three families this is:

| Family | Signal (endpoints / target ids / template keys) | Rules |
| --- | --- | --- |
| **Contractor batch** | `/api/contractor/*`; several `application_id`s; keys `application_decisions` + `summary` | `references/contractor_batch.md` |
| **Liquor package** | `/api/liquor/*`; one `application_id` + `location_id`; keys `recommended_posture`, `covered_risk_codes`, `first_90_day_plan`, … | `references/liquor_package.md` |
| **Renewal queue** | `/api/alcohol/*` + `/api/renewal/rules`; target `license_no`s + a boundary date + queue size; keys `queue` + `summary` | `references/renewal_queue.md` |

Read the matching reference file — it contains the complete, validated decision
logic for that family. Then fetch data and compute.

## Step 3 — Map conditions to the template's codes

The underlying data model is shared across tasks, but **each template uses its own
code vocabulary** for the same real-world conditions (e.g. one contractor template
calls a missing/pending endorsement `endorsement_missing`/`endorsement_pending`,
another collapses both to `endorsement_not_verified`; one liquor template uses
`PATIO`, another uses `PATIO_BOUNDARY`). So:

1. Detect the real conditions from the records using the family rules.
2. For each condition, emit the code the current template's `allowed_values`
   provides for it. If the template has **no** code for a detected condition, omit
   it (that condition is out of scope for this task).
3. Never emit a code that is not in the template's list.

## Step 4 — Format and self-check the output

- Include exactly the keys the template lists — no more, no fewer.
- Include exactly the target records named in the prompt (e.g. "exactly the eight
  applications", "queue size 10"), ordered as the template says
  (usually ascending by id / rank).
- Apply every `ordering` rule: sort code lists (typically ascending lexical),
  sort id lists, and de-duplicate where told.
- Use empty arrays `[]` when nothing applies — never omit a required list key.
- Make `summary` fully consistent with the per-item decisions (counts equal the
  number of items with each determination; id lists contain exactly the qualifying
  ids).
- Use any explicit **review / as-of / boundary date** from the prompt for currency
  and cut-off decisions. If a currency check is needed and no date is stated, use
  the current date.
- Output **only** the JSON object: no prose, markdown, code fences, comments,
  citations, or extra keys.

## Reference files

- `references/environment.md` — connecting, SQL interface, table names, join keys,
  the 200-row cap, and `policies` parsing.
- `references/contractor_batch.md` — contractor eligibility rules.
- `references/liquor_package.md` — restricted liquor staff-package rules.
- `references/renewal_queue.md` — renewal manual-review queue rules.
