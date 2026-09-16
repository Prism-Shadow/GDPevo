# Control Code Families

Every audit task assigns internal control codes from enumerated sets. Different tasks use different family subsets. Each family has consistent internal logic: codes ending in specific digits map to specific data conditions.

## Code Families

### Reference-Basis Codes (RB-xx)
Used for reference-alias decisions. Values: RB-17, RB-42, RB-83. Assign based on whether the alias description maps cleanly to exactly one recognized category, maps ambiguously to multiple categories, or has no recognized mapping.

- **RB-42**: Alias maps to exactly one recognized category (clean mapping).
- **RB-17**: Alias maps to multiple recognized categories (ambiguous mapping).
- **RB-83**: Alias has no recognized mapping (unrecognized).

### Source-Basis Codes (SB-xx)
Used for source-retention decisions on individual transactions/charges. Values: SB-24, SB-61, SB-79. Assign based on the source snapshot and duplication pattern:

- **SB-24**: Charge/transaction appears only in the authoritative CERTIFIED snapshot, no duplicate.
- **SB-61**: Charge/transaction appears in both CERTIFIED and PROVISIONAL; the CERTIFIED copy is retained.
- **SB-79**: Charge/transaction appears only in PROVISIONAL (non-CERTIFIED only).

### Ledger-Disposition Codes (LD-xx)
Used for ledger-routing decisions. Values: LD-14, LD-31, LD-53, LD-72, LD-88. Assign based on the record's classification:

- **LD-14**: Quarantined record - unrecognized category/description (zero-match).
- **LD-31**: Valid record with expected-vs-actual category mismatch.
- **LD-53**: Valid record, no mismatch, single-snapshot (appears only in one snapshot, no duplicate).
- **LD-72**: Valid record, no mismatch, appears in both snapshots (deduplicated, retained from CERTIFIED).
- **LD-88**: Quarantined record - ambiguous description (multi-match, cannot resolve to one category).

### Identity Codes (IC-xx)
Used for partner/people identity decisions. Values: IC-25, IC-40, IC-70, IC-90. Assign based on evidence pattern:

- **IC-25**: Single-source identity - person appears in only one source system, no ambiguity.
- **IC-40**: Quarantined identity - person has no usable contact channel (quarantine row).
- **IC-70**: Multi-source merge - person appears in multiple source systems and is merged via field-level precedence.
- **IC-90**: Contested identity - identifier conflict across sources that prevents automerge.

### Outreach Codes (OR-xx)
Used for contact-readiness and outreach decisions. Values: OR-15, OR-35, OR-60, OR-80. Assign based on status:

- **OR-15**: Inactive exclusion - person is INACTIVE, excluded from outreach.
- **OR-35**: Ready/eligible - person is active with usable contact channels and GRANTED consent.
- **OR-60**: Quarantined/no-contact - person has no usable email or phone.
- **OR-80**: Not-ready - person is active with usable channels but consent is not GRANTED.

### Field-Provenance Codes (FP-xx)
Used for field-provenance decisions. Values: FP-20, FP-55, FP-75. Assign based on source system mix:

- **FP-20**: Single-source provenance - all fields for this entity come from one source system.
- **FP-55**: Mixed provenance - fields from multiple source systems, resolved with field-level precedence.
- **FP-75**: Quarantine provenance - entity is quarantined, fields come from the quarantine source.

### Maintenance-Source Codes (MS-xx)
Used for maintenance event source decisions. Values: MS-12, MS-47, MS-86. Assign based on snapshot provenance and event validity:

- **MS-12**: Event from PROVISIONAL snapshot only (non-CERTIFIED source).
- **MS-47**: Event from CERTIFIED snapshot, valid (no issues detected).
- **MS-86**: Event from CERTIFIED snapshot but flagged as invalid.

### History-Route Codes (HR-xx)
Used for maintenance history routing. Values: HR-19, HR-33, HR-74. Assign based on event disposition:

- **HR-19**: Rejected event - invalid and excluded from history.
- **HR-33**: Duplicate event - appears in both snapshots, retained from CERTIFIED.
- **HR-74**: Valid event - included in history with no issues.

## Assignment Method

When the task provides scoped IDs but no code mapping, infer codes by:
1. Looking up each scoped ID's full record in the API data.
2. Comparing the record's field values, snapshot provenance, and classification against the patterns above.
3. Grouping similar IDs - IDs with matching characteristics get the same code.

Control codes are deterministic: the same evidence always produces the same code. Do not randomize.
