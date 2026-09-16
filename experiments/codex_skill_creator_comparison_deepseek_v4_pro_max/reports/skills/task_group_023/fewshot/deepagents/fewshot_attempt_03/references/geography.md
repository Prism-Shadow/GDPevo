# Geographic Reference Tables

Retrieve live geography tables from the portal at runtime; this reference documents known structures and values from the portal `/geographies/` endpoints.

## State Reference (51 entries)

Retrieve from `/download?dataset=states&format=csv`.
Columns: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`.
51 rows: 50 states plus DC (DC has is_state=0).

### Census Divisions by State

| Division | State Codes |
|----------|-------------|
| Pacific | AK, CA, HI, OR, WA |
| Mountain | AZ, CO, ID, MT, NM, NV, UT, WY |
| West North Central | IA, KS, MN, MO, ND, NE, SD |
| East North Central | IL, IN, MI, OH, WI |
| New England | CT, MA, ME, NH, RI, VT |
| Middle Atlantic | NJ, NY, PA |
| South Atlantic | DC, DE, FL, GA, MD, NC, SC, VA, WV |
| East South Central | AL, KY, MS, TN |
| West South Central | AR, LA, OK, TX |

Region mapping:
- West: Pacific, Mountain
- Midwest: West North Central, East North Central
- South: South Atlantic, East South Central, West South Central
- Northeast: New England, Middle Atlantic

### Canonical Division Order

When a protocol requires a fixed division order: East North Central, East South Central, Middle Atlantic, Mountain, New England, Pacific, South Atlantic, West North Central, West South Central.

State order follows the portal natural order (by FIPS) or an explicit `state_order` field in the protocol.

## County Reference

Retrieve from `/download?dataset=counties&format=csv`.
Columns: `state_fips`, `county_fips`, `state_abbr`, `county_name`, `rucc`.

### RUCC (Rural-Urban Continuum Code)

Integer 1 through 9.
- 1-3: Metropolitan counties
- 4-9: Nonmetropolitan counties

RUCC bands for stratification: [1,3], [4,6], [7,9].
County FIPS is a text field: 2-char state FIPS + 3-char county suffix. Leading zeros are meaningful.

## Country Reference (72 rows)

Retrieve from `/download?dataset=countries&format=csv`.
Columns: `iso3`, `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group`.

Regions: Africa, Americas, Asia, Europe, Middle East, Oceania.
Income groups: LOW, LOWER_MIDDLE, UPPER_MIDDLE, HIGH.

### Label Reconciliation

1. Exact match requested label against `portal_label` and each pipe-delimited `alternate_labels` value
2. Fallback: case-insensitive or substring match
3. Map each uniquely matched label to its `iso3`

Count:
- `resolved_label_count`: unique ISO3 codes matched
- `alias_resolution_count`: resolved labels where matched text differs from `canonical_name`
- `resolved_iso3`: sorted ascending list of ISO3 codes

### Known Label Patterns

The portal uses consistent naming: `Republic of X` (portal_label) vs `X Republic` (canonical), `X Republic`, `X Federation`, `X Isles`. All have ISO3 codes in the QAA-QBX range.
