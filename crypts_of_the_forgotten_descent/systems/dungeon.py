"""BSP dungeon generator — creates one floor's tile map and room list."""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from config import MAP_WIDTH, MAP_HEIGHT


# ---------------------------------------------------------------------------
# Tile constants
# ---------------------------------------------------------------------------

class TileType:
    WALL   = "#"
    FLOOR  = "."
    STAIRS = ">"
    SHRINE = "Ω"  # Ω
    DOOR   = "+"


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

@dataclass
class Room:
    x: int
    y: int
    width:  int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def inner_tiles(self) -> list[tuple[int, int]]:
        return [
            (self.x + dx, self.y + dy)
            for dx in range(self.width)
            for dy in range(self.height)
        ]

    def distance_to(self, other: "Room") -> float:
        cx, cy = self.center
        ox, oy = other.center
        return ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height


# ---------------------------------------------------------------------------
# DungeonMap — the floor data container
# ---------------------------------------------------------------------------

@dataclass
class DungeonMap:
    width:  int = MAP_WIDTH
    height: int = MAP_HEIGHT

    def __post_init__(self) -> None:
        self.tiles: list[list[str]] = [
            [TileType.WALL] * self.width for _ in range(self.height)
        ]
        self.rooms:      list[Room]             = []
        self.enemies:    list                   = []
        self.items:      list                   = []
        self.shrines:    list[tuple[int, int]]  = []
        self.stairs_pos: Optional[tuple[int, int]] = None
        self.spawn_pos:  tuple[int, int]           = (0, 0)
        self.explored:   set[tuple[int, int]]      = set()

    def get_tile(self, x: int, y: int) -> str:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return TileType.WALL

    def set_tile(self, x: int, y: int, tile: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = tile

    def is_walkable(self, x: int, y: int) -> bool:
        return self.get_tile(x, y) not in (TileType.WALL, TileType.DOOR)

    def floor_tiles(self) -> list[tuple[int, int]]:
        """All walkable tile coordinates."""
        return [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self.tiles[y][x] != TileType.WALL
        ]


# ---------------------------------------------------------------------------
# DungeonGenerator — BSP algorithm
# ---------------------------------------------------------------------------

class DungeonGenerator:
    """
    Binary Space Partitioning dungeon generator.

    Splits the map recursively into leaves, places one room per leaf,
    connects them with L-shaped corridors, then validates full connectivity.
    """

    # BSP leaf constraints
    MIN_LEAF_W = 8
    MIN_LEAF_H = 8

    # Room size constraints (inside each leaf, with 1-tile padding)
    ROOM_MIN_W = 5
    ROOM_MIN_H = 4
    ROOM_MAX_W = 15
    ROOM_MAX_H = 10

    MAX_RETRIES = 3
    MAX_BSP_DEPTH = 5

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng  = random.Random(seed)
        self.seed = seed

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def generate(self, floor: int) -> DungeonMap:
        """Generate and return a validated dungeon floor."""
        for _ in range(self.MAX_RETRIES):
            dungeon = self._attempt(floor)
            if dungeon and self._validate(dungeon):
                return dungeon
        return self._fallback()

    # ------------------------------------------------------------------
    # Private — generation
    # ------------------------------------------------------------------

    def _attempt(self, floor: int) -> Optional[DungeonMap]:
        dungeon = DungeonMap()
        leaves  = self._bsp_split(0, 0, MAP_WIDTH, MAP_HEIGHT, depth=0)

        for leaf in leaves:
            room = self._make_room(leaf)
            if room:
                dungeon.rooms.append(room)
                for tx, ty in room.inner_tiles:
                    dungeon.set_tile(tx, ty, TileType.FLOOR)

        if not dungeon.rooms:
            return None

        self._connect_rooms(dungeon)

        # Spawn in first room, stairs in the farthest room
        dungeon.spawn_pos = dungeon.rooms[0].center
        farthest = max(dungeon.rooms, key=lambda r: r.distance_to(dungeon.rooms[0]))
        sx, sy = farthest.center
        dungeon.set_tile(sx, sy, TileType.STAIRS)
        dungeon.stairs_pos = (sx, sy)
        return dungeon

    def _bsp_split(
        self, x: int, y: int, w: int, h: int, depth: int
    ) -> list[tuple[int, int, int, int]]:
        """Recursively split space; return list of (x, y, w, h) leaf rects."""
        too_small = w < self.MIN_LEAF_W * 2 or h < self.MIN_LEAF_H * 2
        if too_small or depth >= self.MAX_BSP_DEPTH:
            return [(x, y, w, h)]

        split_horizontal = w > h   # prefer splitting the longer axis
        if split_horizontal:
            split = self.rng.randint(self.MIN_LEAF_W, w - self.MIN_LEAF_W)
            return (
                self._bsp_split(x,          y, split,     h, depth + 1)
                + self._bsp_split(x + split, y, w - split, h, depth + 1)
            )
        else:
            split = self.rng.randint(self.MIN_LEAF_H, h - self.MIN_LEAF_H)
            return (
                self._bsp_split(x, y,          w, split,     depth + 1)
                + self._bsp_split(x, y + split, w, h - split, depth + 1)
            )

    def _make_room(self, leaf: tuple[int, int, int, int]) -> Optional[Room]:
        lx, ly, lw, lh = leaf
        max_rw = min(self.ROOM_MAX_W, lw - 2)
        max_rh = min(self.ROOM_MAX_H, lh - 2)
        if max_rw < self.ROOM_MIN_W or max_rh < self.ROOM_MIN_H:
            return None
        rw = self.rng.randint(self.ROOM_MIN_W, max_rw)
        rh = self.rng.randint(self.ROOM_MIN_H, max_rh)
        rx = self.rng.randint(lx + 1, lx + lw - rw - 1)
        ry = self.rng.randint(ly + 1, ly + lh - rh - 1)
        return Room(rx, ry, rw, rh)

    def _connect_rooms(self, dungeon: DungeonMap) -> None:
        """Connect consecutive room pairs with L-shaped corridors."""
        for i in range(len(dungeon.rooms) - 1):
            ax, ay = dungeon.rooms[i].center
            bx, by = dungeon.rooms[i + 1].center
            if self.rng.random() < 0.5:
                self._carve_h(dungeon, ax, bx, ay)
                self._carve_v(dungeon, ay, by, bx)
            else:
                self._carve_v(dungeon, ay, by, ax)
                self._carve_h(dungeon, ax, bx, by)

    def _carve_h(self, dungeon: DungeonMap, x1: int, x2: int, y: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            dungeon.set_tile(x, y, TileType.FLOOR)

    def _carve_v(self, dungeon: DungeonMap, y1: int, y2: int, x: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            dungeon.set_tile(x, y, TileType.FLOOR)

    # ------------------------------------------------------------------
    # Private — validation
    # ------------------------------------------------------------------

    def _validate(self, dungeon: DungeonMap) -> bool:
        """BFS flood fill from spawn; confirm every room center is reachable."""
        if not dungeon.rooms:
            return False
        visited: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int]] = deque([dungeon.spawn_pos])
        visited.add(dungeon.spawn_pos)
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                npos = (cx + dx, cy + dy)
                if npos not in visited and dungeon.is_walkable(*npos):
                    visited.add(npos)
                    queue.append(npos)
        return all(r.center in visited for r in dungeon.rooms)

    # ------------------------------------------------------------------
    # Private — fallback
    # ------------------------------------------------------------------

    def _fallback(self) -> DungeonMap:
        """Single large room used when BSP generation fails repeatedly."""
        dungeon = DungeonMap()
        room    = Room(5, 5, 20, 15)
        dungeon.rooms.append(room)
        for tx, ty in room.inner_tiles:
            dungeon.set_tile(tx, ty, TileType.FLOOR)
        dungeon.spawn_pos  = room.center
        dungeon.stairs_pos = (22, 12)
        dungeon.set_tile(22, 12, TileType.STAIRS)
        return dungeon
