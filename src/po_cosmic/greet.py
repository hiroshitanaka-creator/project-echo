"""
Japanese greeting module for po-cosmic.

なぜこの設計か: Wabi-sabi (侘び寂び) の哲学に従い、
シンプルで誠実な挨拶を提供する。AIと人間の対話の出発点として、
透明性と誠実さを体現する最小単位がこの挨拶である。
"""

from __future__ import annotations


def greet(name: str = "") -> str:
    """
    Return a Japanese greeting.

    なぜこの設計か: 挨拶は対話の基盤。名前を受け取ることで
    個人を尊重し、商業バイアスなく純粋な接続を表現する。

    Args:
        name: Optional name to address. Empty string means anonymous.

    Returns:
        Japanese greeting string.
    """
    if name:
        return f"こんにちは、{name}！"
    return "こんにちは！"
