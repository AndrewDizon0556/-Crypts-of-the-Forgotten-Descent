# Changelog — Crypts of the Forgotten Descent

All notable changes to this project, organized by development phase.

---

## Phase 3 — Systems (current)

### Added
- **Inventory overlay** (`ui/inventory_ui.py`)
  - Press `I` to open a full-screen overlay showing all 8 inventory slots
  - Navigate with `↑`/`↓`, press `E` to use or equip, `D` to drop, `I`/`ESC` to close
  - Displays equipped weapon and armor at the top of the panel
  - Color-coded item type tags (`[consumable]` in green, `[weapon]`/`[armor]` in blue)
  - Browsing and equipping gear are free actions (no turn consumed); using a consumable costs a turn

- **Shrine blessing UI** (`ui/shrine_ui.py`)
  - Walking onto a shrine tile (Ω) opens a three-boon selection overlay
  - Seven possible boons: Divine Mend, Warbrand, Stone Skin, Cleansing Light, Gold Bless, XP Surge, Shard Echo
  - Shard Echo (survive one death) only offered on floors 6+
  - Shrine tile reverts to floor after a boon is accepted; ESC leaves the shrine intact

- **Minimap overlay** (`ui/minimap.py`)
  - Press `M` to toggle a 120×80 px overview in the bottom-left of the viewport
  - 2 pixels per map tile; shows explored floors, walls, stairs, shrines, and player position
  - Alive enemies shown as red dots

- **Shrine placement** in `_populate_floor`
  - One shrine placed per floor on floors 2, 4, 6, 8
  - Positioned in the room farthest from the player spawn point

- **Shard of Ethos placement** in `_populate_floor`
  - One Shard of Ethos auto-placed per floor on floors 4–10
  - Positioned in the room farthest from the player spawn point

- **Arcane Surge in inventory use**
  - Mage character class receives ×1.5 fire damage when using Scroll of Fire from inventory
  - AoE kills from inventory-used bombs/scrolls grant XP, gold, and level-up notifications

### Changed
- `game.py` `_update_playing`: routes events to `InventoryUI` or `ShrineUI` when their overlays are active before processing normal player input
- `game.py` `_handle_playing_input`: added `I` (inventory) and `M` (minimap toggle) key handlers
- `game.py` `_try_move`: detects shrine tile after movement and calls `_trigger_shrine`
- `game.py` `_render_playing`: draws minimap, inventory, and shrine overlays on top of the base render
- `game.py` `_populate_floor`: now tracks `occupied` set for items so shrine/shard placement avoids duplicates
- `ui/hud.py` controls panel: added `M — Minimap toggle` entry
- Opening message updated to mention `I` and `M` keys

---

## Phase 2 — Core Engine

### Added
- **Full PLAYING game loop** (`game.py`)
  - Turn pipeline: player act → status tick → FOV update → enemy turns → enemy status tick → condition check
  - `WASD`/arrow key movement; `SPACE` waits one turn and restores 1 HP
  - Bump-to-attack melee: walking into an enemy tile resolves combat
  - Item pickup on movement (auto-equip for weapons/armor; add to inventory for consumables)
  - Stair descent to next floor with re-generation

- **Enemy AI** (`systems/ai.py`)
  - FSM: `IDLE → CHASE → ATTACK` based on distance and adjacency
  - BFS pathfinding that avoids walls and occupied tiles
  - Enemies outside the player's FOV are frozen

- **Combat system** (`systems/combat.py`)
  - Player attack formula with ±variance and 10% crit chance (×2)
  - Rogue backstab passive: ×3 damage on first hit per enemy
  - Enemy attack with DEF mitigation; Wraith bypasses DEF entirely
  - Special ability trigger every 3rd enemy attack
  - AoE functions: `aoe_bomb_damage` (adjacent), `aoe_fire_scroll_damage` (all enemies)
  - Per-turn status damage for Bleed (−1 HP) and Poison (−2 HP)

- **Field of View** (`systems/fov.py`)
  - 360-ray raycasting with radius 6; walls visible but block further rays
  - Explored tiles remembered after leaving FOV

- **Renderer** (`ui/renderer.py`)
  - Renders dungeon tiles with FOV-aware coloring (visible vs explored vs unexplored)
  - Draws items, enemies, and player glyph on an 800×700 game surface
  - Camera centered on player, clamped to map bounds

