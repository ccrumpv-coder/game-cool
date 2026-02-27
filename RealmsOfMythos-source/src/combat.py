"""Turn-based combat system."""

import random
import math
import pygame
from src.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, FPS,
    BLACK, WHITE, RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, CYAN, GOLD,
    UI_BG, UI_BORDER, UI_TEXT, UI_ACCENT, UI_HIGHLIGHT,
    HP_BAR_COLOR, MP_BAR_COLOR,
    ELEM_PHYSICAL, ELEM_FIRE, ELEM_ICE, ELEM_LIGHTNING, ELEM_HOLY, ELEM_DARK, ELEM_POISON,
    COMBAT_TURN_DELAY, DAMAGE_FLASH_DURATION, SHAKE_DURATION, SHAKE_INTENSITY
)
from src.utils import (
    draw_text, draw_panel, draw_bar, draw_tooltip, clamp, shake_offset
)
from src.particles import ParticleSystem, Particle
from src.entities import Ability


ELEMENT_COLORS = {
    ELEM_PHYSICAL: WHITE,
    ELEM_FIRE: ORANGE,
    ELEM_ICE: CYAN,
    ELEM_LIGHTNING: YELLOW,
    ELEM_HOLY: GOLD,
    ELEM_DARK: PURPLE,
    ELEM_POISON: GREEN,
}

ELEMENT_WEAKNESSES = {
    ELEM_FIRE: ELEM_ICE,
    ELEM_ICE: ELEM_FIRE,
    ELEM_LIGHTNING: ELEM_PHYSICAL,
    ELEM_HOLY: ELEM_DARK,
    ELEM_DARK: ELEM_HOLY,
    ELEM_POISON: ELEM_HOLY,
}


class CombatAction:
    """A queued combat action."""

    def __init__(self, actor, ability, target=None):
        self.actor = actor
        self.ability = ability
        self.target = target


class DamageNumber:
    """Floating damage number."""

    def __init__(self, x, y, text, color=WHITE):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.timer = 1.5
        self.vel_y = -40

    def update(self, dt):
        self.y += self.vel_y * dt
        self.vel_y += 50 * dt  # gravity
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface, font):
        alpha = int(255 * min(1.0, self.timer / 0.5))
        color = (*self.color[:3],)
        draw_text(surface, self.text, int(self.x), int(self.y), font, color)


