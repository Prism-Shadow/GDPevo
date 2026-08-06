# PHO Geography Reference

## Census divisions (9 divisions, 4 regions)

### Northeast
- **New England:** CT, ME, MA, NH, RI, VT
- **Middle Atlantic:** NJ, NY, PA

### Midwest
- **East North Central:** IL, IN, MI, OH, WI
- **West North Central:** IA, KS, MN, MO, NE, ND, SD

### South
- **South Atlantic:** DE, DC, FL, GA, MD, NC, SC, VA, WV
- **East South Central:** AL, KY, MS, TN
- **West South Central:** AR, LA, OK, TX

### West
- **Mountain:** AZ, CO, ID, MT, NV, NM, UT, WY
- **Pacific:** AK, CA, HI, OR, WA

## State codes (51 jurisdictions: 50 states + DC)

Ordered alphabetically by two-letter code: AK, AL, AR, AZ, CA, CO, CT, DC, DE, FL, GA, HI, IA, ID, IL, IN, KS, KY, LA, MA, MD, ME, MI, MN, MO, MS, MT, NC, ND, NE, NH, NJ, NM, NV, NY, OH, OK, OR, PA, RI, SC, SD, TN, TX, UT, VA, VT, WA, WI, WV, WY

Note: DC (`is_state=0`) is included in all state-level analyses. Its census division is South Atlantic.

## Common dataset field mappings

| Concept | state_health | state_socioeconomic | county_health | county_socioeconomic | country_indicators |
|---------|-------------|--------------------|---------------|---------------------|-------------------|
| Entity ID | state_abbr | state_abbr | county_fips + state_abbr | county_fips + state_abbr | iso3 |
| Year | year | year | year | year | year |
| Measure | measure_id | — | measure_id | — | indicator_id |
| Value | value | poverty, bachelors, etc. | value | poverty, median_income, etc. | value |
| Precision | standard_error | — | low_ci, high_ci | — | unit |
| Quality | quality_flag, suppression_flag | quality_flag | quality_flag | quality_flag | quality_flag |
| Publication | release_status, revision, released_at | release_status, revision, released_at | release_status, revision, released_at | release_status, revision, released_at | release_status, revision, released_at |
| Geography | state_fips | state_fips | region | region | country_label |
| Sample | sample_size | population | population | population | — |

## Census division order (standard)

When the portal returns divisions in a registered order, it is typically:
East North Central, East South Central, Middle Atlantic, Mountain, New England, Pacific, South Atlantic, West North Central, West South Central
