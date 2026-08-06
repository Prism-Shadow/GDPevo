# Source Resolution Hierarchy

When reconciling conflicting information across court record sources, resolve in this order of authority:

## Tier 1: Courtroom Record (Highest Authority)
- Hearing notes (what the judge pronounced in open court)
- Signed sentencing orders
- Judge's explicit statements on the record
- Minute entries from the hearing

## Tier 2: Official CMS / Case Management System
- Portal case records (`/api/cases`)
- Portal charge records (`/api/charges`)
- Official status and disposition dates
- Counsel type and attorney name as recorded in the CMS

## Tier 3: Corroborating Documents
- Clerk audit memos identifying known exceptions
- Supervisor notes flagging data-quality issues
- Defense cover memos confirming counsel appointments
- Bailiff notes on identity verification

## Tier 4: Financial Queue / Worksheets (Lowest Authority)
- Finance queue extracts (carry-forward values, draft amounts)
- Legacy charge screens (may have stale departure labels)
- Draft worksheets (may reflect pre-hearing assumptions)
- Intake cover sheets with non-final figures

## Fee Schedule Resolution
- **Current schedule** (effective on or before disposition date, no end date or end date after disposition) always beats **stale/archived schedule** (end date before disposition)
- Verify the `effective_date` and `end_date` fields in `/api/fee-schedules` responses
- A schedule with `end_date: null` is current; a schedule with a past `end_date` is stale

## Cross-Reference Rule
When a source at a higher tier is silent on a fact, fall through to the next tier. But when a lower-tier source conflicts with a higher-tier source on the SAME fact, the higher tier controls and the conflict becomes an audit finding.
