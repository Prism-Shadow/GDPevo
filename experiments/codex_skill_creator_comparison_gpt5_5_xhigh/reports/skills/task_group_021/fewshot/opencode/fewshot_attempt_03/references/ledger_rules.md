# Fuel and Freight Ledger Rules

Use these rules for fuel-purchase, charging, freight-charge, and accrual-close tasks.

## Retained Logical Rows

Group raw rows by the stable logical id:

- fuel: `transaction_id`
- freight: `charge_id`

Retain one row per logical id using the shared snapshot precedence from `SKILL.md`. Keep all rows for raw counts and duplicate-group reporting. Normalized totals, mismatch ids, rankings, and decision panels should use retained logical rows unless the template explicitly asks for raw occurrences.

## Alias Recognition

Load `/api/reference/aliases?domain=fuel` or `domain=freight`.

For class/category recognition, use aliases that are:

- `reference_status == "ACTIVE"`
- effective for the transaction or service business date: `valid_from <= date <= valid_to` when `valid_to` exists
- published by the relevant cutoff when the task specifies cutoff evidence

Ignore inactive, future-effective, expired, and provisional aliases for recognition. They still matter for reference decision panels.

Normalize descriptions and aliases with Unicode NFKC and lowercase. Match aliases as phrase tokens, not arbitrary substrings inside longer words. If multiple aliases match but they all map to the same canonical value, the row has one recognized class/category. If matches map to more than one canonical value, it is ambiguous. If no alias matches, it is unrecognized.

## Quarantine and Mismatch

Fuel:

- invalid quantity: missing, nonnumeric, or `quantity <= 0`
- unresolved category: zero recognized fuel categories or ambiguous categories
- valid mismatch: quantity is valid and exactly one recognized fuel type differs from `expected_fuel_type`

Freight:

- invalid weight: missing, nonnumeric, or `billed_weight <= 0`
- invalid distance: missing, nonnumeric, or `distance <= 0`
- unresolved class: zero recognized service classes or ambiguous classes
- valid mismatch: physical measures are valid and exactly one recognized service class differs from `expected_service_class`

Quarantined logical rows do not enter normalized physical or spend totals. Valid mismatches do enter normalized totals under the recognized class/category.

Exception counts are distinct logical ids that are either valid mismatches or quarantined. Merchant/carrier exception rankings are grouped on retained logical rows and sorted exactly as the case scope or template says.

## Normalization

Use `/api/reference/conversions` by kind:

- fuel volume: convert to the case-scope canonical volume unit, usually liters
- freight weight: convert to the canonical weight unit
- freight distance: convert to the canonical distance unit

Use the conversion row effective for the transaction/service date. Multiply by `factor` from source unit to canonical unit. If the source unit is already canonical, still use the reference row when present.

Use `/api/reference/fx` for spend normalization. Pick the certified rate for the transaction/service date and currency; do not assume USD has a 1.0 rate. If certified is absent, use the best available rate allowed by the task and note the fallback in your working notes, not in the final JSON unless requested. Compute USD as `amount * usd_per_unit`.

Round only final answer fields to the precision in the template, commonly two decimals. Sum unrounded converted values internally.

## Common Output Lists and Totals

- Mismatch id arrays include valid expected-vs-recognized mismatches only, sorted lexicographically.
- Unrecognized/unresolved id arrays include zero-match and ambiguous classifications when the template says "cannot be assigned to exactly one" recognized category/class.
- Quarantine id arrays include unresolved aliases and invalid physical measures, sorted lexicographically.
- Per-class totals include exactly the enum values required by the template, sorted by canonical class/category unless another ordering is stated.
- Carrier exposure rankings for freight use normalized USD from valid mismatches only when the case scope defines accrual exposure that way; quarantine counts still contribute to exception counts.

Use `references/codes.md` for reference, source-retention, and ledger decision panels.
