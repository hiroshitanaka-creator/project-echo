"""
Multi-Device Boundary Adapters for Project Echo

Why this exists:
    Different device form factors have fundamentally different I/O constraints.
    The same Echo responsibility boundary contract (candidate set + evidence
    + responsibility boundary) must hold on ALL devices, but confirmation
    mechanisms must adapt to each device's hardware capabilities.

    声で指示するだけのデバイスに「ダブルタップ」を要求しても意味がない。
    しかし「高リスクは必ず人間確認」という不変原則は、どのデバイスでも守られなければならない。

Device catalogue (all built on voice_boundary semantics):
    SmartSpeakerBoundary  → ambient room speaker (no touch, shared public space)
    SmartWatchBoundary    → wrist wearable (haptic tap + tiny screen)
    ARGlassesBoundary     → heads-up display (gaze confirmation + audio hybrid)

Invariants (non-breakable across ALL devices — AGENT.md 不変原則より):
    1. high-risk intents → requires_human_confirm = True, always
    2. bias_score >= high_bias_block_threshold → execution_allowed = False, always
    3. responsibility_boundary dict always contains: device, risk, required_action,
       execution_allowed, requires_human_confirm, reasons
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from po_echo.voice_boundary import (
    HIGH_BIAS_BLOCK_THRESHOLD,
    POLICY,
    _safe_float,
    classify_risk,
)

# Extended confirm action types for multi-device support.
# voice_boundary の "none" / "double_tap" / "passphrase" / "app_confirm" に加えて
# 各デバイス固有の確認手段を追加する。
DeviceConfirm = Literal[
    "none",
    "double_tap",
    "passphrase",
    "app_confirm",
    "voice_passphrase",   # SmartSpeaker: 音声パスフレーズ（タッチ不可）
    "haptic_tap",         # SmartWatch: 振動+タップシーケンス
    "gaze_confirm",       # ARGlasses: 視線確認+音声応答
]

DeviceType = Literal["earworn", "smart_speaker", "smart_watch", "ar_glasses"]


@dataclass(frozen=True)
class DeviceBoundaryConfig:
    """Per-device confirmation policy and safety thresholds.

    Why: each device needs its own policy while sharing the same risk classification
    and the same block threshold (mechanical enforcement — not moral appeal).
    """

    device: DeviceType
    policy: dict[str, dict[str, Any]]  # risk → {required_action, requires_human_confirm}
    high_bias_block_threshold: float = HIGH_BIAS_BLOCK_THRESHOLD
    description: str = ""


# --- Device policy tables ---
# Low risk: auto-execute. Medium: device-appropriate confirmation. High: always app_confirm.
# 「高リスクはapp_confirm固定」で責任境界を機械的に担保する。

_SMART_SPEAKER_POLICY: dict[str, dict[str, Any]] = {
    "low": {"required_action": "none", "requires_human_confirm": False},
    # スマートスピーカーはタッチ不可 → voice passphrase で確認
    "medium": {"required_action": "voice_passphrase", "requires_human_confirm": True},
    # 高リスクはアプリ確認必須（スピーカーだけでは承認不可）
    "high": {"required_action": "app_confirm", "requires_human_confirm": True},
}

_SMART_WATCH_POLICY: dict[str, dict[str, Any]] = {
    "low": {"required_action": "none", "requires_human_confirm": False},
    # スマートウォッチはハプティクス+タップで確認可能
    "medium": {"required_action": "haptic_tap", "requires_human_confirm": True},
    "high": {"required_action": "app_confirm", "requires_human_confirm": True},
}

_AR_GLASSES_POLICY: dict[str, dict[str, Any]] = {
    "low": {"required_action": "none", "requires_human_confirm": False},
    # ARグラスは視線確認でオーバーレイ表示しつつ音声応答で承認
    "medium": {"required_action": "gaze_confirm", "requires_human_confirm": True},
    "high": {"required_action": "app_confirm", "requires_human_confirm": True},
}


DEVICE_CONFIGS: dict[DeviceType, DeviceBoundaryConfig] = {
    "earworn": DeviceBoundaryConfig(
        device="earworn",
        policy=POLICY,  # voice_boundary の既存ポリシーをそのまま使用（非破壊）
        description="Sweetpea-style earworn device (voice + tap). Reference implementation.",
    ),
    "smart_speaker": DeviceBoundaryConfig(
        device="smart_speaker",
        policy=_SMART_SPEAKER_POLICY,
        high_bias_block_threshold=0.5,  # 共有空間のため bias 閾値を厳しく
        description="Ambient room speaker. No touch, shared space → stricter bias gate.",
    ),
    "smart_watch": DeviceBoundaryConfig(
        device="smart_watch",
        policy=_SMART_WATCH_POLICY,
        description="Wrist wearable with haptic tap + tiny screen.",
    ),
    "ar_glasses": DeviceBoundaryConfig(
        device="ar_glasses",
        policy=_AR_GLASSES_POLICY,
        description="Heads-up display. Gaze + audio hybrid confirmation.",
    ),
}


@dataclass(frozen=True)
class DeviceBoundaryDecision:
    """Device-aware responsibility boundary decision.

    Extends VoiceBoundaryDecision with device type context.
    All fields from VoiceBoundaryDecision are preserved for audit compatibility.
    """

    device: DeviceType
    risk: str
    required_action: str
    execution_allowed: bool
    requires_human_confirm: bool
    reasons: list[str]

    def to_responsibility_boundary(self) -> dict[str, Any]:
        """Return canonical responsibility_boundary dict for Echo audit output.

        All device adapters emit the same contract format so downstream auditors
        can verify compliance without device-specific parsing logic.
        """
        return {
            "channel": "audio",
            "device": self.device,
            "risk": self.risk,
            "required_action": self.required_action,
            "execution_allowed": self.execution_allowed,
            "requires_human_confirm": self.requires_human_confirm,
            "reasons": self.reasons,
        }

    def to_audit_payload(
        self,
        intent: str = "",
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build an Echo Mark-compatible audit payload from this device decision.

        Why this exists:
            make_echo_mark / make_echo_mark_dual expect an 'audit' dict that contains
            'responsibility_boundary'. Device decisions have no commercial-bias signals
            (they default to 0.0), but the same canonical Echo Mark v3 signing contract
            still applies — so device boundary decisions become verifiable receipts.

        The returned dict is a valid input to build_payload() / make_echo_mark().
        """
        return {
            "device_schema": "device_receipt_v1",
            "device": self.device,
            "intent": intent,
            "meta": meta or {},
            "responsibility_boundary": self.to_responsibility_boundary(),
            # Commercial-bias signals are not applicable to device decisions;
            # leave absent so build_payload defaults them to 0.0 without confusion.
        }


