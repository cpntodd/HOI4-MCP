#!/usr/bin/env python3
"""Generate the complete HOI4-MCP banner asset suite.

Produces:
  assets/gear-cluster-left.gif   — 3-gear cluster (left variant)
  assets/gear-cluster-right.gif  — 3-gear cluster (right variant, mirrored)
  assets/banner-title.png        — Military-style title plate

All gear clusters feature a large central gear with two smaller meshing
satellite gears, with proper tooth ratios and counter-rotation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ── Fonts ──────────────────────────────────────────────────────────────────
FONT_GOTHIC = "/usr/share/fonts/opentype/urw-base35/URWGothic-Demi.otf"
FONT_NARROW_BOLD = "/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Bold.otf"

# ── Shared palette ─────────────────────────────────────────────────────────
BG_BLACK = (22, 24, 28, 0)         # transparent dark
STEEL_BASE  = (108, 113, 122)
STEEL_DARK  = (68, 73, 80)
STEEL_SHADOW = (48, 52, 58)
STEEL_HIGHLIGHT = (158, 163, 172)
STEEL_TIP   = (178, 183, 192)
HUB_COLOR   = (93, 98, 106)
HUB_RIM     = (128, 133, 140)
BORE_COLOR  = (22, 24, 28)
GOLD        = (201, 168, 76)
GOLD_LIGHT  = (225, 200, 130)
GOLD_DARK   = (160, 130, 50)

# ── Banner colours ─────────────────────────────────────────────────────────
BANNER_BG      = (20, 22, 30)       # near-black steel
BANNER_BORDER  = (55, 60, 68)       # subtle border
RIVET_COLOR    = (90, 95, 102)
RIVET_HIGHLIGHT = (140, 145, 152)


# ═══════════════════════════════════════════════════════════════════════════
# PART 1: GEAR CLUSTER GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GearDef:
    """Definition of a single gear within a cluster."""
    cx: float; cy: float      # center position
    outer_r: int; inner_r: int
    hub_r: int; hole_r: int
    num_teeth: int; num_spokes: int
    direction: int             # 1 = CW, -1 = CCW
    phase: float = 0.0         # starting rotation offset


# ── Left cluster: large gear right-of-center, small gears on left ──────────
# Canvas 280×260
GEARS_LEFT = [
    GearDef(cx=180, cy=130, outer_r=70, inner_r=54, hub_r=18, hole_r=7,
            num_teeth=16, num_spokes=5, direction=1, phase=0.0),
    GearDef(cx=80, cy=58,  outer_r=42, inner_r=32, hub_r=12, hole_r=5,
            num_teeth=10, num_spokes=4, direction=-1, phase=math.pi/10),
    GearDef(cx=65, cy=185, outer_r=36, inner_r=28, hub_r=10, hole_r=4,
            num_teeth=9,  num_spokes=3, direction=-1, phase=-math.pi/9),
]

# ── Right cluster: mirrored version of left ────────────────────────────────
GEARS_RIGHT = [
    GearDef(cx=100, cy=130, outer_r=70, inner_r=54, hub_r=18, hole_r=7,
            num_teeth=16, num_spokes=5, direction=-1, phase=0.0),
    GearDef(cx=200, cy=58,  outer_r=42, inner_r=32, hub_r=12, hole_r=5,
            num_teeth=10, num_spokes=4, direction=1, phase=math.pi/10),
    GearDef(cx=215, cy=185, outer_r=36, inner_r=28, hub_r=10, hole_r=4,
            num_teeth=9,  num_spokes=3, direction=1, phase=-math.pi/9),
]

CLUSTER_SIZE = (280, 260)
NUM_FRAMES = 30
FRAME_DURATION = 40  # ms


# ── Tooth geometry ─────────────────────────────────────────────────────────
def tooth_corners(gd: GearDef, tooth_idx: int, base_angle: float
                  ) -> list[tuple[float, float]]:
    """Return [tip_left, tip_right, root_right, root_left] for a tooth."""
    pitch = 2 * math.pi / gd.num_teeth
    tip_hw = pitch * 0.22
    root_hw = pitch * 0.28
    center = base_angle + tooth_idx * pitch
    or_ = gd.outer_r
    ir = gd.inner_r
    cx, cy = gd.cx, gd.cy

    return [
        (cx + or_ * math.cos(center - tip_hw), cy + or_ * math.sin(center - tip_hw)),
        (cx + or_ * math.cos(center + tip_hw), cy + or_ * math.sin(center + tip_hw)),
        (cx + ir * math.cos(center + root_hw), cy + ir * math.sin(center + root_hw)),
        (cx + ir * math.cos(center - root_hw), cy + ir * math.sin(center - root_hw)),
    ]


def draw_single_gear(draw: ImageDraw.ImageDraw, gd: GearDef, angle: float):
    """Draw one complete gear at the given rotation angle."""
    cx, cy = gd.cx, gd.cy
    or_ = gd.outer_r
    ir = gd.inner_r
    rim_inner = gd.inner_r - 12

    # Shadow disk
    draw.ellipse([cx - or_ - 2, cy - or_ + 1, cx + or_ + 2, cy + or_ + 3],
                 fill=STEEL_SHADOW)

    # Teeth
    for i in range(gd.num_teeth):
        corners = tooth_corners(gd, i, angle)
        tl, tr, rr, rl = corners
        center_angle = angle + i * (2 * math.pi / gd.num_teeth)
        face_n = -math.cos(center_angle) * 0.7 - math.sin(center_angle) * 0.7

        if face_n > 0.15:
            fill = STEEL_HIGHLIGHT
        elif face_n < -0.15:
            fill = STEEL_DARK
        else:
            fill = STEEL_BASE

        draw.polygon(corners, fill=fill, outline=STEEL_SHADOW)
        draw.line([tl, tr], fill=STEEL_TIP, width=2)

        # Valley shadow
        nc = tooth_corners(gd, (i + 1) % gd.num_teeth, angle)
        vm = (cx + ir * 0.97 * math.cos(center_angle + math.pi / gd.num_teeth),
              cy + ir * 0.97 * math.sin(center_angle + math.pi / gd.num_teeth))
        draw.polygon([rr, nc[3], vm], fill=STEEL_SHADOW)

    # Outer rim
    draw.ellipse([cx - or_ + 3, cy - or_ + 3, cx + or_ - 3, cy + or_ - 3],
                 outline=STEEL_DARK, width=2)

    # Inner rim
    draw.ellipse([cx - rim_inner, cy - rim_inner, cx + rim_inner, cy + rim_inner],
                 fill=STEEL_DARK)
    draw.arc([cx - rim_inner, cy - rim_inner, cx + rim_inner, cy + rim_inner],
             start=200, end=340, fill=STEEL_HIGHLIGHT, width=2)

    # Spokes
    for sp in range(gd.num_spokes):
        sa = (angle * 0.3 * gd.direction + gd.phase
              + sp * (2 * math.pi / gd.num_spokes))
        ir2 = gd.hub_r + 3
        or2 = rim_inner - 4
        hwi, hwo = 0.08, 0.06
        sc = [
            (cx + ir2 * math.cos(sa - hwi), cy + ir2 * math.sin(sa - hwi)),
            (cx + ir2 * math.cos(sa + hwi), cy + ir2 * math.sin(sa + hwi)),
            (cx + or2 * math.cos(sa + hwo), cy + or2 * math.sin(sa + hwo)),
            (cx + or2 * math.cos(sa - hwo), cy + or2 * math.sin(sa - hwo)),
        ]
        b = -math.cos(sa) * 0.7 - math.sin(sa) * 0.7
        draw.polygon(sc, fill=STEEL_BASE if b > 0 else STEEL_DARK,
                     outline=STEEL_SHADOW)

    # Hub
    draw.ellipse([cx - gd.hub_r, cy - gd.hub_r, cx + gd.hub_r, cy + gd.hub_r],
                 fill=HUB_COLOR, outline=HUB_RIM, width=2)
    draw.arc([cx - gd.hub_r + 3, cy - gd.hub_r + 3,
              cx + gd.hub_r - 3, cy + gd.hub_r - 3],
             start=200, end=340, fill=STEEL_HIGHLIGHT, width=2)

    # Bore + keyway
    draw.ellipse([cx - gd.hole_r, cy - gd.hole_r,
                  cx + gd.hole_r, cy + gd.hole_r],
                 fill=BORE_COLOR, outline=STEEL_SHADOW, width=2)
    kw = gd.hole_r // 2 + 1
    kd = gd.hole_r // 2 + 1
    kw_c = []
    for kx, ky in [(cx - kw/2, cy - gd.hole_r - kd),
                   (cx + kw/2, cy - gd.hole_r - kd),
                   (cx + kw/2, cy - gd.hole_r),
                   (cx - kw/2, cy - gd.hole_r)]:
        dx, dy = kx - cx, ky - cy
        kw_c.append((cx + dx * math.cos(angle) - dy * math.sin(angle),
                      cy + dx * math.sin(angle) + dy * math.cos(angle)))
    draw.polygon(kw_c, fill=BORE_COLOR, outline=STEEL_SHADOW, width=1)

    # Outer highlight
    har = or_ - 1
    draw.arc([cx - har, cy - har, cx + har, cy + har],
             start=210, end=330, fill=STEEL_TIP, width=2)


def render_cluster_frame(gears: list[GearDef], base_angle: float) -> Image.Image:
    """Render one frame of a gear cluster.

    The base_angle drives the primary (largest) gear. Satellite gears
    counter-rotate at teeth-ratio speeds.
    """
    img = Image.new("RGBA", CLUSTER_SIZE, BG_BLACK)
    draw = ImageDraw.Draw(img)

    primary = gears[0]
    draw_single_gear(draw, primary, base_angle * primary.direction)

    for gd in gears[1:]:
        # Counter-rotate at ratio of teeth counts
        ratio = primary.num_teeth / gd.num_teeth
        sat_angle = -base_angle * primary.direction * ratio + gd.phase
        draw_single_gear(draw, gd, sat_angle)

    return img


def generate_cluster_gif(gears: list[GearDef], path: Path, label: str):
    """Generate a looping gear-cluster GIF."""
    frames = []
    step = (2 * math.pi) / NUM_FRAMES

    for i in range(NUM_FRAMES):
        frames.append(render_cluster_frame(gears, i * step))

    frames[0].save(
        str(path), save_all=True, append_images=frames[1:],
        duration=FRAME_DURATION, loop=0, disposal=2,
        transparency=0, optimize=False,
    )
    print(f"✅ {label}: {path}")


# ═══════════════════════════════════════════════════════════════════════════
# PART 2: MILITARY-STYLE TITLE BANNER
# ═══════════════════════════════════════════════════════════════════════════

BANNER_W = 640
BANNER_H = 140


def draw_rivet(draw: ImageDraw.ImageDraw, x: int, y: int):
    """Draw a single metal rivet with highlight and shadow."""
    r = 5
    draw.ellipse([x - r, y - r, x + r, y + r], fill=RIVET_COLOR)
    draw.ellipse([x - r + 2, y - r + 1, x + r - 2, y + r - 3],
                 fill=RIVET_HIGHLIGHT)
    draw.point((x - 1, y - 1), fill=(180, 185, 190))


def draw_chevron(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int):
    """Draw a small military chevron marker (▶)."""
    pts = [
        (cx - size, cy - size),
        (cx + size, cy),
        (cx - size, cy + size),
    ]
    draw.polygon(pts, fill=GOLD)


def generate_banner() -> None:
    """Generate the military-style title banner plate."""
    img = Image.new("RGBA", (BANNER_W, BANNER_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Background plate with subtle border ──
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, BANNER_W - margin, BANNER_H - margin],
        radius=8, fill=BANNER_BG, outline=BANNER_BORDER, width=2,
    )

    # ── Inner decorative border (thin gold line) ──
    inner_m = 12
    draw.rectangle(
        [inner_m, inner_m, BANNER_W - inner_m, BANNER_H - inner_m],
        outline=GOLD_DARK, width=1,
    )

    # ── Corner rivets ──
    for rx, ry in [(20, 20), (BANNER_W - 20, 20),
                   (20, BANNER_H - 20), (BANNER_W - 20, BANNER_H - 20)]:
        draw_rivet(draw, rx, ry)
    # Extra rivets along top/bottom edges
    for rx in [BANNER_W // 2 - 80, BANNER_W // 2 + 80]:
        draw_rivet(draw, rx, 20)
        draw_rivet(draw, rx, BANNER_H - 20)

    # ── Top accent line with chevrons ──
    line_y = 32
    draw.line([(30, line_y), (BANNER_W - 30, line_y)], fill=GOLD_DARK, width=1)
    for cx in [BANNER_W // 2 - 60, BANNER_W // 2 + 60]:
        draw_chevron(draw, cx, line_y, 5)

    # ── Bottom accent line ──
    line_y2 = BANNER_H - 28
    draw.line([(30, line_y2), (BANNER_W - 30, line_y2)], fill=GOLD_DARK, width=1)
    for cx in [BANNER_W // 2 - 60, BANNER_W // 2 + 60]:
        draw_chevron(draw, cx, line_y2, 5)

    # ── Title text: "HOI4-MCP" ──
    try:
        font_title = ImageFont.truetype(FONT_GOTHIC, 52)
        font_sub = ImageFont.truetype(FONT_NARROW_BOLD, 18)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    title = "HOI4-MCP"
    subtitle = "AI-ASSISTED  HOI4  MODDING  FRAMEWORK"

    # Title with gold gradient effect (draw dark shadow first, then gold)
    tx = BANNER_W // 2
    ty = 62

    # Shadow
    bbox_s = draw.textbbox((0, 0), title, font=font_title)
    tw_s = bbox_s[2] - bbox_s[0]
    draw.text((tx - tw_s // 2 + 2, ty - 16 + 2), title,
              fill=(10, 12, 16), font=font_title)
    # Main gold text
    draw.text((tx - tw_s // 2, ty - 16), title,
              fill=GOLD, font=font_title)
    # Light highlight on top half
    draw.text((tx - tw_s // 2, ty - 18), title,
              fill=GOLD_LIGHT, font=font_title)

    # Subtitle
    bbox_sub = draw.textbbox((0, 0), subtitle, font=font_sub)
    sw = bbox_sub[2] - bbox_sub[0]
    draw.text((tx - sw // 2, ty + 30), subtitle,
              fill=(180, 190, 200), font=font_sub)

    # ── Small tactical crosses flanking subtitle ──
    cross_size = 4
    for cxx in [tx - sw // 2 - 20, tx + sw // 2 + 20]:
        cyy = ty + 38
        draw.line([(cxx - cross_size, cyy), (cxx + cross_size, cyy)],
                  fill=GOLD_DARK, width=1)
        draw.line([(cxx, cyy - cross_size), (cxx, cyy + cross_size)],
                  fill=GOLD_DARK, width=1)

    # ── Save ──
    path = ASSETS_DIR / "banner-title.png"
    img.save(str(path))
    print(f"✅ Banner title: {path}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    generate_cluster_gif(GEARS_LEFT, ASSETS_DIR / "gear-cluster-left.gif",
                         "Left cluster")
    generate_cluster_gif(GEARS_RIGHT, ASSETS_DIR / "gear-cluster-right.gif",
                         "Right cluster")
    generate_banner()
    print("✅ All banner assets generated.")
