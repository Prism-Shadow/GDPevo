# Normalization Rules

## normalized_key
Clinical records (conditions, medications, allergies) carry or require a
`normalized_key` so records can be unioned and compared across patients and sources.

Construct it as lowercase snake_case:
- lowercase the text;
- replace whitespace runs with a single underscore;
- drop punctuation;
- preserve laterality (`left` / `right`) as part of the key, so laterality-distinct
  records are not collapsed into one key;
- drop qualifiers that are not part of the clinical identity (status, severity,
  "history of", etc.).

Use the record's own `normalized_key` when the API supplies one; otherwise derive it
from the description or name. Two records sharing a `normalized_key` are the same
clinical item.

## Active vs inactive
Only **active** clinical records contribute to unions, highlights, and risk-flag
evidence. Inactive / entered-in-error / resolved records are distractors: exclude
them, and where the template asks (e.g. `excluded_distractors`), record their keys.

## Sorting
Default: sort arrays ascending / alphabetically (case-insensitive first, then
case-sensitive tie-break). Override only where the template states otherwise:
- `set_semantics: true` → any order is accepted, but emit sorted for stability;
- `ordering: newest to oldest` → descending by date;
- `ordering: sort by <key>` / `sort ascending` → ascending by that key;
- `ordering: sort ascending by <code>` on object arrays → ascending by that field.

Sort duplicate-group and anomaly objects by their group / anomaly id; sort the id
arrays inside each object ascending. Sort referral-object arrays by referral_id
unless the template says otherwise.

## Enum discipline
- Emit only values listed in the template's `enum` / `allowed_values`.
- If the evidence does not match any listed enum, choose the closest `other` /
  `unknown` variant the template provides, or leave the field at its missing-state —
  never invent a new enum string.
- Where the template leaves a field as free-form labels (e.g. some signal / reason
  lists), derive concise normalized snake_case labels from the underlying field
  comparison; do not copy labels from another task's answer.

## Dates & nulls
- Dates as `YYYY-MM-DD`.
- Use `null` only where the template explicitly allows it (e.g. a merge target when
  not merging, a `document_id` when the document is missing).

## Distractor exclusion
Exclude from the packet:
- inactive / resolved clinical records;
- documents unrelated to identity, external continuity, or the referral reason
  (e.g. internal chart-summary-type documents when the policy is identity /
  external-continuity only);
- audit entries unrelated to the merge / identity event;
- encounters that are stale, outside the handoff window, or clinically unrelated;
- narrative SOP / procedural text the prompt says to omit.

Where the template has an exclusion field (`excluded_distractors`,
`excluded_encounter_ids`, `excluded_document_types`, `missing_sections`, etc.),
populate it; otherwise simply omit the item.

## Output shape
One JSON object. No prose, no comments, no trailing commas, no markdown fences.
Stable IDs only — never substitute a description for an ID, and never substitute an
ID for the human-readable name a contact field asks for.
