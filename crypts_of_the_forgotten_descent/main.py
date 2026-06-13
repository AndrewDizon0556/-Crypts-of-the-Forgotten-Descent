"""Entry point — run this file to start the game."""
from __future__ import annotations

import sys
import pygame

from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE
from game import Game


def main() -> None:
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock  = pygame.time.Clock()

    game = Game(screen, clock)
    game.run()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
