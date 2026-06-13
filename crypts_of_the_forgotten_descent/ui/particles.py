"""Particle system — fire, blood, sparkle, dust, ghost trail."""
from __future__ import annotations
import random
import math
from dataclasses import dataclass, field
from typing import Callable

import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: tuple
    size: float
    alpha_start: int = 200
    gravity: float   = 0.0
    shrink: float    = 0.0   # size reduction per tick

    @property
    def progress(self) -> float:
        return 1.0 - self.life / self.max_life

    @property
    def alpha(self) -> int:
        return max(0, int(self.alpha_start * (1.0 - self.progress)))

    def update(self) -> bool:
        """Return False when dead."""
        self.life -= 1
        self.x   += self.vx
        self.y   += self.vy
        self.vy  += self.gravity
        self.size = max(0.5, self.size - self.shrink)
        return self.life > 0

    def draw(self, surf: pygame.Surface) -> None:
        if self.size < 1:
            return
        s = int(self.size)
        tmp = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        pygame.draw.circle(tmp, (*self.color, self.alpha), (s, s), s)
        surf.blit(tmp, (int(self.x) - s, int(self.y) - s))


class ParticleSystem:
    def __init__(self) -> None:
        self._particles: list[Particle] = []

    def update(self) -> None:
        self._particles = [p for p in self._particles if p.update()]

    def draw(self, surf: pygame.Surface) -> None:
        for p in self._particles:
            p.draw(surf)

    def emit(self, p: Particle) -> None:
        self._particles.append(p)

    # ------------------------------------------------------------------
    # Named emitters (pixel coords on the game surface)
    # ------------------------------------------------------------------

    def blood(self, px: float, py: float, count: int = 6) -> None:
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.8, 2.5)
            self.emit(Particle(
                x=px, y=py,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1.0,
                life=random.randint(14, 24),
                max_life=24,
                color=(random.randint(160, 210), 20, 20),
                size=random.uniform(2, 4),
                gravity=0.15,
                shrink=0.08,
                alpha_start=220,
            ))

    def sparkle(self, px: float, py: float, color=(120, 220, 255), count: int = 8) -> None:
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 2.0)
            self.emit(Particle(
                x=px, y=py,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(18, 30),
                max_life=30,
                color=color,
                size=random.uniform(1.5, 3.5),
                gravity=-0.02,
                shrink=0.07,
                alpha_start=240,
            ))

    def dust(self, px: float, py: float, count: int = 4) -> None:
        for _ in range(count):
            self.emit(Particle(
                x=px + random.uniform(-6, 6),
                y=py + random.uniform(-4, 4),
                vx=random.uniform(-0.4, 0.4),
                vy=random.uniform(-0.8, -0.2),
                life=random.randint(12, 20),
                max_life=20,
                color=(110, 100, 130),
                size=random.uniform(1.5, 3.0),
                shrink=0.1,
                alpha_start=120,
            ))

    def fire(self, px: float, py: float, count: int = 3) -> None:
        for _ in range(count):
            r = random.randint(210, 255)
            g = random.randint(80, 160)
            self.emit(Particle(
                x=px + random.uniform(-3, 3),
                y=py,
                vx=random.uniform(-0.3, 0.3),
                vy=random.uniform(-1.5, -0.6),
                life=random.randint(10, 18),
                max_life=18,
                color=(r, g, 20),
                size=random.uniform(2.0, 4.0),
                shrink=0.15,
                alpha_start=200,
            ))

    def ghost(self, px: float, py: float, color=(160, 80, 220), count: int = 2) -> None:
        for _ in range(count):
            self.emit(Particle(
                x=px + random.uniform(-4, 4),
                y=py + random.uniform(-4, 4),
                vx=random.uniform(-0.3, 0.3),
                vy=random.uniform(-0.5, 0.1),
                life=random.randint(16, 28),
                max_life=28,
                color=color,
                size=random.uniform(3.0, 6.0),
                shrink=0.12,
                alpha_start=140,
            ))

    def level_up(self, px: float, py: float) -> None:
        self.sparkle(px, py, color=(220, 200, 60), count=16)
        for _ in range(8):
            self.emit(Particle(
                x=px, y=py,
                vx=random.uniform(-1.0, 1.0),
                vy=random.uniform(-3.0, -1.0),
                life=40, max_life=40,
                color=(255, 240, 80),
                size=4.0, shrink=0.05,
                alpha_start=255,
            ))
