"""Main menu, character selection, death screen, and victory screen — polished game lobby."""
from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    BG_COLOR, MENU_TEXT, MENU_TITLE, MENU_HIGHLIGHT,
    WHITE, GOLD, HUD_BORDER,
)


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
_BG1   = (4,   2,  10)
_BG2   = (10,  6,  20)
_BG3   = (18, 12,  30)
_ST    = (42, 38,  56)
_ST2   = (62, 56,  78)
_ST3   = (26, 22,  38)
_GLD   = (200,165,  30)
_GLDT  = (240,210,  80)
_GLDD  = (110, 85,  16)
_PUR   = ( 90, 55, 170)
_PURLT = (140, 95, 220)

# Class accent colours (warrior, rogue, mage)
_CLS_COLS = {
    "warrior": (190, 130,  50),
    "rogue":   ( 60, 190, 100),
    "mage":    ( 90, 140, 230),
}


# ---------------------------------------------------------------------------
# Animated background
# ---------------------------------------------------------------------------

class _BgRenderer:
    """Procedural dungeon atmosphere: torches, particles, runes, stone pillars."""

    _RUNE_CHARS = list("ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗ")

    def __init__(self, screen: pygame.Surface, seed: int = 42) -> None:
        self.screen = screen
        self.tick   = 0
        rng         = random.Random(seed)

        self._grad    = self._build_grad()
        self._trim    = self._build_trim()

        self._runes = [
            {
                "x":  rng.randint(80, SCREEN_WIDTH - 80),
                "y":  rng.randint(50, SCREEN_HEIGHT - 80),
                "ch": rng.choice(self._RUNE_CHARS),
                "ph": rng.uniform(0, math.pi * 2),
                "sz": rng.randint(20, 38),
            }
            for _ in range(20)
        ]
        self._rfont: dict[int, pygame.font.Font] = {}

        # Torch positions – one pair per side
        self._torches = [
            (76, 195), (76, 455),
            (SCREEN_WIDTH - 76, 195), (SCREEN_WIDTH - 76, 455),
        ]

        self._parts:  list[dict] = []
        self._prng    = random.Random(seed + 1)
        self._ptimer  = 0

    # ── pre-renders ──────────────────────────────────────────────────

    def _build_grad(self) -> pygame.Surface:
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        stops = [_BG1, _BG2, _BG3, (22, 14, 34)]
        seg   = SCREEN_HEIGHT // (len(stops) - 1)
        for i in range(len(stops) - 1):
            c0, c1 = stops[i], stops[i + 1]
            y0 = i * seg
            for dy in range(seg):
                t = dy / seg
                col = (int(c0[0]+t*(c1[0]-c0[0])), int(c0[1]+t*(c1[1]-c0[1])), int(c0[2]+t*(c1[2]-c0[2])))
                pygame.draw.line(s, col, (0, y0 + dy), (SCREEN_WIDTH, y0 + dy))
        return s

    def _build_trim(self) -> pygame.Surface:
        """Horizontal stone tile strip."""
        s = pygame.Surface((SCREEN_WIDTH, 14), pygame.SRCALPHA)
        for x in range(0, SCREEN_WIDTH, 26):
            pygame.draw.rect(s, _ST2,  (x + 1, 1, 24, 12))
            pygame.draw.rect(s, _ST3,  (x,     0, 26, 14), 1)
        return s

    def _rfont_at(self, sz: int) -> pygame.font.Font:
        if sz not in self._rfont:
            try:
                self._rfont[sz] = pygame.font.SysFont("segoeuisymbol,unifont,freesans", sz)
            except Exception:
                self._rfont[sz] = pygame.font.SysFont("monospace", sz)
        return self._rfont[sz]

    # ── main draw ────────────────────────────────────────────────────

    def draw(self) -> None:
        self.tick += 1
        self.screen.blit(self._grad, (0, 0))
        self._draw_pillars()
        self._draw_inner_shadow()
        self._draw_runes()
        for tx, ty in self._torches:
            self._draw_torch(tx, ty)
        self.screen.blit(self._trim, (0, 0))
        self.screen.blit(self._trim, (0, SCREEN_HEIGHT - 14))
        self._ptimer += 1
        if self._ptimer % 2 == 0:
            self._emit()
        self._tick_parts()
        self._draw_vignette()

    # ── sub-draws ────────────────────────────────────────────────────

    def _draw_pillars(self) -> None:
        pw = 70
        for x0 in (0, SCREEN_WIDTH - pw):
            pygame.draw.rect(self.screen, _ST3,  (x0, 0, pw, SCREEN_HEIGHT))
            ix = x0 + 6 if x0 == 0 else x0 + 2
            pygame.draw.rect(self.screen, _ST,   (ix, 0, pw - 8, SCREEN_HEIGHT))
            ex = x0 + pw - 1 if x0 == 0 else x0
            pygame.draw.line(self.screen, _ST2,  (ex, 0), (ex, SCREEN_HEIGHT), 2)
            for y in range(0, SCREEN_HEIGHT, 40):
                lx0 = x0 + 10;  lx1 = x0 + pw - 10
                pygame.draw.line(self.screen, _ST3, (lx0, y), (lx1, y), 1)

    def _draw_inner_shadow(self) -> None:
        """Soft shadow cast inward from the stone pillars."""
        pw = 70
        for x0, direction in ((pw, 1), (SCREEN_WIDTH - pw - 30, -1)):
            sh = pygame.Surface((30, SCREEN_HEIGHT), pygame.SRCALPHA)
            for i in range(30):
                a = int(55 * (1 - i / 30))
                pygame.draw.line(sh, (0, 0, 0, a), (i, 0), (i, SCREEN_HEIGHT))
            self.screen.blit(sh, (x0 if direction == 1 else x0, 0))

    def _draw_runes(self) -> None:
        for r in self._runes:
            phase = r["ph"] + self.tick * 0.014
            bright = int(22 + 16 * math.sin(phase))
            col = (bright + 55, bright + 28, bright + 95)
            font = self._rfont_at(r["sz"])
            surf = font.render(r["ch"], True, col)
            self.screen.blit(surf, (r["x"], r["y"]))

    def _draw_torch(self, tx: int, ty: int) -> None:
        t = self.tick
        pygame.draw.rect(self.screen, (72, 52, 24), (tx - 5, ty + 4, 10, 24))
        pygame.draw.rect(self.screen, (48, 36, 16), (tx - 7, ty + 22, 14, 5))

        flicker = math.sin(t * 0.21) * 2.8 + math.sin(t * 0.33 + 0.8) * 1.6
        fh = int(20 + flicker)
        fw = int(11 + abs(flicker) * 0.4)

        # Halo
        glow = pygame.Surface((100, 100), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (200, 120, 20, 28), (0, 0, 100, 100))
        self.screen.blit(glow, (tx - 50, ty - 42), special_flags=pygame.BLEND_ADD)

        # Flame layers
        for layer, (fr, fg, fb, fscale) in enumerate([
            (180, 90, 10, 1.0),
            (220, 140, 20, 0.72),
            (255, 200, 80, 0.42),
        ]):
            lfw = max(2, int(fw * fscale))
            lfh = max(2, int(fh * fscale))
            ox  = int(math.sin(t * 0.25 + layer) * 1.5)
            pygame.draw.ellipse(self.screen, (fr, fg, fb),
                                (tx - lfw + ox, ty - lfh, lfw * 2, lfh + 5))

    def _emit(self) -> None:
        rng = self._prng
        for tx, ty in self._torches:
            if rng.random() < 0.55:
                self._parts.append({
                    "x": float(tx + rng.randint(-4, 4)),
                    "y": float(ty - 4),
                    "vx": rng.uniform(-0.4, 0.4),
                    "vy": rng.uniform(-1.5, -0.5),
                    "life": rng.randint(22, 65),
                    "ml":  50,
                    "col": (rng.randint(180, 220), rng.randint(80, 145), 12),
                    "sz":  rng.uniform(1.4, 3.2),
                })
        if rng.random() < 0.12:
            self._parts.append({
                "x": float(rng.randint(110, SCREEN_WIDTH - 110)),
                "y": float(rng.randint(SCREEN_HEIGHT - 220, SCREEN_HEIGHT - 20)),
                "vx": rng.uniform(-0.12, 0.12),
                "vy": rng.uniform(-0.28, -0.06),
                "life": rng.randint(80, 200),
                "ml":  140,
                "col": (145, 125, 180),
                "sz":  rng.uniform(0.8, 1.8),
            })

    def _tick_parts(self) -> None:
        alive = []
        t = self.tick
        for p in self._parts:
            p["x"]    += p["vx"] + math.sin(t * 0.04 + p["y"] * 0.02) * 0.12
            p["y"]    += p["vy"]
            p["life"] -= 1
            if p["life"] <= 0 or p["y"] < -12:
                continue
            frac  = min(1.0, max(0.0, p["life"] / p["ml"]))
            alpha = int(frac * 210)
            sz    = max(1, int(p["sz"] * frac + 0.5))
            ps    = pygame.Surface((sz * 4 + 1, sz * 4 + 1), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*p["col"], alpha), (sz * 2, sz * 2), sz)
            self.screen.blit(ps, (int(p["x"]) - sz * 2, int(p["y"]) - sz * 2),
                             special_flags=pygame.BLEND_ADD)
            alive.append(p)
        self._parts = alive

    def _draw_vignette(self) -> None:
        v  = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        cx = SCREEN_WIDTH  // 2
        cy = SCREEN_HEIGHT // 2
        for i in range(6):
            rw = cx - i * 55
            rh = cy - i * 38
            a  = int(i * 14)
            if rw > 0 and rh > 0:
                pygame.draw.ellipse(v, (0, 0, 0, a), (cx - rw, cy - rh, rw * 2, rh * 2))
        self.screen.blit(v, (0, 0))


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _glow_text(
    screen: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    text_col: tuple,
    glow_col: tuple,
    cx: int,
    y: int,
    glow_passes: int = 5,
) -> int:
    """Render text with a soft glow halo. Returns bottom y of the text."""
    base = font.render(text, True, text_col)
    rect = base.get_rect(centerx=cx, top=y)
    # Glow layers (outer → inner, increasing alpha)
    for i in range(glow_passes, 0, -1):
        pad   = i * 4
        alpha = int(55 / i)
        gs    = pygame.Surface((rect.w + pad * 2, rect.h + pad * 2), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*glow_col, alpha),
                         (0, 0, gs.get_width(), gs.get_height()), border_radius=6)
        screen.blit(gs, (rect.x - pad, rect.y - pad))
    screen.blit(base, rect)
    return rect.bottom


