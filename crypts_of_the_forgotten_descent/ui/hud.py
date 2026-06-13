"""HUD panel — HP/XP bars, stats, equipment, status effects, message log."""
from __future__ import annotations

from collections import deque

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_WIDTH,
    HUD_BG, HUD_BORDER, MENU_TEXT, GOLD, WHITE,
    HEALTH_BAR_FG, HEALTH_BAR_BG, XP_BAR_FG, XP_BAR_BG,
)

HUD_X       = SCREEN_WIDTH - HUD_WIDTH
LOG_LINES   = 10
LOG_PADDING = 12


class HUD:
    """Right-side info panel rendered during gameplay."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen      = screen
        self.font        = pygame.font.SysFont("monospace", 16)
        self.font_small  = pygame.font.SysFont("monospace", 13)
        self.font_large  = pygame.font.SysFont("monospace", 20, bold=True)
        self.message_log: deque[tuple[str, tuple]] = deque(maxlen=LOG_LINES)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def add_message(self, text: str, color: tuple = MENU_TEXT) -> None:
        self.message_log.append((text, color))

    def render(self, player, floor: int, shards: int = 0) -> None:
        self._draw_panel()
        y = 12
        y = self._draw_floor_title(y, floor)
        y = self._draw_health(y, player)
        y = self._draw_xp(y, player)
        y = self._draw_stats(y, player, shards)
        y = self._draw_equipment(y, player)
        y = self._draw_statuses(y, player)
        self._draw_controls()
        self._draw_log()

    # ------------------------------------------------------------------
    # Private — drawing
    # ------------------------------------------------------------------

    def _draw_panel(self) -> None:
        pygame.draw.rect(self.screen, HUD_BG, (HUD_X, 0, HUD_WIDTH, SCREEN_HEIGHT))
        pygame.draw.line(self.screen, HUD_BORDER, (HUD_X, 0), (HUD_X, SCREEN_HEIGHT), 2)

    def _draw_floor_title(self, y: int, floor: int) -> int:
        surf = self.font_large.render(f"Floor  {floor:02d}", True, GOLD)
        self.screen.blit(surf, (HUD_X + 10, y))
        return y + 30

    def _draw_health(self, y: int, player) -> int:
        label = self.font.render(
            f"HP   {player.hp:>3} / {player.max_hp}", True, MENU_TEXT
        )
        self.screen.blit(label, (HUD_X + 10, y))
        y += 20
        self._draw_bar(y, player.hp, player.max_hp, HEALTH_BAR_FG, HEALTH_BAR_BG)
        return y + 16

    def _draw_xp(self, y: int, player) -> int:
        label = self.font.render(
            f"XP   {player.xp:>3} / {player.xp_to_next_level}", True, MENU_TEXT
        )
        self.screen.blit(label, (HUD_X + 10, y))
        y += 20
        self._draw_bar(y, player.xp, player.xp_to_next_level, XP_BAR_FG, XP_BAR_BG)
        return y + 16

    def _draw_bar(
        self, y: int, current: int, maximum: int, fg: tuple, bg: tuple
    ) -> None:
        bar_w  = HUD_WIDTH - 20
        filled = int(bar_w * min(current, maximum) / max(maximum, 1))
        pygame.draw.rect(self.screen, bg, (HUD_X + 10, y, bar_w, 10), border_radius=3)
        if filled > 0:
            pygame.draw.rect(self.screen, fg, (HUD_X + 10, y, filled, 10), border_radius=3)

    def _draw_stats(self, y: int, player, shards: int = 0) -> int:
        y += 10
        shard_color = (80, 220, 220) if shards > 0 else (60, 100, 120)
        rows = [
            (f"LVL  {player.level}",                WHITE),
            (f"ATK  {player.effective_atk}",        (200, 140, 140)),
            (f"DEF  {player.effective_defense}",    (140, 160, 220)),
            (f"GOLD {player.gold}",                 GOLD),
            (f"SHD  {shards}/7",                   shard_color),
        ]
        for text, color in rows:
            self.screen.blit(self.font.render(text, True, color), (HUD_X + 10, y))
            y += 22
        return y

    def _draw_equipment(self, y: int, player) -> int:
        y += 8
        self.screen.blit(
            self.font_small.render("─── Equipment ───", True, HUD_BORDER),
            (HUD_X + 10, y),
        )
        y += 18
        wpn = player.equipped_weapon
        arm = player.equipped_armor
        self.screen.blit(
            self.font_small.render(
                f"Wpn: {wpn.name if wpn else '—'}", True, (180, 160, 200)
            ),
            (HUD_X + 10, y),
        )
        y += 18
        self.screen.blit(
            self.font_small.render(
                f"Arm: {arm.name if arm else '—'}", True, (160, 185, 220)
            ),
            (HUD_X + 10, y),
        )
        return y + 22

    def _draw_statuses(self, y: int, player) -> int:
        if not player.status_effects:
            return y
        y += 6
        self.screen.blit(
            self.font_small.render("─── Status ───", True, HUD_BORDER),
            (HUD_X + 10, y),
        )
        y += 18
        for s in player.status_effects:
            color = (220, 80, 80) if s.name in ("bleed", "poison") else (200, 160, 70)
            self.screen.blit(
                self.font_small.render(
                    f"{s.name.upper()}  ({s.duration}t)", True, color
                ),
                (HUD_X + 10, y),
            )
            y += 16
        return y

    def _draw_controls(self) -> None:
        """Fixed controls reminder above the message log."""
        controls = [
            ("WASD / ↑↓←→", "Move"),
            ("SPACE",        "Wait (+1 HP)"),
            ("I",            "Inventory"),
            ("M",            "Minimap toggle"),
            ("ESC",          "Menu"),
        ]
        # Pin to a fixed position above where the log might start
        cy = SCREEN_HEIGHT - LOG_LINES * 15 - LOG_PADDING - len(controls) * 14 - 20
        pygame.draw.line(
            self.screen, HUD_BORDER,
            (HUD_X, cy - 4), (SCREEN_WIDTH, cy - 4), 1
        )
        key_color  = (160, 150, 180)
        desc_color = (100, 95, 120)
        for key, desc in controls:
            k_surf = self.font_small.render(f"{key:<14}", True, key_color)
            d_surf = self.font_small.render(desc, True, desc_color)
            self.screen.blit(k_surf, (HUD_X + 8, cy))
            self.screen.blit(d_surf, (HUD_X + 8 + k_surf.get_width(), cy))
            cy += 14

    def _draw_log(self) -> None:
        """Render the message log anchored to the bottom of the HUD panel."""
        log_h  = len(self.message_log) * 15 + LOG_PADDING
        y      = SCREEN_HEIGHT - log_h
        pygame.draw.line(
            self.screen, HUD_BORDER, (HUD_X, y - 4), (SCREEN_WIDTH, y - 4), 1
        )
        for text, color in self.message_log:
            surf = self.font_small.render(text, True, color)
            self.screen.blit(surf, (HUD_X + 8, y))
            y += 15
