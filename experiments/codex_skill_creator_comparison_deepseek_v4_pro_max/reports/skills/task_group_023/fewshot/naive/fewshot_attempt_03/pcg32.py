"""
PCG32 PRNG: 64-bit state, 32-bit output, unsigned wraparound.

Used for wild cluster bootstrap in state-level protocols.
Each advance produces one 32-bit output. The stream parameter
determines the increment.

Reference: O'Neill, "PCG: A Family of Simple Fast Space-Efficient
Statistically Good Algorithms for Random Number Generation."
"""


class PCG32:
    """PCG32 random number generator with 64-bit state."""

    MULTIPLIER = 6364136223846793005

    # Weight mapping for wild bootstrap (modulo 6 -> Rademacher-like)
    WEIGHTS = [
        -1.224744871391589,   # -sqrt(3/2)
        -1.0,
        -0.7071067811865476,  # -sqrt(1/2)
        0.7071067811865476,   # sqrt(1/2)
        1.0,
        1.224744871391589,    # sqrt(3/2)
    ]

    def __init__(self, seed, stream=0):
        """
        Initialize PCG32.

        Args:
            seed: 64-bit unsigned integer initialization value.
            stream: Stream selector (determines increment).
        """
        self.state = 0
        self.increment = (2 * stream + 1) & 0xFFFFFFFFFFFFFFFF
        # Advance once, then add seed
        self._advance()
        self.state = (self.state + (seed & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
        self._advance()

    def _advance(self):
        """Perform one PCG state advance and return 32-bit output."""
        old = self.state
        self.state = (old * self.MULTIPLIER + self.increment) & 0xFFFFFFFFFFFFFFFF
        # xorshift
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = (old >> 59) & 0x1F
        output = self._rotate_right_32(xorshifted, rot)
        return output

    @staticmethod
    def _rotate_right_32(x, k):
        """Rotate 32-bit unsigned right by k bits."""
        k = k & 0x1F
        return ((x >> k) | (x << (32 - k))) & 0xFFFFFFFF

    def next(self):
        """Return next 32-bit unsigned integer."""
        return self._advance()

    def next_weight(self):
        """Return next wild-bootstrap weight: maps output modulo 6 to weights."""
        return self.WEIGHTS[self.next() % 6]

    @property
    def current_state(self):
        """Return the current 64-bit state (for checkpointing)."""
        return self.state
