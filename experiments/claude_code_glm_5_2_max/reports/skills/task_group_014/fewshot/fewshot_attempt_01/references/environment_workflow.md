# Environment Workflow

Detailed data-gathering workflow, endpoint-to-entity map, per-work-type notes,
and formatting invariants. Read alongside `SKILL.md`. No value here is a
task-specific answer — every concrete value is fetched live from the
environment.

## 1. Discover, then fetch

1. `GET /api/tables` — learn the entity/table catalog before querying.
2. Fetch the target record by its business ID from `task_context.json`.
3. Traverse related entities (map below). Use REST endpoints first; use
   `POST /sql/query` for joins or facts the REST surface does not expose.
4. Reconcile conflicts with the domain precedence rule before evaluating
   anything — the rule decides which record is authoritative and which is
   excluded/exception.

## Endpoint-to-entity map

| Endpoint | Yields |
|---|---|
| `GET /api/tables` | Catalog of available tables/entities. |
| `GET /portal` | Portal/entry context for the environment. |
| `GET /api/cases` / `GET /api/cases/{case_id}` | Authorization cases: member, plan, requested service/procedure lines, status, linked policy/criteria, document references, authorization record. |
| `GET /api/policies` / `GET /api/policies/{policy_id}` | Medical policy and the criteria definitions used to build `criteria_results`. |
| `GET /api/documents/{document_id}` | Clinical/evidence documents (evaluations, plans of care, cardiology notes, denial notices, etc.). |
| `GET /api/rate-schedules` | Rate/benchmark schedules for repricing (identify the effective one by modifier + date; reject stale/inapplicable ones). |
| `GET /api/appeals` | Appeal records (appeal ID, path, deadline, owner, prior-medication evidence, packet status) and P2P events. |
| `POST /sql/query` | Arbitrary SQL for joins/facts not exposed by REST: drug-trial records, assistance-screen facts, margin `service_margin` rows, claim-line detail, criteria/exception facts. |

## What to gather per work type

### UM-nurse prior-authorization determination
Target case, member/plan context, requested therapy/procedure lines, applicable
policy criteria, clinical documents (evaluations, plans of care), the
authorization record. Reconcile current clinical records against any stale
export; the current record controls and the stale one is excluded. Produce
`recommendation`, `final_status`, `route`, `authorization` (auth number,
approved units/dates/CPT/modifier), `criteria_results`, evidence vs excluded
documents, determination letter, and next action.

### Pharmacy coverage appeal + manufacturer-assistance intake
Target appeal + case, drug, appeal path/expedited flag, deadline, prior
medication evidence (classify documented vs undocumented/insufficient failures),
criteria results, required vs missing packet items, assistance screen
(program, status, missing fields). The appeal controls; assistance is screened
but does not override the appeal disposition. Compute the appeal deadline from
the plan window stated in task context when given.

### Payment-integrity claim repricing
Target claim, claim lines (in claim-line order), case/auth context, policy or
criteria context, and rate schedules. Select the effective benchmark by plan
modifier and service/effective date; reject the stale/inapplicable schedule and
name it as `stale_source_rejected`. Reprice each line; compute paid vs correct
allowed vs recovery (use the underpayment amount when corrected > paid). Set
line dispositions, resubmission route, and priority. Currency in USD rounded to
cents; `null` for absent modifiers.

### Peer-to-peer final summary
Target case, the completed P2P event, requested CPT, current policy criteria,
clinical evidence, authorization status. Determine P2P outcome, final status,
criteria results, unresolved criteria, whether new patient-specific information
materially changed the review, unsupported PET-specific factors, letter type,
recommended alternative modality, and — if the result is adverse — the internal
appeal deadline computed from the plan's appeal window (stated in task context)
off the final adverse determination date. Use `null` when no deadline applies.

### UM-finance margin queue
Target queue and its listed row IDs (use only the rows named in
`task_context`), the finance definitions (total-cost definition,
revenue-to-cost threshold), and the `service_margin` source. Compute per-row
total cost, margin, revenue-to-cost ratio, below-threshold flag,
charge-sensitive flag, and recommended action. Separate below-threshold
segments (contract review) from charge-sensitive ones (monitor). Identify the
top below-threshold issue and the dollar gap to the threshold. Ratios to the
precision stated (typically 4 decimals); currency to two decimals.

## Formatting invariants (apply to every work type)

- **Single JSON object.** No markdown, prose, or comments outside the JSON.
- **Enums** must exactly match the template's choices.
- **List ordering** per each field's template rule. Common rules: ascending
  `document_id`; ascending CPT/HCPCS code; claim-line order from the source
  claim; alphabetical by value; the task-context `queue_row_ids` order; the
  template's `choices` order; operational packet order (payer-appeal items
  before assistance items); exception order (criteria/route gaps before
  stale/excluded records).
- **Numeric precision:** USD rounded to two decimals; ratios to the stated
  precision (typically 4); service units as integers; integer counts as
  integers.
- **Dates:** `YYYY-MM-DD` ISO calendar dates; periods `YYYY-MM`.
- **Nulls:** use JSON `null` (not `""`) for absent modifiers and for fields that
  do not apply (e.g., no internal appeal deadline). Only use `null` where the
  template explicitly allows it.
- **Additional fields:** do not add fields beyond the template unless it
  explicitly permits additional properties.

## Cross-field consistency checks before emitting

- `criteria_results` has every required criterion ID from the template, each
  mapped to an allowed enum value.
- Evidence/excluded lists and controlling/exception lists are each populated
  per their own rule; a record can appear in more than one list, but
  `precedence_record_order` is de-duplicated and reordered.
- Numeric totals are consistent with their line/row components and the stated
  precision.
- Every enum, date, period, and ID matches the template's format and the
  environment's live values.
