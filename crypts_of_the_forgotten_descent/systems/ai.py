"""Enemy AI: 3-state FSM (IDLE / CHASE / ATTACK) with BFS pathfinding."""
from __future__ import annotations

from collections import deque
from typing import Optional

from entities.enemy import Enemy, AIState
from systems.dungeon import DungeonMap


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------

def manhattan(ax: int, ay: int, bx: int, by: int) -> int:
    return abs(ax - bx) + abs(ay - by)


def chebyshev(ax: int, ay: int, bx: int, by: int) -> int:
    return max(abs(ax - bx), abs(ay - by))


# ---------------------------------------------------------------------------
# BFS pathfinder
# ---------------------------------------------------------------------------

def bfs_next_step(
    dungeon:   DungeonMap,
    start:     tuple[int, int],
    goal:      tuple[int, int],
    occupied:  set[tuple[int, int]],
    wall_pass: bool = False,
) -> Optional[tuple[int, int]]:
    """
    BFS from `start` toward `goal`.
    wall_pass=True lets the entity move through walls (Wraith phase-walk).
    Returns the *first step* tile, or None if no path exists.
    """
    if start == goal:
        return None
    visited: set[tuple[int, int]] = {start}
    queue: deque[tuple[tuple[int, int], tuple[int, int] | None]] = deque(
        [(start, None)]
    )
    while queue:
        pos, first = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            npos = (pos[0] + dx, pos[1] + dy)
            if npos in visited:
                continue
            if wall_pass:
                if not (0 <= npos[0] < dungeon.width and 0 <= npos[1] < dungeon.height):
                    continue
                from systems.dungeon import TileType as _TT
                if dungeon.get_tile(*npos) == _TT.DOOR:
                    continue   # locked doors stop even Wraiths
            else:
                if not dungeon.is_walkable(*npos):
                    continue
            step = first if first is not None else npos
            if npos == goal:
                return step
            if npos not in occupied:
                visited.add(npos)
                queue.append((npos, step))
    return None


# ---------------------------------------------------------------------------
# FSM update
# ---------------------------------------------------------------------------

def update_enemy_ai(
    enemy:    Enemy,
    player,
    dungeon:  DungeonMap,
    occupied: set[tuple[int, int]],
    fov_tiles: set[tuple[int, int]],
) -> Optional[dict]:
    """
    Run one AI turn for `enemy`.
    Enemies outside the player's FOV stay frozen (remain IDLE).
    Returns an action dict or None:
      {"move": (x, y)}   — move to tile
      {"attack": True}   — attack player
    """
    # Frozen when outside player's vision
    if (enemy.x, enemy.y) not in fov_tiles:
        enemy.ai_state = AIState.IDLE
        return None

    dist = manhattan(enemy.x, enemy.y, player.x, player.y)

    # IDLE → CHASE transition
    if enemy.ai_state == AIState.IDLE and dist <= enemy.detection_range:
        enemy.ai_state = AIState.CHASE

    # CHASE
    if enemy.ai_state == AIState.CHASE:
        if dist <= 1:
            enemy.ai_state = AIState.ATTACK
        elif dist > enemy.detection_range + 2:
            enemy.ai_state = AIState.IDLE
            return None
        else:
            from entities.enemy import Wraith
            step = bfs_next_step(
                dungeon, enemy.pos, player.pos, occupied,
                wall_pass=isinstance(enemy, Wraith),
            )
            if step:
                return {"move": step}
            return None

    # ATTACK
    if enemy.ai_state == AIState.ATTACK:
        if dist > 1:
            enemy.ai_state = AIState.CHASE
            return None
        return {"attack": True}

    return None