- **HUD** (`ui/hud.py`)
  - HP bar (red), XP bar (blue), floor title, level/ATK/DEF/GOLD stats
  - Equipment slots showing equipped weapon and armor
  - Active status effect display
  - Scrolling message log (10 lines, oldest messages drop off)
  - Pinned controls reminder panel above the log

- **Player progression**
  - XP and gold gained on kills; level-up at N × 50 XP thresholds
  - Level-up: +10 max HP, +2 ATK, +1 DEF; level cap 20
  - Iron Will (Warrior): +4 DEF when HP ≤ 25%

- **Enemy factory and floor scaling** (`entities/enemy.py`)
  - Five enemy types: Skeleton, Ghoul, Wraith, Stone Golem, Lich
  - Unlock floors: Skeleton (1), Ghoul (2), Wraith (3), Golem (4), Lich (7)
  - Floor scaling: +3 HP and +1 ATK per 2 floors

- **Continue / save flash** (`game.py`, `ui/menus.py`)
  - `_handle_continue` loads save if present; shows "No save file found" flash otherwise

### Changed
- Tile colors brightened for visibility (floor `(70,68,90)`, wall `(110,105,135)`)
- Opening HUD message added with controls hint

### Fixed
- `Continue` menu option previously had no handler and did nothing

---

## Phase 1 — Project Setup

### Added
- Project structure under `crypts_of_the_forgotten_descent/`
- `config.py`: all global constants (window size, colors, gameplay values)
- `main.py`: pygame initialization and game entry point
- `entities/`: `Entity` base dataclass with status effect support; `Player`, `Enemy`, `Boss` stubs
- `systems/`: `DungeonGenerator` (BSP), `compute_fov`, `Item` dataclass, `build_item`, `use_item`, `save_game`/`load_game`, `calculate_score`, `save_score`, `get_top_scores`
- `data/items.json`: 13 item definitions
- `data/enemies.json`: 5 enemy definitions
- `ui/`: `Renderer`, `HUD`, `MainMenu`, `CharacterSelectMenu`, `DeathScreen`, `VictoryScreen`
- `requirements.txt`: `pygame>=2.0.0`
- `tests/__init__.py`: placeholder for future test suite
- Main menu with four options: New Game, Continue, Leaderboard, Quit
- Character selection screen with three class cards (Warrior, Rogue, Mage) showing stats, passives, and starting gear

---

---

## Phase 4 — Enemy Polish

### Added
- **Wraith wall-phasing** (`systems/ai.py`)
  - `bfs_next_step` now accepts `wall_pass=True`, treating every in-bounds tile as passable
  - `update_enemy_ai` passes `wall_pass=isinstance(enemy, Wraith)` so Wraiths phase through walls

- **Slow/Stun player turn-skip** (`game.py`)
  - `_handle_playing_input` checks `player.has_status("slow")` at the top; if stunned, prints a message and returns `True` (consuming the turn) without processing any key input
  - Stun duration is 1, so the player loses exactly one turn then recovers

- **Enemy `effective_atk` / `effective_def` base properties** (`entities/enemy.py`)
  - Added to `Enemy` base class (defaults to `self.atk` / `self.defense`)
  - `HollowWarden` already overrides them for Phase 3 rage stats (ATK 25, DEF 3)

- **`enemy_attack` uses `effective_atk`** (`systems/combat.py`)
  - All enemy damage rolls now use `attacker.effective_atk` so boss phase stat changes apply automatically

---

## Phase 5 — Boss Fight

### Added
- **Hollow Warden placement on floor 10** (`game.py._populate_floor`)
  - Boss is placed in the room farthest from the player spawn
  - Ominous messages broadcast on floor entry

- **Boss turn runner** (`game.py._run_boss_turn`)
  - Checks phase transition on every turn; broadcasts phase-change messages
  - Increments `summon_timer`; spawns minions when threshold is reached
  - Phase 2: `move_speed = 2` — boss moves twice per turn but only attacks once
  - Phase 3 AOE slam: when `special == "AOE_SLAM"`, applies an extra 15 direct damage to the player

- **Boss minion spawning** (`game.py._spawn_boss_summon`)
  - Scans adjacent tiles for a free walkable position
  - Spawns Skeleton (Phase 1), Ghoul (Phase 2), or Wraith (Phase 3)

