---
name: clinic-protocol-decision-support
description: >-
  Use when a task asks you to prepare a structured, protocol-bound clinical
  decision-support result for a single synthetic-clinic case and return ONE JSON
  object that conforms to a provided answer template. Fits prompts that name a
  target case id (e.g. respiratory / pneumonia assessment, pediatric head-injury
  triage, potassium/electrolyte repletion, care-management routing, or an
  observation-window / lab-retrieval gate), point you at a read-only clinic
  runtime, and require enum/number/list fields with no prose. Covers how to read
  the template as a contract, pull the case bundle and the matching protocol,
  filter records to the authoritative in-scope set, apply protocol thresholds and
  formulas, and shape output so it scores well.
---

# Clinic protocol-bound decision support (structured JSON)

## What this family of tasks looks like

Each task gives you:

1. A **prompt** naming exactly one **target case id** and the clinical deliverable
   (an assessment, disposition, plan, routing, or a retrieval/gate result).
2. An **answer template** (usually `input/payloads/answer_template.json`) that is a
   strict **contract**: required top-level keys, enums (`allowed_values`), types,
   numeric precision, ordering rules, required constant values, and null rules.
3. A separately-provided **environment-access file** listing the runtime **base URL**
   and the **allowed read-only endpoints** for this run.

Your job: read the clinic data, apply the applicable clinic **protocol**, and return
**exactly one JSON object** that conforms to the template — no markdown, no prose,
no extra keys.

Do not mutate the environment or "place orders." Everything is read-only (GET).

## Workflow

### 1. Parse the task
- Extract the **target case id** verbatim. The environment contains **distractor
  cases and distractor records**; only the named case is in scope.
- Identify the domain from the prompt/summary so you know which protocol governs it.
- Note any explicit constants the template pins (e.g. a fixed `task_id`, `case_id`).

### 2. Treat the answer template as a contract (read it before touching data)
- List every `required_top_level_keys` entry — output all of them, and **only** them.
- For each field record: type, `allowed_values` (enums), precision, `ordering`
  rules, `required_value`/`expected_constant`, and where `null` is permitted.
- Objects usually must be **fully correct to earn credit** — plan to get every
  sub-field right, not just most.

### 3. Pull the data (read-only)
- Read the run's environment-access file for the base URL and allowed endpoints;
  **do not hardcode a URL** — it is provided per run.
- Prefer the **case-detail endpoint** (`GET .../api/cases/{case_id}`). It returns a
  consolidated bundle: `case`, `patient`, `allergies`, `problems`, `medications`,
  `observations`, `imaging`, `findings`, `care_registry`, `sdoh`. The `findings`
  list often spells out the decision-relevant facts (current time, thresholds,
  disclosed barriers) with their `source_id`.
- List protocols (`GET .../api/protocols`), find the `protocol_id` whose title
  matches the domain, and fetch its body (`GET .../api/protocols/{protocol_id}`).
  The body holds the thresholds, controlled codes, formulas, and ordering rules
  you must apply — **read them at runtime; do not assume fixed numbers.**
- If an endpoint returns 401/needs a credential you weren't given, skip it and use
  the open GET endpoints. The case bundle is normally sufficient.

### 4. Filter to the authoritative, in-scope record set
Distractors are deliberate. Before using any observation/result, require **all** of:
- **Status** is authoritative — protocols list `authoritative_statuses` (typically
  `final`). Drop `preliminary`, `entered-in-error`, `canceled`.
- **Code** matches the target **exactly** (e.g. a serum code vs a whole-blood code
  vs a different analyte are different codes). Use the protocol's `controlled_codes`.
- **Patient** equals the target patient. Records for another patient are not part of
  the review — exclude them from every list (matched *and* "excluded distractors").
- **Time window** (if any) is respected: inclusive start, **exclusive end**.
- When you need "the latest/current" value, take the latest **eligible** record by
  `effective_time` after applying the filters above.

See `references/retrieval_and_protocol_rules.md` for the detailed retrieval rules.

### 5. Apply the protocol deterministically
- **Evaluate escalation/urgent branches first.** Protocols encode explicit trigger
  sets (vital thresholds, critical values, high-risk conditions, symptoms). Check
  each trigger against the filtered data. If none fire, take the routine/outpatient
  branch. The disposition, imaging, and urgent-action fields follow from this.
- **Let the protocol's own "support" criteria pick the label.** When a protocol
  lists criteria that *support* a particular assessment/tier and the case meets
  them, choose that label. Matching the protocol's language to the right enum is the
  single highest-value decision — get the primary categorical right first.
- **Apply formulas exactly** (e.g. dose = increments-below-target × per-increment
  amount, then round as specified), using the eligible latest value as input.
- **Be allergy-aware:** use only **active** allergies; avoid the implicated drug
  classes; pick a regimen compatible with them; list avoided classes as a set.
- **Tier by threshold:** map scores/values to tiers using the protocol's cutoffs.

### 6. Build and check the output
Emit one JSON object. Then verify it against the template contract and the
output-conformance rules below.

## Output-conformance rules (these move the score)

- **Exactly the required keys**, no extras, no prose, valid JSON. Honor pinned
  constants and use only `allowed_values` for enums.
- **Numeric precision:** respect stated decimals (one/two places) and integer units
  (whole hours/days/count). Format composite strings exactly as the template shows
  (e.g. a blood pressure as `"systolic/diastolic"`).
- **Canonical clock times:** when a follow-up is described qualitatively (e.g. "next
  morning"), schedule it on the correct calendar day at a **canonical morning hour
  (08:00)** with a trailing `Z`. The exact hour is graded — don't invent an odd time.
- **Sets are scored as exact sets — be evidence-tight, not inclusive.** For
  list/enum fields (red flags, recommended tests, referrals, priority problems,
  escalation conditions), include **only** items with clear support in the data or
  protocol. Over-including weakly-supported items (e.g. a mild screening score →
  a specialty referral) loses points. Prefer minimal-but-complete, protocol-literal
  sets. When a field asks for **absent/negative** findings, list the full set of
  serious findings that are documented or clinically confirmed *not* present.
- **Required structured minima can be true by convention.** Some booleans a
  compliant plan requires (e.g. a person-centered care plan requiring a
  member-stated priority) should be `true` even if the protocol's bulleted list
  doesn't spell them out. Don't set a required-by-domain flag false just because the
  protocol text omits it — and don't overwrite a well-reasoned structured object
  with a guess.
- **Provenance splits:** separate objective chart-derived facts from
  member-disclosed facts per the field's `allowed_values`; include only facts
  actually present (omit a fact key when its source datum is absent).
- **Safety-check booleans:** set each `true` when your answer upholds the condition
  (no contraindicated drug prescribed; no false claim of normal imaging / clear
  exam / an absent symptom). Make the rest of the answer consistent with them.
- **Evidence/id lists:** include the decision-relevant identifiers (target case id
  plus the observation/imaging/protocol ids you relied on) and honor any stated
  ordering (case first, or descending relevance, or `effective_time` ascending).
  These carry little scoring weight — spend your effort on the decision fields.

## Priorities when time is limited
1. Identifiers + pinned constants (free points — verify the patient id from the bundle).
2. The primary categorical assessment/tier/disposition/gate (highest weight).
3. Numeric anchors and formula outputs at the required precision.
4. Fully-correct nested objects (medication order, follow-up, contraindications).
5. Tight, protocol-literal sets.
6. Evidence/id lists last.

See `references/domain_playbooks.md` for per-domain checklists (respiratory,
head injury, electrolyte repletion, care-management routing, observation window).