def decide_for_device(
    device: DeviceType,
    intent: str,
    meta: dict[str, Any] | None = None,
    bias_score: float = 0.0,
    replay_detected: bool = False,
    tamper_detected: bool = False,
) -> DeviceBoundaryDecision:
    """Determine responsibility boundary for any registered device.

    Args:
        device: Device type from DEVICE_CONFIGS.
        intent: Intent category (e.g., "payment", "booking", "search").
        meta: Optional metadata (e.g., {"amount": 10000}).
        bias_score: Commercial bias score [0, 1].
        replay_detected: True if RTH detected a replay attack.
        tamper_detected: True if Echo Mark tamper check failed.

    Returns:
        DeviceBoundaryDecision — always includes responsibility boundary.

    Why: centralised dispatch ensures ALL devices run through the same risk
    classification and bias block logic. Device-specific policy only affects
    the confirmation mechanism, never the block threshold.
    """
    config = DEVICE_CONFIGS[device]
    risk = classify_risk(intent, meta)
    # Security: fail closed for invalid/non-finite bias input to avoid bypassing
    # the bias block gate via NaN/Infinity coercion.
    safe_bias = _safe_float(bias_score, default=float("inf"), field_name="bias_score")
    pol = config.policy[risk]

    reasons = [f"risk:{risk}", f"intent:{intent}", f"device:{device}"]

    # 機械的ブロック条件（不変原則: 商業バイアスはシステムで強制排除）
    should_block = (
        safe_bias >= config.high_bias_block_threshold
        or replay_detected
        or tamper_detected
    )

    if should_block:
        block_reasons = list(reasons)
        if safe_bias >= config.high_bias_block_threshold:
            block_reasons.append(f"bias_score:{safe_bias:.3f}")
        if replay_detected:
            block_reasons.append("replay_detected")
        if tamper_detected:
            block_reasons.append("tamper_detected")
        return DeviceBoundaryDecision(
            device=device,
            risk=risk,
            required_action="app_confirm",
            execution_allowed=False,
            requires_human_confirm=True,
            reasons=block_reasons,
        )

    return DeviceBoundaryDecision(
        device=device,
        risk=risk,
        required_action=pol["required_action"],
        execution_allowed=True,
        requires_human_confirm=pol["requires_human_confirm"],
        reasons=reasons,
    )


def list_devices() -> list[DeviceType]:
    """Return the list of registered device types."""
    return list(DEVICE_CONFIGS.keys())


def get_device_description(device: DeviceType) -> str:
    """Return human-readable description of a device config."""
    return DEVICE_CONFIGS[device].description
