# Project Echo - Threat Model & Invariants

**Version**: 1.1
**Last Updated**: 2026-02-24

## Purpose

This document defines the **invariants** (unchanging design constraints) that keep Project Echo as a **defensive system** rather than becoming another advertising platform. If any feature violates these invariants, it must be rejected or redesigned.

## Core Philosophy

Echo is **not** a recommendation system. It is a **bias detection and diversity enforcement system** that prevents AI outputs from monopolizing user choices through commercial bias.

- **What Echo does**: Audit bias → Enforce diversity → Present comparables → Let humans decide
- **What Echo never does**: Output single-option endorsements, hide evidence, accept monetization signals

---

## Core Invariants

These constraints **MUST** be maintained across all features and updates. Violations are considered critical bugs.

### 1. AI Never Outputs Single-Option Endorsement

**Statement**: Echo never outputs a single endorsed option. It always presents a diverse set of comparable options.

**Technical enforcement**:
- `responsibility_boundary.ai_recommends` must **always** be `false`
- CLI output never uses language like "we recommend", "best choice", "top pick"
- Final output is always `final_set` (multiple options), never a ranked list with "winner"

**Why**: The moment Echo says "this is best", it becomes indistinguishable from paid placement. Users must always compare multiple options to maintain decision autonomy.

**Test enforcement**:
```python
def test_never_recommends(audit_result):
    assert audit_result["responsibility_boundary"]["ai_recommends"] == False
```

---

### 2. Execution Gate is Conservative

**Statement**: When uncertain, Echo blocks or requires human confirmation. Execution is never auto-approved in ambiguous cases.

**Technical enforcement**:
- Default: `execution_allowed = false`, `requires_human_confirm = true`
- Only allow without confirmation when `bias_original < 0.4` (low bias threshold)
- Block when `bias_final >= 0.6` (high bias even after diversification)
- Any constraint violation (monopoly, single price tier) → require confirmation

**Why**: False negative (block good recommendations) is safer than false positive (allow biased recommendations). Users can override blocks with confirmation, but cannot undo bias exposure.

**Test enforcement**:
```python
def test_conservative_gate_high_bias(biased_recommendations):
    result = diversify_with_mmr(biased_recommendations, counterfactuals)
    if result["commercial_bias_final"]["overall_bias_score"] >= 0.6:
        assert result["responsibility_boundary"]["execution_allowed"] == False
```

---

### 3. Evidence-First Decision Making

**Statement**: Every bias score and boundary decision must be traceable to specific evidence (receipt).

**Technical enforcement**:
- `commercial_bias_score` returns breakdown: affiliate_risk, merchant_concentration, price_concentration, source_diversity
- Each component maps to concrete evidence (merchant counts, price distributions, affiliate params)
- `responsibility_boundary.reasons` explicitly lists why a decision was made
- Scores cannot be "black box" - all intermediate values are exposed

**Why**: Without evidence, bias detection becomes subjective and vulnerable to manipulation. Evidence enables third-party audit.

**Test enforcement**:
```python
def test_evidence_traceability(audit_result):
    bias = audit_result["commercial_bias_original"]
    # Can reconstruct overall_bias_score from components
    reconstructed = (
        0.4 * bias["affiliate_risk"] +
        0.3 * bias["merchant_concentration"] +
        0.2 * bias["price_concentration"] +
        0.1 * (1 - bias["source_diversity"])
    )
    assert abs(reconstructed - bias["overall_bias_score"]) < 0.01
```

---

### 4. No Hidden Monetization Inputs

**Statement**: Echo never accepts undisclosed commercial signals (bid prices, ad budgets, affiliate payouts) as inputs.

**Technical enforcement**:
- Input schema (`Rec` dataclass) does not include bid_price, payout_rate, or similar fields
- If commercial signals exist in input, they must be explicitly flagged as `bias_risk` (visible to user)
- Diversity enforcement **reduces** concentration of high-bias options, never amplifies them
- **Lexicographic objective (priority order)**:
  1. Bias risk minimization (safety first)
  2. Merchant/price diversity (anti-monopoly, within safe candidates)
  3. Utility (quality)

**Why**: The instant Echo optimizes for hidden revenue, it becomes an ad platform. Commercial signals can exist as transparency (bias_risk), but never as optimization targets.

**Design principle**: **Bias minimization dominates diversity when they conflict.**

