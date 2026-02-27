"""Main game engine: state management, exploration, UI, save/load."""

import os
import json
import math
import random
import pygame
from src.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, TILE_SIZE,
    BLACK, WHITE, RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, CYAN, GOLD,
    DARK_GRAY, GRAY, LIGHT_GRAY, BROWN, DARK_GREEN, DARK_BLUE,
    UI_BG, UI_BORDER, UI_TEXT, UI_ACCENT, UI_HIGHLIGHT,
    HP_BAR_COLOR, MP_BAR_COLOR, XP_BAR_COLOR,
    STATE_MAIN_MENU, STATE_CHARACTER_CREATE, STATE_EXPLORE, STATE_COMBAT,
    STATE_INVENTORY, STATE_DIALOGUE, STATE_QUEST_LOG, STATE_GAME_OVER,
    STATE_LEVEL_UP, STATE_SHOP, STATE_PAUSE,
    CLASS_WARRIOR, CLASS_MAGE, CLASS_ROGUE, CLASS_RANGER, CLASS_PALADIN,
    SLOT_WEAPON, SLOT_ARMOR, SLOT_HELMET, SLOT_BOOTS, SLOT_ACCESSORY,
    RARITY_COLORS, RARITY_COMMON,
    PLAYER_SPEED, CAMERA_LERP,
)
from src.utils import (
    draw_text, draw_panel, draw_bar, draw_tooltip, wrap_text,
    clamp, lerp, SpriteSheet, get_rarity_color
)
from src.particles import ParticleSystem
from src.entities import Player, CLASS_DATA, generate_encounter
from src.items import Item, create_health_potion, create_mana_potion, create_rusty_sword, create_leather_armor
from src.maps import load_map, TILE_PROPERTIES, TileMap
from src.combat import CombatSystem
from src.quests import Quest


