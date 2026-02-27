"""Item system: weapons, armor, consumables, loot."""

import random
from src.constants import (
    SLOT_WEAPON, SLOT_ARMOR, SLOT_HELMET, SLOT_BOOTS, SLOT_ACCESSORY,
    RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY,
    ELEM_PHYSICAL, ELEM_FIRE, ELEM_ICE, ELEM_LIGHTNING, ELEM_HOLY, ELEM_DARK,
    RED, BLUE, GREEN, YELLOW, PURPLE, CYAN, ORANGE, WHITE, GOLD,
    LIGHT_GRAY, BROWN
)


class Item:
    """Base item class."""

    def __init__(self, name, description, item_type="misc", slot=None,
                 rarity=RARITY_COMMON, stats=None, consumable=False,
                 heal_hp=0, heal_mp=0, buff=None, value=10, level_req=1,
                 element=ELEM_PHYSICAL):
        self.name = name
        self.description = description
        self.item_type = item_type  # "weapon", "armor", "consumable", "misc", "quest"
        self.slot = slot
        self.rarity = rarity
        self.stats = stats or {}
        self.consumable = consumable
        self.heal_hp = heal_hp
        self.heal_mp = heal_mp
        self.buff = buff
        self.value = value
        self.level_req = level_req
        self.element = element

    def get_tooltip_lines(self):
        """Get tooltip text lines."""
        lines = [self.name]
        lines.append(f"[{self.rarity}]")
        if self.slot:
            lines.append(f"Slot: {self.slot}")
        if self.level_req > 1:
            lines.append(f"Requires Level {self.level_req}")
        lines.append("")
        lines.append(self.description)
        if self.stats:
            lines.append("")
            for stat, val in self.stats.items():
                prefix = "+" if val > 0 else ""
                stat_name = stat.replace("_", " ").title()
                lines.append(f"  {prefix}{val} {stat_name}")
        if self.heal_hp:
            lines.append(f"  Restores {self.heal_hp} HP")
        if self.heal_mp:
            lines.append(f"  Restores {self.heal_mp} MP")
        if self.element != ELEM_PHYSICAL:
            lines.append(f"  Element: {self.element}")
        lines.append(f"  Value: {self.value} gold")
        return lines

    def to_dict(self):
        return {
            "name": self.name, "description": self.description,
            "item_type": self.item_type, "slot": self.slot,
            "rarity": self.rarity, "stats": self.stats,
            "consumable": self.consumable, "heal_hp": self.heal_hp,
            "heal_mp": self.heal_mp, "value": self.value,
            "level_req": self.level_req, "element": self.element,
            "buff": self.buff,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


# ─── Consumables ─────────────────────────────────────────────────────

def create_health_potion():
    return Item("Health Potion", "Restores 50 HP", "consumable",
                consumable=True, heal_hp=50, value=25, rarity=RARITY_COMMON)


def create_greater_health_potion():
    return Item("Greater Health Potion", "Restores 150 HP", "consumable",
                consumable=True, heal_hp=150, value=80, rarity=RARITY_UNCOMMON)


def create_mana_potion():
    return Item("Mana Potion", "Restores 30 MP", "consumable",
                consumable=True, heal_mp=30, value=30, rarity=RARITY_COMMON)


def create_greater_mana_potion():
    return Item("Greater Mana Potion", "Restores 80 MP", "consumable",
                consumable=True, heal_mp=80, value=90, rarity=RARITY_UNCOMMON)


def create_elixir():
    return Item("Elixir", "Restores 100 HP and 50 MP", "consumable",
                consumable=True, heal_hp=100, heal_mp=50, value=120, rarity=RARITY_RARE)


def create_strength_potion():
    return Item("Strength Potion", "Boost ATK by 5 for 3 turns", "consumable",
                consumable=True, buff={"stat": "atk", "amount": 5, "duration": 3},
                value=60, rarity=RARITY_UNCOMMON)


def create_defense_potion():
    return Item("Iron Skin Potion", "Boost DEF by 5 for 3 turns", "consumable",
                consumable=True, buff={"stat": "def", "amount": 5, "duration": 3},
                value=60, rarity=RARITY_UNCOMMON)


def create_speed_potion():
    return Item("Haste Potion", "Boost SPD by 5 for 3 turns", "consumable",
                consumable=True, buff={"stat": "spd", "amount": 5, "duration": 3},
                value=60, rarity=RARITY_UNCOMMON)


def create_antidote():
    return Item("Antidote", "Cures poison effects", "consumable",
                consumable=True, value=15, rarity=RARITY_COMMON)


# ─── Weapons ─────────────────────────────────────────────────────────

def create_rusty_sword():
    return Item("Rusty Sword", "A worn but serviceable blade", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 3}, value=15, rarity=RARITY_COMMON)


