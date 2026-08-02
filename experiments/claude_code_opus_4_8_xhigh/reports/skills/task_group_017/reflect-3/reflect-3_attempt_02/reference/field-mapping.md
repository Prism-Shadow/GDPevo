# Field-mapping reference

Generic mappings for turning Investigation Review Hub records into the
answer_template vocabulary. The exact enum *strings* differ per template — always
pick the closest value that actually appears in **this** task's `enums` block.
The tables below name the concept; substitute the template's spelling.

## 3.a Defect archetypes (what "material" looks like)

Recurring material issues across matters, each anchored by one hub record with a
descriptive ID and a concrete, numeric note:

| archetype | home table | signature in the note | typical issue meaning |
|---|---|---|---|
| Personal device erased after hold/subpoena | custodian_sources | "erased/wiped after subpoena/hold", `post_hold=1`, `status` lost | preservation failure / spoliation |
| Custodian scoped-but-not-collected source | custodian_sources | "scoped but not collected", `status` not_collected | collection gap |
| Personal email / messaging not collected | custodian_sources | "personal … identified in interview but not collected" | personal-source gap |
| Available archive / retained source | custodian_sources or retention_events | "archive backup available", `status` available/retained | remediation source (limits loss) |
| Incomplete privilege log | privilege_entries | "Only N of M withheld … are logged", issue_type incomplete_log | privilege-log gap (unlogged = withheld − logged) |
| Over-designated privilege | privilege_entries | "business-only … over-designated", issue_type over_designated | privilege miscoding → under-produced |
| Third-party waiver | privilege_entries | "forwarded to <third party>", `third_party=1` | privilege waiver / exposure |
| Miscoded privilege (QC) | qc_findings | "privileged … coded non-privileged", issue_type miscoded_privilege | privilege miscoding / exposure |
| Responsiveness miscode (QC) | qc_findings | "miscoded nonresponsive", issue_type miscoded_nonresponsive | responsiveness miscode → recode & produce |
| Zero-claim contradiction | production_stats + qc_findings | `status` zero_claim_contradicted, docs found despite a 0-claim | not-produced / underproduced responsive docs |
| Post-hold records destruction | retention_events | "boxes destroyed after the hold date", status post_hold_loss | post-hold loss (spoliation) |
| Policy pre-hold destruction | retention_events | "destroyed pre-hold under policy §x", status policy_destroyed_pre_hold | compliant loss — low risk, often "no action" |
| Should-exist missing record | retention_events | "missing but retention requires N months", status should_exist_missing | missing required record |
| Comms auto-purge | retention_events | "auto-delete configured for N days", status auto_purged | communication gap (auto-purge) |
| Active-system comms loss | retention_events | "messages before <date> lost from active system", status system_loss | communication gap (active-system loss) |
| Deleted collaboration channel | custodian_sources/retention_events | "deleted … channel", archive may exist | deleted-channel loss; pair with its archive |

## 3.b Distractor recognition

A row is noise (exclude unless a non-noise remediation action targets it) when it
has a generic sequential ID **and** a boilerplate note. The recurring noise
phrases are listed in SKILL.md §3. Also treat as noise: `remediation_actions`
whose id carries a NOISE marker / whose description is "Routine action included
as realistic operational noise" / whose target is a bare category code.

## 4.a Enum-selection logic

- **Map raw status → nearest template enum.** e.g. hub `system_loss` → the
  template's active-system-loss value; a wiped device → lost/destroyed source
  status + source_lost production impact; not_collected → not_collected /
  source_missing; an available archive → available_archive / source_available.
- **severity / risk_level = intrinsic severity of the defect:**
  - critical/high: post-hold or post-subpoena destruction (spoliation),
    incomplete privilege log of many docs, privileged docs exposed, a missing
    required record.
  - medium: uncollected personal/collaboration source, auto-purge or
    active-system loss that an archive can still remediate, partial-recovery
    loss, over-designation, third-party waiver of a few docs.
  - low: policy-compliant pre-hold destruction.
  Do **not** copy `remediation_actions.severity`; derive from the issue.
- **finding/risk status:** a spoliation/protocol breach → the "protocol
  noncompliant" value; an issue with a queued fix → "remediation pending /
  needs recode / remediation available"; an available archive → "remediation
  available"; a clean category → the "no gap / ready / closed" value.
- **recommended_action (and the matching action_type):** disclose preservation
  issue (spoliation / post-hold loss); forensic recovery or collect source
  (lost/uncollected source); collect personal device (personal email/phone/
  messaging); search/collect archive (available archive); supplement privilege
  log (incomplete log); privilege recode / waiver assessment (over-designation /
  waiver); recode and produce / QC remediation (responsiveness or privilege
  miscode, zero-claim contradiction); locate missing record (should-exist
  missing); no-action (policy-compliant pre-hold loss); monitor-only (clean).

## 4.b Owner (drive from the action's function)

| action function | owner (map to template enum) |
|---|---|
| disclose to the government / escalate | outside/litigation counsel |
| forensic recovery, personal-device or archive collection | forensics / ediscovery vendor |
| privilege-log supplementation / recode | privilege team |
| waiver assessment & disclosure | privilege counsel |
| recode & produce / QC remediation | review-QC / review vendor |
| records-retention follow-up / locate record | records management |

The hub's raw `owner` strings (e.g. "Forensics", "Review Operations", "Legal
Hold Team") do not map 1:1 to the template's owner enum — pick the enum owner
that fits the action, not the raw string.

## 5.a Metric recipes

Compute from the **material** set only:

- `*_event_count` / `*_source_count` = number of material records of that kind.
  A "retention event count" style metric usually counts **all** material
  retention-table losses (communication-gap events are a labeled subset, not a
  separate population), so count them once in the total.
- `destroyed_box_count` = Σ boxes over records measured in boxes; split into
  `pre_hold` vs `post_hold` by the record's status. A metric scoped to one named
  destroyed source counts only that source's boxes (0 if it isn't box-measured).
- Privilege metrics from the named blocker: `withheld`, `logged`,
  `unlogged = withheld − logged`. Waived = withheld docs of a third-party-waiver
  entry. Miscoded counts = the qc_finding doc_count for that issue type.
- `unique_affected_category_count` = length of the sorted union of category
  codes across material records; the companion list is that union.
- production-ready / rolling-ready boolean = false if any material gap exists.

Read the template's own one-line definition for each metric; when it says
"selected … blockers only" or "the destroyed source named in the task", scope
the count to exactly that.

## 6.a Ordering

Follow `ordering_rules` verbatim. For self-assigned `priority_rank`/`rank`: unique
1..N, ordered by priority tier (P0<P1<P2<P3) then the declared tie-breaker
(record/target ID ascending). Sort every category-code list ascending. Sort
record-ID ref lists ascending.
