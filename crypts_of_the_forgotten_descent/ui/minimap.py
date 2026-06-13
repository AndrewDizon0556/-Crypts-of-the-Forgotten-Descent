"""Minimap overlay — small top-down view of the explored dungeon."""
from __future__ import annotations

import pygame

from config import MAP_WIDTH, MAP_HEIGHT, GAME_AREA_H, PLAYER_COLOR, GOLD
from systems.dungeon import DungeonMap, TileType

_SCALE   = 2          # pixels per map tile
_MINI_W  = MAP_WIDTH  * _SCALE   # 120
_MINI_H  = MAP_HEIGHT * _SCALE   # 80
_PAD     = 8          # margin from game-area edge

# Minimap tile colors
_COLOR_FLOOR    = (72, 68, 92)
_COLOR_WALL     = (50, 46, 65)
_COLOR_STAIRS   = (190, 160, 40)
_COLOR_SHRINE   = (150, 90, 200)
_COLOR_EXPLORED = (35, 32, 46)
_COLOR_BORDER   = (60, 50, 80)
_COLOR_PLAYER   = PLAYER_COLOR
_COLOR_ENEMY    = (200, 80, 80)
_COLOR_ITEM     = (80, 200, 160)


class Minimap:
    """Small overview rendered in the bottom-left corner of the game viewport."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen  = screen
        self.surface = pygame.Surface((_MINI_W + 2, _MINI_H + 2))
        self._font   = pygame.font.SysFont("monospace", 11)

    def render(
        self,
        dungeon:   DungeonMap,
        player,
        explored:  set[tuple[int, int]],
    ) -> None:
        surf = self.surface
        surf.fill((8, 6, 14))

        # Draw explored tiles
        for (tx, ty) in explored:
            tile = dungeon.get_tile(tx, ty)
            px = 1 + tx * _SCALE
            py = 1 + ty * _SCALE
            if tile == TileType.WALL:
                color = _COLOR_WALL
            elif tile == TileType.STAIRS:
                color = _COLOR_STAIRS
            elif tile == TileType.SHRINE:
                color = _COLOR_SHRINE
            else:
                color = _COLOR_FLOOR
            pygame.draw.rect(surf, color, (px, py, _SCALE, _SCALE))

        # Enemy dots (all alive — minimap is a global view)
        for e in dungeon.enemies:
            if e.alive:
                px = 1 + e.x * _SCALE
                py = 1 + e.y * _SCALE
                if 0 <= px < _MINI_W and 0 <= py < _MINI_H:
                    pygame.draw.rect(surf, _COLOR_ENEMY, (px, py, _SCALE, _SCALE))

        # Player dot
        ppx = 1 + player.x * _SCALE
        ppy = 1 + player.y * _SCALE
        if 0 <= ppx < _MINI_W + 1 and 0 <= ppy < _MINI_H + 1:
            pygame.draw.rect(surf, _COLOR_PLAYER, (ppx - 1, ppy - 1, _SCALE + 2, _SCALE + 2))

        # Border
        pygame.draw.rect(surf, _COLOR_BORDER, (0, 0, _MINI_W + 2, _MINI_H + 2), 1)

        # Blit to bottom-left of game area with padding
        blit_x = _PAD
        blit_y = GAME_AREA_H - _MINI_H - _PAD - 2
        self.screen.blit(surf, (blit_x, blit_y))

        # "MAP" label above
        label = self._font.render("MAP", True, (80, 75, 100))
        self.screen.blit(label, (blit_x, blit_y - label.get_height() - 2))
