# Conflict Resolution Rules

When local payload data (finance queue, worksheet, scratchpad, draft) contradicts the Court Operations Portal or hearing notes, resolve using these rules.

## Authority Hierarchy (highest to lowest)

1. **Signed court order** — the final signed sentencing order is the authoritative source.
2. **Hearing notes / bench sheet** — courtroom transcription overrides draft or queue values.
3. **Audit/corroboration memo** — explicitly identifies which values are wrong and why.
4. **Court Operations Portal (CMS)** — authoritative for identity (DOB, name spelling) and case status.
5. **Current fee schedule** — governs fee amounts; stale/archived schedules are never used.
6. **Payment policy** — governs installment rules, account fee applicability, restitution priority.
7. **Form metadata** — governs placeholder text, required fields, and account references.

Local intake sheets, finance queue extracts, and draft worksheets are **not authoritative**. They are starting points that must be verified and corrected.

## Specific Conflict Resolution Patterns

### Identity Conflicts (DOB, Name)
- **Rule**: Use the CMS/portal value for DOB and name.
- **Example**: Queue says DOB 1991-04-19, portal says 1991-04-18 → use portal value.
- **Example**: Queue has "Evan Simons", portal has "Evan Simmons" → use portal spelling.
- **Exception**: If DOB is null in both portal and bench card, use placeholder `TBD from case file`. Never borrow a DOB from a similarly-named defendant.

### Counsel Classification Conflicts
- **Rule**: Hearing notes and judge clarification override intake abbreviations.
- **"PD" label**: Does NOT always mean public defender. Check if hearing notes or CMS confirm `appointed_private` counsel.
- **"APD" label**: Usually means appointed private, not assistant public defender. Verify with hearing notes.
- **Impact on fees**: PD user fee applies only when `counsel_type` = `public_defender`. Appointed-private or retained counsel → exclude PD user fee.

### Fee Schedule Conflicts
- **Rule**: Always use the current (non-archived) fee schedule entry.
- **Archived amounts**: Fee entries with `end_date` before the disposition date are stale. The queue often carries these forward.
- **Missing fee lines**: The queue may omit required fees (e.g., PD user fee, drug assessment). Add them per the current schedule.
- **Extraneous fee lines**: The queue may include fees that don't apply (e.g., PD user fee for appointed-private counsel). Remove them.

### Disposition/Status Conflicts
- **Rule**: The signed order determines final status.
- **No signed order**: Case is deferred or pending. Do NOT enter disposition or post financials. Hold all entries.
- **CMS contradiction**: CMS may show a different disposition than hearing notes. Hearing notes override for the closeout packet, but flag the conflict.

### Departure Conflicts
- **Rule**: Only enter a departure when the judge explicitly made a departure finding.
- **Draft worksheet language**: Ignore departure language from draft worksheets. The judge's on-record statement controls.
- **"Top of range"**: When the judge says "top of the range, no separate departure," → `no_departure` / `none`.

### Amended Charge Conflicts
- **Rule**: The conviction count is the AMENDED count, not the original.
- **Original count**: Marked `nolle_prosequi` or `dismissed` in CMS. Any assessment tied to the original offense code (e.g., drug lab fee for a CS count) does NOT apply to the amended count (e.g., misdemeanor theft).
- **Audit flag**: Use `amended_non_lab_conviction` or similar to indicate the worksheet still shows the old count's fees.
