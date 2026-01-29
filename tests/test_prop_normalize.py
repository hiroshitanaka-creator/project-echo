"""
Property-based tests for input normalization (adversarial robustness).

Tests invariants:
- Merchant name variants normalize to same canonical form
- Price string variants parse to same numeric value
- URL variants canonicalize to same form
- Normalization is idempotent (normalize(normalize(x)) == normalize(x))
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from po_core.normalize import canonicalize_url, normalize_merchant, normalize_price
from tests.strategies_adversarial import (
    affiliate_urls,
    merchant_name_variants,
    price_strings,
    url_variants,
)


@settings(max_examples=50, deadline=None)
@given(st.sampled_from(["OpenTable", "UberEats", "Tabelog", "Google", "Amazon", "Yelp"]))
def test_merchant_normalization_stable(base_name):
    """All variants of a merchant name should normalize to same canonical form."""
    # Create known variants manually
    variants = [
        base_name.upper(),
        base_name.lower(),
        base_name.title(),
        base_name + " Inc",
        base_name + " LLC",
        base_name.replace("e", "e\u200b"),  # Zero-width injection
        base_name + "®",
        base_name + " (Official)",
    ]

    # All variants should normalize to the same form
    normalized_forms = {normalize_merchant(v) for v in variants}

    # Should have exactly 1 unique normalized form
    assert len(normalized_forms) == 1, (
        f"Merchant variants for {base_name} normalized to multiple forms: {normalized_forms}"
    )


@settings(max_examples=100, deadline=None)
@given(st.sampled_from(["OpenTable", "UberEats", "Tabelog"]))
def test_merchant_normalization_removes_noise(base_name):
    """Normalization should remove case, punctuation, and suffixes."""
    # Create noisy variants
    noisy = [
        base_name.upper(),
        base_name.lower(),
        base_name + " Inc",
        base_name + " LLC",
        base_name + " (Official)",
        base_name.replace("e", "e\u200b"),  # Zero-width space injection
        base_name + "®",
    ]

    normalized = [normalize_merchant(n) for n in noisy]

    # All should normalize to lowercase base name (no punctuation/suffixes)
    for norm, orig in zip(normalized, noisy, strict=True):
        # Should be lowercase
        assert norm == norm.lower(), f"{orig} → {norm} (not lowercase)"
        # Should not contain punctuation
        assert not any(c in norm for c in ["-", "_", ".", "/", "|"]), (
            f"{orig} → {norm} (has punctuation)"
        )
        # Should not contain zero-width chars
        assert "\u200b" not in norm, f"{orig} → {norm} (has zero-width)"


@settings(max_examples=100, deadline=None)
@given(st.integers(min_value=1000, max_value=500_000))  # >= 1000 for k notation precision
def test_price_normalization_stable(base_price):
    """All price format variants should parse to same numeric value."""
    # Generate variants (excluding k notation which loses precision)
    variants = [
        str(base_price),  # Plain
        f"{base_price:,}",  # Comma
        f"¥{base_price:,}",  # Yen prefix
        f"{base_price:,}円",  # Yen suffix
        f"¥ {base_price:,} 円",  # Mixed with spaces
    ]

    parsed = [normalize_price(v) for v in variants]

    # All should parse to same value (within floating point tolerance)
    base_val = float(base_price)
    for p, v in zip(parsed, variants, strict=True):
        assert p is not None, f"Failed to parse: {v}"
        assert abs(p - base_val) < 0.01, f"{v} -> {p} (expected {base_val})"


@settings(max_examples=50, deadline=None)
@given(price_strings())
def test_price_normalization_always_numeric(price_str):
    """Price normalization should always return numeric or None."""
    result = normalize_price(price_str)
    assert result is None or isinstance(result, (int, float)), (
        f"normalize_price({price_str!r}) returned {result!r} (type: {type(result)})"
    )


@settings(max_examples=100, deadline=None)
@given(url_variants())
def test_url_canonicalization_stable(url):
    """URL canonicalization should be idempotent."""
    canonical1 = canonicalize_url(url)
    canonical2 = canonicalize_url(canonical1)

    # Should be idempotent: canonicalize(canonicalize(x)) == canonicalize(x)
    assert canonical1 == canonical2, f"Not idempotent: {url} → {canonical1} → {canonical2}"


@settings(max_examples=50, deadline=None)
@given(url_variants())
def test_url_canonicalization_removes_tracking(url):
    """URL canonicalization should remove tracking parameters."""
    canonical = canonicalize_url(url)

    # Should not contain tracking params
    tracking_params = ["utm_source", "utm_medium", "utm_campaign", "fbclid", "gclid", "ref", "aff"]
    for param in tracking_params:
        assert param not in canonical.lower(), (
            f"Tracking param {param} not removed: {url} → {canonical}"
        )


@settings(max_examples=100, deadline=None)
@given(affiliate_urls())
def test_url_canonicalization_handles_affiliate(url):
    """URL canonicalization should handle affiliate URL obfuscation."""
    canonical = canonicalize_url(url)

    # Should be a valid URL structure
    assert canonical.startswith("https://"), f"Canonical URL should use https: {canonical}"

    # Should not contain tracking params as top-level query parameters
    # (nested redirect URLs are OK, they contain the tracking params in the value)
    if "?" in canonical:
        import urllib.parse

        parsed = urllib.parse.urlparse(canonical)
        params = urllib.parse.parse_qs(parsed.query)
        param_names = [k.lower() for k in params.keys()]

        # Only check for tracking params if it's not a redirect URL
        # (redirect URLs have nested tracking in the 'url' param value)
        if "url" not in param_names:  # Not a redirect URL
            tracking_params = [
                "ref",
                "aff",
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "fbclid",
                "gclid",
            ]
            for track in tracking_params:
                assert track not in param_names, (
                    f"Tracking param {track} found in canonical URL: {canonical}"
                )


@settings(max_examples=50, deadline=None)
@given(merchant_name_variants())
def test_merchant_normalization_idempotent(variant):
    """Merchant normalization should be idempotent."""
    norm1 = normalize_merchant(variant)
    norm2 = normalize_merchant(norm1)

    assert norm1 == norm2, f"Not idempotent: {variant} → {norm1} → {norm2}"


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=100, max_value=100_000))
def test_price_normalization_idempotent(base_price):
    """Price normalization should be idempotent (numeric in, numeric out)."""
    # Parse a formatted price string
    price_str = f"¥{base_price:,}"
    parsed1 = normalize_price(price_str)

    assert parsed1 is not None

    # Normalizing the numeric value (as string) should return same value
    parsed2 = normalize_price(str(parsed1))

    assert parsed2 is not None
    assert abs(parsed1 - parsed2) < 0.01, f"Not idempotent: {base_price} → {parsed1} → {parsed2}"
