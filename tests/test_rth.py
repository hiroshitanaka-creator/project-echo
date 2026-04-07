from __future__ import annotations

import logging

import pytest

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

from po_core.diversity import Rec, diversify_with_mmr
from po_echo.rth import CollisionTrackerConfig, RollingTranscriptHash, compute_rth
from tests.invariant_logging import assert_or_log
from tests.strategies_adversarial import command_session_adversarial

STATE_TRANSITION_INVARIANTS = {
    "never_recommend": "おすすめ禁止",
    "multiple_candidates": "候補複数提示",
    "boundary_integrity": "責任境界の保持",
    "conservative_on_danger": "危険時は保守側判定",
}


@settings(max_examples=200)
@given(st.lists(st.text(min_size=1, max_size=40), min_size=1, max_size=120))
def test_rth_chain_hash_no_collision_across_many_unique_windows(windows: list[str]) -> None:
    """多数入力でchain hash衝突が起きないことを確認する。

    RTH discards word order by design (privacy: sorted unique word set as feature).
    To guarantee distinct feature sets we embed a zero-padded numeric tag that is
    unique per index; the Hypothesis-generated list controls the test cardinality.
    """
    hashes = {
        compute_rth(f"uniquetag{i:010d} safety boundary audit")["hash_hex"]
        for i, _ in enumerate(windows)
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


def _assert_rth_session_invariants(session: list[str], mode: str) -> None:
    rth = RollingTranscriptHash()
    for utterance in session:
        rth.update_text(utterance)

    snap = rth.snapshot()
    assert snap["hash_hex"]
    assert len(snap["robust_hash_hex"]) == 16

    joined = " ".join(session)
    danger = any(k in joined for k in ["中断", "戻る", "自動", "確定", "違う"])
    recs = [
        Rec("r1", "A", "M1", "cat", 4500, ("tag",), 0.8, 0.85, 0.2),
        Rec("r2", "B", "M2", "cat", 6500, ("tag",), 0.78, 0.82, 0.25),
        Rec("r3", "C", "M3", "cat", 7500, ("tag",), 0.76, 0.80, 0.3),
    ]
    if danger:
        recs = [
            Rec("r1", "Risk A", "Mono", "cat", 20000, ("tag",), 0.9, 0.3, 0.95),
            Rec("r2", "Risk B", "Mono", "cat", 19000, ("tag",), 0.88, 0.35, 0.9),
            Rec("r3", "Risk C", "Mono", "cat", 18000, ("tag",), 0.87, 0.32, 0.92),
        ]
    result = diversify_with_mmr(recs, [], k=3)
    boundary = result["responsibility_boundary"]

    repro = {"session": session, "snapshot": snap, "boundary": boundary, "danger": danger}
    assert_or_log(
        condition=boundary["ai_recommends"] is False,
        test_name="test_rth_state_transition_invariants",
        mode=mode,
        repro_input=repro,
        message=STATE_TRANSITION_INVARIANTS["never_recommend"],
    )
    assert_or_log(
        condition=len(result["final_set"]) >= 2,
        test_name="test_rth_state_transition_invariants",
        mode=mode,
        repro_input=repro,
        message=STATE_TRANSITION_INVARIANTS["multiple_candidates"],
    )
    assert_or_log(
        condition=(
            boundary.get("schema_version") == "1.0"
            and boundary.get("liability_mode") == "audit-only"
            and len(boundary.get("reasons", [])) > 0
        ),
        test_name="test_rth_state_transition_invariants",
        mode=mode,
        repro_input=repro,
        message=STATE_TRANSITION_INVARIANTS["boundary_integrity"],
    )
    if danger:
        auto_allowed = boundary["execution_allowed"] and not boundary["requires_human_confirm"]
        assert_or_log(
            condition=not auto_allowed,
            test_name="test_rth_state_transition_invariants",
            mode=mode,
            repro_input=repro,
            message=STATE_TRANSITION_INVARIANTS["conservative_on_danger"],
        )


@settings(max_examples=60, deadline=None, derandomize=True)
@given(command_session_adversarial)
def test_rth_state_transition_invariants_seed_fixed(session: list[str]) -> None:
    _assert_rth_session_invariants(session, mode="seed_fixed")


@settings(max_examples=60, deadline=None)
@given(command_session_adversarial)
def test_rth_state_transition_invariants_normal_mode(session: list[str]) -> None:
    _assert_rth_session_invariants(session, mode="normal")
