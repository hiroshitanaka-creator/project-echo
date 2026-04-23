# Operations Guide — Initial Setup & Environment Reference

This document covers **initial environment setup** for new operators.
For day-to-day operational procedures (benchmark cycles, key rotation, audit flows,
incident response), see [`docs/OPERATING_PROCEDURE.md`](OPERATING_PROCEDURE.md).

---

## 1. Environment Variables

All secrets are injected at runtime via environment variables.
**Never hardcode keys in source files or config committed to VCS.**

### Required for signing (Echo Mark)

| Variable | Purpose | Format | Example |
|---|---|---|---|
| `ECHO_MARK_SECRET` | HMAC-SHA256 signing secret | Plain string, ≥16 chars | `export ECHO_MARK_SECRET="my-secret-key-16+"` |
| `ECHO_MARK_PRIVATE_KEY` | Ed25519 private key | 64-char hex (32 bytes) | See key generation below |
| `ECHO_MARK_KEYS` | HMAC key rotation map | `key_id=secret[,...]` | `export ECHO_MARK_KEYS="v1=$ECHO_MARK_SECRET"` |

### Optional for signing verification

| Variable | Purpose | Format |
|---|---|---|
| `ECHO_MARK_PUBLIC_KEYS` | Ed25519 public key registry | JSON map `{key_id: hex_pubkey}` |

### Required for webhook notifications

| Variable | Purpose |
|---|---|
| `ECHO_SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |
| `ECHO_PAGERDUTY_ROUTING_KEY` | PagerDuty Events API v2 routing key (32-char hex) |

---

## 2. Initial Key Generation

### Ed25519 key pair

```bash
# Generate a new Ed25519 key pair (requires PyNaCl)
python tools/generate_keypair.py --key-id echo-prod-$(date +%Y%m) \
    --out-private /tmp/private_key.hex \
    --out-public /tmp/public_key.hex

# Inspect generated keys
cat /tmp/private_key.hex  # → 64-char hex; export as ECHO_MARK_PRIVATE_KEY
cat /tmp/public_key.hex   # → 64-char hex; add to public key registry
```

Store the private key in your secrets manager (Vault, AWS Secrets Manager, GitHub Actions secret, etc.).
Never commit private key material.

### HMAC secret

```bash
# Generate a random 32-char HMAC secret
python -c "import secrets; print(secrets.token_hex(16))"
```

### Public key registry file (optional)

```bash
# Create .keys/public_key_registry.json
mkdir -p .keys
python tools/generate_keypair.py \
    --key-id echo-prod-$(date +%Y%m) \
    --registry .keys/public_key_registry.json \
    --out-private /dev/stdout 2>/dev/null
```

---

## 3. Minimal Quickstart

```bash
# 1. Install
pip install -e .
export ECHO_MARK_SECRET="demo-secret-key-16chars"
export ECHO_MARK_PRIVATE_KEY="1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100"
export ECHO_MARK_KEYS="v1=$ECHO_MARK_SECRET"
export ECHO_TRUSTED_DEVICE_SECRETS="default=abababababababababababababababababababababababababababababababab"

# 2. Run the shopping demo
make demo-shopping

# 3. Verify the generated badge
po-cosmic verify runs/high_bias_affiliate.badge.json

# 4. Run the voice flow
po-cosmic voice \
  --intent search \
  --transcript "候補を見せて" \
  --meta '{}' \
  --simulate-ok \
  --device-secret "abababababababababababababababababababababababababababababababab" \
  --in runs/high_bias_affiliate.audit.json \
  --out runs/voice_out.json
```

---


## 3.5 Development environment setup policy (single source of truth)

Development dependency versions are defined in exactly one place:
`pyproject.toml` (`[project.optional-dependencies].dev`).

Install command (CI and local):

```bash
pip install -e .[dev]
```

`requirements-dev.txt` is retained only as a compatibility shim and delegates to
`-e .[dev]`; it must not carry independent version constraints.

## 4. Webhook Setup

### Slack

1. Create an Incoming Webhook in your Slack workspace.
2. Export the URL:
   ```bash
   export ECHO_SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T.../B.../..."
   ```
3. Test with a dry run:
   ```python
   from po_echo.webhook_dispatch import configs_from_env, dispatch_webhooks
   configs = configs_from_env()
   results = dispatch_webhooks(notification, configs, dry_run=True)
   print(results)
   ```

### PagerDuty

1. Create a service integration with "Events API v2" in PagerDuty.
2. Copy the integration key (32-char hex).
3. Export:
   ```bash
   export ECHO_PAGERDUTY_ROUTING_KEY="abc123..."
   ```

**Idempotency**: PagerDuty calls include a `dedup_key` derived from `generated_at_utc`,
preventing duplicate pages for the same alert window on retry.
Slack does not support native deduplication; `X-Request-Id` (SHA-256 of payload)
is sent for log correlation only.

---

## 5. Key Rotation

See [`docs/OPERATING_PROCEDURE.md` §4](OPERATING_PROCEDURE.md#4-key-rotation-手順) for the full rotation procedure.

Quick summary:

```bash
# Rotate to a new key ID
python tools/generate_keypair.py rotate \
    --key-id echo-prod-$(date +%Y%m) \
    --registry .keys/registry.json

# Verify signing still works with the new key
export ECHO_MARK_PRIVATE_KEY="<new_private_key_hex>"
export ECHO_MARK_KEYS="echo-prod-$(date +%Y%m)=$ECHO_MARK_SECRET"
po-cosmic badge --in runs/high_bias_affiliate.audit.json --out /tmp/test.badge.json
po-cosmic verify /tmp/test.badge.json
```

---

## 6. CI/CD Secret Injection

For GitHub Actions, add the following repository secrets:

| Secret name | Maps to env var |
|---|---|
| `ECHO_MARK_SECRET` | `ECHO_MARK_SECRET` |
| `ECHO_MARK_PRIVATE_KEY` | `ECHO_MARK_PRIVATE_KEY` |
| `ECHO_SLACK_WEBHOOK_URL` | `ECHO_SLACK_WEBHOOK_URL` |
| `ECHO_PAGERDUTY_ROUTING_KEY` | `ECHO_PAGERDUTY_ROUTING_KEY` |

Reference them in your workflow:

```yaml
env:
  ECHO_MARK_SECRET: ${{ secrets.ECHO_MARK_SECRET }}
  ECHO_MARK_PRIVATE_KEY: ${{ secrets.ECHO_MARK_PRIVATE_KEY }}
```

---

## 7. Verifying Your Setup

```bash
# Smoke check: all core components importable
pytest -q tests/test_smoke.py

# Signing round-trip
make demo-shopping
po-cosmic verify runs/high_bias_affiliate.badge.json

# Full test suite
pytest -q tests/
```

If `po-cosmic verify` outputs `VERIFIED`, your key setup is correct.
