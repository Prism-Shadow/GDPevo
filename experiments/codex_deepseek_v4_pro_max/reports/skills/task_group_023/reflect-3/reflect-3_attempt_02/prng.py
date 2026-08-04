 """
 PRNG implementations for Public Health Observatory audits.
 
 PCG32: Used for state-level wild cluster bootstrap (Webb weights).
 Xorshift32: Used for county-level wild cluster bootstrap.
 """
 
 def pcg32_seed(init_state=42):
     """Initialize PCG32 state."""
     return init_state & 0xFFFFFFFFFFFFFFFF
 
 def pcg32_next(state, seq):
     """
     PCG RXS-M-XS 64/32 generator step.
     Returns (new_state, 32-bit output).
     """
     oldstate = state & 0xFFFFFFFFFFFFFFFF
     state = (oldstate * 6364136223846793005 + (seq | 1)) & 0xFFFFFFFFFFFFFFFF
     xorshifted = ((oldstate >> 18) ^ oldstate) >> 27
     rot = oldstate >> 59
     result = ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF
     return state, result
 
 def pcg32_uniform(state, seq):
     """Generate uniform [0, 1) from PCG32."""
     state, bits = pcg32_next(state, seq)
     return state, bits / 4294967296.0
 
 def generate_webb_weights(n_clusters, n_replicates, seed, stream):
     """
     Generate Rademacher (+1/-1) weights for wild cluster bootstrap.
     One weight per cluster per replicate.
     """
     import numpy as np
     W = np.zeros((n_replicates, n_clusters))
     s = seed
     for r in range(n_replicates):
         for c in range(n_clusters):
             s, u = pcg32_uniform(s, stream)
             W[r, c] = 1.0 if u >= 0.5 else -1.0
     return W
 
 def xorshift32_seed(init_state=42):
     """Initialize Xorshift32 state."""
     return init_state & 0xFFFFFFFF
 
 def xorshift32_next(state):
     """Xorshift32 generator step. Returns (new_state, 32-bit output)."""
     x = state & 0xFFFFFFFF
     x ^= (x << 13) & 0xFFFFFFFF
     x ^= (x >> 17) & 0xFFFFFFFF
     x ^= (x << 5) & 0xFFFFFFFF
     return x
 
 def xorshift32_uniform(state):
     """Generate uniform [0, 1) from Xorshift32."""
     new_state = xorshift32_next(state)
     return new_state, new_state / 4294967296.0
