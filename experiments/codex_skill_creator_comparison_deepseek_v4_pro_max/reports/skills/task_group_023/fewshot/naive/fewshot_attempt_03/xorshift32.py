"""
xorshift32 PRNG: unsigned 32-bit state with three-xor sequence.

Used for wild cluster bootstrap in county-level protocols.
Maps low bit to +/-1 for wild bootstrap weights.
"""


class Xorshift32:
    """xorshift32 random number generator (Marsaglia, 2003)."""

    def __init__(self, seed):
        """
        Initialize xorshift32.

        Args:
            seed: 32-bit unsigned integer seed. Must be nonzero.
        """
        self.state = seed & 0xFFFFFFFF
        if self.state == 0:
            self.state = 1  # xorshift requires nonzero state

    def next(self):
        """Advance and return next 32-bit unsigned integer."""
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state

    def next_weight(self):
        """
        Return wild-bootstrap weight: +1 for odd state, -1 for even state.
        Uses the low bit after advancement.
        """
        return 1.0 if (self.next() & 1) else -1.0

    @property
    def current_state(self):
        """Return the current 32-bit state (for checkpointing)."""
        return self.state
