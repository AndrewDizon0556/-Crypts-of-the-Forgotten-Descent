"""Field of View — raycasting implementation."""
from __future__ import annotations

import math

from config import FOV_RADIUS
from systems.dungeon import DungeonMap, TileType


def compute_fov(
    dungeon: DungeonMap,
    origin_x: int,
    origin_y: int,
    radius: int = FOV_RADIUS,
) -> set[tuple[int, int]]:
    """
    Cast rays in 360 degrees from origin; return set of visible tile coords.
    Walls are visible but block further vision along the ray.
    """
    visible: set[tuple[int, int]] = {(origin_x, origin_y)}

    for angle_deg in range(360):
        angle = math.radians(angle_deg)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        dx = dy = 0.0
        for _ in range(radius):
            dx += cos_a
            dy += sin_a
            tx = int(origin_x + dx)
            ty = int(origin_y + dy)
            if not (0 <= tx < dungeon.width and 0 <= ty < dungeon.height):
                break
            visible.add((tx, ty))
            if dungeon.tiles[ty][tx] == TileType.WALL:
                break   # wall blocks further sight along this ray

    return visible
