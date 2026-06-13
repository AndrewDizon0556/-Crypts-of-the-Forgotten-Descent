"""Smooth camera with lerp and screen-shake support."""
from __future__ import annotations
import random
import math
from config import GAME_AREA_W, GAME_AREA_H, TILE_RENDER_SIZE, VIEWPORT_TILES_W, VIEWPORT_TILES_H


class Camera:
    def __init__(self) -> None:
        self.x: float = 0.0   # current camera top-left tile (fractional)
        self.y: float = 0.0
        self._shake_frames: int   = 0
        self._shake_intensity: float = 0.0
        self._shake_dx: float = 0.0
        self._shake_dy: float = 0.0

    # ------------------------------------------------------------------
    def update(self, player, dungeon) -> None:
        """Lerp camera toward player; update shake offset."""
        target_x = player.x - VIEWPORT_TILES_W / 2
        target_y = player.y - VIEWPORT_TILES_H / 2

        max_cx = dungeon.width  - VIEWPORT_TILES_W
        max_cy = dungeon.height - VIEWPORT_TILES_H
        target_x = max(0.0, min(float(target_x), float(max_cx)))
        target_y = max(0.0, min(float(target_y), float(max_cy)))

        LERP = 0.18
        self.x += (target_x - self.x) * LERP
        self.y += (target_y - self.y) * LERP

        # Shake decay
        if self._shake_frames > 0:
            self._shake_frames -= 1
            angle = random.uniform(0, 2 * math.pi)
            self._shake_dx = math.cos(angle) * self._shake_intensity
            self._shake_dy = math.sin(angle) * self._shake_intensity
        else:
            self._shake_dx = 0.0
            self._shake_dy = 0.0

    def add_shake(self, intensity: float = 4.0, frames: int = 6) -> None:
        self._shake_intensity = max(self._shake_intensity, intensity)
        self._shake_frames    = max(self._shake_frames, frames)

    # ------------------------------------------------------------------
    # Coordinate conversion
    # ------------------------------------------------------------------

    def tile_to_screen(self, tx: int, ty: int) -> tuple[int, int]:
        ts = TILE_RENDER_SIZE
        sx = int((tx - self.x) * ts + self._shake_dx)
        sy = int((ty - self.y) * ts + self._shake_dy)
        return sx, sy

    @property
    def cam_tile_x(self) -> int:
        return int(self.x)

    @property
    def cam_tile_y(self) -> int:
        return int(self.y)
