# Record To Output Map

This reference explains how to translate Investigation Review Hub records into common structured answer sections. Apply the task template first; these rules only guide interpretation.

## Record Selection

Start with a matter-scoped evidence ledger. A row is material when it is an open blocker, protocol defect, source gap, loss, waiver, confirmed QC issue, or missing required record that affects requested categories. Rows with routine variance, noisy similarity labels, tentative review language, or no production impact should stay out of the final answer unless the prompt asks for all issues.

Use notes, issue tags, source status, produced status, and numeric counts together. A keyword alone is not enough when the hub intentionally includes noisy records.

## Source And Collection Issues

`custodian_sources` often anchors source problems:

- `lost`, `destroyed`, or post-hold erasure -> preservation/source loss.
- `not_collected` -> source missing or personal source gap.
- `partial_collection` -> partial source missing when the template supports it.
- `available`, `available_archive`, `retained`, or collected archive records -> remediation source, not a loss.

Use `category_impacts` for affected categories. For personal devices and messaging, classify by source type when the template distinguishes phone, personal email, signal/SMS, Teams/channel archives, laptop, shared drive, or off-site records.

## Retention Events

`retention_events` classify records and communication gaps:

- `policy_destroyed_pre_hold`: low risk, policy-compliant loss, usually no action beyond documentation.
- `post_hold_loss`: high or critical preservation issue; disclose or escalate.
- `auto_purged`: communication gap; record purge window and cutoff if present.
- `active_system_loss` or `system_loss`: active system communication gap; document or restore/search archive.
- `should_exist_missing`: high-risk missing required record; locate or escalate.
- `available_archive` or retained archive references: include in available archives or remediation sources.

Compare `event_date` with `hold_date` when the status or prompt requires pre-hold versus post-hold classification. Use `volume_count` and `volume_unit` as provided; do not convert units unless the template requires a specific unit.

## Review Documents And QC

Document-level blockers usually require both `review_documents` and `qc_findings`:

- Responsive document coded nonresponsive or not produced -> responsiveness miscode / recode and produce.
- QC finding with a source document -> include both the finding ID and document ID in refs when proving the issue.
- Zero-production or zero-claim contradiction -> production says no responsive material, but QC/documents show responsive material.
- Privileged documents coded nonprivileged -> privilege miscoding / privilege recode.
- Nonprivileged or business-only materials withheld as privileged -> over-designation / downgrade / QC remediation.

Use `doc_count` from `qc_findings` for the issue count when the finding is the anchor. Use counted `review_documents` only when no QC count exists and the documents themselves anchor the issue.

## Privilege Entries

`privilege_entries` are the source of privilege-log and waiver metrics:

- `incomplete_log`: withheld/logged gap. Compute `unlogged_count = max(withheld_count - logged_count, 0)`.
- `third_party` or third-party issue type: waiver/exposure issue. Count separately in waiver metrics.
- `over_designated`, business-only counsel-copy, family mismatch, or similar notes: privilege correction/QC issue when material to readiness.
- `clean` rows generally do not appear in final gap sections.

Avoid double-counting privilege documents. If a waiver record is fully logged, it contributes to waiver counts but not to incomplete-log unlogged counts. If a template metric says "selected incomplete-log blockers only", aggregate just those blockers.

## Category Rollups

Category-level sections summarize selected material issues:

- Preservation/source loss outranks collection gap.
- Multiple blocker status applies when a category has independent material blockers of different types.
- Privilege exposure or underproduced privilege corrections applies when waiver, privilege miscoding, or log gaps are central.
- Responsiveness gap applies when responsive material was miscoded, omitted, or contradicted by a zero claim.
- Archive available applies only when the open issue is mitigated by a retained source and no higher-status blocker applies.

For each category, include refs for all selected issues supporting that category, sorted and deduplicated. `open_issue_count` should count selected issue records summarized for that category, not every source ref.

## Metrics

Build metrics after final issue selection:

- Counts named for top risks, issue ledger entries, nonready categories, affected categories, or available sources should match the final selected sections.
- Counts named for specific domains, such as post-hold loss events, uncollected personal sources, missing required records, miscoded responsive documents, or destroyed boxes, should count selected records of that domain.
- Privilege log metrics use incomplete-log blockers. Waiver and miscoding metrics use separate selected records.
- Category arrays should be sorted and should include every category with any selected open gap or risk.

## Actions

Actions should target the records that need work, not every noisy candidate action. Rank by legal risk and production impact:

1. Disclosure or escalation for post-hold/source loss.
2. Waiver assessment/disclosure where privilege may be exposed.
3. Recode/produce responsive material and privilege recoding.
4. Supplement incomplete privilege logs.
5. Collect missing personal/source data or search available archives.
6. Locate missing required records or document system gaps.
7. Low-risk/no-action policy losses or monitor-only items.

If a template provides `priority` plus `priority_rank` or `rank`, keep the rank order consistent with priority labels.
