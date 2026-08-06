---
name: ehr-governance-packet
description: Generate a normalized EHR quality-governance / referral-coordination packet or audit as JSON from a read-only EHR API. Use when a task supplies a prompt plus an answer_template.json and asks to prepare a duplicate-merge readiness packet, referral coordination packet, care-transition packet, ServiceRequest/duplicate review, or referral-batch audit. Fetches evidence only over the network via environment_access.md, reconciles records, classifies quality signals, cites evidence IDs, excludes distractors, and emits sorted JSON conforming to the template.
---

# EHR Governance Packet & Audit Generation

This skill produces a single normalized JSON object for EHR quality-governance and
referral-coordination tasks. A task in this family always provides:

- `prompt.txt` — the packet type and the concrete IDs in scope (candidate / patient /
  referral / batch / provider / service-request).
- `input/payloads/answer_template.json` — the exact output contract: required
  top-level keys, field types, enum `allowed_values`, and per-field ordering rules.
- `environment_access.md` (staged at `/work/environment_access.md`) — the only
  network access path: the base URL and the allowed read-only GET endpoints.

The template is the contract. The environment API is the only source of truth.
Never mix the two: do not invent values, and do not carry values over from any
other task's answer.

## Workflow

### 1. Load inputs
1. Read `environment_access.md` to get the base URL and the allowed GET endpoints.
   The `<TASK_ENV_BASE_URL>` placeholder used in prompts resolves to this base URL.
2. Read `prompt.txt` to learn the packet type and the in-scope IDs.
3. Read `answer_template.json` end-to-end. Note every required top-level key, every
   field with `enum` / `allowed_values`, every `set_semantics` / `ordering` rule,
   and every field that allows `null`. The output must conform exactly.

### 2. Fetch evidence (network only)
- Use **only** GET requests to the endpoints listed in `environment_access.md`.
  Do not read local source files for environment data — the network API is the only
  source of truth.
- Resolve every ID named in the prompt first, then chase every ID referenced by
  fetched records (a referral's `performer_provider_id`, an encounter's diagnosis
  codes, a duplicate candidate's `patient_ids`, a batch's referral rows, etc.).
- Fetch the record families the packet type needs. See `references/endpoints.md`
  for the family → record-type → packet-type map.

### 3. Reconcile & classify
- Build `normalized_key` values for clinical records so overlaps can be unioned and
  compared (see `references/normalization.md`).
- Cross-reference records across families (referral ↔ active chart ↔ encounter ↔
  document ↔ ICD-10 ↔ provider).
- Apply the classification logic for the packet type
  (see `references/packet_types.md`). Classify, do not transcribe: every enum value
  emitted must come from the template's `allowed_values`, and every code, ID, or
  contact must trace to a fetched record.
- Exclude distractors per `references/normalization.md` (inactive clinical records,
  unrelated documents/audits, stale or out-of-window encounters, narrative SOP
  text). Where the template asks, record what was excluded.

### 4. Emit normalized JSON
- Emit a single JSON object with exactly the template's top-level keys.
- Use only the enum values the template lists; use `null` only where allowed.
- Sort every array per the template's ordering rules (default ascending /
  alphabetical; newest-to-oldest or by-key only where the template states it).
- Dates as `YYYY-MM-DD`; booleans as `true` / `false`.
- Return JSON only — no prose, no markdown fences, no narrative explanations. Use
  stable IDs, not descriptions.

## Guardrails
- Never invent a value. If a needed record is missing, surface it through the
  template's blocking / missing fields (e.g. `blocking_issue_codes`,
  `missing_required_documents`, `missing_sections`, `ready_for_merge_packet=false`,
  a `null` merge target) rather than fabricating.
- Never copy values from another task's answer. Each packet is derived live from the
  environment for its own in-scope IDs.
- Do not include procedural notes, SOP narrative, or explanatory text in the output.
- If `environment_access.md` is missing, or lists endpoints that do not respond, halt
  and report rather than substituting a different source.

## References
- `references/endpoints.md` — endpoint families, what each returns, which packet
  types use them.
- `references/normalization.md` — `normalized_key` construction, sorting rules, enum
  discipline, distractor exclusion.
- `references/packet_types.md` — per-type classification playbooks.
