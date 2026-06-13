"""Enemy base class, FSM states, concrete enemy types, and factory."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from entities.entity import Entity, StatusEffect


class AIState(Enum):
    IDLE   = auto()
    CHASE  = auto()
    ATTACK = auto()


@dataclass
class Enemy(Entity):
    """Base class for all enemies."""
    xp_reward:       int      = 0
    gold_reward:     int      = 0
    detection_range: int      = 5
    ai_state:        AIState  = field(default=AIState.IDLE)
    attack_count:    int      = 0    # tracks every-3rd-attack specials
    path:            list     = field(default_factory=list)

    @property
    def effective_atk(self) -> int:
        return self.atk

    @property
    def effective_def(self) -> int:
        return self.defense

    def scale_to_floor(self, floor: int) -> None:
        """Scale stats by floor depth (bonus every 2 floors)."""
        bonus = (floor - 1) // 2
        self.max_hp += bonus * 3
        self.hp      = self.max_hp
        self.atk    += bonus

    def special_ability(self, target: Entity) -> Optional[str]:
        """Override in subclasses. Return a string tag or None."""
        return None


# ---------------------------------------------------------------------------
# Concrete enemy types
# ---------------------------------------------------------------------------

@dataclass
class Skeleton(Enemy):
    pass   # no special ability


@dataclass
class Ghoul(Enemy):
    def special_ability(self, target: Entity) -> Optional[str]:
        target.add_status(StatusEffect("bleed", duration=8, magnitude=1))
        return "BLEED"


@dataclass
class Wraith(Enemy):
    def special_ability(self, target: Entity) -> Optional[str]:
        return "PHASE"   # combat.py handles ignoring DEF


@dataclass
class StoneGolem(Enemy):
    def special_ability(self, target: Entity) -> Optional[str]:
        target.add_status(StatusEffect("slow", duration=1, magnitude=0))
        return "STUN"    # combat.py also doubles damage on STUN


@dataclass
class Lich(Enemy):
    def special_ability(self, target: Entity) -> Optional[str]:
        target.add_status(StatusEffect("cursed", duration=4, magnitude=0))
        return "CURSED"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, dict] = {
    "skeleton": dict(
        cls=Skeleton, name="Skeleton", symbol="S",
        max_hp=8,  atk=4,  defense=1,
        xp_reward=10, gold_reward=2,  detection_range=5,
        color=(200, 200, 200),
    ),
    "ghoul": dict(
        cls=Ghoul, name="Ghoul", symbol="G",
        max_hp=14, atk=6,  defense=2,
        xp_reward=20, gold_reward=5,  detection_range=6,
        color=(80, 180, 80),
    ),
    "wraith": dict(
        cls=Wraith, name="Wraith", symbol="W",
        max_hp=10, atk=8,  defense=0,
        xp_reward=25, gold_reward=4,  detection_range=8,
        color=(160, 80, 220),
    ),
    "stone_golem": dict(
        cls=StoneGolem, name="Stone Golem", symbol="O",
        max_hp=30, atk=7,  defense=6,
        xp_reward=50, gold_reward=12, detection_range=4,
        color=(140, 120, 100),
    ),
    "lich": dict(
        cls=Lich, name="Lich", symbol="L",
        max_hp=20, atk=10, defense=3,
        xp_reward=60, gold_reward=15, detection_range=7,
        color=(200, 60, 200),
    ),
}


def create_enemy(enemy_type: str, x: int, y: int, floor: int) -> Enemy:
    """Instantiate and scale an enemy for the given floor."""
    t   = dict(_TEMPLATES[enemy_type])   # shallow copy
    cls = t.pop("cls")
    enemy = cls(x=x, y=y, hp=t["max_hp"], **t)
    enemy.scale_to_floor(floor)
    return enemy


def eligible_enemy_types(floor: int) -> list[str]:
    """Return enemy type keys that can spawn on the given floor."""
    pool = ["skeleton"]
    if floor >= 2:
        pool.append("ghoul")
    if floor >= 3:
        pool.append("wraith")
    if floor >= 4:
        pool.append("stone_golem")
    if floor >= 7:
        pool.append("lich")
    return pool
