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


# ── Enemy character sprites ────────────────────────────────────────────

def _draw_enemy_frame(paint_fn, frame: int) -> pygame.Surface:
    W, H = 64, 64
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    bob = (0, -1, 0, 1)[frame % 4]
    paint_fn(surf, W, H, bob)
    return surf


def _make_humanoid_enemy_spriteset(name: str) -> SpriteSet:
    _PAINTERS = {
        "skeleton":      _paint_skeleton,
        "ghoul":         _paint_ghoul,
        "wraith":        _paint_wraith,
        "stone_golem":   _paint_stone_golem,
        "lich":          _paint_lich,
        "hollow_warden": _paint_hollow_warden,
    }
    paint_fn = _PAINTERS.get(name)
    if paint_fn is None:
        specs = {
            "skeleton":      ((200, 200, 200), "S"),
            "ghoul":         ((80,  180,  80), "G"),
            "wraith":        ((160,  80, 220), "W"),
            "stone_golem":   ((140, 120, 100), "O"),
            "lich":          ((200,  60, 200), "L"),
            "hollow_warden": ((220,  60,  60), "B"),
        }
        color, sym = specs.get(name, ((160, 160, 160), "?"))
        return _make_placeholder_spriteset(color, sym)
    idle_frames = [_draw_enemy_frame(paint_fn, i) for i in range(4)]
    return SpriteSet(idle=AnimStrip(idle_frames, fps=3))


def _paint_skeleton(surf: pygame.Surface, W: int, H: int, b: int) -> None:
    BON = (210, 200, 185)
    DRK = (155, 145, 130)
    SKT = (12,  10,   8)
    BLD = (185, 192, 208)
    HLT = (115,  90,  60)

    # Sword (right side)
    pygame.draw.rect(surf, BLD,  (52,  8+b, 4, 30))
    pygame.draw.line(surf, (220, 228, 245), (53,  9+b), (53, 36+b), 1)
    pygame.draw.rect(surf, HLT,  (46, 37+b, 16,  4))
    pygame.draw.rect(surf, HLT,  (52, 41+b,  4, 10))
    pygame.draw.circle(surf, DRK, (54, 52+b), 3)

    # Legs
    for lx, fx in ((18, 14), (36, 32)):
        pygame.draw.rect(surf, BON, (lx+1, 43+b, 6, 18))
        pygame.draw.circle(surf, DRK, (lx+4, 43+b), 5)
        pygame.draw.circle(surf, DRK, (lx+4, 53+b), 4)
        pygame.draw.ellipse(surf, BON, (fx, 60+b, 14, 5))

    # Pelvis
    pygame.draw.ellipse(surf, BON, (16, 38+b, 32,  9))
    pygame.draw.ellipse(surf, DRK, (16, 38+b, 32,  9), 1)

    # Spine
    pygame.draw.rect(surf, BON, (30, 22+b, 4, 18))
    for i in range(4):
        pygame.draw.circle(surf, DRK, (32, 25 + i * 5 + b), 3)

    # Ribs (4 pairs — angled lines from spine)
    for i in range(4):
        y = 25 + i * 4 + b
        pygame.draw.line(surf, BON, (30, y), (13, y + 3), 2)
        pygame.draw.line(surf, BON, (34, y), (51, y + 3), 2)

    # Arms
    pygame.draw.rect(surf, BON, ( 9, 22+b, 7, 18))
    pygame.draw.circle(surf, DRK, (12, 22+b), 5)
    pygame.draw.circle(surf, DRK, (12, 38+b), 4)
    pygame.draw.circle(surf, BON, (12, 45+b), 4)

    pygame.draw.rect(surf, BON, (45, 20+b, 7, 20))
    pygame.draw.circle(surf, DRK, (48, 20+b), 5)
    pygame.draw.circle(surf, DRK, (48, 38+b), 4)
    pygame.draw.circle(surf, BON, (49, 45+b), 4)

    # Collarbone
    pygame.draw.line(surf, BON, (14, 23+b), (30, 21+b), 2)
    pygame.draw.line(surf, BON, (34, 21+b), (50, 23+b), 2)

    # Neck
    pygame.draw.rect(surf, BON, (29, 16+b, 6,  8))

    # Skull
    pygame.draw.ellipse(surf, BON, (20,  2+b, 24, 20))
    pygame.draw.ellipse(surf, DRK, (20,  2+b, 24, 20), 1)
    pygame.draw.rect(surf,   BON, (23, 16+b, 18,  7))
    pygame.draw.rect(surf,   DRK, (23, 16+b, 18,  7), 1)
    pygame.draw.ellipse(surf, SKT, (22,  7+b,  7,  6))
    pygame.draw.ellipse(surf, SKT, (35,  7+b,  7,  6))
    pygame.draw.polygon(surf, SKT, [(31, 13+b), (33, 13+b), (32, 16+b)])
    for i in range(5):
        pygame.draw.rect(surf, BON, (23 + i * 4, 18+b, 3, 4))
    pygame.draw.line(surf, DRK, (22, 18+b), (41, 18+b), 1)


