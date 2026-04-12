"""
Merkle Transparent Log — RFC 6962-compatible Merkle hash tree.

Hash conventions (domain separation prevents second-preimage attacks):
    leaf_hash(v)        = SHA-256(0x00 || v)
    internal_hash(l, r) = SHA-256(0x01 || l || r)

Inclusion proof (audit path):
    Ordered from leaf-level to root-level (closest-to-leaf first), matching
    RFC 6962 §2.1.1 PATH definition.  verify_inclusion_proof() reconstructs
    the root from a leaf hash and its proof without requiring the full tree.

Empty tree root: SHA-256(b"")

Reference: RFC 6962 §2.1 "Merkle Hash Trees"
           https://www.rfc-editor.org/rfc/rfc6962#section-2.1
"""

from __future__ import annotations

import hashlib

_LEAF_PREFIX: bytes = b"\x00"
_BRANCH_PREFIX: bytes = b"\x01"


# ---------------------------------------------------------------------------
# Primitive hash functions
# ---------------------------------------------------------------------------


def leaf_hash(value: bytes) -> bytes:
    """SHA-256(0x00 || value) — RFC 6962 leaf node hash."""
    return hashlib.sha256(_LEAF_PREFIX + value).digest()


def internal_hash(left: bytes, right: bytes) -> bytes:
    """SHA-256(0x01 || left || right) — RFC 6962 internal node hash."""
    return hashlib.sha256(_BRANCH_PREFIX + left + right).digest()


# ---------------------------------------------------------------------------
# Internal tree helpers
# ---------------------------------------------------------------------------


def _split(n: int) -> int:
    """Return the largest power of 2 strictly less than n (RFC 6962 split point).

    RFC 6962: "k is the largest power of two smaller than n, i.e., k < n ≤ 2k"
    """
    # (n-1).bit_length() = ceil(log2(n)); shift right by one gives floor(log2(n-1)).
    return 1 << ((n - 1).bit_length() - 1)


def _tree_root(hashes: list[bytes], lo: int, hi: int) -> bytes:
    """Recursively compute Merkle root over hashes[lo:hi] (pre-computed leaf hashes)."""
    if hi - lo == 1:
        return hashes[lo]
    k = _split(hi - lo)
    mid = lo + k
    return internal_hash(_tree_root(hashes, lo, mid), _tree_root(hashes, mid, hi))


def _inclusion_proof_rec(
    hashes: list[bytes], index: int, lo: int, hi: int
) -> list[bytes]:
    """RFC 6962 PATH(index, hashes[lo:hi]); returns audit path leaf-to-root."""
    if hi - lo == 1:
        return []
    k = _split(hi - lo)
    mid = lo + k
    if index < mid:
        sibling = _tree_root(hashes, mid, hi)
        return _inclusion_proof_rec(hashes, index, lo, mid) + [sibling]
    else:
        sibling = _tree_root(hashes, lo, mid)
        return _inclusion_proof_rec(hashes, index, mid, hi) + [sibling]


# ---------------------------------------------------------------------------
# Public API — root computation
# ---------------------------------------------------------------------------


def compute_root(leaves: list[bytes]) -> bytes:
    """Compute Merkle root from raw leaf values (applies leaf_hash to each).

    Args:
        leaves: Raw byte values.  leaf_hash() is applied internally.

    Returns:
        32-byte Merkle root.  SHA-256(b"") for an empty tree.
    """
    if not leaves:
        return hashlib.sha256(b"").digest()
    hashes = [leaf_hash(v) for v in leaves]
    return _tree_root(hashes, 0, len(hashes))


def compute_root_from_leaf_hashes(leaf_hashes: list[bytes]) -> bytes:
    """Compute Merkle root from pre-computed leaf hashes.

    Use this when callers have already applied leaf_hash() (e.g. the audit log
    stores leaf_hash_hex directly and must not double-hash).

    Args:
        leaf_hashes: Pre-computed leaf hashes (each 32 bytes).

    Returns:
        32-byte Merkle root.  SHA-256(b"") for an empty list.
    """
    if not leaf_hashes:
        return hashlib.sha256(b"").digest()
    return _tree_root(leaf_hashes, 0, len(leaf_hashes))


