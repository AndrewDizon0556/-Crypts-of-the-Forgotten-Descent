"""Inventory and item management system."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config import MAX_INVENTORY_SLOTS

_ITEMS_FILE = Path(__file__).parent.parent / "data" / "items.json"


@dataclass
class Item:
    key:       str
    name:      str
    symbol:    str
    item_type: str    # "consumable" | "weapon" | "armor" | "shard" | "key"
    color:     tuple[int, int, int]
    x:         int = 0
    y:         int = 0
    # Consumable
    effect: str = ""
    value:  int = 0
    # Equipment
    atk_bonus:  int   = 0
    def_bonus:  int   = 0
    atk_penalty: int  = 0
    lifesteal:  float = 0.0
    # Specials
    is_shard: bool = False
    is_key:   bool = False

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)


def load_item_definitions() -> dict[str, dict]:
    """Load items.json and return the raw dict."""
    with open(_ITEMS_FILE) as f:
        return json.load(f)


def build_item(key: str, x: int = 0, y: int = 0) -> Item:
    """Construct an Item from a key defined in items.json."""
    defs = load_item_definitions()
    d    = defs[key]
    return Item(
        key=key,
        name=d["name"],
        symbol=d["symbol"],
        item_type=d["type"],
        color=tuple(d.get("color", [200, 200, 200])),
        x=x, y=y,
        effect=d.get("effect", ""),
        value=d.get("value", 0),
        atk_bonus=d.get("atk_bonus", 0),
        def_bonus=d.get("def_bonus", 0),
        atk_penalty=d.get("atk_penalty", 0),
        lifesteal=d.get("lifesteal", 0.0),
        is_shard=d.get("is_shard", False),
        is_key=d.get("is_key", False),
    )


# ---------------------------------------------------------------------------
# Item use logic
# ---------------------------------------------------------------------------

def use_item(player, item: Item) -> str:
    """Apply `item` to `player`. Returns a human-readable result string."""
    match item.item_type:
        case "consumable":
            return _use_consumable(player, item)
        case "weapon" | "armor":
            return _equip(player, item)
        case "shard":
            return f"You obtained the {item.name}!"
        case _:
            return "Nothing happens."


def _use_consumable(player, item: Item) -> str:
    match item.effect:
        case "heal":
            healed = player.heal(item.value)
            player.remove_status("bleed")   # any heal cures bleed
            return f"Restored {healed} HP."
        case "cure_poison":
            player.remove_status("poison")
            return "Poison cured."
        case "fire_damage":
            return f"FIRE_SCROLL:{item.value}"   # caller resolves AoE
        case "bomb":
            return f"BOMB:{item.value}"          # caller resolves AoE
        case _:
            return "Used."


def _equip(player, item: Item) -> str:
    if item.item_type == "weapon":
        old = player.equipped_weapon
        if old:
            player.atk -= old.atk_bonus
            player.add_to_inventory(old)
        player.equipped_weapon = item
        player.atk += item.atk_bonus
        return f"Equipped {item.name}."
    else:
        old = player.equipped_armor
        if old:
            player.defense -= old.def_bonus
            player.atk += abs(old.atk_penalty)   # remove old penalty
            player.add_to_inventory(old)
        player.equipped_armor = item
        player.defense += item.def_bonus
        player.atk -= abs(item.atk_penalty)
        return f"Equipped {item.name}."
