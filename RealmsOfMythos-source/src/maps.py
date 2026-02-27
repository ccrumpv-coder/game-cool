"""Map system: tile-based maps with multiple areas."""

import random
from src.constants import (
    TILE_SIZE, MAP_WIDTH, MAP_HEIGHT,
    DARK_GREEN, GREEN, BROWN, DARK_BROWN, SAND, WATER_BLUE,
    GRAY, DARK_GRAY, LIGHT_GRAY, LAVA_RED, ICE_BLUE, BLACK, WHITE,
    GOLD, RED, BLUE, PURPLE
)
from src.entities import NPC, create_boss_goblin_king, create_boss_lich, create_boss_dragon
from src.items import (
    VILLAGE_SHOP, FOREST_SHOP, MOUNTAIN_SHOP,
    create_health_potion, create_mana_potion
)
from src.quests import (
    create_quest_slime_trouble, create_quest_wolf_pelts,
    create_quest_goblin_camp, create_quest_dark_forest,
    create_quest_mountain_pass, create_quest_dragon_threat,
    create_quest_lich_lord, create_quest_elder_dragon,
)


# Tile types
TILE_GRASS = 0
TILE_WALL = 1
TILE_WATER = 2
TILE_STONE = 3
TILE_SAND = 4
TILE_TREE = 5
TILE_DOOR = 6
TILE_CHEST = 7
TILE_STAIRS_UP = 8
TILE_STAIRS_DOWN = 9
TILE_LAVA = 10
TILE_ICE = 11
TILE_PATH = 12
TILE_DARK_STONE = 13
TILE_BRIDGE = 14

TILE_PROPERTIES = {
    TILE_GRASS: {"walkable": True, "color": DARK_GREEN, "name": "Grass", "tile_type": "grass"},
    TILE_WALL: {"walkable": False, "color": GRAY, "name": "Wall", "tile_type": "wall"},
    TILE_WATER: {"walkable": False, "color": WATER_BLUE, "name": "Water", "tile_type": "water"},
    TILE_STONE: {"walkable": True, "color": LIGHT_GRAY, "name": "Stone Floor", "tile_type": "stone"},
    TILE_SAND: {"walkable": True, "color": SAND, "name": "Sand", "tile_type": "sand"},
    TILE_TREE: {"walkable": False, "color": (20, 80, 20), "name": "Tree", "tile_type": "grass"},
    TILE_DOOR: {"walkable": True, "color": BROWN, "name": "Door", "tile_type": "stone"},
    TILE_CHEST: {"walkable": True, "color": GOLD, "name": "Chest", "tile_type": "stone"},
    TILE_STAIRS_UP: {"walkable": True, "color": WHITE, "name": "Exit", "tile_type": "stone"},
    TILE_STAIRS_DOWN: {"walkable": True, "color": DARK_GRAY, "name": "Entrance", "tile_type": "stone"},
    TILE_LAVA: {"walkable": False, "color": LAVA_RED, "name": "Lava", "tile_type": "sand"},
    TILE_ICE: {"walkable": True, "color": ICE_BLUE, "name": "Ice", "tile_type": "stone"},
    TILE_PATH: {"walkable": True, "color": DARK_BROWN, "name": "Path", "tile_type": "sand"},
    TILE_DARK_STONE: {"walkable": True, "color": (40, 35, 50), "name": "Dark Stone", "tile_type": "stone"},
    TILE_BRIDGE: {"walkable": True, "color": (120, 80, 40), "name": "Bridge", "tile_type": "stone"},
}


