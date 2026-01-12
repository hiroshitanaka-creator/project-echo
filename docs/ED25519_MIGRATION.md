# Ed25519 Migration Design (Public-Key Signatures)

**Version**: 1.0
**Last Updated**: 2026-01-12

## Problem Statement

HMAC-SHA256 is **symmetric cryptography** → requires shared secret → cannot do public verification.

**What we need**:
- ✅ Third parties can verify signatures without secret access
- ✅ Public key distribution is safe (no forgery risk)
- ✅ Private key never leaves issuer's system
- ✅ Backward compatibility during transition

**Solution**: Ed25519 digital signatures (asymmetric cryptography)

---

## Ed25519 Overview

### Why Ed25519?

| Property | Value |
|----------|-------|
| **Algorithm** | EdDSA (Edwards-curve Digital Signature Algorithm) |
| **Curve** | Curve25519 |
| **Security level** | ~128-bit (equivalent to RSA-3072) |
| **Signature size** | 64 bytes (128 hex chars) |
| **Public key size** | 32 bytes (64 hex chars) |
| **Private key size** | 32 bytes (64 hex chars) |
| **Performance** | ~50k signatures/sec, ~20k verifications/sec |
| **Deterministic** | Yes (no nonce needed) |

### Advantages over RSA/ECDSA

- **Faster**: 10x faster than RSA-2048
- **Smaller keys**: 32 bytes vs 256 bytes (RSA-2048)
- **No weak keys**: All 32-byte strings are valid private keys
- **Timing-attack resistant**: Constant-time operations
- **No RNG failures**: Deterministic signatures (no k-reuse vulnerability)

### Python Implementation

```python
# Using PyNaCl (libsodium binding)
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder

# Generate keypair
private_key = SigningKey.generate()
public_key = private_key.verify_key

# Sign
signature = private_key.sign(message).signature

# Verify (anyone with public key can do this)
public_key.verify(message, signature)  # Raises exception if invalid
```

---

## Echo Mark v3 Schema (Ed25519)

### Badge Structure

```json
{
  "version": 3,
  "verification_method": "Ed25519",
  "key_id": "v1",
  "public_key": "a3f5c9d2e1b4f8a7c6d5e9f2a1b8c7d4e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8",
  "issued_at": "2026-01-12T10:30:00Z",
  "payload": {
    "label": "ECHO_VERIFIED",
    "bias_original": 0.85,
    "bias_final": 0.35,
    "merchants_original": 1,
    "merchants_final": 4,
    "execution_allowed": true,
    "requires_human_confirm": false,
    "ai_recommends": "allow",
    "reasons": ["bias_reduced", "diversity_enforced"]
  },
  "payload_hash": "a3eb1830f13d3e908229a0a6f9ff0889e890dc1055611db1951ae051e1263fdc",
  "signature": "e5f2a9b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8c1d4e7f0a3b6c9d2e5f8a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8c1d4e7f0a3b6c9d2e5f8"
}
```

**Key changes from v2**:
- `verification_method`: `"Ed25519"` (was `"HMAC-SHA256"`)
- `public_key`: Added (32 bytes hex-encoded)
- `signature`: Now 64 bytes (was 32 bytes for HMAC)

---

## Key Management

### Key Generation

```python
import os
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

def generate_keypair(key_id: str) -> dict:
    """
    Generate Ed25519 keypair.

    Returns:
        {
            "key_id": "v1",
            "private_key": "hex-encoded 32 bytes",
            "public_key": "hex-encoded 32 bytes",
            "created_at": "ISO8601 timestamp"
        }
    """
    # Generate private key
    private_key = SigningKey.generate()

    # Derive public key
    public_key = private_key.verify_key

    return {
        "key_id": key_id,
        "private_key": private_key.encode(HexEncoder).decode(),
        "public_key": public_key.encode(HexEncoder).decode(),
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

# Usage
keypair = generate_keypair("v1")
print(f"Public key:  {keypair['public_key']}")
print(f"Private key: {keypair['private_key']}")  # NEVER SHARE THIS
```

### Private Key Storage

**Requirements**:
- ❌ NEVER commit to git
- ❌ NEVER log or print
- ❌ NEVER send over network (except to secure vault)
- ✅ Store in encrypted vault (AWS Secrets Manager, HashiCorp Vault, etc.)
- ✅ Environment variable for local dev only
- ✅ File permissions: `chmod 600` (owner read/write only)

