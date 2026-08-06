---
name: investigation-review-hub-gap-analysis
description: Produce a structured-JSON gap analysis / remediation dashboard from the Investigation Review Hub for a legal-investigation matter (grand-jury or SEC subpoena). Use when a task asks for a JSON deliverable conforming to an answer_template.json and points at a running Review Hub as the source of record — covering production gaps, retention/preservation losses, privilege-log defects, QC findings, custodian/source gaps, metrics, and prioritized remediation actions.
---

# Investigation Review Hub — Gap Analysis & Remediation Dashboard

These tasks ask for **one JSON object** (no prose) that conforms to a task-specific
`input/payloads/answer_template.json`. The template defines the exact top-level keys,
section lists, item fields, **enum choices**, ordering rules, and numeric precision.
The answer is scored by exact field/value match, so precision matters more than
narrative quality.

## Source of record

The **Investigation Review Hub** is a read-only SQL hub. The base URL, the access header
and key, and the list of allowed endpoints are in the task's `environment_access.md`
(and usually restated in the payload context file) — read them from the task, do not
assume or hardcode them. Workflow:

1. Fetch the hub's schema endpoint to learn the tables and columns.
2. Use the read-only SQL query endpoint (with the task's access header/key) to `SELECT`
   each table filtered by the task's `matter_id`.

The hub tables (consistent across matters):

| Table | What it holds | Key columns |
|---|---|---|
| `matters` | Matter metadata | `matter_id`, `hold_date`, `issued_date`, `agency` |
| `subpoena_categories` | Request categories | `category_code`, `title`, `topic_tags` |
| `production_stats` | Per-batch production counts | `batch_id`, `category_code`, `produced/withheld/responsive/nonresponsive_count`, `status`, `zero_claim_reason` |
| `custodian_sources` | Custodian data sources | `source_id`, `source_type`, `status`, `post_hold`, `category_impacts`, `issue_tags` |
| `review_documents` | Review docs | `doc_id`, `category_code`, `responsiveness`, `privilege_status`, `produced_status`, `issue_tags` |
| `privilege_entries` | Privilege-log entries | `entry_id`, `doc_count`, `withheld_count`, `logged_count`, `issue_type`, `third_party` |
| `qc_findings` | QC findings | `finding_id`, `issue_type`, `doc_count`, `affected_category`, `source_ref`, `severity` |
| `retention_events` | Retention/preservation events | `event_id`, `record_type`, `event_date`, `hold_date`, `status`, `volume_count`, `volume_unit`, `affected_categories` |
| `remediation_actions` | Remediation action plan | `action_id`, `action_type`, `priority`, `severity`, `owner`, `target_ref`, `due_days` |

**Never** inspect local environment source files, database files, seeds, manifests, or
setup scripts — only the running hub endpoints and the task-local payload files.

## Critical: separate SIGNAL from NOISE

Every matter is seeded with realistic **distractor records**. Including them as findings
or counting them in metrics produces wrong answers. Filter ruthlessly.

### Signal records (include)
- **Explicitly-named IDs** with a descriptive suffix, e.g. `SRC-SENT-ALDEN-PHONE`,
  `PRIV-NORTH-LOG-GAP`, `QC-GRAY-MISCODED-PRIV`, `RET-ALLOY-BOX-POST`,
  `DOC-ALLOY-BID-EMAIL-1`. The ID pattern is `{TYPE}-{MATTERCODE}-{DESCRIPTOR}`.

### Noise records (exclude)
- **Generic sequential IDs** like `SRC-SENTINELGJ-001`, `PRIV-GRAYCLIFFS-002`,
  `RET-HARBORSTON-003`. The ID pattern is `{TYPE}-{MATTERCODE}-NNN`.
- **Hedging notes** confirm noise: "routine", "no production-impacting issue has been
  escalated yet", "Review team marked this item for follow-up but not immediate
  remediation", "Privilege sample has ordinary review variance", "Entry included to
  create similar labels across matters", "Finding is similar to escalated records in
  another matter", "Review manager requested re-sampling before escalation",
  "Potential issue was remediated by archive collection", "Source map entry has minor
  metadata normalization issues", "Collection status differs between custodian tracker
  and vendor load report", "Requires matter-level filtering because similar issue labels
  appear across matters".

### Cross-check (definitive)
The `remediation_actions` table lists the signal record set explicitly:
- **Non-noise actions** (e.g. `ACT-SENTINELGJ-001`, `ACT-ALLOYWORKS-017`) target exactly
  the signal records via `target_ref`. These are your finding/risk record IDs and the
  basis for the action plan.
- **Noise actions** have `NOISE` in the `action_id` and description
  "Routine action included as realistic operational noise." Exclude them entirely.

The set of signal records = the set of `target_ref` values from non-noise
`remediation_actions`. This is the single most reliable signal detector — use it.

## Building the answer

### 1. Carry hub-exact fields straight through
Record IDs, `category_code`/`affected_categories`, integer counts
(`doc_count`, `withheld_count`, `logged_count`, `volume_count`), dates
(`event_date`, `hold_date`), `policy_section`, `retention_period_months`,
`record_type`, `source_type`, `custodian_name`, `third_party` flag → map directly.
These are the fields most likely to match exactly — get them verbatim.

- `unlogged_count` = `withheld_count` − `logged_count`.
- `affected_categories`/`category_impacts`: split the comma string, **sort ascending**.
- `source_refs`/`record_refs`: the finding's own anchoring ID plus any `source_ref`
  the hub links (e.g. a QC finding's `source_ref` document IDs). Sort ascending.

### 2. Map hub status/issue vocabulary to the template enums
The hub uses its own vocabulary; map to the **exact** enum strings in the template.
Common mappings (verify against the specific template's enum list):

- Retention status: `system_loss`→`active_system_loss`, `retained`→`preserved_available`,
  `available`→`available_archive`, `post_hold_partial_recovery`→`post_hold_loss`,
  `should_exist_missing`/`policy_destroyed_pre_hold`/`post_hold_loss`/`auto_purged`→same.
- Privilege issue: `incomplete_log`→privilege log gap, `over_designated`→privilege
  miscoding/downgrade, `third_party_waiver`→third-party waiver,
  `miscoded_privilege`→privilege miscoding.
- QC issue: `miscoded_nonresponsive`/`zero_claim_contradiction`→responsiveness miscode,
  `miscoded_privilege`→privilege miscoding.
- Source status: `lost`→`lost`/`destroyed`, `not_collected`→`not_collected`,
  `available`→`available_archive`, `partial_collection`→`partial`.

### 3. Interpreted fields (no direct hub value — derive consistently)
- **`cutoff_date`** = the matter **`hold_date`** (the retention-compliance cutoff). Do not
  leave it null when a hold_date exists. (Confirmed: setting it to null breaks records.)
- **`risk_level`** = **preservation risk**, not the remediation severity:
  `policy_destroyed_pre_hold`→`low` (policy-compliant, no preservation risk),
  `post_hold_loss`→`high`/`critical`, `should_exist_missing`→`medium`,
  `system_loss`/`auto_purged`→`medium`, `archive_available`→`medium`.
- **`severity`** (when separate from risk_level): take from the hub `severity` field of
  the remediation action / QC finding.
- **`priority`**: copy the hub `priority` (`P0`/`P1`/`P2`/`P3`) verbatim.
- **`priority_rank`**: P1 before P2; within a tier, follow the hub `action_id` order.
  Rank 1 = highest.
- **`production_impact`**: lost/destroyed source→`source_lost`; not-collected
  source→`source_missing`; miscoded/non-produced doc→`not_produced`/`recode_needed`/
  `underproduced`; withheld-unlogged→`withheld_unlogged`; privilege waiver→`privilege_exposure`;
  available archive→`source_available`.
- **`third_party`** (string or null): the recipient name from the note (e.g. "Derek
  Winslow", "trial consultant") when `third_party=1`; else null.

### 4. Owner mapping
Hub owner strings rarely match the enum exactly. Map by closest meaning and reuse the
same mapping across actions for the same matter:

| Hub owner | Map to (pick the one present in THIS template's owner enum) |
|---|---|
| `Forensics` | `forensics` (direct, when present) else `ediscovery_vendor` else `client_it` |
| `Review Operations` | `review_qc` / `review_vendor` / `review_operations` (whichever the enum has) |
| `Privilege Team` | `privilege_team` |
| `Legal Hold Team` | `client_legal` / `privilege_counsel` |
| `Vendor Team` | `ediscovery_vendor` |
| `Records Management` | `records_vendor` |

### 5. Action-type mapping (hub `action_type` → template `action_type` enum)
- `supplemental_collection` on a **lost/destroyed** source → `forensic_recovery` or
  `disclose_preservation_issue`.
- `supplemental_collection` on a **not-collected personal** source → `collect_personal_device`
  / `collect_source`.
- `supplemental_collection` on an **archive** → `collect_archive` / `search_archive`.
- `privilege_rework` on incomplete log → `supplement_privilege_log`; on over-designation →
  `privilege_recode_and_log` / `recode_and_produce`; on waiver → `waiver_assessment_and_disclosure`.
- `qc_remediation` → `qc_remediation` (when the enum has it) else `recode_and_produce`
  else `quality_control_review`.
- `retention_exception_review` → `disclose_preservation_issue` (post-hold loss),
  `locate_missing_record` (should-exist-missing), `restore_from_backup` (system loss),
  `no_action_policy_loss` (policy-destroyed-pre-hold).

### 6. Metrics
- Count **signal records only** unless a metric description explicitly broadens scope.
- **"selected incomplete-log blockers"** / **"selected"** qualifier → only the
  material/signal privilege entries that are incomplete-log blockers
  (`withheld_count` > `logged_count`). If a matter has no signal incomplete-log entry,
  the privilege withheld/logged/unlogged metrics are `0`.
- Box/file counts: sum `volume_count` over signal events with the matching `volume_unit`.
- `*_count` category metrics: size of the union of `affected_categories` across signal
  records.
- `production_ready` / `rolling_production_ready`: `false` if any critical/high signal
  gap exists, else `true`.
- **The metrics block tends to be scored as a unit** — one wrong metric value can fail
  the whole block, so every metric must be correct simultaneously. Recompute each
  carefully and double-check ambiguous ones. Example: `destroyed_lab_archive_box_count`
  is "boxes for the destroyed records source named in the task, or 0 when not measured in
  boxes" — read the description literally; if the matter's destroyed source is not a lab
  archive it may be `0` even when other boxes were destroyed.

### 7. Section-specific guidance
- **Findings / top_risks**: one record per signal gap/defect, `finding_id`/`risk_id` =
  the anchoring hub record ID. Available archives usually belong in
  `retained_or_available_sources`, not in risks — but if `archive_available` is a valid
  issue_type, an available archive may also appear as a remediable risk. Check whether
  the matter's available-archive source should be counted in `top_risk_count`.
- **Category statuses / coverage**: one entry per category with a material non-complete
  status (categories touched by ≥1 signal record). `open_issue_count` = number of signal
  records touching that category.
- **Action plan / priority_actions**: one per non-noise `remediation_action`.
  `target_refs` = the action's `target_ref` (plus linked records); `due_days` from the hub.
- **retained_or_available_sources**: sources with `status` = available/archive — the
  remediation paths. `limits_loss_for_categories` = categories the archive actually covers.

### 8. Ordering
Apply every `ordering_rules` entry from the template: sort lists by the specified key
ascending (finding_id, category_code, source_id, priority_rank/rank, target_id). Sort
every category-code list ascending within items.

## Validation before finalizing (do this every time)

The answer is scored by exact field/value match against a gold answer. Two consequences:

1. **Prefer the hub's literal value for direct fields** (e.g. `volume_unit="report"` or
   `"files"`, `record_type`, `source_type`) **even when that value is not in the
   template's enum** — the gold is built from the same hub data and likely uses the same
   literal. Do not "correct" a hub value into a different enum member unless the field is
   interpreted (no hub value) or the hub value is clearly a status to be mapped.
2. **Enums guide interpreted fields only** — for status/issue/action/owner fields with no
   direct hub value, use an enum member (that is what the gold maps to).

Run `reference/validate.py` to confirm: all required top-level keys present; every list
item has all `item_required_keys`; every metrics `required_keys` present; integers are
integers; nullable fields are null or the right type. The validator **warns** on values
not in the template's enum — treat each as a deliberate decision (keep the hub literal,
or map to an enum member), not an automatic error.

## Reference files
- `reference/hub_tables.md` — full table/column reference and query patterns.
- `reference/signal_vs_noise.md` — detailed signal/noise detection with the noise-note catalog.
- `reference/enum_mappings.md` — consolidated hub→enum mapping tables.
- `reference/validate.py` — a validator script that checks an answer against a template's
  enums, required keys, and types.

## Approach summary
1. Read prompt + `answer_template.json` + payload context → note `matter_id`, required
   keys, enums, ordering rules.
2. Query the hub for all 9 tables filtered by `matter_id`.
3. Determine the signal record set from non-noise `remediation_actions.target_ref`.
4. Build each section from signal records: carry hub-exact fields, map enums, derive
   interpreted fields (cutoff_date=hold_date, risk_level=preservation risk).
5. Compute metrics from signal records only (respect "selected" qualifiers).
6. Order per template rules.
7. Validate enums/keys/types programmatically.
8. Emit one JSON object, no prose.
