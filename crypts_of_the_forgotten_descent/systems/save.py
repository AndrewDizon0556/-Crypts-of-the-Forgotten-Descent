"""JSON save / load system — single save slot, permadeath on death."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

SAVE_FILE = Path("save.json")


def save_exists() -> bool:
    return SAVE_FILE.exists()


def delete_save() -> None:
    """Erase the save file (called on player death — permadeath)."""
    if SAVE_FILE.exists():
        SAVE_FILE.unlink()


def save_game(game) -> None:
    """Serialize the current game session and write to save.json."""
    state = _build_state(game)
    with open(SAVE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_game() -> Optional[dict]:
    """Return the parsed save dict, or None if no save exists."""
    if not SAVE_FILE.exists():
        return None
    with open(SAVE_FILE) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Private
# ---------------------------------------------------------------------------

def _build_state(game) -> dict:
    p = game.player
    return {
        "floor":        game.current_floor,
        "dungeon_seed": game.dungeon_seed,
        "player": {
            "name":             p.name,
            "class":            p.character_class,
            "hp":               p.hp,
            "max_hp":           p.max_hp,
            "atk":              p.atk,
            "defense":          p.defense,
            "level":            p.level,
            "xp":               p.xp,
            "gold":             p.gold,
            "passive":          p.passive,
            "shard_echo":       p.shard_echo,
            "backstab_ready":   getattr(p, "backstab_ready", False),
            "equipped_weapon":  p.equipped_weapon.key if p.equipped_weapon else None,
            "equipped_armor":   p.equipped_armor.key  if p.equipped_armor  else None,
            "inventory":        [item.key for item in p.inventory],
        },
        "stats": game.session_stats,
    }
