---
name: atlas-ops-reporting
description: >-
  Produce cutoff-based operational reports and authorized data corrections from
  the Atlas Commerce Operations workplace database. Use when a task points at a
  `<TASK_ENV_BASE_URL>` Atlas service with GET /api/schema, GET /api/data-dictionary,
  POST /api/sql (read-only) and POST /api/sql/transaction, ships a request-facts
  payload plus an answer_template.json JSON-Schema, and asks for one exact
  answer.json — e.g. fulfillment scorecards, refund/settlement reconciliations,
  warehouse productivity reviews, support-health reviews, or carrier-quality
  canonical corrections.
---

# Atlas Commerce Operations reporting & correction

You are given a task folder with `input/prompt.txt`, an
`input/payloads/<something>_request.json` (the authoritative business facts,
windows, thresholds, and orderings), and `input/payloads/answer_template.json`
(the exact output contract). The workplace service is reached over the network
using the credentials in `environment_access.md` (Base URL + `Authorization:
Bearer …`). Your job is to compute the requested result and write it to
`answer.json`, conforming **exactly** to the template with no extra commentary.

## Procedure

1. **Read the two payloads first.** The request payload defines every window,
   cutoff, threshold, tier rule, ordering, and rounding — treat it as ground
   truth and never hardcode values from memory or from past tasks. The
   answer_template defines the output shape. Note whether the task is
   **analytical-only** or an **authorized correction** (it will explicitly grant
   a correction with a reason_code/actor/audit_id/correction_key/success rule).

2. **Connect and discover the real schema.** Use the client:

   ```
   python3 skill/scripts/atlas_client.py schema
   python3 skill/scripts/atlas_client.py dict
   python3 skill/scripts/atlas_client.py sql "SELECT ... "
   ```

   (Or import `AtlasClient` from `skill/scripts/atlas_client.py`.) It reads
   `environment_access.md`, sends the bearer token, and retries transient 5xx.
   Get real table/column names and enum values from `GET /api/schema` and
   `GET /api/data-dictionary`; the dictionary is where domain terms like
   *effective*, *canonical*, *logical*, *production*, and *active time* are
   pinned for this dataset. Probe distinct values before filtering — confirm
   each status/tier/region/currency literal actually exists.

3. **Compute with SQL through `POST /api/sql`** (read-only). Build up the
   metrics the template requires. Honor these recurring rules (details and the
   per-task-type recipes are in `references/playbook.md`):
   - Include only **production** rows; exclude test/sandbox.
   - Evaluate state **as of the stated cutoff**; timestamps are exact UTC
     boundaries with the stated inclusivity. Membership windows and status
     cutoffs are usually different dates — keep them separate.
   - Compute on **effective/canonical** values; refunds net against reversals.
   - Keep full eligible populations in rate **denominators**.
   - **Round only final reported values**; sort and tie-break on unrounded
     values, applying every tie-break key the payload lists.
   - Classify status/risk **top-down, first match wins**, using the exact
     thresholds and comparison operators from the payload.

4. **For an authorized correction only**, use `POST /api/sql/transaction` to
   change the single minimal canonical field and insert exactly one audit row,
   then verify post-change and report `APPLIED`/`NOT_APPLIED` per the success
   rule. Leave raw source values, identity fields, and unrelated rows untouched.
   Never mutate for analytical-only tasks. See the correction section of
   `references/playbook.md`.

5. **Assemble `answer.json` to the contract.** Emit exactly the required keys,
   correct JSON types, exact enum strings, ID formats preserved, arrays sized/
   ordered/deduped as specified. Details and pitfalls: `references/output-
   contract.md`.

6. **Validate before finishing:**

   ```
   python3 skill/scripts/validate_answer.py answer.json input/payloads/answer_template.json
   ```

   Fix every reported shape problem. The output file must contain **only** the
   JSON document — no prose, no code fences, no extra fields.

## Files in this skill

- `references/playbook.md` — recurring Atlas semantics and per-task-type
  computation recipes (fulfillment, refund/FX, warehouse, support, correction).
- `references/output-contract.md` — how to read the answer_template schema and
  the contract mistakes that cost points.
- `scripts/atlas_client.py` — stdlib API client (schema / dictionary / audit /
  sql / transaction / introspect) with token handling and 5xx retry.
- `scripts/validate_answer.py` — best-effort shape validator for answer.json vs
  the template (does not check business correctness).

## Guardrails

- The request payload and data dictionary — not this skill and not prior
  answers — supply all business values. Nothing task-specific is baked in here.
- Analytical tasks are read-only; only run a transaction when the request
  explicitly authorizes the correction and its audit record.
- If the schema endpoints keep returning 5xx, keep retrying (the client backs
  off) and cross-check names via `introspect`; don't guess table names blindly.
