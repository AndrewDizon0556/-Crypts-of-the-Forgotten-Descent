"""Player entity with class-based stat templates and progression."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from config import (
    PLAYER_COLOR, MAX_PLAYER_LEVEL, MAX_INVENTORY_SLOTS,
    XP_PER_LEVEL_BASE,
)
from entities.entity import Entity, StatusEffect

# Starting stats per class
_CLASS_TEMPLATES: dict[str, dict] = {
    "warrior": {"max_hp": 40, "hp": 40, "atk": 6, "defense": 4, "passive": "iron_will"},
    "rogue":   {"max_hp": 25, "hp": 25, "atk": 9, "defense": 2, "passive": "backstab"},
    "mage":    {"max_hp": 20, "hp": 20, "atk": 5, "defense": 1, "passive": "arcane_surge"},
}


@dataclass
class Player(Entity):
    """The player character."""
    level:           int  = 1
    xp:              int  = 0
    gold:            int  = 0
    character_class: str  = "warrior"
    passive:         str  = "iron_will"
    inventory:       list = field(default_factory=list)
    equipped_weapon: Optional[object] = None
    equipped_armor:  Optional[object] = None
    # Rogue backstab tracker: True when the *next* hit on a new enemy gets the bonus
    backstab_ready: bool = False
    # Shrine Extra Life token
    shard_echo:     bool = False

    # ------------------------------------------------------------------
    # Constructor helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_class(cls, character_class: str) -> "Player":
        tmpl = _CLASS_TEMPLATES[character_class]
        player = cls(
            name=character_class.title(),
            symbol="@",
            x=0, y=0,
            max_hp=tmpl["max_hp"],
            hp=tmpl["hp"],
            atk=tmpl["atk"],
            defense=tmpl["defense"],
            color=PLAYER_COLOR,
            character_class=character_class,
            passive=tmpl["passive"],
        )
        if character_class == "rogue":
            player.backstab_ready = True
        return player

    # ------------------------------------------------------------------
    # XP & Leveling
    # ------------------------------------------------------------------

    @property
    def xp_to_next_level(self) -> int:
        return self.level * XP_PER_LEVEL_BASE

    def gain_xp(self, amount: int) -> bool:
        """Add XP; return True if a level-up occurred."""
        if self.level >= MAX_PLAYER_LEVEL:
            return False
        self.xp += amount
        if self.xp >= self.xp_to_next_level:
            self._level_up()
            return True
        return False

    def _level_up(self) -> None:
        self.xp -= self.xp_to_next_level   # carry over excess
        self.level   += 1
        self.max_hp  += 10
        self.hp       = min(self.max_hp, self.hp + 10)
        self.atk     += 2
        self.defense += 1

    # ------------------------------------------------------------------
    # Passive-modified stats
    # ------------------------------------------------------------------

    @property
    def effective_defense(self) -> int:
        """Defense with Iron Will passive applied when below 25% HP."""
        base = self.defense
        if self.passive == "iron_will" and self.hp <= self.max_hp * 0.25:
            base += 4
        # Halved if CURSED
        if self.has_status("cursed"):
            base = max(0, base // 2)
        return base

    @property
    def effective_atk(self) -> int:
        base = self.atk
        if self.has_status("cursed"):
            base = max(1, base // 2)
        return base

    # ------------------------------------------------------------------
    # Inventory helpers
    # ------------------------------------------------------------------

    @property
    def inventory_full(self) -> bool:
        return len(self.inventory) >= MAX_INVENTORY_SLOTS

    def add_to_inventory(self, item: object) -> bool:
        """Return False if inventory is full."""
        if self.inventory_full:
            return False
        self.inventory.append(item)
        return True

    def remove_from_inventory(self, item: object) -> None:
        if item in self.inventory:
            self.inventory.remove(item)
