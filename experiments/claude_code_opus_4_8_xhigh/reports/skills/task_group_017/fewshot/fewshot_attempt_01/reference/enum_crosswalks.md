# Enum crosswalks — hub raw values → template enums

The hub vocabulary is broader than any one template's enum set. For each material
record, pick the closest member of the **task template's** enum (names differ per
task — always read the template's `enums`/`enum_choices` and map into *those*
exact strings). Below are the recurring semantic mappings; treat them as the
reasoning, then snap to the actual enum strings the template offers.

## Defect / issue type

| Hub signal | Semantic | Typical template value(s) |
|---|---|---|
| retention `post_hold_loss` | data destroyed/lost after the hold | `post_hold_loss`, `preservation_failure`, `retention_loss` |
| retention `policy_destroyed_pre_hold` | routine pre-hold policy destruction | `policy_destroyed_pre_hold`, `retention_loss` |
| retention `should_exist_missing` | required record missing | `should_exist_missing`, `missing_required_record` |
| retention `system_loss`/`auto_purged` (messaging/voice) | active-system / auto-purge loss | `active_system_loss`, `auto_purge`, `auto_purged` |
| source `lost` (personal device, post-hold) | spoliation of a personal source | `preservation_failure`, `post_hold_loss`, `personal_source_gap` |
| source `not_collected` (personal) | uncollected personal source | `personal_source_gap`, `collection_gap`, `personal_email_gap`, `personal_phone_gap` |
| source `not_collected` (enterprise site) | uncollected enterprise source | `collection_gap` |
| source `available` + `archive_available` tag | remediation archive on hand | `archive_available` |
| priv `incomplete_log` | privilege-log gap | `privilege_log_gap` |
| priv `third_party_waiver` (`third_party=1`) | privilege waiver exposure | `third_party_waiver`, `privilege_waiver` |
| priv `over_designated` | business docs over-withheld | `over_designation`, `miscoded_privilege`, `privilege_miscoding`, `other` |
| qc `miscoded_nonresponsive` | responsive doc coded out | `responsiveness_miscode`, `responsive_miscoding` |
| qc `zero_claim_contradiction` | zero-prod claim contradicted | `responsiveness_miscode`, `zero_claim_contradiction` |
| qc `miscoded_privilege` | privileged doc coded non-priv | `privilege_miscoding`, `miscoded_privilege` |

## Status of the finding / source

| Situation | Typical value(s) |
|---|---|
| lost/destroyed source or data | `lost`, `destroyed`, `source_lost` |
| never collected | `not_collected`, `should_exist_missing`, `open` |
| partially collected | `partial`, `partial_collection` |
| available archive / retained | `available_archive`, `available_retained_source`, `collected`, `preserved_available` |
| privilege protocol not met (unlogged withholdings, uncured waiver) | `protocol_noncompliant`, `incomplete_log` |
| coding needs correction | `needs_recode`, `open` |
| routine pre-hold loss, nothing to do | `no_gap`, `no_current_gap`, `closed` |
| a field with no source dimension | `not_applicable` |

## Production impact

| Situation | Typical value(s) |
|---|---|
| lost/destroyed data | `source_lost` |
| uncollected source | `source_missing` |
| available remediation source | `source_available` |
| responsive doc withheld from production | `not_produced`, `underproduced`, `recode_needed` |
| withheld-privileged not on the log | `withheld_unlogged` |
| privilege exposure (waiver / miscode) | `privilege_exposure`, `privilege_waiver` |
| required record missing | `missing_record`, `source_missing` |
| nothing outstanding | `no_production_impact`, `no_current_gap` |

## Action type (normalized plan)

| Defect | Action |
|---|---|
| post-hold / spoliation loss | disclose (`disclose_to_government` / `disclose_preservation_issue`) — for a lost post-subpoena personal device, also a `forensic_recovery` action |
| uncollected enterprise source | `collect_source` |
| uncollected personal device | `collect_personal_device` / `collect_personal_email` / `collect_signal_messages` |
| available archive | `collect_archive` / `search_archive` |
| responsiveness miscode / zero-claim | `recode_and_produce` |
| privilege-log gap | `supplement_privilege_log` |
| third-party waiver | `waiver_assessment_and_disclosure` |
| privileged miscode / over-designation | `privilege_recode_and_log` / `privilege_re_review` / `qc_remediation` |
| required record missing | `locate_missing_record` |
| active-system / auto-purge loss | `document_system_gap` |
| pre-hold policy loss | `no_action` / `no_action_policy_loss` |

## Owner (derive from the action, not the hub owner)

The hub `remediation_actions.owner` values (Forensics, Review Operations,
Privilege Team, Legal Hold Team, Vendor Team, Matter Associate) do **not** map
1:1 to template owners. Assign owner by the normalized action, choosing from the
template's owner enum:

| Action | Owner |
|---|---|
| disclose loss / spoliation | `outside_counsel` / `litigation_counsel` |
| forensic recovery, device or archive collection | `forensics` / `ediscovery_vendor` |
| enterprise-source collection | `client_it` / `ediscovery_vendor` |
| recode & produce / QC remediation | `review_vendor` / `review_qc` |
| supplement privilege log | `privilege_team` |
| waiver assessment | `privilege_counsel` (or `privilege_team` if no counsel enum) |
| locate missing record | `compliance_audit` / `investigation_team` |
| document active-system gap | `it_messaging` |
| pre-hold policy loss / no action | `records_management` |

## Priority / risk level

- **P0 / critical** — disclosable post-hold preservation loss or spoliation
  (lost personal device erased after subpoena; post-hold box/share destruction).
- **P1 / high** — uncollected key/personal sources; privilege-log gaps;
  third-party-waiver assessments; responsiveness recodes; privileged miscoding.
- **P2 / medium** — over-designation review; lower-severity/active-system gaps.
- **P3 / low** — monitor-only; pre-hold policy losses (no action).

Snap `risk_level`/`severity` to the template's enum (`critical|high|medium|low`)
and `priority` to `P0|P1|P2|P3`.
