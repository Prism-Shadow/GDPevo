# Materiality filtering & field→enum mapping

The hub mixes a few **material** records into many **distractors**. Only material records belong in
your findings, category coverage, metrics, and action plan. This file gives the signal/noise
heuristics (how the *hub* is built — reusable across any matter) and how to normalize a material
record into whatever enums the current `answer_template.json` defines.

## 1. Separating material records from distractors

Apply these signals together — no single one is sufficient, but they strongly agree in practice.

**(0) Let the prompt narrate the material stories.** `prompt.txt` usually names the specific issues
the matter turns on (e.g. "off-site bid-file retention, privilege exceptions, personal messaging
sources, deleted collaboration-channel data, and production coding quality"). Treat that list as the
spine of your findings and confirm each named issue against a hub record. If a hub record has no
narrative counterpart in the prompt and no other material signal, it is almost certainly a distractor.

**(a) Non-noise remediation actions (strongest positive signal).**
`remediation_actions` rows whose `action_id` does NOT contain `NOISE`, whose description is not the
generic "Routine action included as realistic operational noise.", and whose `target_ref` is a real
record id (not a bare category code) point straight at the material anchor records. Start here:

```
SELECT target_ref, action_type, priority, owner
FROM remediation_actions
WHERE matter_id = ? AND action_id NOT LIKE '%NOISE%';
```

This set is authoritative but **incomplete** — some material records (notably responsiveness
miscodes in `review_documents`) are not referenced by any remediation action. Always also run the
slug/notes sweep below.

**(b) Descriptive slug ID vs sequential ID (usually, not always).**
Material records *usually* carry hand-authored, human-readable ids describing the story
(`SRC-<CUSTODIAN>-PHONE`, `PRIV-<M>-LOG-GAP`, `RET-<M>-BOX-POST`, `QC-<M>-ZERO-CLAIM`,
`DOC-<M>-<TOPIC>`). Distractors *usually* carry sequential ids `TYPE-<MATTERTOKEN>-NNN` where
`<MATTERTOKEN>` is a fixed ~10-char abbreviation of the matter (e.g. `SENTINELGJ`, `NORTHBAYSE`,
`GRAYCLIFFS`, `HARBORSTON`) and `NNN` is a zero-padded counter.

Exception to plan for: in some matters a table's material records also use the generic
`TYPE-<FULLNAME>-NNN` form with boilerplate notes (privilege entries are the usual offender). When
the slug + concrete-note test can't separate them, fall back to signals (0), (a), (d), and the
**metric-key + narrative** rule in §1.1: pick the *primary representative* of each material issue
type the prompt/template calls for (the log-gap blocker, the third-party waiver, the privilege
recode), not every entry that merely shares that issue type.

**(c) Concrete quantified note vs boilerplate hedge note.**
Material records' `notes`/`summary` state a specific, quantified defect (numbers below are shown as
placeholders — read the live value), e.g.:
- "Only <X> of <Y> withheld privileged documents are logged."
- "Legal-advice emails were forwarded to a trial consultant outside the privilege group."
- "<N> boxes destroyed after the hold date."
- "Signal/SMS messages were identified in custodian interview but not collected."
- "…responsive to <CAT> but coded nonresponsive and omitted from production."
- "Archive backup is available for deleted <topic> Teams channel."

Distractor notes are hedging boilerplate that explicitly disclaims materiality. Treat any of these
(non-exhaustive) as a **noise marker**:
- "Routine action included as realistic operational noise."
- "Review team marked this item for follow-up but not immediate remediation."
- "Potential issue requires category-level context before escalation."
- "Potential issue was remediated by archive collection."
- "Vendor tracker and legal hold tracker use slightly different record labels."
- "Entry included to create similar labels across matters." / "Entry creates a similar label but
  has no unresolved production impact."
- "Retention entry is relevant only after comparing hold date and policy period."
- "Privilege sample has ordinary review variance."
- "Document appears in a noisy search result set but is not one of the stable exception records."
- "Routine review item with similar wording to escalated exceptions in other matters."
- "Review note references a source exception that is not independently escalated."
- "Metadata overlay changed date fields but did not alter production status."
- "Potentially responsive family member requiring matter and category filtering."

