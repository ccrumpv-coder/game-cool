"""Entity system: Player, Enemies, NPCs."""

import math
import random
from src.constants import (
    TILE_SIZE, CLASS_WARRIOR, CLASS_MAGE, CLASS_ROGUE, CLASS_RANGER, CLASS_PALADIN,
    ELEM_PHYSICAL, ELEM_FIRE, ELEM_ICE, ELEM_LIGHTNING, ELEM_HOLY, ELEM_DARK, ELEM_POISON,
    BASE_XP_REQUIREMENT, XP_GROWTH_FACTOR, MAX_LEVEL,
    SLOT_WEAPON, SLOT_ARMOR, SLOT_HELMET, SLOT_BOOTS, SLOT_ACCESSORY,
    RED, BLUE, GREEN, YELLOW, PURPLE, CYAN, ORANGE, WHITE, GOLD,
    DARK_GREEN, DARK_RED, LIGHT_GRAY, BROWN, DARK_BROWN
)


# ─── Abilities / Spells ─────────────────────────────────────────────

class Ability:
    """A combat ability or spell."""

    def __init__(self, name, description, mp_cost, damage_mult=1.0, element=ELEM_PHYSICAL,
                 heals=False, heal_amount=0, targets_all=False, buff=None, debuff=None,
                 cooldown=0, level_req=1):
        self.name = name
        self.description = description
        self.mp_cost = mp_cost
        self.damage_mult = damage_mult
        self.element = element
        self.heals = heals
        self.heal_amount = heal_amount
        self.targets_all = targets_all
        self.buff = buff  # dict: {"stat": str, "amount": int, "duration": int}
        self.debuff = debuff
        self.cooldown = cooldown
        self.current_cooldown = 0
        self.level_req = level_req

    def is_available(self, caster_mp, caster_level):
        """Check if ability can be used."""
        return (self.current_cooldown <= 0 and
                caster_mp >= self.mp_cost and
                caster_level >= self.level_req)

    def use(self):
        """Use the ability (sets cooldown)."""
        self.current_cooldown = self.cooldown

    def tick_cooldown(self):
        """Reduce cooldown by 1 turn."""
        if self.current_cooldown > 0:
            self.current_cooldown -= 1


# ─── Class definitions ───────────────────────────────────────────────

