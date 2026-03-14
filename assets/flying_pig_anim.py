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


def _draw_cute_pig(draw, cx: int, cy: int, size: int, wing_flap: float) -> None:
    """Draw a cute flying pig: round body, wings, rosy cheeks, smile."""
    # ---- colours ----
    BODY    = (255, 182, 193)   # pink
    SHADOW  = (230, 140, 160)   # darker pink for inner ears / snout holes
    WHITE   = (255, 255, 255)
    EYE     = (50,  30,  30)
    SHINE   = (255, 255, 255)
    CHEEK   = (255, 120, 140, 180)  # semi-transparent blush
    OUTLINE = (200,  90, 110)
    WING    = (255, 230, 200)   # warm cream for wings
    WING_OL = (220, 180, 140)

    bw = int(size * 1.0)   # body half-width
    bh = int(size * 0.85)  # body half-height

    # --- little curly tail (right side) ---
    tx, ty = cx + bw - 2, cy + bh // 2
    for k in range(6):
        a = math.radians(k * 60)
        tr = 5 - k * 0.5
        draw.ellipse([
            tx + int(tr * math.cos(a)) - 2,
            ty + int(tr * math.sin(a)) - 2,
            tx + int(tr * math.cos(a)) + 2,
            ty + int(tr * math.sin(a)) + 2,
        ], fill=SHADOW, outline=None)

    # --- wings (left & right, flap with wing_flap) ---
    wing_dy = int(6 * math.sin(wing_flap))
    # left wing
    lw_pts = [
        (cx - bw + 4,          cy - wing_dy),
        (cx - bw - int(size * 0.7), cy - int(size * 0.35) - wing_dy),
        (cx - bw - int(size * 0.5), cy + int(size * 0.1)),
        (cx - bw + 2,          cy + int(size * 0.2)),
    ]
    draw.polygon(lw_pts, fill=WING, outline=WING_OL)
    # right wing
    rw_pts = [
        (cx + bw - 4,          cy - wing_dy),
        (cx + bw + int(size * 0.7), cy - int(size * 0.35) - wing_dy),
        (cx + bw + int(size * 0.5), cy + int(size * 0.1)),
        (cx + bw - 2,          cy + int(size * 0.2)),
    ]
    draw.polygon(rw_pts, fill=WING, outline=WING_OL)

    # --- body ---
    draw.ellipse([cx - bw, cy - bh, cx + bw, cy + bh], fill=BODY, outline=OUTLINE, width=2)

    # --- round ears ---
    er = int(size * 0.28)
    # left ear (behind body tint)
    draw.ellipse([cx - bw + 2, cy - bh - er + 4, cx - bw + 2 + er * 2, cy - bh + 4], fill=BODY, outline=OUTLINE, width=2)
    draw.ellipse([cx - bw + 5, cy - bh - er + 8, cx - bw + er * 2 - 1, cy - bh + 2], fill=SHADOW)
    # right ear
    draw.ellipse([cx + bw - 2 - er * 2, cy - bh - er + 4, cx + bw - 2, cy - bh + 4], fill=BODY, outline=OUTLINE, width=2)
    draw.ellipse([cx + bw - er * 2 + 1, cy - bh - er + 8, cx + bw - 5, cy - bh + 2], fill=SHADOW)

    # --- snout ---
    sr = int(size * 0.32)
    draw.ellipse([cx - sr, cy + int(bh * 0.3), cx + sr, cy + int(bh * 0.3) + int(sr * 1.1)], fill=SHADOW, outline=OUTLINE, width=1)
    # nostrils
    nr = max(2, sr // 4)
    draw.ellipse([cx - sr // 2 - nr, cy + int(bh * 0.45) - nr, cx - sr // 2 + nr, cy + int(bh * 0.45) + nr], fill=EYE)
    draw.ellipse([cx + sr // 2 - nr, cy + int(bh * 0.45) - nr, cx + sr // 2 + nr, cy + int(bh * 0.45) + nr], fill=EYE)

    # --- eyes (big, shiny) ---
    eye_r  = max(4, int(size * 0.14))
    eye_y  = cy - int(bh * 0.25)
    eye_lx = cx - int(bw * 0.38)
    eye_rx = cx + int(bw * 0.38)
    for ex in (eye_lx, eye_rx):
        draw.ellipse([ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r], fill=WHITE)
        draw.ellipse([ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r], outline=EYE, width=1)
        draw.ellipse([ex - eye_r + 1, eye_y - eye_r + 1, ex + eye_r - 1, eye_y + eye_r - 1], fill=EYE)
        # shine dot
        sh = max(1, eye_r // 3)
        draw.ellipse([ex - eye_r + 2, eye_y - eye_r + 2, ex - eye_r + 2 + sh, eye_y - eye_r + 2 + sh], fill=SHINE)

    # --- rosy cheeks ---
    ck_r = int(size * 0.22)
    ck_y  = cy + int(bh * 0.1)
    for ckx in (cx - int(bw * 0.55), cx + int(bw * 0.55)):
        draw.ellipse([ckx - ck_r, ck_y - ck_r // 2, ckx + ck_r, ck_y + ck_r // 2], fill=(255, 140, 160, 120))

    # --- smile ---
    sm_w, sm_h = int(size * 0.35), int(size * 0.12)
    sm_y = cy + int(bh * 0.15)
    draw.arc([cx - sm_w, sm_y, cx + sm_w, sm_y + sm_h * 2], start=10, end=170, fill=OUTLINE, width=2)


def generate_gif(output_path: Path) -> None:
    """Render 10-frame looped GIF of a cute flying pig with Echo Mark ripples."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Error: Pillow is required. Install with: pip install Pillow")
        raise

    W, H = 260, 160
    N_FRAMES = 10
    DURATION_MS = 110

    SKY_TOP  = (135, 206, 250)
    SKY_BOT  = (200, 235, 255)
    CLOUD    = (255, 255, 255)
    RIPPLE   = (100, 210, 140)
    TEXT_FG  = (80, 40, 20)

    # Static cloud positions
    CLOUDS = [(30, 20, 70, 36), (160, 12, 210, 26), (100, 40, 130, 50)]

    font_default = ImageFont.load_default()

    frames: list[Image.Image] = []

    for i in range(N_FRAMES):
        phase = i * 2 * math.pi / N_FRAMES

        # Sky gradient
        img = Image.new("RGBA", (W, H), SKY_TOP)
        draw = ImageDraw.Draw(img)
        for y in range(H):
            t = y / H
            r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

        # Drifting clouds
        for (x0, y0, x1, y1) in CLOUDS:
            drift = int(4 * math.sin(phase + x0))
            draw.ellipse([x0 + drift, y0, x1 + drift, y1], fill=(255, 255, 255, 220))

        # Echo Mark ripples (spread from centre)
        rc_x, rc_y = W // 2, H // 2 + 30
        for ring in range(4):
            phase_offset = (i + ring * 2.5) % N_FRAMES
            r_size = int(12 + phase_offset * 5)
            opacity = max(0, int(200 - phase_offset * 22))
            if opacity > 10:
                draw.ellipse(
                    [rc_x - r_size, rc_y - r_size, rc_x + r_size, rc_y + r_size],
                    outline=RIPPLE + (opacity,),
                    width=2,
                )

        # Flying pig — smooth vertical bob + gentle horizontal sway
        pig_cx = W // 2 + int(8 * math.sin(phase * 0.7))
        pig_cy = int(H * 0.38) + int(14 * math.sin(phase))
        pig_size = 28
        wing_flap = phase * 2  # wings flap twice per body bob
        _draw_cute_pig(draw, pig_cx, pig_cy, pig_size, wing_flap)

        # Speech bubble "Buhi!" after first quarter
        if i >= 2:
            bx = pig_cx + pig_size + 10
            by = pig_cy - pig_size - 14
            text = "Buhi!"
            tw = len(text) * 6 + 2
            th = 13
            draw.rounded_rectangle(
                [bx - 5, by - 4, bx + tw + 4, by + th + 4],
                radius=5,
                fill=(255, 255, 230, 230),
                outline=(200, 140, 80, 255),
                width=1,
            )
            # bubble tail
            draw.polygon([(bx, by + th + 4), (bx - 6, by + th + 10), (bx + 6, by + th + 4)], fill=(255, 255, 230, 230))
            draw.text((bx, by), text, fill=TEXT_FG, font=font_default)

        # Convert to palette (required for GIF)
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