**Development**:
```bash
# Generate keypair
python tools/generate_keypair.py --key-id v1 --output .keys/

# .keys/ structure:
# .keys/v1.private.key  (chmod 600, in .gitignore)
# .keys/v1.public.key   (safe to share)

# Load from environment
export ECHO_MARK_PRIVATE_KEY="$(cat .keys/v1.private.key)"
export ECHO_MARK_PUBLIC_KEY="$(cat .keys/v1.public.key)"
```

**Production**:
```python
import boto3

def load_private_key_from_vault(key_id: str) -> SigningKey:
    """Load private key from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=f"echo-mark/{key_id}/private")
    private_key_hex = response['SecretString']
    return SigningKey(private_key_hex, encoder=HexEncoder)
```

### Public Key Distribution

Public keys are **safe to distribute widely**:

1. **In badge JSON** (recommended):
   ```json
   {
     "version": 3,
     "public_key": "a3f5c9d2...",
     ...
   }
   ```

2. **Public key registry** (optional):
   ```json
   // https://echo.example.com/.well-known/echo-public-keys.json
   {
     "keys": [
       {
         "key_id": "v1",
         "public_key": "a3f5c9d2e1b4f8a7c6d5e9f2a1b8c7d4e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8",
         "algorithm": "Ed25519",
         "created_at": "2026-01-01T00:00:00Z",
         "expires_at": "2027-01-01T00:00:00Z",
         "status": "active"
       },
       {
         "key_id": "v2",
         "public_key": "b4g6d0e2f5c9g1b8d7f0e3a2c5f8b1e4g7a0d3f6c9e2b5g8a1d4f7c0e3b6a9",
         "algorithm": "Ed25519",
         "created_at": "2026-06-01T00:00:00Z",
         "expires_at": null,
         "status": "active"
       }
     ]
   }
   ```

3. **DNS TXT record** (for advanced use):
   ```
   _echo-mark.example.com. TXT "v=echo1 k=v1 alg=ed25519 pub=a3f5c9d2..."
   ```

---

## Signature Generation (Issuer Side)

### Implementation

```python
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder
import hashlib
import json

def make_echo_mark_ed25519(
    audit: dict,
    private_key_hex: str,
    key_id: str,
) -> dict:
    """
    Create Echo Mark badge with Ed25519 signature.

    Args:
        audit: Audit result from diversify_with_mmr()
        private_key_hex: Private key (hex-encoded 32 bytes)
        key_id: Key identifier (e.g., "v1")

    Returns:
        Echo Mark badge (dict)
    """
    # Load private key
    private_key = SigningKey(private_key_hex, encoder=HexEncoder)
    public_key = private_key.verify_key

    # Build payload
    boundary = audit["responsibility_boundary"]
    payload = {
        "label": determine_label(boundary),
        "bias_original": audit["commercial_bias_original"]["overall_bias_score"],
        "bias_final": audit["commercial_bias_final"]["overall_bias_score"],
        "merchants_original": len(audit["diversity_report_original"]["merchants"]),
        "merchants_final": len(audit["diversity_report_final"]["merchants"]),
        "execution_allowed": boundary["execution_allowed"],
        "requires_human_confirm": boundary["requires_human_confirm"],
        "ai_recommends": boundary["ai_recommends"],
        "reasons": boundary["reasons"],
    }

    # Canonical JSON (stable serialization)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    # Hash payload (SHA-256)
    payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # Sign the hash (Ed25519)
    signed = private_key.sign(payload_hash.encode("utf-8"))
    signature = signed.signature.hex()

    # Build badge
    badge = {
        "version": 3,
        "verification_method": "Ed25519",
        "key_id": key_id,
        "public_key": public_key.encode(HexEncoder).decode(),
        "issued_at": datetime.utcnow().isoformat() + "Z",
        "payload": payload,
        "payload_hash": payload_hash,
        "signature": signature,
    }

    return badge
```

---

## Signature Verification (Anyone Can Do This)

### Implementation

