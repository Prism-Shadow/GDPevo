 # Output Conventions

 ## Currency

 Integer USD dollars. Compute from the deal's headline purchase price (`headline_value * percent / 100`) unless a source record explicitly states a different basis. Round to the nearest integer dollar.

 When the answer template specifies a different basis (e.g., "upfront_cash" or "equity value"), use that basis consistently.

 ## Percentages

 Decimal numbers. The precision varies by task template — match the template's unit specification exactly:

 - `percent_points` — Two decimal places (e.g., 14.00, 5.50)
 - `whole percent points` — Integer values
 - `holder percentages` — Four decimal places (e.g., 0.1850)

 When no explicit precision is stated, default to two decimal places.

 ## Months

 Integer months. Never output fractional months.

 ## Dates

 `YYYY-MM-DD` format when the template calls for dates. Use dates from the deal record or source documents verbatim.

 ## Stable Identifiers

 Every ID from the workbench is stable — use it exactly as returned. Never shorten, mangle, or invent identifiers.

 | ID Kind | Prefix Pattern | Source |
 |---|---|---|
 | Terms | `TERM_<deal_id>_NN` | `/api/deals/<deal_id>/terms` |
 | Consents | `CNS_<deal_id>_NN` | `/api/deals/<deal_id>/consents` |
 | Employees | `EMP_<deal_id>_NN` | `/api/deals/<deal_id>/employees` |
 | Material Contracts | `MAT_<deal_id>_NN` | `/api/deals/<deal_id>/material-contracts` |
 | Findings | `FND_<deal_id>_NN` | `/api/deals/<deal_id>/diligence-findings` |
 | Risk Estimates | `RSK_<deal_id>_NN` | `/api/deals/<deal_id>/risk-estimates` |
 | Documents | `DOC_<deal_id>_NN` | `/api/deals/<deal_id>/documents` |
 | Regulatory | `REG_<deal_id>` or `REG_<deal_id>_HSR` | `/api/deals/<deal_id>/regulatory` |
 | Playbooks | `PB_SELLER_A`, `PB_BUYER_A`, etc. | `/api/playbooks` |
 | Policies | `POL_MA_YYYY_A`, etc. | `/api/policies` |

 ## Null and Empty Values

 - Use `null` for numeric/string/boolean fields not applicable to the current issue (not zero, not empty string).
 - Use `[]` for array fields with no applicable items.
 - Use `{}` for object fields with no applicable content.
 - When a term is missing from the draft entirely, `source_term_ids` is `[]`.

 ## Enum Compliance

 Every string field with enumerated values must use only the values listed in the answer template's `allowed_enums` or inline string choices. Never use a value that does not appear in the template, even if it seems descriptive.

 ## JSON-Only Output

 Return only the JSON object. Do not include markdown fences, explanatory prose, or commentary outside the JSON structure. The JSON must conform to the answer template's required shape.

 ## Sorting

 Unless the template specifies a different ordering, sort:
 - Issue arrays by `issue_id` ascending or by the template's `priority_order`
 - Redline arrays by `redline_id` ascending
 - Consent arrays by `source_id` ascending

 ## Field Completeness

 Every field listed in the answer template's `required_output_shape` or `issue_object_fields` must appear in the output, even when its value is `null`. Do not omit fields that the template declares.

 ## Computation Chain

 1. Extract `headline_value` from deal record
 2. For each numeric dimension: `amount = headline_value × percent / 100`
 3. For deltas: `delta = |draft - fallback|` (for exceeded) or `delta = |fallback - draft|` (for shortfall)
 4. For missing terms: treat draft as zero, shortfall = fallback_value
 5. When a template field requires a percent but the source provides an amount, reverse: `percent = amount / headline_value × 100`
