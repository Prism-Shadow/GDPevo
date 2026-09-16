# Wild Cluster Bootstrap

## Observed Fit

1. Fit the full unrestricted model on the active analytic matrix.
2. Compute CR1 cluster-robust standard errors using the declared cluster unit.
3. Studentize: t_obs = b_target / SE_CR1(target), or |t_obs| for absolute tests.

## Restricted Model

Fit the model with the target variable removed from the design. Retain:
- restricted_fitted: fitted values from the restricted model
- restricted_residual: residuals from the restricted model (untransformed)

## Pseudo-Random Number Generators

### PCG32 (for 64-bit state, 32-bit output)

Constants: multiplier = 6364136223846793005 (decimal)

Initialization:
1. increment = 2 * stream + 1  (unsigned 64-bit)
2. state = 0
3. Advance: old = state; state = old * multiplier + increment (mod 2^64)
4. state = (state + seed) mod 2^64
5. Advance again

Each advance produces output:
- old = state
- state = old * multiplier + increment (mod 2^64)
- xorshifted = ((old >> 18) ^ old) >> 27  (low 32 bits)
- rot = old >> 59  (low 5 bits)
- output = rotate_right_32(xorshifted, rot)

Mapping to wild weights (Webb 6-point):
- output mod 6 maps to: 0 -> -sqrt(3/2), 1 -> -1, 2 -> -sqrt(1/2), 3 -> sqrt(1/2), 4 -> 1, 5 -> sqrt(3/2)

One continuous generator. Draw once per cluster in entity-code order for each replicate. Never reset the stream between replicates. Record checkpoints only after the completed replicate (state after all draws for that replicate).

### XORSHIFT32 (for 32-bit state)

Operations (all unsigned 32-bit):
1. x ^= x << 13
2. x ^= x >> 17
3. x ^= x << 5
Mask to 32 bits after each xor.

Mapping: low bit = 1 -> +1, low bit = 0 -> -1.

One continuous stream. Draw once per cluster in entity-code (state) order. Odd state index -> +1, even -> -1 depending on the PRNG output low bit.

## Bootstrap Procedure

For each replicate r:
1. Draw one wild weight per cluster from the PRNG in cluster order.
2. Assign the same weight to every observation in that cluster.
3. y* = restricted_fitted + restricted_residual * cluster_weight
4. Refit the full unrestricted model on (X, y*).
5. Recompute CR1 standard errors.
6. Studentize: t*_r = b*_target / SE*_CR1(target), or |t*_r| for absolute tests.
7. Record checkpoint if r is in the declared checkpoint list (after completing the replicate).

## Test and Aggregation

For two-sided test:
- exceedance_count = count of |t*_r| >= |t_obs| (or with tolerance delta: |t*_r| >= |t_obs| - delta)
- plus_one_p = (exceedance_count + 1) / (B + 1)

For one-sided (absolute) test: same counting on absolute values.

## Quantiles

**Nearest-rank (Type 1)**: For sorted values x[0..B-1] and probability p:
- r = min(B, ceil(p * B))  (one-based rank)
- quantile = x[r-1]

**Type-7 interpolation**: For sorted values x[0..B-1] and probability p:
- h = (B - 1) * p
- j = floor(h)
- gamma = h - j
- quantile = (1 - gamma) * x[j] + gamma * x[j+1]  (zero-based indexing)

## Bootstrap Coefficient Distribution

- bootstrap_coefficient_mean = mean of b* across replicates
- bootstrap_coefficient_sample_sd = sample SD of b* across replicates (ddof=1)
- bootstrap_t_quantiles: quantiles of t* distribution

## Batch Exceedance Counts

When reporting batch exceedance counts, divide the B replicates into consecutive batches of size ceil(B / n_batches) or as declared. For each batch, count exceedances among its replicates. The sum of batch counts equals exceedance_n.

For PCG32 weight-index rows: record the first three replicates' weight indices (0-5) for each cluster. Each row has one index per cluster in state order.