def _draw_ornament_line(
    screen: pygame.Surface,
    cx: int,
    y: int,
    width: int = 480,
    color: tuple = (80, 65, 110),
) -> None:
    """Decorative divider: line + centre diamond."""
    half = width // 2
    pygame.draw.line(screen, color, (cx - half, y), (cx + half, y), 1)
    # Diamond
    d = 6
    pts = [(cx, y - d), (cx + d, y), (cx, y + d), (cx - d, y)]
    pygame.draw.polygon(screen, color, pts)
    # Accent dashes
    for ox in (-half // 3, half // 3):
        pygame.draw.line(screen, color, (cx + ox - 10, y), (cx + ox + 10, y), 1)


def _stat_bar(
    screen: pygame.Surface,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: float,         # 0.0–1.0
    fg: tuple,
    bg: tuple = (28, 22, 40),
    label: str = "",
    label_font: Optional[pygame.font.Font] = None,
    label_col: tuple = (160, 150, 180),
) -> int:
    """Draw a stat bar; returns bottom y."""
    if label and label_font:
        lsurf = label_font.render(label, True, label_col)
        screen.blit(lsurf, (x, y - lsurf.get_height() - 2))
        y += 2
    pygame.draw.rect(screen, bg,  (x, y, w, h), border_radius=3)
    filled_w = max(2, int(w * fill))
    pygame.draw.rect(screen, fg,  (x, y, filled_w, h), border_radius=3)
    # Shine
    shine_h = max(1, h // 3)
    shine   = pygame.Surface((filled_w, shine_h), pygame.SRCALPHA)
    shine.fill((255, 255, 255, 35))
    screen.blit(shine, (x, y))
    return y + h


def _draw_portrait(
    screen: pygame.Surface,
    cls: str,
    cx: int,
    cy: int,
    size: int = 192,
    glow_col: Optional[tuple] = None,
    tick: int = 0,
) -> None:
    """Draw a large class portrait by scaling the 64×64 sprite."""
    from ui.sprite_loader import _draw_humanoid_frame
    # Animated bob based on tick
    frame = (tick // 15) % 4
    sprite_surf = _draw_humanoid_frame(cls, frame)
    scaled = pygame.transform.smoothscale(sprite_surf, (size, size))

    blit_x = cx - size // 2
    blit_y = cy - size // 2

    if glow_col:
        # Portrait glow halo
        for r in range(4, 0, -1):
            gs = pygame.Surface((size + r * 16, size + r * 16), pygame.SRCALPHA)
            pygame.draw.ellipse(gs, (*glow_col, int(25 / r)), (0, 0, *gs.get_size()))
            screen.blit(gs, (blit_x - r * 8, blit_y - r * 8))

    screen.blit(scaled, (blit_x, blit_y))


# ---------------------------------------------------------------------------
# Shared base (kept for Death/Victory compatibility)
# ---------------------------------------------------------------------------

class _MenuBase:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen      = screen
        self.font_title  = pygame.font.SysFont("monospace", 52, bold=True)
        self.font_large  = pygame.font.SysFont("monospace", 34, bold=True)
        self.font_medium = pygame.font.SysFont("monospace", 24)
        self.font_small  = pygame.font.SysFont("monospace", 18)
        self.font_tiny   = pygame.font.SysFont("monospace", 14)

    def _blit_centered(self, text: str, font: pygame.font.Font,
                       color: tuple, y: int) -> None:
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(centerx=SCREEN_WIDTH // 2, top=y))

    def _blit_wrapped_centered(self, text: str, font: pygame.font.Font,
                                color: tuple, cx: int, y: int, max_width: int) -> int:
        words, lines, cur = text.split(), [], []
        for word in words:
            test = " ".join(cur + [word])
            if font.size(test)[0] <= max_width:
                cur.append(word)
            else:
                if cur:
                    lines.append(" ".join(cur))
                cur = [word]
        if cur:
            lines.append(" ".join(cur))
        lh = font.get_linesize()
        for line in lines:
            s = font.render(line, True, color)
            self.screen.blit(s, s.get_rect(centerx=cx, top=y))
            y += lh
        return y

    def _draw_divider(self, y: int, color: tuple = (60, 50, 80)) -> None:
        pygame.draw.line(self.screen, color,
                         (SCREEN_WIDTH // 4, y), (SCREEN_WIDTH * 3 // 4, y), 1)


# ---------------------------------------------------------------------------
# Main Menu  — full lobby design
# ---------------------------------------------------------------------------

class MainMenu(_MenuBase):
    _OPTIONS      = ["New Game", "Continue", "Leaderboard", "Quit"]
    _OPTION_KEYS  = ["new_game", "continue", "leaderboard", "quit"]
    _LORE = (
        "Ancient crypts.  Forgotten souls.  Seven Shards of Ethos lost to the dark.",
        "One warrior descends.  None return unchanged.",
    )

    def __init__(self, screen: pygame.Surface) -> None:
        super().__init__(screen)
        self.selected       = 0
        self._no_save_flash = 0
        self._tick          = 0
        self._bg            = _BgRenderer(screen, seed=1)

        # Fonts
        self._f_hero  = pygame.font.SysFont("monospace", 56, bold=True)
        self._f_sub   = pygame.font.SysFont("monospace", 36, bold=True)
        self._f_btn   = pygame.font.SysFont("monospace", 28, bold=True)
        self._f_lore  = pygame.font.SysFont("monospace", 14)
        self._f_foot  = pygame.font.SysFont("monospace", 13)

    # ── public interface ──────────────────────────────────────────────

    def update(self, events: list[pygame.event.Event]) -> Optional[str]:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self._OPTIONS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self._OPTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._OPTION_KEYS[self.selected]
        return None

    def render(self) -> None:
        self._tick += 1
        self._bg.draw()
        self._draw_title()
        self._draw_buttons()
        self._draw_lore()
        self._draw_footer()

    # ── title ─────────────────────────────────────────────────────────

    def _draw_title(self) -> None:
        cx = SCREEN_WIDTH // 2
        t  = self._tick

        # Pulsing top subtitle
        pulse = int(180 + 40 * math.sin(t * 0.03))
        top_col = (pulse, int(pulse * 0.85), int(pulse * 0.6))
        s1 = self._f_sub.render("CRYPTS  OF  THE", True, top_col)
        self.screen.blit(s1, s1.get_rect(centerx=cx, top=68))

        # Main hero title with gold glow
        glow_a = int(160 + 55 * math.sin(t * 0.025))
        glow_col = (glow_a, int(glow_a * 0.72), 0)
        _glow_text(self.screen, "FORGOTTEN  DESCENT",
                   self._f_hero, _GLDT, glow_col, cx, 120, glow_passes=6)

        # Ornamental divider
        _draw_ornament_line(self.screen, cx, 200, 560, (_GLDD[0]+20, _GLDD[1]+10, 60))

        # Gem/shard icon row
        gem_y = 210
        for i, off in enumerate((-160, -80, 0, 80, 160, 240, 320)):
            ox = cx - 160 + i * 45
            pulse_i = int(80 + 60 * math.sin(t * 0.04 + i * 0.7))
            col = (0, pulse_i + 60, pulse_i + 80)
            pygame.draw.polygon(self.screen, col,
                                [(ox, gem_y - 6), (ox + 5, gem_y),
                                 (ox, gem_y + 6), (ox - 5, gem_y)])

    # ── buttons ───────────────────────────────────────────────────────

    def _draw_buttons(self) -> None:
        bw, bh = 360, 54
        bx     = SCREEN_WIDTH // 2 - bw // 2
        by0    = 250
        gap    = 70
        t      = self._tick

        for i, label in enumerate(self._OPTIONS):
            by       = by0 + i * gap
            selected = (i == self.selected)
            self._draw_one_button(bx, by, bw, bh, label, selected, t)

    def _draw_one_button(
        self, bx: int, by: int, bw: int, bh: int,
        label: str, selected: bool, t: int,
    ) -> None:
        cx = bx + bw // 2

        if selected:
            pulse = int(180 + 55 * math.sin(t * 0.055))
            gold  = (_GLD[0], _GLD[1], _GLD[2])
            # Outer glow
            for gi in range(5, 0, -1):
                gs = pygame.Surface((bw + gi * 16, bh + gi * 12), pygame.SRCALPHA)
                a  = int(22 / gi)
                pygame.draw.rect(gs, (*gold, a), (0, 0, *gs.get_size()), border_radius=7 + gi)
                self.screen.blit(gs, (bx - gi * 8, by - gi * 6))

            # Button body
            bg_col = (int(_GLD[0] * 0.12), int(_GLD[1] * 0.08), 10)
            pygame.draw.rect(self.screen, bg_col, (bx, by, bw, bh), border_radius=6)
            # Border top highlight
            pygame.draw.rect(self.screen, gold, (bx, by, bw, bh), 2, border_radius=6)
            pygame.draw.line(self.screen, _GLDT, (bx + 8, by + 1), (bx + bw - 8, by + 1))

            # Corner rune-marks
            for ox, oy in ((bx + 4, by + 4), (bx + bw - 12, by + 4)):
                pygame.draw.rect(self.screen, _GLD, (ox, oy, 8, 2))
                pygame.draw.rect(self.screen, _GLD, (ox, oy, 2, 6))

            # Chevron arrows
            for side, sign in ((-1, -1), (1, 1)):
                ax = cx + sign * (bw // 2 + 18)
                pts = [
                    (ax,           by + bh // 2),
                    (ax + sign * 10, by + bh // 2 - 9),
                    (ax + sign * 10, by + bh // 2 + 9),
                ]
                pygame.draw.polygon(self.screen, gold, pts)

            # Label
            lsurf = self._f_btn.render(label, True, _GLDT)
            self.screen.blit(lsurf, lsurf.get_rect(centerx=cx, centery=by + bh // 2))

        else:
            # Unselected: dim stone button
            pygame.draw.rect(self.screen, (18, 14, 28), (bx, by, bw, bh), border_radius=6)
            pygame.draw.rect(self.screen, (48, 42, 64), (bx, by, bw, bh), 1, border_radius=6)
            lsurf = self._f_btn.render(label, True, (130, 120, 155))
            self.screen.blit(lsurf, lsurf.get_rect(centerx=cx, centery=by + bh // 2))

    # ── lore & footer ─────────────────────────────────────────────────

    def _draw_lore(self) -> None:
        cx = SCREEN_WIDTH // 2
        t  = self._tick
        y  = 548
        for i, line in enumerate(self._LORE):
            alpha = int(70 + 25 * math.sin(t * 0.02 + i * 1.2))
            col   = (alpha, int(alpha * 0.85), int(alpha * 0.6))
            lsurf = self._f_lore.render(line, True, col)
            self.screen.blit(lsurf, lsurf.get_rect(centerx=cx, top=y))
            y += 20

        _draw_ornament_line(self.screen, cx, y + 8, 320, (50, 42, 72))

        if self._no_save_flash > 0:
            self._no_save_flash -= 1
            warn = self._f_lore.render("No save file found — start a New Game first.",
                                       True, (220, 100, 50))
            self.screen.blit(warn, warn.get_rect(centerx=cx, top=y + 18))

    def _draw_footer(self) -> None:
        hint = self._f_foot.render(
            "W / S  or  ↑ / ↓  to navigate     ENTER  to select",
            True, (62, 56, 80),
        )
        self.screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2,
                                              bottom=SCREEN_HEIGHT - 4))


# ---------------------------------------------------------------------------
# Character Select  — full portrait lobby
# ---------------------------------------------------------------------------

class CharacterSelectMenu(_MenuBase):

    _CLASSES = [
        {
            "key":     "warrior",
            "name":    "WARRIOR",
            "lore":    "A hardened knight who fights through pain. Iron Will keeps him standing when others would fall.",
            "stats":   {"HP": (40, 50, (180, 80, 80)),
                        "ATK": (6, 12, (200, 160, 60)),
                        "DEF": (4, 8,  (80, 140, 220))},
            "passive": "Iron Will",
            "passive_desc": "HP < 25% grants +4 DEF",
            "gear":    "Iron Sword  ·  Leather Armor  ·  Health Potion ×1",
        },
        {
            "key":     "rogue",
            "name":    "ROGUE",
            "lore":    "Speed and precision over brute force. The first strike on any foe is a lethal Backstab.",
            "stats":   {"HP": (25, 50, (180, 80, 80)),
                        "ATK": (9, 12, (200, 160, 60)),
                        "DEF": (2, 8,  (80, 140, 220))},
            "passive": "Backstab",
            "passive_desc": "First hit on each new enemy deals 3× damage",
            "gear":    "Rusty Sword  ·  Bomb ×2  ·  Health Potion ×2",
        },
        {
            "key":     "mage",
            "name":    "MAGE",
            "lore":    "Fragile but devastating. Arcane Surge amplifies scroll power to levels no warrior could match.",
            "stats":   {"HP": (20, 50, (180, 80, 80)),
                        "ATK": (5, 12, (200, 160, 60)),
                        "DEF": (1, 8,  (80, 140, 220))},
            "passive": "Arcane Surge",
            "passive_desc": "Scrolls deal 1.5× damage",
            "gear":    "Scroll of Fire ×2  ·  Mega Potion ×1",
        },
    ]

    _CARD_W = 298
    _CARD_H = 548

    def __init__(self, screen: pygame.Surface) -> None:
        super().__init__(screen)
        self.selected = 0
        self._tick    = 0
        self._bg      = _BgRenderer(screen, seed=2)

        self._f_title  = pygame.font.SysFont("monospace", 40, bold=True)
        self._f_cls    = pygame.font.SysFont("monospace", 24, bold=True)
        self._f_lore   = pygame.font.SysFont("monospace", 13)
        self._f_stat   = pygame.font.SysFont("monospace", 13, bold=True)
        self._f_label  = pygame.font.SysFont("monospace", 12)
        self._f_passive= pygame.font.SysFont("monospace", 13)
        self._f_foot   = pygame.font.SysFont("monospace", 13)

    # ── public interface ──────────────────────────────────────────────

    def update(self, events: list[pygame.event.Event]) -> Optional[str]:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.selected = (self.selected - 1) % len(self._CLASSES)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.selected = (self.selected + 1) % len(self._CLASSES)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._CLASSES[self.selected]["key"]
            elif event.key == pygame.K_ESCAPE:
                return "back"
        return None

    def render(self) -> None:
        self._tick += 1
        self._bg.draw()
        self._draw_header()
        self._draw_cards()
        self._draw_nav_arrows()
        self._draw_footer()

    # ── header ───────────────────────────────────────────────────────

    def _draw_header(self) -> None:
        cx = SCREEN_WIDTH // 2
        t  = self._tick
        pulse = int(180 + 45 * math.sin(t * 0.03))
        _glow_text(self.screen, "CHOOSE  YOUR  CLASS",
                   self._f_title, (pulse, int(pulse*0.75), int(pulse*0.45)),
                   _PUR, cx, 22, glow_passes=4)
        _draw_ornament_line(self.screen, cx, 80, 600, (70, 55, 100))

    # ── cards ─────────────────────────────────────────────────────────

    def _draw_cards(self) -> None:
        n       = len(self._CLASSES)
        gap     = 28
        total_w = n * self._CARD_W + (n - 1) * gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        y_top   = 96

        for i, cls in enumerate(self._CLASSES):
            x = start_x + i * (self._CARD_W + gap)
            self._draw_card(x, y_top, cls, selected=(i == self.selected))

    def _draw_card(
        self, x: int, y: int, cls: dict, selected: bool,
    ) -> None:
        cw, ch = self._CARD_W, self._CARD_H
        cx     = x + cw // 2
        t      = self._tick
        col    = _CLS_COLS[cls["key"]]

        # ── card background ──
        bg_col     = (22, 17, 34) if selected else (12, 9, 20)
        border_col = col          if selected else (40, 34, 58)
        border_w   = 2            if selected else 1

        pygame.draw.rect(self.screen, bg_col, (x, y, cw, ch), border_radius=8)
        pygame.draw.rect(self.screen, border_col, (x, y, cw, ch), border_w, border_radius=8)

        # Outer glow on selected card
        if selected:
            for gi in range(4, 0, -1):
                gs = pygame.Surface((cw + gi * 12, ch + gi * 10), pygame.SRCALPHA)
                a  = int(18 / gi)
                pygame.draw.rect(gs, (*col, a), (0, 0, *gs.get_size()), border_radius=10 + gi)
                self.screen.blit(gs, (x - gi * 6, y - gi * 5))

        # Top corner accents
        d = 14
        for ox, oy, dx, dy in ((0, 0, d, 0), (0, 0, 0, d),
                                (cw-d, 0, d, 0), (cw-d, 0, 0, d),
                                (0, ch-d, d, 0), (0, ch-d, 0, d),
                                (cw-d, ch-d, d, 0), (cw-d, ch-d, 0, d)):
            pygame.draw.line(self.screen, col if selected else (40, 34, 58),
                             (x+ox, y+oy), (x+ox+dx, y+oy+dy), 2)

        iy = y + 14

        # ── portrait ──
        portrait_size = 192 if selected else 168
        portrait_y    = iy + portrait_size // 2
        _draw_portrait(self.screen, cls["key"], cx, portrait_y,
                       portrait_size, glow_col=col if selected else None, tick=t)
        iy += portrait_size + 12

        # ── class name ──
        name_col = _GLDT if selected else (140, 130, 160)
        ns = self._f_cls.render(cls["name"], True, name_col)
        self.screen.blit(ns, ns.get_rect(centerx=cx, top=iy))
        iy += ns.get_height() + 6

        # ── divider ──
        pygame.draw.line(self.screen, col if selected else (38, 32, 52),
                         (x + 14, iy), (x + cw - 14, iy), 1)
        iy += 8

        # ── lore line ──
        iy = self._blit_wrapped_centered(
            cls["lore"], self._f_lore, (130, 122, 155) if not selected else (165, 158, 195),
            cx, iy, cw - 24,
        )
        iy += 8

        # ── stat bars ──
        bar_w = cw - 40
        bx    = x + 20
        for stat_name, (val, mx, bar_col) in cls["stats"].items():
            fill = val / mx
            # Label + value
            lbl_s = self._f_label.render(f"{stat_name}  {val}", True, (160, 150, 185))
            self.screen.blit(lbl_s, (bx, iy))
            iy += lbl_s.get_height() + 1
            _stat_bar(self.screen, bx, iy, bar_w, 8, fill, bar_col if selected else tuple(c//2 for c in bar_col))
            iy += 12

        iy += 4
        pygame.draw.line(self.screen, col if selected else (38, 32, 52),
                         (x + 14, iy), (x + cw - 14, iy), 1)
        iy += 8

        # ── passive ──
        ps = self._f_label.render("PASSIVE ABILITY", True, _GLD if selected else _GLDD)
        self.screen.blit(ps, ps.get_rect(centerx=cx, top=iy))
        iy += ps.get_height() + 3
        pn = self._f_passive.render(cls["passive"], True, col if selected else (80, 78, 100))
        self.screen.blit(pn, pn.get_rect(centerx=cx, top=iy))
        iy += pn.get_height() + 2
        iy = self._blit_wrapped_centered(
            cls["passive_desc"], self._f_label,
            (165, 152, 120) if selected else (90, 84, 110),
            cx, iy, cw - 24,
        )
        iy += 6

        # ── gear ──
        gs_lbl = self._f_label.render("STARTING GEAR", True, (80, 155, 210) if selected else (45, 80, 115))
        self.screen.blit(gs_lbl, gs_lbl.get_rect(centerx=cx, top=iy))
        iy += gs_lbl.get_height() + 3
        self._blit_wrapped_centered(
            cls["gear"], self._f_label,
            (130, 155, 195) if selected else (65, 76, 105),
            cx, iy, cw - 24,
        )

        # ── enter prompt (selected only) ──
        if selected:
            pulse = int(180 + 55 * math.sin(t * 0.06))
            pc    = (pulse, int(pulse * 0.78), int(pulse * 0.28))
            ep    = self._f_label.render("[ ENTER  —  Begin Your Descent ]", True, pc)
            self.screen.blit(ep, ep.get_rect(centerx=cx, bottom=y + ch - 8))

    # ── nav arrows ───────────────────────────────────────────────────

    def _draw_nav_arrows(self) -> None:
        t     = self._tick
        pulse = int(140 + 60 * math.sin(t * 0.05))
        col   = (pulse, int(pulse*0.7), int(pulse*0.3))

        # Left arrow
        lx = 78
        my = SCREEN_HEIGHT // 2
        pts_l = [(lx, my), (lx + 22, my - 14), (lx + 22, my + 14)]
        pygame.draw.polygon(self.screen, col, pts_l)
        pygame.draw.polygon(self.screen, _GLDD, pts_l, 1)

        # Right arrow
        rx = SCREEN_WIDTH - 78
        pts_r = [(rx, my), (rx - 22, my - 14), (rx - 22, my + 14)]
        pygame.draw.polygon(self.screen, col, pts_r)
        pygame.draw.polygon(self.screen, _GLDD, pts_r, 1)

    # ── footer ───────────────────────────────────────────────────────

    def _draw_footer(self) -> None:
        hint = self._f_foot.render(
            "A / D  or  ← / →  to browse     ENTER  to select     ESC  back",
            True, (60, 54, 78),
        )
        self.screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2,
                                              bottom=SCREEN_HEIGHT - 4))


# ---------------------------------------------------------------------------
# Death Screen
# ---------------------------------------------------------------------------

class DeathScreen(_MenuBase):
    def __init__(self, screen: pygame.Surface) -> None:
        super().__init__(screen)
        self._bg = _BgRenderer(screen, seed=3)
        self._tick = 0

    def render(self, stats: dict) -> None:
        self._tick += 1
        self._bg.draw()

        cx = SCREEN_WIDTH // 2
        t  = self._tick

        # Title glow
        pulse = int(160 + 60 * math.sin(t * 0.04))
        _glow_text(self.screen, "YOU  HAVE  FALLEN",
                   self.font_title, (220, 50, 50), (140, 20, 20), cx, 50, glow_passes=5)

        _draw_ornament_line(self.screen, cx, 130, 420, (120, 30, 30))

        s2 = self.font_small.render("The Crypts have claimed another soul.", True, (140, 80, 80))
        self.screen.blit(s2, s2.get_rect(centerx=cx, top=142))

        # Stats panel
        pw, ph = 440, 310
        px     = cx - pw // 2
        py     = 180
        pygame.draw.rect(self.screen, (16, 8, 8), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, (90, 28, 28), (px, py, pw, ph), 2, border_radius=8)
        # Corner marks
        for ox, oy, dx, dy in ((0,0,14,0),(0,0,0,14),(pw-14,0,14,0),(pw-14,0,0,14),
                                (0,ph-14,14,0),(0,ph-14,0,14),(pw-14,ph-14,14,0),(pw-14,ph-14,0,14)):
            pygame.draw.line(self.screen, (120, 35, 35), (px+ox, py+oy), (px+ox+dx, py+oy+dy), 2)

        row_keys = [k for k in stats if k != "Score"]
        cy = py + 22
        for key in row_keys:
            label = self.font_medium.render(f"{key}:", True, (170, 90, 90))
            value = self.font_medium.render(str(stats[key]), True, (200, 185, 215))
            self.screen.blit(label, (px + 32, cy))
            self.screen.blit(value, (px + pw - value.get_width() - 32, cy))
            cy += 36

        if "Score" in stats:
            pygame.draw.line(self.screen, (90, 28, 28), (px + 24, cy), (px + pw - 24, cy), 1)
            cy += 12
            _glow_text(self.screen, f"FINAL SCORE:  {stats['Score']:,}",
                       self.font_large, GOLD, (100, 70, 0), cx, cy, glow_passes=3)

        hint = self.font_small.render("Press ENTER to return to menu", True, (110, 70, 70))
        self.screen.blit(hint, hint.get_rect(centerx=cx, top=py + ph + 18))


# ---------------------------------------------------------------------------
# Victory Screen
# ---------------------------------------------------------------------------

class VictoryScreen(_MenuBase):
    def __init__(self, screen: pygame.Surface) -> None:
        super().__init__(screen)
        self._bg = _BgRenderer(screen, seed=4)
        self._tick = 0

    def render(self, stats: dict) -> None:
        self._tick += 1
        self._bg.draw()

        cx = SCREEN_WIDTH // 2
        t  = self._tick

        pulse = int(200 + 55 * math.sin(t * 0.04))
        gold_col = (pulse, int(pulse * 0.82), int(pulse * 0.16))
        _glow_text(self.screen, "V I C T O R Y",
                   self.font_title, gold_col, (120, 80, 0), cx, 50, glow_passes=6)

        _draw_ornament_line(self.screen, cx, 130, 420, (140, 110, 20))

        s2 = self.font_small.render(
            "The Hollow Warden is defeated.  You escape the Crypts!", True, (200, 175, 100))
        self.screen.blit(s2, s2.get_rect(centerx=cx, top=142))

        pw, ph = 440, 310
        px = cx - pw // 2
        py = 180
        pygame.draw.rect(self.screen, (12, 10, 4), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, (130, 95, 18), (px, py, pw, ph), 2, border_radius=8)
        for ox, oy, dx, dy in ((0,0,14,0),(0,0,0,14),(pw-14,0,14,0),(pw-14,0,0,14),
                                (0,ph-14,14,0),(0,ph-14,0,14),(pw-14,ph-14,14,0),(pw-14,ph-14,0,14)):
            pygame.draw.line(self.screen, (160, 120, 24), (px+ox, py+oy), (px+ox+dx, py+oy+dy), 2)

        row_keys = [k for k in stats if k != "Score"]
        cy = py + 22
        for key in row_keys:
            label = self.font_medium.render(f"{key}:", True, (185, 155, 75))
            value = self.font_medium.render(str(stats[key]), True, (210, 198, 225))
            self.screen.blit(label, (px + 32, cy))
            self.screen.blit(value, (px + pw - value.get_width() - 32, cy))
            cy += 36

        if "Score" in stats:
            pygame.draw.line(self.screen, (130, 95, 18), (px + 24, cy), (px + pw - 24, cy), 1)
            cy += 12
            _glow_text(self.screen, f"FINAL SCORE:  {stats['Score']:,}",
                       self.font_large, GOLD, (120, 80, 0), cx, cy, glow_passes=4)

        hint = self.font_small.render("Press ENTER to return to menu", True, (140, 115, 55))
        self.screen.blit(hint, hint.get_rect(centerx=cx, top=py + ph + 18))