```python
from nacl.signing import VerifyKey
from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError
import hashlib
import json

def verify_echo_mark_ed25519(badge: dict) -> dict:
    """
    Verify Echo Mark badge with Ed25519 signature.

    Anyone can call this function - no secret needed!

    Returns:
        {
            "status": "VERIFIED" | "INVALID",
            "reason": str,
            "checks": {
                "hash_integrity": bool,
                "signature_valid": bool,
                "schema_valid": bool,
            }
        }
    """
    try:
        # Extract fields
        public_key_hex = badge["public_key"]
        payload = badge["payload"]
        payload_hash = badge["payload_hash"]
        signature_hex = badge["signature"]

        # Check 1: Hash integrity
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        hash_ok = (payload_hash == expected_hash)

        if not hash_ok:
            return {
                "status": "INVALID",
                "reason": "payload_tampered",
                "checks": {
                    "hash_integrity": False,
                    "signature_valid": False,
                    "schema_valid": True,
                }
            }

        # Check 2: Signature verification
        public_key = VerifyKey(public_key_hex, encoder=HexEncoder)
        signature = bytes.fromhex(signature_hex)

        try:
            public_key.verify(payload_hash.encode("utf-8"), signature)
            signature_ok = True
        except BadSignatureError:
            signature_ok = False

        if not signature_ok:
            return {
                "status": "INVALID",
                "reason": "signature_invalid",
                "checks": {
                    "hash_integrity": True,
                    "signature_valid": False,
                    "schema_valid": True,
                }
            }

        # Check 3: Schema validation (optional but recommended)
        schema_ok = validate_echo_mark_schema(badge)

        if not schema_ok:
            return {
                "status": "INVALID",
                "reason": "schema_invalid",
                "checks": {
                    "hash_integrity": True,
                    "signature_valid": True,
                    "schema_valid": False,
                }
            }

        # All checks passed!
        return {
            "status": "VERIFIED",
            "reason": "signature_valid",
            "checks": {
                "hash_integrity": True,
                "signature_valid": True,
                "schema_valid": True,
            },
            "note": "Cryptographically verified with Ed25519 public key."
        }

    except Exception as e:
        return {
            "status": "INVALID",
            "reason": f"verification_error: {str(e)}",
            "checks": {
                "hash_integrity": False,
                "signature_valid": False,
                "schema_valid": False,
            }
        }
```

**Key insight**: No secret needed! Anyone with the badge can verify it.

---

## Migration Strategy (4 Phases)

### Phase 1: HMAC Only (Current)

```python
# Issuer
badge = make_echo_mark_hmac(audit, secret="...", key_id="v1")

# Verifier (needs secret)
result = verify_echo_mark_hmac(badge, secret="...")
# Returns: VERIFIED or INVALID
```

**Limitations**:
- Third parties cannot verify without secret
- Sharing secret enables forgery

---

### Phase 2: Dual Signature (Transition)

Generate **both** HMAC and Ed25519 signatures:

```python
def make_echo_mark_dual(
    audit: dict,
    hmac_secret: str,
    ed25519_private_key: str,
    key_id: str,
) -> dict:
    """Generate badge with both HMAC and Ed25519 signatures."""
    # ... (payload and hash generation)

    # HMAC signature (for backward compatibility)
    hmac_sig = hmac.new(
        hmac_secret.encode("utf-8"),
        payload_hash.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # Ed25519 signature (for public verification)
    private_key = SigningKey(ed25519_private_key, encoder=HexEncoder)
    ed25519_sig = private_key.sign(payload_hash.encode("utf-8")).signature.hex()

    badge = {
        "version": 3,
        "verification_method": "Ed25519+HMAC",  # Dual mode
        "key_id": key_id,
        "public_key": private_key.verify_key.encode(HexEncoder).decode(),
        "issued_at": datetime.utcnow().isoformat() + "Z",
        "payload": payload,
        "payload_hash": payload_hash,
        "signature": ed25519_sig,  # Primary
        "signature_hmac": hmac_sig,  # Fallback
    }

    return badge
```

