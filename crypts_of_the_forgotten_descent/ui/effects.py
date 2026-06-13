"""Floating damage numbers and other one-shot visual effects."""
from __future__ import annotations
import random
from dataclasses import dataclass, field

import pygame


@dataclass
class FloatingNumber:
    text:  str
    x:     float
    y:     float
    color: tuple
    life:  int = 40
    max_life: int = 40
    vy: float = -0.9

    def update(self) -> bool:
        self.y    += self.vy
        self.vy   *= 0.92
        self.life -= 1
        return self.life > 0

    def draw(self, surf: pygame.Surface, font: pygame.font.Font) -> None:
        alpha  = int(255 * self.life / self.max_life)
        label  = font.render(self.text, True, self.color)
        tmp    = pygame.Surface(label.get_size(), pygame.SRCALPHA)
        tmp.blit(label, (0, 0))
        tmp.set_alpha(alpha)
        surf.blit(tmp, (int(self.x) - label.get_width() // 2, int(self.y)))


class FloatingNumberSystem:
    def __init__(self) -> None:
        self._numbers: list[FloatingNumber] = []
        self._font = pygame.font.SysFont("monospace", 14, bold=True)

    def add(self, text: str, px: float, py: float, color: tuple) -> None:
        self._numbers.append(FloatingNumber(
            text=text,
            x=px + random.uniform(-6, 6),
            y=py - 4,
            color=color,
        ))

    def damage_dealt(self, amount: int, px: float, py: float, crit: bool = False) -> None:
        text  = f"-{amount}{'!' if crit else ''}"
        color = (255, 80, 80) if not crit else (255, 220, 60)
        self.add(text, px, py, color)

    def damage_taken(self, amount: int, px: float, py: float) -> None:
        self.add(f"-{amount}", px, py, (255, 255, 255))

    def heal(self, amount: int, px: float, py: float) -> None:
        self.add(f"+{amount}", px, py, (80, 220, 100))

    def xp(self, amount: int, px: float, py: float) -> None:
        self.add(f"+{amount}XP", px, py, (80, 180, 255))

    def update(self) -> None:
        self._numbers = [n for n in self._numbers if n.update()]

    def draw(self, surf: pygame.Surface) -> None:
        for n in self._numbers:
            n.draw(surf, self._font)