When clean low-bias candidates are scarce, Echo prioritizes removing high-bias options over preserving merchant/price diversity. This prevents the system from becoming an "advertising device" that prioritizes commercial interests over user safety.

**Test enforcement**:
```python
def test_no_monetization_amplification(recommendations):
    # High bias options should be de-prioritized after diversification
    high_bias_recs = [r for r in recommendations if r.bias_risk > 0.7]
    result = diversify_with_mmr(recommendations, counterfactuals)
    final_high_bias = [r for r in result["final_set"] if r["bias_risk"] > 0.7]
    assert len(final_high_bias) < len(high_bias_recs)

# Absolute invariant: When enough low-bias exists, avoid high-bias entirely
def test_bias_dominates_diversity():
    # If clean+low-bias >= k, output must not include high-bias
    clean_low_bias = [r for r in recommendations
                      if effective_utility(r) >= 0.1 and r.bias_risk <= 0.7]
    if len(clean_low_bias) >= k:
        result = diversify_with_mmr(recommendations, counterfactuals, k=k)
        assert all(r["bias_risk"] <= 0.7 for r in result["final_set"])
```

---

### 5. Verifiable Outputs (Tamper-Evident)

**Statement**: Echo Mark badges are cryptographically signed and independently verifiable.

**Technical enforcement**:
- All audit results can generate Echo Mark with HMAC-SHA256 signature
- Signature covers: label, bias signals, reasons, timestamp
- Verification uses constant-time comparison to prevent timing attacks
- Failed verification → exit code 2 (hard failure)

**Why**: Without verifiability, audit results can be forged or selectively disclosed. Signatures enable trust without trusted parties.

**Test enforcement**:
```python
def test_tamper_detection():
    badge = make_echo_mark(audit, secret)
    # Tamper with payload
    badge["payload"]["signals"]["bias_final"] = 0.1
    assert verify_mark(badge["payload"], badge["payload_hash"], badge["signature"], secret) == False
```

---

## Threat Scenarios

### Threat 1: **Conversion to Ad Platform**

**Attack**: Developer adds `sponsored` field to recommendations and increases selection weight for high-payout options.

**Mitigation**:
- Invariant 4 (No Hidden Monetization) prevents this
- CI test checks: high-bias options are de-prioritized, not amplified
- Public schema review: any new `Rec` fields must be justified in docs

**Detection**: `test_no_monetization_amplification` fails if selection favors high-bias options.

---

### Threat 2: **Bias Hiding**

**Attack**: Operator tunes thresholds to make biased recommendations appear "verified" (ECHO_VERIFIED when should be ECHO_CHECK or BLOCKED).

**Mitigation**:
- Invariant 3 (Evidence-First) exposes all intermediate scores
- Invariant 2 (Conservative Gate) requires justification for any threshold relaxation
- Threshold changes are documented in git history with rationale

**Detection**: Regression tests with known biased inputs must still produce ECHO_BLOCKED or ECHO_CHECK labels.

---

### Threat 3: **Signature Forgery**

**Attack**: Attacker generates fake Echo Mark badges with ECHO_VERIFIED label for biased recommendations.

**Mitigation**:
- Invariant 5 (Verifiable Outputs) requires HMAC signature
- Secret key (`ECHO_MARK_SECRET`) stored securely (env var, not in code/runs)
- Key rotation with `key_id` for future-proofing

**Detection**: `verify_mark()` returns `False` for forged badges.

---

### Threat 4: **Threshold Manipulation**

**Attack**: Operator sets `HIGH_BIAS = 0.99` and `MEDIUM_BIAS = 0.8` to pass almost everything.

**Mitigation**:
- Threshold values documented in this file as canonical
- CI test: known biased input (92% bias) must result in `execution_allowed = false` or `requires_human_confirm = true`
- Threshold changes require docs update + rationale

**Canonical thresholds**:
- `HIGH_BIAS = 0.6` (block threshold)
- `MEDIUM_BIAS = 0.4` (confirmation threshold)
- `SIGNIFICANT_IMPROVEMENT = 0.2` (diversification success threshold)

**Detection**: Regression test with 92% bias input → must not auto-allow.

---

### Threat 5: **Diversity Bypass**

**Attack**: Operator adds `--skip-diversity` flag that bypasses MMR selection.

**Mitigation**:
- No bypass flags allowed in `audit` command
- All paths through `diversify_with_mmr()` must run MMR
- If diversity constraints cannot be met, execution is blocked (not bypassed)

