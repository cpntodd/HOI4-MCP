#!/usr/bin/env python3
"""Generate the complete HOI4-MCP banner asset suite.

Produces:
  assets/gear-cluster-left.gif   — 3-gear cluster (left variant)
  assets/gear-cluster-right.gif  — 3-gear cluster (right variant, mirrored)
  assets/banner-title.gif        — Animated military title plate
                                   with pixel-art tank firing animation

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
BANNER_FRAMES = 30
BANNER_DURATION = 60  # ms per frame

# ── Pixel art tank sprite (from reference: green body, black outline) ──────
# Characters: #=outline(black), G=body(dark olive), g=body highlight
#             B=barrel, T=tread dark, W=wheel, .=transparent
TANK_W = 36  # sprite columns
TANK_H = 16  # sprite rows

TANK_SPRITE = [
    # 0         1         2         3
    # 0123456789012345678901234567890123456
    list("..................................."),  # 0
    list("...................####..........."),  # 1
    list("..................#GGGG#.........."),  # 2
    list(".................#gGGGG##........."),  # 3
    list("......####.......#GGGGGG#........."),  # 4
    list("......#BB#######GgGGGGG#........."),  # 5  barrel starts
    list("......#BBB#GGGG#GGGGGG#........."),  # 6
    list("......####B#GGGG#GGGGGG#........."),  # 7
    list(".........#B#GGGG#GGGGG##........"),  # 8
    list(".........##B#GGG#GGGG#G##......."),  # 9  turret/hull
    list("..........###GGG#GGG#GGG##......"),  # 10 hull slope
    list("............#GGGGGGGGGGG##......"),  # 11 hull bottom
    list("............#TTTTTTTTTTT##......"),  # 12 tread top
    list("...........#TWWTTWWTTWWT##......"),  # 13 wheels
    list("...........################....."),  # 14 tread bottom
    list("..................................."),  # 15
]

TANK_COLORS = {
    '#': (20, 22, 18),     # black outline
    'G': (75, 90, 55),     # dark olive body
    'g': (95, 110, 72),    # lighter olive highlight
    'B': (55, 65, 42),     # barrel (slightly darker)
    'T': (38, 42, 32),     # tread
    'W': (58, 62, 50),     # wheel
    '.': None,              # transparent
}

# Animation: barrel recoil + muzzle flash sequence
# (barrel_x_shorten, flash_pixels_list)
FIRING_SEQUENCE = [
    (0, []),                     # idle
    (0, []),                     # idle
    (0, []),                     # idle
    (0, []),                     # idle
    (-2, []),                    # barrel starts recoil
    (-4, [(5, 6), (5, 7), (6, 5), (6, 6), (4, 6)]),  # muzzle flash!
    (-3, [(5, 6), (6, 5)]),      # fading flash
    (-1, []),                    # recovering
    (0, []),                     # back to idle
    (0, []),                     # idle
]


def draw_tank(draw: ImageDraw.ImageDraw, ox: int, oy: int,
              barrel_shorten: int, flashes: list[tuple[int, int]],
              px: int = 2):
    """Draw pixel-art tank at (ox, oy). barrel_shorten > 0 shortens the barrel."""
    for row_idx, row in enumerate(TANK_SPRITE):
        for col_idx, ch in enumerate(row):
            color = TANK_COLORS.get(ch)
            if color is None:
                continue

            # Shorten barrel: skip barrel pixels at the right end
            eff_col = col_idx
            if ch in ('B',) and barrel_shorten > 0 and col_idx >= 8:
                # Check if this barrel pixel is near the tip
                barrel_rightmost = max(c for c, v in enumerate(row) if v == 'B')
                if col_idx > barrel_rightmost - barrel_shorten:
                    continue  # skip this pixel (barrel recoiled)

            x = ox + eff_col * px
            y = oy + row_idx * px
            draw.rectangle(
                [x, y, x + px - 1, y + px - 1], fill=color)

    # Muzzle flash (yellow-orange ellipses)
    for fr, fc in flashes:
        fx = ox + fc * px
        fy = oy + fr * px
        for di, fclr in enumerate(
            [(255, 240, 60), (255, 200, 30), (255, 150, 15), (255, 100, 10)]
        ):
            r = 3 - di
            if r > 0:
                draw.ellipse(
                    [fx - r, fy - r, fx + r, fy + r], fill=fclr)


# ── Static plate (background, borders, rivets, text) ──────────────────────
def draw_static_plate(draw: ImageDraw.ImageDraw):
    """Draw the non-animated military title plate background."""
    m = 4
    draw.rounded_rectangle(
        [m, m, BANNER_W - m, BANNER_H - m],
        radius=8, fill=BANNER_BG, outline=BANNER_BORDER, width=2)

    im = 12
    draw.rectangle([im, im, BANNER_W - im, BANNER_H - im],
                   outline=GOLD_DARK, width=1)

    # Rivets (corners + midpoints)
    for rx, ry in [(20, 20), (BANNER_W - 20, 20),
                   (20, BANNER_H - 20), (BANNER_W - 20, BANNER_H - 20)]:
        r = 5
        draw.ellipse([rx - r, ry - r, rx + r, ry + r], fill=RIVET_COLOR)
        draw.ellipse([rx - r + 2, ry - r + 1, rx + r - 2, ry + r - 3],
                     fill=RIVET_HIGHLIGHT)
        draw.point((rx - 1, ry - 1), fill=(180, 185, 190))
    for rx in [BANNER_W // 2 - 80, BANNER_W // 2 + 80]:
        for ry in [20, BANNER_H - 20]:
            r = 5
            draw.ellipse([rx - r, ry - r, rx + r, ry + r], fill=RIVET_COLOR)
            draw.ellipse([rx - r + 2, ry - r + 1, rx + r - 2, ry + r - 3],
                         fill=RIVET_HIGHLIGHT)
            draw.point((rx - 1, ry - 1), fill=(180, 185, 190))

    # Top accent line + chevrons
    ly = 32
    draw.line([(30, ly), (BANNER_W - 30, ly)], fill=GOLD_DARK, width=1)
    for cx in [BANNER_W // 2 - 60, BANNER_W // 2 + 60]:
        draw.polygon([(cx - 5, ly - 5), (cx + 5, ly), (cx - 5, ly + 5)],
                     fill=GOLD)

    # Bottom accent line + chevrons
    ly2 = BANNER_H - 30
    draw.line([(30, ly2), (BANNER_W - 30, ly2)], fill=GOLD_DARK, width=1)
    for cx in [BANNER_W // 2 - 60, BANNER_W // 2 + 60]:
        draw.polygon([(cx - 5, ly2 - 5), (cx + 5, ly2), (cx - 5, ly2 + 5)],
                     fill=GOLD)


# ── Animated banner generation ─────────────────────────────────────────────
def generate_animated_banner() -> None:
    """Generate animated military title banner with pixel tank firing."""
    frames = []

    # Tank positioned bottom-left
    tank_x = 20
    tank_y = BANNER_H - 8 - TANK_H * 2  # 2px per pixel

    for i in range(BANNER_FRAMES):
        img = Image.new("RGBA", (BANNER_W, BANNER_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw_static_plate(draw)

        # Title text
        try:
            font_title = ImageFont.truetype(FONT_GOTHIC, 52)
            font_sub = ImageFont.truetype(FONT_NARROW_BOLD, 18)
        except OSError:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        title = "HOI4-MCP"
        subtitle = "AI-ASSISTED  HOI4  MODDING  FRAMEWORK"
        TX, TY = BANNER_W // 2, 60

        bb = draw.textbbox((0, 0), title, font=font_title)
        tw = bb[2] - bb[0]
        draw.text((TX - tw // 2 + 2, TY - 16 + 2), title,
                  fill=(10, 12, 16), font=font_title)
        draw.text((TX - tw // 2, TY - 16), title, fill=GOLD, font=font_title)
        draw.text((TX - tw // 2, TY - 18), title, fill=GOLD_LIGHT, font=font_title)

        bb2 = draw.textbbox((0, 0), subtitle, font=font_sub)
        sw = bb2[2] - bb2[0]
        draw.text((TX - sw // 2, TY + 30), subtitle,
                  fill=(180, 190, 200), font=font_sub)

        # Tactical crosses
        cs = 4
        for cxx in [TX - sw // 2 - 20, TX + sw // 2 + 20]:
            cyy = TY + 38
            draw.line([(cxx - cs, cyy), (cxx + cs, cyy)], fill=GOLD_DARK, width=1)
            draw.line([(cxx, cyy - cs), (cxx, cyy + cs)], fill=GOLD_DARK, width=1)

        # Animated tank
        seq = FIRING_SEQUENCE[i % len(FIRING_SEQUENCE)]
        barrel_shorten, flashes = seq
        recoil_x = -1 if barrel_shorten > 0 else 0
        draw_tank(draw, tank_x + recoil_x, tank_y, barrel_shorten, flashes, px=2)

        frames.append(img)

    path = ASSETS_DIR / "banner-title.gif"
    frames[0].save(
        str(path), save_all=True, append_images=frames[1:],
        duration=BANNER_DURATION, loop=0, disposal=2,
        transparency=0, optimize=False,
    )
    print(f"✅ Banner title (animated): {path}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    generate_cluster_gif(GEARS_LEFT, ASSETS_DIR / "gear-cluster-left.gif",
                         "Left cluster")
    generate_cluster_gif(GEARS_RIGHT, ASSETS_DIR / "gear-cluster-right.gif",
                         "Right cluster")
    generate_animated_banner()
    print("✅ All banner assets generated.")
