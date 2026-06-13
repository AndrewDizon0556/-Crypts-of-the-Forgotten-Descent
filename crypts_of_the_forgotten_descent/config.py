"""Global constants for Crypts of the Forgotten Descent."""
from __future__ import annotations

# --- Window & Display ---
SCREEN_WIDTH  = 1120
SCREEN_HEIGHT = 700
FPS           = 60
WINDOW_TITLE  = "Crypts of the Forgotten Descent"

# --- Map ---
MAP_WIDTH  = 60   # tiles
MAP_HEIGHT = 40   # tiles
TILE_SIZE  = 16   # pixels (base)
RENDER_SCALE = 2  # multiplier → 32 px rendered tiles

# --- Viewport (tiles visible at once in the game area) ---
VIEWPORT_TILES_W = 25
VIEWPORT_TILES_H = 21

# --- HUD ---
HUD_WIDTH    = 320              # right-side panel width
GAME_AREA_W  = SCREEN_WIDTH - HUD_WIDTH   # 800
GAME_AREA_H  = SCREEN_HEIGHT              # 700

# --- Tile rendering ---
TILE_RENDER_SIZE = TILE_SIZE * RENDER_SCALE  # 32 px

# --- Colors (dark fantasy palette) ---
BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
DARK_GRAY  = (40,  40,  40)
GRAY       = (100, 100, 100)
LIGHT_GRAY = (180, 180, 180)
RED        = (200,  50,  50)
DARK_RED   = (120,  20,  20)
GREEN      = (50,  200,  80)
DARK_GREEN = (30,  100,  40)
BLUE       = (50,  100, 200)
DARK_BLUE  = (20,   40, 100)
YELLOW     = (220, 200,  60)
GOLD       = (200, 165,  30)
PURPLE     = (120,  50, 180)
ORANGE     = (200, 120,  40)
CYAN       = (80,  200, 220)

# --- UI Colors ---
BG_COLOR       = (10,   8,  15)
WALL_COLOR     = (70,  65,  90)
FLOOR_COLOR    = (45,  42,  58)
FLOOR_VISIBLE  = (70,  68,  90)   # brighter: clearly distinct from black
WALL_VISIBLE   = (110, 105, 135)  # lighter purple-gray walls
EXPLORED_FLOOR = (30,  28,  38)   # dim but visible memory tiles
EXPLORED_WALL  = (50,  48,  62)
HUD_BG         = (15,  12,  22)
HUD_BORDER     = (60,  50,  80)
MENU_BG        = (8,    6,  12)
MENU_HIGHLIGHT = (80,  60, 120)
MENU_TEXT      = (200, 190, 220)
MENU_TITLE     = (180, 140, 220)
HEALTH_BAR_FG  = (180,  40,  40)
HEALTH_BAR_BG  = (60,   15,  15)
XP_BAR_FG      = (60,  160, 220)
XP_BAR_BG      = (15,   40,  60)

# --- Entity Colors ---
PLAYER_COLOR  = (220, 220,  80)
SKELETON_COLOR = (200, 200, 200)
GHOUL_COLOR   = (80,  180,  80)
WRAITH_COLOR  = (160,  80, 220)
GOLEM_COLOR   = (140, 120, 100)
LICH_COLOR    = (200,  60, 200)
BOSS_COLOR    = (220,  60,  60)

# --- Item Colors ---
POTION_COLOR = (200,  60,  60)
SCROLL_COLOR = (220, 180,  80)
WEAPON_COLOR = (160, 160, 200)
ARMOR_COLOR  = (100, 160, 220)
SHARD_COLOR  = (80,  220, 220)
KEY_COLOR    = (220, 200,  60)
SHRINE_COLOR = (180, 120, 220)

# --- Gameplay ---
FOV_RADIUS          = 6
MAX_INVENTORY_SLOTS = 8
MAX_PLAYER_LEVEL    = 20
TOTAL_FLOORS        = 10
TOTAL_SHARDS        = 7
SHRINE_FLOORS       = {2, 4, 6, 8}
SHARD_FLOORS        = {4, 5, 6, 7, 8, 9, 10}
XP_PER_LEVEL_BASE   = 50    # Level N requires N * 50 XP

# --- Score ---
SCORE_PER_FLOOR     = 100
SCORE_PER_KILL      = 10
SCORE_PER_GOLD      = 2
SCORE_PER_SHARD     = 200
SCORE_VICTORY_BONUS = 5000
