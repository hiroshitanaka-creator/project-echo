from __future__ import annotations

import logging

from po_echo.rth import RollingTranscriptHash, compute_rth


def test_rth_chain_hash_no_collision_across_10k_unique_windows() -> None:
    """10,000件入力でchain hash衝突が起きないことを確認する。"""
    n = 10_000
    hashes = {
        compute_rth(f"unique voice token {i} safety boundary audit")['hash_hex']
        for i in range(n)
    }
    assert len(hashes) == n


def test_rth_logs_warning_on_chain_hash_feature_collision(caplog) -> None:
    """同一chain hashに異なる特徴指紋が現れた場合、監査警告が残る。"""
    rth = RollingTranscriptHash()
    with caplog.at_level(logging.WARNING):
        rth._track_chain_hash_collision(chain_hash_hex="forced", feat_fp="fp_1")
        rth._track_chain_hash_collision(chain_hash_hex="forced", feat_fp="fp_2")

    assert any("rth_chain_hash_collision_detected" in m for m in caplog.messages)


def test_rth_chain_hash_collision_dict_pruned_at_upper_bound(caplog) -> None:
    """上限超過時に最古エントリが削除され、警告ログが残る。"""
    rth = RollingTranscriptHash()
    rth.state.t_ms = 1_000
    with caplog.at_level(logging.WARNING):
        for i in range(1001):
            rth.state.t_ms = 1_000 + i
            rth._track_chain_hash_collision(
                chain_hash_hex=f"chain_{i}",
                feat_fp=f"fp_{i}",
                max_seen_count=1000,
            )

    seen = rth.state.seen_chain_hash_to_feat_fp or {}
    assert len(seen) == 1000
    assert "chain_0" not in seen
    assert any("rth_chain_hash_collision_dict_pruned" in m for m in caplog.messages)
