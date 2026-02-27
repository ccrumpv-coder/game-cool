"""Particle system for visual effects."""

import random
import math
import pygame
from src.constants import MAX_PARTICLES


class Particle:
    """A single particle."""

    def __init__(self, x, y, color, vel_x=0, vel_y=0, lifetime=1.0,
                 size=3, gravity=0, shrink=True, fade=True):
        self.x = x
        self.y = y
        self.color = color
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.max_size = size
        self.gravity = gravity
        self.shrink = shrink
        self.fade = fade
        self.alive = True

    def update(self, dt):
        """Update particle state."""
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return

        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        self.vel_y += self.gravity * dt

        if self.shrink:
            ratio = self.lifetime / self.max_lifetime
            self.size = max(1, int(self.max_size * ratio))

    def draw(self, surface, camera_x=0, camera_y=0):
        """Draw the particle."""
        if not self.alive:
            return

        alpha = 255
        if self.fade:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            alpha = max(0, min(255, alpha))

        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)

        if self.size <= 1:
            if 0 <= sx < surface.get_width() and 0 <= sy < surface.get_height():
                surface.set_at((sx, sy), (*self.color[:3], alpha))
        else:
            particle_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, (*self.color[:3], alpha),
                               (self.size, self.size), self.size)
            surface.blit(particle_surf, (sx - self.size, sy - self.size))


class ParticleSystem:
    """Manages all particles."""

    def __init__(self):
        self.particles = []

    def update(self, dt):
        """Update all particles."""
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update(dt)

    def draw(self, surface, camera_x=0, camera_y=0):
        """Draw all particles."""
        for p in self.particles:
            p.draw(surface, camera_x, camera_y)

    def add(self, particle):
        """Add a particle."""
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(particle)

    def emit_burst(self, x, y, color, count=10, speed=80, lifetime=0.8,
                   size=3, gravity=0, spread=360):
        """Emit a burst of particles."""
        for _ in range(count):
            angle = math.radians(random.uniform(0, spread))
            spd = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            sz = random.randint(max(1, size - 1), size + 1)
            lt = random.uniform(lifetime * 0.5, lifetime)
            shade = tuple(min(255, max(0, c + random.randint(-30, 30))) for c in color[:3])
            self.add(Particle(x, y, shade, vx, vy, lt, sz, gravity))

    def emit_trail(self, x, y, color, direction=0, count=3, speed=40, lifetime=0.5, size=2):
        """Emit trailing particles."""
        for _ in range(count):
            angle = math.radians(direction + random.uniform(-30, 30))
            spd = random.uniform(speed * 0.3, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            shade = tuple(min(255, max(0, c + random.randint(-20, 20))) for c in color[:3])
            self.add(Particle(x + random.uniform(-3, 3), y + random.uniform(-3, 3),
                              shade, vx, vy, lifetime, size, 0))

    def emit_float_text(self, x, y, color, count=5, lifetime=1.0):
        """Emit upward floating particles (like for healing)."""
        for _ in range(count):
            vx = random.uniform(-15, 15)
            vy = random.uniform(-60, -30)
            self.add(Particle(x + random.uniform(-8, 8), y, color, vx, vy,
                              lifetime, random.randint(2, 4), 0))

    def clear(self):
        """Remove all particles."""
        self.particles.clear()
