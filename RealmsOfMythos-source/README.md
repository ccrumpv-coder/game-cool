# Realms of Mythos

A complex, feature-rich RPG game built with Python and Pygame.

## Features

- **5 Unique Character Classes**: Warrior, Mage, Rogue, Ranger, Paladin — each with distinct stats, abilities, and playstyles
- **Turn-Based Combat**: Strategic battles with spells, abilities, elemental weaknesses, buffs/debuffs, and critical hits
- **5 Explorable Maps**: Village, Outskirts, Dark Forest, Mountain Pass, and Shadow Citadel
- **Quest System**: 8 interconnected quests with objectives, rewards, and prerequisites
- **Inventory & Equipment**: Weapons, armor, helmets, boots, accessories with rarity tiers (Common to Legendary)
- **NPC Interactions**: Merchants, healers, quest givers, and villagers
- **Boss Battles**: Goblin King, Ancient Lich, and Elder Dragon
- **Leveling System**: Level up to 50 with stat gains and new abilities
- **Save/Load System**: Save your progress and continue later
- **Particle Effects**: Visual feedback for combat actions and spells
- **Minimap**: Always know where you are
- **Procedural Sprites**: All graphics generated procedurally — no external assets needed

## Option 1: Run the Standalone Executable (No Python needed)

Download the pre-built executable from the `dist/` folder and double-click to play:

- **Linux**: `./dist/RealmsOfMythos`
- **Windows**: Build with `python build_executable.py` then run `dist\RealmsOfMythos.exe`
- **macOS**: Build with `python build_executable.py` then run `dist/RealmsOfMythos`

## Option 2: Run from Source

```bash
pip install -r requirements.txt
python main.py
```

## Build Your Own Executable

```bash
pip install -r requirements.txt
pip install pyinstaller
python build_executable.py
```

## Controls

### Menu / General
- **Arrow Keys**: Navigate menus
- **Enter / Space**: Select / Confirm
- **Escape**: Back / Pause

### Exploration
- **WASD / Arrow Keys**: Move
- **E**: Interact with NPCs, chests, doors
- **I**: Open Inventory
- **Q**: Open Quest Log
- **Escape**: Pause Menu

### Combat
- **Up/Down**: Select ability or target
- **Left/Right**: Switch between action menu and ability list
- **Enter/Space**: Confirm selection
- **Escape**: Cancel target selection

### Inventory
- **Tab**: Switch between Items and Equipment tabs
- **Enter/Space**: Use item or equip/unequip
- **X**: Discard item
- **I / Escape**: Close inventory

### Shop
- **Tab**: Switch between Buy and Sell
- **Enter/Space**: Purchase or sell item
- **Escape**: Leave shop

## Game Tips

1. Start by talking to the Village Elder and Hunter Kael for your first quests
2. Heal at Sister Maria (the healer) for free before venturing out
3. Buy equipment from the General Store before leaving the village
4. Explore the Village Outskirts first — enemies are easier there
5. Look for treasure chests in each area
6. Map transitions are shown with arrows at the map edges
7. Save often using the Pause menu (Escape → Save Game)
8. Boss enemies are marked on the map — prepare before engaging!
