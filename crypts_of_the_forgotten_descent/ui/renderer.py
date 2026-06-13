"""Dungeon tile renderer — draws the game-world viewport."""
from __future__ import annotations

import pygame

from config import (
    TILE_RENDER_SIZE, GAME_AREA_W, GAME_AREA_H,
    VIEWPORT_TILES_W, VIEWPORT_TILES_H,
    FLOOR_VISIBLE, WALL_VISIBLE, EXPLORED_FLOOR, EXPLORED_WALL,
    BLACK, GOLD, SHRINE_COLOR, YELLOW,
)
from systems.dungeon import DungeonMap, TileType


# Special tile display colors
_DOOR_COLOR     = (160, 115, 50)
_DOOR_EXP_COLOR = (55,  38, 16)

_TILE_COLORS: dict[str, tuple] = {
    TileType.FLOOR:  FLOOR_VISIBLE,
    TileType.WALL:   WALL_VISIBLE,
    TileType.STAIRS: GOLD,
    TileType.SHRINE: SHRINE_COLOR,
    TileType.DOOR:   _DOOR_COLOR,
}
_EXPLORED_COLORS: dict[str, tuple] = {
    TileType.FLOOR:  EXPLORED_FLOOR,
    TileType.WALL:   EXPLORED_WALL,
    TileType.STAIRS: (60, 50, 20),
    TileType.SHRINE: (50, 30, 60),
    TileType.DOOR:   _DOOR_EXP_COLOR,
}

# Status effect glow colours (SRCALPHA, alpha baked in separately)
_STATUS_GLOW: dict[str, tuple] = {
    "bleed":   (200,  30,  30),
    "poison":  ( 40, 200,  40),
    "cursed":  (150,  40, 200),
    "slow":    (220, 190,  40),
}


class Renderer:
    """
    Draws the dungeon viewport onto a sub-surface, then blits it to the screen.
    Camera is centered on the player, clamped to map bounds.
    """

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen      = screen
        self.font        = pygame.font.SysFont("monospace", TILE_RENDER_SIZE, bold=True)
        self.game_surf   = pygame.Surface((GAME_AREA_W, GAME_AREA_H))

    # ------------------------------------------------------------------
    # Public
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
        cam_x, cam_y = self._camera(player, dungeon)
        self.game_surf.fill(BLACK)
        self._draw_tiles(dungeon, visible_tiles, explored_tiles, cam_x, cam_y)
        self._draw_items(items, visible_tiles, cam_x, cam_y)
        self._draw_entities(entities, visible_tiles, cam_x, cam_y)
        self._draw_player(player, cam_x, cam_y)
        self.screen.blit(self.game_surf, (0, 0))

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _camera(self, player, dungeon: DungeonMap) -> tuple[int, int]:
        """Top-left tile coordinate that keeps the player centered."""
        half_w = VIEWPORT_TILES_W // 2
        half_h = VIEWPORT_TILES_H // 2
        cam_x = max(0, min(player.x - half_w, dungeon.width  - VIEWPORT_TILES_W))
        cam_y = max(0, min(player.y - half_h, dungeon.height - VIEWPORT_TILES_H))
        return cam_x, cam_y

    def _draw_tiles(
        self,
        dungeon:  DungeonMap,
        visible:  set,
        explored: set,
        cam_x:    int,
        cam_y:    int,
    ) -> None:
        ts = TILE_RENDER_SIZE
        for ty in range(cam_y, cam_y + VIEWPORT_TILES_H + 1):
            for tx in range(cam_x, cam_x + VIEWPORT_TILES_W + 1):
                if not (0 <= tx < dungeon.width and 0 <= ty < dungeon.height):
                    continue
                tile   = dungeon.tiles[ty][tx]
                sx, sy = (tx - cam_x) * ts, (ty - cam_y) * ts
                pos    = (tx, ty)

                if pos in visible:
                    color = _TILE_COLORS.get(tile, FLOOR_VISIBLE)
                    pygame.draw.rect(self.game_surf, color, (sx, sy, ts, ts))
                    # Render glyph for special tiles
                    if tile == TileType.STAIRS:
                        g = self.font.render(tile, True, GOLD)
                        self.game_surf.blit(g, (sx, sy))
                    elif tile == TileType.SHRINE:
                        g = self.font.render(tile, True, SHRINE_COLOR)
                        self.game_surf.blit(g, (sx, sy))
                    elif tile == TileType.DOOR:
                        g = self.font.render(tile, True, _DOOR_COLOR)
                        self.game_surf.blit(g, (sx, sy))
                elif pos in explored:
                    color = _EXPLORED_COLORS.get(tile, EXPLORED_FLOOR)
                    pygame.draw.rect(self.game_surf, color, (sx, sy, ts, ts))
                # Else: unexplored → black (already cleared by fill)

    def _draw_items(
        self,
        items:   list,
        visible: set,
        cam_x:   int,
        cam_y:   int,
    ) -> None:
        ts = TILE_RENDER_SIZE
        for item in items:
            if (item.x, item.y) not in visible:
                continue
            sx = (item.x - cam_x) * ts
            sy = (item.y - cam_y) * ts
            surf = self.font.render(item.symbol, True, item.color)
            self.game_surf.blit(surf, (sx, sy))

    def _draw_entities(
        self,
        entities: list,
        visible:  set,
        cam_x: int,
        cam_y: int,
    ) -> None:
        ts = TILE_RENDER_SIZE
        for e in entities:
            if not e.alive or (e.x, e.y) not in visible:
                continue
            sx, sy = (e.x - cam_x) * ts, (e.y - cam_y) * ts
            surf = self.font.render(e.symbol, True, e.color)
            self.game_surf.blit(surf, (sx, sy))

    def _draw_player(self, player, cam_x: int, cam_y: int) -> None:
        ts = TILE_RENDER_SIZE
        sx = (player.x - cam_x) * ts
        sy = (player.y - cam_y) * ts

        # Status-effect glow behind the player glyph
        for status in player.status_effects:
            glow_rgb = _STATUS_GLOW.get(status.name)
            if glow_rgb:
                glow = pygame.Surface((ts, ts), pygame.SRCALPHA)
                glow.fill((*glow_rgb, 80))
                self.game_surf.blit(glow, (sx, sy))
                break   # one glow at a time (highest-priority status wins)

        surf = self.font.render(player.symbol, True, player.color)
        self.game_surf.blit(surf, (sx, sy))
