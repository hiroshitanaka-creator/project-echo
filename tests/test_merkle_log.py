"""Tests for po_echo.merkle_log (RFC 6962 Merkle hash tree)."""

from __future__ import annotations

import hashlib

import pytest

from po_echo.merkle_log import (
    compute_inclusion_proof,
    compute_inclusion_proof_from_leaf_hashes,
    compute_root,
    compute_root_from_leaf_hashes,
    internal_hash,
    leaf_hash,
    verify_inclusion_proof,
)


# ---------------------------------------------------------------------------
# Primitive hash functions
# ---------------------------------------------------------------------------


def test_leaf_hash_uses_zero_prefix():
    """leaf_hash(v) = SHA-256(0x00 || v) — RFC 6962 domain separation."""
    v = b"hello world"
    assert leaf_hash(v) == hashlib.sha256(b"\x00" + v).digest()


def test_internal_hash_uses_one_prefix():
    """internal_hash(l, r) = SHA-256(0x01 || l || r)."""
    l = b"a" * 32
    r = b"b" * 32
    assert internal_hash(l, r) == hashlib.sha256(b"\x01" + l + r).digest()


def test_leaf_and_internal_hashes_are_distinct_for_same_bytes():
    """Domain separation: identical byte content yields different hashes at each level."""
    v = b"x" * 32
    # leaf_hash(v) uses 0x00 prefix; internal_hash uses 0x01 prefix
    assert leaf_hash(v) != internal_hash(v, b"\x00" * 32)


def test_leaf_hash_output_is_32_bytes():
    assert len(leaf_hash(b"data")) == 32


def test_internal_hash_output_is_32_bytes():
    assert len(internal_hash(b"a" * 32, b"b" * 32)) == 32


# ---------------------------------------------------------------------------
# Root computation
# ---------------------------------------------------------------------------


def test_empty_tree_root():
    """Empty tree root is SHA-256(b'') per convention."""
    assert compute_root([]) == hashlib.sha256(b"").digest()


def test_single_leaf_root_equals_leaf_hash():
    """Root of a 1-leaf tree is just the leaf hash."""
    v = b"only leaf"
    assert compute_root([v]) == leaf_hash(v)


def test_two_leaf_root():
    """Root of [L0, L1] = internal_hash(leaf_hash(L0), leaf_hash(L1))."""
    l0, l1 = b"left", b"right"
    expected = internal_hash(leaf_hash(l0), leaf_hash(l1))
    assert compute_root([l0, l1]) == expected


def test_three_leaf_root_structure():
    """3-leaf tree: k=2, left=[L0,L1], right=[L2]; root=internal(Root_L, leaf(L2))."""
    l0, l1, l2 = b"a", b"b", b"c"
    root_left = internal_hash(leaf_hash(l0), leaf_hash(l1))
    assert compute_root([l0, l1, l2]) == internal_hash(root_left, leaf_hash(l2))


def test_four_leaf_root_structure():
    """4-leaf tree: k=2; left=[L0,L1], right=[L2,L3]."""
    leaves = [b"0", b"1", b"2", b"3"]
    rl = internal_hash(leaf_hash(b"0"), leaf_hash(b"1"))
    rr = internal_hash(leaf_hash(b"2"), leaf_hash(b"3"))
    assert compute_root(leaves) == internal_hash(rl, rr)


def test_compute_root_and_from_leaf_hashes_agree():
    """Both root-computation paths must produce identical results."""
    leaves = [b"a", b"b", b"c", b"d", b"e"]
    lh = [leaf_hash(v) for v in leaves]
    assert compute_root(leaves) == compute_root_from_leaf_hashes(lh)


def test_different_inputs_different_roots():
    """Changing any leaf changes the root."""
    leaves = [b"L0", b"L1", b"L2"]
    root_a = compute_root(leaves)
    root_b = compute_root([b"L0", b"L1", b"CHANGED"])
    assert root_a != root_b


# ---------------------------------------------------------------------------
# Inclusion proofs — generation
# ---------------------------------------------------------------------------


def test_single_leaf_proof_is_empty():
    """No sibling hashes needed for a 1-leaf tree."""
    assert compute_inclusion_proof([b"only"], 0) == []


def test_two_leaf_proof_length():
    """2-leaf tree: proof for each leaf has exactly 1 sibling."""
    leaves = [b"L0", b"L1"]
    assert len(compute_inclusion_proof(leaves, 0)) == 1
    assert len(compute_inclusion_proof(leaves, 1)) == 1


def test_two_leaf_proof_sibling_correctness():
    """Leaf 0's sibling is leaf_hash(L1); leaf 1's sibling is leaf_hash(L0)."""
    l0, l1 = b"A", b"B"
    proof0 = compute_inclusion_proof([l0, l1], 0)
    proof1 = compute_inclusion_proof([l0, l1], 1)
    assert proof0 == [leaf_hash(l1)]
    assert proof1 == [leaf_hash(l0)]


