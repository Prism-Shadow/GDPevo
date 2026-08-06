# PRNG and Bootstrap Reference

## PCG32 Implementation

```python
class PCG32:
    def __init__(self, seed, stream=0):
        self.inc = ((stream << 1) | 1) & 0xFFFFFFFFFFFFFFFF
        self.state = (seed + self.inc) & 0xFFFFFFFFFFFFFFFF
        self._step()
        self.state = (self.state + self.inc) & 0xFFFFFFFFFFFFFFFF

    def _step(self):
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & 0xFFFFFFFFFFFFFFFF
        return old

    def next_int(self):
        old = self._step()
        xor = ((old >> 18) ^ old) >> 27
        rot = old >> 59
        return int(((xor >> rot) | (xor << ((-rot) & 31))) & 0xFFFFFFFF)
```

## XORSHIFT32 Implementation

Used in some county-level tasks. Operates on a 32-bit state:

```python
class XORSHIFT32:
    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF
        if self.state == 0:
            self.state = 1  # avoid zero state

    def next_int(self):
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17)
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state
```

## Webb 6-Point Weight Distribution

```python
webb_weights = [-(5/3), -(5/6), -(1/3), (1/3), (5/6), (5/3)]
```

Index 0 through 5. Each cluster's weight index = `prng.next_int() % 6`.

## Wild Cluster Bootstrap Procedure

1. Fit **restricted** model (target coefficient excluded/zeroed under H0).
2. Obtain restricted residuals `e_r`.
3. For each replicate `b = 1..B`:
   a. Generate weight index `w_i` for each cluster `i` via PRNG.
   b. Construct bootstrap y: `y*_i = X_r * beta_r + webb[w_i] * e_r_i` (within each cluster i).
   c. Fit **unrestricted** model on bootstrap data.
   d. Compute cluster-robust t-statistic for target coefficient on bootstrap data.
4. p-value = `(count(|t_bootstrap| >= |t_obs|) + 1) / (B + 1)`.

## Checkpoint Reporting

Tasks may request PRNG state and t-statistic at specific replicate numbers (e.g., 1, 2, 4, 8, ..., 2047). Capture these *after* generating the weight indices for that replicate, before computing the bootstrap fit.

## Batch Exceedance Counts

Some tasks request exceedance counts in batches (e.g., 100-replicate intervals). For batch `b`: count replicates in `[b*100, (b+1)*100)` where `|t_bootstrap| >= |t_obs|`.

## Bootstrap p-value Convention

Always use **plus-one** formulation: `p = (exceedance + 1) / (B + 1)`. This avoids p=0 and is standard for bootstrap inference.