**Verification**:
```python
def verify_echo_mark_dual(badge: dict, hmac_secret: str = None) -> dict:
    """Verify badge with either Ed25519 or HMAC."""
    # Try Ed25519 first (preferred)
    if "signature" in badge and "public_key" in badge:
        result = verify_echo_mark_ed25519(badge)
        if result["status"] == "VERIFIED":
            return result

    # Fallback to HMAC (if secret available)
    if hmac_secret and "signature_hmac" in badge:
        result = verify_echo_mark_hmac(badge, hmac_secret)
        if result["status"] == "VERIFIED":
            return result

    # If Ed25519 verification failed but HMAC not available
    if hmac_secret is None:
        return {
            "status": "UNVERIFIED",
            "reason": "no_secret_for_hmac_fallback",
            ...
        }

    return {"status": "INVALID", ...}
```

**Duration**: 6-12 months (transition period)

---

### Phase 3: Ed25519 Primary, HMAC Deprecated

Stop generating HMAC signatures for new badges:

```python
# Issuer (new badges)
badge = make_echo_mark_ed25519(audit, private_key="...", key_id="v2")

# Verifier (handles both old and new)
if badge["version"] == 2:
    # Old badge (HMAC)
    result = verify_echo_mark_hmac(badge, secret="...")
elif badge["version"] == 3:
    # New badge (Ed25519)
    result = verify_echo_mark_ed25519(badge)
```

**Duration**: 6-12 months (deprecation period)

---

### Phase 4: Ed25519 Only (Future)

Remove HMAC support entirely:

```python
# Issuer
badge = make_echo_mark_ed25519(audit, private_key="...", key_id="v3")

# Verifier (anyone)
result = verify_echo_mark_ed25519(badge)
```

**Outcome**: Full public verification capability

---

## Security Considerations

### Key Rotation

Unlike HMAC (where key leakage requires re-signing all badges), Ed25519 allows seamless rotation:

```python
# Generate new keypair
keypair_v2 = generate_keypair("v2")

# Sign new badges with v2
badge_new = make_echo_mark_ed25519(audit, keypair_v2["private_key"], "v2")

# Old badges (v1) remain valid
# Verifier checks key_id and uses corresponding public key
```

**Best practice**: Rotate keys annually, keep old public keys in registry for verification.

---

### Replay Attack Mitigation

Even with Ed25519, replay attacks are possible (reusing old valid badges).

**Mitigation**:
1. **Timestamp validation**: Reject badges older than threshold
   ```python
   if parse_timestamp(badge["issued_at"]) < now - timedelta(days=30):
       return {"status": "EXPIRED", ...}
   ```

2. **Nonce (optional)**: Include unique ID in payload
   ```python
   payload = {
       "nonce": uuid.uuid4().hex,  # Prevents replay
       ...
   }
   ```

3. **Context binding**: Include request context in payload
   ```python
   payload = {
       "user_id": "...",
       "session_id": "...",
       ...
   }
   ```

---

### Key Compromise Response

**If private key leaks**:

1. **Immediate**:
   - Revoke compromised key (mark as `"status": "revoked"` in public key registry)
   - Generate new keypair with new key_id
   - Update production systems to use new key

2. **Within 24 hours**:
   - Audit all badges signed with compromised key
   - Re-sign critical badges with new key

3. **Within 7 days**:
   - Notify users about key rotation
   - Publish post-mortem (if needed)

**Key insight**: Ed25519 key compromise does **not** allow forging past signatures (unlike HMAC secret leakage).

---

## Performance Comparison

| Operation | HMAC-SHA256 | Ed25519 | Overhead |
|-----------|-------------|---------|----------|
| **Key generation** | N/A (secret is arbitrary) | ~1ms | - |
| **Signing** | ~0.02ms | ~0.02ms | 0% |
| **Verification** | ~0.02ms | ~0.05ms | +150% |
| **Signature size** | 32 bytes | 64 bytes | +100% |
| **Key size (public)** | N/A | 32 bytes | N/A |

**Conclusion**: Ed25519 has negligible performance overhead in practice.

---

## Implementation Checklist

### Phase 2 (Dual Signature) - Next Steps

- [ ] Add PyNaCl dependency (`pip install pynacl`)
- [ ] Implement `generate_keypair()` tool
- [ ] Implement `make_echo_mark_ed25519()`
- [ ] Implement `verify_echo_mark_ed25519()`
- [ ] Implement `make_echo_mark_dual()` (HMAC + Ed25519)
- [ ] Implement `verify_echo_mark_dual()` (try Ed25519 first, fallback to HMAC)
- [ ] Add Ed25519 tests (signature validity, tampering detection, key rotation)
- [ ] Update CLI to support both verification methods
- [ ] Create `.keys/` directory structure (in .gitignore)
- [ ] Document key management in README
- [ ] Add public key registry JSON file (optional)