def test_proof_length_grows_logarithmically():
    """Proof length for a balanced tree ≈ log2(tree_size)."""
    import math

    for n in [1, 2, 4, 8, 16, 32]:
        proof = compute_inclusion_proof([f"l{i}".encode() for i in range(n)], 0)
        expected_len = 0 if n == 1 else int(math.ceil(math.log2(n)))
        assert len(proof) == expected_len, f"n={n}: expected {expected_len}, got {len(proof)}"


def test_inclusion_proof_from_leaf_hashes_matches_from_values():
    """Both proof paths must return identical audit paths."""
    leaves = [b"x", b"y", b"z", b"w"]
    lh = [leaf_hash(v) for v in leaves]
    for i in range(len(leaves)):
        assert compute_inclusion_proof(leaves, i) == compute_inclusion_proof_from_leaf_hashes(lh, i)


def test_compute_inclusion_proof_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        compute_inclusion_proof([], 0)


def test_compute_inclusion_proof_index_out_of_range_raises():
    with pytest.raises(IndexError):
        compute_inclusion_proof([b"a"], 1)


def test_compute_inclusion_proof_negative_index_raises():
    with pytest.raises(IndexError):
        compute_inclusion_proof([b"a", b"b"], -1)


# ---------------------------------------------------------------------------
# Inclusion proofs — verification
# ---------------------------------------------------------------------------


def test_verify_single_leaf_proof():
    v = b"single"
    root = compute_root([v])
    assert verify_inclusion_proof(root, leaf_hash(v), 0, [], 1)


def test_verify_all_leaves_various_tree_sizes():
    """Every leaf in every tree of size 1..20 must verify successfully."""
    for n in range(1, 21):
        leaves = [f"leaf-{i:04d}".encode() for i in range(n)]
        root = compute_root(leaves)
        for i in range(n):
            proof = compute_inclusion_proof(leaves, i)
            assert verify_inclusion_proof(root, leaf_hash(leaves[i]), i, proof, n), (
                f"Proof failed: n={n}, i={i}"
            )


def test_verify_tampered_leaf_fails():
    leaves = [b"a", b"b", b"c"]
    root = compute_root(leaves)
    proof = compute_inclusion_proof(leaves, 1)
    assert not verify_inclusion_proof(root, leaf_hash(b"TAMPERED"), 1, proof, 3)


def test_verify_tampered_proof_node_fails():
    leaves = [b"a", b"b", b"c", b"d"]
    root = compute_root(leaves)
    proof = compute_inclusion_proof(leaves, 2)
    bad_proof = [bytes(b ^ 0xFF for b in p) for p in proof]  # flip all bits
    assert not verify_inclusion_proof(root, leaf_hash(b"c"), 2, bad_proof, 4)


def test_verify_wrong_index_fails():
    """Proof for leaf 0 must not verify for leaf 2."""
    leaves = [b"a", b"b", b"c"]
    root = compute_root(leaves)
    proof_for_0 = compute_inclusion_proof(leaves, 0)
    assert not verify_inclusion_proof(root, leaf_hash(b"a"), 2, proof_for_0, 3)


def test_verify_wrong_root_fails():
    leaves = [b"a", b"b"]
    root = compute_root(leaves)
    proof = compute_inclusion_proof(leaves, 0)
    bad_root = bytes(b ^ 0xFF for b in root)
    assert not verify_inclusion_proof(bad_root, leaf_hash(b"a"), 0, proof, 2)


def test_verify_wrong_tree_size_fails():
    """Claiming the wrong tree size invalidates the proof."""
    leaves = [b"a", b"b"]
    root = compute_root(leaves)
    proof = compute_inclusion_proof(leaves, 0)
    # Correct proof but wrong tree_size → decisions count mismatch
    assert not verify_inclusion_proof(root, leaf_hash(b"a"), 0, proof, 3)


def test_verify_zero_tree_size_returns_false():
    assert not verify_inclusion_proof(b"\x00" * 32, b"\x00" * 32, 0, [], 0)


def test_verify_index_equals_tree_size_returns_false():
    leaves = [b"a"]
    root = compute_root(leaves)
    assert not verify_inclusion_proof(root, leaf_hash(b"a"), 1, [], 1)


def test_verify_proof_from_leaf_hashes():
    leaves = [b"p", b"q", b"r", b"s", b"t"]
    lh = [leaf_hash(v) for v in leaves]
    root = compute_root_from_leaf_hashes(lh)
    for i in range(len(leaves)):
        proof = compute_inclusion_proof_from_leaf_hashes(lh, i)
        assert verify_inclusion_proof(root, lh[i], i, proof, len(leaves))
