#!/usr/bin/env python3
"""Generate spinning mechanical gear GIFs for the HOI4-MCP README banner.

Produces two realistic industrial gear variants (left and right) with
involute-style tooth profiles, directional face shading, keyways, and
metallic gray tones. Output: assets/gear-left.gif, assets/gear-right.gif
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


# ── Gear configuration ─────────────────────────────────────────────────────
@dataclass
class GearConfig:
    """Parameters for a single gear variant."""
    size: int            # canvas px (square)
    num_teeth: int
    outer_radius: int    # tip of teeth
    inner_radius: int    # root between teeth
    hub_radius: int
    hole_radius: int
    keyway_width: int
    keyway_depth: int
    rim_inner: int       # inner edge of outer rim
    num_spokes: int
    direction: int       # 1 = clockwise, -1 = counter-clockwise
    spoke_phase_offset: float  # radians, for visual variety


# Left gear: larger, 16 teeth, counter-clockwise, 5 spokes
GEAR_LEFT = GearConfig(
    size=220, num_teeth=16,
    outer_radius=80, inner_radius=62,
    hub_radius=22, hole_radius=9,
    keyway_width=5, keyway_depth=4,
    rim_inner=48, num_spokes=5,
    direction=-1, spoke_phase_offset=0.0,
)

# Right gear: slightly smaller, 14 teeth, clockwise, 6 spokes
GEAR_RIGHT = GearConfig(
    size=200, num_teeth=14,
    outer_radius=70, inner_radius=54,
    hub_radius=20, hole_radius=8,
    keyway_width=4, keyway_depth=4,
    rim_inner=42, num_spokes=6,
    direction=1, spoke_phase_offset=math.pi / 6,
)

NUM_FRAMES = 30
DURATION = 40  # ms per frame

# ── Metallic palette (cool grays with subtle blue undertone) ───────────────
BG_FILL = (22, 24, 28, 0)          # near-black, transparent
STEEL_BASE = (108, 113, 122)       # mid-gray body
STEEL_DARK = (68, 73, 80)          # shadowed recesses
STEEL_SHADOW = (48, 52, 58)        # deep shadows
STEEL_HIGHLIGHT = (158, 163, 172)  # lit faces
STEEL_TIP = (178, 183, 192)        # tooth tip catch light
HUB_COLOR = (93, 98, 106)          # hub
HUB_RIM = (128, 133, 140)          # hub rim highlight
BORE_COLOR = (22, 24, 28)          # center hole

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


# ── Involute-style tooth geometry ──────────────────────────────────────────
def tooth_corners(
    cx: float, cy: float, tooth_index: int,
    cfg: GearConfig, base_angle: float,
) -> list[tuple[float, float]]:
    """Return [tip_left, tip_right, root_right, root_left] for a trapezoidal tooth."""
    pitch = 2 * math.pi / cfg.num_teeth
    tip_hw = pitch * 0.22
    root_hw = pitch * 0.28
    center = base_angle + tooth_index * pitch

    tip_left = (
        cx + cfg.outer_radius * math.cos(center - tip_hw),
        cy + cfg.outer_radius * math.sin(center - tip_hw),
    )
    tip_right = (
        cx + cfg.outer_radius * math.cos(center + tip_hw),
        cy + cfg.outer_radius * math.sin(center + tip_hw),
    )
    root_right = (
        cx + cfg.inner_radius * math.cos(center + root_hw),
        cy + cfg.inner_radius * math.sin(center + root_hw),
    )
    root_left = (
        cx + cfg.inner_radius * math.cos(center - root_hw),
        cy + cfg.inner_radius * math.sin(center - root_hw),
    )
    return [tip_left, tip_right, root_right, root_left]


# ── Gear drawing ───────────────────────────────────────────────────────────
def draw_gear(draw: ImageDraw.ImageDraw, cx: float, cy: float,
              angle: float, cfg: GearConfig):
    """Draw a complete gear: teeth, rim, spokes, hub, bore, keyway."""
    or_ = cfg.outer_radius
    ir = cfg.inner_radius

    # Shadow disk
    draw.ellipse(
        [cx - or_ - 2, cy - or_ + 1, cx + or_ + 2, cy + or_ + 3],
        fill=STEEL_SHADOW,
    )

    # Teeth with per-face shading
    for i in range(cfg.num_teeth):
        corners = tooth_corners(cx, cy, i, cfg, angle)
        tl, tr, rr, rl = corners
        center_angle = angle + i * (2 * math.pi / cfg.num_teeth)
        face_normal = -math.cos(center_angle) * 0.7 - math.sin(center_angle) * 0.7

        if face_normal > 0.15:
            tooth_fill = STEEL_HIGHLIGHT
        elif face_normal < -0.15:
            tooth_fill = STEEL_DARK
        else:
            tooth_fill = STEEL_BASE

        draw.polygon(corners, fill=tooth_fill, outline=STEEL_SHADOW)
        draw.line([tl, tr], fill=STEEL_TIP, width=2)

        # Valley shadow
        nc = tooth_corners(cx, cy, (i + 1) % cfg.num_teeth, cfg, angle)
        valley_mid = (
            cx + ir * 0.97 * math.cos(center_angle + math.pi / cfg.num_teeth),
            cy + ir * 0.97 * math.sin(center_angle + math.pi / cfg.num_teeth),
        )
        draw.polygon([rr, nc[3], valley_mid], fill=STEEL_SHADOW)

    # Outer rim ring
    draw.ellipse(
        [cx - or_ + 3, cy - or_ + 3, cx + or_ - 3, cy + or_ - 3],
        outline=STEEL_DARK, width=2,
    )

    # Recessed inner rim
    draw.ellipse(
        [cx - cfg.rim_inner, cy - cfg.rim_inner,
         cx + cfg.rim_inner, cy + cfg.rim_inner],
        fill=STEEL_DARK,
    )
    draw.arc(
        [cx - cfg.rim_inner, cy - cfg.rim_inner,
         cx + cfg.rim_inner, cy + cfg.rim_inner],
        start=200, end=340, fill=STEEL_HIGHLIGHT, width=2,
    )

    # Spokes
    for sp in range(cfg.num_spokes):
        spoke_angle = (angle * 0.3 * cfg.direction
                       + cfg.spoke_phase_offset
                       + sp * (2 * math.pi / cfg.num_spokes))
        inner_r = cfg.hub_radius + 3
        outer_r = cfg.rim_inner - 4
        hw_in = 0.08
        hw_out = 0.06

        sc = [
            (cx + inner_r * math.cos(spoke_angle - hw_in),
             cy + inner_r * math.sin(spoke_angle - hw_in)),
            (cx + inner_r * math.cos(spoke_angle + hw_in),
             cy + inner_r * math.sin(spoke_angle + hw_in)),
            (cx + outer_r * math.cos(spoke_angle + hw_out),
             cy + outer_r * math.sin(spoke_angle + hw_out)),
            (cx + outer_r * math.cos(spoke_angle - hw_out),
             cy + outer_r * math.sin(spoke_angle - hw_out)),
        ]
        bright = -math.cos(spoke_angle) * 0.7 - math.sin(spoke_angle) * 0.7
        fill = STEEL_BASE if bright > 0 else STEEL_DARK
        draw.polygon(sc, fill=fill, outline=STEEL_SHADOW)

    # Hub
    draw.ellipse(
        [cx - cfg.hub_radius, cy - cfg.hub_radius,
         cx + cfg.hub_radius, cy + cfg.hub_radius],
        fill=HUB_COLOR, outline=HUB_RIM, width=2,
    )
    draw.arc(
        [cx - cfg.hub_radius + 3, cy - cfg.hub_radius + 3,
         cx + cfg.hub_radius - 3, cy + cfg.hub_radius - 3],
        start=200, end=340, fill=STEEL_HIGHLIGHT, width=2,
    )

    # Bore + keyway
    draw.ellipse(
        [cx - cfg.hole_radius, cy - cfg.hole_radius,
         cx + cfg.hole_radius, cy + cfg.hole_radius],
        fill=BORE_COLOR, outline=STEEL_SHADOW, width=2,
    )
    kw_x1 = cx - cfg.keyway_width / 2
    kw_x2 = cx + cfg.keyway_width / 2
    kw_y1 = cy - cfg.hole_radius - cfg.keyway_depth
    kw_y2 = cy - cfg.hole_radius
    kw_corners = []
    for kx, ky in [(kw_x1, kw_y1), (kw_x2, kw_y1), (kw_x2, kw_y2), (kw_x1, kw_y2)]:
        dx, dy = kx - cx, ky - cy
        rx = cx + dx * math.cos(angle) - dy * math.sin(angle)
        ry = cy + dx * math.sin(angle) + dy * math.cos(angle)
        kw_corners.append((rx, ry))
    draw.polygon(kw_corners, fill=BORE_COLOR, outline=STEEL_SHADOW, width=1)

    # Outer highlight arc
    har = or_ - 1
    draw.arc(
        [cx - har, cy - har, cx + har, cy + har],
        start=210, end=330, fill=STEEL_TIP, width=2,
    )


# ── Frame / GIF generation ─────────────────────────────────────────────────
def make_frame(cfg: GearConfig, angle: float) -> Image.Image:
    """Render one frame."""
    img = Image.new("RGBA", (cfg.size, cfg.size), BG_FILL)
    draw = ImageDraw.Draw(img)
    draw_gear(draw, cfg.size / 2, cfg.size / 2, angle, cfg)
    return img


def generate_gear_gif(cfg: GearConfig, output_path: Path, label: str) -> None:
    """Generate a looping gear GIF."""
    frames: list[Image.Image] = []
    angle_step = (2 * math.pi) / NUM_FRAMES * cfg.direction

    for i in range(NUM_FRAMES):
        angle = i * angle_step
        frames.append(make_frame(cfg, angle))

    frames[0].save(
        str(output_path),
        save_all=True, append_images=frames[1:],
        duration=DURATION, loop=0, disposal=2,
        transparency=0, optimize=False,
    )
    print(f"✅ {label}: {output_path} ({NUM_FRAMES}f, {cfg.size}×{cfg.size}px, "
          f"{cfg.num_teeth}t, {cfg.num_spokes}s)")


# ── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    generate_gear_gif(GEAR_LEFT, ASSETS_DIR / "gear-left.gif", "Left gear")
    generate_gear_gif(GEAR_RIGHT, ASSETS_DIR / "gear-right.gif", "Right gear")

