# Changelog

All notable changes to Project Echo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.2.0] - 2026-01-24

### Added

#### Audio Channel for Ear-worn Devices (Sweetpea)
- **Voice Boundary Policy**: Risk-based execution control for voice-initiated actions
  - `voice_boundary.py`: Risk classification (low/medium/high) for intents
  - Auto-execute for low-risk actions (search, summary)
  - Double-tap confirmation for medium-risk (booking, itinerary)
  - App confirmation for high-risk (payment, identity disclosure)
  - Intent categories: CRITICAL_INTENTS (payment, purchase), SENSITIVE_INTENTS (booking, data_share)
- **Ear-Handshake Protocol**: OS-independent device pairing
  - `ear_handshake.py`: Challenge-response authentication via HMAC
  - QR/ultrasonic challenge generation
  - Short-lived session keys (5-minute default expiry)
  - Replay attack prevention with timestamp validation
  - Graceful degradation to app confirmation on session expiry
- **Rolling Transcript Hash (RTH)**: Minimal-disclosure voice audit trail
  - `rth.py`: Privacy-preserving transcript hashing
  - Never stores raw audio or full transcripts
  - Feature extraction: sorted word sets only (discards order, timing, prosody)
  - Rolling hash chain: H_t = H(H_{t-1} || feat_t)
  - Snapshot attachment to Echo Mark receipts

#### Ed25519 Signatures (Phase 2: Dual Signature)
- **Ed25519 signature support**: Public-key cryptography for tamper-evident badges
  - `make_echo_mark_ed25519()`: Ed25519-only signature generation
  - `make_echo_mark_dual()`: Dual signature (HMAC + Ed25519) for backward compatibility
  - `verify_echo_mark_ed25519()`: Public verification (no secret needed)
  - `verify_echo_mark_dual()`: Dual verification (Ed25519 preferred, HMAC fallback)
- **Keypair generation tool**: `tools/generate_keypair.py`
  - Generate Ed25519 keypair with key_id
  - Automatic file permissions (chmod 600 for private keys)
  - Public key registry support (registry.json)
  - Security reminders (never commit private keys)
- **Public key registry**: Load and verify public keys from registry.json
  - `load_public_key_registry()`: Load registry from JSON
  - `get_public_key_from_registry()`: Lookup public key by key_id
  - `verify_key_in_registry()`: Verify public key matches registry
  - Registry includes key status (active/revoked), expiration dates
- **Timestamp validation**: Replay attack mitigation
  - `validate_timestamp()`: Check badge age against max_age_days (default: 30)
  - Reject badges older than threshold
  - Detect future timestamps (clock skew protection)
  - Timestamp warnings in verification result

#### Property-Based Tests (Extended Suite)
- **Ed25519 property tests** (9 new tests):
  - Sign → verify succeeds; tamper → verify fails
  - Wrong signature always fails
  - Wrong public key always fails
  - Dual signature verification (Ed25519 preferred)
  - HMAC fallback when Ed25519 fails
- **Timestamp validation tests** (5 new tests):
  - Timestamps within max_age are valid
  - Timestamps beyond max_age are invalid (expired)
  - Future timestamps are invalid
  - Missing timestamp is invalid
  - Malformed timestamps are invalid

#### CLI Enhancements
- **Badge command**: `po-cosmic badge`
  - `--sig-mode`: Choose signature mode (hmac/ed25519/dual)
  - `--key-id`: Specify key identifier for Ed25519
  - `--keys-dir`: Directory containing keypair files
  - Auto-detect Ed25519 availability (PyNaCl)
- **Verify command**: `po-cosmic verify`
  - Auto-detect signature type (v2: HMAC, v3: Ed25519)
  - Dual verification (Ed25519 preferred, HMAC fallback)
  - Detailed verification output (hash_integrity, signature_valid, schema_valid, timestamp_valid)
  - Timestamp warnings for expired/future badges

#### Demo Updates
- **Dual signature support**: `tools/demo_shopping.py`
  - Auto-detect Ed25519 availability
  - Generate dual signatures (HMAC + Ed25519) when available
  - Fallback to HMAC-only for backward compatibility

### Changed
- **Echo Mark schema version**: v2 → v3
  - `verification_method`: "Ed25519", "HMAC-SHA256", or "Ed25519+HMAC"
  - `public_key`: Added (32 bytes hex-encoded, only for Ed25519)
  - `signature`: 64 bytes (Ed25519) or 32 bytes (HMAC)
  - `signature_hmac`: Added (dual mode only, for HMAC fallback)
  - `issued_at`: Timestamp for replay attack mitigation
- **Dependencies**: Added PyNaCl >=1.5.0 for Ed25519 support
- **README**: Added Ed25519 quickstart and migration guide