class TileMap:
    """A tile-based map."""

    def __init__(self, width, height, name="Unknown", encounter_area=None,
                 ambient_color=None):
        self.width = width
        self.height = height
        self.name = name
        self.tiles = [[TILE_GRASS] * width for _ in range(height)]
        self.encounter_area = encounter_area
        self.ambient_color = ambient_color or (0, 0, 0, 0)

        # Entities on this map
        self.npcs = []
        self.chests = []  # list of {"x": int, "y": int, "items": [...], "opened": bool}
        self.transitions = []  # list of {"x", "y", "target_map", "target_x", "target_y"}
        self.boss_spawns = []  # list of {"x", "y", "boss_func", "defeated": bool}
        self.encounter_zones = []  # list of {"x1", "y1", "x2", "y2", "area": str}

        # Player spawn
        self.spawn_x = 5
        self.spawn_y = 5

    def get_tile(self, x, y):
        """Get tile type at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return TILE_WALL

    def set_tile(self, x, y, tile_type):
        """Set tile at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = tile_type

    def is_walkable(self, x, y):
        """Check if tile is walkable."""
        tile = self.get_tile(x, y)
        props = TILE_PROPERTIES.get(tile, TILE_PROPERTIES[TILE_WALL])
        if not props["walkable"]:
            return False
        # Check NPC collision
        for npc in self.npcs:
            if npc.tile_x == x and npc.tile_y == y:
                return False
        return True

    def get_npc_at(self, x, y):
        """Get NPC at tile position."""
        for npc in self.npcs:
            if npc.tile_x == x and npc.tile_y == y:
                return npc
        return None

    def get_chest_at(self, x, y):
        """Get chest at tile position."""
        for chest in self.chests:
            if chest["x"] == x and chest["y"] == y and not chest["opened"]:
                return chest
        return None

    def get_transition_at(self, x, y):
        """Get map transition at position."""
        for trans in self.transitions:
            if trans["x"] == x and trans["y"] == y:
                return trans
        return None

    def get_boss_at(self, x, y):
        """Get boss spawn at position."""
        for boss in self.boss_spawns:
            if boss["x"] == x and boss["y"] == y and not boss["defeated"]:
                return boss
        return None

    def get_encounter_area(self, x, y):
        """Get encounter area for position."""
        for zone in self.encounter_zones:
            if zone["x1"] <= x <= zone["x2"] and zone["y1"] <= y <= zone["y2"]:
                return zone["area"]
        return self.encounter_area

    def fill_rect(self, x1, y1, x2, y2, tile_type):
        """Fill a rectangular area."""
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                self.set_tile(x, y, tile_type)

    def draw_border(self, tile_type=TILE_WALL):
        """Draw walls around the map border."""
        for x in range(self.width):
            self.set_tile(x, 0, tile_type)
            self.set_tile(x, self.height - 1, tile_type)
        for y in range(self.height):
            self.set_tile(0, y, tile_type)
            self.set_tile(self.width - 1, y, tile_type)


# ─── Map Builders ────────────────────────────────────────────────────

