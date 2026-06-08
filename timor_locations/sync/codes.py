"""Mint stable canonical pcodes for entities a provider introduces.

The canonical scheme is hierarchical and positional:

    SUCOCODE   = SUBDSTCODE * 100 + suco_seq      (e.g. 30308)
    SUBDSTCODE = DISTCODE    * 100 + post_seq      (e.g. 303)
    DISTCODE   = 1..14                             (fixed municipality set)

A minted code is allocated as the next free sequence *within its parent block*
and, once issued, is recorded in the crosswalk and never reused -- even if the
entity is later removed. Re-parenting an existing entity does **not** re-mint its
code: the code is a stable label, and the true parent is carried separately
(``SUBDSTCODE`` on the suco row), which is why a suco's code prefix may legitimately
differ from its current ``SUBDSTCODE`` after an admin-post reorganisation.
"""

from __future__ import annotations


class CodeAllocator:
    """Allocates next-free child codes within parent blocks, tracking issued codes."""

    def __init__(self, existing_codes: set[int]):
        self._issued = {int(c) for c in existing_codes}

    def _next_in_block(self, block_start: int, block_size: int) -> int:
        for seq in range(1, block_size):
            code = block_start + seq
            if code not in self._issued:
                self._issued.add(code)
                return code
        raise ValueError(f"No free code in block starting {block_start} (size {block_size})")

    def mint_post(self, distcode: int) -> int:
        """Next free SUBDSTCODE under a municipality: DISTCODE*100 + post_seq."""
        return self._next_in_block(int(distcode) * 100, 100)

    def mint_suco(self, subdstcode: int) -> int:
        """Next free SUCOCODE under an admin post: SUBDSTCODE*100 + suco_seq."""
        return self._next_in_block(int(subdstcode) * 100, 100)

    def reserve(self, code: int) -> None:
        self._issued.add(int(code))
