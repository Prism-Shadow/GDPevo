---
name: fleet-data-quality-reconciliation
description: Reconcile Asteria-style fleet data-quality hub collections into schema-valid audit JSON. Use when a task provides a prompt, case scope, answer contract/template, and read-only hub access for contact rosters, fuel or freight ledgers, maintenance histories, duplicate resolution, source-snapshot reconciliation, alias classification, unit/FX normalization, readiness counts, quarantine sets, ranked exception panels, or compact internal control-code panels.
---

# Fleet Data Quality Reconciliation

## Core Workflow

1. Read the prompt, case scope, and answer contract before querying data. Extract the collection ID, cutoff, business period, scoped stable IDs, required sort orders, numeric precision, allowed enum values, and whether totals include or exclude exceptions.
2. Inspect catalog/schema and source snapshots for the scoped collection. Treat snapshot business cutoffs and statuses as source-selection evidence; do not filter source rows by ingestion time unless the task explicitly says to.
3. Pull all in-scope rows through the read-only data interface. Use structured queries over paginated endpoint sampling when the collection may exceed one page.
4. Build a reproducible reconciliation table with raw rows, retained logical records, normalized fields, exception flags, and reason flags. Derive every output field from that table.
5. Validate the final object against the answer contract: exact top-level keys, no extra commentary, sorted arrays, unique IDs, integer counts, required enums, and stated rounding.

## Source Resolution

- Prefer certified snapshots over provisional snapshots when the same stable public ID appears more than once. Keep provisional-only logical records unless the prompt says to certify only an authoritative snapshot.
- Count `raw_row_count` from in-scope raw rows, `logical_*_count` from retained stable IDs, and duplicate raw count as raw rows minus retained logical records when duplicates are defined by the stable ID.
- For duplicate-group outputs, include every stable ID with multiple raw occurrences, sorted by the public ID. Report all contributing snapshot IDs sorted lexicographically and the retained snapshot.
- Use business dates for applicability: transaction purchase/service dates for alias and FX rows, event times for maintenance history, and the case cutoff for source scope.

## Alias Classification

Use reference aliases as dated policy evidence, not simple string contains.

- Apply aliases only when their validity window covers the business date and their status is acceptable for classification. Future-dated aliases do not classify earlier records.
- Match aliases case-insensitively with token boundaries. Sort matches longest-first and ignore shorter matches that overlap an already matched longer phrase, so generic aliases do not make specific phrases ambiguous.
- Collapse multiple matched aliases to unique canonical classes.
- Zero matched classes means unrecognized. More than one canonical class means ambiguous. Both are quarantine conditions when the task requires a unique class.
- A recognized class that differs from the expected class is a valid mismatch unless the row also has a quarantine condition. When the prompt says valid mismatches enter totals, include them in normalized totals under the recognized class.

## Normalization

- Use reference unit conversions for the requested canonical units. Keep IDs as strings even when they contain digits.
- Use certified FX rows for the business date and currency unless the prompt specifies another rate basis. Round only at the final output precision, not during intermediate aggregation.
- Quarantine rows with nonpositive physical measures when the contract names those measures as invalid. Keep separate reason counts when requested; reason counts should follow the contract wording, not assume they must sum to quarantine count.
- Rank exception entities only after applying the task's inclusion rule. For mismatch exposure rankings, use valid mismatch spend and then the stated tie-breakers.

## Contacts

- Normalize email as Unicode NFKC, trimmed, lowercase. Treat blank strings and placeholders such as `N/A`, `none`, and `NULL` as no usable email.
- Normalize phone to digits only. When multiple source systems show the same local phone with extra country or formatting artifacts, prefer the canonical local digits supported by the corroborating sources.
- Merge strong duplicate contact clusters when normalized email or corroborated phone/name evidence identifies the same person. Do not automatically merge rows just because they share a known shared service phone or noisy identifier hint.
- Preserve no-contact rows for quarantine/reporting. Merge no-contact rows only when the task or watchlist evidence clearly asks for identity treatment of those rows.
- A dispatch-ready or channel-ready person must be active, have at least one usable canonical email or phone, and have granted consent. Active usable non-granted records are consent-blocked; inactive usable records are inactive-blocked; no usable channel is no-contact-blocked.
- For field-level canonical contacts, select each field independently using source reliability, verification, recency, and value quality. Use the source system that actually supplied the selected value in provenance fields.

## Maintenance Histories

- Reconstruct logical events across snapshots before computing history metrics. Prefer certified duplicate occurrences, and include provisional-only logical events unless excluded by the prompt.
- Reject events with missing or unparsable timestamps, event times outside the declared business period, invalid odometer values, negative labor, or extreme labor when the contract defines those as invalid ranges.
- Report odometer regressions as sequence findings after invalid event removal. Sequence-only regressions are not the same as invalid event rejection unless the contract says so.
- Compute corrected distance as the sum, per asset, of the last reliable odometer reading minus the first reliable odometer reading in the reconstructed period, using the requested odometer unit conversion.
- Build risk rankings from rejected event counts and regression event counts using the case-scope sort policy.

## Compact Codes

- Treat compact policy/source/routing/control codes as output labels inferred from the scoped evidence and allowed enum families. Do not assume numeric order implies severity.
- Map codes by comparing each scoped decision row to its reconciled condition: source basis, retained duplicate status, reference policy status, clean inclusion, valid mismatch, quarantine reason, no-contact, non-granted consent, inactive exclusion, strong identity, contested identity, or field provenance.
- Apply the same inferred mapping consistently within the task, and use only enum values allowed by the answer contract.

## Final Checks

- Recompute partition sums: depot/readiness partitions, valid plus quarantine relationships, exception unions, and ranked totals.
- Sort stable-ID arrays exactly as specified, usually lexicographically ascending. Add rank numbers only after final sorting.
- Ensure final JSON contains no Markdown, comments, candidate notes, query logs, or task-local training values.
