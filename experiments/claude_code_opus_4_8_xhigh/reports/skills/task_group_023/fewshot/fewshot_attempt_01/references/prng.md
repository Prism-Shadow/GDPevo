# Pseudorandom generators and weight maps

Requests pin an exact PRNG for the wild bootstrap (and any randomized step). Two families
appear; the request's method name / metadata (`seed`, `stream`, "PCG32", "XORSHIFT32")
selects which. Use **one continuous stream** per module, drawing once per cluster/entity in
the declared (usually ascending entity-code) order per replicate. Reuse the same draw
across paired equations when the method says so. Record any `final_prng_state`/checkpoint
**after** the referenced replicate completes, without resetting the stream. All arithmetic
is unsigned with modular wraparound at the stated width.

## PCG32 (64-bit state, 32-bit XSH-RR output)

Constant `MULT = 6364136223846793005`. Let `stream` and `seed` come from the request.

Seeding:
```
increment = (2*stream + 1)            mod 2^64
state     = 0
state     = (state*MULT + increment)  mod 2^64      # advance
state     = (state + seed)            mod 2^64       # add initialization value
state     = (state*MULT + increment)  mod 2^64      # advance
```
Each output:
```
old        = state
state      = (old*MULT + increment)   mod 2^64
xorshifted = (((old >> 18) XOR old) >> 27) AND 0xFFFFFFFF
rot        = old >> 59
output     = ((xorshifted >> rot) | (xorshifted << ((-rot) AND 31))) AND 0xFFFFFFFF   # rotate_right_32
```

**Webb six-point wild weights** (used with PCG32): `idx = output mod 6`, then map *in this
order*:
```
idx: 0                1     2               3              4    5
val: -sqrt(3/2)      -1    -sqrt(1/2)      +sqrt(1/2)     +1   +sqrt(3/2)
```
When a template asks for "weight index rows", it wants the integer `idx` (0–5) per entity,
aligned to the entity order.

## xorshift32 (32-bit state)

Initialize `state = seed AND 0xFFFFFFFF`. Each output (mask to 32 bits after **every** xor):
```
x = state
x ^= (x << 13) AND 0xFFFFFFFF ;  x &= 0xFFFFFFFF
x ^=  x >> 17
x ^= (x << 5)  AND 0xFFFFFFFF ;  x &= 0xFFFFFFFF
state = x
output = x
```
**Rademacher ±1 weights** (used with xorshift32): low bit 1 (odd) → `+1`, else (even) →
`-1`. `final_prng_state` is the 32-bit `state` after all draws for the module.

## Reproducibility notes

- Do **not** substitute a library RNG. Implement the integer recurrences exactly.
- The number of draws per replicate equals the number of clusters/entities; advancing the
  stream must be exact so that checkpoints and `final_prng_state` match.
- Confirm the weight map order against any "first_three_weight_index_rows" or observed
  checkpoint the template exposes before trusting a full run.
