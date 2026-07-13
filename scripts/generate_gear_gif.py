#!/usr/bin/env python3
"""Generate a spinning iron gear GIF for the HOI4-MCP README banner.

Creates a metallic gear with HOI4-inspired colors (steel, brass, gold)
that rotates smoothly in an infinite loop. Output: assets/gear-spin.gif
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


# ── Configuration ──────────────────────────────────────────────────────────
SIZE = 200  # px, square
NUM_TEETH = 12
TOOTH_HEIGHT = 18
INNER_RADIUS = 52
OUTER_RADIUS = INNER_RADIUS + TOOTH_HEIGHT
HOLE_RADIUS = 16
NUM_FRAMES = 30
DURATION = 40  # ms per frame → ~1.2s per full rotation at 30 frames
BG_COLOR = (27, 30, 34, 0)  # transparent BG in RGBA

# HOI4-inspired metallic palette
STEEL_DARK = (45, 55, 65)
STEEL_MID = (75, 85, 95)
STEEL_LIGHT = (130, 140, 150)
BRASS = (201, 168, 76)
BRASS_DARK = (160, 130, 50)
GOLD_HIGHLIGHT = (220, 195, 120)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


# ── Gear geometry ──────────────────────────────────────────────────────────
def gear_polygon(cx: float, cy: float, angle_offset: float) -> list[tuple[float, float]]:
    """Compute the outer polygon of a gear centered at (cx, cy)."""
    points: list[tuple[float, float]] = []
    for i in range(NUM_TEETH * 2):
        angle = angle_offset + (math.pi * 2 * i) / (NUM_TEETH * 2)
        if i % 2 == 0:
            # Tooth tip
            r = OUTER_RADIUS
        else:
            # Valley between teeth
            r = INNER_RADIUS
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    return points


def draw_gear(draw: ImageDraw.ImageDraw, cx: float, cy: float, angle: float):
    """Draw a single gear frame at the given rotation angle."""
    poly = gear_polygon(cx, cy, angle)

    # Gear body (outer polygon)
    draw.polygon(poly, fill=STEEL_MID, outline=STEEL_DARK)

    # Tooth tips — lighter stroke for depth
    for i in range(0, len(poly), 2):
        draw.point(poly[i], fill=STEEL_LIGHT)

    # Inner ring
    draw.ellipse(
        [cx - INNER_RADIUS, cy - INNER_RADIUS, cx + INNER_RADIUS, cy + INNER_RADIUS],
        fill=STEEL_DARK,
        outline=STEEL_MID,
        width=2,
    )

    # Brass accent ring
    accent_r = INNER_RADIUS - 6
    draw.ellipse(
        [cx - accent_r, cy - accent_r, cx + accent_r, cy + accent_r],
        outline=BRASS,
        width=3,
    )

    # Central hub
    hub_r = INNER_RADIUS - 14
    draw.ellipse(
        [cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r],
        fill=STEEL_MID,
        outline=BRASS_DARK,
        width=2,
    )

    # Center hole
    draw.ellipse(
        [cx - HOLE_RADIUS, cy - HOLE_RADIUS, cx + HOLE_RADIUS, cy + HOLE_RADIUS],
        fill=BG_COLOR[:3],
        outline=STEEL_DARK,
        width=2,
    )

    # Spokes (4 diagonal lines from hub to accent ring)
    for spoke_angle in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
        spoke_a = spoke_angle + angle
        x1 = cx + (hub_r + 2) * math.cos(spoke_a)
        y1 = cy + (hub_r + 2) * math.sin(spoke_a)
        x2 = cx + (accent_r - 2) * math.cos(spoke_a)
        y2 = cy + (accent_r - 2) * math.sin(spoke_a)
        draw.line([(x1, y1), (x2, y2)], fill=BRASS_DARK, width=4)

    # Highlight arc (top-left quadrant for metallic sheen)
    highlight_r = INNER_RADIUS - 10
    bbox = [cx - highlight_r, cy - highlight_r, cx + highlight_r, cy + highlight_r]
    draw.arc(bbox, start=210, end=330, fill=GOLD_HIGHLIGHT, width=2)


# ── Frame generation ───────────────────────────────────────────────────────
def make_frame(angle: float) -> Image.Image:
    """Render one gear frame at the given rotation."""
    img = Image.new("RGBA", (SIZE, SIZE), BG_COLOR)
    draw = ImageDraw.Draw(img)
    cx = cy = SIZE / 2
    draw_gear(draw, cx, cy, angle)
    return img


def generate_gear_gif(output_path: Path) -> None:
    """Generate the full spinning gear GIF."""
    frames: list[Image.Image] = []
    angle_step = (2 * math.pi) / NUM_FRAMES

    for i in range(NUM_FRAMES):
        angle = i * angle_step
        frame = make_frame(angle)
        frames.append(frame)

    # Save as looping GIF
    frames[0].save(
        str(output_path),
        save_all=True,
        append_images=frames[1:],
        duration=DURATION,
        loop=0,  # infinite loop
        disposal=2,  # clear previous frame
        transparency=0,
        optimize=False,  # keep quality for metallic gradients
    )
    print(f"✅ Generated {output_path} ({NUM_FRAMES} frames, {SIZE}×{SIZE}px)")


if __name__ == "__main__":
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    output = ASSETS_DIR / "gear-spin.gif"
    generate_gear_gif(output)