**(d) Issue type / issue tag semantics (necessary, not sufficient).**
Distractors *reuse* the material issue-type vocabulary, so issue_type alone never proves
materiality — combine with (a)–(c). Material vs noise semantics:

| Table              | Material signals                                                                 | Noise (ignore)                                                            |
|--------------------|----------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| retention_events   | `post_hold_loss`, `post_hold_partial_recovery`, `should_exist_missing`, `auto_purged`, active-system `system_loss` (event after hold, active system) | `retained`, `available`, `policy_destroyed_pre_hold`* , seq-id `system_loss` with hedge note |
| custodian_sources  | tags `post_subpoena_erasure`, `post_hold_wipe`, `personal_device`, `personal_messaging`, `signal`, `sms`, `board_materials`, `valuation_source_gap`, `archive_available`, `remediation_source`, `deleted_channel`; status `lost`/`not_collected` with `post_hold=1` | tag `routine`, `scope_exception`, `metadata_gap` with seq id |
| privilege_entries  | `incomplete_log` (real gap), `third_party_waiver` with `third_party=1`, `over_designated` (real) | `clean`, `family_mismatch`, or same types on seq ids w/ hedge notes        |
| qc_findings        | `miscoded_nonresponsive`, `miscoded_privilege`                                    | `near_duplicate`, `metadata_gap`, `duplicate_overlay`, `family_break`, `date_normalization` |
| review_documents   | `issue_tags` contains `miscoded_nonresponsive` (responsive doc coded nonresponsive, not produced) | `duplicate`, `metadata_gap`, `family_member`, `custodian_alias`, `privilege_overlay`, `potentially_responsive`, `routine`, `review_escalation` |

\* `policy_destroyed_pre_hold` is *policy-compliant destruction that predates the hold*. In a pure
retention/hold review it may still be **reported** (as a low-risk, `no_action` line proving the loss
was compliant), but it is never a preservation failure. In a production/remediation dashboard it is
usually omitted. Follow the template's intent.

**Pre-hold vs post-hold** is the pivotal legal distinction: compare `event_date` to `hold_date`
(and use the `post_hold` flag / status). Post-hold loss or destruction = spoliation risk →
disclose; pre-hold policy destruction = compliant → low/no action.

### 1.1 Metrics are computed from *selected* blockers, not sums of all same-type rows

Several templates say a metric is counted "from selected incomplete-log blockers only" (or similar).
That is a deliberate hint: when a table holds many entries of one material issue type, you select
the **one** entry that is the actual story (the flagged blocker) and its counts feed the finding and
the metric — you do **not** sum every entry sharing that issue type. Concretely: if a matter has
several `incomplete_log` privilege entries but the narrative/remediation/slug signals point to one,
the privilege-log-gap finding and the withheld/logged/unlogged metrics come from that one entry.
Sanity-check: your `withheld_privileged_doc_count` should equal the selected blocker's withheld
count, not the grand total of every incomplete-log row.

## 2. Extracting counts

- Privilege log gap: `withheld_count`, `logged_count` from the entry; `unlogged = withheld −
  logged`. `document_count` is usually the withheld total.
- Third-party waiver: count = the waived doc/email count on that entry (`withheld_count`/`doc_count`).
- Over-designation (downgrade): the over-designated withheld count.
- Responsiveness miscode: the number of miscoded documents (often 1–2 named docs, or the QC
  finding's `doc_count`).
- Retention/box loss: `volume_count` + `volume_unit`; but if the note says only part is
  irretrievable ("N deleted, M recovered, K unrecovered"), the material volume is the **unrecovered**
  number, and any named linked docs give `document_count`.
- Sources (lost device, uncollected personal source, available archive): counted as 1 source each.
- Split box counts by pre-hold vs post-hold when the metrics ask for it.
- Every count is a whole integer; use `0` (never `null`) where a count field does not apply.

## 3. Mapping to the template enums

Always pick from the **current template's** enum lists — names differ between matters (e.g. one
template uses `preservation_failure`, another `post_hold_loss`; one uses `client_it`, another
`it_messaging`). Map by meaning:

