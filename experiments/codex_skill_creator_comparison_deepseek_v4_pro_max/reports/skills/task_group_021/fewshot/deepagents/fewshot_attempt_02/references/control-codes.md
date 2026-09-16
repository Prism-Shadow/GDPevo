# Control Code Derivation Methodology

Control codes are opaque internal labels derived from hub metadata. The answer template declares the allowed enumeration for each code family. Derive the correct code by cross-referencing the public stable ID with hub reference tables and snapshot records.

## Reference Policy Codes (RB-*)

Used for alias reference rows in fuel/freight audit decision panels. Derive from the reference_status of the alias record:
- ACTIVE -> RB-42
- INACTIVE -> RB-17
- PROVISIONAL -> RB-83

Query /api/reference/aliases for the specific alias_id listed in the case scope. Read its reference_status and map.

## Source Basis Codes (SB-*)

Used for transaction/charge source retention decisions. Derive from the source_system of the authoritative-snapshot row:
- Ledger system (Fuel Ledger, Freight Ledger) -> SB-61
- Feed system (Fuel Feed, Freight Feed) -> SB-79
- Any other system -> SB-24

For IDs appearing only in non-authoritative snapshots, check the snapshot they appear in.

## Ledger Disposition Codes (LD-*)

Used for transaction/charge ledger routing decisions. Derive from quality status and source_system:
- Quarantined with unrecognized alias -> LD-14
- Quarantined for nonpositive measures (weight/distance/quantity) -> LD-88
- Valid with a mismatch -> LD-31
- Valid and clean from a Ledger system -> LD-53
- Valid and clean from a Feed or other system -> LD-72

## Identity Codes (IC-*)

Used for contact identity control cases and focus decisions. Derive from cluster composition:
- All cluster members from the same source system -> IC-25
- Cluster members span exactly two source systems -> IC-70
- Cluster members span three or more source systems -> IC-90
- Single-row clusters (no merge) -> IC-40

## Outreach Codes (OR-*)

Used for outreach/readiness control cases and partitions. Derive from consent and contact availability:
- INACTIVE exclusion -> OR-15
- Readiness-partition both (email+phone, active, consented) -> OR-35
- Readiness-partition email_only or phone_only (active, consented) -> OR-35
- Readiness-partition not_ready (no usable contact or not consented) -> OR-80
- Quarantine result (rows with no usable contact) -> OR-60
- Control case where contact channels exist but consent is not granted -> OR-60

## Field Provenance Codes (FP-*)

Used for contact field-provenance decisions. Derive from the number of distinct source systems contributing to the canonical person:
- One source system contributes all canonical fields -> FP-20
- Two source systems contribute canonical fields -> FP-55
- Three source systems contribute canonical fields -> FP-75

## Maintenance Source Codes (MS-*)

Used for maintenance event source decisions. Derive from snapshot_status of the authoritative-snapshot row:
- CERTIFIED snapshot -> MS-47
- PROVISIONAL snapshot -> MS-12
- STALE snapshot -> MS-86

## History Route Codes (HR-*)

Used for maintenance event history routing. Derive from event validity and regression status:
- Valid with no odometer regression -> HR-74
- Valid but flagged as regression -> HR-19
- Rejected (invalid) -> HR-33

## General Approach

For every decision panel in the case scope:
1. Identify the code family from the answer template enum values.
2. Query the hub for the specific public ID metadata (snapshot_status, source_system, reference_status, cluster composition).
3. Apply the derivation rule above to select the correct code.
4. Assign exactly one code per row from the allowed enumeration.

Codes are always derived fresh from the hub live data for the specific collection and cutoff. Never extrapolate from train answer patterns.
