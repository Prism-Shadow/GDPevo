"""
Reusable random number generators for PHO algorithmic audits.

Supports PCG32 and XORSHIFT32 as used in wild cluster bootstrap
and restricted-null resampling procedures.
"""

import numpy as np


class PCG32:
    """PCG32 random number generator for Webb wild cluster bootstrap.

    Usage:
        pcg = PCG32(seed=14022023, stream=17)
        weights = pcg.webb_weights(n_clusters)

    Implements PCG-XSH-RR 32-bit output variant.
    """

    def __init__(self, seed: int = 0, stream: int = 0):
        self.state = 0
        self.inc = (stream << 1) | 1
        self._step()
        self.state = (self.state + seed) & 0xFFFFFFFFFFFFFFFF
        self._step()

    def _step(self):
        self.state = (self.state * 6364136223846793005 + self.inc) & 0xFFFFFFFFFFFFFFFF

    def random(self) -> float:
        """Return uniform float in [0, 1)."""
        old_state = self.state
        self._step()
        xorshifted = ((old_state >> 18) ^ old_state) >> 27
        rot = old_state >> 59
        result = ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF
        return result / 4294967296.0

    def webb_weights(self, n: int) -> list:
        """Generate n Webb 6-point wild bootstrap weights."""
        w = []
        for _ in range(n):
            r = self.random()
            if r < 1 / 6:
                w.append(-np.sqrt(1.5))
            elif r < 2 / 6:
                w.append(-1.0)
            elif r < 3 / 6:
                w.append(-np.sqrt(0.5))
            elif r < 4 / 6:
                w.append(np.sqrt(0.5))
            elif r < 5 / 6:
                w.append(1.0)
            else:
                w.append(np.sqrt(1.5))
        return w


class XORSHIFT32:
    """XORSHIFT32 random number generator.

    Usage:
        rng = XORSHIFT32(seed=23032023)
        u = rng.random()
    """

    def __init__(self, seed: int = 0):
        self.state = seed & 0xFFFFFFFF
        if self.state == 0:
            self.state = 1

    def random(self) -> float:
        """Return uniform float in [0, 1)."""
        x = self.state & 0xFFFFFFFF
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x
        return x / 4294967296.0


def make_rng(method: str, seed: int, stream: int = 0):
    """Factory for algorithm-specific RNGs."""
    if method.upper() in ("PCG32", "PCG32_WEBB_WILD_CLUSTER_BOOTSTRAP_T"):
        return PCG32(seed=seed, stream=stream)
    if method.upper() in ("XORSHIFT32", "RESTRICTED_NULL_PAIRED_STATE_XORSHIFT32_BOOTSTRAP_T",
                          "RESTRICTED_NULL_STATE_WILD_CLUSTER_BOOTSTRAP_T_WITH_XORSHIFT32"):
        return XORSHIFT32(seed=seed)
    raise ValueError(f"Unknown RNG method: {method}")
