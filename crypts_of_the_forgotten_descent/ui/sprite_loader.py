"""
Asset pipeline — loads PNG sprite sheets and falls back to procedural
placeholder sprites when asset files are not present.

Directory layout (relative to crypts_of_the_forgotten_descent/):
  assets/sprites/player_warrior.png   — 4×4 grid: idle/walk/attack/hurt × 4 dirs
  assets/sprites/player_rogue.png
  assets/sprites/player_mage.png
  assets/sprites/skeleton.png
  assets/sprites/ghoul.png
  assets/sprites/wraith.png
  assets/sprites/golem.png
  assets/sprites/lich.png
  assets/sprites/boss.png
  assets/tiles/tileset.png            — 16-tile row: floor0..3, wall0..1, door, stairs, shrine …
  assets/items/items.png              — item icon sheet, 16x16 per icon

If a file is missing the loader returns a placeholder surface drawn with
pygame.draw so the game always runs.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

import pygame

# ── paths ──────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(__file__)
_ASSETS  = os.path.join(_HERE, "..", "assets")
_SPRITES = os.path.join(_ASSETS, "sprites")
_TILES   = os.path.join(_ASSETS, "tiles")
_ITEMS   = os.path.join(_ASSETS, "items")

TILE_SIZE = 32   # pixels per tile cell in sprite sheets


# ── helpers ────────────────────────────────────────────────────────────

def _load_png(path: str) -> Optional[pygame.Surface]:
    if os.path.isfile(path):
        try:
            return pygame.image.load(path).convert_alpha()
        except Exception:
            return None
    return None


def _slice_sheet(sheet: pygame.Surface, col: int, row: int,
                 w: int = TILE_SIZE, h: int = TILE_SIZE) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.blit(sheet, (0, 0), (col * w, row * h, w, h))
    return surf


# ── procedural placeholders ────────────────────────────────────────────

def _placeholder(color: tuple, symbol: str = "",
                 w: int = TILE_SIZE, h: int = TILE_SIZE) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Body silhouette
    pygame.draw.ellipse(surf, color, (4, 10, w - 8, h - 12))
    # Head
    head_c = tuple(min(255, c + 40) for c in color)
    pygame.draw.circle(surf, head_c, (w // 2, 7), 6)
    if symbol:
        font = pygame.font.SysFont("monospace", 13, bold=True)
        lbl  = font.render(symbol, True, (255, 255, 255))
        surf.blit(lbl, lbl.get_rect(center=(w // 2, h // 2)))
    return surf


def _placeholder_tile(base_color: tuple, accent: tuple | None = None,
                      pattern: str = "floor") -> pygame.Surface:
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    surf.fill(base_color)
    if pattern == "wall":
        # Brick rows
        bc = tuple(max(0, c - 30) for c in base_color)
        for row in range(2):
            y0 = row * 16
            offset = 0 if row % 2 == 0 else 8
            for col in range(3):
                x0 = col * 16 - offset
                pygame.draw.rect(surf, bc, (x0 + 1, y0 + 1, 13, 13), 1)
    elif pattern == "floor":
        bc = tuple(max(0, c - 15) for c in base_color)
        # Random-looking cracks (deterministic)
        pygame.draw.line(surf, bc, (6, 10), (14, 18), 1)
        pygame.draw.line(surf, bc, (20, 4), (26, 12), 1)
    if accent:
        pygame.draw.rect(surf, accent, (1, 1, TILE_SIZE - 2, TILE_SIZE - 2), 1)
    return surf


# ── animation strip ────────────────────────────────────────────────────

class AnimStrip:
    """A single-row animation from a sprite sheet (or list of surfaces)."""

    def __init__(self, frames: list[pygame.Surface], fps: int = 8) -> None:
        self.frames  = frames
        self.frame_dur = max(1, 60 // fps)
        self._tick   = 0
        self._frame  = 0

    def update(self) -> None:
        self._tick += 1
        if self._tick >= self.frame_dur:
            self._tick   = 0
            self._frame  = (self._frame + 1) % len(self.frames)

    @property
    def current(self) -> pygame.Surface:
        return self.frames[self._frame]

    def reset(self) -> None:
        self._tick  = 0
        self._frame = 0


# ── SpriteSet  ────────────────────────────────────────────────────────

class SpriteSet:
    """Holds idle / walk / attack / hurt animations for one entity."""

    def __init__(self,
                 idle:   AnimStrip,
                 walk:   AnimStrip | None = None,
                 attack: AnimStrip | None = None,
                 hurt:   AnimStrip | None = None) -> None:
        self.idle   = idle
        self.walk   = walk   or idle
        self.attack = attack or idle
        self.hurt   = hurt   or idle
        self._mode  = "idle"
        self._mode_timer = 0

    def set_mode(self, mode: str, duration: int = 8) -> None:
        if mode != self._mode:
            self._mode       = mode
            self._mode_timer = duration
            for anim in (self.idle, self.walk, self.attack, self.hurt):
                anim.reset()

    def update(self) -> None:
        if self._mode_timer > 0:
            self._mode_timer -= 1
            if self._mode_timer == 0 and self._mode != "idle":
                self._mode = "idle"
        anim = getattr(self, self._mode)
        anim.update()

    @property
    def current(self) -> pygame.Surface:
        return getattr(self, self._mode).current


# ── loader API ────────────────────────────────────────────────────────

def _make_placeholder_spriteset(color: tuple, symbol: str = "") -> SpriteSet:
    frame = _placeholder(color, symbol)
    return SpriteSet(idle=AnimStrip([frame], fps=4))


# ── Humanoid player sprites (64×64, scaled to 32px at render time) ────

def _make_humanoid_player_spriteset(character_class: str) -> SpriteSet:
    idle_frames = [_draw_humanoid_frame(character_class, i) for i in range(4)]
    walk_frames = [_draw_humanoid_frame(character_class, i, walk=True) for i in range(4)]
    return SpriteSet(
        idle=AnimStrip(idle_frames, fps=4),
        walk=AnimStrip(walk_frames, fps=6),
    )


def _draw_humanoid_frame(cls: str, frame: int, walk: bool = False) -> pygame.Surface:
    W, H = 64, 64
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    bob = (0, -2, 0, 2)[frame % 4] if walk else (0, -1, 0, 1)[frame % 4]
    {"warrior": _paint_warrior, "rogue": _paint_rogue, "mage": _paint_mage}.get(
        cls, _paint_warrior)(surf, W, H, bob)
    return surf


def _paint_warrior(surf: pygame.Surface, W: int, H: int, b: int) -> None:
    S   = (205,168,128); SSH = (170,130, 95)
    ST  = (118,112,138); SLT = (162,157,182); SDK = (78, 74, 98)
    GLD = (178,148, 58)
    CPE = (138, 22, 22); CPD = ( 88, 14, 14)
    LTH = ( 68, 48, 28); LTL = ( 95, 68, 42)
    BLD = (212,216,232); BHL = (245,248,255)

    ag = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.ellipse(ag, (200,160,80,22), (10,22+b,44,36))
    surf.blit(ag, (0,0))

    # Cape behind body
    cp = [(22,20+b),(15,58+b),(21,63+b),(32,57+b),(43,63+b),(49,58+b),(42,20+b)]
    pygame.draw.polygon(surf, CPE, cp); pygame.draw.polygon(surf, CPD, cp, 1)

    # Sword: blade, crossguard, handle, pommel
    pygame.draw.rect(surf, BLD, (53, 6+b, 4,36))
    pygame.draw.line(surf, BHL, (54, 6+b),(54,40+b), 1)
    pygame.draw.line(surf, SDK, (56, 6+b),(56,40+b), 1)
    pygame.draw.rect(surf, GLD, (47,40+b,16, 5))
    pygame.draw.rect(surf,(210,185,90),(48,41+b,14, 2))
    pygame.draw.rect(surf, LTH, (53,45+b, 4,12))
    pygame.draw.circle(surf, GLD, (55,58+b), 4)
    pygame.draw.circle(surf,(210,185,90),(55,57+b), 2)

    # Shield
    sh = [(7,24+b),(7,46+b),(15,52+b),(15,22+b)]
    pygame.draw.polygon(surf,(145,108,48), sh)
    pygame.draw.polygon(surf,( 95, 70,28), sh, 1)
    pygame.draw.circle(surf, GLD,(11,37+b), 6)
    pygame.draw.circle(surf,(210,185,90),(10,36+b), 3)

    # Legs + boots
    for lx in (18, 35):
        pygame.draw.rect(surf, ST, (lx,43+b,11,17))
        pygame.draw.rect(surf, SLT,(lx+1,44+b,5,8))
    pygame.draw.rect(surf, LTH,(16,57+b,14,6)); pygame.draw.rect(surf, LTL,(17,57+b,5,2))
    pygame.draw.rect(surf, LTH,(34,57+b,14,6)); pygame.draw.rect(surf, LTL,(35,57+b,5,2))

    # Chest plate + belt
    pygame.draw.rect(surf, ST, (19,22+b,26,22))
    pygame.draw.rect(surf, SLT,(21,23+b,11, 6))
    pygame.draw.rect(surf, SDK,(19,22+b,26,22), 1)
    pygame.draw.rect(surf, LTH,(17,40+b,30, 5))
    pygame.draw.rect(surf, GLD,(17,40+b,30, 2))
    pygame.draw.rect(surf, GLD,(28,40+b, 8, 5))
    pygame.draw.rect(surf,(210,185,90),(29,41+b, 6, 3))

    # Arms + pauldrons
    pygame.draw.rect(surf, ST, (10,22+b,10,10)); pygame.draw.rect(surf, ST,(10,32+b, 9, 9))
    pygame.draw.rect(surf, SLT,(11,23+b, 4, 5))
    pygame.draw.rect(surf, ST, (44,22+b,10,10)); pygame.draw.rect(surf, ST,(45,32+b, 9,12))
    pygame.draw.rect(surf, SLT,(45,23+b, 4, 5))

    # Neck
    pygame.draw.rect(surf, S,(28,17+b,8,6))

    # Face
    pygame.draw.ellipse(surf, S,  (22, 4+b,20,18))
    pygame.draw.ellipse(surf, SSH,(22,13+b,20, 9))
    pygame.draw.ellipse(surf,(45,35,25),(26, 9+b,5,4))
    pygame.draw.ellipse(surf,(45,35,25),(33, 9+b,5,4))
    pygame.draw.circle(surf,(220,195,175),(27, 9+b), 1)
    pygame.draw.circle(surf,(220,195,175),(34, 9+b), 1)
    pygame.draw.line(surf, SSH,(28,16+b),(36,16+b), 1)

    # Helmet: crown, cheek guards, nose guard, red plume
    pygame.draw.rect(surf, ST, (20, 2+b,24,10))
    pygame.draw.rect(surf, ST, (17, 8+b, 8, 9))
    pygame.draw.rect(surf, ST, (39, 8+b, 8, 9))
    pygame.draw.rect(surf, SDK,(28, 7+b, 8,10))
    pygame.draw.rect(surf, SLT,(21, 3+b, 9, 3))
    pygame.draw.rect(surf, CPE,(29, 0+b, 6, 4))


def _paint_rogue(surf: pygame.Surface, W: int, H: int, b: int) -> None:
    S   = (175,140,108); SSH = (140,108, 78)
    HOD = ( 28, 35, 28); HDL = ( 42, 55, 40)
    LTH = ( 55, 38, 18); LTL = ( 80, 58, 32)
    BLD = (205,214,225); BHL = (240,248,255)
    CLT = ( 38, 48, 38); CLL = ( 55, 70, 52)
    RPE = ( 90, 72, 42); EGL = ( 80,210, 80)

    ag = pygame.Surface((W,H), pygame.SRCALPHA)
    pygame.draw.ellipse(ag,(20,80,20,18),(8,20+b,48,40))
    surf.blit(ag,(0,0))

    # Cloak behind body
    ck = [(20,20+b),(12,60+b),(20,64+b),(32,58+b),(44,64+b),(52,60+b),(44,20+b)]
    pygame.draw.polygon(surf, HOD, ck); pygame.draw.polygon(surf, HDL, ck, 1)

    # Legs + dark boots
    pygame.draw.rect(surf, LTH,(19,43+b,10,17)); pygame.draw.rect(surf, LTL,(20,44+b,4,7))
    pygame.draw.rect(surf, HOD,(17,57+b,14,6))
    pygame.draw.rect(surf, LTH,(35,43+b,10,17)); pygame.draw.rect(surf, LTL,(36,44+b,4,7))
    pygame.draw.rect(surf, HOD,(34,57+b,14,6))

    # Left dagger (pointing down/forward)
    pygame.draw.line(surf, BLD,(14,38+b),(22,52+b), 2)
    pygame.draw.line(surf, BHL,(15,38+b),(23,52+b), 1)
    pygame.draw.rect(surf, RPE,(12,36+b,6,3)); pygame.draw.rect(surf, BLD,(10,38+b,8,2))

    # Right dagger (raised)
    pygame.draw.line(surf, BLD,(50,28+b),(42,44+b), 2)
    pygame.draw.line(surf, BHL,(51,28+b),(43,44+b), 1)
    pygame.draw.rect(surf, RPE,(46,42+b,6,3)); pygame.draw.rect(surf, BLD,(44,42+b,8,2))

    # Torso leather + belt pouches
    pygame.draw.rect(surf, LTH,(19,22+b,26,22)); pygame.draw.rect(surf, LTL,(21,23+b,10,6))
    pygame.draw.rect(surf, HOD,(19,22+b,26,22), 1)
    pygame.draw.rect(surf, RPE,(17,40+b,30,4))
    pygame.draw.rect(surf, LTH,(22,38+b,6,8)); pygame.draw.rect(surf, LTL,(23,39+b,4,2))
    pygame.draw.rect(surf, LTH,(36,38+b,6,8)); pygame.draw.rect(surf, LTL,(37,39+b,4,2))

    # Arms in dark cloth
    pygame.draw.rect(surf, CLT,( 9,22+b,11,20)); pygame.draw.rect(surf, CLL,(10,23+b,4,5))
    pygame.draw.rect(surf, CLT,(44,22+b,11,20)); pygame.draw.rect(surf, CLL,(45,23+b,4,5))

    # Neck
    pygame.draw.rect(surf, S,(28,17+b,8,5))

    # Face (drawn before hood, then re-exposed inside it)
    pygame.draw.ellipse(surf, S,  (23, 6+b,18,15))
    pygame.draw.ellipse(surf, SSH,(23,13+b,18, 7))

    # Hood shadow + fabric
    pygame.draw.ellipse(surf,(15,20,15),(21, 3+b,22,16))
    pygame.draw.ellipse(surf, HOD,(18, 0+b,28,18))
    pygame.draw.ellipse(surf, HDL,(19, 1+b,26,16), 1)

    # Face visible inside hood opening
    pygame.draw.ellipse(surf, S,  (23, 6+b,18,13))
    pygame.draw.ellipse(surf, SSH,(23,13+b,18, 6))
    pygame.draw.ellipse(surf,(20,20,20),(26, 9+b,5,3))
    pygame.draw.ellipse(surf,(20,20,20),(33, 9+b,5,3))
    pygame.draw.ellipse(surf, EGL,(27, 9+b,3,2))
    pygame.draw.ellipse(surf, EGL,(34, 9+b,3,2))
    pygame.draw.line(surf, SSH,(28,15+b),(34,15+b), 1)
    pygame.draw.ellipse(surf, HOD,(18, 1+b,28,18), 2)


def _paint_mage(surf: pygame.Surface, W: int, H: int, b: int) -> None:
    S   = (188,158,138); SSH = (155,122,100)
    ROB = ( 42, 28, 72); RLT = ( 72, 50,112)
    TRM = (182,142,222); TRL = (210,180,255)
    WOD = ( 90, 60, 24); WLT = (118, 84, 40)
    ORB = (115, 75,215); OLT = (160,120,255)
    RUN = (140,100,240); EY  = ( 80,130,240)

    ag = pygame.Surface((W,H), pygame.SRCALPHA)
    pygame.draw.ellipse(ag,(100,60,200,20),(8,18+b,48,44))
    surf.blit(ag,(0,0))

    # Staff with glowing orb
    pygame.draw.rect(surf, WOD,(10, 4+b,5,54)); pygame.draw.rect(surf, WLT,(11, 4+b,2,54))
    pygame.draw.circle(surf, ORB,(12, 5+b), 7)
    pygame.draw.circle(surf, OLT,(11, 4+b), 4)
    pygame.draw.circle(surf,(220,200,255),(10, 3+b), 2)
    og = pygame.Surface((W,H), pygame.SRCALPHA)
    pygame.draw.circle(og,(120,80,220,40),(12, 5+b),12)
    surf.blit(og,(0,0))

    # Robe hem (tapered skirt)
    pygame.draw.polygon(surf, ROB,[(18,42+b),(14,63+b),(50,63+b),(46,42+b)])
    pygame.draw.polygon(surf, RLT,[(18,42+b),(14,63+b),(50,63+b),(46,42+b)], 1)
    pygame.draw.line(surf, TRM,(14,60+b),(50,60+b), 2)
    pygame.draw.rect(surf,(32,24,48),(18,60+b,12,4))
    pygame.draw.rect(surf,(32,24,48),(34,60+b,12,4))

    # Torso robe + arcane rune on chest
    pygame.draw.rect(surf, ROB,(18,22+b,28,22)); pygame.draw.rect(surf, RLT,(20,23+b,12,7))
    pygame.draw.rect(surf, TRM,(18,22+b,28,22), 1)
    cx, cy = 32, 30+b
    pygame.draw.circle(surf, RUN,(cx,cy),5,1)
    pygame.draw.line(surf, RUN,(cx-5,cy),(cx+5,cy),1)
    pygame.draw.line(surf, RUN,(cx,cy-5),(cx,cy+5),1)
    pygame.draw.rect(surf, TRM,(18,40+b,28,4)); pygame.draw.rect(surf, TRL,(20,40+b,8,2))

    # Arms — left holds staff, right in casting gesture
    pygame.draw.rect(surf, ROB,( 8,22+b,12,20)); pygame.draw.rect(surf, RLT,( 9,23+b,5,5))
    pygame.draw.rect(surf, TRM,( 8,22+b,12,20), 1)
    pygame.draw.rect(surf, ROB,(44,22+b,12,18)); pygame.draw.rect(surf, RLT,(45,23+b,5,5))
    pygame.draw.rect(surf, TRM,(44,22+b,12,18), 1)
    pygame.draw.circle(surf, OLT,(52,42+b),4)
    pygame.draw.circle(surf,(220,200,255),(52,42+b),2)

    # Neck
    pygame.draw.rect(surf, S,(28,17+b,8,6))

    # Face
    pygame.draw.ellipse(surf, S,  (22, 5+b,20,16))
    pygame.draw.ellipse(surf, SSH,(22,13+b,20, 7))
    pygame.draw.ellipse(surf,(30,30,50),(25,10+b,6,4))
    pygame.draw.ellipse(surf,(30,30,50),(33,10+b,6,4))
    pygame.draw.ellipse(surf, EY,(26,10+b,4,3))
    pygame.draw.ellipse(surf, EY,(34,10+b,4,3))
    pygame.draw.circle(surf,(200,220,255),(27,10+b),1)
    pygame.draw.circle(surf,(200,220,255),(35,10+b),1)
    pygame.draw.ellipse(surf, SSH,(26,16+b,12,5))

    # Pointed hat: brim, cone, band, rune star
    pygame.draw.ellipse(surf, ROB,(14,14+b,36,8))
    pygame.draw.ellipse(surf, TRM,(14,14+b,36,8), 1)
    hat = [(32,-1+b),(18,16+b),(46,16+b)]
    pygame.draw.polygon(surf, ROB, hat); pygame.draw.polygon(surf, RLT, hat, 1)
    pygame.draw.rect(surf, TRM,(20,12+b,24,3))
    pygame.draw.circle(surf, RUN,(32, 7+b),3,1)


def _load_entity_sheet(filename: str, color: tuple,
                       symbol: str = "") -> SpriteSet:
    path  = os.path.join(_SPRITES, filename)
    sheet = _load_png(path)
    if sheet is None:
        return _make_placeholder_spriteset(color, symbol)

    w, h  = sheet.get_size()
    fw    = w // 4   # 4 columns: idle, walk, attack, hurt
    fh    = h // 4   # 4 rows (directions or frames)

    def row_strip(row: int, fps: int = 6) -> AnimStrip:
        frames = [_slice_sheet(sheet, c, row, fw, fh) for c in range(4)]
        return AnimStrip(frames, fps=fps)

    return SpriteSet(
        idle=row_strip(0, fps=4),
        walk=row_strip(1, fps=8),
        attack=row_strip(2, fps=10),
        hurt=row_strip(3, fps=12),
    )


# Public entity sprite loaders
def load_player(character_class: str) -> SpriteSet:
    path = os.path.join(_SPRITES, f"player_{character_class}.png")
    if _load_png(path) is not None:
        colors = {"warrior": (180,160,220), "rogue": (140,200,140), "mage": (120,160,255)}
        return _load_entity_sheet(f"player_{character_class}.png",
                                  colors.get(character_class, (220,220,80)), "@")
    return _make_humanoid_player_spriteset(character_class)


def load_enemy(name: str) -> SpriteSet:
    specs = {
        "skeleton":     ((200, 200, 200), "S"),
        "ghoul":        ((80,  180,  80), "G"),
        "wraith":       ((160,  80, 220), "W"),
        "stone_golem":  ((140, 120, 100), "O"),
        "lich":         ((200,  60, 200), "L"),
        "hollow_warden":((220,  60,  60), "B"),
    }
    color, sym = specs.get(name, ((160, 160, 160), "?"))
    return _load_entity_sheet(f"{name}.png", color, sym)


# ── Tileset loader ─────────────────────────────────────────────────────

class TilesetLoader:
    """
    Loads tiles from assets/tiles/tileset.png.
    Expected layout (32×32 per cell, one row):
      col 0-3 : floor variants
      col 4-5 : wall variants
      col 6   : door
      col 7   : stairs
      col 8   : shrine
    Falls back to procedural surfaces when the file is missing.
    """

    FLOOR_COLS   = (0, 1, 2, 3)
    WALL_COLS    = (4, 5)
    DOOR_COL     = 6
    STAIRS_COL   = 7
    SHRINE_COL   = 8

    def __init__(self) -> None:
        path  = os.path.join(_TILES, "tileset.png")
        sheet = _load_png(path)
        self._from_sheet = sheet is not None
        if self._from_sheet:
            self._sheet = sheet
            self._cache: dict[str, pygame.Surface] = {}
        else:
            self._build_procedural()

    def _slice(self, col: int, row: int = 0) -> pygame.Surface:
        return _slice_sheet(self._sheet, col, row)

    def _build_procedural(self) -> None:
        import random as _rnd
        ts = TILE_SIZE
        self._floors: list[pygame.Surface] = []
        for i in range(4):
            s = pygame.Surface((ts, ts), pygame.SRCALPHA)
            base = (58 + i * 3, 55 + i * 2, 72 + i * 3)
            s.fill(base)
            r = _rnd.Random(i * 137)
            # Cracks
            for _ in range(3):
                x0 = r.randint(3, ts - 10)
                y0 = r.randint(3, ts - 10)
                x1 = x0 + r.randint(-6, 6)
                y1 = y0 + r.randint(-6, 6)
                pygame.draw.line(s, (40, 38, 52), (x0, y0), (x1, y1), 1)
            # Occasional moss/stain
            if i % 3 == 0:
                pygame.draw.circle(s, (38, 55, 42), (r.randint(5, 26), r.randint(5, 26)), r.randint(2, 5))
            self._floors.append(s)

        # Wall — stone brick
        self._walls: list[pygame.Surface] = []
        for shade in (0, 1):
            s = pygame.Surface((ts, ts), pygame.SRCALPHA)
            bc = (88 + shade * 12, 82 + shade * 10, 108 + shade * 12)
            s.fill(bc)
            dark = (bc[0] - 20, bc[1] - 18, bc[2] - 22)
            hi   = (min(255, bc[0] + 18), min(255, bc[1] + 16), min(255, bc[2] + 22))
            for row in range(2):
                y0  = row * 16
                off = 0 if row % 2 == 0 else 8
                for col in range(-1, 3):
                    x0 = col * 16 + off
                    pygame.draw.rect(s, dark, (x0 + 1, y0 + 1, 13, 13), 1)
                    pygame.draw.line(s, hi, (x0 + 1, y0 + 1), (x0 + 13, y0 + 1), 1)
            self._walls.append(s)

        # Door
        self._door = pygame.Surface((ts, ts), pygame.SRCALPHA)
        self._door.fill((90, 55, 20))
        pygame.draw.rect(self._door, (60, 35, 10), (4, 2, ts - 8, ts - 4))
        # Planks
        for y in range(3):
            pygame.draw.line(self._door, (50, 30, 8), (5, 4 + y * 9), (ts - 6, 4 + y * 9), 1)
        # Iron bands
        pygame.draw.rect(self._door, (80, 78, 82), (4, 10, ts - 8, 3))
        pygame.draw.rect(self._door, (80, 78, 82), (4, 20, ts - 8, 3))
        # Keyhole
        pygame.draw.circle(self._door, (40, 38, 42), (ts // 2, ts // 2 - 2), 3)
        pygame.draw.rect(self._door, (40, 38, 42), (ts // 2 - 2, ts // 2, 4, 5))

        # Stairs
        self._stairs = pygame.Surface((ts, ts), pygame.SRCALPHA)
        self._stairs.fill((45, 42, 55))
        for i in range(5):
            y = 4 + i * 5
            w = ts - 8 - i * 2
            pygame.draw.rect(self._stairs, (80, 160, 200), (4 + i, y, w, 4))
            pygame.draw.rect(self._stairs, (40, 80, 120), (4 + i, y + 3, w, 1))
        # Glow from below
        glow = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (60, 140, 255, 60), (6, 20, ts - 12, ts - 16))
        self._stairs.blit(glow, (0, 0))

        # Shrine
        self._shrine = pygame.Surface((ts, ts), pygame.SRCALPHA)
        self._shrine.fill((30, 20, 45))
        pygame.draw.rect(self._shrine, (100, 60, 160), (4, 18, ts - 8, ts - 20))
        pygame.draw.rect(self._shrine, (130, 80, 200), (2, 14, ts - 4, 6))
        # Rune
        pygame.draw.circle(self._shrine, (180, 80, 255), (ts // 2, 10), 5, 1)
        pygame.draw.line(self._shrine, (180, 80, 255), (ts // 2, 4), (ts // 2, 16), 1)
        pygame.draw.line(self._shrine, (180, 80, 255), (ts // 2 - 5, 10), (ts // 2 + 5, 10), 1)

    # Public interface

    def get_floor(self, variant: int) -> pygame.Surface:
        if self._from_sheet:
            col = self.FLOOR_COLS[variant % len(self.FLOOR_COLS)]
            key = f"floor_{col}"
            if key not in self._cache:
                self._cache[key] = self._slice(col)
            return self._cache[key]
        return self._floors[variant % len(self._floors)]

    def get_wall(self, variant: int) -> pygame.Surface:
        if self._from_sheet:
            col = self.WALL_COLS[variant % len(self.WALL_COLS)]
            key = f"wall_{col}"
            if key not in self._cache:
                self._cache[key] = self._slice(col)
            return self._cache[key]
        return self._walls[variant % len(self._walls)]

    def get_door(self) -> pygame.Surface:
        if self._from_sheet:
            if "door" not in self._cache:
                self._cache["door"] = self._slice(self.DOOR_COL)
            return self._cache["door"]
        return self._door

    def get_stairs(self) -> pygame.Surface:
        if self._from_sheet:
            if "stairs" not in self._cache:
                self._cache["stairs"] = self._slice(self.STAIRS_COL)
            return self._cache["stairs"]
        return self._stairs

    def get_shrine(self) -> pygame.Surface:
        if self._from_sheet:
            if "shrine" not in self._cache:
                self._cache["shrine"] = self._slice(self.SHRINE_COL)
            return self._cache["shrine"]
        return self._shrine
