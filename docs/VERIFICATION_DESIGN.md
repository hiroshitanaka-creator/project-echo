# Public Verification Design (HMAC Limitations & UNVERIFIED Handling)

**Version**: 1.0
**Last Updated**: 2026-01-12

## Problem Statement

Echo Mark currently uses **HMAC-SHA256** for signature, which has a fundamental limitation:

**HMAC is symmetric cryptography** → Only parties with the shared secret can verify signatures.

This means:
- ❌ Third parties **cannot independently verify** Echo Mark badges
- ❌ Public verification is **impossible** without sharing the secret
- ❌ Sharing the secret enables **anyone to forge** signatures

**Consequence**: Echo Mark can only be verified by the issuer (the system that created it), not by external auditors or users.

---

## Current Verification Flow

### 1. Trusted Verification (Secret Available)

When the verifier has access to `ECHO_MARK_SECRET`:

```python
def verify_mark(payload, payload_hash, signature, secret) -> bool:
    # Recompute hash
    canonical = canonical_json(payload)
    expected_hash = sha256_hex(canonical)

    # Hash mismatch → tampered
    if not hmac.compare_digest(payload_hash, expected_hash):
        return False

    # Recompute signature
    expected_sig = hmac_sha256_hex(secret, payload_hash)

    # Signature mismatch → forged or wrong key
    return hmac.compare_digest(signature, expected_sig)
```

**Result**: `True` (verified) or `False` (tampered/forged)

---

### 2. Untrusted Verification (Secret NOT Available)

When the verifier does **not** have the secret:

**Current behavior**: Verification fails (returns `False`)

**Problem**: This conflates two cases:
1. Badge is **tampered** (malicious)
2. Badge is **valid but unverifiable** (no secret available)

**User experience**: Both cases look the same → confusing and misleading.

---

## Design Solution: UNVERIFIED Status

### Three-State Verification Model

Instead of binary `True/False`, introduce **three states**:

| State | Meaning | Condition |
|-------|---------|-----------|
| `VERIFIED` | Signature valid, tamper-evident | Secret available + signature matches |
| `UNVERIFIED` | Signature unknown, cannot verify | Secret NOT available (third-party view) |
| `INVALID` | Signature invalid, likely tampered | Secret available + signature mismatch |

---

### Implementation Strategy

#### Option A: Graceful Degradation (Recommended)

When secret is not available, verify **structural integrity** only:

```python
def verify_mark_public(payload, payload_hash, signature) -> dict:
    """
    Public verification (no secret needed).

    Returns:
        {
            "status": "VERIFIED" | "UNVERIFIED" | "INVALID",
            "reason": str,
            "checks": {
                "hash_integrity": bool,  # payload matches payload_hash
                "signature_format": bool,  # signature is valid hex
                "schema_valid": bool,     # payload matches Echo Mark schema
            }
        }
    """
    # Check 1: Hash integrity (payload → payload_hash)
    canonical = canonical_json(payload)
    expected_hash = sha256_hex(canonical)
    hash_ok = hmac.compare_digest(payload_hash, expected_hash)

    # Check 2: Signature format (64 hex chars for SHA256)
    sig_format_ok = bool(re.match(r'^[0-9a-f]{64}$', signature))

    # Check 3: Schema validation
    schema_ok = validate_echo_mark_schema(payload)

    # Decision logic
    if not hash_ok:
        # Payload was tampered (hash mismatch)
        return {
            "status": "INVALID",
            "reason": "payload_tampered",
            "checks": {
                "hash_integrity": False,
                "signature_format": sig_format_ok,
                "schema_valid": schema_ok,
            }
        }

    if not sig_format_ok:
        # Signature format invalid
        return {
            "status": "INVALID",
            "reason": "signature_malformed",
            "checks": {
                "hash_integrity": True,
                "signature_format": False,
                "schema_valid": schema_ok,
            }
        }

    if not schema_ok:
        # Schema invalid
        return {
            "status": "INVALID",
            "reason": "schema_invalid",
            "checks": {
                "hash_integrity": True,
                "signature_format": True,
                "schema_valid": False,
            }
        }

    # All checks passed, but no secret → UNVERIFIED
    return {
        "status": "UNVERIFIED",
        "reason": "no_secret_available",
        "checks": {
            "hash_integrity": True,
            "signature_format": True,
            "schema_valid": True,
        },
        "note": "Badge structure is valid. Cryptographic signature cannot be verified without secret key. Consider using public-key signatures (Ed25519) for independent verification."
    }
```

**Trust model**:
- `VERIFIED`: Strong trust (cryptographically verified)
- `UNVERIFIED`: Weak trust (structurally valid, not cryptographically verified)
- `INVALID`: No trust (definitely tampered or malformed)

---

#### Option B: Reject with Clear Message

Alternative: Fail verification but provide clear messaging:

```python
def verify_mark(payload, payload_hash, signature, secret=None) -> dict:
    if secret is None:
        return {
            "verified": False,
            "reason": "HMAC_REQUIRES_SECRET",
            "message": "Cannot verify HMAC signature without secret key. For public verification, use Ed25519 signatures.",
            "fallback": {
                "hash_integrity": check_hash(payload, payload_hash),
                "schema_valid": validate_schema(payload),
            }
        }

    # ... existing HMAC verification
```

**Trade-off**: More explicit, but less user-friendly for third parties.

