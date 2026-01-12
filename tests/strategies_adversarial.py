"""
Adversarial input generators for property-based testing.

Simulates attacker strategies to evade bias detection:
- Merchant name variations (case, punctuation, zero-width chars)
- URL obfuscation (redirects, param order, encoding)
- Price format variations (comma, yen symbols, k notation)
- Affiliate link hiding (case variations, URL encoding, nesting)
"""

from __future__ import annotations

import random
import string
import urllib.parse

from hypothesis import strategies as st
from hypothesis.strategies import composite

# Zero-width characters (invisible)
ZERO_WIDTH = ["\u200b", "\u200c", "\u200d", "\ufeff"]

# Weird whitespace characters
WEIRD_SPACES = [" ", "\t", "\n", "\u00a0", "\u2002", "\u2003", "\u2009"]

# Punctuation variations
PUNCT = ["-", "_", ".", "/", "|", "·", "•", "—"]

# Case manipulation strategies
CASE_FUN = ["lower", "upper", "title", "swap"]


@composite
def merchant_name_variants(draw, base: str | None = None):
    """
    Generate merchant name variations that should normalize to same entity.

    Attacker strategies:
    - Case manipulation (lower, UPPER, Title, sWaP)
    - Punctuation insertion (-, _, ., /)
    - Zero-width character injection
    - Weird whitespace
    - Corporate suffixes (Inc, LLC, 公式, ®)
    """
    base_name = base or draw(
        st.sampled_from(["OpenTable", "UberEats", "Tabelog", "Google", "Amazon", "Yelp"])
    )
    s = base_name

    # Case mangling
    mode = draw(st.sampled_from(CASE_FUN))
    if mode == "lower":
        s = s.lower()
    elif mode == "upper":
        s = s.upper()
    elif mode == "title":
        s = s.title()
    elif mode == "swap":
        s = "".join(ch.lower() if ch.isupper() else ch.upper() for ch in s)

    # Insert punctuation / spaces / zero-width
    inserts = draw(
        st.lists(st.sampled_from(PUNCT + WEIRD_SPACES + ZERO_WIDTH), min_size=0, max_size=4)
    )
    for ins in inserts:
        if s:  # Ensure non-empty before inserting
            pos = draw(st.integers(min_value=0, max_value=len(s)))
            s = s[:pos] + ins + s[pos:]

    # Optional suffix like "(Official)" or "Inc."
    suffix = draw(st.sampled_from(["", " Inc", " LLC", " (Official)", "公式", "®"]))
    return s + suffix


@composite
def url_variants(draw):
    """
    Generate URL variations that point to same destination.

    Attacker strategies:
    - Scheme variations (http/https)
    - www prefix presence/absence
    - Tracking parameter order shuffle
    - Percent-encoding in path
    - Fragment additions
    - Host case variations
    """
    domain = draw(st.sampled_from(["example.com", "shop.example.com", "www.example.com"]))
    scheme = draw(st.sampled_from(["http", "https"]))
    path = draw(st.sampled_from(["/item", "/product", "/p/123", "/redirect"]))
    base = f"{scheme}://{domain}{path}"

    # Core params
    core = {"id": str(draw(st.integers(1, 10_000)))}

    # Optional tracking params
    tracking_keys = [
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "ref",
        "aff",
        "tag",
        "fbclid",
        "gclid",
    ]
    tracking = {}
    for k in draw(st.lists(st.sampled_from(tracking_keys), min_size=0, max_size=3, unique=True)):
        tracking[k] = draw(
            st.text(min_size=1, max_size=12, alphabet=string.ascii_letters + string.digits + "-_")
        )

    params = {**core, **tracking}

    # Param order shuffle
    items = list(params.items())
    random.shuffle(items)

    query = urllib.parse.urlencode(items)

    # Percent-encode the path sometimes
    if draw(st.booleans()):
        path2 = urllib.parse.quote(path, safe="/")
        base = f"{scheme}://{domain}{path2}"

    # Optional fragment
    frag = ""
    if draw(st.booleans()):
        frag = "#section-" + str(draw(st.integers(1, 9)))

    # Host uppercase sometimes
    if draw(st.booleans()):
        base = base.replace(domain, domain.upper())

    return base + "?" + query + frag


@composite
def price_strings(draw):
    """
    Generate price representations that should normalize to same value.

    Attacker strategies:
    - Comma separators (12,000)
    - Yen symbols (¥12,000, 12000円)
    - k notation (12k, 12.5k JPY)
    - Extra whitespace
    """
    n = draw(st.integers(min_value=0, max_value=500_000))
    kind = draw(
        st.sampled_from(
            ["plain", "comma", "yen_prefix", "yen_suffix", "k", "k_jpy", "spaces"]
        )
    )

    if kind == "plain":
        return str(n)
    if kind == "comma":
        return f"{n:,}"
    if kind == "yen_prefix":
        return f"¥{n:,}"
    if kind == "yen_suffix":
        return f"{n:,}円"
    if kind == "k":
        return f"{n/1000:.1f}k"
    if kind == "k_jpy":
        return f"{n/1000:.2f}k JPY"
    return f"  ¥ {n:,}  "


@composite
def affiliate_urls(draw):
    """
    Generate affiliate URLs with obfuscation.

    Attacker strategies:
    - Case variations (REF, Aff, aFf)
    - URL encoding (ref%3Dxxx)
    - Nested URL param (url=https%3A%2F%2F...%3Fref%3D)
    """
    base = draw(url_variants())

    # Choose obfuscation mode
    mode = draw(st.sampled_from(["case", "encode", "nested"]))

    if mode == "case":
        # Replace "ref" → "REF" etc if present; else append
        if "ref=" in base.lower():
            # Case variation on ref param
            base = base.replace("ref=", "REF=").replace("Ref=", "REF=")
        else:
            ref_value = draw(
                st.text(min_size=1, max_size=8, alphabet=string.ascii_letters + string.digits)
            )
            return base + "&REF=" + ref_value

    if mode == "encode":
        # Encode "ref=xxx" as part of a param value
        ref_value = draw(
            st.text(min_size=1, max_size=8, alphabet=string.ascii_letters + string.digits)
        )
        ref = "ref=" + ref_value
        return base + "&q=" + urllib.parse.quote(ref)

    # nested
    nested_target = draw(url_variants())
    # Ensure nested has affiliate
    ref_value = draw(
        st.text(min_size=1, max_size=8, alphabet=string.ascii_letters + string.digits)
    )
    nested_target += "&ref=" + ref_value
    return "https://tracker.example/redirect?url=" + urllib.parse.quote(nested_target, safe="")

    return base
