# Environment Data Linking Reference

The licensing environment is a small relational database exposed as JSON list endpoints.
Each task family joins records differently. This reference captures the joins so you scope
correctly and avoid distractors. It is generic.

## Contractor family endpoints

Records and their join keys:

| Endpoint | Join key into applications |
|---|---|
| `applications` | root records (carry `application_id`, `trade`, `requested_class`, `years_experience`, `endorsement_status`, `prior_license_id`, `applicant_name`, `submitted_date`, `self_disclosed_issue`) |
| `bonds` | `application_id` |
| `insurance` | `application_id` |
| `license-history` | **`applicant_name`** (NOT application id); may also resolve via `prior_license_id` |
| `violations` | `related_application_id` (+ `license_id`) |
| `correspondence` | `related_application_id` |
| `inspections` | `related_application_id` |

Notes:
- A single application commonly has multiple bond rows (an active "A" bond plus a
  cancelled/expired "OLD" bond). Only `status: active` bonds are operative; the rest are
  history.
- Insurance rows likewise have active + expired variants; check `expiration_date` against
  the review date, not just `status`.
- License-history may list several rows per applicant (e.g., an active newer license plus
  an expired prior). The `prior_license_id` on the application tells you which history row
  is the relevant prior license.
- A `suspended` history status with a note like "pending board action" is an active
  suspension — treat as a suspension deficiency and a board-review action.

## Liquor family endpoints

| Endpoint | Join key |
|---|---|
| `applications` | root; carries `location_id` and `license_class` |
| `settlements` | `location_id` |
| `incidents` | `location_id` |
| `site-evidence` | `location_id` |
| `privileges` | keyed by `license_class` + `obligation_code`; `standard_required` flags class obligations |

Notes:
- A location has multiple settlement rows; only the row with `controls_json.active == true`
  (and a future `expires` date) defines the **current active controls**. Inactive
  settlements are history that informs `same_premises_basis_applies` and prior board orders
  but do not contribute to `location_specific_control_codes`.
- `settlements.basis_code` is the risk basis (SAME_PREMISES, NOISE, PUBLIC_SAFETY,
  SALE_TO_MINOR, ...). The active settlement's basis informs covered risks; the
  same-premises *history* informs whether the same-premises basis remains applicable.
- `incidents` carry `risk_code`, `severity`, and `status`. Open incidents drive
  verification gaps and escalation triggers; closed/dismissed incidents are history
  (serious/closed history can still inform covered-risk posture).
- `site-evidence` `evidence_code` (CONTROL_SIGNAGE, FLOOR_PLAN, POLICE_MEMO, SITE_PHOTO,
  NEIGHBOR_NOTICE, TAX_CLEARANCE) + `status` (verified/missing/conflicting) drive
  verification gaps. A "verified" evidence item with a stale date or identity note
  ("Old location name") can still be a gap.

## Renewal family endpoints

| Endpoint | Join key |
|---|---|
| `licensees` | root; carries `license_no`, `successor_to`, `active`, `address`, `facility_name` |
| `violations` | `license_no` (direct); also joinable by `address`/`facility_name` (these are **distractors** unless the license_no matches or it is the successor license) |
| `renewal/rules` | named release rule sets the boundary date and matching rules |

Notes:
- Target licenses are the active licenses in the prompt's target id range. Inactive
  `*-OLD-*` licenses are predecessors reached via `successor_to`, not queue entries.
- A licensee with `successor_to = <old_no>` inherits the old license's pre-boundary
  violations; mark that queue entry's match confidence uncertain and include its number in
  the close/uncertain summary list.
- `late_rows_are_distractors`: violations sourced from `post_boundary_feed`/dated after the
  boundary are excluded and listed in `post_boundary_violation_ids_excluded`, regardless of
  license.
- Distractor look-alikes (other test batches sharing an address) are never matched.

## SQL access

A `POST /api/sql` endpoint may be offered but is restricted (blocked constructs, no direct
table names mirroring the endpoint names). Prefer fetching the JSON endpoints and joining
locally; do not rely on SQL to answer a task. Use local filtering on the fetched JSON.