def create_iron_sword():
    return Item("Iron Sword", "A sturdy iron blade", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 6}, value=50, rarity=RARITY_COMMON,
                level_req=3)


def create_steel_sword():
    return Item("Steel Sword", "A well-forged steel sword", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 10, "spd": 1}, value=120,
                rarity=RARITY_UNCOMMON, level_req=5)


def create_flame_blade():
    return Item("Flame Blade", "A sword wreathed in fire", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 14, "mag": 4}, value=300,
                rarity=RARITY_RARE, element=ELEM_FIRE, level_req=8)


def create_frost_edge():
    return Item("Frost Edge", "A blade of eternal ice", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 12, "mag": 6, "spd": 2}, value=320,
                rarity=RARITY_RARE, element=ELEM_ICE, level_req=8)


def create_shadow_dagger():
    return Item("Shadow Dagger", "A dagger that drinks in light", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 11, "spd": 5}, value=280,
                rarity=RARITY_RARE, element=ELEM_DARK, level_req=7)


def create_holy_avenger():
    return Item("Holy Avenger", "A legendary paladin's sword", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 20, "mag": 8, "defense": 3}, value=800,
                rarity=RARITY_EPIC, element=ELEM_HOLY, level_req=12)


def create_staff_of_storms():
    return Item("Staff of Storms", "Crackles with raw power", "weapon",
                slot=SLOT_WEAPON, stats={"mag": 18, "atk": 5, "spd": 2}, value=750,
                rarity=RARITY_EPIC, element=ELEM_LIGHTNING, level_req=11)


def create_excalibur():
    return Item("Excalibur", "The legendary sword of kings", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 30, "mag": 10, "defense": 5, "spd": 3},
                value=2000, rarity=RARITY_LEGENDARY, element=ELEM_HOLY, level_req=15)


def create_apprentice_staff():
    return Item("Apprentice Staff", "A basic magical staff", "weapon",
                slot=SLOT_WEAPON, stats={"mag": 5, "atk": 2}, value=40,
                rarity=RARITY_COMMON, level_req=2)


def create_hunting_bow():
    return Item("Hunting Bow", "A reliable bow", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 5, "spd": 2}, value=45,
                rarity=RARITY_COMMON, level_req=2)


def create_longbow():
    return Item("Longbow", "A powerful ranged weapon", "weapon",
                slot=SLOT_WEAPON, stats={"atk": 9, "spd": 3}, value=110,
                rarity=RARITY_UNCOMMON, level_req=5)


# ─── Armor ───────────────────────────────────────────────────────────

def create_leather_armor():
    return Item("Leather Armor", "Basic protective gear", "armor",
                slot=SLOT_ARMOR, stats={"defense": 3}, value=30, rarity=RARITY_COMMON)


def create_chain_mail():
    return Item("Chain Mail", "Interlocking metal rings", "armor",
                slot=SLOT_ARMOR, stats={"defense": 6, "spd": -1}, value=80,
                rarity=RARITY_COMMON, level_req=4)


def create_plate_armor():
    return Item("Plate Armor", "Heavy but very protective", "armor",
                slot=SLOT_ARMOR, stats={"defense": 12, "spd": -2}, value=250,
                rarity=RARITY_UNCOMMON, level_req=7)


def create_mage_robes():
    return Item("Mage Robes", "Enchanted robes of power", "armor",
                slot=SLOT_ARMOR, stats={"defense": 3, "mag": 6, "spd": 1}, value=200,
                rarity=RARITY_UNCOMMON, level_req=5)


def create_dragon_scale():
    return Item("Dragon Scale Armor", "Forged from dragon scales", "armor",
                slot=SLOT_ARMOR, stats={"defense": 18, "atk": 3}, value=600,
                rarity=RARITY_EPIC, level_req=12)


def create_shadow_cloak():
    return Item("Shadow Cloak", "Woven from living shadows", "armor",
                slot=SLOT_ARMOR, stats={"defense": 8, "spd": 6}, value=400,
                rarity=RARITY_RARE, element=ELEM_DARK, level_req=9)


# ─── Helmets ─────────────────────────────────────────────────────────

def create_leather_cap():
    return Item("Leather Cap", "Simple head protection", "armor",
                slot=SLOT_HELMET, stats={"defense": 1}, value=15, rarity=RARITY_COMMON)


def create_iron_helm():
    return Item("Iron Helm", "Sturdy metal helmet", "armor",
                slot=SLOT_HELMET, stats={"defense": 3}, value=60,
                rarity=RARITY_COMMON, level_req=4)


def create_crown_of_wisdom():
    return Item("Crown of Wisdom", "Enhances magical ability", "armor",
                slot=SLOT_HELMET, stats={"defense": 2, "mag": 5}, value=350,
                rarity=RARITY_RARE, level_req=8)