def create_village_map():
    """Create the starting village map."""
    m = TileMap(40, 30, "Peaceful Village", encounter_area=None)

    # Fill with grass
    m.fill_rect(0, 0, 39, 29, TILE_GRASS)
    m.draw_border(TILE_TREE)

    # Paths
    m.fill_rect(5, 14, 35, 15, TILE_PATH)
    m.fill_rect(19, 5, 20, 25, TILE_PATH)

    # Water pond
    m.fill_rect(30, 3, 35, 7, TILE_WATER)
    m.fill_rect(31, 2, 34, 8, TILE_WATER)
    m.set_tile(32, 8, TILE_BRIDGE)
    m.set_tile(33, 8, TILE_BRIDGE)

    # Houses (walls)
    for bx, by in [(3, 3), (3, 18), (12, 3), (12, 18), (25, 18)]:
        m.fill_rect(bx, by, bx + 5, by + 4, TILE_STONE)
        m.fill_rect(bx, by, bx + 5, by, TILE_WALL)
        m.fill_rect(bx, by + 4, bx + 5, by + 4, TILE_WALL)
        m.fill_rect(bx, by, bx, by + 4, TILE_WALL)
        m.fill_rect(bx + 5, by, bx + 5, by + 4, TILE_WALL)
        m.set_tile(bx + 2, by + 4, TILE_DOOR)

    # Trees decoration
    tree_positions = [
        (10, 10), (11, 10), (27, 5), (28, 5), (27, 6),
        (15, 24), (16, 24), (17, 24), (35, 20), (36, 20),
        (2, 10), (2, 11), (37, 10), (37, 11),
    ]
    for tx, ty in tree_positions:
        m.set_tile(tx, ty, TILE_TREE)

    # NPC: Elder (quest giver)
    elder = NPC("Village Elder", "quest", 20, 10,
                dialogue=[
                    "Welcome, adventurer! Our village needs your help.",
                    "Slimes have been appearing near the outskirts.",
                    "If you could clear them out, we'd be grateful!",
                    "Talk to me again when you've dealt with them.",
                ],
                quest=create_quest_slime_trouble(),
                color=(180, 140, 100))
    m.npcs.append(elder)

    # NPC: Merchant
    merchant = NPC("General Store", "merchant", 14, 7,
                   dialogue=[
                       "Welcome to my shop! Take a look around.",
                       "I have all the essentials an adventurer needs.",
                   ],
                   shop_items=VILLAGE_SHOP,
                   color=(100, 140, 180))
    m.npcs.append(merchant)

    # NPC: Healer
    healer = NPC("Sister Maria", "healer", 6, 7,
                 dialogue=[
                     "Blessings upon you, traveler.",
                     "Let me tend to your wounds. Rest here and recover.",
                 ],
                 color=(220, 220, 240))
    m.npcs.append(healer)

    # NPC: Villager with hints
    villager1 = NPC("Old Farmer", "villager", 26, 22,
                    dialogue=[
                        "I've heard strange noises from the forest to the east.",
                        "They say goblins have set up camp there.",
                        "Be careful if you venture out!",
                    ],
                    color=(140, 100, 70))
    m.npcs.append(villager1)

    # NPC: Wolf quest giver
    hunter = NPC("Hunter Kael", "quest", 30, 12,
                 dialogue=[
                     "Hail! I'm tracking a pack of dire wolves.",
                     "They've grown bold, attacking travelers on the road.",
                     "Help me thin their numbers, will you?",
                 ],
                 quest=create_quest_wolf_pelts(),
                 color=(100, 120, 80))
    m.npcs.append(hunter)

    # Transitions to other maps
    m.transitions.append({"x": 39, "y": 14, "target_map": "village_outskirts",
                          "target_x": 1, "target_y": 15, "label": "Village Outskirts"})
    m.transitions.append({"x": 39, "y": 15, "target_map": "village_outskirts",
                          "target_x": 1, "target_y": 15, "label": "Village Outskirts"})
    m.set_tile(39, 14, TILE_PATH)
    m.set_tile(39, 15, TILE_PATH)

    m.spawn_x = 20
    m.spawn_y = 15

    return m


def create_village_outskirts_map():
    """The area just outside the village - first combat zone."""
    m = TileMap(50, 35, "Village Outskirts", encounter_area="village_outskirts")

    m.fill_rect(0, 0, 49, 34, TILE_GRASS)
    m.draw_border(TILE_TREE)

    # Path from village
    m.fill_rect(0, 14, 25, 16, TILE_PATH)
    m.fill_rect(25, 10, 27, 25, TILE_PATH)
    m.fill_rect(27, 10, 49, 12, TILE_PATH)

    # Scattered trees
    for _ in range(30):
        tx = random.randint(2, 47)
        ty = random.randint(2, 32)
        if m.get_tile(tx, ty) == TILE_GRASS:
            m.set_tile(tx, ty, TILE_TREE)

    # Small pond
    m.fill_rect(10, 25, 14, 28, TILE_WATER)

    # Sand areas
    m.fill_rect(35, 20, 42, 27, TILE_SAND)

    # Chest with starter loot
    m.chests.append({"x": 38, "y": 24, "items": [create_health_potion(), create_health_potion()],
                     "opened": False})
    m.set_tile(38, 24, TILE_CHEST)

    # Back to village
    m.transitions.append({"x": 0, "y": 14, "target_map": "village",
                          "target_x": 38, "target_y": 14, "label": "Peaceful Village"})
    m.transitions.append({"x": 0, "y": 15, "target_map": "village",
                          "target_x": 38, "target_y": 14, "label": "Peaceful Village"})
    m.transitions.append({"x": 0, "y": 16, "target_map": "village",
                          "target_x": 38, "target_y": 15, "label": "Peaceful Village"})
    m.set_tile(0, 14, TILE_PATH)
    m.set_tile(0, 15, TILE_PATH)
    m.set_tile(0, 16, TILE_PATH)

    # To dark forest
    m.transitions.append({"x": 49, "y": 10, "target_map": "dark_forest",
                          "target_x": 1, "target_y": 15, "label": "Dark Forest"})
    m.transitions.append({"x": 49, "y": 11, "target_map": "dark_forest",
                          "target_x": 1, "target_y": 15, "label": "Dark Forest"})
    m.transitions.append({"x": 49, "y": 12, "target_map": "dark_forest",
                          "target_x": 1, "target_y": 15, "label": "Dark Forest"})
    m.set_tile(49, 10, TILE_PATH)
    m.set_tile(49, 11, TILE_PATH)
    m.set_tile(49, 12, TILE_PATH)

    # Encounter zones
    m.encounter_zones.append({"x1": 2, "y1": 2, "x2": 48, "y2": 33,
                              "area": "village_outskirts"})

    m.spawn_x = 1
    m.spawn_y = 15

    # NPC: Wandering merchant
    wander_merch = NPC("Traveling Merchant", "merchant", 20, 20,
                       dialogue=[
                           "Fine wares! Come have a look!",
                           "I travel between the village and forest.",
                       ],
                       shop_items=VILLAGE_SHOP,
                       color=(150, 120, 80))
    m.npcs.append(wander_merch)

    return m