class CombatSystem:
    """Manages turn-based combat."""

    def __init__(self, player, enemies, fonts):
        self.player = player
        self.enemies = enemies
        self.fonts = fonts
        self.particles = ParticleSystem()
        self.damage_numbers = []

        # Turn order
        self.turn_order = []
        self.current_turn = 0
        self.turn_count = 0

        # State
        self.phase = "player_choose"  # player_choose, player_target, animating, enemy_turn, victory, defeat
        self.selected_ability_index = 0
        self.selected_target_index = 0
        self.selected_menu = "abilities"  # abilities, items, defend

        # Animation
        self.anim_timer = 0
        self.shake_timer = 0
        self.flash_timer = 0
        self.flash_target = None
        self.combat_log = []
        self.max_log = 6

        # Menu
        self.menu_options = ["Abilities", "Items", "Defend", "Flee"]
        self.menu_index = 0

        # Rewards
        self.total_xp = 0
        self.total_gold = 0
        self.loot_drops = []

        # Victory/defeat state
        self.result = None  # "victory", "defeat", "fled"
        self.result_timer = 0

        self._calculate_turn_order()

    def _calculate_turn_order(self):
        """Calculate turn order based on speed."""
        entities = [("player", self.player.stats.spd)]
        for i, e in enumerate(self.enemies):
            if e.stats.is_alive:
                entities.append((f"enemy_{i}", e.stats.spd))
        entities.sort(key=lambda x: x[1], reverse=True)
        self.turn_order = [e[0] for e in entities]
        self.current_turn = 0

    def _get_current_actor(self):
        """Get who acts next."""
        if not self.turn_order:
            return None
        return self.turn_order[self.current_turn % len(self.turn_order)]

    def _add_log(self, text):
        """Add to combat log."""
        self.combat_log.append(text)
        if len(self.combat_log) > self.max_log:
            self.combat_log.pop(0)

    def _calculate_damage(self, attacker_atk, attacker_mag, defender_def,
                          ability, is_player_attacking):
        """Calculate damage for an attack."""
        if ability.heals and not ability.damage_mult:
            return 0

        # Base damage from ATK or MAG depending on element
        if ability.element in (ELEM_FIRE, ELEM_ICE, ELEM_LIGHTNING, ELEM_HOLY, ELEM_DARK):
            base = attacker_mag * ability.damage_mult
        else:
            base = attacker_atk * ability.damage_mult

        # Defense reduction
        reduction = defender_def * 0.5
        damage = max(1, base - reduction)

        # Random variance
        damage *= random.uniform(0.85, 1.15)

        # Critical hit (10% chance, 1.5x damage)
        crit = False
        if random.random() < 0.10:
            damage *= 1.5
            crit = True

        # Elemental weakness
        weakness_bonus = False
        if ability.element in ELEMENT_WEAKNESSES:
            # Check if defender is weak (simplified)
            if random.random() < 0.3:
                damage *= 1.3
                weakness_bonus = True

        return int(damage), crit, weakness_bonus

    def _apply_ability(self, attacker, target, ability, is_player):
        """Apply an ability's effects."""
        results = []

        # Healing
        if ability.heals:
            if is_player:
                heal_amount = int(self.player.stats.max_hp * ability.heal_amount)
                self.player.stats.heal(heal_amount)
                self._add_log(f"{self.player.name} heals for {heal_amount} HP!")
                self.damage_numbers.append(
                    DamageNumber(SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2,
                                 f"+{heal_amount}", GREEN))
                self.particles.emit_float_text(SCREEN_WIDTH // 4,
                                                SCREEN_HEIGHT // 2, GREEN)
            else:
                heal_amount = int(attacker.stats.max_hp * ability.heal_amount)
                attacker.stats.heal(heal_amount)
                self._add_log(f"{attacker.name} heals for {heal_amount} HP!")

        # Damage
        if ability.damage_mult > 0:
            if is_player:
                atk = self.player.get_total_atk()
                mag = self.player.get_total_mag()
            else:
                atk = attacker.stats.atk
                mag = attacker.stats.mag

            if ability.targets_all:
                if is_player:
                    targets = [e for e in self.enemies if e.stats.is_alive]
                else:
                    targets = [self.player]
            else:
                targets = [target] if target else []

            for t in targets:
                t_def = t.stats.defense if not is_player else self.player.get_total_def()
                if is_player:
                    t_def = t.stats.defense
                damage, crit, weak = self._calculate_damage(
                    atk, mag, t_def, ability, is_player)

                t.stats.hp -= damage
                t.stats.hp = max(0, t.stats.hp)

                # Visual feedback
                color = ELEMENT_COLORS.get(ability.element, WHITE)
                crit_text = " CRITICAL!" if crit else ""
                weak_text = " EFFECTIVE!" if weak else ""

                if is_player:
                    idx = self.enemies.index(t) if t in self.enemies else 0
                    dx = SCREEN_WIDTH * 3 // 4
                    dy = 120 + idx * 100
                    self.flash_target = ("enemy", idx)
                else:
                    dx = SCREEN_WIDTH // 4
                    dy = SCREEN_HEIGHT // 2
                    self.flash_target = ("player", 0)

                self.damage_numbers.append(
                    DamageNumber(dx, dy, f"-{damage}{crit_text}{weak_text}",
                                 RED if not crit else YELLOW))
                self.particles.emit_burst(dx, dy, color, count=15)
                self.shake_timer = SHAKE_DURATION / 1000.0
                self.flash_timer = DAMAGE_FLASH_DURATION / 1000.0

                name = t.name if hasattr(t, 'name') else self.player.name
                self._add_log(
                    f"{ability.name} deals {damage} to {name}!{crit_text}{weak_text}")

                # Apply debuff
                if ability.debuff and t.stats.is_alive:
                    t.stats.apply_buff(ability.debuff)
                    self._add_log(f"{name} is affected by {ability.name}!")

        # Buff (self)
        if ability.buff:
            if is_player:
                self.player.stats.apply_buff(ability.buff)
                self._add_log(f"{self.player.name} gains a buff!")
                self.particles.emit_float_text(SCREEN_WIDTH // 4,
                                                SCREEN_HEIGHT // 2, GOLD)
            else:
                attacker.stats.apply_buff(ability.buff)
                self._add_log(f"{attacker.name} powers up!")

        # Use ability
        ability.use()
        if is_player:
            self.player.stats.mp -= ability.mp_cost
            self.player.stats.mp = max(0, self.player.stats.mp)

    def handle_input(self, event):
        """Handle combat input."""
        if self.phase == "player_choose":
            return self._handle_menu_input(event)
        elif self.phase == "player_target":
            return self._handle_target_input(event)
        elif self.phase in ("victory", "defeat"):
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.result
        return None

    def _handle_menu_input(self, event):
        """Handle main combat menu."""
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_UP:
            if self.selected_menu == "abilities":
                self.selected_ability_index = max(0, self.selected_ability_index - 1)
            else:
                self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        elif event.key == pygame.K_DOWN:
            if self.selected_menu == "abilities":
                abilities = self.player.get_available_abilities()
                self.selected_ability_index = min(len(abilities) - 1,
                                                   self.selected_ability_index + 1)
            else:
                self.menu_index = (self.menu_index + 1) % len(self.menu_options)
        elif event.key == pygame.K_LEFT:
            self.selected_menu = "menu"
            self.selected_ability_index = 0
        elif event.key == pygame.K_RIGHT:
            self.selected_menu = "abilities"
            self.selected_ability_index = 0
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.selected_menu == "menu":
                return self._select_menu_option()
            elif self.selected_menu == "abilities":
                return self._select_ability()
        elif event.key == pygame.K_ESCAPE:
            self.selected_menu = "menu"

        return None

    def _select_menu_option(self):
        """Process menu selection."""
        option = self.menu_options[self.menu_index]
        if option == "Abilities":
            self.selected_menu = "abilities"
            self.selected_ability_index = 0
        elif option == "Items":
            # Use first health potion if available
            for item in self.player.inventory:
                if item.consumable and item.heal_hp > 0:
                    self.player.use_item(item)
                    self._add_log(f"Used {item.name}! Restored {item.heal_hp} HP.")
                    self.particles.emit_float_text(SCREEN_WIDTH // 4,
                                                    SCREEN_HEIGHT // 2, GREEN)
                    self._advance_turn()
                    return None
            self._add_log("No usable items!")
        elif option == "Defend":
            self.player.stats.apply_buff(
                {"stat": "def", "amount": 5, "duration": 1})
            self._add_log(f"{self.player.name} takes a defensive stance!")
            self._advance_turn()
        elif option == "Flee":
            if random.random() < 0.5:
                self._add_log("Fled successfully!")
                self.result = "fled"
                self.phase = "defeat"
                return "fled"
            else:
                self._add_log("Couldn't escape!")
                self._advance_turn()
        return None

    def _select_ability(self):
        """Select and use an ability."""
        abilities = self.player.get_available_abilities()
        if not abilities:
            self._add_log("No abilities available!")
            return None

        idx = min(self.selected_ability_index, len(abilities) - 1)
        ability = abilities[idx]

        if ability.targets_all or ability.heals or ability.buff:
            # Apply immediately (no targeting needed)
            alive_enemies = [e for e in self.enemies if e.stats.is_alive]
            target = alive_enemies[0] if alive_enemies else None
            self._apply_ability(self.player, target, ability, True)
            self._advance_turn()
        else:
            # Need to select target
            self.phase = "player_target"
            self.selected_target_index = 0
        return None

    def _handle_target_input(self, event):
        """Handle target selection."""
        if event.type != pygame.KEYDOWN:
            return None

        alive_enemies = [e for e in self.enemies if e.stats.is_alive]
        if not alive_enemies:
            self.phase = "player_choose"
            return None

        if event.key == pygame.K_UP:
            self.selected_target_index = max(0, self.selected_target_index - 1)
        elif event.key == pygame.K_DOWN:
            self.selected_target_index = min(len(alive_enemies) - 1,
                                              self.selected_target_index + 1)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            target = alive_enemies[self.selected_target_index]
            abilities = self.player.get_available_abilities()
            idx = min(self.selected_ability_index, len(abilities) - 1)
            ability = abilities[idx]
            self._apply_ability(self.player, target, ability, True)
            self.phase = "player_choose"
            self._advance_turn()
        elif event.key == pygame.K_ESCAPE:
            self.phase = "player_choose"

        return None

    def _advance_turn(self):
        """Move to next turn."""
        # Check for victory
        if all(not e.stats.is_alive for e in self.enemies):
            self._handle_victory()
            return

        # Check for defeat
        if not self.player.stats.is_alive:
            self._handle_defeat()
            return

        # Enemy turns
        self.anim_timer = COMBAT_TURN_DELAY / 1000.0
        self.phase = "animating"

    def _do_enemy_turns(self):
        """Execute all enemy turns."""
        for enemy in self.enemies:
            if not enemy.stats.is_alive:
                continue
            if not self.player.stats.is_alive:
                break

            # Tick buffs
            enemy.stats.tick_buffs()
            for ability in enemy.abilities:
                ability.tick_cooldown()

            # Choose and execute action
            action = enemy.choose_action()
            self._add_log(f"{enemy.name} uses {action.name}!")
            self._apply_ability(enemy, self.player, action, False)

        # Tick player buffs
        self.player.stats.tick_buffs()
        for ability in self.player.abilities:
            ability.tick_cooldown()

        # Check conditions
        if not self.player.stats.is_alive:
            self._handle_defeat()
        elif all(not e.stats.is_alive for e in self.enemies):
            self._handle_victory()
        else:
            self.phase = "player_choose"
            self.turn_count += 1

    def _handle_victory(self):
        """Handle combat victory."""
        self.phase = "victory"
        self.result = "victory"

        for enemy in self.enemies:
            self.total_xp += enemy.xp_reward
            self.total_gold += enemy.gold_reward
            self.loot_drops.extend(enemy.get_loot())

        self.player.gold += self.total_gold
        level_ups = self.player.gain_xp(self.total_xp)

        self._add_log("--- VICTORY! ---")
        self._add_log(f"Gained {self.total_xp} XP and {self.total_gold} gold!")
        for gains in level_ups:
            self._add_log(f"LEVEL UP! Now level {self.player.level}!")

        for item in self.loot_drops:
            if self.player.add_item(item):
                self._add_log(f"Obtained: {item.name}")

    def _handle_defeat(self):
        """Handle combat defeat."""
        self.phase = "defeat"
        self.result = "defeat"
        self._add_log("--- DEFEATED ---")
        self._add_log("You have fallen in battle...")

    def update(self, dt):
        """Update combat state."""
        self.particles.update(dt)

        # Update damage numbers
        self.damage_numbers = [d for d in self.damage_numbers if d.update(dt)]

        # Shake
        if self.shake_timer > 0:
            self.shake_timer -= dt

        # Flash
        if self.flash_timer > 0:
            self.flash_timer -= dt

        # Animation delay
        if self.phase == "animating":
            self.anim_timer -= dt
            if self.anim_timer <= 0:
                self._do_enemy_turns()

    def draw(self, surface):
        """Draw the combat scene."""
        # Background
        surface.fill((15, 10, 25))

        # Shake offset
        sx, sy = shake_offset(self.shake_timer, SHAKE_INTENSITY) if self.shake_timer > 0 else (0, 0)

        # Draw combat arena background
        arena_rect = pygame.Rect(50 + sx, 50 + sy, SCREEN_WIDTH - 100, SCREEN_HEIGHT // 2 - 30)
        draw_panel(surface, arena_rect.x, arena_rect.y, arena_rect.width, arena_rect.height,
                   bg=(25, 20, 35))

        # Draw player
        player_x = SCREEN_WIDTH // 4 + sx
        player_y = SCREEN_HEIGHT // 3 + sy
        self._draw_combatant_player(surface, player_x, player_y)

        # Draw enemies
        alive_enemies = [e for e in self.enemies if e.stats.is_alive]
        for i, enemy in enumerate(alive_enemies):
            ex = SCREEN_WIDTH * 3 // 4 + sx
            ey = 100 + i * 100 + sy
            self._draw_combatant_enemy(surface, ex, ey, enemy, i)

        # Draw particles
        self.particles.draw(surface)

        # Draw damage numbers
        for dmg in self.damage_numbers:
            dmg.draw(surface, self.fonts["small"])

        # Draw UI
        self._draw_combat_ui(surface)

        # Draw combat log
        self._draw_combat_log(surface)

        # Target selection indicator
        if self.phase == "player_target":
            self._draw_target_cursor(surface, alive_enemies)

        # Victory/Defeat overlay
        if self.phase in ("victory", "defeat"):
            self._draw_result_overlay(surface)

    def _draw_combatant_player(self, surface, x, y):
        """Draw player in combat."""
        from src.utils import SpriteSheet
        sprite = SpriteSheet.create_character_sprite(
            (100, 150, 255), 64, self.player.char_class.lower())
        surface.blit(sprite, (x - 32, y - 32))

        # HP/MP bars
        draw_bar(surface, x - 40, y + 40, 80, 8,
                 self.player.stats.hp, self.player.stats.max_hp, HP_BAR_COLOR)
        draw_bar(surface, x - 40, y + 52, 80, 6,
                 self.player.stats.mp, self.player.stats.max_mp, MP_BAR_COLOR)
        draw_text(surface, self.player.name, x, y + 65,
                  self.fonts["small"], WHITE, center=True)
        draw_text(surface, f"HP: {self.player.stats.hp}/{self.player.stats.max_hp}",
                  x, y + 78, self.fonts["tiny"], WHITE, center=True)

        # Flash effect
        if self.flash_timer > 0 and self.flash_target == ("player", 0):
            flash_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            alpha = int(180 * (self.flash_timer / (DAMAGE_FLASH_DURATION / 1000.0)))
            flash_surf.fill((255, 50, 50, alpha))
            surface.blit(flash_surf, (x - 40, y - 40))

    def _draw_combatant_enemy(self, surface, x, y, enemy, index):
        """Draw an enemy in combat."""
        from src.utils import SpriteSheet
        sprite = SpriteSheet.create_enemy_sprite(enemy.color, 56, enemy.enemy_type)
        surface.blit(sprite, (x - 28, y - 28))

        # HP bar
        draw_bar(surface, x - 35, y + 35, 70, 8,
                 enemy.stats.hp, enemy.stats.max_hp, HP_BAR_COLOR)
        draw_text(surface, f"{enemy.name} Lv.{enemy.level}",
                  x, y + 48, self.fonts["tiny"], WHITE, center=True)
        draw_text(surface, f"HP: {enemy.stats.hp}/{enemy.stats.max_hp}",
                  x, y + 60, self.fonts["tiny"], YELLOW, center=True)

        # Flash effect
        if self.flash_timer > 0 and self.flash_target == ("enemy", index):
            flash_surf = pygame.Surface((70, 70), pygame.SRCALPHA)
            alpha = int(180 * (self.flash_timer / (DAMAGE_FLASH_DURATION / 1000.0)))
            flash_surf.fill((255, 255, 255, alpha))
            surface.blit(flash_surf, (x - 35, y - 35))

    def _draw_combat_ui(self, surface):
        """Draw combat action menu."""
        panel_y = SCREEN_HEIGHT // 2 + 40
        panel_h = SCREEN_HEIGHT // 2 - 60

        # Menu panel
        draw_panel(surface, 20, panel_y, 180, panel_h)
        draw_text(surface, "Actions", 30, panel_y + 5, self.fonts["small"], UI_ACCENT)

        for i, option in enumerate(self.menu_options):
            color = GOLD if (self.selected_menu == "menu" and i == self.menu_index) else UI_TEXT
            prefix = "> " if (self.selected_menu == "menu" and i == self.menu_index) else "  "
            draw_text(surface, f"{prefix}{option}", 30, panel_y + 30 + i * 25,
                      self.fonts["small"], color)

        # Abilities panel
        draw_panel(surface, 210, panel_y, 400, panel_h)
        draw_text(surface, "Abilities", 220, panel_y + 5, self.fonts["small"], UI_ACCENT)

        abilities = self.player.get_available_abilities()
        all_abilities = [a for a in self.player.abilities if a.level_req <= self.player.level]

        for i, ability in enumerate(all_abilities):
            available = ability in abilities
            if self.selected_menu == "abilities" and i == self.selected_ability_index:
                color = GOLD if available else (120, 80, 80)
                prefix = "> "
            else:
                color = UI_TEXT if available else GRAY
                prefix = "  "

            text = f"{prefix}{ability.name}"
            if ability.mp_cost > 0:
                text += f" ({ability.mp_cost} MP)"
            draw_text(surface, text, 220, panel_y + 30 + i * 22,
                      self.fonts["small"], color)

        # Ability description
        if self.selected_menu == "abilities" and all_abilities:
            idx = min(self.selected_ability_index, len(all_abilities) - 1)
            ab = all_abilities[idx]
            desc_y = panel_y + panel_h - 40
            draw_text(surface, ab.description, 220, desc_y,
                      self.fonts["tiny"], LIGHT_GRAY)
            elem_color = ELEMENT_COLORS.get(ab.element, WHITE)
            draw_text(surface, f"[{ab.element}]", 220, desc_y + 15,
                      self.fonts["tiny"], elem_color)

        # Player stats panel
        draw_panel(surface, 620, panel_y, 180, panel_h)
        draw_text(surface, f"{self.player.name}", 630, panel_y + 5,
                  self.fonts["small"], UI_ACCENT)
        draw_text(surface, f"Lv. {self.player.level} {self.player.char_class}",
                  630, panel_y + 25, self.fonts["tiny"], LIGHT_GRAY)

        stats_y = panel_y + 50
        draw_text(surface, f"HP: {self.player.stats.hp}/{self.player.stats.max_hp}",
                  630, stats_y, self.fonts["small"], HP_BAR_COLOR)
        draw_text(surface, f"MP: {self.player.stats.mp}/{self.player.stats.max_mp}",
                  630, stats_y + 20, self.fonts["small"], MP_BAR_COLOR)
        draw_text(surface, f"ATK: {self.player.get_total_atk()}",
                  630, stats_y + 45, self.fonts["tiny"], UI_TEXT)
        draw_text(surface, f"DEF: {self.player.get_total_def()}",
                  630, stats_y + 60, self.fonts["tiny"], UI_TEXT)
        draw_text(surface, f"MAG: {self.player.get_total_mag()}",
                  630, stats_y + 75, self.fonts["tiny"], UI_TEXT)
        draw_text(surface, f"SPD: {self.player.get_total_spd()}",
                  630, stats_y + 90, self.fonts["tiny"], UI_TEXT)

        # Buffs
        if self.player.stats.buffs:
            draw_text(surface, "Buffs:", 630, stats_y + 115, self.fonts["tiny"], GOLD)
            for bi, buff in enumerate(self.player.stats.buffs[:3]):
                sign = "+" if buff["amount"] > 0 else ""
                draw_text(surface, f"{sign}{buff['amount']} {buff['stat']} ({buff['duration']}t)",
                          635, stats_y + 130 + bi * 14, self.fonts["tiny"],
                          GREEN if buff["amount"] > 0 else RED)

    def _draw_combat_log(self, surface):
        """Draw combat log."""
        log_y = SCREEN_HEIGHT - 80
        for i, msg in enumerate(self.combat_log[-4:]):
            alpha = 255 - i * 30
            draw_text(surface, msg, 25, log_y + i * 16,
                      self.fonts["tiny"], (*UI_TEXT[:3],))

    def _draw_target_cursor(self, surface, alive_enemies):
        """Draw target selection cursor."""
        if not alive_enemies:
            return
        idx = min(self.selected_target_index, len(alive_enemies) - 1)
        ex = SCREEN_WIDTH * 3 // 4
        ey = 100 + idx * 100

        # Blinking arrow
        offset = int(math.sin(pygame.time.get_ticks() * 0.005) * 5)
        pygame.draw.polygon(surface, GOLD, [
            (ex - 50 + offset, ey - 5),
            (ex - 40 + offset, ey),
            (ex - 50 + offset, ey + 5),
        ])
        draw_text(surface, "SELECT TARGET", SCREEN_WIDTH // 2,
                  SCREEN_HEIGHT // 2 + 20, self.fonts["small"], GOLD, center=True)

    def _draw_result_overlay(self, surface):
        """Draw victory/defeat overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        if self.result == "victory":
            draw_text(surface, "VICTORY!", SCREEN_WIDTH // 2, 200,
                      self.fonts["title"], GOLD, center=True)
            draw_text(surface, f"XP Gained: {self.total_xp}", SCREEN_WIDTH // 2, 280,
                      self.fonts["medium"], YELLOW, center=True)
            draw_text(surface, f"Gold Gained: {self.total_gold}", SCREEN_WIDTH // 2, 320,
                      self.fonts["medium"], GOLD, center=True)

            if self.loot_drops:
                draw_text(surface, "Loot:", SCREEN_WIDTH // 2, 370,
                          self.fonts["medium"], WHITE, center=True)
                for i, item in enumerate(self.loot_drops[:5]):
                    from src.utils import get_rarity_color
                    color = get_rarity_color(item.rarity)
                    draw_text(surface, item.name, SCREEN_WIDTH // 2, 400 + i * 25,
                              self.fonts["small"], color, center=True)

        elif self.result == "defeat":
            draw_text(surface, "DEFEATED", SCREEN_WIDTH // 2, 250,
                      self.fonts["title"], RED, center=True)
            draw_text(surface, "You have fallen in battle...", SCREEN_WIDTH // 2, 330,
                      self.fonts["medium"], UI_TEXT, center=True)

        draw_text(surface, "Press ENTER to continue", SCREEN_WIDTH // 2, 500,
                  self.fonts["small"], LIGHT_GRAY, center=True)


# Import at module level
from src.constants import LIGHT_GRAY, GRAY
