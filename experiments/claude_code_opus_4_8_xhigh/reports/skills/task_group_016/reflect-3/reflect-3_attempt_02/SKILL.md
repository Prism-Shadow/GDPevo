---
name: clinic-protocol-structured-response
description: >-
  Produce a single strict-JSON answer for protocol-bound clinical decision-support
  tasks against a synthetic FHIR-like clinic runtime. Use when a task gives a target
  case id, points to a runtime clinic environment (patients, cases, observations,
  medications, allergies, problems, imaging, registry, SDOH, protocols) plus a
  separately-listed access description, and asks for a JSON object conforming to an
  answer_template.json (e.g. respiratory/CAP triage, pediatric head-injury/concussion,
  electrolyte repletion, care-management routing, or observation-window retrieval).
---

# Clinic Protocol → Structured JSON Response

These tasks give you (1) a prompt naming a target case and a decision to make,
(2) a runtime clinic environment plus a *separately listed access description* for
that run, and (3) an `answer_template.json` (usually under `input/payloads/`). Your
job is to read the record and the governing protocol, apply the protocol's rules to
the case data, and return **exactly one JSON object** that conforms to the template.

The template is authoritative for structure; the protocol is authoritative for
clinical logic; the case record is the ground truth. Nothing else is.

## Workflow

1. **Read all three inputs first.** Parse the prompt (what decision, which target
   case id, any hard constraints like "do not mutate / do not place orders"), the
   `answer_template.json` (required keys, enums, types, nullability, precision,
   ordering rules), and the run's environment-access description. Use **only** the
   resources/access that description lists for this run; if it names allowed
   resources, treat anything not listed as unavailable. If some listed access
   returns an error or demands a credential you were not given, do not depend on
   it — get what you need from the resources that do work.

2. **Retrieve the target case as a consolidated record**, then the applicable
   **protocol**. Pull the target case by its id (this usually returns a bundle:
   case, patient, findings, observations, medications, allergies, problems, imaging,
   registry, SDOH). Fetch the protocol whose scope matches the case type; its body
   carries the thresholds, controlled codes, status rules, and decision branches you
   must apply. Read-only always — never write or place orders.

3. **Scope and filter the data before reasoning:**
   - **Patient scope:** keep only records for the target patient. A record attached
     to the case but carrying a *different* patient id is out of scope entirely — it
     is neither a match nor an in-scope distractor.
   - **Status:** honor the protocol's authoritative statuses (typically `final`
     only). Treat `preliminary`, `entered-in-error`, `canceled` as non-authoritative.
   - **Code:** match the exact controlled code from the protocol. Look-alikes are
     traps — e.g. a serum analyte code differs from the whole-blood/point-of-care
     code for the same substance, and a neighboring analyte in the same panel/month
     is a different code.
   - **Time window:** apply the stated window with its stated boundary semantics
     (commonly inclusive start, **exclusive** end). "Latest" means the maximum
     `effective_time` among the records that survive all filters.

4. **Apply the protocol's decision logic literally.** Map each protocol threshold /
   trigger to the corresponding template field. Escalation/urgent branches are
   usually OR-logic over several conditions — evaluate every condition against the
   data, not just the obvious one. Compute any numeric outputs with the protocol's
   own formula and rounding rule. Pull controlled identifiers (NDC, LOINC, test
   codes) straight from the protocol's controlled-codes map rather than inventing
   them. Choose the highest-severity route that the data actually supports; when no
   trigger fires, take the routine/outpatient branch.

5. **Fill the template exactly, then self-check** against every rule in the template
   (see `references/field-checklist.md`).

## Reasoning rules that transfer across these tasks

- **The primary assessment / classification is the pivotal field.** Match it to the
  protocol's own supported terminology and to explicit observations (e.g. an
  observation stating an event's absence supports a "without-…" classification).
  Prefer the most specific enum value the data justifies; if the protocol lists the
  criteria that "support" a classification and they are met, that classification is
  usually the intended one.

- **List/set fields are scored as sets and usually need to be *exact*** — both a
  missing supported item and an added unsupported item cost you. Include an item
  only when the record clearly supports it *right now*; drop plausible-but-unstated
  ones. Watch for deliberate distractors placed in the bundle.

- **Distinguish current state from forward-looking watch-lists.** "Red flags /
  findings" mean things objectively present at this encounter. "Return precautions /
  escalation conditions / monitoring" mean things to watch for later — a presenting
  symptom (e.g. fever, a stable headache) belongs on the watch-list, not necessarily
  on the current-findings list. Derive return-precaution/monitoring sets from the
  protocol's own code list, mapped to the template's enum.

- **Allergy-aware medication choice:** use only *active* allergies, avoid every
  implicated drug class, and select an alternative from a non-contraindicated class;
  list the classes to avoid from the active allergies (not inactive ones).

- **Absence / not-assessed ≠ false-negative.** Only assert something is absent when
  the record actually documents it as absent. If a finding was never assessed, do
  not claim it either way — that is exactly what the "safety-check" booleans guard.

- **Safety-check booleans assert you did *not* make an unsupported claim** (no
  contraindicated drug class prescribed; no claiming imaging/exam normal when it is
  abnormal or was not done). They are `true` when your answer honors the guard.

## Output discipline

- Emit **one** JSON object with exactly the required keys — no extra top-level keys,
  no markdown, no comments, no prose around it.
- Copy required constant values (task id, case id, and any `expected_constant` /
  `required_value`) verbatim from the template/prompt. Use the patient id exactly as
  it appears in the record.
- Honor declared **types, enums, nullability, and numeric precision** (decimal
  places, integer-only, "null only where permitted"). Timestamps: ISO-8601 UTC with
  a trailing `Z`; scheduled follow-up times are exact — resolve relative phrasing
  ("next morning") to the next calendar day at a clinic morning hour.
- Honor any **ordering rule** a field states (e.g. `effective_time` ascending then
  id ascending; case id first; descending relevance); where a field says order is
  not meaningful, order does not matter but membership still does.

See `references/field-checklist.md` for the pre-submission checklist and the common
distractor catalog.
