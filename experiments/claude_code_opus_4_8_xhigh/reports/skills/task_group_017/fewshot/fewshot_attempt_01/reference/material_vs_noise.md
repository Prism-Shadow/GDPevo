# Material vs. noise — per-table signal catalog

The hub mixes a small number of **escalated, material** issues into a larger pool
of realistic **noise**. Reproducing the gold answer means selecting exactly the
material set. Use three converging signals: the **remediation-action anchor**,
the **id shape**, and the **note text / issue type**. When they disagree, prefer
the anchor + a concrete-defect note, and cross-check against the prompt's focus
list.

## The anchor: `remediation_actions`

Split the rows:
- **Noise:** `description` == "Routine action included as realistic operational
  noise"; `action_type` ∈ {`load_file_cleanup`, `custodian_followup`,
  `sampling_review`}; `target_ref` is a **bare category code** (`C`, `F`, `R11`,
  `SEC-1`, …). Discard.
- **Material:** `description` == "Review and remediate <ID> before next production
  certification"; `target_ref` is a **record id** (`RET-…`, `SRC-…`, `PRIV-…`,
  `QC-…`). These target the matter's real escalated issues. Their `severity`/
  `priority` inform (but do not dictate) your final ranking.

The anchor is the backbone of the material set. Then adjust:
- **Add** privilege-log / third-party-waiver defects for the privilege-focus
  category, and any doc named by a material QC finding's `source_ref`, even if no
  remediation row points at them.
- **Drop** an anchored target that is immaterial to this specific deliverable
  (e.g. a pure over-designation cleanup omitted from a preservation-only
  dashboard). The template's enums + the prompt's focus list are the arbiter.

## Id-shape heuristic

- **Material:** descriptive id with a semantic token —
  `SRC-<M>-<CUSTODIAN>-<DEVICE>`, `RET-<M>-<TOPIC>`, `QC-<M>-<DEFECT>`,
  `PRIV-<M>-<NAME/DEFECT>`, `DOC-<M>-<TOPIC>`.
- **Usually noise:** dense sequential id — `SRC-<MATTER>-007`,
  `QC-<MATTER>-004`, `DOC-<MATTER>-0126`, `RET-<MATTER>-003`.
- **Caveat:** some matters escalate plain-sequential privilege entries
  (`PRIV-<MATTER>-001`/`-002`) as material. Never rely on id shape alone —
  confirm with the note and issue type.

## Note-text heuristic

- **Material notes** state a specific defect with real numbers/dates/names:
  "erased on <date> after subpoena issuance", "log covers N of M withheld …",
  "two boxes destroyed after the hold date", "zero-production claim contradicted
  by two responsive … emails", "N privileged documents were initially coded
  non-privileged", "N business-only emails are over-designated as privileged".
- **Noise notes** are generic, hedging, or self-cancelling: "included as
  realistic operational noise", "…to create similar labels across matters",
  "ordinary review variance", "similar to escalated records in another matter",
  "requested re-sampling before escalation", "remediated by archive collection",
  "no unresolved production impact", "not dispositive without source comparison",
  "relevant only after comparing hold date and policy period", "differs between
  custodian tracker and vendor load report".

## Per-table quick reference

### retention_events
- Material statuses: `post_hold_loss` (highest — disclosable), `should_exist_missing`,
  `policy_destroyed_pre_hold` (no-fault/low), and communication/system losses
  `system_loss` / `auto_purged` when on a messaging or voice record type.
- Noise: `retained`, `available` (these are retained/available sources, not
  losses — but an `available` archive may still be reported as a *remediation
  source*), and any generic-id row whose note self-cancels.

### custodian_sources
- Material: `status='lost'` (esp. `post_hold=1`, `source_type` a personal device
  → critical spoliation); `status='not_collected'` for a key/personal/board
  source; `status='available'` with `issue_tags` including `archive_available` /
  `remediation_source` (an available remediation archive).
- Noise: `collected`, `in_review`, most `partial_collection`, and routine rows
  (`issue_tags:['routine']`) with generic ids/notes.

### privilege_entries
- Material: `issue_type='incomplete_log'` (privilege-log gap; report
  withheld/logged and unlogged=diff); `issue_type='third_party_waiver'` with
  `third_party=1` (waiver exposure); `issue_type='over_designated'` when the
  deliverable calls for downgrade/QC of business docs withheld as privileged.
- Noise: `issue_type` ∈ {`clean`, `family_mismatch`}; and duplicate defect entries
  in non-focus categories (pick the entry that matches the matter's privilege
  focus, not every same-typed row).

### qc_findings
- Material: `issue_type` ∈ {`miscoded_nonresponsive`, `zero_claim_contradiction`,
  `miscoded_privilege`} — genuine coding/production defects. Follow `source_ref`
  to the affected document(s).
- Noise: `issue_type` ∈ {`near_duplicate`, `metadata_gap`, `family_break`,
  `duplicate_overlay`, `date_normalization`, `family_mismatch`} — routine QC
  variance, **even when `severity='high'`**.

### production_stats
- Context, not usually a standalone finding: `status='rolling_review'`/
  `'supplement_pending'` and a `zero_claim_reason` can corroborate a QC
  zero-claim contradiction or an incomplete rolling production, but the escalated
  issue itself comes from qc_findings / privilege / sources / retention.
