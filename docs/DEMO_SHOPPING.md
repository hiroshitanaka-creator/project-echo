# Demo B — Shopping Bias Defense (Echo Proxy)

This demo shows how Echo prevents "convenience capture": a system that only presents high-bid / sponsored options.

## What you get

- **Evidence-first commercial bias receipt** (reconstructable)
- **Diversified alternatives** (MMR + diversity enforcement + bias penalty)
- **Responsibility boundary** (execution gate)
- **Tamper-evident Echo Mark** (HMAC)

## Run

```bash
export ECHO_MARK_SECRET="demo-secret-key-16chars"
make demo-shopping
```

※ 上記secretはデモ専用です。本番運用では使わないでください。

## Expected outcomes

### 1) High-bias affiliate list → ECHO_BLOCKED

**Input**: Single-merchant dominance with affiliate evidence
- All 5 recommendations from same merchant (`ShopExample`)
- All URLs contain affiliate tracking params (`utm_source`, `ref`, `aff`, etc.)
- All at same price point (¥29,800)
- High bias_risk (0.88 - 0.95)

**Echo's response**:
- Detects commercial bias (affiliate_risk, merchant_concentration, price_concentration)
- Cannot fully diversify (no counterfactuals available)
- Sets execution gate: `execution_allowed: false, requires_human_confirm: true`
- Label: **ECHO_BLOCKED** (high bias remains after diversification)

**Key insight**: Echo is honest about limitations. When only biased options exist and final bias remains high, it blocks auto-execution and makes the boundary explicit.

---

### 2) Clean list → ECHO_CHECK (with current sample input)

**Input**: Multi-merchant with low bias
- 5 merchants (MerchantA, B, C, D, E)
- 3 price tiers (budget ¥6,900, standard ¥8,900-9,900, premium ¥12,900)
- Low bias_risk (0.04 - 0.08)
- No affiliate params

**Echo's response**:
- Bias already low → no diversification needed
- Merchant diversity: 5 merchants ✓
- Input includes multiple price tiers
- Bias remains low, but final price-bucket diversity is still limited in this sample
- Sets execution gate: `execution_allowed: true, requires_human_confirm: true`
- Label: **ECHO_CHECK** (human confirmation required)

**Key insight**: Echo doesn't interfere when recommendations are already unbiased. It's a defensive system, not a control system.

---

### 3) Mixed contaminated → CHECK or BLOCK (honest defense)

**Input**: Mix of clean and biased options
- 2 clean options (GoodStore, OkStore) with bias_risk 0.05-0.08
- 3 high-bias options (BadStore) with bias_risk 0.70-0.90
- 1 medium-bias option (MidStore) with bias_risk 0.25

**Echo's response** (depends on conditional invariants):
- **If clean+low-bias candidates >= k**: Filters out high-bias (>0.7) entirely → ECHO_VERIFIED or ECHO_CHECK
- **If clean candidates insufficient**: Includes some high-bias options, bias proportion doesn't worsen → ECHO_CHECK
- **If bias cannot be reduced**: May block execution → ECHO_BLOCKED

**Key insight**: This is the "realistic" case. Echo makes bias tradeoffs explicit through the execution gate, rather than hiding them.

---

## Why this is defense, not attack

Echo does **not** sabotage external systems. It only:

1. **Audits** recommendations (evidence-based bias detection)
2. **Enforces diversity** (MMR with bias penalty β=0.8)
3. **Requires human confirmation** when needed (conservative gate)

The execution gate has 3 outputs:
- `ECHO_VERIFIED`: Low bias, diverse → execute without confirmation
- `ECHO_CHECK`: Improved but still requires review → execute with human confirmation
- `ECHO_BLOCKED`: High bias even after diversification → block execution (user can override)

**Philosophy**: Echo prioritizes user autonomy over convenience. It never hides commercial bias in the name of "user experience."

---

## Technical details

### Lexicographic objective (priority order)

1. **Bias risk minimization** (safety first)
2. **Merchant/price diversity** (anti-monopoly, within safe candidates)
3. **Utility** (quality)

### Conditional invariants

- **Absolute**: If clean+low-bias candidates >= k, output must exclude high-bias (>0.7)
- **Conditional**: Merchant/price diversity enforced only when clean candidates exist across multiple merchants/price tiers
- **Design principle**: "Bias minimization dominates diversity when they conflict"

### MMR with bias penalty

```python
effective_utility = utility - β * bias_risk  # β = 0.8
MMR_score = λ * effective_utility - (1-λ) * diversity_penalty
```

This prevents high-utility high-bias recommendations from dominating output.

---

## Verification

All audit results are signed with HMAC-SHA256:

```bash
# Verify Echo Mark badge
po-cosmic verify runs/high_bias_affiliate.badge.json

# Expected output:
# ================================================================================
# [Echo Mark Verification]
# ================================================================================
# Label: ECHO_BLOCKED
# Schema version: echo_mark_v2
# Verification method: HMAC-SHA256
#
# Signature: VALID ✓
# ================================================================================
```

Signature covers: label, bias signals, reasons, timestamp. Tampering detection is constant-time to prevent timing attacks.

---

## What's next

After this demo:

1. **Public verification design** (handling UNVERIFIED cases with HMAC limitations)
2. **Ed25519 migration design** (for future social implementation)

---

## Files

- Input: `examples/demo_inputs/shopping/*.json`
- Output: `runs/{case_name}.audit.json`, `runs/{case_name}.badge.json`
- Makefile: `make demo-shopping`

---

**Remember**: The goal is not to be clever. The goal is to be trustworthy.
