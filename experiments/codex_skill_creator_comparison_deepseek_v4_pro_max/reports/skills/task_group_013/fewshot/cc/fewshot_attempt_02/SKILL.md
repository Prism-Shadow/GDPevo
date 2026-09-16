---
name: cedar-ridge-intake
description: Complete Cedar Ridge Intake Coordination Portal intake workflows – new-patient access verification, referral batch audit, dialysis transfer review, chronic-care program enrollment, and referral-to-chart activation. Use whenever the user mentions Cedar Ridge, intake coordination, patient access verification, referral audit, transfer review, program enrollment, or chart activation in a healthcare portal context, or when a task references the (TASK_ENV_BASE_URL) placeholder or cedar ridge intake coordination portal.
---

# Cedar Ridge Intake Coordination

This skill covers the five intake workflows available through the Cedar Ridge
Intake Coordination Portal, a REST API at a configurable base URL. Every
workflow follows the same skeleton: read the answer template, fetch records
from the portal, cross-reference and classify, and return structured JSON.

## Workflow skeleton

1. **Read the answer template.** The prompt references a file under
   `input/payloads/answer_template.json`. Read it first -- it defines every
   required key, allowed value, and sort order. If there is an additional
   payload file (e.g. a target roster), read that as well.

2. **Identify the intake type.** The prompt, template top-level keys, and
   batch identifiers tell you which workflow this is:

   | Intake Type | Hallmark keys | Description |
   |---|---|---|
   | New-patient access verification | `patient_results`, `insurance_status`, `registration_status` | Verify insurance, PBM, pharmacy, risk for a roster |
   | Referral batch audit | `referral_reviews`, `icd_discrepancies`, `ready_to_schedule` | Audit referrals for coding, duplicates, auth blockers |
   | Dialysis transfer review | `packet_completeness_status`, `stale_documents`, `requested_start` | Review transfer packets, capacity, and freshness |
   | Chronic-care enrollment panel | `eligible`, `enrollment_status`, `initial_monitoring_package` | Build enrollment panel from program candidates |
   | Referral-to-chart activation | `readiness_by_referral`, `ready_referral_chart_needs`, `correspondence_queue` | Determine referral readiness and chart activation needs |

3. **Fetch data from the portal.** Use the endpoints documented in
   [references/endpoints.md](references/endpoints.md). Start with the
   collection endpoint that matches the batch (e.g. `/referrals` for a
   referral audit), then fetch individual records, charts, documents, and
   code metadata as needed. When the answer depends on cross-referencing
   records, use `POST /query` to run SQL directly -- this is often faster
   than fetching records one by one.

4. **Classify and decide.** Apply the decision trees in
   [references/decision_trees.md](references/decision_trees.md). Every
   intake type has a section there with the rules for mapping portal data
   to controlled output values. Do not guess -- follow the rules for each
   field.

5. **Build the output.** Produce exactly one JSON object matching the
   answer template. Use only the controlled values from the template and
   from [references/controlled_values.md](references/controlled_values.md).
   Sort lists by the ordering specified in the template (usually ascending
   by ID). Treat reason-code and issue-code arrays as unordered sets. Do
   not include prose outside the JSON.

6. **Build the cohort summary.** Count every patient/transfer/referral in
   the batch across status, risk, urgency, and other dimensions listed in
   the template's summary section. Integer counts only.

## Portal interaction rules

- The base URL is `(TASK_ENV_BASE_URL)` as given in the prompt. Replace
  this placeholder with the actual URL before making requests.
- All endpoints return JSON. Collection endpoints (`/patients`,
  `/referrals`, `/transfers`, `/documents`, `/pharmacies`) return lists.
- `POST /query` accepts `{"query": "<SQL statement>"}` and returns a JSON
  array of row objects. Use this for bulk cross-referencing.
- When a patient or referral ID appears in the batch but returns 404 from
  its detail endpoint, treat it as missing data (not an error) and flag it
  accordingly in the output.
- Document staleness: compare the `received_date` on each document against
  the current date (from the system or the `as_of_date` field) using the
  `freshness_limit_days` documented in the decision trees reference. A
  document is stale when `(current_date - received_date) > freshness_limit_days`.

## Output rules

- Return only the JSON object. No markdown fences, no commentary.
- All enum values must be lowercase exactly as listed in the answer template.
- Empty arrays use `[]`, not `null`.
- Null fields use `null` (JSON null), only where the template explicitly
  allows null.
- Verify every patient/transfer/referral in the batch appears in the output
  exactly once.

## Reference files

- [references/endpoints.md](references/endpoints.md) -- full API reference
  with endpoint paths, query parameters, and response shapes.
- [references/decision_trees.md](references/decision_trees.md) --
  classification rules for each intake type.
- [references/controlled_values.md](references/controlled_values.md) --
  allowed enum values organized by intake type.
