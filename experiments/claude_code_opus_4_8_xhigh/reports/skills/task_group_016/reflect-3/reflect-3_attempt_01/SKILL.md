---
name: clinic-protocol-json-assessment
description: >-
  Use when a task asks for a protocol-bound clinical decision-support result
  over a synthetic FHIR-like clinic runtime and requires returning a single
  strict-schema JSON object that conforms to a provided answer_template.json
  (e.g. respiratory/CAP triage, pediatric head-injury triage, potassium
  repletion, care-management routing, or observation-window retrieval). Covers
  how to read the record, apply the matching protocol, filter distractors, and
  emit exactly the required JSON. Not for free-text clinical advice or tasks
  without a fixed answer template.
---

# Clinic protocol → strict-JSON assessment

These tasks give you (1) a prompt naming one target **case id** and pointing at
an `answer_template.json`, and (2) access to a synthetic clinic runtime plus a
matching clinical **protocol**. Your job is to read the record, apply the
protocol's rules, and return **one JSON object** that satisfies the template
exactly — no prose. The runtime is seeded with deliberate distractors; most of
the difficulty is filtering them out correctly.

The runtime access details (base location, any credentials, and the exact set
of available read resources) are supplied **separately for each run** — read
that access list first and use only what it grants. Do not assume or hardcode
locations; treat the runtime as read-only and never mutate it or place orders.

## Workflow

1. **Parse the prompt.** Extract the target case id and the template path. Note
   any expected constant values the template pins (task id, case id).

2. **Read the answer template completely — it is the contract.** Capture, per
   field: required top-level keys, type (string/number/integer/boolean/enum/
   list/object, and `*_or_null`), `allowed_values` for every enum, numeric
   precision and units, timestamp format, ordering rules, nullability, and any
   "no extra keys" rule. You will emit exactly these keys and only these keys.

3. **Pull the full case bundle once.** Use the runtime's per-case detail view —
   it bundles patient, case, findings, observations, medications, allergies,
   problems, imaging, and (when present) care-registry and social-context
   records for that case. This single bundle is your richest source; prefer it
   over stitching many list calls. Record the patient id it resolves to.

4. **Load the matching protocol.** Match the case's `case_type` to the protocol
   whose scope/title covers it, and read its body. Protocols encode the actual
   decision rules — read them as machine rules, not background reading:
   - `authoritative_statuses` / status rule → which observation `status` values
     count (typically **final** only).
   - `controlled_codes` → the canonical code for each clinical concept. Use the
     exact code; a different code is a different concept.
   - thresholds & branches → escalation/urgent criteria, target values, dosing
     formulas, rounding rules, referral triggers, risk cutoffs.
   - timing → follow-up windows / "next morning" style rules.
   - allergy rule, ordering rules, and any provenance rules.

5. **Filter before you reason (this is where the distractors are).** Apply, in
   order, and keep only records that pass every gate:
   - **Patient gate — filter to the target patient id first.** A record whose
     `patient_id` is a *different* patient is not this patient's data. It never
     appears anywhere in your answer — not as a match and not as an excluded
     distractor. (Wrong-patient rows are a common trap.)
   - **Status gate.** Keep only authoritative statuses (final); drop
     preliminary / entered-in-error / canceled.
   - **Code gate.** Keep only the exact controlled code for the concept
     (e.g. a serum measurement's code ≠ a whole-blood or a different-analyte
     code, even when the value looks plausible).
   - **Window gate.** Honor bounds precisely — start is typically inclusive,
     end exclusive. A value just outside the window does not qualify.
   - **"Latest / most recent" is computed AFTER filtering** — the newest
     `effective_time` among the records that passed *all* gates. Never let a
     filtered-out higher/lower value drive a threshold decision.

6. **Map facts to the controlled vocabulary.** Convert each clinical fact to the
   closest `allowed_values` enum using the protocol's codes and thresholds.
   Never emit a value outside `allowed_values`. Check any **urgent/override
   branch before the routine branch**: if any urgent trigger is met take that
   branch; otherwise apply the routine path.

7. **Allergy-aware medication choice.** Read **active** allergies, avoid the
   implicated drug classes, and pick a protocol-consistent alternative. Fill
   dose/route/frequency/duration per the template's types, and list the avoided
   allergen classes. When the setting calls for deferral or no medication, use
   the template's null/enum options rather than inventing a drug.

8. **Assert conservatively — only what is documented.** This drives the safety
   fields and the accuracy of every list:
   - Mark a danger sign **present** only with positive evidence, and **absent**
     only when it is explicitly documented/assessed as absent (an observation
     reading zero/negative, or an exam note "no X"). A sign that is simply
     *unmentioned* goes in neither list.
   - Never claim a normal/negative/"clear" result that the record does not
     support; set safety booleans to reflect that you avoided unsupported
     claims.
   - **Do not over-populate list fields.** Extra, weakly-supported members lower
     accuracy. Prefer the smallest set the evidence and protocol justify.

9. **Numbers, timestamps, formats.** Honor the template's precision (e.g. one
   decimal), integer-vs-number, and units. Emit timestamps in the required
   ISO-8601 UTC form (trailing `Z`). Use composite string formats exactly as
   specified (e.g. `systolic/diastolic`). Derive follow-up/scheduled times from
   the protocol's timing rule anchored on the case's current/clock time (a
   "next morning" rule resolves to the following calendar day at a morning
   clock time). Use `null` only where the field permits it.

10. **Evidence & provenance.** Cite the stable identifiers (case, encounter/
    visit, observations, imaging, protocol) that actually support your
    decisions, in the template's required order (e.g. case id first). Do **not**
    cite an identifier for data that is absent (if a value was never measured,
    it is not evidence). When the template separates provenance, put
    chart-measured facts in the chart group and member/patient-reported facts in
    the disclosure group.

11. **Emit and self-check.** Output exactly one JSON object with exactly the
    required keys, correct types, empty lists for "none," and no markdown,
    comments, or prose. Run the checklist in
    `references/answer-contract-checklist.md` before finalizing.

## Guiding principle

Everything you assert must be **traceable** to a filtered record plus a protocol
rule. Deterministic parts — identifiers, exact codes, status/window filtering,
threshold and dose math, precision/format, protocol-defined enums and timing —
are fully gettable and should be exact. For genuinely fuzzy list membership,
stay conservative and evidence-anchored rather than comprehensive.
