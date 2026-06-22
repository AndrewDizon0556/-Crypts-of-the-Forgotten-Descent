# Crypts of the Forgotten Descent — Documentation

A turn-based roguelike dungeon crawler built with Python 3.10+ and Pygame 2.x.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Controls](#2-controls)
3. [Game Objective](#3-game-objective)
4. [Player Classes](#4-player-classes)
5. [Combat System](#5-combat-system)
6. [Enemies](#6-enemies)
7. [Items & Inventory](#7-items--inventory)
8. [Status Effects](#8-status-effects)
9. [Shrines](#9-shrines)
10. [Dungeon Generation](#10-dungeon-generation)
11. [Scoring](#11-scoring)
12. [Saving & Permadeath](#12-saving--permadeath)
13. [Architecture Overview](#13-architecture-overview)
14. [File Reference](#14-file-reference)

---

## 1. Getting Started

**Requirements**
- Python 3.10 or higher
- Pygame 2.x (`py -3 -m pip install pygame`)

**Run the game**
```
cd crypts_of_the_forgotten_descent
py -3 main.py
```

---

## 2. Controls

| Key | Action |
|-----|--------|
| `W` / `↑` | Move up |
| `S` / `↓` | Move down |
| `A` / `←` | Move left |
| `D` / `→` | Move right |
| `SPACE` | Wait one turn (restores 1 HP) |
| `I` | Open / close inventory |
| `M` | Toggle minimap overlay |
| `ESC` | Return to main menu |

**Inside the inventory**

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate items |
| `E` | Use or equip selected item |
| `D` | Drop selected item on the floor |
| `I` / `ESC` | Close inventory (no turn spent) |

**At a shrine (Ω)**

| Key | Action |
|-----|--------|
| `↑` / `↓` | Choose a boon |
| `E` / `ENTER` | Accept the selected boon |
| `ESC` | Leave shrine without a boon |

---

## 3. Game Objective

Descend 10 floors and collect all **7 Shards of Ethos** (one per floor, floors 4–10). Shards are scattered in the deepest rooms of each floor. Reaching the victory condition requires defeating the final boss on floor 10.

- **Stairs** (`>`) descend to the next floor.
- **Permadeath applies** — death deletes the save file.

---

## 4. Player Classes

| Stat | Warrior | Rogue | Mage |
|------|---------|-------|------|
| HP | 40 | 25 | 20 |
| ATK | 6 | 9 | 5 |
| DEF | 4 | 2 | 1 |
| Passive | Iron Will | Backstab | Arcane Surge |

**Level-up bonuses** (every level): +10 max HP, +2 ATK, +1 DEF. Max level is 20. XP required for level N = N × 50.

### Passive Abilities

**Iron Will (Warrior)**
When HP drops to 25% or below, gain a permanent +4 DEF bonus. Activates automatically and stays active as long as HP remains low.

**Backstab (Rogue)**
The first melee hit on each enemy deals 3× damage. The bonus resets after the target dies, making the next fresh enemy vulnerable again. Enabled from the start of the game.

**Arcane Surge (Mage)**
Scrolls of Fire deal 1.5× their base damage (12 → 18). Applied automatically when using any fire-damage scroll.

---

## 5. Combat System

### Turn Order

Each time the player takes an action:
1. Player acts (move, attack, use item)
2. Player status effects tick (bleed/poison damage dealt)
3. Field of view updates
4. All enemies take their turns (BFS pathfinding + attack)
5. Enemy status effects tick
6. Win/lose conditions checked

Browsing or closing the inventory does **not** consume a turn. Opening and equipping gear from inventory also does not consume a turn. Using a consumable item from inventory **does** consume a turn.

### Melee (Bump-to-Attack)

Walk into an enemy tile to attack. No separate attack key.

**Player attack formula:**
```
raw    = effective_atk - enemy.defense + randint(-1, 2)
damage = max(1, raw)
```

- 10% chance of a critical hit (×2 damage).
- Rogue backstab multiplier (×3) is applied before critical, then the backstab flag clears.
- A critted backstab is therefore 6× base.

**Enemy attack formula:**
```
raw    = enemy.atk - player.effective_defense + randint(-1, 2)
damage = max(1, raw)
```

- Wraith bypasses DEF entirely (uses `atk + randint(-1, 2)` only).
- Every 3rd attack triggers the enemy's special ability.

### AoE Items

| Item | Effect |
|------|--------|
| Bomb | 20 damage to all tiles within 1 step of the player |
| Scroll of Fire | 12 damage (18 for Mage) to every living enemy on the floor |

---

## 6. Enemies

Enemies that cannot see the player (outside FOV) are frozen — they do not move or attack.

| Enemy | Sym | HP | ATK | DEF | XP | Gold | Min Floor | Special (every 3rd attack) |
|-------|-----|----|-----|-----|----|------|-----------|---------------------------|
| Skeleton | S | 8 | 4 | 1 | 10 | 2 | 1 | None |
| Ghoul | G | 14 | 6 | 2 | 20 | 5 | 2 | BLEED (8 turns, 1 HP/turn) |
| Wraith | W | 10 | 8 | 0 | 25 | 4 | 3 | PHASE (ignores player DEF) |
| Stone Golem | O | 30 | 7 | 6 | 50 | 12 | 4 | STUN (2× damage that hit) |
| Lich | L | 20 | 10 | 3 | 60 | 15 | 7 | CURSED (4 turns, halved ATK+DEF) |

**Floor scaling:** Every 2 floors, all enemies gain +3 max HP and +1 ATK.

**Spawn count per floor:** `floor × 2 + randint(2, 5)` enemies. Enemies do not spawn in the starting room.

### AI Behaviour (FSM)

```
IDLE → CHASE  : player enters detection_range tiles
CHASE → ATTACK: player is adjacent (1 tile)
ATTACK → CHASE: player moves away from adjacent tile
```

Pathfinding uses BFS, avoiding walls and other occupied tiles (but can target the player's tile for attacks).

---

## 7. Items & Inventory

### Inventory Rules

- Maximum **8 slots**.
- Equipment (weapons, armor) picked from the floor is **auto-equipped**. The old item (if any) moves to an inventory slot.
- If inventory is full when picking up a **consumable**, the inventory overlay opens automatically. Drop any item to resolve the pending pickup — it is added instantly and the overlay closes.
- If inventory is full when picking up **gear** (weapon/armor), the item is rejected with a message and stays on the floor.
- Items dropped from inventory appear on the player's current tile.

### Item Table

| Key | Name | Type | Effect |
|-----|------|------|--------|
| `health_potion` | Health Potion | Consumable | Restore 15 HP; cures Bleed |
| `mega_potion` | Mega Potion | Consumable | Restore 35 HP; cures Bleed |
| `bomb` | Bomb | Consumable | 20 AoE damage within 1 tile |
| `scroll_of_fire` | Scroll of Fire | Consumable | 12 damage all enemies (18 for Mage) |
| `antidote` | Antidote | Consumable | Cure Poison |
| `rusty_sword` | Rusty Sword | Weapon | +2 ATK |
| `iron_sword` | Iron Sword | Weapon | +4 ATK |
| `shadow_blade` | Shadow Blade | Weapon | +7 ATK, 15% lifesteal |
| `leather_armor` | Leather Armor | Armor | +2 DEF |
| `chain_mail` | Chain Mail | Armor | +4 DEF |
| `obsidian_plate` | Obsidian Plate | Armor | +7 DEF, −1 ATK |
| `shard_of_ethos` | Shard of Ethos | Shard | Quest item (collect 7) |
| `dungeon_key` | Dungeon Key | Key | Opens locked rooms |

### Starting Gear

| Class | Starting Equipment |
|-------|--------------------|
| Warrior | Iron Sword, Leather Armor, 1× Health Potion |
| Rogue | Rusty Sword, 2× Bomb, 2× Health Potion |
| Mage | 2× Scroll of Fire, 1× Mega Potion |

### Item Availability by Floor

| Floor Range | New Items |
|-------------|-----------|
| 1–2 | Potions, Bombs, Scrolls, Antidote |
| 3+ | Rusty Sword, Leather Armor |
| 5+ | Iron Sword, Chain Mail |
| 7+ | Shadow Blade, Obsidian Plate |

---

## 8. Status Effects

| Status | Source | Duration | Effect per turn | Cure |
|--------|--------|----------|-----------------|------|
| Bleed | Ghoul | 8 turns | −1 HP | Any heal item |
| Poison | (future) | 5 turns | −2 HP | Antidote |
| Cursed | Lich | 4 turns | ATK and DEF halved | Cleansing Light shrine boon |
| Slow | Stone Golem | 1 turn | — | Expires automatically |

Status effects tick **before** enemies act each turn.

---

## 9. Shrines

Shrines (Ω) appear on floors **2, 4, 6, and 8**, placed in a room far from the spawn point. Walk onto the tile to open the shrine menu. Three boons are offered at random; choose one, or press ESC to leave.

After a boon is chosen, the shrine tile reverts to floor — it cannot be used again.

### Boon Table

| Boon | Effect | Notes |
|------|--------|-------|
| Divine Mend | Restore HP to maximum | |
| Warbrand | Permanently +3 ATK | |
| Stone Skin | Permanently +2 DEF | |
| Cleansing Light | Remove all status effects | |
| Gold Bless | +25 GOLD | |
| XP Surge | +75 XP (may trigger level-up) | |
| Shard Echo | Survive one death at 1 HP | Only offered on floors 6–10 |

---

## 10. Dungeon Generation

The dungeon uses **Binary Space Partitioning (BSP)**:

1. The map (60×40 tiles) is recursively split up to depth 5.
2. A room (5–15 wide, 4–10 tall) is placed inside each leaf.
3. Rooms are connected with L-shaped corridors.
4. A BFS validation ensures all rooms are reachable.
5. If generation fails (< 3 rooms), it retries up to 3 times with a fallback single-room map.

**Locked rooms (floors 3+):** On floors 3 and beyond, one room per floor is sealed with DOOR tiles (`+`) placed on the corridor entry points leading into it. The room contents (enemies, items) are inaccessible until the player finds the **Dungeon Key** placed elsewhere on the same floor and walks into a locked door. Wraiths cannot phase through DOOR tiles.

**Field of View** uses 360-ray raycasting with a radius of 6 tiles. Walls are visible but block rays. Explored tiles remain dimly visible as memory.

**Minimap** (press M): A 120×80 pixel overlay (2 px per map tile) in the bottom-left of the viewport. Shows all explored tiles and your current position.

---

## 11. Scoring

```
score = (floors_reached × 100)
      + (enemies_killed × 10)
      + (gold_collected × 2)
      + (shards_found   × 200)
      + turns_survived
      + (5000 if victory)
```

Scores are saved to `data/scores.db` (SQLite). The leaderboard shows the top 10 runs.

---

## 12. Saving & Permadeath

- The game auto-saves to `save.json` in the working directory.
- **Death permanently deletes the save file.** There is no recovery.
- `Continue` on the main menu loads the most recent save. If no save exists, a warning message is shown.

---

## 13. Architecture Overview

```
main.py                     Entry point — init pygame, create Game, call run()
game.py                     Core loop, state machine, turn pipeline, overlay flags
config.py                   All global constants (sizes, colors, gameplay values)

entities/
  entity.py                 Base Entity dataclass + StatusEffect
  player.py                 Player(Entity) — classes, XP, passives, inventory helpers
  enemy.py                  Enemy(Entity), FSM state, 5 concrete types, factory
  boss.py                   HollowWarden(Enemy) — 3-phase boss (Phase 8)

systems/
  dungeon.py                DungeonMap, DungeonGenerator (BSP)
  fov.py                    compute_fov() — 360-ray raycasting
  combat.py                 player_attack, enemy_attack, status damage, AoE
  inventory.py              Item dataclass, build_item(), use_item()
  ai.py                     bfs_next_step(), update_enemy_ai() FSM
  save.py                   JSON save / load / delete
  score.py                  SQLite leaderboard, calculate_score()

ui/
  renderer.py               Renders dungeon tiles, items, entities to game surface
  hud.py                    Right-side panel: HP/XP bars, stats, log, controls
  menus.py                  MainMenu, CharacterSelectMenu, DeathScreen, VictoryScreen
  inventory_ui.py           Inventory overlay (I key)
  shrine_ui.py              Shrine boon selection overlay (Ω tile)
  minimap.py                Minimap overlay (M key)

data/
  items.json                Item definitions
  enemies.json              Enemy definitions (base stats, min_floor)
  scores.db                 SQLite leaderboard (created at runtime)
```

### Turn Pipeline (PLAYING state)

```
Player presses key
  └─ inventory_open?  → route to InventoryUI.update()
  └─ shrine_active?   → route to ShrineUI.update()
  └─ _handle_playing_input()
       └─ move / bump-attack / pickup / stairs / shrine trigger
  → _tick_player_statuses()    bleed/poison damage
  → _update_fov()              recompute visible tiles
  → _process_enemy_turns()     BFS move + attack for each enemy
  → _tick_enemy_statuses()     enemy bleed/poison + prune dead
  → _check_conditions()        death / victory
  → session_stats["turns"] += 1
```

### Overlay System

Three flags in `Game` control overlays drawn on top of the playing view:

| Flag | Trigger | Blocks turns |
|------|---------|--------------|
| `inventory_open` | `I` key | Browsing/equipping: no. Using consumable: yes |
| `shrine_active` | Walk onto Ω tile | Yes (until boon chosen or ESC) |
| `show_minimap` | `M` key (toggle) | No |

---

## 14. File Reference

### config.py — Key Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `SCREEN_WIDTH` | 1120 | Window width (px) |
| `SCREEN_HEIGHT` | 700 | Window height (px) |
| `GAME_AREA_W` | 800 | Viewport width (px) |
| `HUD_WIDTH` | 320 | Right panel width (px) |
| `MAP_WIDTH` | 60 | Map tile columns |
| `MAP_HEIGHT` | 40 | Map tile rows |
| `TILE_RENDER_SIZE` | 32 | Rendered tile size (px) |
| `FOV_RADIUS` | 6 | Field of view in tiles |
| `MAX_INVENTORY_SLOTS` | 8 | Maximum carried items |
| `MAX_PLAYER_LEVEL` | 20 | Level cap |
| `TOTAL_FLOORS` | 10 | Dungeon depth |
| `TOTAL_SHARDS` | 7 | Shards to collect (floors 4–10) |
| `SHRINE_FLOORS` | {2,4,6,8} | Floors with shrines |
| `SHARD_FLOORS` | {4–10} | Floors with a shard |
| `XP_PER_LEVEL_BASE` | 50 | Level N costs N×50 XP |

### TileType Symbols

| Symbol | Meaning |
|--------|---------|
| `#` | Wall |
| `.` | Floor |
| `>` | Stairs (descend) |
| `Ω` | Shrine |
| `+` | Locked door |
