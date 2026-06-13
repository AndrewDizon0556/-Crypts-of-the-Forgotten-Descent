"""Main game loop and state manager."""
from __future__ import annotations

import random
from enum import Enum, auto

import pygame

from config import FPS, BG_COLOR, SCREEN_WIDTH, SCREEN_HEIGHT, MENU_TEXT, GOLD


class GameState(Enum):
    MAIN_MENU        = auto()
    CHARACTER_SELECT = auto()
    PLAYING          = auto()
    DEATH            = auto()
    VICTORY          = auto()
    LEADERBOARD      = auto()


class Game:
    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock) -> None:
        self.screen  = screen
        self.clock   = clock
        self.state   = GameState.MAIN_MENU
        self.running = True

        from ui.menus import MainMenu, CharacterSelectMenu, DeathScreen, VictoryScreen
        self.main_menu    = MainMenu(screen)
        self.char_select  = CharacterSelectMenu(screen)
        self.death_screen = DeathScreen(screen)
        self.vic_screen   = VictoryScreen(screen)

        # Session state — populated by _start_new_game
        self.player         = None
        self.dungeon        = None
        self.renderer       = None
        self.hud            = None
        self.inv_ui         = None
        self.shrine_ui      = None
        self.minimap        = None
        self.current_floor: int  = 1
        self.dungeon_seed:  int  = 0
        self.session_stats: dict = {}
        self.visible_tiles: set  = set()
        self.explored_tiles: set = set()
        # Overlay flags (do not require a separate GameState)
        self.inventory_open: bool  = False
        self.shrine_active:  bool  = False
        self.show_minimap:   bool  = False
        self.shrine_pos:     tuple = (0, 0)
        # Score for end screens
        self._final_score:   int   = 0
        # Item waiting to be picked up when inventory was full
        self._pending_pickup        = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        while self.running:
            self.clock.tick(FPS)
            events = pygame.event.get()
            self._handle_global_quit(events)
            if not self.running:
                break
            self._update(events)
            self._render()
            pygame.display.flip()

    # ------------------------------------------------------------------
    # Update dispatch
    # ------------------------------------------------------------------

    def _handle_global_quit(self, events: list) -> None:
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False

    def _update(self, events: list) -> None:
        match self.state:
            case GameState.MAIN_MENU:
                result = self.main_menu.update(events)
                if result == "new_game":
                    self.state = GameState.CHARACTER_SELECT
                elif result == "continue":
                    self._handle_continue()
                elif result == "leaderboard":
                    self.state = GameState.LEADERBOARD
                elif result == "quit":
                    self.running = False

            case GameState.CHARACTER_SELECT:
                result = self.char_select.update(events)
                if result in ("warrior", "rogue", "mage"):
                    self._start_new_game(result)
                elif result == "back":
                    self.state = GameState.MAIN_MENU

            case GameState.PLAYING:
                self._update_playing(events)

            case GameState.DEATH | GameState.VICTORY:
                for e in events:
                    if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                        self.state = GameState.MAIN_MENU

            case GameState.LEADERBOARD:
                for e in events:
                    if e.type == pygame.KEYDOWN and e.key in (
                        pygame.K_ESCAPE, pygame.K_RETURN
                    ):
                        self.state = GameState.MAIN_MENU

    # ------------------------------------------------------------------
    # Render dispatch
    # ------------------------------------------------------------------

    def _render(self) -> None:
        self.screen.fill(BG_COLOR)
        match self.state:
            case GameState.MAIN_MENU:
                self.main_menu.render()
            case GameState.CHARACTER_SELECT:
                self.char_select.render()
            case GameState.PLAYING:
                self._render_playing()
            case GameState.DEATH:
                self.death_screen.render(self._death_stats())
            case GameState.VICTORY:
                self.vic_screen.render(self._victory_stats())
            case GameState.LEADERBOARD:
                self._render_leaderboard()

    # ==================================================================
    # PLAYING STATE — update pipeline
    # ==================================================================

    def _update_playing(self, events: list) -> None:
        # Inventory overlay — browsing / equipping does not consume a turn
        if self.inventory_open:
            result = self.inv_ui.update(events, self.player.inventory)
            if result:
                self._handle_inventory_result(result)
            return

        # Shrine overlay — blocks all movement until player chooses a boon
        if self.shrine_active:
            result = self.shrine_ui.update(events)
            if result:
                self._handle_shrine_result(result)
            return

        player_acted = self._handle_playing_input(events)
        if not player_acted:
            return
        self._tick_player_statuses()
        self._update_fov()
        self._process_enemy_turns()
        self._tick_enemy_statuses()
        self._check_conditions()
        self.session_stats["turns_survived"] += 1

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def _handle_playing_input(self, events: list) -> bool:
        """Return True if the player consumed a turn."""
        # Slow/stun — player loses this turn
        if self.player.has_status("slow"):
            self.hud.add_message("You are STUNNED — turn lost!", (220, 180, 60))
            return True

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            k = event.key
            if k == pygame.K_ESCAPE:
                self.state = GameState.MAIN_MENU
                return False
            elif k in (pygame.K_UP, pygame.K_w):
                return self._try_move(0, -1)
            elif k in (pygame.K_DOWN, pygame.K_s):
                return self._try_move(0, 1)
            elif k in (pygame.K_LEFT, pygame.K_a):
                return self._try_move(-1, 0)
            elif k in (pygame.K_RIGHT, pygame.K_d):
                return self._try_move(1, 0)
            elif k == pygame.K_SPACE:
                healed = self.player.heal(1)
                if healed:
                    self.hud.add_message("You rest (+1 HP).", MENU_TEXT)
                return True
            elif k == pygame.K_i:
                if self.player.inventory:
                    self.inventory_open = True
                    self.inv_ui.selected = 0
                else:
                    self.hud.add_message("Inventory is empty.", MENU_TEXT)
                return False
            elif k == pygame.K_m:
                self.show_minimap = not self.show_minimap
                return False
        return False

    # ------------------------------------------------------------------
    # Player action — move / attack / pickup / stairs
    # ------------------------------------------------------------------

    def _try_move(self, dx: int, dy: int) -> bool:
        """
        Attempt a one-tile move. Returns True if a turn was consumed.
        Moving into a wall is free (no turn spent).
        Moving into an enemy triggers melee combat.
        """
        p  = self.player
        nx = p.x + dx
        ny = p.y + dy

        # Locked door — check before walkable (DOOR is not walkable)
        from systems.dungeon import TileType as _TT
        if self.dungeon.get_tile(nx, ny) == _TT.DOOR:
            key_item = next((it for it in self.player.inventory if it.is_key), None)
            if key_item:
                self.player.inventory.remove(key_item)
                self.dungeon.set_tile(nx, ny, _TT.FLOOR)
                self.hud.add_message("You use the Dungeon Key — the door swings open!", GOLD)
                return True   # unlocking costs a turn
            self.hud.add_message("Locked door! You need a Dungeon Key.", (220, 160, 60))
            return False

        if not self.dungeon.is_walkable(nx, ny):
            return False   # wall — no turn cost

        # Bump-to-attack
        target = self._enemy_at(nx, ny)
        if target:
            self._do_player_attack(target)
            return True

        # Move
        p.x, p.y = nx, ny

        # Item on tile
        item = self._item_at(nx, ny)
        if item:
            self._pick_up(item)

        # Check tile type after landing
        from systems.dungeon import TileType
        tile = self.dungeon.get_tile(nx, ny)
        if tile == TileType.STAIRS:
            self._descend()
        elif tile == TileType.SHRINE:
            self._trigger_shrine(nx, ny)

        return True

    def _do_player_attack(self, target) -> None:
        from systems.combat import player_attack
        p      = self.player
        result = player_attack(p, target)

        # Visual effects
        self.renderer.emit_damage_dealt(target, result["damage"], crit=result["is_crit"])

        msg = f"You hit {target.name} for {result['damage']}"
        if result["is_crit"]:
            msg += " (CRIT!)"
        self.hud.add_message(msg + ".", (220, 160, 160))

        if result["killed"]:
            self.hud.add_message(
                f"{target.name} slain! +{target.xp_reward} XP  +{target.gold_reward} G",
                (140, 220, 140),
            )
            leveled = p.gain_xp(target.xp_reward)
            p.gold += target.gold_reward
            self.session_stats["enemies_killed"] += 1
            self.session_stats["gold_collected"] += target.gold_reward
            if leveled:
                self.hud.add_message(
                    f"LEVEL UP! LVL {p.level}  +10 HP  +2 ATK  +1 DEF", GOLD
                )
                self.renderer.emit_level_up(p)
            # Rogue: backstab resets for the next enemy
            if p.character_class == "rogue":
                p.backstab_ready = True

    def _pick_up(self, item) -> None:
        from systems.inventory import use_item
        p = self.player

        if item.is_shard:
            p.add_to_inventory(item)
            self.dungeon.items.remove(item)
            self.session_stats["shards_found"] += 1
            self.hud.add_message(f"Shard of Ethos obtained! ({self.session_stats['shards_found']}/7)", (80, 220, 220))
            self.renderer.emit_pickup(item, p.x, p.y)
            return

        if item.item_type in ("weapon", "armor"):
            result = use_item(p, item)
            self.dungeon.items.remove(item)
            self.hud.add_message(result, (160, 190, 220))
        elif item.item_type == "consumable":
            if p.add_to_inventory(item):
                self.dungeon.items.remove(item)
                self.hud.add_message(f"Picked up {item.name}.", MENU_TEXT)
            else:
                self._pending_pickup = item
                self.inventory_open  = True
                self.inv_ui.selected = 0
                self.hud.add_message(
                    f"Inventory full! Drop an item to pick up {item.name}.", (220, 140, 60)
                )
        elif item.item_type == "key":
            p.add_to_inventory(item)
            self.dungeon.items.remove(item)
            self.hud.add_message("You found a Dungeon Key.", (220, 200, 60))

    # ------------------------------------------------------------------
    # Enemy turns
    # ------------------------------------------------------------------

    def _process_enemy_turns(self) -> None:
        from systems.ai import update_enemy_ai
        from systems.combat import enemy_attack
        from entities.boss import HollowWarden

        occupied = {(e.x, e.y) for e in self.dungeon.enemies if e.alive}
        occupied.add(self.player.pos)

        for enemy in list(self.dungeon.enemies):
            if not enemy.alive:
                continue

            # Enemies can also be slowed (e.g., future items)
            if enemy.has_status("slow"):
                continue

            if isinstance(enemy, HollowWarden):
                self._run_boss_turn(enemy, occupied)
            else:
                action = update_enemy_ai(
                    enemy, self.player, self.dungeon, occupied, self.visible_tiles
                )
                if not action:
                    continue

                if "move" in action:
                    dest = action["move"]
                    if dest not in occupied:
                        occupied.discard(enemy.pos)
                        enemy.x, enemy.y = dest
                        occupied.add(dest)

                elif action.get("attack"):
                    result = enemy_attack(enemy, self.player)
                    self._report_enemy_attack(enemy, result)

    # ------------------------------------------------------------------
    # Status ticks
    # ------------------------------------------------------------------

    def _tick_player_statuses(self) -> None:
        from systems.combat import apply_status_damage
        dmg = apply_status_damage(self.player)
        if dmg:
            self.hud.add_message(f"Status damage: -{dmg} HP.", (220, 120, 60))
        for name in self.player.tick_statuses():
            self.hud.add_message(f"{name.upper()} has worn off.", (160, 210, 160))

    def _tick_enemy_statuses(self) -> None:
        from systems.combat import apply_status_damage
        for e in self.dungeon.enemies:
            if e.alive:
                apply_status_damage(e)
                e.tick_statuses()
        self.dungeon.enemies = [e for e in self.dungeon.enemies if e.alive]

    # ------------------------------------------------------------------
    # FOV
    # ------------------------------------------------------------------

    def _update_fov(self) -> None:
        from systems.fov import compute_fov
        self.visible_tiles = compute_fov(self.dungeon, self.player.x, self.player.y)
        self.explored_tiles.update(self.visible_tiles)

    # ------------------------------------------------------------------
    # Win / lose
    # ------------------------------------------------------------------

    def _check_conditions(self) -> None:
        if not self.player.alive:
            # Shard Echo: survive one death at 1 HP
            if self.player.shard_echo:
                self.player.hp    = 1
                self.player.alive = True
                self.player.shard_echo = False
                self.hud.add_message("SHARD ECHO activates — you survive at 1 HP!", (80, 220, 220))
                return
            self._end_run(victory=False)
            return

        # Victory: boss dead (flagged in session_stats)
        if self.session_stats.get("victory"):
            self._end_run(victory=True)

    def _end_run(self, victory: bool) -> None:
        from systems.save import delete_save
        from systems.score import calculate_score, save_score
        delete_save()
        self._final_score = calculate_score(self.session_stats, victory=victory)
        try:
            save_score(
                name=self.player.character_class.title(),
                score=self._final_score,
                character_class=self.player.character_class,
                floors=self.session_stats.get("floors_reached", 1),
            )
        except Exception:
            pass
        self.state = GameState.VICTORY if victory else GameState.DEATH

    # ------------------------------------------------------------------
    # Stair descent
    # ------------------------------------------------------------------

    def _descend(self) -> None:
        self.current_floor += 1
        self.session_stats["floors_reached"] = self.current_floor
        self.hud.add_message(
            f"You descend to floor {self.current_floor}.", (180, 140, 220)
        )
        self._generate_floor()
        # Auto-save after each descent
        try:
            from systems.save import save_game
            save_game(self)
        except Exception:
            pass

    # ==================================================================
    # Game initialization
    # ==================================================================

    def _start_new_game(self, character_class: str) -> None:
        import time
        from entities.player import Player
        from ui.renderer import Renderer
        from ui.hud import HUD

        self.dungeon_seed    = int(time.time())
        self.player          = Player.from_class(character_class)
        self.current_floor   = 1
        self.session_stats   = {
            "floors_reached": 1,
            "enemies_killed": 0,
            "gold_collected": 0,
            "shards_found":   0,
            "turns_survived": 0,
            "character_class": character_class,
        }
        self.visible_tiles  = set()
        self.explored_tiles = set()
        from ui.inventory_ui import InventoryUI
        from ui.shrine_ui import ShrineUI
        from ui.minimap import Minimap
        self.renderer  = Renderer(self.screen, character_class=character_class)
        self.renderer.set_character_class(character_class)
        self.hud       = HUD(self.screen)
        self.inv_ui    = InventoryUI(self.screen)
        self.shrine_ui = ShrineUI(self.screen)
        self.minimap   = Minimap(self.screen)
        self.inventory_open  = False
        self.shrine_active   = False
        self.show_minimap    = False
        self._final_score    = 0
        self._pending_pickup = None

        self._give_starting_gear(character_class)
        self._generate_floor()

        self.hud.add_message("You enter the Crypts of the Forgotten Descent.", (180, 140, 220))
        self.hud.add_message("Find the 7 Shards of Ethos. Survive.", MENU_TEXT)
        self.hud.add_message("WASD move | SPACE wait | I inventory | M map | ESC menu", (100, 95, 120))
        self.state = GameState.PLAYING

    def _handle_continue(self) -> None:
        from systems.save import save_exists, load_game
        if not save_exists():
            self.main_menu._no_save_flash = 60
            return
        data = load_game()
        if not data:
            self.main_menu._no_save_flash = 60
            return
        self._restore_game(data)

    def _restore_game(self, data: dict) -> None:
        """Fully reconstruct a saved session from its save dict."""
        from entities.player import Player
        from systems.inventory import build_item
        from ui.renderer import Renderer
        from ui.hud import HUD
        from ui.inventory_ui import InventoryUI
        from ui.shrine_ui import ShrineUI
        from ui.minimap import Minimap

        pd = data["player"]
        cls = pd["class"]

        self.current_floor  = data["floor"]
        self.dungeon_seed   = data["dungeon_seed"]
        self.session_stats  = data.get("stats", {})
        self.visible_tiles  = set()
        self.explored_tiles = set()
        self._final_score   = 0

        # Rebuild player — start from class template to get defaults, then override
        p = Player.from_class(cls)
        p.hp             = pd["hp"]
        p.max_hp         = pd["max_hp"]
        p.atk            = pd["atk"]
        p.defense        = pd["defense"]
        p.level          = pd["level"]
        p.xp             = pd["xp"]
        p.gold           = pd["gold"]
        p.shard_echo     = pd.get("shard_echo", False)
        p.backstab_ready = pd.get("backstab_ready", False)

        # Restore equipped gear (stats already baked into saved atk/defense)
        wpn_key = pd.get("equipped_weapon")
        arm_key = pd.get("equipped_armor")
        if wpn_key:
            p.equipped_weapon = build_item(wpn_key)
        if arm_key:
            p.equipped_armor = build_item(arm_key)

        # Restore inventory
        for key in pd.get("inventory", []):
            item = build_item(key)
            p.inventory.append(item)

        self.player = p

        # Re-init UI
        self.renderer  = Renderer(self.screen, character_class=cls)
        self.renderer.set_character_class(cls)
        self.hud       = HUD(self.screen)
        self.inv_ui    = InventoryUI(self.screen)
        self.shrine_ui = ShrineUI(self.screen)
        self.minimap   = Minimap(self.screen)
        self.inventory_open = False
        self.shrine_active  = False
        self.show_minimap   = False

        self._generate_floor()
        self.hud.add_message(f"Continuing on floor {self.current_floor}.", (180, 140, 220))
        self.hud.add_message("WASD move | SPACE wait | I inventory | M map | ESC menu", (100, 95, 120))
        self.state = GameState.PLAYING

    def _give_starting_gear(self, character_class: str) -> None:
        from systems.inventory import build_item, use_item
        p = self.player
        match character_class:
            case "warrior":
                use_item(p, build_item("iron_sword"))
                use_item(p, build_item("leather_armor"))
                p.add_to_inventory(build_item("health_potion"))
            case "rogue":
                use_item(p, build_item("rusty_sword"))
                p.add_to_inventory(build_item("bomb"))
                p.add_to_inventory(build_item("bomb"))
                p.add_to_inventory(build_item("health_potion"))
                p.add_to_inventory(build_item("health_potion"))
            case "mage":
                p.add_to_inventory(build_item("scroll_of_fire"))
                p.add_to_inventory(build_item("scroll_of_fire"))
                p.add_to_inventory(build_item("mega_potion"))

    def _generate_floor(self) -> None:
        from systems.dungeon import DungeonGenerator
        gen           = DungeonGenerator(seed=self.dungeon_seed + self.current_floor)
        self.dungeon  = gen.generate(self.current_floor)
        px, py        = self.dungeon.spawn_pos
        self.player.x = px
        self.player.y = py
        self.visible_tiles  = set()
        self.explored_tiles = set()
        self._populate_floor()
        self._update_fov()

    def _populate_floor(self) -> None:
        """Place enemies and items on the current floor."""
        from entities.enemy import eligible_enemy_types, create_enemy
        from systems.inventory import build_item

        floor  = self.current_floor
        rng    = random.Random(self.dungeon_seed + floor * 997)
        dungeon = self.dungeon

        occupied: set[tuple[int, int]] = {dungeon.spawn_pos}
        rooms = dungeon.rooms[1:] if len(dungeon.rooms) > 1 else dungeon.rooms

        # --- Enemies ---
        enemy_count = floor * 2 + rng.randint(2, 5)
        etype_pool  = eligible_enemy_types(floor)

        for _ in range(enemy_count):
            room = rng.choice(rooms)
            candidates = [
                (room.x + dx, room.y + dy)
                for dx in range(room.width)
                for dy in range(room.height)
                if dungeon.is_walkable(room.x + dx, room.y + dy)
                and (room.x + dx, room.y + dy) not in occupied
            ]
            if not candidates:
                continue
            ex, ey = rng.choice(candidates)
            enemy  = create_enemy(rng.choice(etype_pool), ex, ey, floor)
            dungeon.enemies.append(enemy)
            occupied.add((ex, ey))

        # --- Items ---
        item_count = rng.randint(3, floor + 4)
        item_pool  = [
            "health_potion", "health_potion", "health_potion",
            "mega_potion", "bomb", "scroll_of_fire", "antidote",
        ]
        if floor >= 3:
            item_pool += ["rusty_sword", "leather_armor"]
        if floor >= 5:
            item_pool += ["iron_sword", "chain_mail"]
        if floor >= 7:
            item_pool += ["shadow_blade", "obsidian_plate"]

        floor_tiles = [
            t for t in dungeon.floor_tiles()
            if t not in occupied and t != dungeon.stairs_pos
        ]
        for _ in range(item_count):
            if not floor_tiles:
                break
            pos = rng.choice(floor_tiles)
            floor_tiles.remove(pos)
            item = build_item(rng.choice(item_pool), pos[0], pos[1])
            dungeon.items.append(item)
            occupied.add(pos)

        # --- Shrine (floors 2, 4, 6, 8) ---
        from config import SHRINE_FLOORS, SHARD_FLOORS
        from systems.dungeon import TileType

        if floor in SHRINE_FLOORS:
            far = sorted(
                [t for t in floor_tiles if t not in occupied],
                key=lambda t: abs(t[0] - dungeon.spawn_pos[0]) + abs(t[1] - dungeon.spawn_pos[1]),
                reverse=True,
            )
            if far:
                sx, sy = far[0]
                dungeon.set_tile(sx, sy, TileType.SHRINE)
                dungeon.shrines.append((sx, sy))
                occupied.add((sx, sy))

        # --- Shard of Ethos (floors 4–10) ---
        if floor in SHARD_FLOORS:
            far = sorted(
                [t for t in floor_tiles if t not in occupied],
                key=lambda t: abs(t[0] - dungeon.spawn_pos[0]) + abs(t[1] - dungeon.spawn_pos[1]),
                reverse=True,
            )
            if far:
                sx, sy = far[0]
                shard = build_item("shard_of_ethos", sx, sy)
                dungeon.items.append(shard)
                occupied.add((sx, sy))

        # --- Locked room with Dungeon Key (floors 3+) ---
        if floor >= 3 and len(dungeon.rooms) > 2:
            # All room tiles combined (for corridor detection)
            all_room_tiles: set[tuple[int, int]] = set()
            for r in dungeon.rooms:
                all_room_tiles.update(r.inner_tiles)

            # Pick a room that doesn't contain spawn or stairs
            def _has_pos(room, pos):
                return pos is not None and room.contains(*pos)

            candidates = [
                r for r in dungeon.rooms
                if not _has_pos(r, dungeon.spawn_pos)
                and not _has_pos(r, dungeon.stairs_pos)
            ]
            if candidates:
                locked_room = rng.choice(candidates)
                locked_tiles = set(locked_room.inner_tiles)

                # Corridor tiles just outside the locked room (not part of any room)
                door_positions: set[tuple[int, int]] = set()
                for rx, ry in locked_tiles:
                    for ndx, ndy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx2, ny2 = rx + ndx, ry + ndy
                        if (nx2, ny2) not in all_room_tiles:
                            if dungeon.get_tile(nx2, ny2) == TileType.FLOOR:
                                door_positions.add((nx2, ny2))

                if door_positions:
                    for dp in door_positions:
                        dungeon.set_tile(*dp, TileType.DOOR)

                    # Place dungeon key outside the locked room
                    key_candidates = [
                        t for r in dungeon.rooms
                        if r is not locked_room
                        for t in r.inner_tiles
                        if t not in occupied
                    ]
                    if key_candidates:
                        kx, ky = rng.choice(key_candidates)
                        key_item = build_item("dungeon_key", kx, ky)
                        dungeon.items.append(key_item)
                        occupied.add((kx, ky))

        # --- Hollow Warden boss (floor 10 only) ---
        if floor == 10:
            from entities.boss import create_hollow_warden
            far = sorted(
                [t for t in floor_tiles if t not in occupied],
                key=lambda t: abs(t[0] - dungeon.spawn_pos[0]) + abs(t[1] - dungeon.spawn_pos[1]),
                reverse=True,
            )
            if far:
                bx, by = far[0]
                boss = create_hollow_warden(bx, by)
                dungeon.enemies.append(boss)
                occupied.add((bx, by))
            self.hud.add_message("A dreadful presence fills the Crypts...", (220, 60, 60))
            self.hud.add_message("THE HOLLOW WARDEN AWAKENS.", (220, 60, 60))

    # ==================================================================
    # Inventory handling
    # ==================================================================

    def _handle_inventory_result(self, result: tuple) -> None:
        action = result[0]
        if action == "close":
            self.inventory_open = False
            return
        if action == "use":
            idx = result[1]
            if idx < len(self.player.inventory):
                self._execute_item_use(idx)
            self.inventory_open = False
        elif action == "drop":
            idx = result[1]
            if idx < len(self.player.inventory):
                dropped = self.player.inventory.pop(idx)
                dropped.x, dropped.y = self.player.x, self.player.y
                self.dungeon.items.append(dropped)
                self.hud.add_message(f"Dropped {dropped.name}.", MENU_TEXT)
            # If there's a pending pickup, grab it now that space exists
            if self._pending_pickup:
                p = self._pending_pickup
                if self.player.add_to_inventory(p):
                    if p in self.dungeon.items:
                        self.dungeon.items.remove(p)
                    self.hud.add_message(f"Picked up {p.name}.", MENU_TEXT)
                self._pending_pickup = None
            self.inventory_open = False

    def _execute_item_use(self, idx: int) -> None:
        """Apply item at inventory index, handle AoE side-effects, remove if consumable."""
        from systems.inventory import use_item
        p    = self.player
        item = p.inventory[idx]

        if item.item_type in ("weapon", "armor"):
            p.inventory.pop(idx)          # remove from bag before equipping
            result = use_item(p, item)    # _equip may add old gear to bag
            self.hud.add_message(result, (160, 190, 220))
            return   # equipping is free (no turn consumed)

        # Consumable
        result = use_item(p, item)
        p.inventory.pop(idx)

        if result.startswith("FIRE_SCROLL:"):
            base_dmg = int(result.split(":")[1])
            dmg = int(base_dmg * 1.5) if p.character_class == "mage" else base_dmg
            from systems.combat import aoe_fire_scroll_damage
            hits = aoe_fire_scroll_damage(self.dungeon.enemies, dmg)
            self._resolve_aoe_kills(hits)
            self.hud.add_message(
                f"Fire erupts! {dmg} dmg x {len(hits)} enemies.", (220, 160, 60)
            )
            # Consume a turn after fire scroll
            self._tick_player_statuses()
            self._update_fov()
            self._process_enemy_turns()
            self._tick_enemy_statuses()
            self._check_conditions()
            self.session_stats["turns_survived"] += 1
        elif result.startswith("BOMB:"):
            from systems.combat import aoe_bomb_damage
            hits = aoe_bomb_damage(p, self.dungeon.enemies)
            self._resolve_aoe_kills(hits)
            self.hud.add_message(
                f"BOOM! {sum(h['damage'] for h in hits)} dmg to {len(hits)} targets.",
                (220, 180, 80),
            )
            self._tick_player_statuses()
            self._update_fov()
            self._process_enemy_turns()
            self._tick_enemy_statuses()
            self._check_conditions()
            self.session_stats["turns_survived"] += 1
        else:
            self.hud.add_message(result, (160, 220, 160))

    def _resolve_aoe_kills(self, hits: list) -> None:
        for h in hits:
            if h["killed"]:
                e = h["enemy"]
                self.hud.add_message(
                    f"{e.name} slain! +{e.xp_reward} XP  +{e.gold_reward} G",
                    (140, 220, 140),
                )
                leveled = self.player.gain_xp(e.xp_reward)
                self.player.gold += e.gold_reward
                self.session_stats["enemies_killed"] += 1
                self.session_stats["gold_collected"] += e.gold_reward
                if leveled:
                    self.hud.add_message(
                        f"LEVEL UP! LVL {self.player.level}  +10 HP  +2 ATK  +1 DEF", GOLD
                    )

    # ==================================================================
    # Shrine handling
    # ==================================================================

    def _trigger_shrine(self, x: int, y: int) -> None:
        """Open the shrine boon selection UI and mark the tile as active."""
        import random as _rng_mod
        self.shrine_pos    = (x, y)
        self.shrine_active = True
        rng = _rng_mod.Random(self.dungeon_seed + self.current_floor * 13 + x * 7 + y)
        self.shrine_ui.roll(self.current_floor, rng)
        self.hud.add_message("An ancient shrine pulses with power...", (160, 100, 210))

    def _handle_shrine_result(self, result: tuple) -> None:
        action = result[0]
        self.shrine_active = False

        if action == "close":
            self.hud.add_message("You leave the shrine untouched.", MENU_TEXT)
            return

        # action == "boon"
        key = result[1]
        p   = self.player
        match key:
            case "heal":
                p.hp = p.max_hp
                self.hud.add_message("Divine Mend: HP fully restored!", (160, 220, 160))
            case "atk":
                p.atk += 3
                self.hud.add_message("Warbrand: +3 ATK permanently.", (220, 140, 140))
            case "def":
                p.defense += 2
                self.hud.add_message("Stone Skin: +2 DEF permanently.", (140, 160, 220))
            case "curse":
                p.status_effects.clear()
                self.hud.add_message("Cleansing Light: all statuses removed.", (200, 200, 140))
            case "gold":
                p.gold += 25
                self.hud.add_message("Gold Bless: +25 GOLD.", GOLD)
            case "xp":
                leveled = p.gain_xp(75)
                self.hud.add_message("XP Surge: +75 XP!", (120, 180, 220))
                if leveled:
                    self.hud.add_message(
                        f"LEVEL UP! LVL {p.level}  +10 HP  +2 ATK  +1 DEF", GOLD
                    )
            case "echo":
                p.shard_echo = True
                self.hud.add_message("Shard Echo: you will survive one death.", (80, 220, 220))

        # Consume the shrine tile (becomes floor so player can walk away freely)
        from systems.dungeon import TileType
        self.dungeon.set_tile(*self.shrine_pos, TileType.FLOOR)
        if self.shrine_pos in self.dungeon.shrines:
            self.dungeon.shrines.remove(self.shrine_pos)

    # ==================================================================
    # Boss helpers
    # ==================================================================

    def _run_boss_turn(self, boss, occupied: set) -> None:
        from systems.ai import update_enemy_ai
        from systems.combat import enemy_attack
        from entities.boss import BossPhase

        # Phase transition check
        if boss.update_phase():
            msgs = {
                BossPhase.PHASE_2: "The Warden accelerates — bleeding aura unleashed!",
                BossPhase.PHASE_3: "The Warden RAGES — unstoppable power!",
            }
            if boss.phase in msgs:
                self.hud.add_message(msgs[boss.phase], (220, 60, 60))

        # Summon on interval
        boss.summon_timer += 1
        if boss.summon_timer >= boss.summon_interval:
            self._spawn_boss_summon(boss, occupied)
            boss.summon_timer = 0

        # Double speed in Phase 2: move twice, but only attack once
        steps = boss.move_speed
        attacked = False
        for _ in range(steps):
            action = update_enemy_ai(boss, self.player, self.dungeon, occupied, self.visible_tiles)
            if not action:
                break
            if "move" in action:
                dest = action["move"]
                if dest not in occupied:
                    occupied.discard(boss.pos)
                    boss.x, boss.y = dest
                    occupied.add(dest)
            elif action.get("attack") and not attacked:
                result = enemy_attack(boss, self.player)
                self._report_enemy_attack(boss, result)
                # AoE slam (Phase 3 every 3rd attack)
                if result["special"] == "AOE_SLAM":
                    splash = 15
                    self.player.take_damage(splash)
                    self.hud.add_message(
                        f"THE WARDEN SLAMS — {splash} extra AoE damage!", (220, 60, 60)
                    )
                    self.renderer.emit_boss_slam(self.player)
                attacked = True
                break  # one attack per turn regardless of move_speed

        # Victory when boss dies
        if not boss.alive:
            self.session_stats["victory"] = True
            self.hud.add_message("THE HOLLOW WARDEN HAS FALLEN!", GOLD)
            self.hud.add_message("You escape the Crypts with all 7 Shards!", (200, 200, 80))

    def _report_enemy_attack(self, enemy, result: dict) -> None:
        msg = f"{enemy.name} hits you for {result['damage']}"
        special = result.get("special")
        if special and special != "AOE_SLAM":
            msg += f"  [{special}]"
        self.hud.add_message(msg + ".", (220, 100, 100))
        self.renderer.emit_damage_taken(self.player, result["damage"])

    def _spawn_boss_summon(self, boss, occupied: set) -> None:
        from entities.enemy import create_enemy
        # Find adjacent free tile
        candidates = [
            (boss.x + dx, boss.y + dy)
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1))
            if self.dungeon.is_walkable(boss.x + dx, boss.y + dy)
            and (boss.x + dx, boss.y + dy) not in occupied
        ]
        if not candidates:
            return
        sx, sy = candidates[0]
        minion = create_enemy(boss.summon_type, sx, sy, self.current_floor)
        self.dungeon.enemies.append(minion)
        occupied.add((sx, sy))
        self.hud.add_message(
            f"The Warden summons a {minion.name}!", (220, 80, 80)
        )

    # ==================================================================
    # Helpers
    # ==================================================================

    def _enemy_at(self, x: int, y: int):
        for e in self.dungeon.enemies:
            if e.alive and e.x == x and e.y == y:
                return e
        return None

    def _item_at(self, x: int, y: int):
        for item in self.dungeon.items:
            if item.x == x and item.y == y:
                return item
        return None

    def _death_stats(self) -> dict:
        s = self.session_stats
        return {
            "Class":  s.get("character_class", "?").title(),
            "Floor":  s.get("floors_reached", 1),
            "Kills":  s.get("enemies_killed", 0),
            "Gold":   s.get("gold_collected", 0),
            "Shards": s.get("shards_found", 0),
            "Turns":  s.get("turns_survived", 0),
            "Score":  self._final_score,
        }

    def _victory_stats(self) -> dict:
        return self._death_stats()

    # ==================================================================
    # Render helpers
    # ==================================================================

    def _render_playing(self) -> None:
        self.renderer.render_frame(
            self.dungeon,
            self.player,
            self.dungeon.enemies,
            self.dungeon.items,
            self.visible_tiles,
            self.explored_tiles,
        )
        self.hud.render(
            self.player,
            self.current_floor,
            shards=self.session_stats.get("shards_found", 0),
        )
        if self.show_minimap:
            self.minimap.render(self.dungeon, self.player, self.explored_tiles)
        if self.inventory_open:
            self.inv_ui.render(self.player)
        if self.shrine_active:
            self.shrine_ui.render()

    def _render_leaderboard(self) -> None:
        from systems.score import get_top_scores
        font_h = pygame.font.SysFont("monospace", 30, bold=True)
        font   = pygame.font.SysFont("monospace", 20)
        y = 80
        surf = font_h.render("LEADERBOARD", True, GOLD)
        self.screen.blit(surf, surf.get_rect(centerx=SCREEN_WIDTH // 2, top=y))
        y += 60
        try:
            scores = get_top_scores()
        except Exception:
            scores = []
        if not scores:
            s = font.render("No scores yet — complete a run!", True, (150, 140, 170))
            self.screen.blit(s, s.get_rect(centerx=SCREEN_WIDTH // 2, top=y))
        else:
            hdr = f"{'Rank':<6}{'Name':<16}{'Class':<12}{'Score':>8}  {'Floors':>6}  Date"
            self.screen.blit(font.render(hdr, True, (180, 140, 220)), (120, y))
            y += 30
            for s in scores:
                row = (
                    f"{s['rank']:<6}{s['name']:<16}{s['class']:<12}"
                    f"{s['score']:>8}  {s['floors']:>6}  {s['date']}"
                )
                self.screen.blit(font.render(row, True, (200, 190, 220)), (120, y))
                y += 26
        y += 30
        hint = font.render("Press ENTER or ESC to return", True, (100, 90, 120))
        self.screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, top=y))
