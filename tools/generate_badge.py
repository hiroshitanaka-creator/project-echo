"""Generate Echo Mark SVG badge from a badge JSON file.

Usage:
    python tools/generate_badge.py runs/high_bias_affiliate.badge.json
    python tools/generate_badge.py runs/badge.json -o my_badge.svg
    make generate-badge BADGE=runs/high_bias_affiliate.badge.json
"""

from __future__ import annotations

import argparse
import colorsys
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Label configuration
# ---------------------------------------------------------------------------

LABEL_CONFIG: dict[str, dict] = {
    "ECHO_VERIFIED": {
        "bg": "#27ae60",
        "fg": "#ffffff",
        "text": "ECHO VERIFIED",
        "ripple": True,
    },
    "ECHO_CHECK": {
        "bg": "#e67e22",
        "fg": "#ffffff",
        "text": "ECHO CHECK",
        "ripple": False,
    },
    "ECHO_BLOCKED": {
        "bg": "#c0392b",
        "fg": "#ffffff",
        "text": "ECHO BLOCKED",
        "ripple": False,
    },
}

# ---------------------------------------------------------------------------
# SVG template
# ---------------------------------------------------------------------------

_BADGE_TEMPLATE = """\
<svg xmlns="http://www.w3.org/2000/svg" width="240" height="80" viewBox="0 0 240 80">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{bg_top}"/>
      <stop offset="100%" stop-color="{bg_bot}"/>
    </linearGradient>
    {ripple_defs}
  </defs>

  <!-- Badge body -->
  <rect width="240" height="80" rx="10" ry="10" fill="url(#bg)"/>
  <rect width="240" height="80" rx="10" ry="10" fill="none"
        stroke="{fg}" stroke-width="1.5" stroke-opacity="0.4"/>

  <!-- Pig glyph -->
  <text x="22" y="50" font-family="serif" font-size="32" fill="{fg}">🐷</text>

  <!-- Ripple animation (VERIFIED only) -->
  {ripple_circles}

  <!-- Label lines -->
  <text x="68" y="32" font-family="monospace" font-size="13" font-weight="bold"
        fill="{fg}" letter-spacing="1">{label_text}</text>
  <text x="68" y="50" font-family="monospace" font-size="10"
        fill="{fg}" opacity="0.85">v1 certified flying pig</text>
  <text x="68" y="66" font-family="monospace" font-size="9"
        fill="{fg}" opacity="0.7">{schema}</text>
</svg>
"""

_RIPPLE_DEFS = """\
    <style>
      .rpl { animation: rpl 2s infinite ease-out; transform-origin: 30px 42px; }
      @keyframes rpl {
        0%   { opacity: 0.6; r: 18; }
        100% { opacity: 0; r: 42; }
      }
    </style>"""

_RIPPLE_CIRCLES = """\
  <circle class="rpl" cx="30" cy="42" r="18" fill="none"
          stroke="{fg}" stroke-width="1.5" style="animation-delay:0s"/>
  <circle class="rpl" cx="30" cy="42" r="18" fill="none"
          stroke="{fg}" stroke-width="1" opacity="0.5" style="animation-delay:0.7s"/>"""


# ---------------------------------------------------------------------------
# SVG generation
# ---------------------------------------------------------------------------


def _darken_hex(hex_color: str, factor: float = 0.82) -> str:
    """Return a darkened version of a hex colour string."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    hue, sat, val = colorsys.rgb_to_hsv(r, g, b)
    rd, gd, bd = colorsys.hsv_to_rgb(hue, sat, val * factor)
    return "#{:02x}{:02x}{:02x}".format(int(rd * 255), int(gd * 255), int(bd * 255))


def generate_svg(badge: dict) -> str:
    """Generate SVG badge string from a parsed badge dict."""
    label = str(badge.get("label", "ECHO_BLOCKED"))
    config = LABEL_CONFIG.get(label, LABEL_CONFIG["ECHO_BLOCKED"])

    bg_top = config["bg"]
    bg_bot = _darken_hex(bg_top)
    fg = config["fg"]

    ripple_defs = _RIPPLE_DEFS if config["ripple"] else ""
    ripple_circles = _RIPPLE_CIRCLES.format(fg=fg) if config["ripple"] else ""

    schema = str(badge.get("schema_version", "echo_mark_v3"))

    return _BADGE_TEMPLATE.format(
        bg_top=bg_top,
        bg_bot=bg_bot,
        fg=fg,
        label_text=config["text"],
        schema=schema,
        ripple_defs=ripple_defs,
        ripple_circles=ripple_circles,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Echo Mark SVG badge from a badge JSON file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("badge_json", help="Path to badge JSON file")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output SVG path (default: <badge_json stem>.svg alongside input)",
    )
    args = parser.parse_args()

    badge_path = Path(args.badge_json)
    if not badge_path.exists():
        print(f"Error: {badge_path} not found", file=sys.stderr)
        sys.exit(1)

    badge = json.loads(badge_path.read_text(encoding="utf-8"))
    svg = generate_svg(badge)

    out_path = Path(args.output) if args.output else badge_path.with_suffix(".svg")
    out_path.write_text(svg, encoding="utf-8")

    print(f"SVG badge written to: {out_path}")
    print(f"Label  : {badge.get('label', '(not found)')}")
    print(f"Schema : {badge.get('schema_version', '(not found)')}")


if __name__ == "__main__":
    main()
