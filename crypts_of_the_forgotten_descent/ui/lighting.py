"""Radial gradient lighting overlay drawn on top of the game surface."""
from __future__ import annotations
import math
import pygame
from config import GAME_AREA_W, GAME_AREA_H, TILE_RENDER_SIZE, FOV_RADIUS


# Pre-bake a radial gradient "light disc" into a surface.
# The disc is white in the center, transparent at the edge; we subtract
# it from a dark overlay to punch warm-light holes.

_LIGHT_RADIUS_PX = int(FOV_RADIUS * TILE_RENDER_SIZE * 1.1)


def _bake_light_disc(radius: int, warm: tuple = (255, 160, 80)) -> pygame.Surface:
    """Radial gradient disc — white core fading to transparent."""
    diam = radius * 2
    surf = pygame.Surface((diam, diam), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    for r in range(radius, 0, -1):
        t     = r / radius            # 1 at edge → 0 at center
        alpha = int(255 * (1.0 - t ** 0.5))
        color = (warm[0], warm[1], warm[2], alpha)
        pygame.draw.circle(surf, color, (radius, radius), r)
    return surf


class LightingSystem:
    """
    Manages a per-frame SRCALPHA overlay.
    Usage:
        lighting.begin_frame()
        lighting.add_light(screen_x, screen_y, radius_px, warm_color)
        lighting.blit_onto(game_surface)
    """

    # Ambient darkness level 0-255 (higher = darker)
    AMBIENT_DARK = 210

    def __init__(self) -> None:
        self._overlay = pygame.Surface((GAME_AREA_W, GAME_AREA_H), pygame.SRCALPHA)
        self._disc    = _bake_light_disc(_LIGHT_RADIUS_PX, (255, 160, 80))
        self._small_disc = _bake_light_disc(TILE_RENDER_SIZE * 2, (255, 140, 60))
        self._torch_tick = 0

    def begin_frame(self) -> None:
        """Fill overlay with dark, then punch light holes."""
        self._overlay.fill((0, 0, 0, self.AMBIENT_DARK))
        self._torch_tick += 1

    def add_light(self, sx: int, sy: int,
                  disc: pygame.Surface | None = None) -> None:
        """Blit a light disc centered at (sx, sy) using BLEND_RGBA_SUB."""
        d = disc or self._disc
        cx = sx - d.get_width()  // 2
        cy = sy - d.get_height() // 2
        self._overlay.blit(d, (cx, cy), special_flags=pygame.BLEND_RGBA_SUB)

    def add_torch_light(self, sx: int, sy: int) -> None:
        """Smaller warm light with subtle flicker."""
        flicker = math.sin(self._torch_tick * 0.25) * 6
        r = int(TILE_RENDER_SIZE * 2.2 + flicker)
        if r > 4:
            disc = _bake_light_disc(r, (255, 140, 60))
            self.add_light(sx, sy, disc)

    def blit_onto(self, surf: pygame.Surface) -> None:
        surf.blit(self._overlay, (0, 0))

    # Pre-baked disc for the player (reused every frame)
    @property
    def player_disc(self) -> pygame.Surface:
        return self._disc
