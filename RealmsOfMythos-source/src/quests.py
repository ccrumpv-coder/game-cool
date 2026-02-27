"""Quest system."""

from src.constants import GOLD


class QuestObjective:
    """A single objective within a quest."""

    def __init__(self, obj_type, target, required_count=1, description=""):
        self.obj_type = obj_type  # "kill", "collect", "talk", "explore", "boss"
        self.target = target  # enemy name, item name, NPC name, or map name
        self.required_count = required_count
        self.current_count = 0
        self.description = description or f"{obj_type.title()} {target}"
        self.completed = False

    def update(self, event_type, event_target):
        """Update objective progress."""
        if self.completed:
            return False
        if event_type == self.obj_type and event_target == self.target:
            self.current_count += 1
            if self.current_count >= self.required_count:
                self.completed = True
                return True
        return False

    @property
    def progress_text(self):
        return f"{self.description} ({self.current_count}/{self.required_count})"

    def to_dict(self):
        return {
            "obj_type": self.obj_type, "target": self.target,
            "required_count": self.required_count,
            "current_count": self.current_count,
            "description": self.description,
            "completed": self.completed,
        }


class Quest:
    """A quest with objectives and rewards."""

    def __init__(self, quest_id, name, description, objectives,
                 xp_reward=0, gold_reward=0, item_rewards=None,
                 prerequisite=None, level_req=1):
        self.quest_id = quest_id
        self.name = name
        self.description = description
        self.objectives = objectives
        self.xp_reward = xp_reward
        self.gold_reward = gold_reward
        self.item_rewards = item_rewards or []
        self.prerequisite = prerequisite  # quest_id or None
        self.level_req = level_req
        self.accepted = False
        self.completed = False
        self.turned_in = False

    @property
    def is_complete(self):
        return all(obj.completed for obj in self.objectives)

    def update(self, event_type, event_target):
        """Update quest objectives."""
        if not self.accepted or self.completed:
            return False
        any_update = False
        for obj in self.objectives:
            if obj.update(event_type, event_target):
                any_update = True
        if self.is_complete:
            self.completed = True
        return any_update

    def get_description_lines(self):
        """Get full quest description for UI."""
        lines = [self.name, ""]
        lines.append(self.description)
        lines.append("")
        lines.append("Objectives:")
        for obj in self.objectives:
            status = "[X]" if obj.completed else "[ ]"
            lines.append(f"  {status} {obj.progress_text}")
        lines.append("")
        lines.append("Rewards:")
        if self.xp_reward:
            lines.append(f"  {self.xp_reward} XP")
        if self.gold_reward:
            lines.append(f"  {self.gold_reward} Gold")
        for item_func in self.item_rewards:
            item = item_func()
            lines.append(f"  {item.name}")
        return lines

    def to_dict(self):
        return {
            "quest_id": self.quest_id, "name": self.name,
            "objectives": [o.to_dict() for o in self.objectives],
            "accepted": self.accepted, "completed": self.completed,
            "turned_in": self.turned_in,
        }


# ─── Quest Definitions ───────────────────────────────────────────────

def create_quest_slime_trouble():
    return Quest(
        "slime_trouble", "Slime Trouble",
        "The village elder is worried about slimes near the village. "
        "Clear them out to prove your worth!",
        objectives=[
            QuestObjective("kill", "Green Slime", 5, "Slay Green Slimes"),
        ],
        xp_reward=100, gold_reward=50, level_req=1,
    )


def create_quest_wolf_pelts():
    return Quest(
        "wolf_pelts", "Wolf Pack",
        "Dire wolves have been terrorizing travelers on the road. "
        "Thin their numbers for the safety of all.",
        objectives=[
            QuestObjective("kill", "Dire Wolf", 3, "Slay Dire Wolves"),
        ],
        xp_reward=150, gold_reward=80, level_req=2,
    )


def create_quest_goblin_camp():
    return Quest(
        "goblin_camp", "Goblin Menace",
        "A goblin camp has been established in the dark forest. "
        "Defeat the goblins and their king!",
        objectives=[
            QuestObjective("kill", "Goblin", 5, "Slay Goblins"),
            QuestObjective("boss", "Goblin King", 1, "Defeat the Goblin King"),
        ],
        xp_reward=400, gold_reward=200, level_req=4,
        prerequisite="slime_trouble",
    )


def create_quest_dark_forest():
    return Quest(
        "dark_forest_explore", "Into the Darkness",
        "The Dark Forest holds many secrets. Explore its depths "
        "and defeat the undead that lurk within.",
        objectives=[
            QuestObjective("kill", "Skeleton", 5, "Slay Skeletons"),
            QuestObjective("kill", "Dark Mage", 2, "Defeat Dark Mages"),
        ],
        xp_reward=350, gold_reward=150, level_req=4,
    )


def create_quest_mountain_pass():
    return Quest(
        "mountain_climb", "The Mountain Pass",
        "The mountain pass is blocked by dangerous creatures. "
        "Clear a path to the Shadow Citadel beyond.",
        objectives=[
            QuestObjective("kill", "Ice Golem", 3, "Destroy Ice Golems"),
            QuestObjective("kill", "Fire Elemental", 3, "Extinguish Fire Elementals"),
        ],
        xp_reward=500, gold_reward=250, level_req=7,
        prerequisite="goblin_camp",
    )


def create_quest_dragon_threat():
    return Quest(
        "dragon_threat", "Dragon Threat",
        "Dragon whelps have been spotted near the mountain. "
        "They must be stopped before they grow larger.",
        objectives=[
            QuestObjective("kill", "Dragon Whelp", 4, "Slay Dragon Whelps"),
        ],
        xp_reward=600, gold_reward=300, level_req=8,
    )


def create_quest_lich_lord():
    return Quest(
        "lich_lord", "The Ancient Lich",
        "An Ancient Lich has risen in the Shadow Citadel. "
        "This undead horror must be destroyed before it amasses an army.",
        objectives=[
            QuestObjective("boss", "Ancient Lich", 1, "Defeat the Ancient Lich"),
        ],
        xp_reward=1000, gold_reward=500, level_req=10,
        prerequisite="mountain_climb",
    )


def create_quest_elder_dragon():
    return Quest(
        "elder_dragon", "The Elder Dragon",
        "The Elder Dragon, ancient terror of the realm, has awakened. "
        "Only a true hero can face this legendary beast.",
        objectives=[
            QuestObjective("boss", "Elder Dragon", 1, "Defeat the Elder Dragon"),
        ],
        xp_reward=2000, gold_reward=1000, level_req=14,
        prerequisite="lich_lord",
    )


# All quests
ALL_QUESTS = [
    create_quest_slime_trouble,
    create_quest_wolf_pelts,
    create_quest_goblin_camp,
    create_quest_dark_forest,
    create_quest_mountain_pass,
    create_quest_dragon_threat,
    create_quest_lich_lord,
    create_quest_elder_dragon,
]
