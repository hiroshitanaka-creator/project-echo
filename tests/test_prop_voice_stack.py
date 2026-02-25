"""Property-based tests for integrated voice stack invariants."""

from __future__ import annotations

import copy

from hypothesis import given, settings
from hypothesis import strategies as st

from po_echo.ear_handshake import issue_challenge, new_device, verify_response
from po_echo.rth import compute_rth
from po_echo.voice_boundary import classify_risk


@settings(max_examples=120, deadline=None)
@given(st.floats(min_value=10000, max_value=10_000_000, allow_nan=False, allow_infinity=False))
def test_voice_boundary_amount_high_always_high_risk(amount: float) -> None:
    # Project Echo 不変原則：選択肢を残すには高リスクを機械的に強制する
    risk = classify_risk("generic", {"amount": amount})
    assert risk == "high"


@settings(max_examples=120, deadline=None)
@given(st.floats(min_value=1000, max_value=9999.99, allow_nan=False, allow_infinity=False))
def test_voice_boundary_amount_medium_window_maps_to_medium_risk(amount: float) -> None:
    # Project Echo 不変原則：選択肢を残すには閾値境界を安定化する
    risk = classify_risk("generic", {"amount": amount})
    assert risk == "medium"


@settings(max_examples=100, deadline=None)
@given(st.binary(min_size=32, max_size=32))
def test_ear_handshake_rejects_tampered_signature(master_key: bytes) -> None:
    # Project Echo 不変原則：画面なし音声経路でも改ざん拒否を機械的に担保する
    device = new_device(master_key=master_key)
    challenge = issue_challenge(device)
    assert verify_response(device, challenge) is True

    tampered = copy.deepcopy(challenge)
    tampered["sig_hex"] = (tampered["sig_hex"][:-1] + ("0" if tampered["sig_hex"][-1] != "0" else "1"))
    assert verify_response(device, tampered) is False


@settings(max_examples=120, deadline=None)
@given(st.text(min_size=0, max_size=200))
def test_rth_empty_transcript_boundary_and_hash_shape(transcript: str) -> None:
    # Project Echo 不変原則：生音声保存なしで監査可能性を確保する
    snap = compute_rth(transcript)
    assert len(snap["robust_hash_hex"]) == 16
    assert all(ch in "0123456789abcdef" for ch in snap["robust_hash_hex"])

    empty = compute_rth("")
    assert empty["hash_hex"] == ""
    assert empty["robust_hash_hex"] == "0" * 16
