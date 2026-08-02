# Investigation Review Hub — data model

The hub is a read‑only store shared across many matters. Every table has a
`matter_id`; always filter by yours. Learn the live layout from the hub's schema
description at task time; the tables and the fields that drive the answer are:

| Table | Grain | Key columns you use |
|---|---|---|
| `matters` | one per matter | `matter_id`, `agency`, `investigation_type`, `issued_date`, **`hold_date`** (baseline for pre/post‑hold classification), `status` |
| `subpoena_categories` | one per request category | `category_code`, `title`, `topic_tags` — category codes and titles only |
| `production_stats` | one per production batch/category | `category_code`, `status`, `produced_count`, `withheld_count`, `responsive_count`, **`zero_claim_reason`** (non‑empty / a `zero_claim_contradicted` status flags a zero‑production‑claim problem), `notes` |
| `custodian_sources` | one per collected/known source | `source_id`, `custodian_name`, `role`, `source_type` (personal_phone, personal_email, personal_messaging, laptop, mailbox, teams_export, teams_archive, sharepoint_site, network_share, mobile_backup, email_archive, …), `status` (lost, not_collected, partial_collection, collected, available, in_review), **`post_hold`** (0/1), `category_impacts`, `issue_tags`, `notes` |
| `review_documents` | one per document | `doc_id`, `category_code`, `responsiveness`, `privilege_status`, `produced_status`, `issue_tags` — supporting detail behind QC/privilege findings |
| `privilege_entries` | one per privilege issue | `entry_id`, `category_code`, `doc_count`, **`withheld_count`**, **`logged_count`**, `issue_type` (incomplete_log, over_designated, third_party_waiver, family_mismatch, clean), `third_party` (0/1), `notes` |
| `qc_findings` | one per QC finding | `finding_id`, `batch_id`, `issue_type` (miscoded_nonresponsive, miscoded_privilege, zero_claim_contradiction, family_break, near_duplicate, metadata_gap, …), `doc_count`, `affected_category`, `source_ref`, `severity`, `notes` |
| `retention_events` | one per retention/loss event | `event_id`, `record_type`, `status` (policy_destroyed_pre_hold, post_hold_loss, system_loss, auto_purged, should_exist_missing, retained, available, post_hold_partial_recovery), `event_date`, `hold_date`, `policy_section`, `retention_period_months`, `volume_count`, `volume_unit`, `affected_categories`, `source_ref`, `notes` |
| `remediation_actions` | one per escalated action | `action_id`, `action_type`, `priority` (P0–P3), `severity`, `owner`, **`target_ref`**, `due_days`, `description` — the authoritative list of what is material |

## Access shape (generic)
The environment access file the task provides names a read‑only hub exposing a
read endpoint per record type plus one read‑only SQL query endpoint, and the
credential header to send. Use the SQL endpoint for efficient, matter‑filtered
bulk pulls (`SELECT * FROM <table> WHERE matter_id = '<your matter>'`). Read the
real base location and credential from that file each run rather than hard‑coding
anything.

## How tables map to typical output sections
- **Findings / issue ledger / top risks** ← the material records from
  `custodian_sources`, `retention_events`, `privilege_entries`, `qc_findings`,
  `production_stats` (zero‑claim).
- **Category statuses / coverage / readiness** ← per `subpoena_categories` code
  that a material record touches.
- **Retention events vs communication gaps** ← `retention_events`, split by
  record medium (records/boxes vs messaging systems).
- **Privilege corrections** ← `privilege_entries` (and privilege‑miscode QC).
- **Available / retained sources** ← `custodian_sources` whose status is an
  available archive or retained system.
- **Metrics** ← rollups of the above.
- **Priority actions / action plan** ← the non‑noise `remediation_actions`.
