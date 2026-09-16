# Output Conventions

Formatting rules that apply to all output JSON objects.

## Rounding

| Type | Decimal Places | Example |
|------|---------------|---------|
| Currency (USD) | 2 | 123456.78 |
| Percentage / ratio | 4 | 0.0138 |
| Growth rate | 4 | 0.0966 |
| Count | 0 | 26 |

Use Python round(value, N) for all rounding.

## List Ordering

Unless the answer template description specifies otherwise:
- Branch IDs: ascending string sort (BR-001, BR-002, ...)
- Pay types: order from the rate book pay_types array
- Per-musician arrays: ascending by musician_id
- Conflict flags: alphabetical sort

When a rank field is specified (e.g. ebitda_rank_desc), that field is an integer position, not a list order constraint.

## Key Presence

All required_top_level_keys from the answer template must be present in the output, even if their value is 0, 0.0, [], or null. Do not omit keys.

## Field Types

The field_types section of the answer template defines expected value types:
- string: A quoted string
- integer: A whole number
- currency: A number rounded to 2 decimals
- decimal percent: A number rounded to 4 decimals (already in decimal form, e.g. 0.0966 for 9.66%)
- enum: Must be exactly one of the listed string values
- list of X strings: A JSON array of strings
- object mapping X to Y: A JSON object with keys of type X and values of type Y
- sorted list: An array sorted as described

## JSON Output

Write a single JSON object. Do not include markdown fences, trailing commas, or comments. Use json.dumps(obj, indent=2) in Python for consistent formatting.

## Answer Template Adherence

The answer template defines the exact output structure. Key points:
- The template required_top_level_keys is the definitive list
- Follow nested key names exactly as shown in field_types
- The description field may contain additional rules (rounding or ordering) - always follow those

## Cross-Checking

Before finalizing verify:
- Every required top-level key is present
- All currency values rounded to 2 decimals
- All percentage/ratio values rounded to 4 decimals
- Lists follow the correct sort order
- Growth rates use the correct denominator (older period)
- EBITDA includes the allocations deduction
- ARPU uses active_customers, not revenue_units
