# Project Echo
**Anti-sponsored AI.**

[![Release](https://img.shields.io/github/v/release/hiroshitanaka-creator/project-echo?label=Release)](https://github.com/hiroshitanaka-creator/project-echo/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Echo audits AI recommendations, injects diversity noise, and gates execution — with tamper-evident badges.

Echo prevents "convenience capture": AI outputs quietly collapsing into sponsored, bid-driven, or monopolistic choices by enforcing **Audit → Diversity Noise → Execution Gate → Tamper-evident Badge**.

> Echo never recommends.
> It returns **a comparable candidate set + reconstructable evidence + a responsibility boundary**.

## What it does
- **Receipt-style Commercial Bias Audit**
  Every bias decision is backed by reconstructable evidence (affiliate traces, concentration metrics, source diversity, price bucket distribution).
- **Diversity Noise (defense, not sabotage)**
  Echo injects counterfactual alternatives (multi-merchant, multi-price-band, multi-source) to break recommendation lock-in.
- **Execution Gate**
  Mechanical policy outputs: `execution_allowed` / `requires_human_confirm` based on bias + risk signals.
- **Echo Mark (tamper-evident badge)**
  HMAC-signed badge (`ECHO_VERIFIED / ECHO_CHECK / ECHO_BLOCKED`) + verify CLI.
- **Property-based tests (adversarial inputs included)**
  Defends against obfuscation tricks: merchant name drift, redirect-like URLs, price format drift, affiliate parameter hiding.

## Quickstart
```bash
pip install -e .
export ECHO_MARK_SECRET="your-secret-key"  # Min 16 chars
make demo-shopping
```

### Demo: Shopping Bias Defense

`make demo-shopping` runs three cases and produces 6 files under `runs/`:

#### Case 1 — High-bias / Affiliate-heavy
- `runs/high_bias_affiliate.audit.json` — audit result (receipt + gate)
- `runs/high_bias_affiliate.badge.json` — Echo Mark (signed)

#### Case 2 — Clean / Multi-merchant
- `runs/clean_multi_merchant.audit.json`
- `runs/clean_multi_merchant.badge.json`

#### Case 3 — Mixed / Contaminated inputs
- `runs/mixed_contaminated.audit.json`
- `runs/mixed_contaminated.badge.json`

Verify any badge:

```bash
po-cosmic verify runs/high_bias_affiliate.badge.json
```

**Output:**
```
================================================================================
[Echo Mark Verification]
================================================================================
Label: ECHO_VERIFIED
Signature: VALID ✓
================================================================================
```

### Demo outputs (6 files)
Generated under `runs/` (audit + badge for each case):

- `runs/high_bias_affiliate.audit.json`
- `runs/high_bias_affiliate.badge.json`
- `runs/clean_multi_merchant.audit.json`
- `runs/clean_multi_merchant.badge.json`
- `runs/mixed_contaminated.audit.json`
- `runs/mixed_contaminated.badge.json`

### Output schema (high level)

Each `*.audit.json` includes:

- `commercial_bias_original` / `commercial_bias_final` (receipt-style evidence + scores)
- `diversity_report_original` / `diversity_report_final`
- `responsibility_boundary`:
  - `execution_allowed`
  - `requires_human_confirm`
  - `ai_recommends`: false
  - `reasons` + `signals`
- `final_set` (diversified candidate set)

Each `*.badge.json` includes:

- `label`: `ECHO_VERIFIED` | `ECHO_CHECK` | `ECHO_BLOCKED`
- `payload_hash` + `signature` (HMAC-SHA256)
- Verify result is deterministic given the same `ECHO_MARK_SECRET`

## Philosophy

**The threat is not "AI is wrong."**

**The threat is AI becomes a paid funnel while looking helpful.**

Echo counters this with systems, not morals:

- **Audit** (evidence-first)
- **Noise** (diversity enforcement)
- **Gate** (responsibility boundary)
- **Badge** (tamper-evident accountability)

## Status

Research-grade defensive prototype with CI and property-based testing.

PRs welcome.

---

## Advanced Topics

### Property-based testing

Echo uses Hypothesis for adversarial input testing:

```bash
pytest tests/test_prop_*.py -v
```

Tests include:
- Merchant name normalization stability
- URL canonicalization
- Price format robustness
- MMR bias penalty enforcement
- Execution gate conservative behavior

See `docs/threat_model.md` for invariants.

### Public verification design

Current Echo Mark uses HMAC-SHA256 (symmetric cryptography). For public verification without shared secret:

- See `docs/VERIFICATION_DESIGN.md` for three-state verification model
- See `docs/ED25519_MIGRATION.md` for Ed25519 migration strategy

### Demo documentation

- `docs/DEMO_SHOPPING.md` — Shopping bias defense walkthrough
- `examples/demo_inputs/shopping/` — 3 realistic input scenarios

## Architecture

```
project-echo/
├── src/
│   ├── po_core/
│   │   ├── diversity.py           # MMR + bias penalty
│   │   ├── normalize.py           # Adversarial input defense
│   │   └── cosmic_ethics_39/      # 39 philosophers (legacy)
│   └── po_echo/
│       └── echo_mark.py           # HMAC badge generation
│
├── tests/
│   ├── test_prop_diversity.py     # Property-based tests
│   ├── test_prop_normalize.py
│   └── strategies_adversarial.py  # Hypothesis strategies
│
├── examples/demo_inputs/shopping/
│   ├── 01_high_bias_affiliate.json
│   ├── 02_clean_multi_merchant.json
│   └── 03_mixed_contaminated.json
│
├── tools/
│   └── demo_shopping.py           # Demo runner
│
└── docs/
    ├── threat_model.md            # Invariants + design principles
    ├── DEMO_SHOPPING.md           # Shopping demo guide
    ├── VERIFICATION_DESIGN.md     # Public verification (HMAC limitations)
    └── ED25519_MIGRATION.md       # Ed25519 migration design
```

## Design Principles

### Lexicographic Objective

Priority order for MMR diversification:

1. **Bias risk minimization** (safety first)
2. **Merchant/price diversity** (anti-monopoly, within safe candidates)
3. **Utility** (quality)

**Design principle**: Bias minimization dominates diversity when they conflict.

### Conservative Gate Pattern

Execution gate decision logic:

1. **PRIORITY 1**: High bias final → BLOCK (conservative gate)
2. **PRIORITY 2**: Low bias originally → allow without confirmation
3. **PRIORITY 3**: Bias improved → allow with confirmation
4. **ELSE**: Medium bias → allow with confirmation

See `src/po_core/diversity.py:330-380` for implementation.

### Conditional Invariants

Property-based tests use conditional invariants:

- **Absolute invariants** (always enforced):
  - High-bias exclusion when clean+low-bias >= k
  - Bias proportion improvement (within ε=0.15)
  - Max bias never amplified

- **Conditional invariants** (situation-dependent):
  - Merchant diversity only when clean candidates exist across merchants
  - Price diversity only when clean candidates exist across price bands

See `tests/test_prop_diversity.py` for test implementation.

## Contributing

This is a research prototype. Issues and PRs welcome.

### Running tests

```bash
# All tests
make test

# Property-based tests only
pytest tests/test_prop_*.py -v

# Specific test with verbose output
pytest tests/test_prop_diversity.py::test_diversify_prefers_low_bias_when_enough_low_bias_exists -v
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Citation

If you use Project Echo in research, please cite:

```bibtex
@software{project_echo,
  title = {Project Echo: Anti-sponsored AI with Audit, Diversity Noise, and Execution Gate},
  author = {hiroshitanaka-creator},
  year = {2026},
  url = {https://github.com/hiroshitanaka-creator/project-echo}
}
```

---

**Important**: Echo is a defensive framework for preventing commercial bias in AI recommendations. It does not make recommendations itself—it audits, diversifies, and gates execution with tamper-evident accountability.
