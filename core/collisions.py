"""Collision detection and resolution."""

from dataclasses import dataclass, field
from random import uniform

import pygame as pg

from core import config as C
from core.entities import Asteroid, BlackHole, Bullet, Ship, UFO, UFO_BULLET_OWNER, PlayerId, PowerUp
from core.utils import Vec, rand_unit_vec


@dataclass
class CollisionResult:
    """Outcome of a single collision resolution pass."""

    events: list[str] = field(default_factory=list)
    score_deltas: dict[PlayerId, int] = field(default_factory=dict)
    ship_deaths: list[PlayerId] = field(default_factory=list)
    asteroids_to_spawn: list[tuple[Vec, Vec, str]] = field(default_factory=list)
    powerups_to_apply: list[tuple[PowerUp, Ship]] = field(default_factory=list)
    ufo_deaths: list[UFO] = field(default_factory=list)
    instant_deaths: list[PlayerId] = field(default_factory=list)


class CollisionManager:
    """Resolves all collisions between game entities."""

    def resolve(
        self,
        ships: dict[PlayerId, Ship],
        bullets: pg.sprite.Group,
        asteroids: pg.sprite.Group,
        ufos: pg.sprite.Group,
        powerups: pg.sprite.Group,
        black_holes: pg.sprite.Group | None = None,
    ) -> CollisionResult:
        result = CollisionResult()
        self._bullets_vs_asteroids(bullets, asteroids, result)
        self._ufo_vs_player_bullets(ufos, bullets, result)
        self._ufo_vs_asteroids(ufos, asteroids, result)
        self._ship_vs_asteroids(ships, asteroids, result)
        self._ship_vs_ufo_bullets(ships, bullets, result)
        self._ship_vs_powerup(ships, powerups, result)
        if black_holes is not None:
            self._ship_vs_black_holes(ships, black_holes, result)
        return result

    def _bullets_vs_asteroids(
        self,
        bullets: pg.sprite.Group,
        asteroids: pg.sprite.Group,
        result: CollisionResult,
    ) -> None:
        hits = pg.sprite.groupcollide(
            asteroids,
            bullets,
            False,
            True,
            collided=lambda a, b: (a.pos - b.pos).length() < a.r,
        )

        for ast, hit_bullets in hits.items():
            if any(b.owner_id == UFO_BULLET_OWNER for b in hit_bullets):
                ast.kill()
                result.events.append("asteroid_explosion")
                continue

            player_bullets = [b for b in hit_bullets if b.owner_id > 0]
            scorer = player_bullets[0].owner_id if player_bullets else None
            self._split_asteroid(ast, scorer_id=scorer, result=result)

    def _ufo_vs_player_bullets(
        self,
        ufos: pg.sprite.Group,
        bullets: pg.sprite.Group,
        result: CollisionResult,
    ) -> None:
        for ufo in list(ufos):
            for bullet in list(bullets):
                if bullet.owner_id <= 0:
                    continue
                if (ufo.pos - bullet.pos).length() < (ufo.r + bullet.r):
                    score = (
                        C.UFO_SMALL["score"]
                        if ufo.small
                        else C.UFO_BIG["score"]
                    )
                    result.score_deltas[bullet.owner_id] = (
                        result.score_deltas.get(bullet.owner_id, 0) + score
                    )
                    result.ufo_deaths.append(ufo)
                    ufo.kill()
                    bullet.kill()
                    result.events.append("ship_explosion")

    def _ufo_vs_asteroids(
        self,
        ufos: pg.sprite.Group,
        asteroids: pg.sprite.Group,
        result: CollisionResult,
    ) -> None:
        """UFO collided with asteroid.

        - UFO is destroyed.
        - Asteroid splits as if it were hit by a bullet, but
          without adding score.
        """
        for ufo in list(ufos):
            for ast in list(asteroids):
                if (ufo.pos - ast.pos).length() < (ufo.r + ast.r):
                    ufo.kill()
                    if ufo in ufos:
                        ufos.remove(ufo)

                    result.events.append("ship_explosion")
                    self._split_asteroid(ast, result=result)
                    break

    def _ship_vs_asteroids(
        self,
        ships: dict[PlayerId, Ship],
        asteroids: pg.sprite.Group,
        result: CollisionResult,
    ) -> None:
        for ship in ships.values():
            if ship.invuln > 0.0 or ship.shield_active: 
                continue
            if ship.invuln > 0.0:
                continue
            for ast in asteroids:
                if (ast.pos - ship.pos).length() < (ast.r + ship.r):
                    result.ship_deaths.append(ship.player_id)
                    return

    def _ship_vs_ufo_bullets(
        self,
        ships: dict[PlayerId, Ship],
        bullets: pg.sprite.Group,
        result: CollisionResult,
    ) -> None:
        for ship in ships.values():
            if ship.invuln > 0.0 or ship.shield_active: 
                continue
            if ship.invuln > 0.0:
                continue
            for bullet in list(bullets):
                if bullet.owner_id != UFO_BULLET_OWNER:
                    continue
                if (bullet.pos - ship.pos).length() < (bullet.r + ship.r):
                    bullet.kill()
                    result.ship_deaths.append(ship.player_id)
                    return

    def _ship_vs_powerup(
        self,
        ships: dict[PlayerId, Ship],
        powerups: pg.sprite.Group,
        result: CollisionResult,
    ):
        for ship in ships.values():
            for powerup in list(powerups):
                if pg.sprite.collide_rect(powerup, ship):
                    result.powerups_to_apply.append((powerup, ship))
                    result.events.append("powerup_got")
                    powerup.kill()
    def _ship_vs_black_holes(
        self,
        ships: dict[PlayerId, Ship],
        black_holes: pg.sprite.Group,
        result: CollisionResult,
    ) -> None:
        """Touching a black hole = instant Game Over.

        Ignores shield and invulnerability by design.
        """
        for ship in ships.values():
            for bh in black_holes:
                if (bh.pos - ship.pos).length() < (bh.r + ship.r):
                    result.instant_deaths.append(ship.player_id)
                    result.events.append("ship_explosion")
                    return

    def _split_asteroid(
        self,
        ast: Asteroid,
        result: CollisionResult,
        scorer_id: PlayerId | None = None,
    ) -> None:
        """Split or destroy an asteroid.

        scorer_id=None means no score is awarded (e.g. UFO-asteroid collision).
        """
        if scorer_id is not None:
            result.score_deltas[scorer_id] = (
                result.score_deltas.get(scorer_id, 0)
                + C.AST_SIZES[ast.size]["score"]
            )

        split = C.AST_SIZES[ast.size]["split"]
        pos = Vec(ast.pos)
        ast.kill()

        result.events.append("asteroid_explosion")

        for new_size in split:
            dirv = rand_unit_vec()
            speed = uniform(C.AST_VEL_MIN, C.AST_VEL_MAX) * C.AST_SPLIT_SPEED_MULT
            result.asteroids_to_spawn.append((pos, dirv * speed, new_size))
