# Asteria Opaque Control Codes — quick reference

Codes are undocumented in task materials; infer from record characteristics.
The allowed enum values for each field come from the task's `answer_template.json`
— always confirm against that enum set. When a record matches two rules, choose
the **most specific / most severe** applicable value, never one outside the enum.
Full reasoning in SKILL.md §6.

## Contacts — IC / OR / FP

| field | value | rule |
|---|---|---|
| `identity_code` | IC-25 | single-source identity (no cross-source merge) |
| | IC-40 | exactly 2 contributing source systems merged |
| | IC-70 | 3+ contributing source systems merged (clean cluster) |
| | IC-90 | contested / conflicting identity (shared identifier across distinct people) |
| `outreach_code` | OR-80 | consent_status = GRANTED |
| | OR-60 | consent_status = PENDING |
| | OR-35 | consent_status = DENIED |
| | OR-15 | consent_status = UNKNOWN |
| `field_provenance_code` | FP-75 | authoritative source + verified_flag=1 |
| | FP-55 | ≥2 contributing source systems |
| | FP-20 | single unverified source |

## Fuel & freight — RB / SB / LD

| field | value | rule |
|---|---|---|
| reference policy | RB-83 | alias ACTIVE and effective as-of cutoff |
| | RB-42 | alias ACTIVE but not-yet-effective-as-of-cutoff, OR PROVISIONAL |
| | RB-17 | alias INACTIVE / expired / no match |
| source basis | SB-79 | retained occurrence is from the CERTIFIED/authoritative snapshot |
| | SB-24 | retained occurrence is from a PROVISIONAL snapshot |
| ledger disposition | LD-14 | quarantined (unrecognized/ambiguous alias OR invalid physical measure) |
| | LD-31 | non-USD currency (FX routing) |
| | LD-53 | record_status = REVIEW |
| | LD-72 | recognized but class-mismatch (valid) |
| | LD-88 | clean POSTED/BILLED USD record |

Precedence for LD when multiple apply: quarantined (LD-14) > class-mismatch (LD-72)
> REVIEW (LD-53) > non-USD (LD-31) > clean (LD-88).

## Maintenance — MS / HR

| field | value | rule |
|---|---|---|
| `maintenance_source_code` | MS-86 | retained from authoritative snapshot |
| | MS-47 | retained from provisional snapshot |
| | MS-12 | (reserved) third / legacy source when present |
| `history_route_code` | HR-19 | rejected / invalid event (missing/unparseable time, bad odometer/labor) |
| | HR-33 | regression event (odometer went backward vs prior reliable reading) |
| | HR-74 | clean, properly-sequenced event |

Reminder: a regression-only event is NOT an `invalid_event_id` — it stays in the
sequenced history and routes to HR-33, not HR-19. See SKILL.md §5 Maintenance.
