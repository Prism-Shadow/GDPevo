---
name: licensing-board-structured-decisions
description: >-
  Solve State Licensing Board / regulatory "structured decision" tasks that ask for a JSON answer
  conforming to a provided input/payloads/answer_template.json, built by reading a licensing data
  service (policies/rules plus contractor, liquor, or alcohol-renewal datasets, usually with a
  read-only SQL endpoint). Use for contractor batch eligibility reviews, restricted liquor-license
  staff packages, and alcohol renewal manual-review queues. Triggers: a prompt that assigns a
  licensing-examiner / staff-review role, lists GET endpoints under /api/... plus an answer template,
  and asks for determinations, deficiency/risk codes, control/obligation codes, verification gaps,
  monitoring plans, or a ranked review queue.
---

# Licensing-board structured decisions

These tasks give you (1) a role + a set of target IDs, (2) a licensing **data service** (HTTP GET
endpoints and, usually, a read-only SQL endpoint), and (3) an `answer_template.json` that specifies
the exact JSON shape, enums, and ordering to return. Your job is to read the records, apply the
regulatory rules, and emit JSON that conforms **exactly** to the template.

Read the task's own `environment_access.md` for the base URL, credentials, and the list of allowed
endpoints/tables — connection details are per-deployment and are not repeated here. Produce the final
JSON directly from the records and the rules below; solve it in one pass without any external
answer-checking.

## Workflow

1. **Read three things first:** the `prompt.txt` (role, target IDs, any review/boundary date,
   which endpoints are relevant), the `answer_template.json` (required keys, enum vocabularies,
   ordering, lengths, empty-array rules), and `environment_access.md` (how to reach the data).
2. **Identify the task type** and open the matching reference file:
   - Contractor batch eligibility → `references/contractor-eligibility.md`
   - Restricted liquor-license staff package → `references/liquor-staff-package.md`
   - Alcohol renewal manual-review queue → `references/renewal-review-queue.md`
3. **Pull the data** for exactly the target entities. Prefer the SQL endpoint filtered by the target
   IDs (e.g. `WHERE application_id LIKE '<prefix>%'`). **The GET endpoints and each SQL response are
   capped at 200 rows**, so a whole-table GET can silently miss records — always filter to the
   targets, and use SQL when a table can exceed 200 rows (bonds, insurance, violations).
4. **Read the governing thresholds from the data, not from memory.** The `policies` / `renewal_rules`
   datasets carry a `details_json` blob with the numeric minimums, required endorsement, blocking
   flags, boundary dates, and a *legacy/prior baseline* record used for "policy-impacted" comparisons.
   Look them up live for the specific class/family involved.
5. **Apply the domain rules** in the matching reference file to compute each field.
6. **Format to the template exactly** (see Output discipline), then re-check every ordering, enum,
   length, and the internal consistency between item-level decisions and any summary counts/lists.

## Universal principles

These held across every task type and are the highest-value part of this skill.

- **Conform to the template literally.** Use only enum values listed in the template. Respect every
  stated ordering ("ascending by id", "sort ascending by code", "sort by date then id",
  "intended operational sequence", "any order accepted"). Use empty arrays where nothing applies.
  Include exactly the requested entities — no more, no fewer. Emit only the keys shown; no prose,
  comments, citations, or extra keys.

- **Be precise, never maximal.** Scoring rewards the *exact minimal correct set* for each list field
  and **penalizes over-inclusion**. Padding a field with plausible-but-unsupported codes lowers the
  result. Include a code only when a specific record or rule supports it; otherwise leave it out.

- **Attribute records by matching keys; discard distractors.** Each dataset has an entity key
  (`application_id`, `related_application_id`, `license_id`/`prior_license_id`, `location_id`,
  `license_no`). Attach a record to a target only when its key matches the target's identity.
  Watch for planted distractors:
  - IDs containing `-DIS-` are often decoys. They are only "real" when their entity key still matches
    the target (e.g. a `-DIS-` violation whose `license_id` equals the target's prior license). A
    `-DIS-` row whose key points elsewhere, or a same-address row with a **different** license
    prefix, is a distractor — ignore it. (One exception observed: an "unverified/questionable"
    correspondence row still counts toward an *unverified-correspondence* field even if its id is
    `-DIS-`, because being unverified is the point of that field.)
  - When several records describe the same thing over time (e.g. site evidence of the same type, or
    an old vs. current bond/insurance), the **latest/current** record governs; older ones are
    superseded, not additional findings.

- **Currency is date-driven when a review date is given.** If the prompt supplies a review date,
  test coverage currency against it (e.g. an "active"-status policy whose expiration precedes the
  review date is *not current*) rather than trusting the status flag alone. With no review date,
  rely on the record's status field.

- **Keep summaries consistent.** Summary counts and id-lists must be derived from the item-level
  decisions you produced (approve/hold/deny counts, high-risk ids, policy-impacted ids, etc.), not
  computed independently.

- **Reproducibility.** These mappings are mechanical; compute them in a small script rather than by
  hand so ordering, dedup, and code→action mappings stay consistent across many items.

## Output discipline checklist

- [ ] Only template keys present; nothing extra; valid JSON only.
- [ ] Every list uses allowed enum values and the required ordering; duplicates removed.
- [ ] Exactly the requested entities/length; empty arrays where nothing applies.
- [ ] Each list field is the minimal set actually supported by records/rules (no padding).
- [ ] Summary fields reconcile with the item-level decisions.
- [ ] Dates in `YYYY-MM-DD`; enum spellings copied verbatim from the template (case-sensitive).
