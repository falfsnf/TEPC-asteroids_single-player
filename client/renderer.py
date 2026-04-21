"""Client-side rendering (pygame)."""

import math

import pygame as pg

from core import config as C
from core.entities import Asteroid, BlackHole, Bullet, Ship, UFO, PowerUp
from core.scene import SceneState
from core.utils import draw_image


class Renderer:
    """Draws scenes and entities without coupling game rules to Game."""

    def __init__(
        self,
        screen: pg.Surface,
        config: object = C,
        fonts: dict[str, pg.font.Font] | None = None,
    ) -> None:
        self.screen = screen
        self.config = config
        safe_fonts = fonts or {}
        self.font = safe_fonts["font"]
        self.big = safe_fonts["big"]

        self._draw_dispatch: dict[type, callable] = {
            Bullet: self._draw_bullet,
            Asteroid: self._draw_asteroid,
            Ship: self._draw_ship,
            UFO: self._draw_ufo,
            PowerUp: self._draw_powerup,
            BlackHole: self._draw_black_hole,
        }

    def clear(self) -> None:
        self.screen.fill(self.config.BLACK)

    def draw_world(self, world: object) -> None:
        sprites = getattr(world, "all_sprites", [])
        for sprite in sprites:
            drawer = self._draw_dispatch.get(type(sprite))
            if drawer is not None:
                drawer(sprite)

    def draw_hud(
        self,
        score: int,
        lives: int,
        wave: int,
        state: SceneState,
        ship = None,
        freeze_timer = 0.0
    ) -> None:
        if state != SceneState.PLAY:
            return

        text = f"SCORE {score:06d}   LIVES {lives}   WAVE {wave}"
        label = self.font.render(text, True, self.config.WHITE)
        self.screen.blit(label, (10, 10))

        if freeze_timer > 0.0:
            f_text = f"FROZEN {freeze_timer:.1f}s"
            f_label = self.font.render(f_text, True, (100, 200, 255))
            self.screen.blit(f_label, (self.config.WIDTH - 200, 10))

        if ship is not None:
            self._draw_shield_bar(ship)

    def draw_menu(self) -> None:
        self._draw_text(
            self.big,
            "ASTEROIDS",
            self.config.WIDTH // 2 - 170,
            200,
        )
        self._draw_text(
            self.font,
            "Press any key",
            self.config.WIDTH // 2 - 170,
            350,
        )

    def draw_game_over(self) -> None:
        self._draw_text(
            self.big,
            "GAME OVER",
            self.config.WIDTH // 2 - 170,
            260,
        )
        self._draw_text(
            self.font,
            "Press any key",
            self.config.WIDTH // 2 - 170,
            340,
        )

    def _draw_text(
        self,
        font: pg.font.Font,
        text: str,
        x: int,
        y: int,
    ) -> None:
        label = font.render(text, True, self.config.WHITE)
        self.screen.blit(label, (x, y))

    def _draw_bullet(self, bullet: Bullet) -> None:
        center = (int(bullet.pos.x), int(bullet.pos.y))
        pg.draw.circle(
            self.screen,
            self.config.WHITE,
            center,
            bullet.r,
            width=1,
        )

    def _draw_asteroid(self, asteroid: Asteroid) -> None:
        points = []
        for point in asteroid.poly:
            px = int(asteroid.pos.x + point.x)
            py = int(asteroid.pos.y + point.y)
            points.append((px, py))
        pg.draw.polygon(self.screen, self.config.WHITE, points, width=1)

    def _draw_ship(self, ship: Ship) -> None:
        p1, p2, p3 = ship.ship_points()
        points = [
            (int(p1.x), int(p1.y)),
            (int(p2.x), int(p2.y)),
            (int(p3.x), int(p3.y)),
        ]
        pg.draw.polygon(self.screen, self.config.WHITE, points, width=1)

        if ship.shield_active:
            center = (int(ship.pos.x), int(ship.pos.y))
            pg.draw.circle(self.screen, self.config.WHITE, center, ship.r + 10, width=2)

        if ship.invuln > 0.0 and int(ship.invuln * 10) % 2 == 0:
            center = (int(ship.pos.x), int(ship.pos.y))
            pg.draw.circle(
                self.screen,
                self.config.WHITE,
                center,
                ship.r + 6,
                width=1,
            )

    def _draw_black_hole(self, bh: BlackHole) -> None:
        center = (int(bh.pos.x), int(bh.pos.y))

        # Faint outer influence ring (so the player sees the danger zone).
        pg.draw.circle(
            self.screen,
            (60, 60, 80),
            center,
            int(bh.influence_r),
            width=1,
        )

        # Pulsing accretion rings between influence and event horizon.
        t = bh.age
        for i in range(3):
            phase = (t * 0.6 + i * 0.33) % 1.0
            ring_r = int(bh.r + 6 + phase * (bh.influence_r - bh.r - 6) * 0.4)
            # Fade as the ring expands outward.
            brightness = int(180 * (1.0 - phase))
            color = (brightness, brightness, min(255, brightness + 30))
            pg.draw.circle(self.screen, color, center, ring_r, width=1)

        # Solid black disk (swallows what's behind it visually).
        pg.draw.circle(self.screen, self.config.BLACK, center, bh.r)

        # Bright event-horizon ring.
        pg.draw.circle(self.screen, self.config.WHITE, center, bh.r, width=2)

        # Inner swirl: a small rotating tick mark to give it motion.
        ang = t * 4.0
        inner_r = max(2, bh.r // 2)
        tip = (
            int(bh.pos.x + math.cos(ang) * inner_r),
            int(bh.pos.y + math.sin(ang) * inner_r),
        )
        pg.draw.line(self.screen, self.config.WHITE, center, tip, 1)

    def _draw_ufo(self, ufo: UFO) -> None:
        width = ufo.r * 2
        height = ufo.r

        body = pg.Rect(0, 0, width, height)
        body.center = (int(ufo.pos.x), int(ufo.pos.y))
        pg.draw.ellipse(self.screen, self.config.WHITE, body, width=1)

        cup = pg.Rect(0, 0, int(width * 0.5), int(height * 0.7))
        cup.center = (int(ufo.pos.x), int(ufo.pos.y - height * 0.3))
        pg.draw.ellipse(self.screen, self.config.WHITE, cup, width=1)

    def _draw_powerup(self, powerup: PowerUp) -> None:
        center = (int(powerup.pos.x), int(powerup.pos.y))
        r = powerup.r
        points = [
            (center[0], center[1] - r),
            (center[0] + r, center[1]),
            (center[0], center[1] + r),
            (center[0] - r, center[1]),
        ]
        color = (100, 200, 255) if powerup.type == "freeze" else self.config.WHITE
        pg.draw.polygon(self.screen, color, points, width=2)
        pg.draw.circle(self.screen, color, center, r // 2, width=1)

    def _draw_shield_bar(self, ship) -> None:
        bar_x      = 10
        bar_y      = 36        
        bar_width  = 120
        bar_height = 8

        ratio = ship.shield_energy / self.config.SHIELD_MAX_ENERGY
        fill  = int(bar_width * ratio)

        pg.draw.rect(self.screen, (80, 80, 80),
                    (bar_x, bar_y, bar_width, bar_height))

        if fill > 0:
            color = self.config.WHITE if not ship.shield_active else (100, 180, 255)
            pg.draw.rect(self.screen, color,
                        (bar_x, bar_y, fill, bar_height))

        pg.draw.rect(self.screen, self.config.WHITE,
                    (bar_x, bar_y, bar_width, bar_height), width=1)

        label = self.font.render("SH", True, self.config.WHITE)
        self.screen.blit(label, (bar_x + bar_width + 6, bar_y - 4))
