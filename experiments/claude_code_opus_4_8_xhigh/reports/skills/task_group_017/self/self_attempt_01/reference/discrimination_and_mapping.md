# Material discrimination, gap taxonomy & hub→template mapping

Companion to `SKILL.md`. Use after you have the material record set.

## 1. Material vs. noise — quick reference

| Signal | MATERIAL | NOISE (exclude) |
|---|---|---|
| Remediation action | `P1`/`P2`, `target_ref` = specific record id | `*-NOISE-*`, `P3`/low, `target_ref` = bare category code |
| Record id | descriptive suffix (`-LOG-GAP`, `-POST`, `-SIGNAL`, `-ZERO-CLAIM`, `-MISCODED-PRIV`, `-CONSULTANT`, `-OVERDESIG`, `-SHARE-DEL`, `-EHS-POST`, …) | plain sequential (`PRIV-<MATTER>-007`, `QC-<MATTER>-003`) |
| Note | concrete, quantified, unresolved problem | hedging/dismissive phrasing (see SKILL.md list) |
| Status/tags | loss/gap status; non-routine `issue_tags` | `["routine"]`; "no unresolved impact" |
| Owner (action) | Forensics / Privilege Team / Review Operations / Legal Hold Team | Matter Associate / Vendor Team |

**Severity and raw counts are NOT selection signals.** Noise carries high
severity and big numbers on purpose. The note + id + anchoring decide it.

## 2. Gap taxonomy (what each material record means)

- **Post-hold preservation loss / spoliation** — `retention_events` with
  `event_date >= hold_date` and a post-hold-loss status, or a custodian source
  `lost` after the hold. Most severe. Must be disclosed to the government.
- **Pre-hold policy-compliant destruction** — `event_date < hold_date`,
  routine records-schedule destruction, "no unresolved impact." **Not a gap;**
  report as policy-destroyed / no-action where the schema asks, and keep it out
  of loss metrics.
- **Missing required record** — status `should_exist_missing`: a record that
  should exist but is absent.
- **Uncollected personal source** — `custodian_sources` `not_collected` /
  `partial_collection` for personal phones, SMS/Signal (`personal_messaging`),
  personal email, laptops. Collection gap.
- **Deleted collaboration channel** — deleted Teams/Slack channel; often paired
  with an **available archive** that limits the loss.
- **Available archive / retained source** — status `available` with
  `archive_available` tag: a remediation path that limits irretrievable loss;
  list it as a retained/available source and as the fix for the related gap.
- **Responsiveness miscode / zero-claim contradiction** — `qc_findings`
  `zero_claim_contradiction` (a "zero production" category contradicted by
  responsive docs) or responsive docs coded nonresponsive. Recode and produce.
- **Privilege log gap** — `privilege_entries` `incomplete_log` with
  `unlogged = withheld − logged > 0` (material one has the factual note).
  Supplement the log.
- **Privilege over-designation / miscoding** — `over_designated`, or a
  `miscoded_privilege` QC finding (privileged docs coded non-priv, or vice
  versa). Recode / downgrade / re-review.
- **Third-party privilege waiver** — `third_party_waiver` (`third_party=1`):
  privileged material shared outside privilege (e.g. to a consultant). Assess
  waiver and disclose.

## 3. Retention pre/post-hold logic

1. Compare the event's `event_date` to the matter `hold_date`
   (`GET /api/matters`).
2. `event_date >= hold_date` **and** a loss status → **post-hold loss**:
   critical, disclose. Counts toward post-hold-loss metrics.
3. `event_date < hold_date` **and** routine policy destruction with a "no
   unresolved impact / remediated" note → **pre-hold policy loss**: no gap, no
   action, excluded from loss metrics.
4. `should_exist_missing` → missing-required-record finding.
5. `available` archive → remediation path; note the categories it rescues.

## 4. Owner translation (raw hub → template `owner` enum)

Pick the closest value present in *this template's* owner enum.

| Raw hub owner | Maps to (choose from template enum) |
|---|---|
| Forensics | `forensics` → else `ediscovery_vendor` → else `outside_counsel` |
| Privilege Team | `privilege_team` → else `privilege_counsel` |
| Review Operations | `review_qc` / `review_operations` / `review_vendor` |
| Legal Hold Team | `client_legal` / `litigation_counsel` / `records_management` / `legal_operations` |
| Vendor Team | `ediscovery_vendor` / `records_vendor` (usually a noise action) |
| Matter Associate | (noise — do not surface) |

For a finding the hub did not pre-stage an action for, choose the owner by the
work: collection → forensics/ediscovery; privilege → privilege team/counsel;
recode/QC → review QC; disclosure → outside counsel/client legal.

## 5. Action-type translation (raw hub → template `action_type` enum)

Driven by the finding's issue semantics **and** source type. Always pick a value
that exists in the template's `action_type` enum.

| Raw hub action_type | Finding context | Maps to (examples across templates) |
|---|---|---|
| supplemental_collection | personal phone / SMS / Signal | `collect_personal_device`, `collect_signal_messages`, `collect_source` |
| supplemental_collection | personal email | `collect_personal_email`, `collect_source` |
| supplemental_collection | available archive / deleted channel | `search_archive`, `collect_archive` |
| privilege_rework | incomplete_log | `supplement_privilege_log` |
| privilege_rework | over_designated | `privilege_recode_and_log`, `privilege_re_review`, `downgrade` |
| privilege_rework | third_party_waiver | `waiver_assessment_and_disclosure`, `waiver_assessment` |
| qc_remediation | responsiveness / zero-claim | `recode_and_produce` |
| qc_remediation | miscoded_privilege | `privilege_recode_and_log`, `recode_and_produce`, `qc_remediation` |
| retention_exception_review | post-hold loss | `disclose_preservation_issue`, `disclose_to_government` |
| retention_exception_review | available archive | `search_archive`, `collect_archive`, `restore_from_backup` |
| retention_exception_review | pre-hold policy loss | `no_action`, `no_action_policy_loss` |
| custodian_followup / load_file_cleanup / sampling_review | — | noise; use `monitor_only`/`no_action` only if the schema forces an entry |

## 6. Priority, rank, severity, due_days

- `priority` field: use the hub action's `P0/P1/P2/P3` when it exists; otherwise
  assign by severity (post-hold loss/spoliation → P0/P1).
- `priority_rank` / `rank`: 1-based ordering across the action list. Order by
  priority (P0<P1<P2<P3), then severity (critical<high<medium<low), then
  smaller `due_days` first; break ties by target id ascending.
- `risk_level` / `severity`: map hub `severity` (critical/high/medium/low)
  straight to the template enum; post-hold preservation loss is typically
  `critical`.
- `due_days`: use the material remediation action's `due_days` when the template
  asks for it.

## 7. Category coverage

- One entry per request category that has a **material** non-complete status.
- `status` = the category-level enum that best summarizes the material findings
  touching that category (preservation loss, collection/personal-source gap,
  privilege log gap, responsiveness gap, archive available, missing record, …).
- `issue_refs` / `source_refs` = the material record ids touching the category,
  sorted ascending. `open_issue_count` = number of material issue records
  summarized for that category.
- Categories with no material issue are `no_open_gap` / `complete` /
  `no_current_gap` (per the template) — usually omitted unless the template asks
  to list every category.
