from __future__ import annotations

import logging

import pytest

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

from po_echo.rth import CollisionTrackerConfig, RollingTranscriptHash, compute_rth


@settings(max_examples=200)
@given(st.lists(st.text(min_size=1, max_size=40), min_size=1, max_size=120))
def test_rth_chain_hash_no_collision_across_many_unique_windows(windows: list[str]) -> None:
    """多数入力でchain hash衝突が起きないことを確認する。"""
    hashes = {
        compute_rth(f"{window} unique voice token {i} safety boundary audit")["hash_hex"]
        for i, window in enumerate(windows)
    }
    assert len(hashes) == len(windows)


def test_rth_logs_warning_on_chain_hash_feature_collision(caplog) -> None:
    """同一chain hashに異なる特徴指紋が現れた場合、監査警告が残る。"""
    rth = RollingTranscriptHash()
    with caplog.at_level(logging.WARNING):
        rth._track_chain_hash_collision(chain_hash_hex="forced", feat_fp="fp_1")
        rth._track_chain_hash_collision(chain_hash_hex="forced", feat_fp="fp_2")

    assert any("rth_chain_hash_collision_detected" in m for m in caplog.messages)


def test_rth_chain_hash_collision_dict_pruned_at_upper_bound(caplog) -> None:
    """上限超過時に最古エントリが削除され、警告ログが残る。"""
    rth = RollingTranscriptHash(
        collision_tracker_config=CollisionTrackerConfig(max_seen_count=10, ttl_ms=10_000)
    )
    rth.state.t_ms = 1_000
    with caplog.at_level(logging.WARNING):
        for i in range(11):
            rth.state.t_ms = 1_000 + i
            rth._track_chain_hash_collision(
                chain_hash_hex=f"chain_{i}",
                feat_fp=f"fp_{i}",
            )

    seen = rth.state.seen_chain_hash_to_feat_fp or {}
    assert len(seen) == 10
    assert any("reason=max_count" in m for m in caplog.messages)


def test_rth_chain_hash_collision_dict_pruned_by_ttl(caplog) -> None:
    """TTL超過エントリが削除され、警告ログが残る。"""
    rth = RollingTranscriptHash(
        collision_tracker_config=CollisionTrackerConfig(max_seen_count=100, ttl_ms=5)
    )
    with caplog.at_level(logging.WARNING):
        rth.state.t_ms = 1_000
        rth._track_chain_hash_collision(chain_hash_hex="chain_a", feat_fp="fp_a")
        rth.state.t_ms = 1_020
        rth._track_chain_hash_collision(chain_hash_hex="chain_b", feat_fp="fp_b")

    seen = rth.state.seen_chain_hash_to_feat_fp or {}
    assert len(seen) == 1
    assert any("reason=ttl" in m for m in caplog.messages)
