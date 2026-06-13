"""Shrine blessing selection UI — shown when the player steps on a shrine tile."""
from __future__ import annotations

import random
from typing import Optional

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    MENU_TEXT, MENU_HIGHLIGHT, GOLD, WHITE, SHRINE_COLOR, HUD_BORDER,
)

# Panel geometry
_PW = 520
_PH = 340
_PX = (SCREEN_WIDTH - _PW) // 2
_PY = (SCREEN_HEIGHT - _PH) // 2
_BOON_H = 52

# Full boon table
_ALL_BOONS: list[dict] = [
    {
        "key":   "heal",
        "label": "Divine Mend",
        "desc":  "Fully restore HP to maximum",
        "color": (160, 220, 160),
    },
    {
        "key":   "atk",
        "label": "Warbrand",
        "desc":  "Permanently gain +3 ATK",
        "color": (220, 140, 140),
    },
    {
        "key":   "def",
        "label": "Stone Skin",
        "desc":  "Permanently gain +2 DEF",
        "color": (140, 160, 220),
    },
    {
        "key":   "curse",
        "label": "Cleansing Light",
        "desc":  "Remove all negative status effects",
        "color": (200, 200, 140),
    },
    {
        "key":   "gold",
        "label": "Gold Bless",
        "desc":  "Gain 25 GOLD",
        "color": GOLD,
    },
    {
        "key":   "xp",
        "label": "XP Surge",
        "desc":  "Gain 75 XP instantly",
        "color": (120, 180, 220),
    },
    {
        "key":   "echo",
        "label": "Shard Echo",
        "desc":  "Survive one death (restored to 1 HP)",
        "color": (80, 220, 220),
    },
]


class ShrineUI:
    """Presents three random shrine boons for the player to choose."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen     = screen
        self.font_title = pygame.font.SysFont("monospace", 24, bold=True)
        self.font       = pygame.font.SysFont("monospace", 18)
        self.font_small = pygame.font.SysFont("monospace", 14)
        self.selected   = 0
        self.boons:  list[dict] = []

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def roll(self, floor: int, rng: random.Random) -> None:
        """Pick 3 random boons (Shard Echo only on floor 6+)."""
        pool = [b for b in _ALL_BOONS if b["key"] != "echo" or floor >= 6]
        self.boons    = rng.sample(pool, min(3, len(pool)))
        self.selected = 0

    def update(
        self, events: list[pygame.event.Event]
    ) -> Optional[tuple]:
        """
        Return values:
          None              — still deciding
          ("close",)        — player pressed ESC (no boon taken)
          ("boon", key)     — player confirmed a boon choice
        """
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            k = event.key
            if k == pygame.K_ESCAPE:
                return ("close",)
            elif k in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.boons)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.boons)
            elif k in (pygame.K_RETURN, pygame.K_e):
                return ("boon", self.boons[self.selected]["key"])
        return None

    def render(self) -> None:
        # Dim overlay
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        self.screen.blit(dim, (0, 0))

        # Panel
        pygame.draw.rect(self.screen, (12, 8, 22), (_PX, _PY, _PW, _PH), border_radius=8)
        pygame.draw.rect(self.screen, SHRINE_COLOR, (_PX, _PY, _PW, _PH), 2, border_radius=8)

        cx = _PX + _PW // 2
        y  = _PY + 16

        # Title
        title = self.font_title.render("✦  ANCIENT SHRINE  ✦", True, SHRINE_COLOR)
        self.screen.blit(title, title.get_rect(centerx=cx, top=y))
        y += 42

        # Subtitle
        sub = self.font_small.render(
            "Three boons are offered. Choose one blessing.", True, (145, 135, 165)
        )
        self.screen.blit(sub, sub.get_rect(centerx=cx, top=y))
        y += 22
        pygame.draw.line(
            self.screen, (70, 50, 90),
            (_PX + 20, y), (_PX + _PW - 20, y), 1,
        )
        y += 10

        # Boon rows
        for i, boon in enumerate(self.boons):
            sel = i == self.selected
            row_bg = (40, 28, 60) if sel else (20, 14, 35)
            border  = boon["color"] if sel else (50, 40, 70)

            pygame.draw.rect(
                self.screen, row_bg,
                (_PX + 16, y, _PW - 32, _BOON_H - 4), border_radius=5,
            )
            pygame.draw.rect(
                self.screen, border,
                (_PX + 16, y, _PW - 32, _BOON_H - 4), 1, border_radius=5,
            )

            label_color = WHITE if sel else MENU_TEXT
            self.screen.blit(
                self.font.render(boon["label"], True, label_color),
                (_PX + 28, y + 8),
            )
            desc_color = GOLD if sel else (120, 115, 140)
            self.screen.blit(
                self.font_small.render(boon["desc"], True, desc_color),
                (_PX + 28, y + 30),
            )
            y += _BOON_H

        # Footer
        y += 6
        pygame.draw.line(
            self.screen, (70, 50, 90),
            (_PX + 20, y), (_PX + _PW - 20, y), 1,
        )
        hint = self.font_small.render(
            "↑↓ Choose  |  ENTER / E Accept  |  ESC Leave shrine",
            True, (75, 70, 95),
        )
        self.screen.blit(hint, hint.get_rect(centerx=cx, top=y + 8))