def create_dark_forest_map():
    """A dark, dangerous forest with tougher enemies."""
    m = TileMap(55, 40, "Dark Forest", encounter_area="dark_forest",
                ambient_color=(0, 10, 0, 60))

    m.fill_rect(0, 0, 54, 39, TILE_GRASS)
    m.draw_border(TILE_TREE)

    # Dense trees
    for _ in range(80):
        tx = random.randint(2, 52)
        ty = random.randint(2, 37)
        m.set_tile(tx, ty, TILE_TREE)

    # Clear path through forest
    m.fill_rect(0, 14, 30, 16, TILE_PATH)
    m.fill_rect(28, 10, 30, 30, TILE_PATH)
    m.fill_rect(28, 28, 54, 30, TILE_PATH)

    # Clear areas around paths
    for y in range(40):
        for x in range(55):
            if m.get_tile(x, y) == TILE_PATH:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = x + dx, y + dy
                        if m.get_tile(nx, ny) == TILE_TREE and random.random() < 0.5:
                            m.set_tile(nx, ny, TILE_GRASS)

    # Swamp area
    m.fill_rect(8, 25, 16, 32, TILE_WATER)
    m.fill_rect(10, 24, 14, 33, TILE_WATER)

    # Goblin camp area (stone floor clearing)
    m.fill_rect(40, 5, 50, 15, TILE_STONE)
    m.fill_rect(40, 5, 50, 5, TILE_WALL)
    m.fill_rect(40, 15, 50, 15, TILE_WALL)
    m.fill_rect(40, 5, 40, 15, TILE_WALL)
    m.fill_rect(50, 5, 50, 15, TILE_WALL)
    m.set_tile(45, 15, TILE_DOOR)
    m.set_tile(46, 15, TILE_DOOR)

    # Boss spawn: Goblin King
    m.boss_spawns.append({"x": 45, "y": 10, "boss_func": create_boss_goblin_king,
                          "defeated": False, "level": 5})

    # Chests
    m.chests.append({"x": 48, "y": 7, "items": [create_health_potion(), create_mana_potion()],
                     "opened": False})
    m.set_tile(48, 7, TILE_CHEST)

    # Back to outskirts
    m.transitions.append({"x": 0, "y": 14, "target_map": "village_outskirts",
                          "target_x": 48, "target_y": 11, "label": "Village Outskirts"})
    m.transitions.append({"x": 0, "y": 15, "target_map": "village_outskirts",
                          "target_x": 48, "target_y": 11, "label": "Village Outskirts"})
    m.transitions.append({"x": 0, "y": 16, "target_map": "village_outskirts",
                          "target_x": 48, "target_y": 11, "label": "Village Outskirts"})
    m.set_tile(0, 14, TILE_PATH)
    m.set_tile(0, 15, TILE_PATH)
    m.set_tile(0, 16, TILE_PATH)

    # To mountain pass
    m.transitions.append({"x": 54, "y": 28, "target_map": "mountain_pass",
                          "target_x": 1, "target_y": 15, "label": "Mountain Pass"})
    m.transitions.append({"x": 54, "y": 29, "target_map": "mountain_pass",
                          "target_x": 1, "target_y": 15, "label": "Mountain Pass"})
    m.transitions.append({"x": 54, "y": 30, "target_map": "mountain_pass",
                          "target_x": 1, "target_y": 15, "label": "Mountain Pass"})
    m.set_tile(54, 28, TILE_PATH)
    m.set_tile(54, 29, TILE_PATH)
    m.set_tile(54, 30, TILE_PATH)

    # NPCs
    forest_quest = NPC("Forest Warden", "quest", 15, 15,
                       dialogue=[
                           "The forest grows darker each day...",
                           "Undead creatures roam these woods now.",
                           "Please, help us cleanse this corruption!",
                       ],
                       quest=create_quest_dark_forest(),
                       color=(80, 120, 60))
    m.npcs.append(forest_quest)

    goblin_quest = NPC("Scout Lyra", "quest", 35, 17,
                       dialogue=[
                           "I've been tracking the goblin camp to the north.",
                           "Their king commands them from within.",
                           "We need someone brave enough to end his reign!",
                       ],
                       quest=create_quest_goblin_camp(),
                       color=(120, 100, 80))
    m.npcs.append(goblin_quest)

    forest_merchant = NPC("Hermit Alchemist", "merchant", 22, 22,
                          dialogue=[
                              "Ah, a visitor! I don't get many out here.",
                              "I've brewed some potions you might find useful.",
                          ],
                          shop_items=FOREST_SHOP,
                          color=(100, 80, 120))
    m.npcs.append(forest_merchant)

    m.encounter_zones.append({"x1": 2, "y1": 2, "x2": 52, "y2": 37,
                              "area": "dark_forest"})

    m.spawn_x = 1
    m.spawn_y = 15

    return m