# ---------------------------------------------------------------------------
# Public API — inclusion proofs
# ---------------------------------------------------------------------------


def compute_inclusion_proof(leaves: list[bytes], index: int) -> list[bytes]:
    """Compute RFC 6962 inclusion proof for the leaf at *index* from raw values.

    Args:
        leaves: Full list of raw leaf values (leaf_hash is applied internally).
        index:  0-based position of the target leaf.

    Returns:
        Ordered list of sibling hashes (leaf-to-root).  Empty list for a
        single-leaf tree (no proof needed).

    Raises:
        ValueError: if *leaves* is empty.
        IndexError: if *index* is out of range.
    """
    if not leaves:
        raise ValueError("Cannot compute inclusion proof for an empty tree")
    if index < 0 or index >= len(leaves):
        raise IndexError(f"index {index} out of range [0, {len(leaves)})")
    hashes = [leaf_hash(v) for v in leaves]
    return _inclusion_proof_rec(hashes, index, 0, len(hashes))


def compute_inclusion_proof_from_leaf_hashes(
    leaf_hashes: list[bytes], index: int
) -> list[bytes]:
    """Compute RFC 6962 inclusion proof from pre-computed leaf hashes.

    Args:
        leaf_hashes: Pre-computed leaf hashes (each 32 bytes).
        index:       0-based position of the target leaf.

    Returns:
        Ordered list of sibling hashes (leaf-to-root).  Empty list for a
        single-leaf tree.

    Raises:
        ValueError: if *leaf_hashes* is empty.
        IndexError: if *index* is out of range.
    """
    if not leaf_hashes:
        raise ValueError("Cannot compute inclusion proof for an empty tree")
    if index < 0 or index >= len(leaf_hashes):
        raise IndexError(f"index {index} out of range [0, {len(leaf_hashes)})")
    return _inclusion_proof_rec(leaf_hashes, index, 0, len(leaf_hashes))


# ---------------------------------------------------------------------------
# Public API — verification
# ---------------------------------------------------------------------------


def verify_inclusion_proof(
    root: bytes,
    leaf_hash_val: bytes,
    index: int,
    proof: list[bytes],
    tree_size: int,
) -> bool:
    """Verify a RFC 6962 inclusion proof without the full tree.

    Args:
        root:          Expected 32-byte Merkle root.
        leaf_hash_val: Pre-computed leaf hash (leaf_hash(value), 32 bytes).
        index:         0-based position of the leaf in the committed tree.
        proof:         Audit path returned by compute_inclusion_proof*()
                       (leaf-to-root order).
        tree_size:     Total number of leaves in the committed tree.

    Returns:
        True only when the audit path successfully reconstructs *root* from
        *leaf_hash_val* at *index*.  False for any invalid input or tampered data.
    """
    if tree_size <= 0 or index < 0 or index >= tree_size:
        return False
    if tree_size == 1:
        return leaf_hash_val == root and len(proof) == 0

    # Reconstruct the left/right decisions made during proof generation.
    # decisions[0] is the top-level split (root level),
    # decisions[-1] is the deepest split (leaf level).
    decisions: list[bool] = []
    n = tree_size
    j = index
    while n > 1:
        k = _split(n)
        if j < k:
            decisions.append(False)  # went left; proof element is right subtree
            n = k
        else:
            decisions.append(True)   # went right; proof element is left subtree
            j -= k
            n -= k

    if len(decisions) != len(proof):
        return False

    # proof is leaf-to-root; decisions is root-to-leaf → zip in reverse.
    current = leaf_hash_val
    for went_right, sibling in zip(reversed(decisions), proof):
        if went_right:
            current = internal_hash(sibling, current)  # sibling is left child
        else:
            current = internal_hash(current, sibling)  # sibling is right child

    return current == root
