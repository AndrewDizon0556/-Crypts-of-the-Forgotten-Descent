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
    colors = {"warrior": (180, 160, 220), "rogue": (140, 200, 140), "mage": (120, 160, 255)}
    symbols = {"warrior": "@", "rogue": "@", "mage": "@"}
    c = colors.get(character_class, (220, 220, 80))
    return _load_entity_sheet(f"player_{character_class}.png", c, symbols.get(character_class, "@"))


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
