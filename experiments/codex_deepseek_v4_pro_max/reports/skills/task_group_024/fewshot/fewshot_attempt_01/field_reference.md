 # Work Item Field Reference

 Common fields returned by the work item endpoints and their meanings in portfolio analysis.

 ## Identity

 | Field | Description |
 |---|---|
 | `id` | Unique work item identifier, e.g. `WI-24024-P001` |
 | `title` | Human-readable title |

 ## Organization

 | Field | Description |
 |---|---|
 | `team` | Owning engineering team |
 | `owner` | Individual owner; empty/null means unassigned |
 | `product_area` | Product area (e.g. Atlas Backend, Checkout, Identity) |

 ## Classification

 | Field | Description |
 |---|---|
 | `category` | General category label |
 | `portfolio_category` | Authoritative portfolio category: `NewFeature`, `TechDebt`, `Reliability`, `Security` |
 | `severity` | SLA severity: `S1`, `S2`, `S3`, `S4` |

 ## Status and dates

 | Field | Description |
 |---|---|
 | `status` | Current status: `Closed`, `Cancelled`, `In Progress`, `Open`, etc. |
 | `closed_at` | ISO-8601 timestamp when the item was closed |
 | `sla_target_date` | ISO-8601 date by which the SLA should be met |
 | `created_at` | ISO-8601 timestamp of creation |

 ## Data quality

 | Field | Description |
 |---|---|
 | `duplicate_of` | If set, this item is a duplicate of the referenced primary ID. Exclude from primary counts. |
 | `mirror_of` | If set, this item mirrors another record. Exclude from primary counts; use the canonical record. |
 | `is_duplicate` | Boolean flag indicating a duplicate. Treat same as `duplicate_of` being non-null. |
 | `mirror_status` | Stale status from a mirrored record. Do not use for analysis. |
 | `legacy_category` | Deprecated category field. Do not use; prefer `portfolio_category`. |

 ## Release and milestone

 | Field | Description |
 |---|---|
 | `release_id` | Associated release identifier |
 | `milestone_id` | Associated milestone identifier |

 ## Category resolution rule

 When `portfolio_category` and `category` disagree (or only one is populated), prefer `portfolio_category`. When both are absent, use `title` pattern matching as a fallback: items mentioning "security", "vuln", "CVE" → Security; "reliability", "SLO", "resilience" → Reliability; "tech debt", "refactor" → TechDebt; otherwise → NewFeature.