def create_mountain_pass_map():
    """A treacherous mountain path with tough enemies."""
    m = TileMap(50, 40, "Mountain Pass", encounter_area="mountain_pass",
                ambient_color=(20, 20, 30, 40))

    m.fill_rect(0, 0, 49, 39, TILE_STONE)
    m.draw_border(TILE_WALL)

    # Mountain terrain - lots of walls
    for _ in range(60):
        wx = random.randint(2, 47)
        wy = random.randint(2, 37)
        ww = random.randint(2, 5)
        wh = random.randint(2, 4)
        m.fill_rect(wx, wy, min(47, wx + ww), min(37, wy + wh), TILE_WALL)

    # Carve paths
    m.fill_rect(0, 14, 25, 16, TILE_STONE)
    m.fill_rect(23, 5, 25, 35, TILE_STONE)
    m.fill_rect(23, 5, 49, 7, TILE_STONE)

    # Ice patches
    for _ in range(15):
        ix = random.randint(3, 46)
        iy = random.randint(3, 36)
        if m.get_tile(ix, iy) == TILE_STONE:
            m.fill_rect(ix, iy, min(47, ix + 2), min(37, iy + 2), TILE_ICE)

    # Lava cracks
    for _ in range(8):
        lx = random.randint(5, 44)
        ly = random.randint(5, 34)
        length = random.randint(3, 7)
        for i in range(length):
            if random.random() < 0.5:
                m.set_tile(min(47, lx + i), ly, TILE_LAVA)
            else:
                m.set_tile(lx, min(37, ly + i), TILE_LAVA)

    # Back to forest
    m.transitions.append({"x": 0, "y": 14, "target_map": "dark_forest",
                          "target_x": 53, "target_y": 29, "label": "Dark Forest"})
    m.transitions.append({"x": 0, "y": 15, "target_map": "dark_forest",
                          "target_x": 53, "target_y": 29, "label": "Dark Forest"})
    m.transitions.append({"x": 0, "y": 16, "target_map": "dark_forest",
                          "target_x": 53, "target_y": 29, "label": "Dark Forest"})
    m.set_tile(0, 14, TILE_STONE)
    m.set_tile(0, 15, TILE_STONE)
    m.set_tile(0, 16, TILE_STONE)

    # To shadow citadel
    m.transitions.append({"x": 49, "y": 5, "target_map": "shadow_citadel",
                          "target_x": 1, "target_y": 20, "label": "Shadow Citadel"})
    m.transitions.append({"x": 49, "y": 6, "target_map": "shadow_citadel",
                          "target_x": 1, "target_y": 20, "label": "Shadow Citadel"})
    m.transitions.append({"x": 49, "y": 7, "target_map": "shadow_citadel",
                          "target_x": 1, "target_y": 20, "label": "Shadow Citadel"})
    m.set_tile(49, 5, TILE_STONE)
    m.set_tile(49, 6, TILE_STONE)
    m.set_tile(49, 7, TILE_STONE)

    # NPCs
    mountain_quest = NPC("Mountain Guide", "quest", 12, 15,
                         dialogue=[
                             "The pass ahead is incredibly dangerous.",
                             "Golems of ice and elementals of fire block the way.",
                             "Clear them out so travelers can pass safely!",
                         ],
                         quest=create_quest_mountain_pass(),
                         color=(140, 140, 160))
    m.npcs.append(mountain_quest)

    dragon_quest = NPC("Dragon Scholar", "quest", 30, 10,
                       dialogue=[
                           "I've been studying the dragon whelps here.",
                           "They grow rapidly and could threaten the realm!",
                           "We must cull their numbers before it's too late.",
                       ],
                       quest=create_quest_dragon_threat(),
                       color=(180, 160, 120))
    m.npcs.append(dragon_quest)

    mountain_merchant = NPC("Dwarf Blacksmith", "merchant", 20, 25,
                            dialogue=[
                                "Forged in the heart of the mountain!",
                                "Only the finest equipment here.",
                            ],
                            shop_items=MOUNTAIN_SHOP,
                            color=(160, 120, 80))
    m.npcs.append(mountain_merchant)

    # Chest
    m.chests.append({"x": 40, "y": 20, "items": [create_health_potion(), create_mana_potion(),
                                                   create_health_potion()],
                     "opened": False})
    m.set_tile(40, 20, TILE_CHEST)

    m.encounter_zones.append({"x1": 2, "y1": 2, "x2": 47, "y2": 37,
                              "area": "mountain_pass"})

    m.spawn_x = 1
    m.spawn_y = 15

    return m


