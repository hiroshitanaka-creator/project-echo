"""
Input normalization for adversarial robustness.

This module provides normalization functions to handle adversarial input variations:
- Merchant names (case, punctuation, zero-width chars, corporate suffixes)
- Prices (comma separators, yen symbols, k notation)
- URLs (scheme, param order, encoding)

These normalizations ensure that bias detection is stable across evasion attempts.
"""

from __future__ import annotations

import re
import unicodedata
import urllib.parse
from typing import Any


def normalize_merchant(name: str) -> str:
    """
    Normalize merchant name to canonical form.

    Handles adversarial variations:
    - Case manipulation (lower, UPPER, Title, sWaP)
    - Punctuation/whitespace insertion (-, _, ., /, |, ·, •, —)
    - Zero-width character injection (\u200b, \u200c, \u200d, \ufeff)
    - Weird whitespace (\u00a0, \u2002, \u2003, \u2009)
    - Corporate suffixes (Inc, LLC, (Official), 公式, ®, ™, ©)

    Strategy:
    1. Unicode normalization (NFC)
    2. Remove zero-width characters
    3. Normalize whitespace (including weird unicode spaces)
    4. Remove punctuation
    5. Lowercase
    6. Remove corporate suffixes
    7. Strip and deduplicate spaces

    Returns:
        Canonical merchant name (lowercase, no punctuation, no suffixes)
    """
    if not name:
        return ""

    # 1. Unicode normalization (NFC - composed form)
    s = unicodedata.normalize("NFC", name)

    # 2. Remove zero-width characters
    zero_width = ["\u200b", "\u200c", "\u200d", "\ufeff"]
    for zw in zero_width:
        s = s.replace(zw, "")

    # 3. Normalize whitespace (replace all whitespace variants with space)
    # Includes: \t, \n, \u00a0 (non-breaking space), \u2002-\u2009 (various spaces)
    s = re.sub(r"\s+", " ", s)

    # 4. Remove punctuation and special characters (keep only alphanumeric and spaces)
    # This handles: -, _, ., /, |, ·, •, —, etc.
    s = re.sub(r"[^\w\s]", "", s, flags=re.UNICODE)

    # 5. Lowercase
    s = s.lower()

    # 6. Remove common corporate suffixes
    # English: Inc, LLC, Ltd, Corp, Co, Company, (Official)
    # Japanese: 公式, 株式会社, 会社
    # Symbols: ®, ™, ©
    suffixes = [
        r"\binc\b",
        r"\bllc\b",
        r"\bltd\b",
        r"\bcorp\b",
        r"\bco\b",
        r"\bcompany\b",
        r"\bofficial\b",
        r"公式",
        r"株式会社",
        r"会社",
        r"®",
        r"™",
        r"©",
    ]
    for suffix in suffixes:
        s = re.sub(suffix, "", s, flags=re.IGNORECASE)

    # 7. Strip and deduplicate spaces
    s = " ".join(s.split())

    return s


def normalize_price(price_str: str) -> float | None:
    """
    Parse price string to float, handling various formats.

    Handles adversarial variations:
    - Comma separators (12,000)
    - Yen symbols (¥12,000, 12000円, 円12000)
    - k notation (12k, 12.5k JPY)
    - Extra whitespace
    - Mixed formats (¥ 12,000 円)

    Strategy:
    1. Remove whitespace
    2. Remove currency symbols (¥, 円, JPY, $, etc.)
    3. Handle k notation (multiply by 1000)
    4. Remove commas
    5. Parse float

    Returns:
        Numeric price value, or None if parsing fails
    """
    if not price_str:
        return None

    # 1. Remove all whitespace
    s = price_str.strip().replace(" ", "").replace("\t", "").replace("\n", "")

    # 2. Remove currency symbols
    # ¥, 円, $, €, £, JPY, USD, EUR, GBP
    s = s.replace("¥", "").replace("円", "").replace("$", "").replace("€", "").replace("£", "")
    s = re.sub(r"(?i)(jpy|usd|eur|gbp)", "", s)

    # 3. Handle k notation (12k → 12000, 12.5k → 12500)
    k_match = re.match(r"^([\d,.]+)k$", s, re.IGNORECASE)
    if k_match:
        num_str = k_match.group(1)
        num_str = num_str.replace(",", "")
        try:
            value = float(num_str) * 1000
            return value
        except ValueError:
            return None

    # 4. Remove commas
    s = s.replace(",", "")

    # 5. Parse float
    try:
        return float(s)
    except ValueError:
        return None


def canonicalize_url(url: str) -> str:
    """
    Canonicalize URL to normalized form.

    Handles adversarial variations:
    - Scheme variations (http/https)
    - www prefix presence/absence
    - Tracking parameter order shuffle
    - Percent-encoding in path
    - Fragment additions
    - Host case variations
    - Trailing slashes

    Strategy:
    1. Parse URL
    2. Normalize scheme (always https)
    3. Normalize host (lowercase, remove www prefix)
    4. Normalize path (decode percent-encoding, remove trailing slash)
    5. Sort query parameters (ignore tracking params like utm_*, fbclid, gclid)
    6. Remove fragment
    7. Reconstruct

    Returns:
        Canonical URL string
    """
    if not url:
        return ""

    # 1. Parse URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        # If parsing fails, return lowercase version as fallback
        return url.lower()

    # 2. Normalize scheme (always https)
    scheme = "https"

    # 3. Normalize host (lowercase, remove www prefix)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    # 4. Normalize path (decode percent-encoding, remove trailing slash)
    path = urllib.parse.unquote(parsed.path)
    if path.endswith("/") and len(path) > 1:
        path = path[:-1]

    # 5. Filter and sort query parameters
    # Remove tracking params: utm_*, fbclid, gclid, ref, aff, tag, etc.
    tracking_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "ref",
        "aff",
        "tag",
        "affiliate",
        "source",
    }

    query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    # Filter out tracking params
    filtered = {k: v for k, v in query_params.items() if k.lower() not in tracking_params}
    # Sort by key for deterministic output
    sorted_params = sorted(filtered.items())
    # Reconstruct query string (use first value if list)
    query_parts = []
    for k, v_list in sorted_params:
        if v_list:
            query_parts.append(f"{k}={v_list[0]}")
        else:
            query_parts.append(k)
    query = "&".join(query_parts)

    # 6. Remove fragment (ignored)

    # 7. Reconstruct
    canonical = f"{scheme}://{host}{path}"
    if query:
        canonical += f"?{query}"

    return canonical


def normalize_rec(rec_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a recommendation dictionary.

    Applies all normalization functions to relevant fields:
    - merchant → normalize_merchant()
    - price (if string) → normalize_price()
    - Any URL fields → canonicalize_url()

    Returns:
        Normalized recommendation dictionary
    """
    normalized = dict(rec_dict)

    # Normalize merchant
    if "merchant" in normalized and isinstance(normalized["merchant"], str):
        normalized["merchant"] = normalize_merchant(normalized["merchant"])

    # Normalize price (if it's a string)
    if "price" in normalized and isinstance(normalized["price"], str):
        parsed_price = normalize_price(normalized["price"])
        if parsed_price is not None:
            normalized["price"] = parsed_price

    # Normalize URLs (common fields: url, link, affiliate_url, product_url)
    url_fields = ["url", "link", "affiliate_url", "product_url"]
    for field in url_fields:
        if field in normalized and isinstance(normalized[field], str):
            normalized[field] = canonicalize_url(normalized[field])

    return normalized