def _paint_ghoul(surf: pygame.Surface, W: int, H: int, b: int) -> None:
    SKN = (82, 148, 72)
    SKD = (55, 105, 48)
    RAG = (38,  30, 22)
    RGL = (58,  48, 32)
    EY  = (18,  12,  5)
    CLW = (155, 130, 85)
    BLD = (140,  18, 18)

    # Legs
    pygame.draw.rect(surf, SKN, (18, 44+b, 10, 18))
    pygame.draw.rect(surf, SKN, (36, 44+b, 10, 18))
    pygame.draw.rect(surf, SKD, (18, 56+b, 10,  6))
    pygame.draw.rect(surf, SKD, (36, 56+b, 10,  6))
    pygame.draw.ellipse(surf, SKD, (13, 60+b, 16,  6))
    pygame.draw.ellipse(surf, SKD, (35, 60+b, 16,  6))
    # Clawed toes
    for cx in (14, 18, 22):
        pygame.draw.line(surf, CLW, (cx, 64+b), (cx - 1, 68+b), 2)
    for cx in (36, 40, 44):
        pygame.draw.line(surf, CLW, (cx, 64+b), (cx - 1, 68+b), 2)

    # Loincloth rags
    pygame.draw.polygon(surf, RAG, [(15, 42+b), (22, 55+b), (32, 50+b), (42, 55+b), (49, 42+b)])
    pygame.draw.polygon(surf, RGL, [(17, 43+b), (23, 50+b), (32, 46+b), (41, 50+b), (47, 43+b)], 1)

    # Torso
    pygame.draw.ellipse(surf, SKN, (16, 22+b, 32, 24))
    pygame.draw.ellipse(surf, SKD, (16, 22+b, 32, 24), 1)
    pygame.draw.rect(surf, RAG, (18, 24+b, 28, 16))
    pygame.draw.ellipse(surf, SKN, (20, 24+b, 24, 12))
    pygame.draw.ellipse(surf, BLD, (26, 28+b,  8,  6))

    # Arms (long, clawed)
    pygame.draw.rect(surf, SKN, ( 5, 22+b, 12, 22))
    pygame.draw.rect(surf, SKD, ( 5, 22+b, 12, 22), 1)
    pygame.draw.rect(surf, SKN, (47, 22+b, 12, 22))
    pygame.draw.rect(surf, SKD, (47, 22+b, 12, 22), 1)
    for i in range(3):
        pygame.draw.line(surf, CLW, ( 7 + i * 3, 44+b), ( 5 + i * 3, 50+b), 2)
        pygame.draw.line(surf, CLW, (49 + i * 3, 44+b), (47 + i * 3, 50+b), 2)

    # Neck
    pygame.draw.rect(surf, SKN, (27, 16+b, 10,  8))

    # Head (forward-leaning)
    pygame.draw.ellipse(surf, SKN, (22,  4+b, 22, 18))
    pygame.draw.ellipse(surf, SKD, (22, 10+b, 22, 10))
    pygame.draw.ellipse(surf, EY,  (24,  7+b,  6,  5))
    pygame.draw.ellipse(surf, EY,  (34,  7+b,  6,  5))
    pygame.draw.circle(surf, (175, 165, 15), (27,  9+b), 2)
    pygame.draw.circle(surf, (175, 165, 15), (37,  9+b), 2)
    pygame.draw.circle(surf, SKD, (32, 14+b), 2)
    pygame.draw.ellipse(surf, (12,  8,  4), (25, 16+b, 14,  6))
    for i in range(3):
        pygame.draw.line(surf, (198, 182, 160), (27 + i * 4, 16+b), (27 + i * 4, 20+b), 1)
    pygame.draw.line(surf, (95, 155, 75), (30, 22+b), (29, 26+b), 1)
    pygame.draw.ellipse(surf, SKD, (22,  4+b, 22, 18), 1)