- **Victory trigger** — when boss HP reaches 0 `session_stats["victory"] = True`; `_check_conditions` picks it up and calls `_end_run(victory=True)`

- **Shard Echo** (`game.py._check_conditions`)
  - If `player.shard_echo` is True when the player would die, HP is restored to 1, `alive` stays True, and the token is consumed instead of triggering death

---

## Phase 6 — Persistence & End Screens

### Added
- **Full save/load restore** (`systems/save.py`, `game.py._restore_game`)
  - `_build_state` now serialises `equipped_weapon`, `equipped_armor` (by item key), and `backstab_ready`
  - `_restore_game` rebuilds the `Player` object from saved values, re-attaches equipment and inventory, then regenerates the floor
  - Stats (HP, ATK, DEF, level, XP, gold) are restored exactly as saved — equipment bonuses are already baked in so no double-application

- **Auto-save on stair descent** (`game.py._descend`)
  - `save_game(self)` called after each floor transition; exceptions are swallowed silently

- **Score calculation and leaderboard saving** (`game.py._end_run`)
  - `calculate_score(session_stats, victory)` is called on death and victory
  - `save_score` writes the result to `data/scores.db` (class name used as the run name)

- **Death screen** (`ui/menus.py.DeathScreen`)
  - Two-column stat table (label / value), final score in gold at the bottom

- **Victory screen** (`ui/menus.py.VictoryScreen`)
  - Same layout in gold/amber tones; "The Hollow Warden is defeated" flavour text

- **`_report_enemy_attack` extracted** (`game.py`)
  - Shared helper used by both the normal enemy loop and `_run_boss_turn` for consistent HUD messages

### Changed
- `_handle_continue` now calls `_restore_game` instead of starting a brand new game with the same class

---

## Phase 7 — Polish

### Added
- **Locked rooms with Dungeon Key** (`game.py._populate_floor`, `game.py._try_move`, `systems/dungeon.py`)
  - On floors 3+, one room per floor is locked behind DOOR tiles (`+`) placed on corridor entries
  - DOOR tiles block all movement (including BFS pathfinding for enemies)
  - Wraiths cannot phase through DOOR tiles even with `wall_pass=True`
  - A **Dungeon Key** item is placed in a different room on the same floor
  - Walking into a locked door with the key in inventory auto-consumes it and opens the door permanently (tile becomes FLOOR)
  - Walking into a locked door without a key shows a warning and costs no turn

- **Shard counter in HUD** (`ui/hud.py`)
  - Added `SHD X/7` row to the stats panel in cyan
  - Dims to a muted teal when the player has found 0 shards

- **Item comparison in inventory** (`ui/inventory_ui.py._compare_tag`)
  - Weapon slots show delta vs equipped weapon: `+N ATK` (green) / `−N ATK` (red) / `±0 ATK` (neutral)
  - Armor slots show delta vs equipped armor: `+N DEF` / `−N DEF` / `±0 DEF`
  - If no weapon/armor is equipped, shows the raw bonus instead of a delta
  - Lifesteal and ATK-penalty suffixes appended where applicable

- **Status-effect glow on player** (`ui/renderer.py._draw_player`)
  - An SRCALPHA tinted rectangle (alpha 80) is drawn under the player glyph while a status is active
  - Bleed → red, Poison → green, Cursed → purple, Slow → yellow
  - Only the first/highest-priority status is shown at a time

- **Pending-pickup flow when inventory is full** (`game.py._pick_up`, `game.py._handle_inventory_result`)
  - When a consumable cannot fit in the inventory, it is stored as `_pending_pickup` and the inventory overlay opens automatically
  - Dropping any item from the inventory resolves the pending pickup: the item is added, a message is shown, and the overlay closes
  - Gear (weapons/armor) picked up when all 8 slots are full is still rejected with a message (no pending flow)

### Changed
- `systems/dungeon.py` `is_walkable`: now returns `False` for DOOR tiles in addition to WALL tiles
- `ui/renderer.py`: added `_DOOR_COLOR`/`_DOOR_EXP_COLOR` to tile color dicts; renders `+` glyph on DOOR tiles; added `_STATUS_GLOW` dict
- `ui/hud.py` `render` / `_draw_stats`: signature now accepts `shards: int = 0`; new "SHD" row
- `game.py` `_render_playing`: passes `shards=session_stats["shards_found"]` to `hud.render`