---

## Recommended Approach

**Use Option A** (graceful degradation) with clear documentation:

### User-facing messages

| Verification Result | CLI Output | Meaning |
|---------------------|------------|---------|
| `VERIFIED` | ✅ `ECHO_VERIFIED (cryptographically verified with key_id: v1)` | Strong trust |
| `UNVERIFIED` | ⚠️  `ECHO_CHECK (unverified: no secret key available)` | Weak trust |
| `INVALID` | ❌ `ECHO_BLOCKED (tampered: hash mismatch)` | No trust |

### Documentation requirements

1. **README.md**: Explain HMAC vs Ed25519 verification differences
2. **CLI help text**: Show example of public verification command
3. **Badge JSON**: Include `verification_method: "HMAC-SHA256"` field
4. **Threat model**: Document trust assumptions for HMAC

---

## HMAC Limitations Summary

| Property | HMAC-SHA256 | Ed25519 (future) |
|----------|-------------|------------------|
| **Public verification** | ❌ No (requires secret) | ✅ Yes (public key) |
| **Key distribution** | ❌ Risky (shared secret) | ✅ Safe (only public key) |
| **Third-party audit** | ❌ Impossible | ✅ Possible |
| **Forgery resistance** | ⚠️  Only if secret protected | ✅ Strong (private key never shared) |
| **Signature size** | 64 hex chars (32 bytes) | 128 hex chars (64 bytes) |
| **Performance** | Fast | Fast |
| **Implementation complexity** | Simple | Moderate (requires crypto library) |

**Recommendation**: Use HMAC for MVP/internal use, migrate to Ed25519 for public deployment.

---

## Migration Strategy (Phased)

### Phase 1: Current (HMAC only)
- Use HMAC-SHA256 for all signatures
- Verify only with `ECHO_MARK_SECRET`
- Return `VERIFIED` or `INVALID`

### Phase 2: Graceful Degradation (this design)
- Add `verify_mark_public()` for third parties
- Return `VERIFIED`, `UNVERIFIED`, or `INVALID`
- Document trust model

### Phase 3: Dual Signature (transition)
- Generate both HMAC and Ed25519 signatures
- Accept either for verification
- Allow gradual migration

### Phase 4: Ed25519 Only (future)
- Deprecate HMAC signatures
- Use Ed25519 exclusively
- Full public verification

---

## Implementation Checklist

- [ ] Add `verify_mark_public()` function
- [ ] Update `verify_mark()` to return structured dict
- [ ] Add schema validation for Echo Mark
- [ ] Update CLI to show `UNVERIFIED` status
- [ ] Document HMAC limitations in README
- [ ] Add `verification_method` field to badge JSON
- [ ] Write tests for all three states (VERIFIED, UNVERIFIED, INVALID)
- [ ] Update threat_model.md with trust assumptions

---

## Example Usage

### Trusted Party (has secret)
```bash
export ECHO_MARK_SECRET="production-key"
po-cosmic verify runs/badge.json

# Output:
# ✅ ECHO_VERIFIED (cryptographically verified with key_id: v1)
# Bias: 0.25 (low)
# Merchants: 5
# Execution: allowed without confirmation
```

### Third Party (no secret)
```bash
# No ECHO_MARK_SECRET set
po-cosmic verify runs/badge.json

# Output:
# ⚠️  ECHO_CHECK (unverified: no secret key available)
# Hash integrity: ✓
# Schema valid: ✓
# Signature format: ✓
# Note: Badge structure is valid. Cryptographic verification requires secret key.
#       For independent verification, request Ed25519-signed badges.
```

### Tampered Badge (has secret)
```bash
export ECHO_MARK_SECRET="production-key"
po-cosmic verify runs/tampered_badge.json

# Output:
# ❌ ECHO_BLOCKED (tampered: signature mismatch)
# Hash integrity: ✗ (payload was modified)
# Expected hash: a3eb1830f13d3e908229a0a6f9ff0889e890dc1055611db1951ae051e1263fdc
# Actual hash:   b4fc2941e24d4f018330b1a7f0881779f991ed2166722ec2062bf152f2374efd
```

---

## Security Considerations

### HMAC-specific risks

1. **Secret leakage**: If `ECHO_MARK_SECRET` leaks, all badges can be forged
   - Mitigation: Use key rotation (v2 schema with `key_id`)
   - Mitigation: Store secret in secure vault (not in code/env files)

2. **Replay attacks**: Old signed badges can be reused
   - Mitigation: Include `issued_at` timestamp in payload
   - Mitigation: Reject badges older than threshold (e.g., 30 days)

3. **False sense of security**: Users may think HMAC = public verification
   - Mitigation: Clear documentation about HMAC limitations
   - Mitigation: Add `UNVERIFIED` status to surface limitations

### Why HMAC is still useful

Despite limitations, HMAC is appropriate for:
- Internal audit systems (trusted environment)
- MVP/prototype deployments
- Performance-critical scenarios
- Environments where public verification is not required

**But**: For social-scale deployment, Ed25519 is necessary.

---

## References

- HMAC: [RFC 2104](https://tools.ietf.org/html/rfc2104)
- Ed25519: [RFC 8032](https://tools.ietf.org/html/rfc8032)
- Constant-time comparison: prevents timing attacks

---

**Next**: See `ED25519_MIGRATION.md` for public-key signature design.