### Security
- **Replay attack mitigation**: Timestamp validation (30-day default expiration)
- **Key rotation**: Ed25519 supports seamless key rotation (old public keys remain valid)
- **Public verification**: Third parties can verify signatures without secret access
- **Backward compatibility**: Dual signature mode supports both HMAC and Ed25519

### Testing
- **51 tests passing**: All existing tests + 14 new Ed25519/timestamp tests
- **100% property-based test coverage**: Ed25519, timestamp validation, dual signature

---

## [v0.1.1] - 2026-01-12

### Added
- **Demo B: Shopping Bias Defense** - Complete demonstration package
  - 3 realistic scenarios (high-bias affiliate, clean multi-merchant, mixed contaminated)
  - 6 output files (3 × audit.json + badge.json)
  - `make demo-shopping` target for one-command execution
  - `tools/demo_shopping.py` runner script
  - `docs/DEMO_SHOPPING.md` comprehensive guide
- **Public Verification Design** (`docs/VERIFICATION_DESIGN.md`)
  - Three-state verification model (VERIFIED / UNVERIFIED / INVALID)
  - Graceful degradation strategy for HMAC limitations
  - Implementation roadmap for public verification
- **Ed25519 Migration Design** (`docs/ED25519_MIGRATION.md`)
  - Complete 4-phase migration strategy (HMAC → Dual → Ed25519-primary → Ed25519-only)
  - Key management, signature generation/verification
  - Security considerations (key rotation, replay mitigation)
- **Release Assets** for v0.1.0
  - `demo_inputs_shopping.zip` (3 JSON input files)
  - Ready for GitHub Release attachment

### Changed
- **README Rebranding** - "Anti-sponsored AI" positioning
  - New tagline: "Verify before you trust."
  - Philosophy section: "AI becomes a paid funnel while looking helpful"
  - Demo outputs section: Clear 6-file list
  - Release badge added to README header
- **CHANGELOG Format** - Now follows Keep a Changelog standard

### Documentation
- All design documents ready for public review
- Complete reproduction package for Demo B

---

## [v0.1.0] - 2026-01-12

### Added

#### Core Features
- **Commercial Bias Audit**: Receipt-style evidence for bias decisions
  - Affiliate risk detection (URL pattern matching)
  - Merchant concentration (Herfindahl index)
  - Price concentration (bucketing + entropy)
  - Source diversity metrics
- **Diversity Enforcement**: MMR algorithm with bias penalty
  - Lexicographic objective: 1) Bias minimization, 2) Diversity, 3) Utility
  - Beta=0.8 for false positive robustness
  - Pre-filtering: effective_utility >= 0.1, high-bias exclusion when clean candidates exist
- **Execution Gate**: Responsibility boundary with conservative pattern
  - Priority 1: High bias final (>=0.6) → BLOCK
  - Priority 2: Low bias original (<0.4) → ALLOW without confirmation
  - Priority 3: Bias improved → ALLOW with confirmation
  - Else: Medium bias → ALLOW with confirmation
- **Echo Mark v2**: HMAC-SHA256 tamper-evident badges
  - Three labels: ECHO_VERIFIED / ECHO_CHECK / ECHO_BLOCKED
  - Signature verification CLI: `po-cosmic verify`
  - Key rotation support with `key_id` field

#### Property-Based Testing
- **Hypothesis integration**: Adversarial input testing
  - Merchant name normalization stability (Unicode, whitespace, punctuation, suffixes)
  - URL canonicalization (scheme, tracking params, query sorting)
  - Price format robustness (comma, yen symbol, k notation)
  - MMR bias penalty enforcement
  - Execution gate conservative behavior
- **Conditional Invariants**: Test specification with preconditions
  - Absolute invariants: High-bias exclusion, bias improvement, max bias non-amplification
  - Conditional invariants: Merchant/price diversity only when clean candidates exist
- **Adversarial Strategies**: Custom Hypothesis strategies
  - `adversarial_merchant_variants()`: Name obfuscation patterns
  - `adversarial_url()`: Tracking parameter injection, redirect chains
  - `adversarial_price_str()`: Format variations

#### Demo & Documentation
- **Demo B: Shopping Bias Defense**: 3 realistic scenarios
  - High-bias affiliate (bias: 0.85 → 0.35)
  - Clean multi-merchant (maintains diversity)
  - Mixed contaminated (filters high-bias, preserves utility)
  - Makefile target: `make demo-shopping`
  - Output: 6 files (3 × audit.json + badge.json)
- **Verification Design**: HMAC limitations + public verification strategy
  - Three-state model: VERIFIED / UNVERIFIED / INVALID
  - Graceful degradation without secret access
  - docs/VERIFICATION_DESIGN.md
- **Ed25519 Migration Design**: Asymmetric cryptography for public verification
  - 4-phase migration: HMAC-only → Dual → Ed25519-primary → Ed25519-only
  - Key management, signature generation/verification
  - Security considerations (key rotation, replay mitigation)
  - docs/ED25519_MIGRATION.md
