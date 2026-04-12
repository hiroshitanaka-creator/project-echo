"""
Hardware-Signed Audit Log — append-only transparent log with device attestation.

Implementation of the "minimum viable" design from the transparent-log proposal:

    Normalize → leaf_hash → hardware-key sign → local append →
    batch commit (Merkle root + sign STH) → issue inclusion receipts

Privacy model:
    Raw content is NEVER stored.  Each append() computes
    HMAC-SHA256(per-log-salt, canonical_json(content)) and stores only that
    digest.  Without the salt, third-party verifiers cannot reverse a leaf hash
    to recover the original content.  The content owner retains the salt and
    can later call verify_content_in_receipt() to prove inclusion.

Hardware key abstraction (HardwareKeyProvider protocol):
    SoftwareKeyProvider — Ed25519 via PyNaCl.  Identical interface; no hardware.
    iOS production    — CryptoKit SecureEnclave.P256.Signing (via Python-ObjC bridge).
    Android production — Android Keystore + Key Attestation (via Chaquopy JNI).
    Server / HSM      — python-pkcs11 or Cloud KMS (GCP/AWS/Azure) adapter.

Verification flow (third party, zero internal dependencies):
    1. Obtain the log operator's published public_key_hex.
    2. Receive an InclusionReceipt from the log.
    3. Call HardwareAuditLog.verify_receipt(receipt, public_key_hex) → bool.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Any, Protocol, runtime_checkable

from po_echo.merkle_log import (
    compute_inclusion_proof_from_leaf_hashes,
    compute_root_from_leaf_hashes,
    leaf_hash,
    verify_inclusion_proof,
)

try:
    from nacl.encoding import HexEncoder
    from nacl.exceptions import BadSignatureError
    from nacl.signing import SigningKey, VerifyKey

    NACL_AVAILABLE = True
except ImportError:  # pragma: no cover — depends on environment
    NACL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Hardware key provider interface
# ---------------------------------------------------------------------------


@runtime_checkable
class HardwareKeyProvider(Protocol):
    """Structural protocol for a hardware (or simulated) signing key.

    Implementations must provide the three members below.  The Protocol is
    runtime-checkable so isinstance() can be used in guards.

    iOS (Secure Enclave):
        Wrap SecureEnclave.P256.Signing.PrivateKey.signature(for:) in a
        Python-ObjC or ctypes/cffi adapter that returns the raw DER bytes.

    Android (Hardware-backed Keystore):
        Wrap Signature.getInstance("SHA256withECDSA").sign() via Chaquopy JNI;
        return raw signature bytes.  Use Key Attestation to publish the
        attestation certificate alongside public_key_hex().

    WebAuthn / Passkey:
        Use the FIDO2 authenticator's sign() output; public_key_hex() may
        return the COSE-encoded public key instead of raw hex.
    """

    @property
    def key_id(self) -> str:
        """Stable identifier for this key (e.g. 'se-p256-device42')."""
        ...

    def sign(self, message: bytes) -> bytes:
        """Sign *message*; return raw signature bytes."""
        ...

    def public_key_hex(self) -> str:
        """Hex-encoded public key for out-of-band publication by the log operator."""
        ...


class SoftwareKeyProvider:
    """Ed25519 software key provider that simulates iOS Secure Enclave / Android TEE.

    The signing API is identical to production hardware providers, so all
    verification code (including verify_receipt) works without modification.

    Production swap guide:
        iOS:     Replace sign() with CryptoKit SecureEnclave signing call.
        Android: Replace sign() with Android KeyStore ECDSA/Ed25519 signing.
        HSM:     Replace sign() with python-pkcs11 or Cloud KMS sign call.
    """

    def __init__(self, private_key_hex: str, key_id: str = "sw-ed25519-v1") -> None:
        if not NACL_AVAILABLE:
            raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")
        self._private_key_hex = private_key_hex
        self._key_id = key_id

    @classmethod
    def generate(cls, key_id: str = "sw-ed25519-v1") -> "SoftwareKeyProvider":
        """Generate a new ephemeral Ed25519 key pair."""
        if not NACL_AVAILABLE:
            raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")
        raw_hex: str = SigningKey.generate().encode(HexEncoder).decode()
        return cls(raw_hex, key_id=key_id)

    @property
    def key_id(self) -> str:
        return self._key_id

    def sign(self, message: bytes) -> bytes:
        sk = SigningKey(self._private_key_hex.encode(), encoder=HexEncoder)
        return bytes(sk.sign(message).signature)

    def public_key_hex(self) -> str:
        sk = SigningKey(self._private_key_hex.encode(), encoder=HexEncoder)
        return sk.verify_key.encode(HexEncoder).decode()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class AuditLogEntry:
    """One immutable, hardware-signed entry in the append-only log."""

    index: int
    timestamp_ms: int
    leaf_hash_hex: str   # leaf_hash(content_digest) — RFC 6962 leaf node
    device_sig_hex: str  # Ed25519(canonical_entry_json, hardware_key)
    key_id: str
    schema_version: str = "hardware_audit_log_entry_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SignedTreeHead:
    """RFC 6962-style Signed Tree Head (STH) for a committed Merkle tree."""

    tree_size: int
    timestamp_ms: int
    root_hash_hex: str
    sig_hex: str   # Ed25519(canonical_sth_json, hardware_key)
    key_id: str
    schema_version: str = "hardware_audit_log_sth_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InclusionReceipt:
    """Inclusion receipt: STH + Merkle audit path for one log entry.

    Third-party verifiers only need this receipt and the log operator's
    published public key to confirm "this leaf is in this tree".
    """

    sth: SignedTreeHead
    leaf_index: int
    leaf_hash_hex: str
    audit_path: list[str]  # hex-encoded sibling hashes, leaf-to-root order
    schema_version: str = "hardware_audit_log_receipt_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Main log class
# ---------------------------------------------------------------------------


class HardwareAuditLog:
    """Append-only, hardware-signed Merkle transparent log.

    Minimal flow (per the design spec):
        log = HardwareAuditLog(SoftwareKeyProvider.generate())
        entry = log.append({"label": "ECHO_VERIFIED", "bias_final": 0.05})
        sth   = log.commit()
        receipt = log.get_receipt(entry.index)
        ok = HardwareAuditLog.verify_receipt(receipt, provider.public_key_hex())
    """

    def __init__(
        self,
        key_provider: HardwareKeyProvider,
        *,
        salt: bytes | None = None,
    ) -> None:
        """
        Args:
            key_provider: Signing key (hardware or software).
            salt:         Per-log random secret for HMAC privacy protection.
                          Auto-generated (32 bytes) if not supplied.
        """
        self._key_provider = key_provider
        self._salt: bytes = salt if salt is not None else secrets.token_bytes(32)
        self._entries: list[AuditLogEntry] = []
        self._committed_sth: SignedTreeHead | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def salt(self) -> bytes:
        """Per-log HMAC salt.

        The content owner must retain this to later prove content inclusion via
        verify_content_in_receipt().  It should NOT be published alongside the
        log; keep it with the original content.
        """
        return self._salt

    def append(self, content: dict[str, Any]) -> AuditLogEntry:
        """Append *content* to the log as a new signed leaf.

        Privacy: only HMAC-SHA256(salt, canonical_json(content)) is stored.
        The raw *content* dict is never persisted or transmitted.

        Args:
            content: Arbitrary JSON-serialisable dict (Echo Mark payload,
                     voice-action record, etc.).

        Returns:
            The new AuditLogEntry (immutable after creation).
        """
        index = len(self._entries)
        timestamp_ms = int(time.time() * 1000)

        digest = self._content_digest(content)
        lh_hex = leaf_hash(digest).hex()

        sig_hex = self._key_provider.sign(
            self._entry_sign_msg(index, timestamp_ms, lh_hex)
        ).hex()

        entry = AuditLogEntry(
            index=index,
            timestamp_ms=timestamp_ms,
            leaf_hash_hex=lh_hex,
            device_sig_hex=sig_hex,
            key_id=self._key_provider.key_id,
        )
        self._entries.append(entry)
        return entry

    def commit(self) -> SignedTreeHead:
        """Compute the Merkle root over all current entries and sign a new STH.

        Multiple calls are allowed; each produces a new STH for the current
        tree size.  Receipts reference the specific STH active at call time.

        Raises:
            ValueError: if the log has no entries yet.
        """
        if not self._entries:
            raise ValueError("Cannot commit an empty log")

        lh_bytes = [bytes.fromhex(e.leaf_hash_hex) for e in self._entries]
        root_hex = compute_root_from_leaf_hashes(lh_bytes).hex()
        ts = int(time.time() * 1000)

        sig_hex = self._key_provider.sign(
            _sth_sign_msg(len(self._entries), ts, root_hex)
        ).hex()

        sth = SignedTreeHead(
            tree_size=len(self._entries),
            timestamp_ms=ts,
            root_hash_hex=root_hex,
            sig_hex=sig_hex,
            key_id=self._key_provider.key_id,
        )
        self._committed_sth = sth
        return sth

    def get_receipt(self, leaf_index: int) -> InclusionReceipt:
        """Return an inclusion receipt for the entry at *leaf_index*.

        The receipt contains the current STH and the Merkle audit path; any
        third party can verify it with only the log's public key.

        Raises:
            RuntimeError: if commit() has not been called.
            IndexError:   if *leaf_index* is out of range.
        """
        if self._committed_sth is None:
            raise RuntimeError("Call commit() before get_receipt()")
        n = len(self._entries)
        if leaf_index < 0 or leaf_index >= n:
            raise IndexError(f"leaf_index {leaf_index} out of range [0, {n})")

        lh_bytes = [bytes.fromhex(e.leaf_hash_hex) for e in self._entries]
        proof = compute_inclusion_proof_from_leaf_hashes(lh_bytes, leaf_index)

        return InclusionReceipt(
            sth=self._committed_sth,
            leaf_index=leaf_index,
            leaf_hash_hex=self._entries[leaf_index].leaf_hash_hex,
            audit_path=[h.hex() for h in proof],
        )

    def entries(self) -> list[AuditLogEntry]:
        """Return a shallow copy of all entries (read-only view)."""
        return list(self._entries)

    # ------------------------------------------------------------------
    # Static verification helpers (zero instance dependencies)
    # ------------------------------------------------------------------

    @staticmethod
    def verify_receipt(
        receipt: InclusionReceipt,
        public_key_hex: str,
    ) -> bool:
        """Verify an inclusion receipt produced by get_receipt().

        Checks (in order):
            1. STH signature is valid for *public_key_hex*.
            2. Merkle audit path reconstructs the STH root hash.

        Args:
            receipt:        InclusionReceipt from get_receipt().
            public_key_hex: Hex-encoded Ed25519 public key of the log operator.

        Returns:
            True only if both checks pass; False otherwise.

        Raises:
            RuntimeError: if PyNaCl is not installed.
        """
        if not NACL_AVAILABLE:
            raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")

        sth = receipt.sth
        try:
            vk = VerifyKey(public_key_hex.encode(), encoder=HexEncoder)
            vk.verify(
                _sth_sign_msg(sth.tree_size, sth.timestamp_ms, sth.root_hash_hex),
                bytes.fromhex(sth.sig_hex),
            )
        except Exception:
            return False

        return verify_inclusion_proof(
            root=bytes.fromhex(sth.root_hash_hex),
            leaf_hash_val=bytes.fromhex(receipt.leaf_hash_hex),
            index=receipt.leaf_index,
            proof=[bytes.fromhex(h) for h in receipt.audit_path],
            tree_size=sth.tree_size,
        )

    @staticmethod
    def verify_content_in_receipt(
        receipt: InclusionReceipt,
        content: dict[str, Any],
        salt: bytes,
        public_key_hex: str,
    ) -> bool:
        """Verify that *content* is the exact value committed in *receipt*.

        The content owner provides the original dict and the per-log salt to
        prove "this specific content is in this verified Merkle tree".

        Args:
            receipt:        InclusionReceipt from get_receipt().
            content:        The original content dict passed to append().
            salt:           The per-log salt (HardwareAuditLog.salt).
            public_key_hex: Hex-encoded Ed25519 public key of the log operator.

        Returns:
            True only if the content's derived leaf hash matches the receipt
            AND the receipt itself is cryptographically valid.
        """
        canonical = json.dumps(
            content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        digest = _hmac.new(salt, canonical.encode("utf-8"), hashlib.sha256).digest()
        expected_lh_hex = leaf_hash(digest).hex()
        if receipt.leaf_hash_hex != expected_lh_hex:
            return False
        return HardwareAuditLog.verify_receipt(receipt, public_key_hex)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _content_digest(self, content: dict[str, Any]) -> bytes:
        """HMAC-SHA256(self._salt, canonical_json(content)) — privacy veil."""
        canonical = json.dumps(
            content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return _hmac.new(self._salt, canonical.encode("utf-8"), hashlib.sha256).digest()

    def _entry_sign_msg(
        self, index: int, timestamp_ms: int, leaf_hash_hex: str
    ) -> bytes:
        return json.dumps(
            {
                "index": index,
                "leaf_hash_hex": leaf_hash_hex,
                "schema_version": "hardware_audit_log_entry_v1",
                "timestamp_ms": timestamp_ms,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


# ---------------------------------------------------------------------------
# Module-level helper (used by both instance and static methods)
# ---------------------------------------------------------------------------


def _sth_sign_msg(tree_size: int, timestamp_ms: int, root_hash_hex: str) -> bytes:
    """Canonical signing input for a Signed Tree Head."""
    return json.dumps(
        {
            "root_hash_hex": root_hash_hex,
            "schema_version": "hardware_audit_log_sth_v1",
            "timestamp_ms": timestamp_ms,
            "tree_size": tree_size,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