# ─── Boots ───────────────────────────────────────────────────────────

def create_leather_boots():
    return Item("Leather Boots", "Basic footwear", "armor",
                slot=SLOT_BOOTS, stats={"spd": 1}, value=20, rarity=RARITY_COMMON)


def create_iron_boots():
    return Item("Iron Boots", "Heavy but protective", "armor",
                slot=SLOT_BOOTS, stats={"defense": 2, "spd": -1}, value=50,
                rarity=RARITY_COMMON, level_req=3)


def create_winged_boots():
    return Item("Winged Boots", "Incredibly light footwear", "armor",
                slot=SLOT_BOOTS, stats={"spd": 5}, value=300,
                rarity=RARITY_RARE, level_req=7)


# ─── Accessories ─────────────────────────────────────────────────────

def create_ring_of_strength():
    return Item("Ring of Strength", "Enhances physical power", "accessory",
                slot=SLOT_ACCESSORY, stats={"atk": 3}, value=100,
                rarity=RARITY_UNCOMMON, level_req=3)


def create_ring_of_protection():
    return Item("Ring of Protection", "A magical ward", "accessory",
                slot=SLOT_ACCESSORY, stats={"defense": 3}, value=100,
                rarity=RARITY_UNCOMMON, level_req=3)


def create_amulet_of_vitality():
    return Item("Amulet of Vitality", "Increases life force", "accessory",
                slot=SLOT_ACCESSORY, stats={"defense": 2, "spd": 2}, value=180,
                rarity=RARITY_RARE, level_req=5)


def create_pendant_of_arcana():
    return Item("Pendant of Arcana", "Channel raw magic", "accessory",
                slot=SLOT_ACCESSORY, stats={"mag": 6}, value=250,
                rarity=RARITY_RARE, level_req=6)


def create_legendary_ring():
    return Item("Ring of the Ancients", "Power of forgotten gods", "accessory",
                slot=SLOT_ACCESSORY, stats={"atk": 5, "mag": 5, "defense": 5, "spd": 3},
                value=1500, rarity=RARITY_LEGENDARY, level_req=14)


# ─── Loot Tables ─────────────────────────────────────────────────────

COMMON_LOOT = [
    (create_health_potion, 0.4),
    (create_mana_potion, 0.3),
    (create_antidote, 0.2),
]

UNCOMMON_LOOT = [
    (create_health_potion, 0.3),
    (create_greater_health_potion, 0.15),
    (create_mana_potion, 0.2),
    (create_strength_potion, 0.1),
    (create_defense_potion, 0.1),
    (create_iron_sword, 0.05),
    (create_chain_mail, 0.05),
]

RARE_LOOT = [
    (create_greater_health_potion, 0.25),
    (create_greater_mana_potion, 0.2),
    (create_elixir, 0.1),
    (create_steel_sword, 0.08),
    (create_flame_blade, 0.05),
    (create_frost_edge, 0.05),
    (create_shadow_dagger, 0.05),
    (create_plate_armor, 0.05),
    (create_mage_robes, 0.05),
    (create_crown_of_wisdom, 0.03),
    (create_winged_boots, 0.03),
    (create_amulet_of_vitality, 0.03),
]

BOSS_LOOT = [
    (create_elixir, 0.5),
    (create_holy_avenger, 0.1),
    (create_staff_of_storms, 0.1),
    (create_dragon_scale, 0.1),
    (create_shadow_cloak, 0.1),
    (create_pendant_of_arcana, 0.1),
    (create_legendary_ring, 0.05),
    (create_excalibur, 0.03),
]


def get_loot_table(enemy_type, level):
    """Get appropriate loot table for an enemy."""
    if enemy_type == "boss":
        return BOSS_LOOT
    if level >= 8:
        return RARE_LOOT
    if level >= 4:
        return UNCOMMON_LOOT
    return COMMON_LOOT


# ─── Shop Inventories ────────────────────────────────────────────────

VILLAGE_SHOP = [
    create_health_potion, create_mana_potion, create_antidote,
    create_rusty_sword, create_leather_armor, create_leather_cap,
    create_leather_boots, create_apprentice_staff, create_hunting_bow,
]

FOREST_SHOP = [
    create_health_potion, create_greater_health_potion,
    create_mana_potion, create_greater_mana_potion,
    create_strength_potion, create_defense_potion, create_speed_potion,
    create_iron_sword, create_chain_mail, create_iron_helm, create_iron_boots,
    create_longbow, create_ring_of_strength, create_ring_of_protection,
]

MOUNTAIN_SHOP = [
    create_greater_health_potion, create_greater_mana_potion, create_elixir,
    create_steel_sword, create_plate_armor, create_mage_robes,
    create_crown_of_wisdom, create_winged_boots,
    create_amulet_of_vitality, create_pendant_of_arcana,
]
