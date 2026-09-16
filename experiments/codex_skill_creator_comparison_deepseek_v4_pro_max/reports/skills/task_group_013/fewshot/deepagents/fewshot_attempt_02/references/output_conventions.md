# Output Conventions

Rules for constructing the final JSON answer object that is the only output from any Cedar Ridge intake task.

## Template Authority

The answer template is the authoritative source for output shape. Extract from it:

- Every required top-level key
- Every allowed enum value for every field
- Sort order for every list
- Which arrays are unordered sets vs ordered lists
- Which keys are required vs optional
- Numeric precision (usually integer counts)

Never invent a key, value, or structure not in the template.

## List Sorting

Unless specified otherwise in the template:
- Sort lists ascending by their primary ID field (patient_id, referral_id, transfer_id, etc.)
- When a list has no natural ID sort, follow the template's explicit ordering instruction

Common sort patterns:
- patient_results: ascending by patient_id
- referral_reviews: ascending by referral_id
- icd_discrepancies: ascending by referral_id
- duplicate_groups: ascending by group_id
- blocker_sets lists: ascending by referral_id
- ready_to_schedule: ascending by referral_id
- action_plan: ascending by referral_id
- correspondence_queue: ascending by referral_id
- patients (enrollment): ascending by patient_id

## Unordered Sets

These arrays are treated as unordered sets. Order within them does not matter, but be consistent:

- blocked_reason_codes
- issue_codes
- reason_codes
- blocker_codes
- action_codes
- missing_required_documents
- missing_chart_artifacts
- components (monitoring package)
- artifacts_to_create

## Summary Counts

Every count in a summary object must equal the number of entities in the corresponding state across the per-entity results:

- Total count must equal the number of entities processed
- Each status count must equal the count of entities with that status
- Each risk-level count must equal the count with that risk level
- Each cadence count must equal the count with that cadence
- Cross-tabulation counts must exactly equal the matching entities

Validate all summary counts against per-entity results before finalizing.

## Output Format

- Return pure JSON, no markdown wrapping, no explanatory prose
- The JSON must parse cleanly as a single object
- Use double quotes for all strings
- Do not include comments

## Common Pitfalls

- Copying a task_id value from an example instead of using the one from the prompt
- Using an enum value not listed in the template
- Forgetting to include overall_risk_high in blocked_reason_codes when overall_risk is high
- Sorting unordered-set arrays differently across entities
- Summary counts that do not match per-entity results
- Including ready referrals in priority_order (priority_order is non-ready referrals only)
