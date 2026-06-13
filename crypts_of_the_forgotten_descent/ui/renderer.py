"""Dungeon renderer — integrates tileset, lighting, particles, effects."""
from __future__ import annotations
import random

import pygame

from config import (
    TILE_RENDER_SIZE, GAME_AREA_W, GAME_AREA_H,
    VIEWPORT_TILES_W, VIEWPORT_TILES_H,
    BLACK, GOLD, SHRINE_COLOR,
)
from systems.dungeon import DungeonMap, TileType
from ui.camera     import Camera
from ui.lighting   import LightingSystem
from ui.particles  import ParticleSystem
from ui.effects    import FloatingNumberSystem
from ui.sprite_loader import TilesetLoader, load_player, load_enemy, SpriteSet


_STATUS_GLOW: dict[str, tuple] = {
    "bleed":  (200,  30,  30),
    "poison": ( 40, 200,  40),
    "cursed": (150,  40, 200),
    "slow":   (220, 190,  40),
}

# Tile variant seeds per (x,y) → keep floor variety deterministic
def _floor_variant(x: int, y: int) -> int:
    return (x * 2654435761 ^ y * 2246822519) & 3

def _wall_variant(x: int, y: int) -> int:
    return (x * 374761393 ^ y * 1073741789) & 1


class Renderer:
    def __init__(self, screen: pygame.Surface, character_class: str = "warrior") -> None:
        self.screen      = screen
        self.game_surf   = pygame.Surface((GAME_AREA_W, GAME_AREA_H))

        # Sub-systems
        self.camera    = Camera()
        self.lighting  = LightingSystem()
        self.particles = ParticleSystem()
        self.numbers   = FloatingNumberSystem()
        self.tileset   = TilesetLoader()

        # Torch animation tick
        self._tick = 0

        # Entity sprite sets — keyed by entity id
        self._entity_sprites: dict[int, SpriteSet] = {}
        self._player_sprites: SpriteSet | None = None
        self._char_class = character_class

        # Font for item symbols (fallback glyphs)
        self._glyph_font = pygame.font.SysFont("monospace", TILE_RENDER_SIZE, bold=True)
        self._small_font = pygame.font.SysFont("monospace", 11)

    # ------------------------------------------------------------------
    # Public helpers called by game.py
    # ------------------------------------------------------------------

    def set_character_class(self, cls: str) -> None:
        self._char_class = cls
        self._player_sprites = load_player(cls)

    def get_entity_sprite(self, enemy) -> SpriteSet:
        eid = id(enemy)
        if eid not in self._entity_sprites:
            name = type(enemy).__name__.lower()
            # Normalise boss name
            if "hollowwarden" in name or "warden" in name:
                name = "hollow_warden"
            elif "golem" in name:
                name = "stone_golem"
            self._entity_sprites[eid] = load_enemy(name)
        return self._entity_sprites[eid]

    # ------------------------------------------------------------------
    # Main render entry point
    # ------------------------------------------------------------------

    def render_frame(
        self,
        dungeon:        DungeonMap,
        player,
        entities:       list,
        items:          list,
        visible_tiles:  set[tuple[int, int]],
        explored_tiles: set[tuple[int, int]],
    ) -> None:
        self._tick += 1
        self.camera.update(player, dungeon)

        # Lazy-init player sprite
        if self._player_sprites is None:
            self._player_sprites = load_player(self._char_class)

        self.game_surf.fill(BLACK)
        cam = self.camera

        self._draw_tiles(dungeon, visible_tiles, explored_tiles)
        self._draw_items(items, visible_tiles)
        self._draw_entities(entities, visible_tiles)
        self._draw_player(player)

        # Lighting overlay
        self.lighting.begin_frame()
        sx, sy = cam.tile_to_screen(player.x, player.y)
        px_center = sx + TILE_RENDER_SIZE // 2
        py_center = sy + TILE_RENDER_SIZE // 2
        self.lighting.add_light(px_center, py_center)

        # Torch flicker on visible wall-adjacent tiles (every other tile to keep perf)
        for (tx, ty) in visible_tiles:
            if (tx + ty) % 4 == (self._tick // 30) % 4:
                t = dungeon.get_tile(tx, ty)
                if t == TileType.WALL:
                    wxs, wys = cam.tile_to_screen(tx, ty)
                    self.lighting.add_torch_light(
                        wxs + TILE_RENDER_SIZE // 2,
                        wys + TILE_RENDER_SIZE // 2,
                    )

        self.lighting.blit_onto(self.game_surf)

        # Particles + floating numbers on top of lighting
        self.particles.update()
        self.particles.draw(self.game_surf)
        self.numbers.update()
        self.numbers.draw(self.game_surf)

        self.screen.blit(self.game_surf, (0, 0))

    # ------------------------------------------------------------------
    # Tile drawing
    # ------------------------------------------------------------------

    def _draw_tiles(
        self,
        dungeon:  DungeonMap,
        visible:  set,
        explored: set,
    ) -> None:
        ts  = TILE_RENDER_SIZE
        cam = self.camera
        cx  = cam.cam_tile_x
        cy  = cam.cam_tile_y

        for ty in range(cy, min(cy + VIEWPORT_TILES_H + 2, dungeon.height)):
            for tx in range(cx, min(cx + VIEWPORT_TILES_W + 2, dungeon.width)):
                tile = dungeon.tiles[ty][tx]
                sx, sy = cam.tile_to_screen(tx, ty)
                pos    = (tx, ty)

                if pos in visible:
                    self._blit_tile_visible(tile, sx, sy, tx, ty)
                elif pos in explored:
                    self._blit_tile_explored(tile, sx, sy, tx, ty)
                # else: black (already cleared)

    def _blit_tile_visible(self, tile: str, sx: int, sy: int, tx: int, ty: int) -> None:
        ts = TILE_RENDER_SIZE
        if tile == TileType.FLOOR:
            surf = self.tileset.get_floor(_floor_variant(tx, ty))
            self.game_surf.blit(surf, (sx, sy))
        elif tile == TileType.WALL:
            surf = self.tileset.get_wall(_wall_variant(tx, ty))
            self.game_surf.blit(surf, (sx, sy))
        elif tile == TileType.DOOR:
            surf = self.tileset.get_door()
            self.game_surf.blit(surf, (sx, sy))
        elif tile == TileType.STAIRS:
            surf = self.tileset.get_stairs()
            # Subtle glow pulse
            glow = pygame.Surface((ts, ts), pygame.SRCALPHA)
            alpha = 40 + int(30 * abs(__import__('math').sin(self._tick * 0.05)))
            pygame.draw.ellipse(glow, (60, 140, 255, alpha), (4, 14, ts - 8, ts - 18))
            self.game_surf.blit(surf, (sx, sy))
            self.game_surf.blit(glow, (sx, sy))
        elif tile == TileType.SHRINE:
            surf = self.tileset.get_shrine()
            # Shrine pulse
            glow = pygame.Surface((ts, ts), pygame.SRCALPHA)
            alpha = 50 + int(40 * abs(__import__('math').sin(self._tick * 0.04)))
            pygame.draw.circle(glow, (180, 80, 255, alpha), (ts // 2, ts // 2), ts // 2 - 2)
            self.game_surf.blit(surf, (sx, sy))
            self.game_surf.blit(glow, (sx, sy))
        else:
            pygame.draw.rect(self.game_surf, (50, 47, 62), (sx, sy, ts, ts))

    def _blit_tile_explored(self, tile: str, sx: int, sy: int, tx: int, ty: int) -> None:
        ts = TILE_RENDER_SIZE
        # Dim version of the visible tile
        if tile in (TileType.FLOOR, TileType.STAIRS, TileType.SHRINE, TileType.DOOR):
            surf = self.tileset.get_floor(_floor_variant(tx, ty))
        elif tile == TileType.WALL:
            surf = self.tileset.get_wall(_wall_variant(tx, ty))
        else:
            return
        # Darken by blitting a semi-transparent black rect on a copy
        dim = surf.copy()
        dark = pygame.Surface((ts, ts), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 155))
        dim.blit(dark, (0, 0))
        self.game_surf.blit(dim, (sx, sy))

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def _draw_items(self, items: list, visible: set) -> None:
        ts  = TILE_RENDER_SIZE
        cam = self.camera
        for item in items:
            pos = (item.x, item.y)
            if pos not in visible:
                continue
            sx, sy = cam.tile_to_screen(item.x, item.y)

            # Item icon base circle
            icon = pygame.Surface((ts, ts), pygame.SRCALPHA)
            color = item.color
            pygame.draw.rect(icon, (*color, 60), (2, 2, ts - 4, ts - 4), border_radius=5)
            pygame.draw.rect(icon, (*color, 180), (2, 2, ts - 4, ts - 4), 1, border_radius=5)

            # Glyph
            glyph = self._glyph_font.render(item.symbol, True, color)
            icon.blit(glyph, glyph.get_rect(center=(ts // 2, ts // 2)))

            # Shard gets a pulse glow
            if getattr(item, "is_shard", False):
                alpha = 60 + int(50 * abs(__import__('math').sin(self._tick * 0.06)))
                glow  = pygame.Surface((ts, ts), pygame.SRCALPHA)
                pygame.draw.circle(glow, (80, 220, 220, alpha), (ts // 2, ts // 2), ts // 2)
                self.game_surf.blit(glow, (sx, sy))

            self.game_surf.blit(icon, (sx, sy))

            # Occasional sparkle for shard / key
            if getattr(item, "is_shard", False) and self._tick % 12 == 0:
                self.particles.sparkle(sx + ts // 2, sy + ts // 2, color=(80, 220, 220), count=2)

    # ------------------------------------------------------------------
    # Enemies
    # ------------------------------------------------------------------

    def _draw_entities(self, entities: list, visible: set) -> None:
        ts  = TILE_RENDER_SIZE
        cam = self.camera
        for e in entities:
            if not e.alive or (e.x, e.y) not in visible:
                continue
            sx, sy = cam.tile_to_screen(e.x, e.y)
            sprite = self.get_entity_sprite(e)
            sprite.update()

            frame = sprite.current
            # Scale to TILE_RENDER_SIZE if needed
            if frame.get_size() != (ts, ts):
                frame = pygame.transform.scale(frame, (ts, ts))

            # Status glow
            for status in e.status_effects:
                glow_rgb = _STATUS_GLOW.get(status.name)
                if glow_rgb:
                    glow = pygame.Surface((ts, ts), pygame.SRCALPHA)
                    glow.fill((*glow_rgb, 60))
                    self.game_surf.blit(glow, (sx, sy))
                    break

            self.game_surf.blit(frame, (sx, sy))

            # Ghost trail for Wraith
            from entities.enemy import Wraith
            if isinstance(e, Wraith) and self._tick % 3 == 0:
                self.particles.ghost(sx + ts // 2, sy + ts // 2)

            # HP bar above enemy
            self._draw_hp_bar(sx, sy, e.hp, e.max_hp)

    def _draw_hp_bar(self, sx: int, sy: int, hp: int, max_hp: int) -> None:
        ts  = TILE_RENDER_SIZE
        bw  = ts - 4
        bh  = 3
        by  = sy - 6
        bx  = sx + 2
        fill = max(0, int(bw * hp / max(max_hp, 1)))
        pygame.draw.rect(self.game_surf, (60, 15, 15), (bx, by, bw, bh))
        if fill > 0:
            r = int(220 * (1 - hp / max_hp))
            g = int(180 * (hp / max_hp))
            pygame.draw.rect(self.game_surf, (r, g, 20), (bx, by, fill, bh))

    # ------------------------------------------------------------------
    # Player
    # ------------------------------------------------------------------

    def _draw_player(self, player) -> None:
        ts  = TILE_RENDER_SIZE
        cam = self.camera
        sx, sy = cam.tile_to_screen(player.x, player.y)

        # Status glow under player
        for status in player.status_effects:
            glow_rgb = _STATUS_GLOW.get(status.name)
            if glow_rgb:
                glow = pygame.Surface((ts, ts), pygame.SRCALPHA)
                glow.fill((*glow_rgb, 80))
                self.game_surf.blit(glow, (sx, sy))
                # Particle indicator
                if self._tick % 8 == 0:
                    if status.name in ("bleed",):
                        self.particles.blood(sx + ts // 2, sy + ts // 2, count=1)
                    elif status.name in ("poison",):
                        self.particles.sparkle(sx + ts // 2, sy + ts // 2,
                                               color=(40, 200, 40), count=1)
                    elif status.name == "cursed":
                        self.particles.ghost(sx + ts // 2, sy + ts // 2,
                                             color=(150, 40, 200), count=1)
                break

        sprite = self._player_sprites
        if sprite:
            sprite.update()
            frame = sprite.current
            if frame.get_size() != (ts, ts):
                frame = pygame.transform.scale(frame, (ts, ts))
            self.game_surf.blit(frame, (sx, sy))
        else:
            # Fallback glyph
            glyph = self._glyph_font.render("@", True, (220, 220, 80))
            self.game_surf.blit(glyph, (sx, sy))

    # ------------------------------------------------------------------
    # Convenience: emit events (called by game.py)
    # ------------------------------------------------------------------

    def emit_damage_dealt(self, target, amount: int, crit: bool = False) -> None:
        cam = self.camera
        sx, sy = cam.tile_to_screen(target.x, target.y)
        ts = TILE_RENDER_SIZE
        self.numbers.damage_dealt(amount, sx + ts // 2, sy, crit=crit)
        self.particles.blood(sx + ts // 2, sy + ts // 2, count=4 if crit else 2)
        if crit:
            self.camera.add_shake(3.0, 5)

    def emit_damage_taken(self, player, amount: int) -> None:
        cam = self.camera
        sx, sy = cam.tile_to_screen(player.x, player.y)
        ts = TILE_RENDER_SIZE
        self.numbers.damage_taken(amount, sx + ts // 2, sy)
        self.camera.add_shake(2.5, 4)

    def emit_heal(self, player, amount: int) -> None:
        cam = self.camera
        sx, sy = cam.tile_to_screen(player.x, player.y)
        ts = TILE_RENDER_SIZE
        self.numbers.heal(amount, sx + ts // 2, sy)
        self.particles.sparkle(sx + ts // 2, sy + ts // 2, color=(80, 220, 100), count=4)

    def emit_level_up(self, player) -> None:
        cam = self.camera
        sx, sy = cam.tile_to_screen(player.x, player.y)
        ts = TILE_RENDER_SIZE
        self.particles.level_up(sx + ts // 2, sy + ts // 2)

    def emit_pickup(self, item, px: int, py: int) -> None:
        cam = self.camera
        sx, sy = cam.tile_to_screen(px, py)
        ts = TILE_RENDER_SIZE
        self.particles.sparkle(sx + ts // 2, sy + ts // 2, color=item.color, count=5)

    def emit_boss_slam(self, player) -> None:
        self.camera.add_shake(8.0, 12)
        cam = self.camera
        sx, sy = cam.tile_to_screen(player.x, player.y)
        ts = TILE_RENDER_SIZE
        self.numbers.damage_taken(15, sx + ts // 2, sy)
        self.particles.blood(sx + ts // 2, sy + ts // 2, count=10)
