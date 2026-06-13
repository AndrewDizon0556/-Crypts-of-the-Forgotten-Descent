"""The Hollow Warden — 3-phase final boss for Floor 10."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from config import BOSS_COLOR
from entities.entity import Entity, StatusEffect
from entities.enemy import Enemy, AIState


class BossPhase(Enum):
    PHASE_1 = auto()   # HP 150-100: standard + skeleton summons every 5 turns
    PHASE_2 = auto()   # HP  99-50 : double speed, bleed on hit, ghoul summons
    PHASE_3 = auto()   # HP  49-1  : rage (ATK 25), AoE slam, wraith summons


@dataclass
class HollowWarden(Enemy):
    """Final boss of Crypts of the Forgotten Descent."""
    phase:          BossPhase = field(default=BossPhase.PHASE_1)
    summon_timer:   int       = 0   # counts up; summons when it hits the interval

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    def update_phase(self) -> bool:
        """Recalculate phase from current HP. Return True if phase changed."""
        old = self.phase
        if self.hp >= 100:
            self.phase = BossPhase.PHASE_1
        elif self.hp >= 50:
            self.phase = BossPhase.PHASE_2
        else:
            self.phase = BossPhase.PHASE_3
        return self.phase != old

    # ------------------------------------------------------------------
    # Phase-dependent stats
    # ------------------------------------------------------------------

    @property
    def move_speed(self) -> int:
        """Tiles moved per turn (doubles in Phase 2)."""
        return 2 if self.phase == BossPhase.PHASE_2 else 1

    @property
    def effective_atk(self) -> int:
        return 25 if self.phase == BossPhase.PHASE_3 else self.atk

    @property
    def effective_def(self) -> int:
        return 3 if self.phase == BossPhase.PHASE_3 else self.defense

    @property
    def summon_type(self) -> str:
        match self.phase:
            case BossPhase.PHASE_1: return "skeleton"
            case BossPhase.PHASE_2: return "ghoul"
            case BossPhase.PHASE_3: return "wraith"

    @property
    def summon_interval(self) -> int:
        match self.phase:
            case BossPhase.PHASE_1: return 5
            case BossPhase.PHASE_2: return 4
            case BossPhase.PHASE_3: return 5

    # ------------------------------------------------------------------
    # Special ability override
    # ------------------------------------------------------------------

    def special_ability(self, target: Entity) -> str | None:
        if self.phase == BossPhase.PHASE_3 and self.attack_count % 3 == 0:
            return "AOE_SLAM"   # combat.py applies 15 dmg to all adjacent tiles
        if self.phase == BossPhase.PHASE_2:
            target.add_status(StatusEffect("bleed", duration=8, magnitude=1))
            return "BLEED"
        return None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_hollow_warden(x: int, y: int) -> HollowWarden:
    return HollowWarden(
        name="Hollow Warden",
        symbol="B",
        x=x, y=y,
        max_hp=150, hp=150,
        atk=18,
        defense=8,
        color=BOSS_COLOR,
        xp_reward=500,
        gold_reward=100,
        detection_range=20,
    )
