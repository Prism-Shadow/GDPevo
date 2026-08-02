# Pre-submission checklist

Work top to bottom before writing `answer.json`.

## Inputs understood
- [ ] Read the request payload AND the answer_template fully.
- [ ] Listed every required output key with its type, enum, pattern, array bounds,
      ordering, and precision.
- [ ] Identified whether this is read-only analytics or a correction task.

## Schema grounded
- [ ] Pulled `/api/schema` and `/api/data-dictionary`; mapped each business concept to a
      real table/column. No guessed names.
- [ ] Found the production/eligibility flag and the raw-vs-canonical column pair(s).

## Population
- [ ] Applied every scope filter (tier, segment, region, warehouse, campaign, batch,
      priority, production).
- [ ] Applied window/membership as of the cutoff with correct inclusivity (exact UTC).
- [ ] Eligible/base count is exact — every rate depends on it.

## Metrics
- [ ] Counted at the correct grain (distinct orders / logical refunds / reversals /
      shipments / tasks / cases).
- [ ] Used the request's stated denominator; kept non-qualifying members in it when told to.
- [ ] FX: per-row daily rate for that row's service_date & currency; net subtracts reversals.
- [ ] Medians: even count averages the two central values.
- [ ] Rounded ONLY final reported values; comparisons/sorts/thresholds use unrounded values.

## Ordering
- [ ] Every ranked/list output sorted by primary → secondary → id/label ascending, then
      sliced to the exact required size.
- [ ] Enum-valued IDs match the template pattern; arrays satisfy uniqueItems/min/max.

## Classification
- [ ] Walked status/risk rules top-down, first match wins, catch-all last.
- [ ] Honored exact operators (>=, >, <, strictly before) and compound AND conditions.

## Correction tasks only
- [ ] Correction found via the raw↔canonical contradiction; only ONE field on ONE row changed.
- [ ] Used `/api/sql/transaction`; raw/source and identity fields untouched.
- [ ] Audit constants copied verbatim from the request; old/new values reported as strings.
- [ ] Post-commit re-query confirmed the new canonical value and exactly 1 business + 1 audit row.
- [ ] Status = APPLIED only if the success rule fully holds; else NOT_APPLIED with observed values.

## Output
- [ ] `answer.json` = exactly the required keys, correct types, no extra keys, no commentary.
- [ ] Validated against the template. Nothing but the JSON object in the file.