def _paint_wraith(surf: pygame.Surface, W: int, H: int, b: int) -> None:
    ROB = (22,  8, 48)
    RLT = (52, 26, 96)
    EY  = (175, 75, 255)
    EYG = (220, 155, 255)

    # Fading ethereal bottom
    for i in range(9):
        alpha = max(0, 130 - i * 20)
        w_f   = max(6, 28 - i * 4)
        fade  = pygame.Surface((w_f, 4), pygame.SRCALPHA)
        fade.fill((32, 12, 68, alpha))
        surf.blit(fade, ((W - w_f) // 2, 48 + i * 2 + b))

    # Body mass
    body = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.ellipse(body, (*ROB, 205), (12, 22+b, 40, 30))
    surf.blit(body, (0, 0))
    pygame.draw.line(surf, RLT, (22, 24+b), (18, 50+b), 2)
    pygame.draw.line(surf, RLT, (32, 22+b), (30, 52+b), 2)
    pygame.draw.line(surf, RLT, (42, 24+b), (46, 50+b), 2)

    # Ghostly arm tendrils
    pygame.draw.lines(surf, RLT, False, [(16, 30+b), ( 7, 36+b), ( 3, 44+b), ( 9, 50+b)], 3)
    pygame.draw.lines(surf, RLT, False, [(48, 30+b), (57, 36+b), (61, 44+b), (55, 50+b)], 3)
    for i, (fx, fy) in enumerate([(5, 50+b), (9, 52+b), (13, 51+b)]):
        ws = pygame.Surface((8, 10), pygame.SRCALPHA)
        ws.fill((52, 22, 108, 155 - i * 35))
        surf.blit(ws, (fx - 4, fy))
    for i, (fx, fy) in enumerate([(51, 50+b), (55, 52+b), (59, 51+b)]):
        ws = pygame.Surface((8, 10), pygame.SRCALPHA)
        ws.fill((52, 22, 108, 155 - i * 35))
        surf.blit(ws, (fx - 4, fy))

    # Aura behind hood
    aura = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.circle(aura, (95, 35, 175, 50), (W // 2, 12+b), 18)
    surf.blit(aura, (0, 0))

    # Hood shape
    hood = [(18, 22+b), (12, 10+b), (20, 2+b), (32, 0+b), (44, 2+b), (52, 10+b), (46, 22+b)]
    pygame.draw.polygon(surf, ROB, hood)
    pygame.draw.polygon(surf, RLT, hood, 1)
    pygame.draw.ellipse(surf, (8, 3, 18), (20,  8+b, 24, 16))

    # Glowing eyes
    for ex in (26, 38):
        eg = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.circle(eg, (*EY, 65), (ex, 13+b), 6)
        surf.blit(eg, (0, 0))
        pygame.draw.circle(surf, EY,  (ex, 13+b), 3)
        pygame.draw.circle(surf, EYG, (ex, 13+b), 1)


def _paint_stone_golem(surf: pygame.Surface, W: int, H: int, b: int) -> None:
    STN = (102,  97, 115)
    STL = (132, 127, 145)
    STD = ( 68,  64,  82)
    CRK = (250, 130,  25)
    CRL = (255, 200,  80)
    EY  = (255, 148,  28)

    # Legs
    for lx in (11, 39):
        pygame.draw.rect(surf, STN, (lx, 44+b, 14, 18))
        pygame.draw.rect(surf, STL, (lx+1, 45+b,  6,  6))
        pygame.draw.rect(surf, STD, (lx, 44+b, 14, 18), 1)
        pygame.draw.line(surf, CRK, (lx + 7, 46+b), (lx + 7, 60+b), 2)
    pygame.draw.rect(surf, STD, ( 7, 60+b, 22, 5))
    pygame.draw.rect(surf, STN, ( 9, 60+b, 18, 4))
    pygame.draw.rect(surf, STD, (35, 60+b, 22, 5))
    pygame.draw.rect(surf, STN, (37, 60+b, 18, 4))

    # Torso
    pygame.draw.rect(surf, STN, (10, 24+b, 44, 22))
    pygame.draw.rect(surf, STL, (12, 25+b, 16,  6))
    pygame.draw.rect(surf, STD, (10, 24+b, 44, 22), 2)
    pygame.draw.line(surf, CRK, (32, 28+b), (32, 44+b), 3)
    pygame.draw.line(surf, CRK, (32, 32+b), (20, 44+b), 2)
    pygame.draw.line(surf, CRK, (32, 32+b), (44, 44+b), 2)
    pygame.draw.line(surf, CRL, (32, 29+b), (32, 42+b), 1)
    pygame.draw.circle(surf, (188, 100, 18), (32, 33+b), 5, 1)

    # Arms
    for ax, sign in ((0, 1), (52, -1)):
        pygame.draw.rect(surf, STN, (ax, 22+b, 12, 22))
        pygame.draw.rect(surf, STL, (ax+1, 23+b, 5, 5))
        pygame.draw.rect(surf, STD, (ax, 22+b, 12, 22), 1)
        pygame.draw.line(surf, CRK, (ax + 6, 28+b), (ax + 6 - sign * 2, 38+b), 2)
        pygame.draw.rect(surf, STD, (ax - 1, 42+b, 14, 12))
        pygame.draw.rect(surf, STN, (ax, 43+b, 12, 10))

    # Head
    pygame.draw.rect(surf, STN, (14,  2+b, 36, 24))
    pygame.draw.rect(surf, STL, (16,  3+b, 14,  7))
    pygame.draw.rect(surf, STD, (14,  2+b, 36, 24), 2)
    for ex in (20, 38):
        pygame.draw.rect(surf, STD, (ex - 2, 10+b, 10, 8))
        eg = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.circle(eg, (*EY, 80), (ex + 3, 14+b), 7)
        surf.blit(eg, (0, 0))
        pygame.draw.ellipse(surf, CRK, (ex,     11+b,  8, 6))
        pygame.draw.ellipse(surf, CRL, (ex + 1, 12+b,  6, 4))
    pygame.draw.line(surf, STD, (22, 20+b), (42, 20+b), 2)
    pygame.draw.line(surf, CRK, (26, 21+b), (38, 21+b), 1)
    pygame.draw.line(surf, STD, (24,  2+b), (20, 12+b), 1)
    pygame.draw.line(surf, STD, (44,  3+b), (48, 10+b), 1)


def _paint_lich(surf: pygame.Surface, W: int, H: int, b: int) -> None:
    SKN = (208, 200, 188)
    SKD = (155, 147, 132)
    SKT = ( 10,   8,   5)
    ROB = ( 26,  12,  56)
    RLT = ( 52,  26, 108)
    TRM = (178, 138, 218)
    TRL = (212, 172, 252)
    WOD = ( 75,  50,  18)
    ORB = (158,  78, 252)
    OLT = (208, 158, 252)
    GLD = (192, 158,  48)
    EY  = (198,  95, 252)

    # Staff
    pygame.draw.rect(surf, WOD, (8, 8+b, 5, 48))
    pygame.draw.rect(surf, (105, 74, 32), (9, 8+b, 2, 48))
    pygame.draw.ellipse(surf, SKN, (3, 2+b, 15, 12))
    pygame.draw.ellipse(surf, SKD, (3, 2+b, 15, 12), 1)
    pygame.draw.ellipse(surf, SKT, (5, 4+b, 4, 4))
    pygame.draw.ellipse(surf, SKT, (11, 4+b, 4, 4))
    og = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.circle(og, (*ORB, 62), (10, 3+b), 10)
    surf.blit(og, (0, 0))
    pygame.draw.circle(surf, ORB, (10, 5+b), 4)
    pygame.draw.circle(surf, OLT, (10, 4+b), 2)

    # Robe hem
    pygame.draw.polygon(surf, ROB, [(17, 40+b), (12, 63+b), (52, 63+b), (47, 40+b)])
    pygame.draw.polygon(surf, TRM, [(17, 40+b), (12, 63+b), (52, 63+b), (47, 40+b)], 1)
    pygame.draw.line(surf, TRM, (13, 60+b), (51, 60+b), 2)
    cx, cy = 32, 54 + b
    pygame.draw.circle(surf, TRM, (cx, cy), 5, 1)
    pygame.draw.line(surf, TRM, (cx, cy - 5), (cx, cy + 5), 1)
    pygame.draw.line(surf, TRM, (cx - 5, cy), (cx + 5, cy), 1)

    # Torso
    pygame.draw.rect(surf, ROB, (17, 22+b, 30, 20))
    pygame.draw.rect(surf, RLT, (19, 23+b, 12,  6))
    pygame.draw.rect(surf, TRM, (17, 22+b, 30, 20), 1)
    cx2, cy2 = 32, 30 + b
    pygame.draw.circle(surf, TRM, (cx2, cy2), 6, 1)
    pygame.draw.line(surf, TRM, (cx2 - 6, cy2), (cx2 + 6, cy2), 1)
    pygame.draw.line(surf, TRM, (cx2, cy2 - 6), (cx2, cy2 + 6), 1)
    pygame.draw.rect(surf, TRM, (17, 38+b, 30, 4))
    pygame.draw.rect(surf, TRL, (18, 38+b, 10, 2))

    # Arms
    pygame.draw.rect(surf, ROB, ( 8, 22+b, 11, 22))
    pygame.draw.rect(surf, RLT, ( 9, 23+b,  4,  5))
    pygame.draw.rect(surf, TRM, ( 8, 22+b, 11, 22), 1)
    pygame.draw.ellipse(surf, SKN, ( 6, 43+b, 12,  8))
    for i in range(3):
        pygame.draw.line(surf, SKD, (8 + i * 3, 49+b), (7 + i * 3, 54+b), 2)

    pygame.draw.rect(surf, ROB, (45, 22+b, 11, 20))
    pygame.draw.rect(surf, RLT, (46, 23+b,  4,  5))
    pygame.draw.rect(surf, TRM, (45, 22+b, 11, 20), 1)
    pygame.draw.ellipse(surf, SKN, (46, 41+b, 12,  8))
    cg = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.circle(cg, (*ORB, 72), (54, 45+b), 8)
    surf.blit(cg, (0, 0))
    pygame.draw.circle(surf, ORB, (54, 45+b), 4)
    pygame.draw.circle(surf, OLT, (54, 44+b), 2)

    # Neck
    pygame.draw.rect(surf, SKN, (28, 16+b, 8, 8))
    pygame.draw.rect(surf, SKD, (28, 16+b, 8, 8), 1)

    # Skull
    pygame.draw.ellipse(surf, SKN, (20,  2+b, 24, 20))
    pygame.draw.ellipse(surf, SKD, (20,  2+b, 24, 20), 1)
    pygame.draw.ellipse(surf, SKD, (22, 13+b, 20, 10))
    pygame.draw.ellipse(surf, SKT, (22,  7+b,  7,  6))
    pygame.draw.ellipse(surf, SKT, (35,  7+b,  7,  6))
    eg = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.circle(eg, (*EY, 82), (25, 10+b), 5)
    pygame.draw.circle(eg, (*EY, 82), (38, 10+b), 5)
    surf.blit(eg, (0, 0))
    pygame.draw.circle(surf, EY,  (25, 10+b), 2)
    pygame.draw.circle(surf, OLT, (25, 10+b), 1)
    pygame.draw.circle(surf, EY,  (38, 10+b), 2)
    pygame.draw.circle(surf, OLT, (38, 10+b), 1)
    pygame.draw.polygon(surf, SKT, [(31, 13+b), (33, 13+b), (32, 16+b)])
    for i in range(4):
        pygame.draw.rect(surf, SKN, (24 + i * 4, 18+b, 3, 4))
    pygame.draw.line(surf, SKD, (23, 18+b), (39, 18+b), 1)

    # Crown
    pygame.draw.rect(surf, GLD, (18,  2+b, 28,  5))
    pygame.draw.rect(surf, (208, 178, 68), (19,  2+b, 10,  3))
    for cx3 in (22, 29, 36, 43):
        pygame.draw.polygon(surf, GLD, [(cx3 - 2, 2+b), (cx3, -2+b), (cx3 + 2, 2+b)])
    pygame.draw.circle(surf, EY,  (32, 1+b), 3)
    pygame.draw.circle(surf, OLT, (32, 0+b), 1)


def _paint_hollow_warden(surf: pygame.Surface, W: int, H: int, b: int) -> None:
    ARM = (46,  40,  60)
    ARL = (76,  68,  96)
    ARD = (26,  22,  36)
    CRK = (218,  38,  38)
    CRL = (255, 138,  75)
    EY  = (255,  48,  48)
    EYG = (255, 198, 115)
    BON = (198, 190, 175)
    BND = (152, 145, 132)
    BLD = (168, 175, 198)
    BLH = (218, 222, 242)

    # Greatsword (large, left side)
    for i in range(3):
        pygame.draw.line(surf, BLD, (4 + i, 8+b), (30 + i, 58+b), 3 - (i % 2))
    pygame.draw.line(surf, BLH, (5, 9+b), (30, 56+b), 1)
    pygame.draw.rect(surf, (128, 112, 78), (0, 33+b, 22,  5))
    pygame.draw.rect(surf, (162, 145, 92), (1, 34+b,  8,  2))
    pygame.draw.rect(surf, (88,  62,  28), (6, 38+b,  8, 14))
    pygame.draw.circle(surf, (128, 98, 38), (10, 53+b), 4)

    # Legs
    for lx in (22, 40):
        pygame.draw.rect(surf, ARM, (lx, 44+b, 14, 18))
        pygame.draw.rect(surf, ARL, (lx+1, 45+b, 6, 6))
        pygame.draw.rect(surf, ARD, (lx, 44+b, 14, 18), 1)
        pygame.draw.line(surf, CRK, (lx + 7, 46+b), (lx + 7, 60+b), 2)
    pygame.draw.rect(surf, ARD, (18, 60+b, 20, 6))
    pygame.draw.rect(surf, ARM, (20, 61+b, 16, 4))
    pygame.draw.rect(surf, ARD, (36, 60+b, 20, 6))
    pygame.draw.rect(surf, ARM, (38, 61+b, 16, 4))

    # Torso
    pygame.draw.rect(surf, ARM, (16, 22+b, 32, 24))
    pygame.draw.rect(surf, ARL, (18, 23+b, 14,  8))
    pygame.draw.rect(surf, ARD, (16, 22+b, 32, 24), 2)
    pygame.draw.line(surf, CRK, (32, 26+b), (32, 44+b), 3)
    pygame.draw.line(surf, CRK, (32, 30+b), (20, 44+b), 2)
    pygame.draw.line(surf, CRK, (32, 30+b), (44, 44+b), 2)
    pygame.draw.line(surf, CRL, (32, 27+b), (32, 43+b), 1)

    # Pauldrons
    pygame.draw.ellipse(surf, ARM, ( 5, 18+b, 18, 14))
    pygame.draw.ellipse(surf, ARL, ( 7, 19+b,  8,  6))
    pygame.draw.ellipse(surf, ARD, ( 5, 18+b, 18, 14), 1)
    pygame.draw.line(surf, CRK, (11, 20+b), ( 7, 30+b), 2)
    pygame.draw.ellipse(surf, ARM, (41, 18+b, 18, 14))
    pygame.draw.ellipse(surf, ARL, (43, 19+b,  8,  6))
    pygame.draw.ellipse(surf, ARD, (41, 18+b, 18, 14), 1)
    pygame.draw.line(surf, CRK, (53, 20+b), (57, 30+b), 2)

    # Arms
    for ax in (7, 47):
        pygame.draw.rect(surf, ARM, (ax, 26+b, 10, 22))
        pygame.draw.rect(surf, ARL, (ax+1, 27+b, 4, 6))
        pygame.draw.rect(surf, ARD, (ax, 26+b, 10, 22), 1)
        pygame.draw.line(surf, CRK, (ax + 5, 28+b), (ax + 5, 44+b), 2)
        pygame.draw.rect(surf, ARD, (ax - 1, 46+b, 14,  8))
        pygame.draw.rect(surf, ARM, (ax,     47+b, 12,  6))

    # Neck gorget
    pygame.draw.rect(surf, ARM, (26, 16+b, 12, 8))
    pygame.draw.rect(surf, ARD, (26, 16+b, 12, 8), 1)

    # Helm (cracked, skull showing through)
    pygame.draw.ellipse(surf, ARM, (16,  0+b, 32, 20))
    pygame.draw.ellipse(surf, ARL, (18,  1+b, 14,  7))
    pygame.draw.ellipse(surf, ARD, (16,  0+b, 32, 20), 2)
    pygame.draw.line(surf, CRK, (28,  0+b), (24, 14+b), 3)
    pygame.draw.line(surf, CRL, (28,  1+b), (25, 12+b), 1)
    pygame.draw.ellipse(surf, BON, (21,  6+b, 14, 12))

    # Eye glow slots
    for ex, ew in ((17, 9), (36, 9)):
        eg = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(eg, (*EY, 122), (ex, 8+b, ew, 7))
        surf.blit(eg, (0, 0))
        pygame.draw.ellipse(surf, CRK, (ex + 1,  8+b, ew - 2, 6))
        pygame.draw.ellipse(surf, EYG, (ex + 2,  9+b, ew - 4, 4))

    # Jaw
    pygame.draw.rect(surf, BON, (22, 14+b, 20,  8))
    pygame.draw.rect(surf, BND, (22, 14+b, 20,  8), 1)
    for i in range(4):
        pygame.draw.rect(surf, BON, (24 + i * 4, 18+b, 3, 4))
    pygame.draw.line(surf, BND, (23, 18+b), (41, 18+b), 1)

    # Boss red aura
    aura = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.circle(aura, (200, 18, 18, 24), (W // 2, H // 2 + b), 36)
    surf.blit(aura, (0, 0))


# ── Entity sheet loader ────────────────────────────────────────────────

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
    path = os.path.join(_SPRITES, f"{name}.png")
    if _load_png(path) is not None:
        specs = {
            "skeleton":      ((200, 200, 200), "S"),
            "ghoul":         ((80,  180,  80), "G"),
            "wraith":        ((160,  80, 220), "W"),
            "stone_golem":   ((140, 120, 100), "O"),
            "lich":          ((200,  60, 200), "L"),
            "hollow_warden": ((220,  60,  60), "B"),
        }
        color, sym = specs.get(name, ((160, 160, 160), "?"))
        return _load_entity_sheet(f"{name}.png", color, sym)
    return _make_humanoid_enemy_spriteset(name)


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
