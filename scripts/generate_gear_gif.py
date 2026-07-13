#!/usr/bin/env python3
"""Generate a spinning mechanical gear GIF for the HOI4-MCP README banner.

Produces a realistic industrial gear with involute-style tooth profiles,
face shading, keyway, and metallic gray tones — inspired by mechanical
gear reference imagery. Output: assets/gear-spin.gif
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw


# ── Configuration ──────────────────────────────────────────────────────────
SIZE = 240  # px, square canvas
NUM_TEETH = 16
OUTER_RADIUS = 88   # tip of teeth
INNER_RADIUS = 68   # root between teeth
HUB_RADIUS = 24     # central solid hub
HOLE_RADIUS = 10    # center bore
KEYWAY_WIDTH = 5    # keyway slot width
KEYWAY_DEPTH = 5    # keyway depth beyond hole radius
RIM_INNER = 52      # inner edge of the outer rim
NUM_FRAMES = 30
DURATION = 40       # ms per frame
PRESSURE_ANGLE = math.radians(22)  # tooth side angle off radial

# Metallic grays with cool undertone (matches reference)
BG_FILL = (22, 24, 28, 0)       # near-black, transparent
STEEL_BASE = (110, 115, 125)     # mid-gray body
STEEL_DARK = (70, 75, 82)        # shadowed recesses
STEEL_SHADOW = (50, 54, 60)     # deep shadows
STEEL_HIGHLIGHT = (160, 165, 175)  # lit faces
STEEL_TIP = (180, 185, 195)     # tooth tip highlight
HUB_COLOR = (95, 100, 108)      # hub slightly darker than body
HUB_RIM = (130, 135, 142)       # hub rim highlight
BORE_COLOR = (22, 24, 28)       # center hole (matches BG)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


# ── Involute-style tooth geometry ──────────────────────────────────────────
def tooth_corners(
    cx: float, cy: float, tooth_index: int, total_teeth: int, base_angle: float
) -> list[tuple[float, float]]:
    """Return the 4 corners of a trapezoidal tooth.

    Each tooth has a flat outer tip (arc segment) and angled sides.
    Returns [tip_left, tip_right, root_right, root_left] in order.
    """
    pitch = 2 * math.pi / total_teeth
    # Tooth occupies ~45% of the pitch at the tip, ~55% at the root
    tip_half_width = pitch * 0.22   # angular half-width of tooth tip
    root_half_width = pitch * 0.28  # angular half-width at root

    center_angle = base_angle + tooth_index * pitch

    # Tip corners (outer radius)
    tip_left = (
        cx + OUTER_RADIUS * math.cos(center_angle - tip_half_width),
        cy + OUTER_RADIUS * math.sin(center_angle - tip_half_width),
    )
    tip_right = (
        cx + OUTER_RADIUS * math.cos(center_angle + tip_half_width),
        cy + OUTER_RADIUS * math.sin(center_angle + tip_half_width),
    )

    # Root corners (inner radius, wider base)
    root_right = (
        cx + INNER_RADIUS * math.cos(center_angle + root_half_width),
        cy + INNER_RADIUS * math.sin(center_angle + root_half_width),
    )
    root_left = (
        cx + INNER_RADIUS * math.cos(center_angle - root_half_width),
        cy + INNER_RADIUS * math.sin(center_angle - root_half_width),
    )

    return [tip_left, tip_right, root_right, root_left]


def draw_gear_body(draw: ImageDraw.ImageDraw, cx: float, cy: float, angle: float):
    """Draw the main gear: teeth, rim, hub, spokes, and bore."""
    # ── Step 1: Dark under-disk (shadow/base silhouette) ──
    draw.ellipse(
        [cx - OUTER_RADIUS - 2, cy - OUTER_RADIUS + 1,
         cx + OUTER_RADIUS + 2, cy + OUTER_RADIUS + 3],
        fill=STEEL_SHADOW,
    )

    # ── Step 2: Draw each tooth individually with face shading ──
    for i in range(NUM_TEETH):
        corners = tooth_corners(cx, cy, i, NUM_TEETH, angle)
        tip_left, tip_right, root_right, root_left = corners
        center_angle = angle + i * (2 * math.pi / NUM_TEETH)

        # Determine which side faces the light (light from upper-left)
        cos_a = math.cos(center_angle)
        sin_a = math.sin(center_angle)
        # Light direction: from top-left (-0.7, -0.7)
        face_normal = -cos_a * 0.7 - sin_a * 0.7

        if face_normal > 0.15:
            # Tooth faces the light — brighter
            tooth_fill = STEEL_HIGHLIGHT
            side_fill = STEEL_BASE
        elif face_normal < -0.15:
            # Tooth faces away — darker
            tooth_fill = STEEL_DARK
            side_fill = STEEL_SHADOW
        else:
            tooth_fill = STEEL_BASE
            side_fill = STEEL_DARK

        # Draw tooth body
        draw.polygon(corners, fill=tooth_fill, outline=STEEL_SHADOW)

        # Tip highlight line
        draw.line([tip_left, tip_right], fill=STEEL_TIP, width=2)

        # Root fill (the valley to the right of this tooth)
        next_corners = tooth_corners(cx, cy, (i + 1) % NUM_TEETH, NUM_TEETH, angle)
        valley = [root_right, next_corners[3], next_corners[2], next_corners[1]]
        # Only fill the valley area
        draw.polygon(
            [root_right, next_corners[3],
             (cx + INNER_RADIUS * 0.98 * math.cos(center_angle + math.pi / NUM_TEETH),
              cy + INNER_RADIUS * 0.98 * math.sin(center_angle + math.pi / NUM_TEETH))],
            fill=STEEL_SHADOW,
        )

    # ── Step 3: Outer rim ring ──
    draw.ellipse(
        [cx - OUTER_RADIUS + 3, cy - OUTER_RADIUS + 3,
         cx + OUTER_RADIUS - 3, cy + OUTER_RADIUS - 3],
        outline=STEEL_DARK, width=2,
    )

    # ── Step 4: Inner rim (recessed area between teeth and hub) ──
    draw.ellipse(
        [cx - RIM_INNER, cy - RIM_INNER, cx + RIM_INNER, cy + RIM_INNER],
        fill=STEEL_DARK,
    )
    # Inner rim highlight (top edge catches light)
    draw.arc(
        [cx - RIM_INNER, cy - RIM_INNER, cx + RIM_INNER, cy + RIM_INNER],
        start=200, end=340, fill=STEEL_HIGHLIGHT, width=2,
    )

    # ── Step 5: Spokes (5 spokes for industrial look) ──
    for sp in range(5):
        spoke_angle = angle * 0.3 + sp * (2 * math.pi / 5)  # spokes rotate slower than teeth
        inner_r = HUB_RADIUS + 3
        outer_r = RIM_INNER - 4

        # Each spoke is a tapered trapezoid
        half_w_inner = 0.08  # angular half-width at hub
        half_w_outer = 0.06  # angular half-width at rim

        spoke_corners = [
            (cx + inner_r * math.cos(spoke_angle - half_w_inner),
             cy + inner_r * math.sin(spoke_angle - half_w_inner)),
            (cx + inner_r * math.cos(spoke_angle + half_w_inner),
             cy + inner_r * math.sin(spoke_angle + half_w_inner)),
            (cx + outer_r * math.cos(spoke_angle + half_w_outer),
             cy + outer_r * math.sin(spoke_angle + half_w_outer)),
            (cx + outer_r * math.cos(spoke_angle - half_w_outer),
             cy + outer_r * math.sin(spoke_angle - half_w_outer)),
        ]
        # Shade based on orientation
        cos_s = math.cos(spoke_angle)
        sin_s = math.sin(spoke_angle)
        spoke_bright = -cos_s * 0.7 - sin_s * 0.7
        if spoke_bright > 0:
            spoke_fill = STEEL_BASE
            spoke_outline = STEEL_SHADOW
        else:
            spoke_fill = STEEL_DARK
            spoke_outline = STEEL_SHADOW

        draw.polygon(spoke_corners, fill=spoke_fill, outline=spoke_outline)

    # ── Step 6: Hub (solid center) ──
    draw.ellipse(
        [cx - HUB_RADIUS, cy - HUB_RADIUS, cx + HUB_RADIUS, cy + HUB_RADIUS],
        fill=HUB_COLOR, outline=HUB_RIM, width=2,
    )
    # Hub face highlight
    draw.arc(
        [cx - HUB_RADIUS + 3, cy - HUB_RADIUS + 3,
         cx + HUB_RADIUS - 3, cy + HUB_RADIUS - 3],
        start=200, end=340, fill=STEEL_HIGHLIGHT, width=2,
    )

    # ── Step 7: Center bore with keyway ──
    draw.ellipse(
        [cx - HOLE_RADIUS, cy - HOLE_RADIUS, cx + HOLE_RADIUS, cy + HOLE_RADIUS],
        fill=BORE_COLOR, outline=STEEL_SHADOW, width=2,
    )
    # Keyway slot (rectangular notch at top of bore)
    kw_x1 = cx - KEYWAY_WIDTH / 2
    kw_x2 = cx + KEYWAY_WIDTH / 2
    kw_y1 = cy - HOLE_RADIUS - KEYWAY_DEPTH
    kw_y2 = cy - HOLE_RADIUS
    # Rotate keyway with gear
    kw_angle = angle
    kw_corners_rot = []
    for kx, ky in [(kw_x1, kw_y1), (kw_x2, kw_y1), (kw_x2, kw_y2), (kw_x1, kw_y2)]:
        dx, dy = kx - cx, ky - cy
        rx = cx + dx * math.cos(kw_angle) - dy * math.sin(kw_angle)
        ry = cy + dx * math.sin(kw_angle) + dy * math.cos(kw_angle)
        kw_corners_rot.append((rx, ry))
    draw.polygon(kw_corners_rot, fill=BORE_COLOR, outline=STEEL_SHADOW, width=1)

    # ── Step 8: Outer rim edge highlight (catches light on top-left) ──
    highlight_arc_r = OUTER_RADIUS - 1
    draw.arc(
        [cx - highlight_arc_r, cy - highlight_arc_r,
         cx + highlight_arc_r, cy + highlight_arc_r],
        start=210, end=330, fill=STEEL_TIP, width=2,
    )


# ── Frame generation ───────────────────────────────────────────────────────
def make_frame(angle: float) -> Image.Image:
    """Render one gear frame at the given rotation angle."""
    img = Image.new("RGBA", (SIZE, SIZE), BG_FILL)
    draw = ImageDraw.Draw(img)
    cx = cy = SIZE / 2
    draw_gear_body(draw, cx, cy, angle)
    return img


def generate_gear_gif(output_path: Path) -> None:
    """Generate the full spinning gear GIF."""
    frames: list[Image.Image] = []
    angle_step = (2 * math.pi) / NUM_FRAMES

    for i in range(NUM_FRAMES):
        angle = i * angle_step
        frame = make_frame(angle)
        frames.append(frame)

    frames[0].save(
        str(output_path),
        save_all=True,
        append_images=frames[1:],
        duration=DURATION,
        loop=0,
        disposal=2,
        transparency=0,
        optimize=False,
    )
    print(f"✅ Generated {output_path} ({NUM_FRAMES} frames, {SIZE}×{SIZE}px)")


if __name__ == "__main__":
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    output = ASSETS_DIR / "gear-spin.gif"
    generate_gear_gif(output)

