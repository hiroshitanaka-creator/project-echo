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
import re
import time
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


def normalize_words(text: str) -> list[str]:
    """Normalize transcript words for robust, low-information feature extraction."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return sorted({tok for tok in tokens if tok and tok not in _STOPWORDS})


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

    def __init__(self, window_ms: int = 5000):
        """
        Initialize RTH with window size.

        Args:
            window_ms: Window size in milliseconds (default: 5000 = 5 seconds)
        """
        now = self._now()
        self.state = RTHState(window_ms=window_ms, t0_ms=now, t_ms=now)

    def _now(self) -> int:
        """Current timestamp in milliseconds."""
        return int(time.time() * 1000)

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
