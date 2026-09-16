#!/usr/bin/env python3
"""Deterministic PRNG implementations used across PHO audit protocols.

PCG32 (wild cluster bootstrap with stream parameter, e.g. train_001):
  64-bit state, 32-bit output. increment = 2 * stream + 1.
  multiplier = 6364136223846793005.
  Each advance: old = state; state = old * multiplier + increment (mod 2^64);
  xorshifted = low32(((old >> 18) ^ old) >> 27); rot = old >> 59;
  output = rotate_right_32(xorshifted, rot).

  Output -> Webb six-point weight mapping:
    output % 6 -> index into [-sqrt(1.5), -1, -sqrt(0.5), sqrt(0.5), 1, sqrt(1.5)].

XORSHIFT32 (wild cluster bootstrap, e.g. train_002, train_005):
  32-bit state. Each step: state ^= state << 13; state ^= state >> 17;
  state ^= state << 5. Output is the state itself.

All operations use 32-bit or 64-bit unsigned wraparound (MASK32, MASK64).
"""

import math

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF


def rotate_right_32(x: int, r: int) -> int:
    r &= 31
    return ((x >> r) | (x << (32 - r))) & MASK32


def low32(x: int) -> int:
    return x & MASK32


class PCG32:
    """PCG32 with 64-bit state and stream selector.

    increment = 2 * stream + 1.
    Init: state = 0; advance; state = (state + seed) % 2^64; advance.
    """

    MULTIPLIER = 6364136223846793005

    def __init__(self, seed: int, stream: int):
        self.state: int = 0
        self.increment: int = ((stream << 1) | 1) & MASK64
        self._advance()
        self.state = (self.state + (seed & MASK64)) & MASK64
        self._advance()

    def _advance(self):
        old = self.state
        self.state = (old * self.MULTIPLIER + self.increment) & MASK64
        return old

    def next_u32(self) -> int:
        old = self._advance()
        xorshifted = low32(((old >> 18) ^ old) >> 27)
        rot = old >> 59
        return rotate_right_32(xorshifted, rot)

    def next_weight(self) -> float:
        weights = [-math.sqrt(1.5), -1.0, -math.sqrt(0.5),
                    math.sqrt(0.5), 1.0, math.sqrt(1.5)]
        idx = self.next_u32() % 6
        return weights[idx]

    def get_state(self) -> int:
        """Return low 32 bits of current state (before next advance)."""
        return self.state & MASK32


class XORSHIFT32:
    """XORSHIFT32 generator.

    Init with 32-bit seed (forced non-zero). Each step:
      x ^= x << 13; x ^= x >> 17; x ^= x << 5.
    """

    def __init__(self, seed: int):
        self.state = seed & MASK32
        if self.state == 0:
            self.state = 1

    def next_u32(self) -> int:
        x = self.state
        x ^= (x << 13) & MASK32
        x ^= (x >> 17)
        x ^= (x << 5) & MASK32
        self.state = x
        return x

    def next_weight(self) -> float:
        weights = [-math.sqrt(1.5), -1.0, -math.sqrt(0.5),
                    math.sqrt(0.5), 1.0, math.sqrt(1.5)]
        idx = self.next_u32() % 6
        return weights[idx]

    def get_state(self) -> int:
        return self.state
