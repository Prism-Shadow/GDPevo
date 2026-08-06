---
name: licensing-review-batch
description: >-
  Produce structured JSON decisions for state licensing review tasks backed by the
  shared licensing data service (contractor application batches, restricted liquor
  license staff packages, and alcohol renewal manual-review queues). Use when a
  prompt asks you to review licensing records over a network environment and return
  JSON that must conform to an answer_template.json, especially when the prompt names
  contractor applications (C-*), liquor applications/locations (L-*/LOC-*), or
  alcohol licenses (AL-*), and lists /api/... endpoints plus POST /api/sql.
---

# Licensing review batch → structured JSON

You are acting as a state licensing examiner. Each task gives you a small set of
target records (application ids, a location, or a license batch), points you at a
shared licensing data service, and requires **JSON only** that conforms to the
task's `input/payloads/answer_template.json`. There is no free-text memo.

The data service is the same across tasks; only the target ids, the review
parameters, and the exact output vocabulary change. Do not guess values — read the
real records and apply the rules below.

## 0. Orient before you compute

1. Read the prompt and extract: the **target ids** (and any location id), the
   **review/as-of/boundary date**, the **target count** (e.g. "eight applications",
   "queue size 10"), and the list of allowed endpoints.
2. Read `input/payloads/answer_template.json` **completely**. It is the contract:
   it fixes the exact top-level keys, the item shape, every enum's `allowed_values`,
   the required ordering, list lengths, and "empty list when nothing applies" rules.
   The code vocabularies differ from task to task even within the same family — always
   map your findings onto *this* template's `allowed_values`, never a memorized list.
3. Get network access from `environment_access.md` (base URL, the `X-Task-Token`
   header value for `POST /api/sql`, and the allowed endpoints). Reach the service
   only over the network described there.

## 1. Data access — read `references/environment.md` first

Key facts (details and gotchas in `references/environment.md`):

- Every `GET /api/...` endpoint returns JSON. `POST /api/sql` accepts
  `{"query":"SELECT ..."}` with header `X-Task-Token: <token from environment_access.md>`
  and returns `{columns,rows,row_count,truncated,...}`.
- **The GET endpoints are a filtered subset; the SQL tables are the complete source.**
  Target records are frequently *absent* from the GET feeds but present in SQL. Pull
  the authoritative data with `POST /api/sql`, filtering by your target ids
  (`WHERE ... LIKE '<PREFIX>-%'`). GET is fine for small reference tables
  (`/api/policies`, `/api/liquor/privileges`, `/api/renewal/rules`).
- SQL is **row-limited (~200 rows) and truncates**, and blocks schema introspection
  (`sqlite_master`, `PRAGMA`). Always filter by your target ids; never rely on bare
  `SELECT *`. Table names equal the GET path with `/`→`_` (e.g.
  `/api/contractor/bonds` → `contractor_bonds`, `/api/liquor/site-evidence` →
  `liquor_site_evidence`).
- **Distractors are everywhere.** Records for other batches share your addresses and
  id shapes (`*-DIS-*`, `*-TE2-*`, `*-TE5-*`, `*-OLD-*`, and `*-LATE` rows). Only
  attach a record to a target when the join key says so (see each family's rules).

`references/environment.md` also documents `scripts/env_query.sh`, a helper for
GET and SQL calls.

## 2. Pick the task family and apply its rules

Route by the target ids / endpoints, then follow the matching reference file
exactly. Each reference gives the record joins, the condition→code logic, the
determination/ranking logic, and how to build the summary.

| Signal in prompt | Family | Reference |
|---|---|---|
| Contractor application ids (`C-...`), `/api/contractor/*`, batch of APPROVE/HOLD/DENY | Contractor batch eligibility | `references/contractor_batch.md` |
| One liquor application + location (`L-...` / `LOC-...`), `/api/liquor/*`, "restricted"/"staff package" | Liquor restricted-license package | `references/liquor_package.md` |
| Alcohol license batch (`AL-...`), `/api/alcohol/*` + `/api/renewal/rules`, "queue"/"release boundary" | Renewal manual-review queue | `references/renewal_queue.md` |

All families share the same shape of reasoning:

- **Select** each target's own records via the correct join key (ignore distractors).
- **Detect conditions** from thresholds in `/api/policies` (or `/api/renewal/rules`,
  `/api/liquor/privileges`) and record fields — comparing against the review/boundary
  date the prompt supplies.
- **Map** each detected condition to the closest code in *this template's*
  `allowed_values`; pair deficiencies with their required action where the template
  asks for actions.
- **Aggregate** into the required summary/queue.

## 3. Output discipline (all families)

- Emit **only** the JSON object, no prose/markdown/comments/citations, and only the
  keys the template shows.
- Honor every ordering rule (usually ascending lexical for code lists and ids;
  renewal `matched_violation_ids` sort by date then id; queue by rank). De-duplicate
  code lists. Use `[]` when nothing applies.
- Return exactly the required number of items (e.g. all N targets, queue length N),
  ordered as specified (application decisions by id; queue by rank 1..N with no gaps).
- Make the summary **internally consistent** with the item-level decisions
  (counts equal the decisions; id-lists are exactly the items that qualify).
- Every enum value you emit must be a member of that field's `allowed_values`.

## 4. Self-check before returning

- JSON parses; top-level keys == template keys exactly.
- Counts/derived lists recomputed from your own items match.
- No distractor ids leaked in; no `*-LATE`/post-boundary or other-batch rows counted.
- Dates in the required format; lists ordered and de-duplicated.
