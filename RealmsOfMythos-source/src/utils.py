"""Utility functions and helpers."""

import math
import random
import pygame
from src.constants import (
    TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, BLACK,
    UI_BG, UI_BORDER, UI_TEXT, GOLD, RARITY_COLORS, RARITY_COMMON
)


def clamp(value, min_val, max_val):
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * t


def distance(x1, y1, x2, y2):
    """Euclidean distance."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def manhattan_distance(x1, y1, x2, y2):
    """Manhattan distance."""
    return abs(x2 - x1) + abs(y2 - y1)


def tile_to_pixel(tx, ty):
    """Convert tile coords to pixel coords."""
    return tx * TILE_SIZE, ty * TILE_SIZE


def pixel_to_tile(px, py):
    """Convert pixel coords to tile coords."""
    return int(px // TILE_SIZE), int(py // TILE_SIZE)


def random_choice_weighted(choices):
    """Pick from weighted choices: list of (item, weight)."""
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    cumulative = 0
    for item, weight in choices:
        cumulative += weight
        if r <= cumulative:
            return item
    return choices[-1][0]


def draw_text(surface, text, x, y, font, color=UI_TEXT, shadow=True, center=False):
    """Draw text with optional shadow."""
    if shadow:
        shadow_surf = font.render(text, True, BLACK)
        if center:
            rect = shadow_surf.get_rect(center=(x + 1, y + 1))
            surface.blit(shadow_surf, rect)
        else:
            surface.blit(shadow_surf, (x + 1, y + 1))
    text_surf = font.render(text, True, color)
    if center:
        rect = text_surf.get_rect(center=(x, y))
        surface.blit(text_surf, rect)
    else:
        surface.blit(text_surf, (x, y))
    return text_surf.get_width(), text_surf.get_height()


def draw_panel(surface, x, y, width, height, bg=UI_BG, border=UI_BORDER, alpha=230):
    """Draw a UI panel with border."""
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((*bg, alpha))
    surface.blit(panel, (x, y))
    pygame.draw.rect(surface, border, (x, y, width, height), 2)


def draw_bar(surface, x, y, width, height, current, maximum, color, bg_color=(30, 25, 40)):
    """Draw a progress bar."""
    pygame.draw.rect(surface, bg_color, (x, y, width, height))
    if maximum > 0:
        fill_width = int((current / maximum) * width)
        fill_width = clamp(fill_width, 0, width)
        if fill_width > 0:
            pygame.draw.rect(surface, color, (x, y, fill_width, height))
            highlight = tuple(min(255, c + 40) for c in color)
            pygame.draw.rect(surface, highlight, (x, y, fill_width, height // 3))
    pygame.draw.rect(surface, UI_BORDER, (x, y, width, height), 1)


def draw_tooltip(surface, text_lines, x, y, font):
    """Draw a tooltip box with text."""
    padding = 8
    line_height = font.get_linesize()
    max_width = max(font.size(line)[0] for line in text_lines) + padding * 2
    total_height = len(text_lines) * line_height + padding * 2

    # Keep on screen
    if x + max_width > SCREEN_WIDTH:
        x = SCREEN_WIDTH - max_width - 5
    if y + total_height > SCREEN_HEIGHT:
        y = SCREEN_HEIGHT - total_height - 5

    draw_panel(surface, x, y, max_width, total_height, alpha=240)
    for i, line in enumerate(text_lines):
        draw_text(surface, line, x + padding, y + padding + i * line_height, font)


def get_rarity_color(rarity):
    """Get color for item rarity."""
    return RARITY_COLORS.get(rarity, RARITY_COLORS[RARITY_COMMON])


def shake_offset(duration_remaining, intensity):
    """Generate screen shake offset."""
    if duration_remaining <= 0:
        return 0, 0
    ox = random.randint(-intensity, intensity)
    oy = random.randint(-intensity, intensity)
    return ox, oy


def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width."""
    words = text.split(" ")
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def create_surface_with_outline(width, height, fill_color, outline_color, outline_width=1):
    """Create a surface with fill and outline."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill(fill_color)
    pygame.draw.rect(surf, outline_color, (0, 0, width, height), outline_width)
    return surf


class SpriteSheet:
    """Simple procedural sprite generator for the game."""

    @staticmethod
    def create_character_sprite(color, size=TILE_SIZE, char_class="warrior"):
        """Generate a character sprite procedurally."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2

        # Body
        body_rect = pygame.Rect(size // 4, size // 3, size // 2, size // 2)
        pygame.draw.rect(surf, color, body_rect, border_radius=3)

        # Head
        head_radius = size // 5
        pygame.draw.circle(surf, (220, 180, 140), (center, size // 4), head_radius)

        # Class-specific details
        if char_class == "warrior":
            # Sword
            pygame.draw.line(surf, (180, 180, 200), (size - 6, size // 4), (size - 6, size * 3 // 4), 2)
            pygame.draw.line(surf, (180, 180, 200), (size - 9, size // 3), (size - 3, size // 3), 2)
        elif char_class == "mage":
            # Staff
            pygame.draw.line(surf, GOLD, (size - 6, size // 6), (size - 6, size * 3 // 4), 2)
            pygame.draw.circle(surf, (100, 150, 255), (size - 6, size // 6), 3)
        elif char_class == "rogue":
            # Daggers
            pygame.draw.line(surf, (180, 180, 200), (size - 5, size // 3), (size - 5, size * 2 // 3), 2)
            pygame.draw.line(surf, (180, 180, 200), (3, size // 3), (3, size * 2 // 3), 2)
        elif char_class == "ranger":
            # Bow
            pygame.draw.arc(surf, (139, 90, 43), (size - 10, size // 5, 8, size // 2), -1.2, 1.2, 2)
        elif char_class == "paladin":
            # Shield
            pygame.draw.ellipse(surf, (200, 200, 50), (2, size // 3, 8, 10))
            pygame.draw.line(surf, (180, 180, 200), (size - 6, size // 4), (size - 6, size * 3 // 4), 2)

        return surf

    @staticmethod
    def create_enemy_sprite(color, size=TILE_SIZE, enemy_type="normal"):
        """Generate an enemy sprite procedurally."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2

        if enemy_type == "boss":
            # Larger, menacing
            pygame.draw.polygon(surf, color, [
                (center, 2), (size - 3, size // 3),
                (size - 5, size - 3), (5, size - 3), (3, size // 3)
            ])
            # Eyes
            pygame.draw.circle(surf, (255, 50, 50), (center - 5, size // 3), 3)
            pygame.draw.circle(surf, (255, 50, 50), (center + 5, size // 3), 3)
            # Crown
            pygame.draw.polygon(surf, GOLD, [
                (center - 8, 6), (center - 4, 2), (center, 6),
                (center + 4, 2), (center + 8, 6)
            ])
        elif enemy_type == "undead":
            # Skull-like
            pygame.draw.ellipse(surf, color, (size // 5, size // 6, size * 3 // 5, size * 2 // 3))
            pygame.draw.rect(surf, (0, 0, 0), (center - 5, size // 3, 4, 4))
            pygame.draw.rect(surf, (0, 0, 0), (center + 1, size // 3, 4, 4))
            pygame.draw.rect(surf, (0, 0, 0), (center - 3, size // 2 + 2, 6, 3))
        elif enemy_type == "beast":
            # Animal-like
            pygame.draw.ellipse(surf, color, (4, size // 3, size - 8, size // 2))
            pygame.draw.circle(surf, color, (size - 6, size // 3 + 2), 5)
            pygame.draw.circle(surf, (255, 200, 0), (size - 5, size // 3), 2)
            # Tail
            pygame.draw.arc(surf, color, (0, size // 4, 12, size // 2), 0.5, 2.5, 2)
        else:
            # Generic enemy
            pygame.draw.ellipse(surf, color, (size // 5, size // 5, size * 3 // 5, size * 3 // 5))
            pygame.draw.circle(surf, (255, 0, 0), (center - 4, center - 2), 2)
            pygame.draw.circle(surf, (255, 0, 0), (center + 4, center - 2), 2)
            pygame.draw.arc(surf, (255, 0, 0), (center - 5, center, 10, 6), 3.14, 6.28, 1)

        return surf

    @staticmethod
    def create_item_sprite(color, size=24, item_type="potion"):
        """Generate an item sprite."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2

        if item_type == "potion":
            pygame.draw.ellipse(surf, color, (size // 4, size // 2, size // 2, size // 2 - 1))
            pygame.draw.rect(surf, (200, 200, 200), (center - 2, size // 4, 4, size // 4))
            pygame.draw.rect(surf, (200, 200, 200), (center - 4, size // 4 - 2, 8, 3))
        elif item_type == "weapon":
            pygame.draw.line(surf, (180, 180, 200), (4, size - 4), (size - 4, 4), 3)
            pygame.draw.line(surf, color, (size // 3, size * 2 // 3), (size * 2 // 3, size // 3), 2)
        elif item_type == "armor":
            pygame.draw.rect(surf, color, (size // 4, size // 4, size // 2, size // 2), border_radius=3)
            pygame.draw.rect(surf, (200, 200, 200), (size // 4, size // 4, size // 2, size // 2), 1, border_radius=3)
        elif item_type == "scroll":
            pygame.draw.rect(surf, (220, 200, 160), (size // 4, size // 5, size // 2, size * 3 // 5))
            pygame.draw.circle(surf, (200, 180, 140), (center, size // 5), size // 6)
            pygame.draw.circle(surf, (200, 180, 140), (center, size * 4 // 5), size // 6)
        elif item_type == "ring":
            pygame.draw.circle(surf, color, (center, center), size // 3, 2)
            pygame.draw.circle(surf, GOLD, (center, size // 3), 3)
        elif item_type == "gold":
            pygame.draw.circle(surf, GOLD, (center, center), size // 3)
            pygame.draw.circle(surf, (200, 170, 0), (center, center), size // 3, 1)

        return surf

    @staticmethod
    def create_npc_sprite(color, size=TILE_SIZE, npc_type="villager"):
        """Generate an NPC sprite."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2

        # Body
        body_rect = pygame.Rect(size // 4, size // 3, size // 2, size // 2)
        pygame.draw.rect(surf, color, body_rect, border_radius=3)

        # Head
        pygame.draw.circle(surf, (220, 180, 140), (center, size // 4), size // 5)

        if npc_type == "merchant":
            # Hat
            pygame.draw.rect(surf, GOLD, (center - 7, size // 8 - 2, 14, 4))
            pygame.draw.rect(surf, GOLD, (center - 4, 2, 8, size // 8))
        elif npc_type == "quest":
            # Exclamation mark
            pygame.draw.circle(surf, GOLD, (center, 3), 3)
            pygame.draw.rect(surf, GOLD, (center - 1, 1, 2, 3))
        elif npc_type == "healer":
            # Cross
            pygame.draw.rect(surf, WHITE, (center - 1, size // 3 + 2, 3, 8))
            pygame.draw.rect(surf, WHITE, (center - 4, size // 3 + 5, 9, 3))

        return surf

    @staticmethod
    def create_tile_sprite(color, size=TILE_SIZE, tile_type="grass"):
        """Generate a tile sprite."""
        surf = pygame.Surface((size, size))
        surf.fill(color)

        if tile_type == "grass":
            for _ in range(5):
                gx = random.randint(2, size - 3)
                gy = random.randint(2, size - 3)
                shade = random.randint(-20, 20)
                c = tuple(clamp(color[i] + shade, 0, 255) for i in range(3))
                pygame.draw.line(surf, c, (gx, gy), (gx, gy - random.randint(2, 5)), 1)
        elif tile_type == "stone":
            for _ in range(3):
                sx = random.randint(3, size - 5)
                sy = random.randint(3, size - 5)
                shade = random.randint(-15, 15)
                c = tuple(clamp(color[i] + shade, 0, 255) for i in range(3))
                pygame.draw.rect(surf, c, (sx, sy, random.randint(3, 8), random.randint(3, 6)))
        elif tile_type == "water":
            for i in range(0, size, 6):
                wave_y = size // 2 + int(math.sin(i * 0.3) * 3)
                c = tuple(clamp(color[j] + 30, 0, 255) for j in range(3))
                pygame.draw.line(surf, c, (i, wave_y), (i + 4, wave_y), 1)
        elif tile_type == "sand":
            for _ in range(8):
                dx = random.randint(0, size - 1)
                dy = random.randint(0, size - 1)
                shade = random.randint(-10, 10)
                c = tuple(clamp(color[i] + shade, 0, 255) for i in range(3))
                surf.set_at((dx, dy), c)
        elif tile_type == "wall":
            pygame.draw.rect(surf, tuple(max(0, c - 20) for c in color), (0, 0, size, size), 2)
            pygame.draw.line(surf, tuple(min(255, c + 20) for c in color), (0, 0), (size, 0), 1)
            pygame.draw.line(surf, tuple(max(0, c - 30) for c in color), (0, size - 1), (size, size - 1), 1)

        return surf

    @staticmethod
    def create_chest_sprite(size=TILE_SIZE):
        """Generate a chest sprite."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # Body
        pygame.draw.rect(surf, GOLD, (4, size // 3, size - 8, size // 2), border_radius=2)
        pygame.draw.rect(surf, (180, 140, 0), (4, size // 3, size - 8, size // 2), 1, border_radius=2)
        # Lid
        pygame.draw.rect(surf, (200, 160, 20), (3, size // 3 - 4, size - 6, 6), border_radius=2)
        # Lock
        pygame.draw.circle(surf, (150, 150, 160), (size // 2, size // 2 + 2), 3)
        return surf

    @staticmethod
    def create_door_sprite(size=TILE_SIZE, locked=False):
        """Generate a door sprite."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        color = (120, 80, 40) if not locked else (80, 50, 30)
        pygame.draw.rect(surf, color, (6, 2, size - 12, size - 4), border_radius=2)
        pygame.draw.rect(surf, (90, 60, 30), (6, 2, size - 12, size - 4), 1, border_radius=2)
        # Handle
        handle_color = GOLD if locked else (160, 160, 170)
        pygame.draw.circle(surf, handle_color, (size - 10, size // 2), 2)
        return surf