class Camera:
    """Smooth-following camera."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0

    def update(self, target_x, target_y, map_width, map_height, dt):
        """Smoothly follow target."""
        self.target_x = target_x - SCREEN_WIDTH // 2
        self.target_y = target_y - SCREEN_HEIGHT // 2

        # Clamp to map bounds
        max_x = map_width * TILE_SIZE - SCREEN_WIDTH
        max_y = map_height * TILE_SIZE - SCREEN_HEIGHT
        self.target_x = clamp(self.target_x, 0, max(0, max_x))
        self.target_y = clamp(self.target_y, 0, max(0, max_y))

        # Smooth interpolation
        speed = min(1.0, CAMERA_LERP * dt * 60)
        self.x = lerp(self.x, self.target_x, speed)
        self.y = lerp(self.y, self.target_y, speed)

    def apply(self, x, y):
        """Convert world coords to screen coords."""
        return x - int(self.x), y - int(self.y)


class Game:
    """Main game class."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        # Fonts
        self.fonts = {
            "tiny": pygame.font.Font(None, 18),
            "small": pygame.font.Font(None, 24),
            "medium": pygame.font.Font(None, 32),
            "large": pygame.font.Font(None, 42),
            "title": pygame.font.Font(None, 64),
            "huge": pygame.font.Font(None, 80),
        }

        # State
        self.state = STATE_MAIN_MENU
        self.prev_state = None
        self.player = None
        self.current_map = None
        self.camera = Camera()
        self.particles = ParticleSystem()
        self.combat_system = None

        # Input timing
        self.move_cooldown = 0
        self.move_delay = 0.12  # seconds between moves

        # Random encounter
        self.steps_since_encounter = 0
        self.encounter_rate = 15  # steps before encounter check

        # UI state
        self.menu_selection = 0
        self.class_selection = 0
        self.name_input = ""
        self.name_input_active = True
        self.dialogue_lines = []
        self.dialogue_index = 0
        self.dialogue_npc = None
        self.inventory_selection = 0
        self.inventory_tab = 0  # 0=items, 1=equipment
        self.shop_items = []
        self.shop_selection = 0
        self.shop_mode = "buy"  # buy or sell
        self.quest_selection = 0
        self.notification_text = ""
        self.notification_timer = 0
        self.level_up_gains = None

        # Tile cache
        self.tile_cache = {}

        # Title animation
        self.title_timer = 0

        # Pre-generate tile sprites
        self._init_tile_cache()

    def _init_tile_cache(self):
        """Pre-generate tile sprites."""
        for tile_id, props in TILE_PROPERTIES.items():
            self.tile_cache[tile_id] = SpriteSheet.create_tile_sprite(
                props["color"], TILE_SIZE, props["tile_type"])

    def show_notification(self, text, duration=3.0):
        """Show a notification message."""
        self.notification_text = text
        self.notification_timer = duration

    def change_state(self, new_state):
        """Change game state."""
        self.prev_state = self.state
        self.state = new_state

    def start_new_game(self, name, char_class):
        """Initialize a new game."""
        self.player = Player(name, char_class)

        # Give starter items
        starter_weapon = create_rusty_sword()
        starter_armor = create_leather_armor()
        self.player.equip_item(starter_weapon)
        self.player.equip_item(starter_armor)
        for _ in range(3):
            self.player.add_item(create_health_potion())
        self.player.add_item(create_mana_potion())

        self.current_map = load_map("village")
        self.player.tile_x = self.current_map.spawn_x
        self.player.tile_y = self.current_map.spawn_y
        self.player.pixel_x = self.player.tile_x * TILE_SIZE
        self.player.pixel_y = self.player.tile_y * TILE_SIZE
        self.player.current_map = "village"

        # Center camera immediately
        self.camera.x = self.player.pixel_x - SCREEN_WIDTH // 2
        self.camera.y = self.player.pixel_y - SCREEN_HEIGHT // 2

        self.change_state(STATE_EXPLORE)
        self.show_notification(f"Welcome to Realms of Mythos, {name}!")

    def transition_map(self, target_map, target_x, target_y):
        """Transition to a new map."""
        self.current_map = load_map(target_map)
        self.player.tile_x = target_x
        self.player.tile_y = target_y
        self.player.pixel_x = target_x * TILE_SIZE
        self.player.pixel_y = target_y * TILE_SIZE
        self.player.current_map = target_map
        self.camera.x = self.player.pixel_x - SCREEN_WIDTH // 2
        self.camera.y = self.player.pixel_y - SCREEN_HEIGHT // 2
        self.steps_since_encounter = 0
        self.show_notification(f"Entering: {self.current_map.name}")

    def start_combat(self, enemies):
        """Start a combat encounter."""
        self.combat_system = CombatSystem(self.player, enemies, self.fonts)
        self.change_state(STATE_COMBAT)

    def start_dialogue(self, npc):
        """Start dialogue with an NPC."""
        self.dialogue_npc = npc
        self.dialogue_lines = npc.dialogue
        self.dialogue_index = 0
        self.change_state(STATE_DIALOGUE)

    def check_random_encounter(self):
        """Check for random encounter on the map."""
        if not self.current_map or not self.current_map.encounter_area:
            return
        area = self.current_map.get_encounter_area(self.player.tile_x, self.player.tile_y)
        if not area:
            return

        self.steps_since_encounter += 1
        if self.steps_since_encounter >= self.encounter_rate:
            if random.random() < 0.25:
                self.steps_since_encounter = 0
                enemies = generate_encounter(area, self.player.level)
                if enemies:
                    enemy_names = ", ".join(e.name for e in enemies)
                    self.show_notification(f"Encountered: {enemy_names}!")
                    self.start_combat(enemies)

    # ─── Main Loop ──────────────────────────────────────────────

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # Cap delta time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self.handle_event(event)

            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()

    def handle_event(self, event):
        """Route events to current state handler."""
        handlers = {
            STATE_MAIN_MENU: self._handle_main_menu,
            STATE_CHARACTER_CREATE: self._handle_character_create,
            STATE_EXPLORE: self._handle_explore_event,
            STATE_COMBAT: self._handle_combat,
            STATE_INVENTORY: self._handle_inventory,
            STATE_DIALOGUE: self._handle_dialogue,
            STATE_QUEST_LOG: self._handle_quest_log,
            STATE_GAME_OVER: self._handle_game_over,
            STATE_SHOP: self._handle_shop,
            STATE_PAUSE: self._handle_pause,
            STATE_LEVEL_UP: self._handle_level_up,
        }
        handler = handlers.get(self.state)
        if handler:
            handler(event)

    def update(self, dt):
        """Update current state."""
        self.title_timer += dt
        self.particles.update(dt)

        if self.notification_timer > 0:
            self.notification_timer -= dt

        if self.state == STATE_EXPLORE:
            self._update_explore(dt)
        elif self.state == STATE_COMBAT:
            if self.combat_system:
                self.combat_system.update(dt)

    def draw(self):
        """Draw current state."""
        self.screen.fill(BLACK)

        drawers = {
            STATE_MAIN_MENU: self._draw_main_menu,
            STATE_CHARACTER_CREATE: self._draw_character_create,
            STATE_EXPLORE: self._draw_explore,
            STATE_COMBAT: self._draw_combat,
            STATE_INVENTORY: self._draw_inventory,
            STATE_DIALOGUE: self._draw_dialogue,
            STATE_QUEST_LOG: self._draw_quest_log,
            STATE_GAME_OVER: self._draw_game_over,
            STATE_SHOP: self._draw_shop,
            STATE_PAUSE: self._draw_pause,
            STATE_LEVEL_UP: self._draw_level_up,
        }
        drawer = drawers.get(self.state)
        if drawer:
            drawer()

        # Draw notification
        if self.notification_timer > 0:
            self._draw_notification()

    # ─── Main Menu ──────────────────────────────────────────────

    def _handle_main_menu(self, event):
        if event.type != pygame.KEYDOWN:
            return
        options = ["New Game", "Load Game", "Quit"]
        if event.key == pygame.K_UP:
            self.menu_selection = (self.menu_selection - 1) % len(options)
        elif event.key == pygame.K_DOWN:
            self.menu_selection = (self.menu_selection + 1) % len(options)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.menu_selection == 0:
                self.change_state(STATE_CHARACTER_CREATE)
                self.name_input = ""
                self.class_selection = 0
            elif self.menu_selection == 1:
                if self.load_game():
                    self.change_state(STATE_EXPLORE)
                    self.show_notification("Game loaded!")
                else:
                    self.show_notification("No save file found!")
            elif self.menu_selection == 2:
                self.running = False

    def _draw_main_menu(self):
        self.screen.fill((10, 8, 20))

        # Animated background particles
        t = self.title_timer
        for i in range(20):
            px = (SCREEN_WIDTH // 2 + math.cos(t * 0.5 + i * 0.8) * 300)
            py = (SCREEN_HEIGHT // 2 + math.sin(t * 0.3 + i * 1.1) * 200)
            radius = int(2 + math.sin(t + i) * 1.5)
            alpha = int(80 + math.sin(t * 0.7 + i) * 40)
            color = (100 + int(math.sin(t + i) * 50), 60, 180 + int(math.cos(t + i) * 50))
            pygame.draw.circle(self.screen, color, (int(px), int(py)), radius)

        # Title
        title_y = 150 + int(math.sin(t * 1.5) * 8)
        draw_text(self.screen, "REALMS OF", SCREEN_WIDTH // 2, title_y - 40,
                  self.fonts["large"], UI_ACCENT, center=True)
        draw_text(self.screen, "MYTHOS", SCREEN_WIDTH // 2, title_y + 10,
                  self.fonts["huge"], GOLD, center=True)

        # Subtitle
        draw_text(self.screen, "A Fantasy RPG Adventure", SCREEN_WIDTH // 2, title_y + 75,
                  self.fonts["small"], LIGHT_GRAY, center=True)

        # Menu options
        options = ["New Game", "Load Game", "Quit"]
        for i, opt in enumerate(options):
            y = 380 + i * 50
            color = GOLD if i == self.menu_selection else UI_TEXT
            prefix = "> " if i == self.menu_selection else "  "
            draw_text(self.screen, f"{prefix}{opt}", SCREEN_WIDTH // 2, y,
                      self.fonts["medium"], color, center=True)

        # Controls hint
        draw_text(self.screen, "Arrow Keys to navigate, Enter to select",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60,
                  self.fonts["tiny"], GRAY, center=True)
        draw_text(self.screen, "v1.0 - Built with Pygame",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT - 35,
                  self.fonts["tiny"], DARK_GRAY, center=True)

    # ─── Character Creation ─────────────────────────────────────

    def _handle_character_create(self, event):
        if event.type != pygame.KEYDOWN:
            return

        classes = [CLASS_WARRIOR, CLASS_MAGE, CLASS_ROGUE, CLASS_RANGER, CLASS_PALADIN]

        if self.name_input_active:
            if event.key == pygame.K_RETURN:
                if self.name_input.strip():
                    self.name_input_active = False
                else:
                    self.name_input = "Hero"
                    self.name_input_active = False
            elif event.key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
            elif event.key == pygame.K_ESCAPE:
                self.change_state(STATE_MAIN_MENU)
            else:
                if len(self.name_input) < 16 and event.unicode.isprintable():
                    self.name_input += event.unicode
        else:
            if event.key == pygame.K_UP:
                self.class_selection = (self.class_selection - 1) % len(classes)
            elif event.key == pygame.K_DOWN:
                self.class_selection = (self.class_selection + 1) % len(classes)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                char_class = classes[self.class_selection]
                self.start_new_game(self.name_input.strip() or "Hero", char_class)
            elif event.key == pygame.K_BACKSPACE:
                self.name_input_active = True
            elif event.key == pygame.K_ESCAPE:
                self.change_state(STATE_MAIN_MENU)

    def _draw_character_create(self):
        self.screen.fill((10, 8, 20))
        draw_text(self.screen, "CREATE YOUR HERO", SCREEN_WIDTH // 2, 40,
                  self.fonts["large"], GOLD, center=True)

        # Name input
        draw_text(self.screen, "Name:", 100, 110, self.fonts["medium"], UI_TEXT)
        name_box_color = GOLD if self.name_input_active else UI_BORDER
        pygame.draw.rect(self.screen, name_box_color, (200, 105, 300, 35), 2)
        name_display = self.name_input
        if self.name_input_active and int(self.title_timer * 2) % 2:
            name_display += "|"
        draw_text(self.screen, name_display, 210, 112, self.fonts["medium"], WHITE)

        if self.name_input_active:
            draw_text(self.screen, "Type your name, then press Enter",
                      SCREEN_WIDTH // 2, 160, self.fonts["small"], LIGHT_GRAY, center=True)
            return

        # Class selection
        draw_text(self.screen, "Choose Your Class:", 100, 180, self.fonts["medium"], UI_ACCENT)

        classes = [CLASS_WARRIOR, CLASS_MAGE, CLASS_ROGUE, CLASS_RANGER, CLASS_PALADIN]
        for i, cls_name in enumerate(classes):
            data = CLASS_DATA[cls_name]
            y = 220 + i * 55
            selected = i == self.class_selection

            if selected:
                draw_panel(self.screen, 80, y - 5, 400, 50, bg=(30, 25, 50))
                color = GOLD
                prefix = "> "
            else:
                color = UI_TEXT
                prefix = "  "

            draw_text(self.screen, f"{prefix}{cls_name}", 90, y,
                      self.fonts["medium"], color)
            draw_text(self.screen, data["description"], 120, y + 25,
                      self.fonts["tiny"], LIGHT_GRAY)

            # Draw class sprite
            sprite = SpriteSheet.create_character_sprite(data["color"], 40, cls_name.lower())
            self.screen.blit(sprite, (50, y - 2))

        # Selected class details
        sel_class = classes[self.class_selection]
        sel_data = CLASS_DATA[sel_class]
        detail_x = 520

        draw_panel(self.screen, detail_x - 10, 180, 300, 350)
        draw_text(self.screen, sel_class, detail_x + 130, 190,
                  self.fonts["large"], sel_data["color"], center=True)

        # Big sprite
        big_sprite = SpriteSheet.create_character_sprite(sel_data["color"], 80, sel_class.lower())
        self.screen.blit(big_sprite, (detail_x + 90, 230))

        # Stats
        stats_y = 330
        stats = [
            ("HP", sel_data["base_hp"], HP_BAR_COLOR),
            ("MP", sel_data["base_mp"], MP_BAR_COLOR),
            ("ATK", sel_data["base_atk"], RED),
            ("DEF", sel_data["base_def"], BLUE),
            ("MAG", sel_data["base_mag"], PURPLE),
            ("SPD", sel_data["base_spd"], GREEN),
        ]
        for i, (name, val, color) in enumerate(stats):
            sy = stats_y + i * 28
            draw_text(self.screen, f"{name}:", detail_x + 10, sy,
                      self.fonts["small"], UI_TEXT)
            bar_width = int(val * 2.5)
            draw_bar(self.screen, detail_x + 70, sy + 3, 150, 14, val,
                     max(s[1] for s in stats), color)
            draw_text(self.screen, str(val), detail_x + 230, sy,
                      self.fonts["small"], WHITE)

        # Abilities preview
        draw_text(self.screen, "Starting Abilities:", detail_x + 10, stats_y + 175,
                  self.fonts["small"], UI_ACCENT)
        for i, ab in enumerate(sel_data["abilities"][:3]):
            draw_text(self.screen, f"- {ab.name}", detail_x + 20, stats_y + 200 + i * 20,
                      self.fonts["tiny"], LIGHT_GRAY)

        draw_text(self.screen, "Press Enter to begin your adventure!",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40,
                  self.fonts["small"], GOLD, center=True)

    # ─── Exploration ────────────────────────────────────────────

    def _handle_explore_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_i:
            self.inventory_selection = 0
            self.inventory_tab = 0
            self.change_state(STATE_INVENTORY)
        elif event.key == pygame.K_q:
            self.quest_selection = 0
            self.change_state(STATE_QUEST_LOG)
        elif event.key == pygame.K_ESCAPE:
            self.change_state(STATE_PAUSE)
        elif event.key == pygame.K_e:
            self._interact()

    def _update_explore(self, dt):
        """Update exploration state."""
        if not self.player or not self.current_map:
            return

        self.move_cooldown -= dt
        if self.move_cooldown <= 0:
            keys = pygame.key.get_pressed()
            dx, dy = 0, 0
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
                self.player.facing = "up"
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1
                self.player.facing = "down"
            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
                self.player.facing = "left"
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
                self.player.facing = "right"

            if dx != 0 or dy != 0:
                new_x = self.player.tile_x + dx
                new_y = self.player.tile_y + dy

                if self.current_map.is_walkable(new_x, new_y):
                    self.player.tile_x = new_x
                    self.player.tile_y = new_y
                    self.player.moving = True
                    self.move_cooldown = self.move_delay

                    # Check transitions
                    trans = self.current_map.get_transition_at(new_x, new_y)
                    if trans:
                        self.transition_map(trans["target_map"],
                                            trans["target_x"], trans["target_y"])
                        return

                    # Check boss spawns
                    boss = self.current_map.get_boss_at(new_x, new_y)
                    if boss:
                        boss_enemy = boss["boss_func"](boss["level"])
                        self.show_notification(f"BOSS: {boss_enemy.name}!")
                        self.start_combat([boss_enemy])
                        boss["defeated"] = True
                        return

                    # Check chests
                    chest = self.current_map.get_chest_at(new_x, new_y)
                    if chest:
                        chest["opened"] = True
                        for item in chest["items"]:
                            self.player.add_item(item)
                        item_names = ", ".join(i.name for i in chest["items"])
                        self.show_notification(f"Found: {item_names}")

                    # Random encounter
                    self.check_random_encounter()
                else:
                    # Check if NPC is there
                    npc = self.current_map.get_npc_at(new_x, new_y)
                    if npc:
                        self.start_dialogue(npc)
            else:
                self.player.moving = False

        # Smooth pixel movement
        target_px = self.player.tile_x * TILE_SIZE
        target_py = self.player.tile_y * TILE_SIZE
        speed = PLAYER_SPEED * TILE_SIZE * dt * 8
        if abs(self.player.pixel_x - target_px) > 1:
            self.player.pixel_x += (target_px - self.player.pixel_x) * min(1.0, dt * 15)
        else:
            self.player.pixel_x = target_px
        if abs(self.player.pixel_y - target_py) > 1:
            self.player.pixel_y += (target_py - self.player.pixel_y) * min(1.0, dt * 15)
        else:
            self.player.pixel_y = target_py

        # Update camera
        self.camera.update(self.player.pixel_x, self.player.pixel_y,
                           self.current_map.width, self.current_map.height, dt)

    def _interact(self):
        """Interact with adjacent tile/NPC."""
        if not self.player or not self.current_map:
            return
        facing_offsets = {
            "up": (0, -1), "down": (0, 1),
            "left": (-1, 0), "right": (1, 0)
        }
        dx, dy = facing_offsets.get(self.player.facing, (0, 0))
        tx = self.player.tile_x + dx
        ty = self.player.tile_y + dy

        # Check NPC
        npc = self.current_map.get_npc_at(tx, ty)
        if npc:
            self.start_dialogue(npc)
            return

        # Check chest
        chest = self.current_map.get_chest_at(tx, ty)
        if chest:
            chest["opened"] = True
            for item in chest["items"]:
                self.player.add_item(item)
            item_names = ", ".join(i.name for i in chest["items"])
            self.show_notification(f"Found: {item_names}")

    def _draw_explore(self):
        """Draw exploration view."""
        if not self.current_map:
            return

        # Calculate visible tile range
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        start_tx = max(0, cam_x // TILE_SIZE)
        start_ty = max(0, cam_y // TILE_SIZE)
        end_tx = min(self.current_map.width, (cam_x + SCREEN_WIDTH) // TILE_SIZE + 2)
        end_ty = min(self.current_map.height, (cam_y + SCREEN_HEIGHT) // TILE_SIZE + 2)

        # Draw tiles
        for ty in range(start_ty, end_ty):
            for tx in range(start_tx, end_tx):
                tile = self.current_map.get_tile(tx, ty)
                sprite = self.tile_cache.get(tile)
                if sprite:
                    sx, sy = self.camera.apply(tx * TILE_SIZE, ty * TILE_SIZE)
                    self.screen.blit(sprite, (sx, sy))

        # Draw chests
        for chest in self.current_map.chests:
            if not chest["opened"]:
                sx, sy = self.camera.apply(chest["x"] * TILE_SIZE, chest["y"] * TILE_SIZE)
                chest_sprite = SpriteSheet.create_chest_sprite()
                self.screen.blit(chest_sprite, (sx, sy))

        # Draw NPCs
        for npc in self.current_map.npcs:
            sx, sy = self.camera.apply(npc.tile_x * TILE_SIZE, npc.tile_y * TILE_SIZE)
            npc_sprite = SpriteSheet.create_npc_sprite(npc.color, TILE_SIZE, npc.npc_type)
            self.screen.blit(npc_sprite, (sx, sy))

            # Draw name above NPC
            draw_text(self.screen, npc.name, sx + TILE_SIZE // 2, sy - 12,
                      self.fonts["tiny"], GOLD, center=True)

            # Quest indicator
            if npc.quest and not npc.quest.turned_in:
                indicator_color = YELLOW if not npc.quest.completed else GREEN
                indicator = "!" if not npc.quest.accepted else "?"
                draw_text(self.screen, indicator, sx + TILE_SIZE // 2, sy - 25,
                          self.fonts["medium"], indicator_color, center=True)

        # Draw boss indicators
        for boss in self.current_map.boss_spawns:
            if not boss["defeated"]:
                sx, sy = self.camera.apply(boss["x"] * TILE_SIZE, boss["y"] * TILE_SIZE)
                # Skull icon
                draw_text(self.screen, "BOSS", sx + TILE_SIZE // 2, sy - 10,
                          self.fonts["tiny"], RED, center=True)
                boss_sprite = SpriteSheet.create_enemy_sprite(RED, TILE_SIZE, "boss")
                self.screen.blit(boss_sprite, (sx, sy))

        # Draw transitions
        for trans in self.current_map.transitions:
            sx, sy = self.camera.apply(trans["x"] * TILE_SIZE, trans["y"] * TILE_SIZE)
            if 0 <= sx < SCREEN_WIDTH and 0 <= sy < SCREEN_HEIGHT:
                label = trans.get("label", "Exit")
                t = math.sin(self.title_timer * 2) * 0.5 + 0.5
                arrow_color = (int(200 * t), int(200 * t), int(50 + 200 * t))
                draw_text(self.screen, f">> {label}", sx, sy - 10,
                          self.fonts["tiny"], arrow_color)

        # Draw player
        px, py = self.camera.apply(int(self.player.pixel_x), int(self.player.pixel_y))
        class_name = self.player.char_class.lower()
        player_color = CLASS_DATA[self.player.char_class]["color"]
        player_sprite = SpriteSheet.create_character_sprite(player_color, TILE_SIZE, class_name)
        self.screen.blit(player_sprite, (px, py))

        # Draw ambient overlay
        if self.current_map.ambient_color and self.current_map.ambient_color[3] > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(self.current_map.ambient_color)
            self.screen.blit(overlay, (0, 0))

        # Draw HUD
        self._draw_hud()

        # Draw minimap
        self._draw_minimap()

    def _draw_hud(self):
        """Draw the heads-up display."""
        # Top-left: Player info
        draw_panel(self.screen, 5, 5, 250, 75)
        draw_text(self.screen, f"{self.player.name} - Lv.{self.player.level} {self.player.char_class}",
                  15, 10, self.fonts["small"], UI_ACCENT)

        # HP bar
        draw_bar(self.screen, 15, 32, 180, 14,
                 self.player.stats.hp, self.player.stats.max_hp, HP_BAR_COLOR)
        draw_text(self.screen, f"HP: {self.player.stats.hp}/{self.player.stats.max_hp}",
                  200, 32, self.fonts["tiny"], WHITE)

        # MP bar
        draw_bar(self.screen, 15, 50, 180, 12,
                 self.player.stats.mp, self.player.stats.max_mp, MP_BAR_COLOR)
        draw_text(self.screen, f"MP: {self.player.stats.mp}/{self.player.stats.max_mp}",
                  200, 50, self.fonts["tiny"], WHITE)

        # XP bar
        draw_bar(self.screen, 15, 65, 180, 8,
                 self.player.xp, self.player.xp_to_next_level, XP_BAR_COLOR)

        # Gold
        draw_text(self.screen, f"Gold: {self.player.gold}", 15, SCREEN_HEIGHT - 25,
                  self.fonts["small"], GOLD)

        # Map name
        if self.current_map:
            draw_text(self.screen, self.current_map.name,
                      SCREEN_WIDTH // 2, 10, self.fonts["small"], UI_TEXT, center=True)

        # Controls hint
        draw_text(self.screen, "[I]nventory  [Q]uests  [E]nteract  [ESC]Pause",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20,
                  self.fonts["tiny"], GRAY, center=True)

    def _draw_minimap(self):
        """Draw a minimap in the corner."""
        if not self.current_map:
            return

        mm_size = 120
        mm_x = SCREEN_WIDTH - mm_size - 10
        mm_y = 10
        scale_x = mm_size / self.current_map.width
        scale_y = mm_size / self.current_map.height

        # Background
        draw_panel(self.screen, mm_x - 2, mm_y - 2, mm_size + 4, mm_size + 4)

        mm_surface = pygame.Surface((mm_size, mm_size))
        mm_surface.fill(UI_BG)

        for ty in range(self.current_map.height):
            for tx in range(self.current_map.width):
                tile = self.current_map.get_tile(tx, ty)
                props = TILE_PROPERTIES.get(tile, TILE_PROPERTIES[1])
                px_x = int(tx * scale_x)
                px_y = int(ty * scale_y)
                color = props["color"]
                mm_surface.set_at((min(px_x, mm_size - 1), min(px_y, mm_size - 1)), color)

        # Player dot
        player_mx = int(self.player.tile_x * scale_x)
        player_my = int(self.player.tile_y * scale_y)
        pygame.draw.circle(mm_surface, WHITE, (player_mx, player_my), 2)

        # NPC dots
        for npc in self.current_map.npcs:
            nx = int(npc.tile_x * scale_x)
            ny = int(npc.tile_y * scale_y)
            pygame.draw.circle(mm_surface, YELLOW, (nx, ny), 1)

        self.screen.blit(mm_surface, (mm_x, mm_y))

    # ─── Combat ─────────────────────────────────────────────────

    def _handle_combat(self, event):
        if not self.combat_system:
            return
        result = self.combat_system.handle_input(event)
        if result == "victory":
            # Update quests for kills
            for enemy in self.combat_system.enemies:
                for quest in self.player.active_quests:
                    quest.update("kill", enemy.name)
                    if enemy.enemy_type == "boss":
                        quest.update("boss", enemy.name)
            self.change_state(STATE_EXPLORE)
            self.combat_system = None
        elif result == "defeat":
            self.change_state(STATE_GAME_OVER)
            self.combat_system = None
        elif result == "fled":
            self.change_state(STATE_EXPLORE)
            self.combat_system = None

    def _draw_combat(self):
        if self.combat_system:
            self.combat_system.draw(self.screen)

    # ─── Inventory ──────────────────────────────────────────────

    def _handle_inventory(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE or event.key == pygame.K_i:
            self.change_state(STATE_EXPLORE)
            return

        if event.key == pygame.K_TAB:
            self.inventory_tab = (self.inventory_tab + 1) % 2
            self.inventory_selection = 0
            return

        if self.inventory_tab == 0:  # Items
            items = self.player.inventory
            if not items:
                return
            if event.key == pygame.K_UP:
                self.inventory_selection = max(0, self.inventory_selection - 1)
            elif event.key == pygame.K_DOWN:
                self.inventory_selection = min(len(items) - 1, self.inventory_selection + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                item = items[self.inventory_selection]
                if item.consumable:
                    self.player.use_item(item)
                    self.show_notification(f"Used {item.name}")
                    if self.inventory_selection >= len(self.player.inventory):
                        self.inventory_selection = max(0, len(self.player.inventory) - 1)
                elif item.slot:
                    old = self.player.equip_item(item)
                    self.show_notification(f"Equipped {item.name}")
                    if self.inventory_selection >= len(self.player.inventory):
                        self.inventory_selection = max(0, len(self.player.inventory) - 1)
            elif event.key == pygame.K_x:
                if items:
                    item = items[self.inventory_selection]
                    self.player.remove_item(item)
                    self.show_notification(f"Discarded {item.name}")
                    if self.inventory_selection >= len(self.player.inventory):
                        self.inventory_selection = max(0, len(self.player.inventory) - 1)

        else:  # Equipment
            slots = list(self.player.equipment.keys())
            if event.key == pygame.K_UP:
                self.inventory_selection = max(0, self.inventory_selection - 1)
            elif event.key == pygame.K_DOWN:
                self.inventory_selection = min(len(slots) - 1, self.inventory_selection + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                slot = slots[self.inventory_selection]
                item = self.player.unequip_item(slot)
                if item:
                    self.show_notification(f"Unequipped {item.name}")

    def _draw_inventory(self):
        self.screen.fill((10, 8, 20))
        draw_text(self.screen, "INVENTORY", SCREEN_WIDTH // 2, 20,
                  self.fonts["large"], GOLD, center=True)

        # Tabs
        tabs = ["Items", "Equipment"]
        for i, tab in enumerate(tabs):
            color = GOLD if i == self.inventory_tab else UI_TEXT
            draw_text(self.screen, tab, 100 + i * 150, 60, self.fonts["medium"], color)
            if i == self.inventory_tab:
                pygame.draw.line(self.screen, GOLD, (100 + i * 150, 82),
                                 (100 + i * 150 + 80, 82), 2)

        if self.inventory_tab == 0:
            # Items list
            draw_panel(self.screen, 30, 90, 450, SCREEN_HEIGHT - 130)
            items = self.player.inventory
            if not items:
                draw_text(self.screen, "No items", 50, 110, self.fonts["small"], GRAY)
            else:
                visible_start = max(0, self.inventory_selection - 15)
                for i, item in enumerate(items[visible_start:visible_start + 16]):
                    real_i = visible_start + i
                    y = 100 + i * 35
                    selected = real_i == self.inventory_selection
                    if selected:
                        draw_panel(self.screen, 35, y - 2, 440, 32, bg=(30, 25, 50))
                    color = get_rarity_color(item.rarity)
                    prefix = "> " if selected else "  "
                    draw_text(self.screen, f"{prefix}{item.name}", 45, y,
                              self.fonts["small"], color)
                    if item.consumable:
                        draw_text(self.screen, "[USE]", 380, y, self.fonts["tiny"], GREEN)
                    elif item.slot:
                        draw_text(self.screen, "[EQUIP]", 370, y, self.fonts["tiny"], CYAN)

            # Item details panel
            draw_panel(self.screen, 490, 90, 300, SCREEN_HEIGHT - 130)
            if items and 0 <= self.inventory_selection < len(items):
                item = items[self.inventory_selection]
                tooltip = item.get_tooltip_lines()
                for j, line in enumerate(tooltip):
                    color = get_rarity_color(item.rarity) if j == 0 else UI_TEXT
                    draw_text(self.screen, line, 510, 110 + j * 22,
                              self.fonts["small"], color)

        else:
            # Equipment view
            draw_panel(self.screen, 30, 90, 450, SCREEN_HEIGHT - 130)
            slots = list(self.player.equipment.keys())
            for i, slot in enumerate(slots):
                y = 100 + i * 55
                selected = i == self.inventory_selection
                if selected:
                    draw_panel(self.screen, 35, y - 5, 440, 50, bg=(30, 25, 50))

                item = self.player.equipment[slot]
                draw_text(self.screen, f"{slot}:", 50, y, self.fonts["small"], UI_ACCENT)
                if item:
                    color = get_rarity_color(item.rarity)
                    draw_text(self.screen, item.name, 160, y, self.fonts["small"], color)
                    # Show stats
                    stat_text = ", ".join(f"+{v} {k}" for k, v in item.stats.items() if v > 0)
                    draw_text(self.screen, stat_text, 160, y + 22,
                              self.fonts["tiny"], LIGHT_GRAY)
                else:
                    draw_text(self.screen, "Empty", 160, y, self.fonts["small"], GRAY)

            # Player stats panel
            draw_panel(self.screen, 490, 90, 300, SCREEN_HEIGHT - 130)
            draw_text(self.screen, "Character Stats", 510, 100, self.fonts["medium"], UI_ACCENT)
            stats_info = [
                ("Level", str(self.player.level)),
                ("HP", f"{self.player.stats.hp}/{self.player.stats.max_hp}"),
                ("MP", f"{self.player.stats.mp}/{self.player.stats.max_mp}"),
                ("ATK", str(self.player.get_total_atk())),
                ("DEF", str(self.player.get_total_def())),
                ("MAG", str(self.player.get_total_mag())),
                ("SPD", str(self.player.get_total_spd())),
                ("XP", f"{self.player.xp}/{self.player.xp_to_next_level}"),
                ("Gold", str(self.player.gold)),
            ]
            for j, (stat, val) in enumerate(stats_info):
                draw_text(self.screen, f"{stat}: {val}", 510, 140 + j * 28,
                          self.fonts["small"], UI_TEXT)

        # Controls
        hint = "[Tab] Switch tabs  [Enter] Use/Equip  [X] Discard  [I/Esc] Close"
        draw_text(self.screen, hint, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25,
                  self.fonts["tiny"], GRAY, center=True)

    # ─── Dialogue ───────────────────────────────────────────────

    def _handle_dialogue(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            if self.dialogue_index < len(self.dialogue_lines) - 1:
                self.dialogue_index += 1
            else:
                # End of dialogue - handle NPC type
                if self.dialogue_npc:
                    npc = self.dialogue_npc
                    if npc.npc_type == "healer":
                        self.player.rest_at_inn()
                        self.show_notification("Fully healed!")
                    elif npc.npc_type == "merchant":
                        self.shop_items = [func() for func in npc.shop_items]
                        self.shop_selection = 0
                        self.shop_mode = "buy"
                        self.change_state(STATE_SHOP)
                        return
                    elif npc.npc_type == "quest" and npc.quest:
                        quest = npc.quest
                        if not quest.accepted:
                            quest.accepted = True
                            self.player.active_quests.append(quest)
                            self.show_notification(f"Quest accepted: {quest.name}")
                        elif quest.completed and not quest.turned_in:
                            quest.turned_in = True
                            self.player.gold += quest.gold_reward
                            level_ups = self.player.gain_xp(quest.xp_reward)
                            for item_func in quest.item_rewards:
                                self.player.add_item(item_func())
                            self.player.active_quests.remove(quest)
                            self.player.completed_quests.append(quest)
                            self.show_notification(
                                f"Quest complete! +{quest.xp_reward} XP, +{quest.gold_reward} gold")
                            if level_ups:
                                self.level_up_gains = level_ups[-1]
                                self.change_state(STATE_LEVEL_UP)
                                return
                self.change_state(STATE_EXPLORE)
                self.dialogue_npc = None
        elif event.key == pygame.K_ESCAPE:
            self.change_state(STATE_EXPLORE)
            self.dialogue_npc = None

    def _draw_dialogue(self):
        # Draw the exploration scene behind
        self._draw_explore()

        # Dialogue box
        box_h = 160
        box_y = SCREEN_HEIGHT - box_h - 20
        draw_panel(self.screen, 40, box_y, SCREEN_WIDTH - 80, box_h, alpha=240)

        if self.dialogue_npc:
            draw_text(self.screen, self.dialogue_npc.name, 60, box_y + 10,
                      self.fonts["medium"], GOLD)

        if self.dialogue_lines and self.dialogue_index < len(self.dialogue_lines):
            text = self.dialogue_lines[self.dialogue_index]
            lines = wrap_text(text, self.fonts["small"], SCREEN_WIDTH - 140)
            for i, line in enumerate(lines):
                draw_text(self.screen, line, 60, box_y + 45 + i * 25,
                          self.fonts["small"], UI_TEXT)

        # Continue indicator
        if int(self.title_timer * 3) % 2:
            draw_text(self.screen, "Press Enter to continue...",
                      SCREEN_WIDTH - 240, box_y + box_h - 25,
                      self.fonts["tiny"], LIGHT_GRAY)

        # Quest info if applicable
        if self.dialogue_npc and self.dialogue_npc.quest:
            quest = self.dialogue_npc.quest
            if quest.accepted and not quest.turned_in:
                status = "COMPLETE - Turn in!" if quest.completed else "In Progress"
                color = GREEN if quest.completed else YELLOW
                draw_text(self.screen, f"Quest: {quest.name} [{status}]",
                          60, box_y - 25, self.fonts["small"], color)

    # ─── Shop ───────────────────────────────────────────────────

    def _handle_shop(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.change_state(STATE_EXPLORE)
            return

        if event.key == pygame.K_TAB:
            self.shop_mode = "sell" if self.shop_mode == "buy" else "buy"
            self.shop_selection = 0
            return

        items = self.shop_items if self.shop_mode == "buy" else self.player.inventory
        if not items:
            return

        if event.key == pygame.K_UP:
            self.shop_selection = max(0, self.shop_selection - 1)
        elif event.key == pygame.K_DOWN:
            self.shop_selection = min(len(items) - 1, self.shop_selection + 1)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.shop_mode == "buy":
                item = items[self.shop_selection]
                if self.player.gold >= item.value:
                    if self.player.add_item(Item.from_dict(item.to_dict())):
                        self.player.gold -= item.value
                        self.show_notification(f"Bought {item.name} for {item.value} gold")
                    else:
                        self.show_notification("Inventory full!")
                else:
                    self.show_notification("Not enough gold!")
            else:
                item = items[self.shop_selection]
                sell_price = item.value // 2
                self.player.gold += sell_price
                self.player.remove_item(item)
                self.show_notification(f"Sold {item.name} for {sell_price} gold")
                if self.shop_selection >= len(self.player.inventory):
                    self.shop_selection = max(0, len(self.player.inventory) - 1)

    def _draw_shop(self):
        self.screen.fill((10, 8, 20))
        draw_text(self.screen, "SHOP", SCREEN_WIDTH // 2, 20,
                  self.fonts["large"], GOLD, center=True)
        draw_text(self.screen, f"Gold: {self.player.gold}", SCREEN_WIDTH // 2, 55,
                  self.fonts["medium"], GOLD, center=True)

        # Tabs
        for i, tab in enumerate(["Buy", "Sell"]):
            color = GOLD if (i == 0 and self.shop_mode == "buy") or \
                           (i == 1 and self.shop_mode == "sell") else UI_TEXT
            draw_text(self.screen, tab, 100 + i * 150, 80, self.fonts["medium"], color)

        # Items list
        draw_panel(self.screen, 30, 110, 500, SCREEN_HEIGHT - 150)
        items = self.shop_items if self.shop_mode == "buy" else self.player.inventory

        if not items:
            draw_text(self.screen, "Nothing to show", 50, 130, self.fonts["small"], GRAY)
        else:
            visible_start = max(0, self.shop_selection - 12)
            for i, item in enumerate(items[visible_start:visible_start + 14]):
                real_i = visible_start + i
                y = 120 + i * 35
                selected = real_i == self.shop_selection
                if selected:
                    draw_panel(self.screen, 35, y - 2, 490, 32, bg=(30, 25, 50))

                color = get_rarity_color(item.rarity)
                prefix = "> " if selected else "  "
                draw_text(self.screen, f"{prefix}{item.name}", 45, y,
                          self.fonts["small"], color)

                price = item.value if self.shop_mode == "buy" else item.value // 2
                price_color = GREEN if self.player.gold >= price else RED
                draw_text(self.screen, f"{price}g", 430, y,
                          self.fonts["small"], price_color)

        # Item details
        draw_panel(self.screen, 540, 110, 250, SCREEN_HEIGHT - 150)
        if items and 0 <= self.shop_selection < len(items):
            item = items[self.shop_selection]
            tooltip = item.get_tooltip_lines()
            for j, line in enumerate(tooltip):
                c = get_rarity_color(item.rarity) if j == 0 else UI_TEXT
                draw_text(self.screen, line, 555, 125 + j * 20,
                          self.fonts["tiny"], c)

        draw_text(self.screen, "[Tab] Buy/Sell  [Enter] Purchase  [Esc] Leave",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25,
                  self.fonts["tiny"], GRAY, center=True)

    # ─── Quest Log ──────────────────────────────────────────────

    def _handle_quest_log(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_q):
            self.change_state(STATE_EXPLORE)
        elif event.key == pygame.K_UP:
            quests = self.player.active_quests
            if quests:
                self.quest_selection = max(0, self.quest_selection - 1)
        elif event.key == pygame.K_DOWN:
            quests = self.player.active_quests
            if quests:
                self.quest_selection = min(len(quests) - 1, self.quest_selection + 1)

    def _draw_quest_log(self):
        self.screen.fill((10, 8, 20))
        draw_text(self.screen, "QUEST LOG", SCREEN_WIDTH // 2, 20,
                  self.fonts["large"], GOLD, center=True)

        # Quest list
        draw_panel(self.screen, 30, 60, 350, SCREEN_HEIGHT - 100)
        quests = self.player.active_quests

        if not quests:
            draw_text(self.screen, "No active quests", 50, 80,
                      self.fonts["small"], GRAY)
            draw_text(self.screen, "Talk to NPCs with ! marks", 50, 110,
                      self.fonts["tiny"], LIGHT_GRAY)
        else:
            for i, quest in enumerate(quests):
                y = 70 + i * 40
                selected = i == self.quest_selection
                if selected:
                    draw_panel(self.screen, 35, y - 2, 340, 36, bg=(30, 25, 50))

                color = GREEN if quest.completed else GOLD if selected else UI_TEXT
                prefix = "> " if selected else "  "
                status = " [COMPLETE]" if quest.completed else ""
                draw_text(self.screen, f"{prefix}{quest.name}{status}", 45, y,
                          self.fonts["small"], color)
                draw_text(self.screen, f"Level {quest.level_req}+", 45, y + 20,
                          self.fonts["tiny"], LIGHT_GRAY)

        # Quest details
        draw_panel(self.screen, 390, 60, 400, SCREEN_HEIGHT - 100)
        if quests and 0 <= self.quest_selection < len(quests):
            quest = quests[self.quest_selection]
            lines = quest.get_description_lines()
            for j, line in enumerate(lines):
                color = GOLD if j == 0 else UI_TEXT
                draw_text(self.screen, line, 410, 75 + j * 22,
                          self.fonts["small"], color)

        # Completed count
        draw_text(self.screen, f"Completed: {len(self.player.completed_quests)}",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25,
                  self.fonts["tiny"], GRAY, center=True)

    # ─── Level Up ───────────────────────────────────────────────

    def _handle_level_up(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.change_state(STATE_EXPLORE)
            self.level_up_gains = None

    def _draw_level_up(self):
        # Draw explore behind
        if self.prev_state == STATE_EXPLORE:
            self._draw_explore()

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        draw_text(self.screen, "LEVEL UP!", SCREEN_WIDTH // 2, 150,
                  self.fonts["huge"], GOLD, center=True)
        draw_text(self.screen, f"Level {self.player.level}",
                  SCREEN_WIDTH // 2, 230, self.fonts["large"], WHITE, center=True)

        if self.level_up_gains:
            gains = self.level_up_gains
            y = 290
            stat_labels = [
                ("HP", gains["hp"], HP_BAR_COLOR),
                ("MP", gains["mp"], MP_BAR_COLOR),
                ("ATK", gains["atk"], RED),
                ("DEF", gains["def"], BLUE),
                ("MAG", gains["mag"], PURPLE),
                ("SPD", gains["spd"], GREEN),
            ]
            for label, val, color in stat_labels:
                draw_text(self.screen, f"{label}: +{val}", SCREEN_WIDTH // 2, y,
                          self.fonts["medium"], color, center=True)
                y += 35

        # New abilities
        new_abilities = [a for a in self.player.abilities
                         if a.level_req == self.player.level]
        if new_abilities:
            draw_text(self.screen, "New Ability Unlocked!",
                      SCREEN_WIDTH // 2, 520, self.fonts["medium"], CYAN, center=True)
            for i, ab in enumerate(new_abilities):
                draw_text(self.screen, f"{ab.name} - {ab.description}",
                          SCREEN_WIDTH // 2, 555 + i * 25,
                          self.fonts["small"], UI_TEXT, center=True)

        draw_text(self.screen, "Press Enter to continue",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50,
                  self.fonts["small"], LIGHT_GRAY, center=True)

    # ─── Game Over ──────────────────────────────────────────────

    def _handle_game_over(self, event):
        if event.type != pygame.KEYDOWN:
            return
        options = ["Return to Village", "Main Menu"]
        if event.key == pygame.K_UP:
            self.menu_selection = (self.menu_selection - 1) % len(options)
        elif event.key == pygame.K_DOWN:
            self.menu_selection = (self.menu_selection + 1) % len(options)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.menu_selection == 0:
                # Revive at village with half HP
                self.player.stats.hp = self.player.stats.max_hp // 2
                self.player.stats.mp = self.player.stats.max_mp // 2
                self.player.gold = max(0, self.player.gold - self.player.gold // 4)
                self.transition_map("village",
                                    load_map("village").spawn_x,
                                    load_map("village").spawn_y)
                self.change_state(STATE_EXPLORE)
                self.show_notification("You wake up at the village, weakened...")
            elif self.menu_selection == 1:
                self.change_state(STATE_MAIN_MENU)
                self.menu_selection = 0

    def _draw_game_over(self):
        self.screen.fill((15, 5, 5))

        draw_text(self.screen, "GAME OVER", SCREEN_WIDTH // 2, 200,
                  self.fonts["huge"], RED, center=True)
        draw_text(self.screen, "You have fallen in battle...",
                  SCREEN_WIDTH // 2, 280, self.fonts["medium"], UI_TEXT, center=True)

        options = ["Return to Village", "Main Menu"]
        for i, opt in enumerate(options):
            y = 380 + i * 50
            color = GOLD if i == self.menu_selection else UI_TEXT
            prefix = "> " if i == self.menu_selection else "  "
            draw_text(self.screen, f"{prefix}{opt}", SCREEN_WIDTH // 2, y,
                      self.fonts["medium"], color, center=True)

    # ─── Pause ──────────────────────────────────────────────────

    def _handle_pause(self, event):
        if event.type != pygame.KEYDOWN:
            return
        options = ["Resume", "Save Game", "Main Menu", "Quit"]
        if event.key == pygame.K_ESCAPE:
            self.change_state(STATE_EXPLORE)
        elif event.key == pygame.K_UP:
            self.menu_selection = (self.menu_selection - 1) % len(options)
        elif event.key == pygame.K_DOWN:
            self.menu_selection = (self.menu_selection + 1) % len(options)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.menu_selection == 0:
                self.change_state(STATE_EXPLORE)
            elif self.menu_selection == 1:
                self.save_game()
                self.show_notification("Game saved!")
            elif self.menu_selection == 2:
                self.change_state(STATE_MAIN_MENU)
                self.menu_selection = 0
            elif self.menu_selection == 3:
                self.running = False

    def _draw_pause(self):
        self._draw_explore()

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        draw_text(self.screen, "PAUSED", SCREEN_WIDTH // 2, 200,
                  self.fonts["huge"], UI_ACCENT, center=True)

        options = ["Resume", "Save Game", "Main Menu", "Quit"]
        for i, opt in enumerate(options):
            y = 320 + i * 50
            color = GOLD if i == self.menu_selection else UI_TEXT
            prefix = "> " if i == self.menu_selection else "  "
            draw_text(self.screen, f"{prefix}{opt}", SCREEN_WIDTH // 2, y,
                      self.fonts["medium"], color, center=True)

    # ─── Notifications ──────────────────────────────────────────

    def _draw_notification(self):
        if self.notification_timer <= 0:
            return
        alpha = min(255, int(self.notification_timer * 255))
        notif_surf = pygame.Surface((SCREEN_WIDTH, 40), pygame.SRCALPHA)
        notif_surf.fill((20, 15, 40, min(220, alpha)))
        self.screen.blit(notif_surf, (0, 85))
        color = GOLD
        draw_text(self.screen, self.notification_text,
                  SCREEN_WIDTH // 2, 92, self.fonts["small"], color, center=True)

    # ─── Save / Load ────────────────────────────────────────────

    def save_game(self):
        """Save game to file."""
        if not self.player:
            return
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, "save.json")

        data = {
            "player": self.player.to_dict(),
            "current_map": self.player.current_map,
        }

        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_game(self):
        """Load game from file."""
        save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 "saves", "save.json")
        if not os.path.exists(save_path):
            return False

        try:
            with open(save_path, "r") as f:
                data = json.load(f)

            pd = data["player"]
            self.player = Player(pd["name"], pd["char_class"])
            self.player.level = pd["level"]
            self.player.xp = pd["xp"]
            self.player.gold = pd["gold"]
            self.player.stats = __import__("src.entities", fromlist=["Stats"]).Stats.from_dict(pd["stats"])
            self.player.tile_x = pd["tile_x"]
            self.player.tile_y = pd["tile_y"]
            self.player.pixel_x = pd["tile_x"] * TILE_SIZE
            self.player.pixel_y = pd["tile_y"] * TILE_SIZE
            self.player.current_map = pd["current_map"]

            # Restore inventory
            self.player.inventory = [Item.from_dict(i) for i in pd.get("inventory", [])]

            # Restore equipment
            for slot, item_data in pd.get("equipment", {}).items():
                if item_data:
                    self.player.equipment[slot] = Item.from_dict(item_data)

            # Load map
            self.current_map = load_map(self.player.current_map)
            self.camera.x = self.player.pixel_x - SCREEN_WIDTH // 2
            self.camera.y = self.player.pixel_y - SCREEN_HEIGHT // 2

            return True

        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"Error loading save: {e}")
            return False
