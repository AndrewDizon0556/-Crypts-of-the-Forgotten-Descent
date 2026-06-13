"""Inventory overlay — shown on top of the game when the player presses I."""
from __future__ import annotations

from typing import Optional

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    MENU_TEXT, MENU_HIGHLIGHT, GOLD, WHITE, HUD_BORDER,
)

# Panel geometry
_PW = 500
_PH = 450
_PX = (SCREEN_WIDTH - _PW) // 2
_PY = (SCREEN_HEIGHT - _PH) // 2
_SLOT_H = 38


class InventoryUI:
    """
    Pure UI: renders the inventory panel and reports user selections.
    All game-state changes are applied by game.py.
    """

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen     = screen
        self.font_title = pygame.font.SysFont("monospace", 22, bold=True)
        self.font       = pygame.font.SysFont("monospace", 17)
        self.font_small = pygame.font.SysFont("monospace", 13)
        self.selected   = 0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def update(
        self, events: list[pygame.event.Event], inventory: list
    ) -> Optional[tuple]:
        """
        Return values:
          None              — still open, no decision yet
          ("close", None)   — ESC / I pressed, close with no action
          ("use",   index)  — E pressed, use item at index
          ("drop",  index)  — D pressed, drop item at index
        """
        n = len(inventory)
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            k = event.key
            if k in (pygame.K_ESCAPE, pygame.K_i):
                return ("close", None)
            elif k in (pygame.K_UP, pygame.K_w) and n:
                self.selected = (self.selected - 1) % n
            elif k in (pygame.K_DOWN, pygame.K_s) and n:
                self.selected = (self.selected + 1) % n
            elif k == pygame.K_e and n and self.selected < n:
                return ("use", self.selected)
            elif k == pygame.K_d and n and self.selected < n:
                return ("drop", self.selected)
        return None

    def render(self, player) -> None:
        # Semi-transparent dim overlay
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 155))
        self.screen.blit(dim, (0, 0))

        # Panel background + border
        pygame.draw.rect(self.screen, (16, 13, 26), (_PX, _PY, _PW, _PH), border_radius=7)
        pygame.draw.rect(self.screen, (90, 65, 130), (_PX, _PY, _PW, _PH), 2, border_radius=7)

        # Title
        title = self.font_title.render("I N V E N T O R Y", True, GOLD)
        self.screen.blit(title, title.get_rect(centerx=_PX + _PW // 2, top=_PY + 14))

        # Equipped gear summary
        wpn = player.equipped_weapon
        arm = player.equipped_armor
        y = _PY + 48
        gear_txt = (
            f"Equipped — Weapon: {wpn.name if wpn else '—'}"
            f"   Armor: {arm.name if arm else '—'}"
        )
        gs = self.font_small.render(gear_txt, True, (130, 155, 200))
        self.screen.blit(gs, gs.get_rect(centerx=_PX + _PW // 2, top=y))
        y += 20
        pygame.draw.line(
            self.screen, HUD_BORDER,
            (_PX + 12, y), (_PX + _PW - 12, y), 1,
        )
        y += 8

        # Item slots
        inv = player.inventory
        for i in range(8):
            row_y = y + i * _SLOT_H
            is_sel = i == self.selected and i < len(inv)

            if is_sel:
                pygame.draw.rect(
                    self.screen, MENU_HIGHLIGHT,
                    (_PX + 10, row_y, _PW - 20, _SLOT_H - 2),
                    border_radius=4,
                )

            if i < len(inv):
                item = inv[i]
                # Slot number
                num_s = self.font_small.render(f"[{i+1}]", True, (90, 80, 110))
                self.screen.blit(num_s, (_PX + 16, row_y + 11))
                # Symbol
                sym_s = self.font.render(item.symbol, True, item.color)
                self.screen.blit(sym_s, (_PX + 46, row_y + 9))
                # Name
                name_color = WHITE if is_sel else MENU_TEXT
                name_s = self.font.render(item.name, True, name_color)
                self.screen.blit(name_s, (_PX + 70, row_y + 9))
                # Comparison tag for equipment (right side)
                cmp_text, cmp_color = self._compare_tag(item, player)
                if cmp_text:
                    cmp_s = self.font_small.render(cmp_text, True, cmp_color)
                    self.screen.blit(
                        cmp_s,
                        (_PX + _PW - cmp_s.get_width() - 16, row_y + 12),
                    )
                else:
                    tag_color = (110, 180, 110) if item.item_type == "consumable" else (110, 140, 210)
                    tag_s = self.font_small.render(f"[{item.item_type}]", True, tag_color)
                    self.screen.blit(
                        tag_s,
                        (_PX + _PW - tag_s.get_width() - 16, row_y + 12),
                    )
            else:
                empty_s = self.font_small.render(f"[{i+1}]  empty", True, (48, 44, 62))
                self.screen.blit(empty_s, (_PX + 16, row_y + 11))

        # Footer hints
        hint_y = _PY + _PH - 36
        pygame.draw.line(
            self.screen, HUD_BORDER,
            (_PX + 12, hint_y - 6), (_PX + _PW - 12, hint_y - 6), 1,
        )
        hint = self.font_small.render(
            "↑↓ Select  |  E Use / Equip  |  D Drop  |  I / ESC Close",
            True, (75, 70, 95),
        )
        self.screen.blit(hint, hint.get_rect(centerx=_PX + _PW // 2, top=hint_y))

    def _compare_tag(self, item, player) -> tuple[str, tuple]:
        """Return (label, color) showing stat delta vs equipped gear, or ('', ()) if n/a."""
        if item.item_type == "weapon":
            equipped = player.equipped_weapon
            if equipped:
                delta = item.atk_bonus - equipped.atk_bonus
                label = f"{delta:+d} ATK"
                color = (100, 220, 100) if delta > 0 else (220, 100, 100) if delta < 0 else (160, 155, 175)
            else:
                label = f"+{item.atk_bonus} ATK"
                color = (100, 220, 100)
            if item.lifesteal:
                label += f" {int(item.lifesteal*100)}%ls"
            return label, color
        if item.item_type == "armor":
            equipped = player.equipped_armor
            if equipped:
                delta = item.def_bonus - equipped.def_bonus
                label = f"{delta:+d} DEF"
                color = (100, 220, 100) if delta > 0 else (220, 100, 100) if delta < 0 else (160, 155, 175)
            else:
                label = f"+{item.def_bonus} DEF"
                color = (100, 220, 100)
            if item.atk_penalty:
                label += f" {item.atk_penalty}atk"
            return label, color
        return "", ()
