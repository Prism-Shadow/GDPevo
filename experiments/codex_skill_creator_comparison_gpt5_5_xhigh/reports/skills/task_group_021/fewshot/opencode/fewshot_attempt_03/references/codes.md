# Compact Code Semantics

Only use a code when the current answer template allows it. The compact code panels are evidence classifications; populate them from the record condition, not from position in a requested list.

## Reference Policy Codes

- `RB-42`: reference alias row is active and effective for the relevant business date or cutoff.
- `RB-17`: reference alias row is inactive, expired, or not yet effective for the relevant business date or cutoff.
- `RB-83`: reference alias row is provisional, even if its dates overlap the period.

## Source Basis and Retention Codes

For fuel/freight transaction source panels:

- `SB-24`: retained logical row is a single certified-source occurrence.
- `SB-61`: retained logical row comes from a certified occurrence in a cross-snapshot duplicate group.
- `SB-79`: retained logical row is provisional because no certified occurrence exists for that logical id.

For maintenance source panels:

- `MS-12`: retained event is a single certified-source event.
- `MS-47`: retained event is the certified member of a cross-snapshot duplicate event.
- `MS-86`: retained event is provisional because no certified occurrence exists.

## Ledger and History Route Codes

For fuel/freight ledger disposition:

- `LD-72`: valid retained row with a uniquely recognized class/category and no expected-vs-actual mismatch.
- `LD-31`: valid retained row with a uniquely recognized class/category that differs from the expected class/category.
- `LD-14`: unresolved because no active/effective alias uniquely recognizes the description.
- `LD-88`: unresolved because the description matches aliases for more than one canonical class/category.
- `LD-53`: quarantined for invalid physical measure such as nonpositive fuel quantity, billed weight, or distance.

For maintenance history route:

- `HR-33`: retained event is accepted into corrected history.
- `HR-74`: retained event is rejected for missing/unparsable time, invalid odometer, or invalid labor.
- `HR-19`: retained event is a sequence-only odometer regression; report it in regression outputs, not invalid-id lists.

## Contact Control Codes

Identity:

- `IC-70`: rows are confidently merged into one canonical entity through strong shared identifiers and field-level precedence.
- `IC-25`: identifier evidence is contested, such as a shared helpdesk phone or shared master hint across different names/emails, so do not auto-merge.
- `IC-90`: evidence indicates separate people/entities despite weak similarities such as same name, location, or source pattern.
- `IC-40`: contact row/entity is quarantined because it lacks a usable identity/contact channel for outreach.

Outreach:

- `OR-35`: entity has a usable channel and consent is granted, so it is channel-ready or dispatchable.
- `OR-80`: active entity has a usable channel but is blocked by consent or other readiness policy.
- `OR-15`: entity is inactive and therefore excluded even if it has contact data.
- `OR-60`: entity has no usable email or phone channel.

Field provenance:

- `FP-55`: canonical fields are selected from multiple source rows by field-level source precedence.
- `FP-20`: source evidence is single-source or direct, without a field-precedence merge.
- `FP-75`: field result is quarantined or unusable because no reliable contact field can be retained.
