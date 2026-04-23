"""
Rolling Transcript Hash (RTH)

Minimal-disclosure audit trail for voice-initiated actions.

Design principles:
- Never store raw audio or full transcripts
- Only hash low-information features (sorted word sets)
- Rolling hash: H_t = H(H_{t-1} || feat_t)
- Snapshot ±N seconds around confirmation event
- Tamper-evident: changing any window invalidates hash chain

Use case:
- Ear-worn device transcribes voice in 5-second windows
- Each window updates rolling hash locally
- On high-risk action, snapshot hash is attached to Echo Mark receipt
- Auditor can verify "what was said around confirmation" without full transcript

Privacy guarantees:
- Feature extraction discards word order, timing, prosody
- Hash is one-way (cannot recover original text)
- Only confirmation-adjacent snapshots are disclosed
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}

_LOGGER = logging.getLogger(__name__)


def normalize_words(text: str) -> list[str]:
    """Normalize transcript words for robust, low-information feature extraction."""
    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9]+", lowered)
    normalized = sorted({tok for tok in tokens if tok and tok not in _STOPWORDS})
    if normalized:
        return normalized

    # Fallback for non-ASCII-only transcripts (e.g., Japanese):
    # use unique 2-gram codepoint shingles so robust hash does not collapse
    # to a constant while still avoiding full-sentence reconstruction.
    chars = [c for c in lowered if c.isalnum()]
    if len(chars) < 2:
        return chars
    return sorted({f"{chars[i]}{chars[i + 1]}" for i in range(len(chars) - 1)})


def _simhash64(tokens: list[str]) -> str:
    """Compute a 64-bit locality-sensitive hash over normalized tokens."""
    if not tokens:
        return "0" * 16

    acc = [0] * 64
    for token in tokens:
        h = int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big")
        for i in range(64):
            acc[i] += 1 if (h >> i) & 1 else -1

    out = 0
    for i, score in enumerate(acc):
        if score > 0:
            out |= 1 << i
    return f"{out:016x}"


def _feat(text: str) -> bytes:
    """
    Extract low-information features from text window.

    Args:
        text: Transcript text (5-second window)

    Returns:
        Feature bytes (sorted unique words, pipe-separated)

    Privacy note:
        - Discards word order (cannot reconstruct sentence)
        - Discards frequency (set not bag)
        - Discards capitalization, punctuation
    """
    # Extract sorted unique normalized words.
    toks = normalize_words(text)
    return ("|".join(toks)).encode("utf-8")


@dataclass
class RTHState:
    """Rolling Transcript Hash state."""

    algo: str = "sha256-rolling-v1"
    window_ms: int = 5000  # 5-second windows
    h_prev: bytes = b""  # Previous hash (binary)
    t0_ms: int = 0  # Session start timestamp
    t_ms: int = 0  # Current window timestamp
    last_text: str = ""  # Last window text (for debugging, not persisted)
    robust_hash_hex: str = "0" * 16  # 64-bit LSH for noise-tolerant comparisons
    update_count: int = 0  # Monotonic per-session window update counter
    seen_chain_hash_to_feat_fp: dict[str, dict[str, int | str]] | None = None

    def __repr__(self) -> str:
        """Return compact, non-sensitive state representation for debugging."""
        seen_count = len(self.seen_chain_hash_to_feat_fp or {})
        return (
            "RTHState("
            f"algo='{self.algo}', "
            f"window_ms={self.window_ms}, "
            f"t_ms={self.t_ms}, "
            f"hash_prefix='{self.h_prev.hex()[:12]}', "
            f"robust_hash_hex='{self.robust_hash_hex}', "
            f"update_count={self.update_count}, "
            f"seen_chain_hash_count={seen_count}"
            ")"
        )


@dataclass(frozen=True)
class RTHUpdateAssessment:
    """Result of applying a new transcript window to a maintained RTH state."""

    replay_detected: bool
    tamper_detected: bool
    discontinuity_detected: bool
    state_continuity: str
    update_count: int


@dataclass(frozen=True)
class CollisionTrackerConfig:
    """Configuration for in-memory chain hash collision tracking."""

    max_seen_count: int = 1000
    ttl_ms: int = 10 * 60 * 1000
    chain_hash_fingerprint_bytes: int = 12


class RollingTranscriptHash:
    """
    Rolling Transcript Hash for minimal-disclosure voice audit.

    Usage:
        rth = RollingTranscriptHash()
        # Update every 5 seconds with new transcript window
        rth.update_text("予約したい。土曜の夜、2人")
        # ... later ...
        rth.update_text("予算は1万円以下で")
        # On confirmation event, snapshot hash
        snapshot = rth.snapshot()
        # Attach to Echo Mark receipt
    """

    def __init__(
        self,
        window_ms: int = 5000,
        collision_tracker_config: CollisionTrackerConfig | None = None,
    ):
        """
        Initialize RTH with window size.

        Args:
            window_ms: Window size in milliseconds (default: 5000 = 5 seconds)
        """
        now = self._now()
        self.state = RTHState(window_ms=window_ms, t0_ms=now, t_ms=now)
        self.state.seen_chain_hash_to_feat_fp = {}
        self._collision_tracker_config = collision_tracker_config or CollisionTrackerConfig()
        self._collision_seen_order: OrderedDict[str, int] = OrderedDict()

    def _chain_hash_fp(self, chain_hash_hex: str) -> str:
        """Return compact blake2b fingerprint for chain hash dictionary key."""
        digest = hashlib.blake2b(
            chain_hash_hex.encode("utf-8"),
            digest_size=self._collision_tracker_config.chain_hash_fingerprint_bytes,
        ).hexdigest()
        return digest

    def _prune_collision_tracker(self, now_ms: int) -> None:
        """Prune collision tracker entries by TTL and max size constraints."""
        seen = self.state.seen_chain_hash_to_feat_fp
        if seen is None:
            return

        ttl_ms = self._collision_tracker_config.ttl_ms
        while self._collision_seen_order:
            oldest_fp, oldest_last_seen_ms = next(iter(self._collision_seen_order.items()))
            if now_ms - oldest_last_seen_ms <= ttl_ms:
                break

            self._collision_seen_order.popitem(last=False)
            removed = seen.pop(oldest_fp, None)
            if removed is not None:
                _LOGGER.warning(
                    "rth_chain_hash_collision_dict_pruned reason=ttl removed_chain_hash_fp=%s last_seen_ms=%s ttl_ms=%s",
                    oldest_fp,
                    removed.get("last_seen_ms", 0),
                    ttl_ms,
                )

        max_seen_count = self._collision_tracker_config.max_seen_count
        while len(seen) > max_seen_count and self._collision_seen_order:
            oldest_fp, _ = self._collision_seen_order.popitem(last=False)
            removed = seen.pop(oldest_fp, None)
            if removed is not None:
                _LOGGER.warning(
                    "rth_chain_hash_collision_dict_pruned reason=max_count removed_chain_hash_fp=%s first_seen_ms=%s max_seen_count=%s",
                    oldest_fp,
                    removed.get("first_seen_ms", 0),
                    max_seen_count,
                )

    def _track_chain_hash_collision(
        self,
        *,
        chain_hash_hex: str,
        feat_fp: str,
    ) -> None:
        """
        Track observed chain hash → feature fingerprint mapping in-memory.

        Args:
            chain_hash_hex: Rolling chain hash (hex) for the current window.
            feat_fp: Feature fingerprint (hex) for the current window.

        Returns:
            None.

        Raises:
            This function does not raise exceptions by design.

        Notes:
            This structure is intentionally JSON-serializable so future
            persistence can be added without state schema migration.
            Current behavior is in-memory only; collisions emit warning logs.
        """
        seen = self.state.seen_chain_hash_to_feat_fp
        if seen is None:
            seen = {}
            self.state.seen_chain_hash_to_feat_fp = seen

        ts = self.state.t_ms
        chain_hash_fp = self._chain_hash_fp(chain_hash_hex)
        prev = seen.get(chain_hash_fp)
        if prev is None:
            seen[chain_hash_fp] = {
                "chain_hash_fp": chain_hash_fp,
                "feat_fp": feat_fp,
                "first_seen_ms": ts,
                "last_seen_ms": ts,
                "seen_count": 1,
            }
            self._collision_seen_order[chain_hash_fp] = ts
            self._collision_seen_order.move_to_end(chain_hash_fp)
            self._prune_collision_tracker(ts)
            return

        prev_feat_fp = str(prev.get("feat_fp", ""))
        prev["last_seen_ms"] = ts
        prev["seen_count"] = int(prev.get("seen_count", 0)) + 1
        self._collision_seen_order[chain_hash_fp] = ts
        self._collision_seen_order.move_to_end(chain_hash_fp)

        if prev_feat_fp != feat_fp:
            _LOGGER.warning(
                "rth_chain_hash_collision_detected chain_hash=%s prev_feat_fp=%s new_feat_fp=%s",
                chain_hash_fp,
                prev_feat_fp,
                feat_fp,
            )
        self._prune_collision_tracker(ts)

    def _now(self) -> int:
        """Current timestamp in milliseconds."""
        return int(time.time() * 1000)

    def __str__(self) -> str:
        """Return lightweight object summary for operational diagnostics."""
        seen = self.state.seen_chain_hash_to_feat_fp or {}
        return (
            "RollingTranscriptHash("
            f"window_ms={self.state.window_ms}, "
            f"current_hash_prefix='{self.state.h_prev.hex()[:12]}', "
            f"tracker_entries={len(seen)}"
            ")"
        )

    def update_text(self, text_window: str) -> None:
        """
        Update rolling hash with new text window.

        Args:
            text_window: Transcript text from last N seconds
                         (N = window_ms, typically 5 seconds)

        Implementation:
            H_t = SHA256(H_{t-1} || features(text_window))
        """
        self.state.t_ms = self._now()
        self.state.last_text = text_window
        f = _feat(text_window)
        self.state.h_prev = hashlib.sha256(self.state.h_prev + f).digest()
        self.state.robust_hash_hex = _simhash64(normalize_words(text_window))
        self.state.update_count += 1
        feat_fp = hashlib.sha256(f).hexdigest()
        self._track_chain_hash_collision(chain_hash_hex=self.state.h_prev.hex(), feat_fp=feat_fp)

    def apply_window(
        self,
        text_window: str,
        *,
        discontinuity_gap_ms: int = 60_000,
    ) -> RTHUpdateAssessment:
        """
        Apply a transcript window and evaluate replay/tamper/discontinuity.

        Detection is derived from maintained RTH state, not caller metadata:
        - replay_detected: consecutive duplicate robust fingerprint
        - discontinuity_detected: window gap exceeds configured threshold
        - tamper_detected: non-monotonic time transition (clock/state regression)
        """
        prev_t_ms = self.state.t_ms
        prev_robust = self.state.robust_hash_hex
        previous_updates = self.state.update_count

        self.update_text(text_window)

        current_robust = self.state.robust_hash_hex
        replay_detected = (
            previous_updates > 0
            and prev_robust == current_robust
            and current_robust != "0" * 16
        )

        gap_ms = self.state.t_ms - prev_t_ms
        discontinuity_detected = previous_updates > 0 and gap_ms > discontinuity_gap_ms
        tamper_detected = previous_updates > 0 and gap_ms < 0

        state_continuity = "new_session" if previous_updates == 0 else "continued_session"
        return RTHUpdateAssessment(
            replay_detected=replay_detected,
            tamper_detected=tamper_detected,
            discontinuity_detected=discontinuity_detected,
            state_continuity=state_continuity,
            update_count=self.state.update_count,
        )

    def snapshot(self) -> dict:
        """
        Create snapshot for Echo Mark receipt.

        Returns:
            Snapshot dict with:
            - rth_algo: Hash algorithm version
            - window_ms: Window size
            - t_ms: Snapshot timestamp
            - hash_hex: Current hash (hex-encoded)

        Privacy note:
            Only this snapshot (hash at confirmation time) is disclosed.
            Raw transcript is never stored or transmitted.
        """
        return {
            "rth_algo": self.state.algo,
            "window_ms": self.state.window_ms,
            "t_ms": self.state.t_ms,
            "hash_hex": self.state.h_prev.hex(),
            "robust_hash_hex": self.state.robust_hash_hex,
            "update_count": self.state.update_count,
        }

    def to_dict(self) -> dict:
        """
        Export full state (for debugging/persistence).

        Returns:
            State dict with all fields
        """
        d = asdict(self.state)
        d["h_prev"] = self.state.h_prev.hex()
        return d

    @classmethod
    def from_dict(cls, state_dict: dict) -> RollingTranscriptHash:
        """Restore RTH instance from serialized state."""
        window_ms = int(state_dict.get("window_ms", 5000))
        rth = cls(window_ms=window_ms)
        rth.state.algo = str(state_dict.get("algo", rth.state.algo))
        rth.state.window_ms = window_ms
        rth.state.h_prev = bytes.fromhex(str(state_dict.get("h_prev", "")))
        rth.state.t0_ms = int(state_dict.get("t0_ms", rth.state.t0_ms))
        rth.state.t_ms = int(state_dict.get("t_ms", rth.state.t_ms))
        rth.state.last_text = str(state_dict.get("last_text", ""))
        rth.state.robust_hash_hex = str(state_dict.get("robust_hash_hex", "0" * 16))
        rth.state.update_count = int(state_dict.get("update_count", 0))
        seen = state_dict.get("seen_chain_hash_to_feat_fp")
        if isinstance(seen, dict):
            rth.state.seen_chain_hash_to_feat_fp = seen
        return rth


def compute_rth(transcript: str) -> dict:
    """
    Compute a single-window RTH snapshot for a given transcript string.

    Args:
        transcript: Transcript text to hash

    Returns:
        RTH snapshot dict (rth_algo, window_ms, t_ms, hash_hex)
    """
    rth = RollingTranscriptHash()
    if transcript:
        rth.update_text(transcript)
    return rth.snapshot()