### Phase 3 (Deprecation) - Future

- [ ] Update all badge generation to use Ed25519 by default
- [ ] Add deprecation warnings for HMAC verification
- [ ] Audit old HMAC-signed badges
- [ ] Publish migration guide for third parties

### Phase 4 (Ed25519 Only) - Future

- [ ] Remove HMAC code from codebase
- [ ] Update schema to require `version: 3`
- [ ] Archive old public keys in registry

---

## Example: End-to-End Flow

### 1. Generate Keypair (One-time)

```bash
python tools/generate_keypair.py --key-id v1 --output .keys/
# Created: .keys/v1.private.key (KEEP SECRET)
# Created: .keys/v1.public.key (safe to share)
```

### 2. Sign Badge (Issuer)

```python
# Load private key
with open(".keys/v1.private.key") as f:
    private_key = f.read().strip()

# Run audit
audit = diversify_with_mmr(...)

# Sign with Ed25519
badge = make_echo_mark_ed25519(audit, private_key, "v1")

# Save badge
with open("runs/demo.badge.json", "w") as f:
    json.dump(badge, f, indent=2)
```

### 3. Verify Badge (Anyone)

```python
# Load badge
with open("runs/demo.badge.json") as f:
    badge = json.load(f)

# Verify (no secret needed!)
result = verify_echo_mark_ed25519(badge)

if result["status"] == "VERIFIED":
    print("✅ ECHO_VERIFIED (cryptographically verified)")
    print(f"   Public key: {badge['public_key'][:16]}...")
    print(f"   Bias: {badge['payload']['bias_final']:.2f}")
else:
    print(f"❌ ECHO_INVALID ({result['reason']})")
```

**Key insight**: Verifier doesn't need access to private key or any secret. Public key in badge is sufficient.

---

## Comparison: HMAC vs Ed25519

| Aspect | HMAC-SHA256 | Ed25519 |
|--------|-------------|---------|
| **Public verification** | ❌ No (requires secret) | ✅ Yes (public key) |
| **Key distribution** | ❌ Risky (secret must be protected) | ✅ Safe (public key can be shared) |
| **Third-party audit** | ❌ Impossible | ✅ Possible |
| **Forgery after key leak** | ❌ All badges can be forged | ✅ Only future badges (past signatures remain valid) |
| **Key rotation** | ⚠️  Requires re-signing all badges | ✅ Simple (old public keys remain valid) |
| **Performance** | ✅ Fast (~0.02ms) | ✅ Fast (~0.05ms) |
| **Implementation** | ✅ Simple (stdlib only) | ⚠️  Requires crypto library (PyNaCl) |
| **Use case** | Internal/trusted systems | Public/social-scale deployment |

---

## Threat Model Updates

With Ed25519, the threat model improves:

### Before (HMAC):
- **Threat**: Secret leakage → all badges forgeable
- **Threat**: Third parties cannot verify → trust must be centralized

### After (Ed25519):
- **Mitigation**: Private key leakage → only future badges forgeable (past signatures remain valid)
- **Mitigation**: Anyone can verify → trust is decentralized

### Remaining Threats:
- **Replay attacks**: Old valid badges reused → mitigate with timestamp validation
- **Key compromise**: Attacker signs fake badges with stolen key → mitigate with key rotation and revocation
- **Social engineering**: Users trust forged badges without verification → mitigate with clear UI/UX

---

## References

- **Ed25519**: [RFC 8032](https://tools.ietf.org/html/rfc8032)
- **PyNaCl**: [https://pynacl.readthedocs.io/](https://pynacl.readthedocs.io/)
- **Curve25519**: [https://cr.yp.to/ecdh.html](https://cr.yp.to/ecdh.html)
- **libsodium**: [https://doc.libsodium.org/](https://doc.libsodium.org/)

---

**Next**: Implement Phase 2 (Dual Signature) with `tools/generate_keypair.py` and updated `po_echo/echo_mark.py`.