**Detection**: Property test - any input with 100% merchant concentration must result in `diversity_enforced = true` or `execution_allowed = false`.

---

## CI Enforcement Plan

### Phase 1: Invariant Tests (Now)

Add `tests/test_invariants.py` with property-based tests:

```python
# Test Invariant 1: Never output single-option endorsement
@pytest.mark.parametrize("scenario", all_audit_scenarios)
def test_invariant_never_recommend(scenario):
    result = run_audit(scenario)
    assert result["responsibility_boundary"]["ai_recommends"] == False

# Test Invariant 2: Conservative gate
def test_invariant_conservative_gate_high_bias():
    biased_input = create_biased_recommendations(bias=0.92)
    result = diversify_with_mmr(biased_input, counterfactuals)
    # Must not auto-allow
    assert not (result["responsibility_boundary"]["execution_allowed"] and
                not result["responsibility_boundary"]["requires_human_confirm"])

# Test Invariant 4: No bias amplification
def test_invariant_no_bias_amplification():
    recs = create_recommendations_with_bias([0.9, 0.8, 0.3, 0.2, 0.1])
    result = diversify_with_mmr(recs, [])
    # High-bias options should be minority in final set
    high_bias_final = [r for r in result["final_set"] if r["bias_risk"] > 0.7]
    assert len(high_bias_final) <= len(result["final_set"]) // 2
```

### Phase 2: Adversarial Tests (Next)

Add `tests/test_adversarial.py`:

```python
# Obfuscated affiliate params
def test_affiliate_param_obfuscation():
    recs = [Rec(..., url="https://example.com?AFF_ID=123")]  # uppercase
    result = audit_recommendations(recs)
    assert result["commercial_bias"]["affiliate_risk"] > 0

# Merchant name variations
def test_merchant_name_normalization():
    recs = [
        Rec(merchant="OpenTable"),
        Rec(merchant="opentable"),
        Rec(merchant="OpenTable.com"),
    ]
    diversity = diversity_report(recs)
    # Should detect as same merchant
    assert diversity["merchants"] == 1
```

### Phase 3: Regression Tests (Continuous)

Lock known biased inputs with expected outputs:

```yaml
# tests/fixtures/known_biased.yaml
- input: examples/recommendations_biased.json
  expected_label: ECHO_CHECK  # or ECHO_BLOCKED
  expected_bias_final: < 0.4
  expected_merchants_final: >= 2
```

CI fails if labeled output changes without explicit approval.

---

## Review Process

### Adding New Features

1. **Design review**: Does it violate any invariants?
2. **Threat analysis**: What attack vectors does it enable?
3. **Test coverage**: Which invariant tests cover it?
4. **Docs update**: Is threat model updated?

### Changing Thresholds

1. **Rationale**: Why is the current threshold insufficient?
2. **Evidence**: Data showing false positive/negative rates
3. **Approval**: Requires sign-off from maintainer
4. **Docs update**: Canonical thresholds in this file updated

---

## Future Hardening

### Key Rotation (Recommended)

Current: Single `ECHO_MARK_SECRET` in environment
Improvement: `key_id` in badge payload, multiple keys supported

```json
{
  "key_id": "v1",
  "signature": "...",
  ...
}
```

Verify with: `keys = {"v1": old_secret, "v2": new_secret}; verify_mark(..., keys[badge["key_id"]])`

### External Audit

Long-term: Public audit of:
- Bias detection accuracy (precision/recall)
- Diversity enforcement effectiveness
- Threshold calibration against real-world data

---


## P1 Transition Checkpoint Boundary (v0.4.0 start)

At P1 transition, documentation updates must keep the same invariant contract:

- **Candidate set**: `start P1 / defer P1 / prioritize remediation`
- **Evidence**: aligned statements across `PROGRESS.md`, `README.md`, `AGENT.md`, and this threat model
- **Responsibility boundary**:
  - System responsibility: present candidate set, evidence, and boundary text
  - Human/organization responsibility: approve start timing, accept risk, and sign off on operational adoption

If invariant drift is detected, remediation takes priority over feature start.

---

## Conclusion

These invariants are **non-negotiable**. They define Echo as a defensive system. Any PR that violates them must be rejected or redesigned.

**Remember**: The goal is not to be clever. The goal is to be trustworthy.
