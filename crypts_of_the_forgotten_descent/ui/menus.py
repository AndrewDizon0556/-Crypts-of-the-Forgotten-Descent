"""Main menu, character selection, death screen, and victory screen."""
from __future__ import annotations

from typing import Optional

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    BG_COLOR, MENU_TEXT, MENU_TITLE, MENU_HIGHLIGHT,
    WHITE, GOLD, HUD_BORDER,
)


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class _MenuBase:
    """Common drawing helpers used across all menu screens."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen      = screen
        self.font_title  = pygame.font.SysFont("monospace", 52, bold=True)
        self.font_large  = pygame.font.SysFont("monospace", 34, bold=True)
        self.font_medium = pygame.font.SysFont("monospace", 24)
        self.font_small  = pygame.font.SysFont("monospace", 18)
        self.font_tiny   = pygame.font.SysFont("monospace", 14)

    # -- helpers --

    def _blit_centered(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple,
        y: int,
    ) -> None:
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(centerx=SCREEN_WIDTH // 2, top=y))

    def _blit_wrapped_centered(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple,
        cx: int,
        y: int,
        max_width: int,
    ) -> int:
        """Word-wrap `text` and blit each line centered at `cx`. Returns y after last line."""
        words   = text.split()
        lines: list[str] = []
        current: list[str] = []
        for word in words:
            test = " ".join(current + [word])
            if font.size(test)[0] <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))

        lh = font.get_linesize()
        for line in lines:
            surf = font.render(line, True, color)
            self.screen.blit(surf, surf.get_rect(centerx=cx, top=y))
            y += lh
        return y

    def _draw_divider(self, y: int, color: tuple = (60, 50, 80)) -> None:
        pygame.draw.line(
            self.screen, color,
            (SCREEN_WIDTH // 4,     y),
            (SCREEN_WIDTH * 3 // 4, y),
            1,
        )


# ---------------------------------------------------------------------------
# Main Menu
# ---------------------------------------------------------------------------

class MainMenu(_MenuBase):
    """Four-option main menu: New Game / Continue / Leaderboard / Quit."""

    _OPTIONS     = ["New Game", "Continue", "Leaderboard", "Quit"]
    _OPTION_KEYS = ["new_game", "continue", "leaderboard", "quit"]

    def __init__(self, screen: pygame.Surface) -> None:
        super().__init__(screen)
        self.selected       = 0
        self._no_save_flash = 0   # frames to show "No save found" hint

    def update(self, events: list[pygame.event.Event]) -> Optional[str]:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self._OPTIONS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self._OPTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._OPTION_KEYS[self.selected]
        return None

    def render(self) -> None:
        self._draw_title()
        self._draw_options()
        self._draw_footer()

    def _draw_title(self) -> None:
        self._blit_centered("CRYPTS  OF  THE",     self.font_title, MENU_TITLE, 90)
        self._blit_centered("FORGOTTEN  DESCENT",  self.font_title, GOLD, 150)
        self._draw_divider(230)
        self._blit_centered(
            "— a roguelike dungeon crawler —",
            self.font_tiny, (80, 75, 100), 240,
        )

    def _draw_options(self) -> None:
        start_y = 290
        spacing = 66
        for i, option in enumerate(self._OPTIONS):
            y = start_y + i * spacing
            if i == self.selected:
                label = f"> {option} <"
                surf  = self.font_large.render(label, True, GOLD)
                rect  = surf.get_rect(centerx=SCREEN_WIDTH // 2, top=y)
                bg    = rect.inflate(24, 14)
                pygame.draw.rect(self.screen, MENU_HIGHLIGHT, bg, border_radius=5)
                self.screen.blit(surf, rect)
            else:
                self._blit_centered(option, self.font_large, MENU_TEXT, y)

    def _draw_footer(self) -> None:
        self._blit_centered(
            "Arrow Keys / WASD to navigate  |  ENTER to select",
            self.font_tiny, (70, 65, 90), SCREEN_HEIGHT - 30,
        )
        if self._no_save_flash > 0:
            self._no_save_flash -= 1
            self._blit_centered(
                "No save file found — start a New Game first.",
                self.font_small, (220, 120, 60), SCREEN_HEIGHT - 60,
            )


# ---------------------------------------------------------------------------
# Character Select
# ---------------------------------------------------------------------------

class CharacterSelectMenu(_MenuBase):
    """Three-card class selection screen."""

    _CLASSES = [
        {
            "key":     "warrior",
            "name":    "Warrior",
            "symbol":  "W",
            "color":   (180, 120, 60),
            "stats":   "HP: 40   ATK: 6   DEF: 4",
            "desc":    "Tough. Excels at sustained melee.",
            "passive": "Iron Will: HP < 25% grants +4 DEF",
            "gear":    "Iron Sword, Leather Armor, 1x Potion",
        },
        {
            "key":     "rogue",
            "name":    "Rogue",
            "symbol":  "R",
            "color":   (80, 180, 120),
            "stats":   "HP: 25   ATK: 9   DEF: 2",
            "desc":    "Fast. High risk, high reward.",
            "passive": "Backstab: 1st hit on each enemy = 3x",
            "gear":    "Rusty Sword, 2x Bomb, 2x Health Potion",
        },
        {
            "key":     "mage",
            "name":    "Mage",
            "symbol":  "M",
            "color":   (100, 140, 220),
            "stats":   "HP: 20   ATK: 5   DEF: 1",
            "desc":    "Fragile. Master of arcane scrolls.",
            "passive": "Arcane Surge: Scrolls deal 1.5x damage",
            "gear":    "Scroll of Fire x2, Mega Potion x1",
        },
    ]

    _CARD_W = 300
    _CARD_H = 420

    def __init__(self, screen: pygame.Surface) -> None:
        super().__init__(screen)
        self.selected = 0

    def update(self, events: list[pygame.event.Event]) -> Optional[str]:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.selected = (self.selected - 1) % len(self._CLASSES)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.selected = (self.selected + 1) % len(self._CLASSES)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._CLASSES[self.selected]["key"]
            elif event.key == pygame.K_ESCAPE:
                return "back"
        return None

    def render(self) -> None:
        self._blit_centered("CHOOSE  YOUR  CLASS", self.font_title, MENU_TITLE, 50)
        self._draw_divider(118)
        self._draw_cards()
        self._draw_footer()

    def _draw_cards(self) -> None:
        n       = len(self._CLASSES)
        gap     = 40
        total_w = n * self._CARD_W + (n - 1) * gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        y_top   = 140

        for i, cls in enumerate(self._CLASSES):
            x = start_x + i * (self._CARD_W + gap)
            self._draw_card(x, y_top, cls, selected=(i == self.selected))

    def _draw_card(self, x: int, y: int, cls: dict, selected: bool) -> None:
        cw, ch = self._CARD_W, self._CARD_H
        cx     = x + cw // 2
        inner  = cw - 24   # usable text width inside card

        # Background & border
        bg_col     = (25, 20, 38) if selected else (14, 11, 20)
        border_col = cls["color"] if selected else (45, 40, 60)
        border_w   = 2 if selected else 1
        pygame.draw.rect(self.screen, bg_col,     (x, y, cw, ch), border_radius=7)
        pygame.draw.rect(self.screen, border_col, (x, y, cw, ch), border_w, border_radius=7)

        iy = y + 14

        # Symbol
        sym_surf = self.font_title.render(f"[{cls['symbol']}]", True, cls["color"])
        self.screen.blit(sym_surf, sym_surf.get_rect(centerx=cx, top=iy))
        iy += sym_surf.get_height() + 8

        # Name
        name_col = WHITE if selected else MENU_TEXT
        self.screen.blit(
            self.font_large.render(cls["name"], True, name_col),
            self.font_large.render(cls["name"], True, name_col).get_rect(centerx=cx, top=iy),
        )
        iy += self.font_large.get_linesize() + 6

        # Stats
        iy = self._blit_wrapped_centered(cls["stats"], self.font_small,
                                         (160, 200, 160), cx, iy, inner)
        iy += 4

        # Desc
        iy = self._blit_wrapped_centered(cls["desc"], self.font_small,
                                         (150, 140, 170), cx, iy, inner)
        iy += 10

        # Divider
        pygame.draw.line(self.screen, (50, 45, 65),
                         (x + 12, iy), (x + cw - 12, iy), 1)
        iy += 10

        # Passive
        self.screen.blit(
            self.font_tiny.render("PASSIVE", True, GOLD),
            self.font_tiny.render("PASSIVE", True, GOLD).get_rect(centerx=cx, top=iy),
        )
        iy += self.font_tiny.get_linesize() + 2
        iy = self._blit_wrapped_centered(cls["passive"], self.font_tiny,
                                         (200, 180, 120), cx, iy, inner)
        iy += 10

        # Gear
        self.screen.blit(
            self.font_tiny.render("STARTING GEAR", True, (100, 180, 220)),
            self.font_tiny.render("STARTING GEAR", True, (100, 180, 220)).get_rect(
                centerx=cx, top=iy
            ),
        )
        iy += self.font_tiny.get_linesize() + 2
        self._blit_wrapped_centered(cls["gear"], self.font_tiny,
                                    (140, 160, 200), cx, iy, inner)

        # "Press ENTER" at bottom when selected
        if selected:
            label = self.font_small.render("[ ENTER to Select ]", True, cls["color"])
            self.screen.blit(label, label.get_rect(centerx=cx, bottom=y + ch - 10))

    def _draw_footer(self) -> None:
        self._blit_centered(
            "Left / Right to browse  |  ENTER to select  |  ESC to go back",
            self.font_tiny, (70, 65, 90), SCREEN_HEIGHT - 30,
        )


# ---------------------------------------------------------------------------
# Death Screen
# ---------------------------------------------------------------------------

class DeathScreen(_MenuBase):
    def __init__(self, screen: pygame.Surface) -> None:
        super().__init__(screen)

    def render(self, stats: dict) -> None:
        self._blit_centered("YOU  HAVE  FALLEN", self.font_title, (220, 40, 40), 60)
        self._draw_divider(145, (120, 30, 30))
        self._blit_centered(
            "The Crypts have claimed another soul.",
            self.font_small, (140, 80, 80), 158,
        )

        # Stats panel
        panel_w, panel_h = 420, 300
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = 195
        pygame.draw.rect(self.screen, (18, 10, 10), (panel_x, panel_y, panel_w, panel_h), border_radius=6)
        pygame.draw.rect(self.screen, (80, 25, 25), (panel_x, panel_y, panel_w, panel_h), 1, border_radius=6)

        row_keys = [k for k in stats if k != "Score"]
        cy = panel_y + 18
        for key in row_keys:
            label = self.font_medium.render(f"{key}:", True, (160, 100, 100))
            value = self.font_medium.render(str(stats[key]), True, MENU_TEXT)
            self.screen.blit(label, (panel_x + 30, cy))
            self.screen.blit(value, (panel_x + panel_w - value.get_width() - 30, cy))
            cy += 34

        if "Score" in stats:
            pygame.draw.line(self.screen, (80, 25, 25),
                             (panel_x + 20, cy), (panel_x + panel_w - 20, cy), 1)
            cy += 10
            score_s = self.font_large.render(f"SCORE:  {stats['Score']:,}", True, GOLD)
            self.screen.blit(score_s, score_s.get_rect(centerx=SCREEN_WIDTH // 2, top=cy))

        self._blit_centered(
            "Press ENTER to return to menu",
            self.font_small, (120, 80, 80), panel_y + panel_h + 20,
        )


# ---------------------------------------------------------------------------
# Victory Screen
# ---------------------------------------------------------------------------

class VictoryScreen(_MenuBase):
    def __init__(self, screen: pygame.Surface) -> None:
        super().__init__(screen)

    def render(self, stats: dict) -> None:
        self._blit_centered("V I C T O R Y", self.font_title, GOLD, 60)
        self._draw_divider(145, (150, 120, 30))
        self._blit_centered(
            "The Hollow Warden is defeated. You escape the Crypts!",
            self.font_small, (200, 180, 100), 158,
        )

        # Stats panel
        panel_w, panel_h = 420, 300
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = 195
        pygame.draw.rect(self.screen, (12, 12, 8), (panel_x, panel_y, panel_w, panel_h), border_radius=6)
        pygame.draw.rect(self.screen, (120, 90, 20), (panel_x, panel_y, panel_w, panel_h), 1, border_radius=6)

        row_keys = [k for k in stats if k != "Score"]
        cy = panel_y + 18
        for key in row_keys:
            label = self.font_medium.render(f"{key}:", True, (180, 150, 80))
            value = self.font_medium.render(str(stats[key]), True, MENU_TEXT)
            self.screen.blit(label, (panel_x + 30, cy))
            self.screen.blit(value, (panel_x + panel_w - value.get_width() - 30, cy))
            cy += 34

        if "Score" in stats:
            pygame.draw.line(self.screen, (120, 90, 20),
                             (panel_x + 20, cy), (panel_x + panel_w - 20, cy), 1)
            cy += 10
            score_s = self.font_large.render(f"SCORE:  {stats['Score']:,}", True, GOLD)
            self.screen.blit(score_s, score_s.get_rect(centerx=SCREEN_WIDTH // 2, top=cy))

        self._blit_centered(
            "Press ENTER to return to menu",
            self.font_small, (140, 120, 60), panel_y + panel_h + 20,
        )