CLASS_DATA = {
    CLASS_WARRIOR: {
        "color": RED,
        "base_hp": 120, "base_mp": 30, "base_atk": 14, "base_def": 12,
        "base_mag": 4, "base_spd": 8,
        "hp_growth": 15, "mp_growth": 3, "atk_growth": 3, "def_growth": 3,
        "mag_growth": 1, "spd_growth": 1,
        "description": "A mighty frontline fighter with high HP and defense.",
        "abilities": [
            Ability("Slash", "A powerful sword strike", 0, 1.2, ELEM_PHYSICAL),
            Ability("Shield Bash", "Stun attack with shield", 8, 0.8, ELEM_PHYSICAL,
                    debuff={"stat": "spd", "amount": -3, "duration": 2}),
            Ability("War Cry", "Boost attack power", 12, 0, ELEM_PHYSICAL,
                    buff={"stat": "atk", "amount": 5, "duration": 3}, level_req=3),
            Ability("Whirlwind", "Hit all enemies", 20, 0.9, ELEM_PHYSICAL,
                    targets_all=True, level_req=6),
            Ability("Berserker Rage", "Massive damage but lower defense", 30, 2.5, ELEM_PHYSICAL,
                    debuff={"stat": "def", "amount": -5, "duration": 2}, level_req=10, cooldown=3),
        ]
    },
    CLASS_MAGE: {
        "color": BLUE,
        "base_hp": 70, "base_mp": 100, "base_atk": 5, "base_def": 6,
        "base_mag": 16, "base_spd": 9,
        "hp_growth": 8, "mp_growth": 12, "atk_growth": 1, "def_growth": 1,
        "mag_growth": 4, "spd_growth": 1,
        "description": "A master of arcane magic with devastating spells.",
        "abilities": [
            Ability("Fireball", "Hurl a ball of fire", 10, 1.5, ELEM_FIRE),
            Ability("Ice Shard", "Pierce with frozen crystal", 10, 1.4, ELEM_ICE),
            Ability("Lightning Bolt", "Strike with electricity", 15, 1.8, ELEM_LIGHTNING, level_req=4),
            Ability("Blizzard", "Freeze all enemies", 30, 1.2, ELEM_ICE,
                    targets_all=True, level_req=8),
            Ability("Meteor Storm", "Rain destruction from above", 50, 2.5, ELEM_FIRE,
                    targets_all=True, level_req=12, cooldown=4),
            Ability("Arcane Heal", "Restore HP with magic", 20, 0, ELEM_PHYSICAL,
                    heals=True, heal_amount=0.4, level_req=5),
        ]
    },
    CLASS_ROGUE: {
        "color": PURPLE,
        "base_hp": 85, "base_mp": 50, "base_atk": 12, "base_def": 7,
        "base_mag": 6, "base_spd": 15,
        "hp_growth": 10, "mp_growth": 5, "atk_growth": 3, "def_growth": 1,
        "mag_growth": 1, "spd_growth": 3,
        "description": "A swift shadow striker with critical hits and evasion.",
        "abilities": [
            Ability("Backstab", "Strike from behind for bonus damage", 0, 1.5, ELEM_PHYSICAL),
            Ability("Poison Blade", "Coat weapon in poison", 10, 1.0, ELEM_POISON,
                    debuff={"stat": "hp", "amount": -5, "duration": 3}),
            Ability("Smoke Bomb", "Boost evasion greatly", 15, 0, ELEM_PHYSICAL,
                    buff={"stat": "spd", "amount": 8, "duration": 2}, level_req=4),
            Ability("Fan of Knives", "Throw knives at all enemies", 20, 0.8, ELEM_PHYSICAL,
                    targets_all=True, level_req=7),
            Ability("Assassinate", "Devastating single-target strike", 35, 3.0, ELEM_DARK,
                    level_req=11, cooldown=3),
        ]
    },
    CLASS_RANGER: {
        "color": GREEN,
        "base_hp": 90, "base_mp": 60, "base_atk": 11, "base_def": 8,
        "base_mag": 8, "base_spd": 12,
        "hp_growth": 11, "mp_growth": 6, "atk_growth": 2, "def_growth": 2,
        "mag_growth": 2, "spd_growth": 2,
        "description": "A versatile archer with nature magic and traps.",
        "abilities": [
            Ability("Power Shot", "A focused arrow strike", 0, 1.3, ELEM_PHYSICAL),
            Ability("Entangling Vines", "Slow an enemy with nature", 10, 0.6, ELEM_PHYSICAL,
                    debuff={"stat": "spd", "amount": -5, "duration": 2}),
            Ability("Heal Herbs", "Heal with natural remedies", 15, 0, ELEM_PHYSICAL,
                    heals=True, heal_amount=0.3, level_req=3),
            Ability("Multishot", "Fire arrows at all foes", 22, 0.7, ELEM_PHYSICAL,
                    targets_all=True, level_req=6),
            Ability("Nature's Wrath", "Unleash the fury of nature", 40, 2.2, ELEM_PHYSICAL,
                    targets_all=True, level_req=10, cooldown=3),
        ]
    },
    CLASS_PALADIN: {
        "color": GOLD,
        "base_hp": 110, "base_mp": 60, "base_atk": 10, "base_def": 14,
        "base_mag": 10, "base_spd": 7,
        "hp_growth": 13, "mp_growth": 7, "atk_growth": 2, "def_growth": 3,
        "mag_growth": 2, "spd_growth": 1,
        "description": "A holy knight who protects allies and smites evil.",
        "abilities": [
            Ability("Holy Strike", "Smite with divine power", 5, 1.3, ELEM_HOLY),
            Ability("Lay on Hands", "Heal with holy energy", 15, 0, ELEM_HOLY,
                    heals=True, heal_amount=0.5, level_req=2),
            Ability("Divine Shield", "Boost defense greatly", 20, 0, ELEM_HOLY,
                    buff={"stat": "def", "amount": 8, "duration": 3}, level_req=5),
            Ability("Smite Evil", "Extra damage vs undead/dark", 25, 2.0, ELEM_HOLY, level_req=8),
            Ability("Holy Nova", "Heal self and damage all foes", 40, 1.5, ELEM_HOLY,
                    targets_all=True, heals=True, heal_amount=0.3, level_req=12, cooldown=4),
        ]
    }
}


