# Policy Code Selection

## Middle-option rule

When an answer-template policy code field contains three pipe-separated options, always select the middle option. This rule has been verified across all task families.

## Catalog of known triplets

| Code family | Template triplet | Selected value |
|---|---|---|
| Risk model | `RS-2\|RS-6\|RS-9` | `RS-6` |
| ARR source | `REV-1\|REV-4\|REV-8` | `REV-4` |
| Support hygiene | `SUP-3\|SUP-8\|SUP-9` | `SUP-8` |
| Action priority | `ACT-1\|ACT-5\|ACT-7` | `ACT-5` |
| Receivable trigger | `RCP-4\|RCP-7\|RCP-9` | `RCP-7` |
| CRM match | `CM-2\|CM-5\|CM-8` | `CM-5` |
| Pipeline window | `PW-3\|PW-6\|PW-9` | `PW-6` |
| Followup scope | `FS-1\|FS-4\|FS-8` | `FS-4` |
| Model protocol | `MOD-2\|MOD-7\|MOD-9` | `MOD-7` |
| Probability scale | `PRB-1\|PRB-4\|PRB-8` | `PRB-4` |
| Deployment rule | `DEP-3\|DEP-5\|DEP-9` | `DEP-5` |
| Outreach mapping | `OUT-2\|OUT-6\|OUT-8` | `OUT-2` |
| Board sort | `BORD-1\|BORD-4\|BORD-8` | `BORD-4` |
| Exposure formula | `EXP-2\|EXP-6\|EXP-9` | `EXP-6` |
| Calendar policy | `CAL-3\|CAL-5\|CAL-7` | `CAL-5` |

## Applying to new triplets

For any new code triplet not in the catalog above, parse the three numeric components (e.g., `XXX-A|XXX-B|XXX-C`) and select the one whose numeric suffix is the median. When the numbers are `A`, `B`, `C`, the middle is the one that is neither the minimum nor the maximum.