- **Threat Model**: Invariants + design principles
  - Conservative gate pattern
  - Lexicographic objective priority
  - Conditional invariant specification
  - docs/threat_model.md
- **Demo Guide**: Shopping bias defense walkthrough
  - Expected outcomes for 3 scenarios
  - Technical details (MMR, beta, conditional invariants)
  - docs/DEMO_SHOPPING.md

#### CLI & Tooling
- **po-cosmic CLI**: Unified command-line interface
  - `audit`: Commercial bias audit + diversity enforcement
  - `badge`: Generate Echo Mark from audit result
  - `verify`: Verify Echo Mark signature
  - `cosmic-39`: 39-dimensional ethical evaluation (legacy)
- **Normalization Functions**: Adversarial input defense
  - `normalize_merchant()`: Unicode NFC, zero-width removal, corporate suffix removal
  - `normalize_price()`: Multi-format parsing (comma, yen, k notation)
  - `canonicalize_url()`: Scheme normalization, tracking param removal, query sorting
- **Demo Runner**: tools/demo_shopping.py
  - Loads JSON inputs, runs diversity enforcement, generates badges
  - Prints summary (bias, diversity, execution gate, label)

#### Testing & CI
- **24 Property-Based Tests**: 100% passing
  - 9 normalization tests
  - 6 diversity tests (conditional invariants)
  - 5 execution gate tests
  - 4 Echo Mark integrity tests
- **GitHub Actions CI**: Automated testing on push/PR
  - Ruff linting + formatting
  - Pytest with coverage
  - Property-based tests with Hypothesis

### Changed
- **README Rebranding**: "Anti-sponsored AI" positioning
  - Tagline: "Echo audits AI recommendations, injects diversity noise, and gates execution"
  - Philosophy: "AI becomes a paid funnel while looking helpful" → systems, not morals
  - Quickstart: `make demo-shopping` → `po-cosmic verify`
  - Architecture + Design Principles sections added
- **Threat Model Updates**: Lexicographic objective and design principles
  - Invariant 4: MMR with bias penalty (beta=0.8)
  - Design principle: "Bias minimization dominates diversity when they conflict"
- **Test Refactoring**: Absolute vs conditional invariants
  - Clear preconditions for diversity enforcement
  - Helper functions: `is_clean()`, `is_high_bias()`
  - Constants: BETA=0.8, MIN_EFFECTIVE_UTILITY=0.1, HIGH_BIAS_THRESHOLD=0.7

### Fixed
- **P0 Bug: recommendation_boundary()**: Conservative gate violation
  - **Before**: Checked `bias_original < 0.4` before `bias_final >= 0.6`
  - **After**: Checks `bias_final >= 0.6` FIRST (safety-first pattern)
  - Verified with property-based tests (Hypothesis found falsifying example)
- **MMR Advertising Device Risk**: High-utility high-bias dominance
  - Added `effective_utility = utility - beta * bias_risk` (beta=0.8)
  - Pre-filter: Remove candidates with effective_utility < 0.1
  - Additional filter: If clean+low-bias >= k, remove high-bias (>0.7)

### Infrastructure
- MIT License
- pyproject.toml with Hypothesis dependency
- Makefile: `make demo-shopping`, `make test`
- .gitignore: runs/, reports/, .keys/

### Legacy (Preserved for Compatibility)
- **Cosmic Ethics 39**: 39-dimensional ethical evaluation framework
  - 39 philosophers (Western, Eastern, Modern)
  - 5 philosopher presets (cosmic13, east_asia, kantian, existentialist, classical)
  - Responsibility boundary protocol
  - Marked as (legacy) in documentation

---

## Future Roadmap

### v0.2.1 (Next)
- Property-based tests for Audio Channel (voice_boundary, ear_handshake, rth)
- Audio Channel CLI integration (`po-cosmic voice` subcommand)
- Demo C: Voice-initiated booking scenario

### v0.3.0 (Planned)
- Real-world integration examples (browser extension, API proxy)
- Performance benchmarks (10k recommendations)
- Multi-language support (i18n)
- Ed25519 Phase 3: Ed25519-primary (deprecate HMAC-only)

### v1.0.0 (Vision)
- Production-ready Audio Channel for ear-worn devices
- Ed25519 Phase 4: Ed25519-only (remove HMAC)
- Public audit registry (verifiable without secret access)
- SDK for third-party integrations

---

[v0.2.0]: https://github.com/hiroshitanaka-creator/project-echo/releases/tag/v0.2.0
[v0.1.1]: https://github.com/hiroshitanaka-creator/project-echo/releases/tag/v0.1.1
[v0.1.0]: https://github.com/hiroshitanaka-creator/project-echo/releases/tag/v0.1.0