# ─── Stat Block ──────────────────────────────────────────────────────

class Stats:
    """Character statistics."""

    def __init__(self, hp=100, mp=50, atk=10, defense=10, mag=10, spd=10):
        self.max_hp = hp
        self.hp = hp
        self.max_mp = mp
        self.mp = mp
        self.atk = atk
        self.defense = defense
        self.mag = mag
        self.spd = spd

        # Buff/debuff tracking
        self.buffs = []  # list of {"stat", "amount", "duration"}
        self.base_atk = atk
        self.base_def = defense
        self.base_mag = mag
        self.base_spd = spd

    def apply_buff(self, buff):
        """Apply a buff/debuff."""
        self.buffs.append({**buff})
        self._recalc_stats()

    def tick_buffs(self):
        """Reduce buff durations."""
        for b in self.buffs:
            b["duration"] -= 1
        self.buffs = [b for b in self.buffs if b["duration"] > 0]
        self._recalc_stats()

    def _recalc_stats(self):
        """Recalculate stats from base + buffs."""
        self.atk = self.base_atk + sum(b["amount"] for b in self.buffs if b["stat"] == "atk")
        self.defense = self.base_def + sum(b["amount"] for b in self.buffs if b["stat"] == "def")
        self.mag = self.base_mag + sum(b["amount"] for b in self.buffs if b["stat"] == "mag")
        self.spd = self.base_spd + sum(b["amount"] for b in self.buffs if b["stat"] == "spd")

        # Apply HP poison/regen
        hp_effects = sum(b["amount"] for b in self.buffs if b["stat"] == "hp")
        if hp_effects != 0:
            self.hp = max(1, min(self.max_hp, self.hp + hp_effects))

    def heal(self, amount):
        """Heal HP."""
        self.hp = min(self.max_hp, self.hp + amount)

    def restore_mp(self, amount):
        """Restore MP."""
        self.mp = min(self.max_mp, self.mp + amount)

    @property
    def is_alive(self):
        return self.hp > 0

    def to_dict(self):
        """Serialize stats."""
        return {
            "max_hp": self.max_hp, "hp": self.hp,
            "max_mp": self.max_mp, "mp": self.mp,
            "atk": self.base_atk, "defense": self.base_def,
            "mag": self.base_mag, "spd": self.base_spd,
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize stats."""
        s = cls(data["max_hp"], data["max_mp"], data["atk"],
                data["defense"], data["mag"], data["spd"])
        s.hp = data["hp"]
        s.mp = data.get("mp", s.max_mp)
        return s


# ─── Player ──────────────────────────────────────────────────────────

class Player:
    """The player character."""

    def __init__(self, name, char_class):
        self.name = name
        self.char_class = char_class
        self.level = 1
        self.xp = 0
        self.gold = 50

        data = CLASS_DATA[char_class]
        self.stats = Stats(
            hp=data["base_hp"], mp=data["base_mp"],
            atk=data["base_atk"], defense=data["base_def"],
            mag=data["base_mag"], spd=data["base_spd"]
        )
        self.abilities = [Ability(a.name, a.description, a.mp_cost, a.damage_mult,
                                   a.element, a.heals, a.heal_amount, a.targets_all,
                                   a.buff, a.debuff, a.cooldown, a.level_req)
                          for a in data["abilities"]]

        # Position (tile coords)
        self.tile_x = 5
        self.tile_y = 5
        self.pixel_x = self.tile_x * TILE_SIZE
        self.pixel_y = self.tile_y * TILE_SIZE
        self.facing = "down"

        # Equipment
        self.equipment = {
            SLOT_WEAPON: None,
            SLOT_ARMOR: None,
            SLOT_HELMET: None,
            SLOT_BOOTS: None,
            SLOT_ACCESSORY: None,
        }

        # Inventory (list of Item objects)
        self.inventory = []
        self.max_inventory = 30

        # Quests
        self.active_quests = []
        self.completed_quests = []

        # Animation
        self.anim_timer = 0
        self.anim_frame = 0
        self.moving = False

        # Current map
        self.current_map = "village"

    @property
    def xp_to_next_level(self):
        return int(BASE_XP_REQUIREMENT * (XP_GROWTH_FACTOR ** (self.level - 1)))

    def gain_xp(self, amount):
        """Gain XP and return list of level ups."""
        level_ups = []
        self.xp += amount
        while self.xp >= self.xp_to_next_level and self.level < MAX_LEVEL:
            self.xp -= self.xp_to_next_level
            self.level += 1
            level_ups.append(self._apply_level_up())
        return level_ups

    def _apply_level_up(self):
        """Apply stat gains for a level up."""
        data = CLASS_DATA[self.char_class]
        gains = {
            "hp": data["hp_growth"],
            "mp": data["mp_growth"],
            "atk": data["atk_growth"],
            "def": data["def_growth"],
            "mag": data["mag_growth"],
            "spd": data["spd_growth"],
        }
        self.stats.max_hp += gains["hp"]
        self.stats.hp = self.stats.max_hp
        self.stats.max_mp += gains["mp"]
        self.stats.mp = self.stats.max_mp
        self.stats.base_atk += gains["atk"]
        self.stats.atk = self.stats.base_atk
        self.stats.base_def += gains["def"]
        self.stats.defense = self.stats.base_def
        self.stats.base_mag += gains["mag"]
        self.stats.mag = self.stats.base_mag
        self.stats.base_spd += gains["spd"]
        self.stats.spd = self.stats.base_spd
        return gains

    def get_total_atk(self):
        """Get attack including equipment."""
        bonus = sum(eq.stats.get("atk", 0) for eq in self.equipment.values() if eq)
        return self.stats.atk + bonus

    def get_total_def(self):
        """Get defense including equipment."""
        bonus = sum(eq.stats.get("defense", 0) for eq in self.equipment.values() if eq)
        return self.stats.defense + bonus

    def get_total_mag(self):
        """Get magic including equipment."""
        bonus = sum(eq.stats.get("mag", 0) for eq in self.equipment.values() if eq)
        return self.stats.mag + bonus

    def get_total_spd(self):
        """Get speed including equipment."""
        bonus = sum(eq.stats.get("spd", 0) for eq in self.equipment.values() if eq)
        return self.stats.spd + bonus

    def equip_item(self, item):
        """Equip an item, unequipping current if needed."""
        if item.slot and item.slot in self.equipment:
            old = self.equipment[item.slot]
            self.equipment[item.slot] = item
            if item in self.inventory:
                self.inventory.remove(item)
            if old:
                self.inventory.append(old)
            return old
        return None

    def unequip_item(self, slot):
        """Unequip an item from a slot."""
        item = self.equipment.get(slot)
        if item and len(self.inventory) < self.max_inventory:
            self.equipment[slot] = None
            self.inventory.append(item)
            return item
        return None

    def add_item(self, item):
        """Add item to inventory."""
        if len(self.inventory) < self.max_inventory:
            self.inventory.append(item)
            return True
        return False

    def remove_item(self, item):
        """Remove item from inventory."""
        if item in self.inventory:
            self.inventory.remove(item)
            return True
        return False

    def use_item(self, item):
        """Use a consumable item."""
        if item.consumable and item in self.inventory:
            if item.heal_hp:
                self.stats.heal(item.heal_hp)
            if item.heal_mp:
                self.stats.restore_mp(item.heal_mp)
            if item.buff:
                self.stats.apply_buff(item.buff)
            self.inventory.remove(item)
            return True
        return False

    def get_available_abilities(self):
        """Get abilities available at current level and MP."""
        return [a for a in self.abilities
                if a.is_available(self.stats.mp, self.level)]

    def rest_at_inn(self):
        """Full restore at an inn."""
        self.stats.hp = self.stats.max_hp
        self.stats.mp = self.stats.max_mp
        self.stats.buffs.clear()

    def to_dict(self):
        """Serialize player."""
        return {
            "name": self.name,
            "char_class": self.char_class,
            "level": self.level,
            "xp": self.xp,
            "gold": self.gold,
            "stats": self.stats.to_dict(),
            "tile_x": self.tile_x,
            "tile_y": self.tile_y,
            "current_map": self.current_map,
            "equipment": {k: v.to_dict() if v else None
                          for k, v in self.equipment.items()},
            "inventory": [it.to_dict() for it in self.inventory],
            "active_quests": [q.to_dict() for q in self.active_quests],
            "completed_quests": [q.quest_id for q in self.completed_quests],
        }


# ─── Enemy ───────────────────────────────────────────────────────────

class Enemy:
    """An enemy in combat."""

    def __init__(self, name, level, stats, abilities=None, xp_reward=0,
                 gold_reward=0, loot_table=None, enemy_type="normal",
                 element=ELEM_PHYSICAL, color=RED, description=""):
        self.name = name
        self.level = level
        self.stats = stats
        self.abilities = abilities or []
        self.xp_reward = xp_reward
        self.gold_reward = gold_reward
        self.loot_table = loot_table or []
        self.enemy_type = enemy_type
        self.element = element
        self.color = color
        self.description = description

        # Combat state
        self.is_defending = False

    def choose_action(self):
        """AI: choose an ability or basic attack."""
        available = [a for a in self.abilities
                     if a.is_available(self.stats.mp, self.level)]

        # If low HP, prefer healing if available
        if self.stats.hp < self.stats.max_hp * 0.3:
            heals = [a for a in available if a.heals]
            if heals:
                return random.choice(heals)

        # Random choice with bias toward stronger moves
        if available and random.random() < 0.6:
            return random.choice(available)

        # Basic attack
        return Ability("Attack", "Basic attack", 0, 1.0, self.element)

    def get_loot(self):
        """Roll for loot drops."""
        drops = []
        for item_func, chance in self.loot_table:
            if random.random() < chance:
                drops.append(item_func())
        return drops


# ─── Enemy Templates ─────────────────────────────────────────────────

def create_slime(level=1):
    return Enemy(
        "Green Slime", level,
        Stats(hp=20 + level * 8, mp=5, atk=4 + level * 2, defense=3 + level,
              mag=2, spd=5 + level),
        abilities=[Ability("Acid Splash", "Corrosive attack", 3, 1.1, ELEM_POISON)],
        xp_reward=15 + level * 5, gold_reward=random.randint(3, 8),
        enemy_type="normal", color=(50, 200, 80),
        description="A wobbly blob of green goo."
    )


def create_skeleton(level=2):
    return Enemy(
        "Skeleton", level,
        Stats(hp=30 + level * 10, mp=10, atk=7 + level * 2, defense=5 + level,
              mag=3 + level, spd=7 + level),
        abilities=[
            Ability("Bone Throw", "Hurl a bone", 3, 1.2, ELEM_PHYSICAL),
            Ability("Dark Slash", "Shadow-infused strike", 8, 1.5, ELEM_DARK, level_req=3),
        ],
        xp_reward=25 + level * 8, gold_reward=random.randint(5, 15),
        enemy_type="undead", element=ELEM_DARK, color=(200, 200, 180),
        description="Animated bones wielding a rusty sword."
    )


def create_wolf(level=2):
    return Enemy(
        "Dire Wolf", level,
        Stats(hp=35 + level * 9, mp=5, atk=9 + level * 2, defense=4 + level,
              mag=2, spd=12 + level * 2),
        abilities=[
            Ability("Fang Strike", "Savage bite", 0, 1.3, ELEM_PHYSICAL),
            Ability("Pack Howl", "Boost attack", 5, 0, ELEM_PHYSICAL,
                    buff={"stat": "atk", "amount": 3, "duration": 2}),
        ],
        xp_reward=22 + level * 7, gold_reward=random.randint(2, 6),
        enemy_type="beast", color=(100, 80, 60),
        description="A fearsome wolf with glowing eyes."
    )


def create_goblin(level=1):
    return Enemy(
        "Goblin", level,
        Stats(hp=25 + level * 7, mp=10, atk=6 + level * 2, defense=4 + level,
              mag=3, spd=10 + level),
        abilities=[
            Ability("Stab", "Quick stab", 0, 1.1, ELEM_PHYSICAL),
            Ability("Dirty Trick", "Lower enemy defense", 5, 0.5, ELEM_PHYSICAL,
                    debuff={"stat": "def", "amount": -3, "duration": 2}),
        ],
        xp_reward=18 + level * 5, gold_reward=random.randint(5, 12),
        enemy_type="normal", color=(80, 140, 50),
        description="A sneaky little green menace."
    )


def create_fire_elemental(level=5):
    return Enemy(
        "Fire Elemental", level,
        Stats(hp=50 + level * 12, mp=40, atk=5 + level, defense=6 + level,
              mag=14 + level * 3, spd=8 + level),
        abilities=[
            Ability("Flame Burst", "Explosion of fire", 8, 1.4, ELEM_FIRE),
            Ability("Inferno", "Engulf all in flames", 20, 1.0, ELEM_FIRE,
                    targets_all=True, level_req=6),
        ],
        xp_reward=40 + level * 10, gold_reward=random.randint(10, 25),
        enemy_type="normal", element=ELEM_FIRE, color=(255, 100, 30),
        description="A swirling mass of living flame."
    )


def create_ice_golem(level=6):
    return Enemy(
        "Ice Golem", level,
        Stats(hp=80 + level * 15, mp=30, atk=10 + level * 2, defense=16 + level * 2,
              mag=8 + level, spd=4 + level),
        abilities=[
            Ability("Frost Slam", "Frozen fist smash", 5, 1.5, ELEM_ICE),
            Ability("Frozen Armor", "Boost defense", 10, 0, ELEM_ICE,
                    buff={"stat": "def", "amount": 6, "duration": 3}),
        ],
        xp_reward=50 + level * 12, gold_reward=random.randint(15, 30),
        enemy_type="normal", element=ELEM_ICE, color=(150, 200, 255),
        description="A towering construct of enchanted ice."
    )


def create_dark_mage(level=7):
    return Enemy(
        "Dark Mage", level,
        Stats(hp=45 + level * 10, mp=80, atk=4 + level, defense=5 + level,
              mag=16 + level * 3, spd=9 + level),
        abilities=[
            Ability("Shadow Bolt", "Dark energy missile", 8, 1.5, ELEM_DARK),
            Ability("Life Drain", "Steal life force", 12, 1.2, ELEM_DARK,
                    heals=True, heal_amount=0.3),
            Ability("Curse", "Weaken an enemy", 15, 0.5, ELEM_DARK,
                    debuff={"stat": "atk", "amount": -4, "duration": 3}),
        ],
        xp_reward=55 + level * 12, gold_reward=random.randint(15, 35),
        enemy_type="normal", element=ELEM_DARK, color=(80, 40, 120),
        description="A sinister spellcaster cloaked in shadow."
    )


def create_dragon_whelp(level=8):
    return Enemy(
        "Dragon Whelp", level,
        Stats(hp=70 + level * 14, mp=50, atk=12 + level * 3, defense=10 + level * 2,
              mag=12 + level * 2, spd=10 + level),
        abilities=[
            Ability("Claw Swipe", "Razor sharp claws", 0, 1.4, ELEM_PHYSICAL),
            Ability("Fire Breath", "Breathe flames", 15, 1.8, ELEM_FIRE, targets_all=True),
        ],
        xp_reward=70 + level * 15, gold_reward=random.randint(20, 40),
        enemy_type="beast", element=ELEM_FIRE, color=(180, 50, 30),
        description="A young dragon, still deadly."
    )


# ─── Boss Templates ──────────────────────────────────────────────────

def create_boss_goblin_king(level=5):
    return Enemy(
        "Goblin King", level,
        Stats(hp=200 + level * 20, mp=50, atk=12 + level * 3, defense=10 + level * 2,
              mag=8 + level, spd=8 + level),
        abilities=[
            Ability("Royal Decree", "Command subjects to attack", 10, 1.5, ELEM_PHYSICAL,
                    targets_all=True),
            Ability("Golden Shield", "Raise defense", 15, 0, ELEM_PHYSICAL,
                    buff={"stat": "def", "amount": 8, "duration": 3}),
            Ability("Crushing Blow", "Devastating overhead strike", 20, 2.2, ELEM_PHYSICAL,
                    cooldown=2),
        ],
        xp_reward=200 + level * 30, gold_reward=random.randint(80, 150),
        enemy_type="boss", color=(120, 160, 50),
        description="The self-proclaimed ruler of all goblins!"
    )


def create_boss_lich(level=10):
    return Enemy(
        "Ancient Lich", level,
        Stats(hp=300 + level * 25, mp=200, atk=8 + level * 2, defense=12 + level * 2,
              mag=22 + level * 4, spd=7 + level),
        abilities=[
            Ability("Death Bolt", "Necrotic energy blast", 15, 2.0, ELEM_DARK),
            Ability("Soul Drain", "Drain life from all", 25, 1.2, ELEM_DARK,
                    targets_all=True, heals=True, heal_amount=0.2),
            Ability("Raise Dead", "Boost own stats", 30, 0, ELEM_DARK,
                    buff={"stat": "atk", "amount": 6, "duration": 4}, cooldown=3),
            Ability("Apocalypse", "Ultimate destruction", 60, 2.5, ELEM_DARK,
                    targets_all=True, cooldown=5),
        ],
        xp_reward=500 + level * 50, gold_reward=random.randint(200, 400),
        enemy_type="boss", element=ELEM_DARK, color=(60, 30, 80),
        description="An ancient sorcerer who cheated death itself."
    )


def create_boss_dragon(level=15):
    return Enemy(
        "Elder Dragon", level,
        Stats(hp=500 + level * 30, mp=150, atk=18 + level * 4, defense=16 + level * 3,
              mag=16 + level * 3, spd=10 + level),
        abilities=[
            Ability("Dragon Claw", "Mighty claw strike", 0, 1.8, ELEM_PHYSICAL),
            Ability("Infernal Breath", "Fire across all foes", 20, 1.5, ELEM_FIRE,
                    targets_all=True),
            Ability("Wing Buffet", "Knockback attack", 15, 1.3, ELEM_PHYSICAL,
                    debuff={"stat": "spd", "amount": -4, "duration": 2}),
            Ability("Ancient Roar", "Terrifying roar", 25, 0, ELEM_PHYSICAL,
                    debuff={"stat": "atk", "amount": -5, "duration": 3},
                    targets_all=True),
            Ability("Cataclysm", "Ultimate dragon attack", 50, 3.0, ELEM_FIRE,
                    targets_all=True, cooldown=4),
        ],
        xp_reward=1000 + level * 100, gold_reward=random.randint(500, 1000),
        enemy_type="boss", element=ELEM_FIRE, color=(200, 40, 20),
        description="The mightiest of all dragons. Legend incarnate."
    )


# ─── Encounter Table ─────────────────────────────────────────────────

ENCOUNTER_TABLES = {
    "village_outskirts": [
        (create_slime, 1, 3, 0.4),
        (create_goblin, 1, 3, 0.4),
        (create_wolf, 2, 4, 0.2),
    ],
    "dark_forest": [
        (create_wolf, 3, 6, 0.3),
        (create_skeleton, 3, 6, 0.3),
        (create_goblin, 3, 5, 0.2),
        (create_dark_mage, 5, 8, 0.2),
    ],
    "mountain_pass": [
        (create_ice_golem, 5, 8, 0.3),
        (create_fire_elemental, 5, 8, 0.3),
        (create_dragon_whelp, 7, 10, 0.2),
        (create_dark_mage, 6, 9, 0.2),
    ],
    "shadow_citadel": [
        (create_dark_mage, 8, 12, 0.3),
        (create_skeleton, 8, 12, 0.3),
        (create_dragon_whelp, 9, 13, 0.2),
        (create_fire_elemental, 8, 11, 0.2),
    ],
}


def generate_encounter(area, player_level):
    """Generate a random encounter for an area."""
    table = ENCOUNTER_TABLES.get(area, ENCOUNTER_TABLES["village_outskirts"])
    enemies = []
    num_enemies = random.randint(1, 3)

    for _ in range(num_enemies):
        eligible = [(func, min_l, max_l, w) for func, min_l, max_l, w in table
                     if min_l <= player_level + 2]
        if not eligible:
            eligible = table[:1]

        weights = [w for _, _, _, w in eligible]
        total = sum(weights)
        r = random.uniform(0, total)
        cumulative = 0
        chosen = eligible[0]
        for entry in eligible:
            cumulative += entry[3]
            if r <= cumulative:
                chosen = entry
                break

        func, min_l, max_l, _ = chosen
        enemy_level = random.randint(
            max(min_l, player_level - 2),
            min(max_l, player_level + 2)
        )
        enemies.append(func(enemy_level))

    return enemies


# ─── NPC ─────────────────────────────────────────────────────────────

class NPC:
    """A non-player character."""

    def __init__(self, name, npc_type, tile_x, tile_y, dialogue=None,
                 quest=None, shop_items=None, color=BROWN):
        self.name = name
        self.npc_type = npc_type  # "villager", "merchant", "quest", "healer"
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.dialogue = dialogue or ["..."]
        self.quest = quest
        self.shop_items = shop_items or []
        self.color = color
        self.interacted = False