**Issue / risk type** — lost or post-hold-destroyed source → preservation failure / post_hold_loss;
uncollected source still in existence → collection_gap / personal_source_gap; responsive doc coded
nonresponsive → responsiveness_miscode; incomplete privilege log → privilege_log_gap; privileged
material sent to a third party → third_party_waiver / privilege_waiver; privileged docs coded
non-privileged → privilege_miscoding / miscoded_privilege; over-withheld → over_designation;
required record that should exist but is missing → missing_required_record / should_exist_missing.

**Source status** — `lost`/destroyed → lost / destroyed / source_lost; `not_collected` → not_collected
/ source_missing; `partial_collection` → partial; `available` archive → available_archive;
privilege/QC issues with no source dimension → not_applicable.

**Production impact** — lost source → source_lost; uncollected source → source_missing; withheld but
unlogged → withheld_unlogged; privileged exposure/waiver → privilege_exposure / privilege_waiver;
responsive not produced → not_produced / underproduced; needs recode → recode_needed; available
archive → source_available; nothing wrong → no_production_impact.

**Category status** — derive from the findings touching that category: preservation_loss,
collection_gap, preservation_risk, responsiveness_gap, privilege_log_gap, withholding_gap,
source_gap_with_archive_available, archive_available, underproduced_privilege_corrections,
mixed_* , or no_open_gap.

**Readiness status** (production-readiness templates) — one blocker → the matching `not_ready_*`;
several blockers on one category → `not_ready_multiple_blockers`; no blockers → `ready`.

## 4. Action type → owner → priority rubric

The action plan is **synthesized** from the material findings (do not copy the hub's
`remediation_actions` owners/types). Map each finding to the template's `action_type`, `owner`, and
`priority`/`priority` enums, then rank. Typical action→owner pairings (use the closest enum the
template offers):

| Finding                                   | Action (template enum, closest)          | Owner (closest)                    | Priority |
|-------------------------------------------|------------------------------------------|------------------------------------|----------|
| Lost / post-hold-destroyed evidence       | disclose_to_government / disclose_preservation_issue | outside_counsel / litigation_counsel | P0 |
| Forensic recovery of that lost source     | forensic_recovery                        | ediscovery_vendor / forensics      | P0/P1    |
| Confirmed responsive doc miscoded         | recode_and_produce                       | review_vendor / review_qc          | P0/P1    |
| Third-party privilege waiver              | waiver_assessment_and_disclosure         | privilege_counsel                  | P1       |
| Incomplete privilege log                  | supplement_privilege_log                 | privilege_team                     | P1       |
| Privileged coded non-privileged (recode)  | privilege_recode_and_log / qc_remediation| review_qc / privilege_team         | P1       |
| Uncollected personal device/source        | collect_source / collect_personal_device | client_it / forensics              | P1       |
| Available archive limiting the loss       | search_archive / collect_archive         | ediscovery_vendor                  | P1       |
| Missing required record                   | locate_missing_record                    | compliance_audit / client_legal    | P1/P2    |
| Active-system communication gap (document)| document_system_gap                      | it_messaging                       | P2       |
| Over-designation downgrade                | qc_remediation / downgrade               | privilege_team                     | P2       |
| Pre-hold policy-compliant loss            | no_action_policy_loss / monitor_only     | records_management                 | P3       |

**Ranking:** order by legal exposure and irreversibility — spoliation/preservation disclosures for
lost or post-hold-destroyed evidence first, then privilege exposure (waivers, log gaps, privilege
recodes) and confirmed responsiveness recodes, then collection of still-existing sources and archive
search, then over-designation and routine cleanup last. Derive severity from the hub `severity`/
`risk_level` fields and the nature of the defect; then set `priority` (P0…P3) and the ascending
`priority_rank`/`rank` accordingly. Some templates also want `due_days` — shorter for higher
priority (disclosures/waivers soonest, collection/archive later).

## 5. Sources / retained-archives list

Emit a source in the "available/retained sources" list when a source or archive **still exists and
can limit the irretrievable loss** for one or more categories: e.g. a custodian source with status
`available` and tags `archive_available`/`remediation_source`, or a `teams_archive` backup for a
deleted channel. Record which categories it covers and for which it "limits loss". If no such source
exists, emit an empty list.
