"""Generate the Project Echo Flying Pig animated GIF.

Produces assets/pig_flying.gif — commit the output, not this script.

Requirements: Pillow>=10.0.0
    pip install Pillow
    # or: pip install -e ".[demo]"

Usage:
    python assets/flying_pig_anim.py
    python assets/flying_pig_anim.py --output assets/pig_flying.gif
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path


def _draw_pig(draw, cx: int, cy: int, size: int, color: tuple) -> None:
    """Draw a geometric pig (body + ears + snout) — no emoji font needed."""
    from PIL import ImageDraw  # noqa: F401 (type hint only)

    # Body (ellipse)
    bw, bh = size, int(size * 0.8)
    draw.ellipse([cx - bw, cy - bh, cx + bw, cy + bh], fill=color)

    # Ears (small circles)
    ear_r = size // 3
    draw.ellipse(
        [cx - bw + ear_r // 2, cy - bh - ear_r, cx - bw + ear_r + ear_r // 2, cy - bh],
        fill=color,
    )
    draw.ellipse(
        [cx + bw - ear_r - ear_r // 2, cy - bh - ear_r, cx + bw - ear_r // 2, cy - bh],
        fill=color,
    )

    # Snout (lighter oval)
    sr = size // 3
    snout_color = tuple(min(255, c + 40) for c in color)
    draw.ellipse([cx - sr, cy, cx + sr, cy + sr + 4], fill=snout_color)

    # Eyes (dark dots)
    eye_r = max(2, size // 8)
    draw.ellipse([cx - bw // 2 - eye_r, cy - bh // 2 - eye_r, cx - bw // 2 + eye_r, cy - bh // 2 + eye_r], fill=(40, 20, 20))
    draw.ellipse([cx + bw // 2 - eye_r, cy - bh // 2 - eye_r, cx + bw // 2 + eye_r, cy - bh // 2 + eye_r], fill=(40, 20, 20))


def generate_gif(output_path: Path) -> None:
    """Render 8-frame looped GIF of a flying pig with Echo Mark ripples."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Error: Pillow is required. Install with: pip install Pillow")
        raise

    W, H = 220, 130
    N_FRAMES = 8
    DURATION_MS = 130

    SKY_TOP = (100, 180, 240)
    SKY_BOT = (170, 220, 255)
    PIG_COLOR = (255, 160, 160)
    RIPPLE_COLOR = (80, 200, 120)
    TEXT_COLOR = (60, 40, 20)

    frames: list[Image.Image] = []

    for i in range(N_FRAMES):
        # Sky gradient background
        img = Image.new("RGB", (W, H), SKY_TOP)
        draw = ImageDraw.Draw(img)
        for y in range(H):
            t = y / H
            r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # Echo Mark ripple rings (expand over frames)
        ripple_cx, ripple_cy = W // 2, H // 2 + 20
        for ring in range(3):
            base_r = 10 + ring * 18
            r_size = base_r + i * 4
            alpha_val = max(0, 200 - ring * 50 - i * 15)
            if r_size < W and alpha_val > 10:
                draw.ellipse(
                    [ripple_cx - r_size, ripple_cy - r_size, ripple_cx + r_size, ripple_cy + r_size],
                    outline=RIPPLE_COLOR + (alpha_val,) if img.mode == "RGBA" else RIPPLE_COLOR,
                    width=2,
                )

        # Flying pig — oscillates vertically (sine wave)
        pig_cx = W // 2
        pig_cy = 48 + int(12 * math.sin(i * math.pi / 4))
        pig_size = 22
        _draw_pig(draw, pig_cx, pig_cy, pig_size, PIG_COLOR)

        # Speech bubble "Buhi!" appears from frame 2
        if i >= 2:
            bubble_x, bubble_y = pig_cx + pig_size + 6, pig_cy - pig_size - 8
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            text = "Buhi!"
            tw = len(text) * 6
            th = 12
            draw.rounded_rectangle(
                [bubble_x - 4, bubble_y - 2, bubble_x + tw + 4, bubble_y + th + 2],
                radius=4,
                fill=(255, 255, 220),
                outline=(180, 140, 80),
                width=1,
            )
            draw.text((bubble_x, bubble_y), text, fill=TEXT_COLOR, font=font)

        # Convert to palette mode for GIF
        frames.append(img.convert("P", palette=Image.ADAPTIVE, dither=0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=DURATION_MS,
        optimize=True,
    )
    print(f"GIF written to: {output_path}  ({N_FRAMES} frames × {DURATION_MS}ms)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Project Echo Flying Pig animated GIF")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "pig_flying.gif"),
        help="Output GIF path (default: assets/pig_flying.gif)",
    )
    args = parser.parse_args()
    generate_gif(Path(args.output))


if __name__ == "__main__":
    main()
