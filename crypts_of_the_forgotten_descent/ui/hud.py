"""HUD panel — reskinned dark-fantasy style."""
from __future__ import annotations
import math
from collections import deque

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_WIDTH,
    GOLD, WHITE, MENU_TEXT,
    HEALTH_BAR_FG, HEALTH_BAR_BG, XP_BAR_FG, XP_BAR_BG,
)

HUD_X       = SCREEN_WIDTH - HUD_WIDTH
LOG_LINES   = 10
LOG_PADDING = 8
_BORDER     = (70, 50, 100)
_PANEL_BG   = (12, 9, 20)
_RULE       = (45, 35, 65)
_DIM        = (80, 70, 100)

# Color coding for the log
_LOG_COLORS = {
    "dmg_dealt":  (220, 100, 100),
    "dmg_taken":  (255, 255, 255),
    "heal":       (80,  220, 100),
    "pickup":     (220, 200,  60),
    "level_up":   (200, 165,  30),
    "status":     (160, 80,  220),
    "info":       (160, 145, 190),
    "default":    (180, 170, 200),
}


class HUD:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen       = screen
        self.font         = pygame.font.SysFont("monospace", 15)
        self.font_small   = pygame.font.SysFont("monospace", 12)
        self.font_large   = pygame.font.SysFont("monospace", 19, bold=True)
        self.font_title   = pygame.font.SysFont("monospace", 22, bold=True)
        self.message_log: deque[tuple[str, tuple]] = deque(maxlen=LOG_LINES)
        self._tick        = 0

    # ------------------------------------------------------------------
    def add_message(self, text: str, color: tuple = MENU_TEXT) -> None:
        self.message_log.append((text, color))

    def render(self, player, floor: int, shards: int = 0) -> None:
        self._tick += 1
        self._draw_panel()
        y = 10
        y = self._draw_floor_title(y, floor)
        y = self._draw_health(y, player)
        y = self._draw_xp(y, player)
        y = self._draw_rule(y)
        y = self._draw_stats(y, player, shards)
        y = self._draw_rule(y)
        y = self._draw_equipment(y, player)
        y = self._draw_statuses(y, player)
        self._draw_controls()
        self._draw_log()

    # ------------------------------------------------------------------
    # Panel background
    # ------------------------------------------------------------------

    def _draw_panel(self) -> None:
        # Stone-texture gradient — several dark rects layered
        pygame.draw.rect(self.screen, _PANEL_BG, (HUD_X, 0, HUD_WIDTH, SCREEN_HEIGHT))
        # Left edge dark bar
        pygame.draw.rect(self.screen, (8, 6, 14), (HUD_X, 0, 3, SCREEN_HEIGHT))
        # Ornate border line
        pygame.draw.line(self.screen, _BORDER, (HUD_X + 3, 0), (HUD_X + 3, SCREEN_HEIGHT), 2)
        # Subtle vertical highlight
        pygame.draw.line(self.screen, (30, 22, 45), (HUD_X + 5, 0), (HUD_X + 5, SCREEN_HEIGHT), 1)

    def _draw_rule(self, y: int) -> int:
        y += 4
        pygame.draw.line(self.screen, _RULE, (HUD_X + 10, y), (SCREEN_WIDTH - 10, y), 1)
        return y + 6

    # ------------------------------------------------------------------
    # Floor title
    # ------------------------------------------------------------------

    def _draw_floor_title(self, y: int, floor: int) -> int:
        # Background accent
        pygame.draw.rect(self.screen, (25, 18, 40),
                         (HUD_X + 6, y, HUD_WIDTH - 12, 28), border_radius=4)
        pygame.draw.rect(self.screen, _BORDER,
                         (HUD_X + 6, y, HUD_WIDTH - 12, 28), 1, border_radius=4)
        label = self.font_title.render(f"Floor  {floor:02d}", True, GOLD)
        self.screen.blit(label, label.get_rect(centerx=HUD_X + HUD_WIDTH // 2, top=y + 4))
        return y + 36

    # ------------------------------------------------------------------
    # HP bar
    # ------------------------------------------------------------------

    def _draw_health(self, y: int, player) -> int:
        ratio = player.hp / max(player.max_hp, 1)
        label = self.font.render(f"HP  {player.hp:>3}/{player.max_hp}", True, (220, 160, 160))
        self.screen.blit(label, (HUD_X + 10, y))
        y += 18
        self._draw_gradient_bar(y, player.hp, player.max_hp,
                                (180, 40, 40), (220, 70, 40), HEALTH_BAR_BG)
        # Pulse border when low
        if ratio < 0.25:
            pulse = int(100 + 80 * abs(math.sin(self._tick * 0.12)))
            pygame.draw.rect(self.screen, (220, pulse, 0),
                             (HUD_X + 10, y, HUD_WIDTH - 20, 10), 1, border_radius=3)
        return y + 18

    def _draw_xp(self, y: int, player) -> int:
        self.screen.blit(
            self.font.render(f"XP  {player.xp:>3}/{player.xp_to_next_level}", True, (100, 160, 220)),
            (HUD_X + 10, y),
        )
        y += 18
        self._draw_gradient_bar(y, player.xp, player.xp_to_next_level,
                                (60, 140, 210), (80, 200, 240), XP_BAR_BG)
        return y + 18

    def _draw_gradient_bar(self, y: int, current: int, maximum: int,
                           fg_left: tuple, fg_right: tuple, bg: tuple) -> None:
        bw     = HUD_WIDTH - 20
        filled = max(0, int(bw * min(current, maximum) / max(maximum, 1)))
        bx     = HUD_X + 10
        pygame.draw.rect(self.screen, bg, (bx, y, bw, 10), border_radius=3)
        if filled > 0:
            # Horizontal gradient approximation (5 segments)
            segs = max(1, filled // 5)
            for i in range(segs):
                t  = i / max(segs - 1, 1)
                r  = int(fg_left[0] + (fg_right[0] - fg_left[0]) * t)
                g  = int(fg_left[1] + (fg_right[1] - fg_left[1]) * t)
                b  = int(fg_left[2] + (fg_right[2] - fg_left[2]) * t)
                sw = filled // segs + 1
                pygame.draw.rect(self.screen, (r, g, b),
                                 (bx + i * sw, y, sw, 10), border_radius=3)
        # Shine stripe
        pygame.draw.rect(self.screen, (255, 255, 255),
                         (bx + 2, y + 1, max(0, filled - 4), 2), border_radius=1)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def _draw_stats(self, y: int, player, shards: int = 0) -> int:
        shard_color = (80, 220, 220) if shards > 0 else (50, 80, 100)
        rows = [
            (f"LVL  {player.level}",            WHITE),
            (f"ATK  {player.effective_atk}",    (220, 140, 140)),
            (f"DEF  {player.effective_defense}", (140, 170, 230)),
            (f"GOLD {player.gold}",              GOLD),
            (f"SHD  {shards}/7",                shard_color),
        ]
        for text, color in rows:
            self.screen.blit(self.font.render(text, True, color), (HUD_X + 14, y))
            y += 20
        return y

    # ------------------------------------------------------------------
    # Equipment
    # ------------------------------------------------------------------

    def _draw_equipment(self, y: int, player) -> int:
        self.screen.blit(
            self.font_small.render("Equipment", True, _DIM),
            (HUD_X + 14, y),
        )
        y += 16

        wpn = player.equipped_weapon
        arm = player.equipped_armor

        # Weapon box
        self._draw_gear_slot(HUD_X + 10, y, "WPN",
                             wpn.name if wpn else "—",
                             wpn.color if wpn else (60, 55, 80))
        y += 26

        # Armor box
        self._draw_gear_slot(HUD_X + 10, y, "ARM",
                             arm.name if arm else "—",
                             arm.color if arm else (60, 55, 80))
        return y + 30

    def _draw_gear_slot(self, x: int, y: int, tag: str, name: str, color: tuple) -> None:
        w = HUD_WIDTH - 20
        pygame.draw.rect(self.screen, (20, 15, 32), (x, y, w, 22), border_radius=3)
        pygame.draw.rect(self.screen, (*color, 180), (x, y, w, 22), 1, border_radius=3)
        tag_s  = self.font_small.render(f"[{tag}]", True, color)
        name_s = self.font_small.render(name, True, (190, 180, 210))
        self.screen.blit(tag_s,  (x + 4,  y + 5))
        self.screen.blit(name_s, (x + 4 + tag_s.get_width() + 4, y + 5))

    # ------------------------------------------------------------------
    # Status effects
    # ------------------------------------------------------------------

    def _draw_statuses(self, y: int, player) -> int:
        if not player.status_effects:
            return y
        y = self._draw_rule(y)
        self.screen.blit(self.font_small.render("Status", True, _DIM), (HUD_X + 14, y))
        y += 16
        _colors = {
            "bleed":  (220,  70,  70),
            "poison": ( 60, 210,  80),
            "cursed": (180,  60, 220),
            "slow":   (100, 160, 255),
        }
        for s in player.status_effects:
            c   = _colors.get(s.name, (200, 160, 70))
            txt = f"* {s.name.upper()}  {s.duration}t"
            self.screen.blit(self.font_small.render(txt, True, c), (HUD_X + 14, y))
            y += 15
        return y

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def _draw_controls(self) -> None:
        controls = [
            ("WASD/↑↓←→", "Move"),
            ("SPACE",      "Wait (+1 HP)"),
            ("I",          "Inventory"),
            ("M",          "Minimap"),
            ("ESC",        "Menu"),
        ]
        n  = len(controls)
        cy = SCREEN_HEIGHT - LOG_LINES * 14 - LOG_PADDING - n * 13 - 16
        pygame.draw.line(self.screen, _RULE, (HUD_X + 8, cy - 4), (SCREEN_WIDTH - 8, cy - 4), 1)
        for key, desc in controls:
            k = self.font_small.render(f"{key:<13}", True, (130, 120, 160))
            d = self.font_small.render(desc, True, (80, 72, 100))
            self.screen.blit(k, (HUD_X + 8, cy))
            self.screen.blit(d, (HUD_X + 8 + k.get_width(), cy))
            cy += 13

    # ------------------------------------------------------------------
    # Message log
    # ------------------------------------------------------------------

    def _draw_log(self) -> None:
        n     = len(self.message_log)
        log_h = n * 14 + LOG_PADDING
        y     = SCREEN_HEIGHT - log_h

        # Semi-transparent log background
        bg = pygame.Surface((HUD_WIDTH, log_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 100))
        self.screen.blit(bg, (HUD_X, y))

        pygame.draw.line(self.screen, _RULE, (HUD_X + 8, y - 4), (SCREEN_WIDTH - 8, y - 4), 1)
        for i, (text, color) in enumerate(self.message_log):
            # Older messages fade out
            fade = max(80, int(255 * (i + 1) / max(n, 1)))
            surf = self.font_small.render(text, True, color)
            surf.set_alpha(fade)
            self.screen.blit(surf, (HUD_X + 8, y))
            y += 14