def create_shadow_citadel_map():
    """The final dungeon - Shadow Citadel."""
    m = TileMap(55, 45, "Shadow Citadel", encounter_area="shadow_citadel",
                ambient_color=(15, 0, 20, 80))

    m.fill_rect(0, 0, 54, 44, TILE_DARK_STONE)
    m.draw_border(TILE_WALL)

    # Create dungeon rooms
    # Entry hall
    m.fill_rect(1, 18, 15, 22, TILE_DARK_STONE)

    # Main corridor
    m.fill_rect(15, 15, 17, 30, TILE_DARK_STONE)

    # West chamber
    m.fill_rect(3, 5, 15, 15, TILE_DARK_STONE)
    m.fill_rect(3, 5, 15, 5, TILE_WALL)
    m.fill_rect(3, 15, 15, 15, TILE_WALL)
    m.fill_rect(3, 5, 3, 15, TILE_WALL)
    m.fill_rect(15, 5, 15, 15, TILE_WALL)
    m.set_tile(15, 10, TILE_DOOR)

    # East chamber
    m.fill_rect(20, 5, 35, 15, TILE_DARK_STONE)
    m.fill_rect(20, 5, 35, 5, TILE_WALL)
    m.fill_rect(20, 15, 35, 15, TILE_WALL)
    m.fill_rect(20, 5, 20, 15, TILE_WALL)
    m.fill_rect(35, 5, 35, 15, TILE_WALL)
    m.set_tile(20, 10, TILE_DOOR)
    m.fill_rect(15, 8, 20, 12, TILE_DARK_STONE)

    # South chamber
    m.fill_rect(10, 30, 30, 40, TILE_DARK_STONE)
    m.fill_rect(10, 30, 30, 30, TILE_WALL)
    m.fill_rect(10, 40, 30, 40, TILE_WALL)
    m.fill_rect(10, 30, 10, 40, TILE_WALL)
    m.fill_rect(30, 30, 30, 40, TILE_WALL)
    m.set_tile(20, 30, TILE_DOOR)
    m.fill_rect(15, 25, 17, 30, TILE_DARK_STONE)

    # Throne room (Lich boss)
    m.fill_rect(38, 5, 52, 20, TILE_DARK_STONE)
    m.fill_rect(38, 5, 52, 5, TILE_WALL)
    m.fill_rect(38, 20, 52, 20, TILE_WALL)
    m.fill_rect(38, 5, 38, 20, TILE_WALL)
    m.fill_rect(52, 5, 52, 20, TILE_WALL)
    m.set_tile(38, 12, TILE_DOOR)
    m.fill_rect(35, 8, 38, 14, TILE_DARK_STONE)

    # Dragon's lair
    m.fill_rect(35, 30, 52, 42, TILE_DARK_STONE)
    m.fill_rect(35, 30, 52, 30, TILE_WALL)
    m.fill_rect(35, 42, 52, 42, TILE_WALL)
    m.fill_rect(35, 30, 35, 42, TILE_WALL)
    m.fill_rect(52, 30, 52, 42, TILE_WALL)
    m.set_tile(35, 36, TILE_DOOR)
    m.fill_rect(30, 33, 35, 38, TILE_DARK_STONE)
    # Lava in dragon lair
    m.fill_rect(40, 33, 48, 39, TILE_LAVA)
    m.fill_rect(42, 34, 46, 38, TILE_DARK_STONE)

    # Fill walls between areas to make it dungeon-like
    for y in range(45):
        for x in range(55):
            if m.get_tile(x, y) == TILE_DARK_STONE:
                continue
            if m.get_tile(x, y) not in (TILE_WALL, TILE_DOOR, TILE_LAVA):
                m.set_tile(x, y, TILE_WALL)

    # Boss spawns
    m.boss_spawns.append({"x": 45, "y": 12, "boss_func": create_boss_lich,
                          "defeated": False, "level": 10})
    m.boss_spawns.append({"x": 44, "y": 36, "boss_func": create_boss_dragon,
                          "defeated": False, "level": 15})

    # Chests
    m.chests.append({"x": 8, "y": 10, "items": [create_health_potion(), create_mana_potion()],
                     "opened": False})
    m.set_tile(8, 10, TILE_CHEST)
    m.chests.append({"x": 28, "y": 10, "items": [create_health_potion()],
                     "opened": False})
    m.set_tile(28, 10, TILE_CHEST)

    # Back to mountain
    m.transitions.append({"x": 0, "y": 19, "target_map": "mountain_pass",
                          "target_x": 48, "target_y": 6, "label": "Mountain Pass"})
    m.transitions.append({"x": 0, "y": 20, "target_map": "mountain_pass",
                          "target_x": 48, "target_y": 6, "label": "Mountain Pass"})
    m.transitions.append({"x": 0, "y": 21, "target_map": "mountain_pass",
                          "target_x": 48, "target_y": 6, "label": "Mountain Pass"})

    # NPCs
    lich_quest = NPC("Spirit of the Fallen", "quest", 5, 20,
                     dialogue=[
                         "You... you can see me?",
                         "The Lich... in the throne room... destroyed everything.",
                         "Please... avenge us. Destroy the Lich!",
                     ],
                     quest=create_quest_lich_lord(),
                     color=(180, 180, 220))
    m.npcs.append(lich_quest)

    dragon_quest = NPC("Ancient Guardian", "quest", 20, 35,
                       dialogue=[
                           "The Elder Dragon sleeps in the depths below.",
                           "If it fully awakens, nothing can stop it.",
                           "You are our last hope, hero.",
                       ],
                       quest=create_quest_elder_dragon(),
                       color=(200, 180, 100))
    m.npcs.append(dragon_quest)

    m.encounter_zones.append({"x1": 2, "y1": 2, "x2": 52, "y2": 43,
                              "area": "shadow_citadel"})

    m.spawn_x = 1
    m.spawn_y = 20

    return m


# ─── Map Registry ────────────────────────────────────────────────────

MAP_BUILDERS = {
    "village": create_village_map,
    "village_outskirts": create_village_outskirts_map,
    "dark_forest": create_dark_forest_map,
    "mountain_pass": create_mountain_pass_map,
    "shadow_citadel": create_shadow_citadel_map,
}


def load_map(map_name):
    """Load a map by name."""
    builder = MAP_BUILDERS.get(map_name)
    if builder:
        return builder()
    return create_village_map()
