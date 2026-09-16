# Enum Reference

Allowed values that appear across answer templates and API responses. Always use these exact strings.

## Actions (trade_package / rotation)

| Value | Meaning |
|-------|---------|
| `BUY` | Purchase |
| `SELL` | Sell |
| `HOLD` | No change |
| `NO_TRADE` | No action |

## Sleeve actions

| Value | Meaning |
|-------|---------|
| `trim` | Reduce allocation |
| `add` | Increase allocation |
| `hold` | Maintain current |
| `hedge` | Add currency hedge |
| `monitor` | Watch only |
| `rotate` | Shift between sleeves |

## Views

| Value | Meaning |
|-------|---------|
| `UW` | Underweight |
| `N` | Neutral |
| `OW` | Overweight |

## View changes

| Value | Meaning |
|-------|---------|
| `UP` | Upgraded |
| `DOWN` | Downgraded |
| `UNCHANGED` | No change |

## Conviction

| Value | Meaning |
|-------|---------|
| `LOW` | Low conviction |
| `MEDIUM` | Medium conviction |
| `HIGH` | High conviction |

## Rationale codes

| Value | Associates with |
|-------|-----------------|
| `GROWTH_IMPROVES` | Growth/momentum positive |
| `RATE_CUT_SUPPORT` | Rate cutting cycle favorable |
| `CREDIT_SPREAD_RISK` | Spread widening risk |
| `DOLLAR_DEFENSIVE` | USD as defensive currency |
| `CHINA_DEPENDENCE` | China-linked headwinds |
| `LATAM_DIVERSIFIER` | Latin America diversification |
| `INDIA_OFFSET` | India as portfolio offset |
| `DURATION_SUPPORT` | Duration favorable |
| `HY_VALUATION_RISK` | High yield valuation stretched |
| `EUROPE_RECOVERY` | European recovery |
| `JAPAN_POLICY_RISK` | Japan policy uncertainty |
| `NEUTRAL_BALANCE` | No strong directional signal |

## Rating buckets

| Value |
|-------|
| `IG` |
| `HY` |

## Credit outlooks

| Value |
|-------|
| `stable` |
| `positive` |
| `negative` |

## Asset classes

| Value |
|-------|
| `Equities` |
| `Duration` |
| `Credit` |
| `Currency` |
| `Fixed Income` |
| `Equity` |

## Sales positioning (credit trade strategy)

### target_segment

| Value |
|-------|
| `insurance_general_account` |
| `pension_liability_matching` |
| `multi_asset_income` |
| `private_bank_income` |
| `endowment_opportunistic` |

### theme

| Value |
|-------|
| `lng_export_tailwind` |
| `oil_oversupply_caution` |
| `midstream_stability` |
| `transition_bond_selectivity` |
| `avoid_watchlist_yield_trap` |

## Concentration codes

| Value |
|-------|
| `CHINA_ASIA_DEPENDENCE` |
| `GLOBAL_DEVELOPED_OVERLAP` |
| `NO_MATERIAL_CONCENTRATION` |

## Diversification candidates

| Value |
|-------|
| `IDX_EM_EX_CHINA` |
| `IDX_INDIA` |
| `IDX_LATAM` |

## Overlay codes

| Value |
|-------|
| `DURATION_QUALITY_TILT` |
| `CREDIT_RISK_REDUCTION` |
| `EQUITY_BETA_EXTENSION` |
| `CURRENCY_DEFENSIVE_HEDGE` |
| `NO_OVERLAY` |

## Primary actions (risk overlay)

| Value |
|-------|
| `tilt_to_duration_quality` |
| `trim_credit_beta` |
| `add_cyclical_equity_beta` |
| `add_currency_hedge` |
| `hold_policy_weights` |

## Rebalance triggers

| Value |
|-------|
| `correlation_cap_breach` |
| `hy_cap_pressure` |
| `duration_drift` |
| `watchlist_concentration` |
| `committee_review` |

## Next steps

| Value |
|-------|
| `approve_rotation` |
| `defer_pending_risk_review` |
| `approve_with_monitoring` |
| `reject_constraint_breach` |

## Risk note codes

| Value |
|-------|
| `hy_cap_pressure` |
| `watchlist_concentration` |
| `duration_preservation` |
| `carry_tradeoff` |
| `no_action` |

## Data precedence

| Value |
|-------|
| `current_environment_over_stale_payload` |
| `local_payload_over_current_environment` |
| `no_conflict_found` |

## Pair roles

| Value |
|-------|
| `highest_concentration` |
| `best_diversifier` |

## Energy market direction labels

| Value |
|-------|
| `positive` |
| `negative` |
| `neutral_to_positive` |

## Energy market signal IDs

| Value |
|-------|
| `OIL_RANGE_BOUND` |
| `US_GAS_TIGHTENS` |
| `LNG_EXPORT_PULL` |
| `REFINING_VOLATILE` |
| `RENEWABLES_STABILIZE` |

## Energy pitch themes

| Value |
|-------|
| `LNG_EXPORT_GROWTH` |
| `MIDSTREAM_DEFENSIVE_CARRY` |
| `OIL_DISCIPLINE` |
| `RENEWABLES_RATE_RELIEF` |
| `AVOID_REFINING_WATCHLIST` |

## Bond recommended theme tags

| Value |
|-------|
| `OIL_DISCIPLINE` |
| `OIL_UPSIDE` |
| `DURATION_LONG` |
| `LNG_EXPORTS` |
| `GAS_DEMAND` |
| `LNG_DEMAND` |
| `HY_CARRY` |
| `MIDSTREAM_DEFENSIVE` |
| `MIDSTREAM_TOLLS` |
| `DELEVERAGING` |
| `HIGH_CARRY` |
| `WATCHLIST_RISK` |
| `REFINANCING_RISK` |
| `RENEWABLES` |
| `IG_DIVERSIFIER` |
| `MINING_CYCLICAL` |
| `DEFENSIVE_DURATION` |
| `HY_CONSUMER` |
| `CONSUMER_CREDIT` |
| `BANK_CAPITAL` |
| `CHEMICALS_CARRY` |
| `REAL_ESTATE` |
| `REFINING_MARGIN` |
| `AI_DEMAND` |
| `POWER_PRICE_BETA` |
