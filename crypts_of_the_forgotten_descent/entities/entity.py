"""Base entity dataclass shared by Player, Enemy, and Boss."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StatusEffect:
    name:      str
    duration:  int    # turns remaining
    magnitude: int = 0


@dataclass
class Entity:
    """Abstract base for all game entities."""
    name:    str
    symbol:  str
    x:       int
    y:       int
    max_hp:  int
    hp:      int
    atk:     int
    defense: int
    color:   tuple[int, int, int]
    alive:   bool = True
    status_effects: list[StatusEffect] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    # ------------------------------------------------------------------
    # HP
    # ------------------------------------------------------------------

    def take_damage(self, amount: int) -> int:
        """Apply damage (minimum 1). Return actual HP lost."""
        actual = max(1, amount)
        self.hp = max(0, self.hp - actual)
        if self.hp == 0:
            self.alive = False
        return actual

    def heal(self, amount: int) -> int:
        """Restore HP up to max_hp. Return amount actually healed."""
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    # ------------------------------------------------------------------
    # Status effects
    # ------------------------------------------------------------------

    def has_status(self, name: str) -> bool:
        return any(s.name == name for s in self.status_effects)

    def add_status(self, effect: StatusEffect) -> None:
        """Add or refresh a status effect by name."""
        self.remove_status(effect.name)
        self.status_effects.append(effect)

    def remove_status(self, name: str) -> None:
        self.status_effects = [s for s in self.status_effects if s.name != name]

    def tick_statuses(self) -> list[str]:
        """Decrement all durations; return names of effects that expired this tick."""
        expired: list[str] = []
        remaining: list[StatusEffect] = []
        for s in self.status_effects:
            s.duration -= 1
            if s.duration <= 0:
                expired.append(s.name)
            else:
                remaining.append(s)
        self.status_effects = remaining
        return expired
