# Control Code Mapping

These opaque control codes appear across Asteria Fleet DQ Hub tasks. The codes
are inferred from record properties, not chosen arbitrarily. Each code set is
always enumerated in the answer template schema — use the schema's `enum`
constraint as your allowed palette.

## Contact / Onboarding domain

### Identity codes (IC-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| IC-25 | Single-source consensus | The evidence cluster for an anchored control case has rows from exactly one source system, or the focus cluster survivor row is the only row from that source in the cluster. |
| IC-40 | Multi-source with quarantine overlay | The record or cluster contains at least one quarantined row. Quarantine-result identity code. |
| IC-70 | Multi-source merge, no quarantine | The focus cluster has rows from more than one source system and no quarantined rows. Survivor row is from the highest-precedence source. |
| IC-90 | Multi-source with orphan or quarantined | The anchored control cluster includes at least one quarantined row or a row without a merge partner. |

### Outreach codes (OR-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| OR-15 | Inactive exclusion | The person has `record_status` INACTIVE. Assign to `inactive_exclusion`. |
| OR-35 | Channel ready | The person is active and has at least one usable channel (email or phone). Assign to readiness-partition entries for `both`, `email_only`, and `phone_only`. |
| OR-60 | Quarantine (no usable contact) | The row has neither a usable email nor a usable phone. Assign to `quarantine_result`. |
| OR-80 | Not ready | The person lacks any usable channel. Assign to `not_ready` readiness partition. Also assign to anchored cases where evidence contains quarantined rows. |

### Field-provenance codes (FP-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| FP-20 | Single source, clean | The evidence rows all come from one source system. Anchored-case default for single-source clusters. |
| FP-55 | Multi-source merge | The focus cluster has rows from multiple source systems and the survivor is chosen by field-level precedence. Assign to all focus-cluster decisions. |
| FP-75 | Quarantine / no usable source | At least one row in the evidence set has no usable contact fields. Assign to `quarantine_result`. |

## Fuel domain

### Reference-policy codes (RB-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| RB-17 | Unrecognized or ambiguous description | The reference alias's description maps to zero canonical categories (unrecognized) or more than one (ambiguous). |
| RB-42 | Clean single-category match | The reference alias's description unambiguously maps to exactly one recognized fuel category. |
| RB-83 | Category-spanning alias | The alias can match descriptions from multiple fuel categories. |

### Source-basis codes (SB-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| SB-24 | Provisional-only or unrecognized record | The transaction appears only in a provisional snapshot, or its description is unrecognized. |
| SB-61 | Certified record, no mismatch | The transaction is in the certified snapshot and its expected category matches its recognized category. |
| SB-79 | Certified record, mismatch or unrecognized | The transaction is in the certified snapshot but has an expected-vs-actual mismatch OR its description is unrecognized. |

### Ledger-disposition codes (LD-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| LD-14 | Quarantine — unrecognized/ambiguous | The transaction's description is unrecognized or ambiguous. Excluded from ledger totals. |
| LD-31 | Certified, category mismatch | The transaction is valid but has an expected-vs-actual category mismatch. Flagged for review but included in totals. |
| LD-53 | Invalid quantity or clean single-match | The transaction has an invalid (non-positive) quantity OR is a clean single-match valid record from a single source. |
| LD-72 | Certified clean match, multi-source survivor | The transaction survived deduplication across certified and provisional snapshots (in the certified snapshot). Clean match. |
| LD-88 | Provisional record or ambiguous alias | The transaction comes from a provisional record that was not retained after dedup, or the description is ambiguous. Excluded from totals. |

## Maintenance domain

### Maintenance-source codes (MS-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| MS-12 | Clean certified, no issues | Event is in the certified snapshot, valid timestamp and odometer, no regression, no rejection. |
| MS-47 | Certified, duplicate-survivor | Event was present in both snapshots and the certified row was retained. |
| MS-86 | Provisional-origin with issues | Event originated from provisional data, or the event has timestamp/odometer/labor issues but was not outright rejected. |

### History-route codes (HR-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| HR-19 | Regression or rejected | Event contributed to odometer regression for its asset, or was rejected for invalid data. |
| HR-33 | Clean certified, no regression | Event is valid, in certified snapshot, and its asset has no odometer regression. |
| HR-74 | Certified, regression elsewhere on asset | Event is valid and in certified snapshot, but another event on the same asset caused a regression. |

## Freight domain

### Reference-policy codes (RB-*)

Same as fuel domain: RB-17 for unrecognized/ambiguous aliases, RB-42 for clean
single-category matches, RB-83 for category-spanning aliases.

### Source-retention codes (SB-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| SB-24 | Provisional-only or unrecognized alias | Charge appears only in provisional snapshot, or its alias is unrecognized. |
| SB-61 | Certified duplicate survivor, clean match | Charge survived dedup (was in both snapshots, certified retained) and has no class mismatch. |
| SB-79 | Certified, mismatch or quarantine | Charge in certified snapshot with expected-vs-actual class mismatch, or the charge is quarantined for invalid measures. |

### Ledger-routing codes (LD-*)

| Code | Meaning | When to assign |
|------|---------|----------------|
| LD-14 | Quarantine for invalid measures | Charge has non-positive weight or non-positive distance. Excluded from accrual totals. |
| LD-31 | Valid class mismatch | Charge is valid but expected service class differs from recognized class. Included in totals, flagged for review. |
| LD-53 | Quarantine for alias issues, or clean single-instance | Charge has unrecognized or ambiguous alias, OR charge is valid with clean class match and only one raw occurrence. |
| LD-72 | Certified clean match, duplicate survivor | Charge survived dedup with certified retained, clean class match. Included in totals. |
| LD-88 | Ambiguous alias or provisional duplicate | Charge description maps to multiple service classes (ambiguous), or charge's provisional row was discarded during dedup. Excluded from totals. |

## Field-service domain

Same control code families as Contact/Onboarding domain (IC-*, OR-*, FP-*),
with control families explicitly labeled in the case scope (IDENTITY, OUTREACH,
FIELD_PROVENANCE). Map evidence rows to codes following the same logic:
source-system counts, quarantine presence, and active/inactive status drive the
assignments.
