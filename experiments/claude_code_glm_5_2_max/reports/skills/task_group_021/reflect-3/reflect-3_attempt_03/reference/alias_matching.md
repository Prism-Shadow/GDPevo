# Alias Matching Algorithm

## Problem
Transaction descriptions must be classified into canonical categories using reference aliases. A single description may contain multiple alias substrings, and shorter aliases can be substrings of longer ones (e.g., "diesel" appears inside "bio diesel").

## Greedy Longest-Match Algorithm

1. **Filter aliases to valid period.** Only include aliases where:
   - `reference_status` = `ACTIVE`
   - `valid_from` ≤ cutoff_date
   - `valid_to` ≥ cutoff_date (treat NULL `valid_to` as unbounded)

2. **Sort aliases by text length descending.** Process longest aliases first so "bio diesel" is tried before "diesel".

3. **For each description:**
   - Convert to lowercase
   - For each alias (longest first), find first occurrence in description
   - If found and the matched region does not overlap with any previously consumed region, record the canonical value and mark the region as consumed
   - Continue until all aliases are checked

4. **Classify the result:**
   - 0 matches → **unrecognized** (quarantine)
   - 1 match → compare to `expected_fuel_type` / `expected_service_class`
     - Same → valid
     - Different → **mismatch** (still valid for totals)
   - >1 match → **ambiguous** (quarantine)

## Example

Description: "ULSD road diesel pump"
- Try "road diesel" (length 11) → found at index 5 → match DIESEL, consume [5:16]
- Try "bio diesel" (length 10) → not found
- Try "ulsd" (length 4) → found at index 0 but region [0:4] doesn't overlap consumed → match DIESEL, consume [0:4]
- Wait — both map to DIESEL, so unique match → DIESEL

Description: "diesel and unleaded mixed card entry"
- Try "bio diesel" → not found
- Try "unleaded" (length 8) → found → match UNLEADED
- Try "diesel" (length 6) → found in unconsumed region → match DIESEL
- 2 unique canonical values → **ambiguous**

## Why Not Simple Substring?

Simple substring matching (checking each alias independently) would mark "bio diesel" as matching both "bio diesel" → BIODIESEL and "diesel" → DIESEL, producing false ambiguity. Greedy longest-match consumes "bio diesel" first, preventing "diesel" from matching in the same region.
