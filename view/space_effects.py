# Kart-Engine v2.3
import math
import random
import pygame
from constants import TILE_SIZE
from model.circuit import Circuit
from view.theme_effects import ThemeEffects
from view.tile_renderer import chevron_points, boost_pad

S = TILE_SIZE


class SpaceEffects(ThemeEffects):
    """Animations du thème espace.

      - draw_background : sous la piste (étoiles qui scintillent, étoiles filantes, planète) ;
      - draw_ground     : sur la piste (balises qui clignotent, boosts, poussière) ;
      - draw_sky        : au-dessus des voitures (cargo spatial qui survole la station).
    """

    def __init__(self, circuit: Circuit):
        rng = random.Random(2026)
        self.width = circuit.pixel_width()
        self.height = circuit.pixel_height()

        # Étoiles qui scintillent : (x, y, vitesse, phase)
        self.stars = [(rng.randrange(self.width), rng.randrange(self.height),
                       rng.uniform(1.0, 3.0), rng.uniform(0, 2 * math.pi)) for _ in range(90)]

        # La planète : placée sous le plus grand trou du circuit
        self.planet_center = self._biggest_void_center(circuit)
        self.planet_radius = 95
        self._build_planet()

        # Balises lumineuses au bord du vide (sur le hors-piste) : (x, y, couleur, phase)
        self.beacons = []
        for row in circuit.grid:
            for tile in row:
                if tile.terrain != "grass":
                    continue
                for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    neighbour = circuit.get_tile(tile.col + dc, tile.row + dr)
                    if (neighbour is None or neighbour.terrain == "void") and rng.random() < 0.5:
                        x = tile.col * S + S // 2 + dc * (S // 2 - 14)
                        y = tile.row * S + S // 2 + dr * (S // 2 - 14)
                        color = (255, 60, 60) if rng.random() < 0.6 else (60, 255, 120)
                        self.beacons.append((x, y, color, rng.uniform(0, 1.2)))

        # Cases de boost (pour faire défiler une flèche lumineuse)
        self.boosts = [(pygame.Rect(t.col * S, t.row * S, S, S), t.boost_angle)
                       for row in circuit.grid for t in row if t.block == "boost"]

        # Poussière spatiale qui dérive lentement : (x, y, vx, vy)
        self.dust = [(rng.uniform(0, self.width), rng.uniform(0, self.height),
                      rng.uniform(-12, 12), rng.uniform(4, 14)) for _ in range(45)]

        self.ship = self._build_ship()
        self.font = pygame.font.SysFont("Arial", 12, bold=True)

    # ================= Préparation =================

    def _biggest_void_center(self, circuit: Circuit) -> tuple:
        """Centre (en pixels) de la case de vide la plus entourée de vide : là où on voit le mieux."""
        best, best_score = (self.width * 3 // 4, self.height * 3 // 4), -1
        for row in circuit.grid:
            for tile in row:
                if tile.terrain != "void":
                    continue
                score = sum(1 for dc in range(-2, 3) for dr in range(-2, 3)
                            if (t := circuit.get_tile(tile.col + dc, tile.row + dr)) is not None
                            and t.terrain == "void")
                if score > best_score:
                    best_score = score
                    best = (tile.col * S + S // 2, tile.row * S + S)
        return best

    def _build_planet(self) -> None:
        """Prépare la planète : une texture de bandes (qui défilera) et un masque rond avec de l'ombre."""
        d = self.planet_radius * 2
        rng = random.Random(5)
        self.bands = pygame.Surface((d * 2, d))
        y = 0
        while y < d:   # bandes horizontales de couleurs proches : une planète gazeuse
            h = rng.randint(6, 18)
            color = rng.choice([(196, 120, 80), (220, 160, 110), (170, 90, 70), (235, 190, 140), (150, 80, 70)])
            pygame.draw.rect(self.bands, color, (0, y, d * 2, h))
            for _ in range(6):   # petits tourbillons
                x = rng.randrange(d * 2)
                pygame.draw.ellipse(self.bands, tuple(min(255, c + 20) for c in color), (x, y, 26, max(3, h // 2)))
            y += h
        self.bands.blit(self.bands, (d, 0), (0, 0, d, d))   # la texture boucle sans raccord

        self.planet_mask = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(self.planet_mask, (255, 255, 255, 255), (d // 2, d // 2), self.planet_radius)
        self.planet_shade = pygame.Surface((d, d), pygame.SRCALPHA)
        for k in range(40):   # ombre progressive du côté opposé à la lumière
            alpha = int(k * 5)
            pygame.draw.circle(self.planet_shade, (0, 0, 20, alpha),
                               (d // 2 + 30 + k * 2, d // 2 + 20 + k), self.planet_radius - k)
        self.planet_shade.blit(self.planet_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def _build_ship(self) -> pygame.Surface:
        """Petit cargo spatial vu de dessus, l'avant vers la droite."""
        ship = pygame.Surface((140, 60), pygame.SRCALPHA)
        hull = [(10, 18), (90, 10), (132, 30), (90, 50), (10, 42), (2, 30)]
        pygame.draw.polygon(ship, (120, 126, 140), hull)
        pygame.draw.polygon(ship, (70, 74, 88), hull, 2)
        for x in (28, 48, 68):   # conteneurs
            pygame.draw.rect(ship, (210, 120, 40), (x, 20, 16, 20), border_radius=2)
            pygame.draw.rect(ship, (150, 80, 30), (x, 20, 16, 20), 1, border_radius=2)
        pygame.draw.polygon(ship, (30, 40, 70), [(98, 22), (120, 30), (98, 38)])   # cockpit
        for y in (16, 44):   # réacteurs
            pygame.draw.circle(ship, (60, 60, 75), (6, y - 2 if y < 30 else y + 2), 7)
        return ship

    # ================= Sous la piste =================

    def draw_background(self, screen: pygame.Surface, time_ms: int) -> None:
        t = time_ms / 1000
        self._draw_planet(screen, t)
        for x, y, speed, phase in self.stars:   # scintillement
            light = (math.sin(t * speed + phase) + 1) / 2
            b = int(90 + 165 * light)
            screen.set_at((x, y), (b, b, 255))
            if light > 0.85:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    screen.set_at((x + dx, y + dy), (b // 2, b // 2, 160))
        self._draw_shooting_star(screen, time_ms)

    def _draw_planet(self, screen: pygame.Surface, t: float) -> None:
        d = self.planet_radius * 2
        cx, cy = self.planet_center
        # Lune en orbite : derrière la planète quand elle est « en haut » de l'ellipse
        a = t * 0.5
        moon = (cx + 150 * math.cos(a), cy + 45 * math.sin(a))
        behind = math.sin(a) < 0
        if behind:
            self._draw_moon(screen, moon)
        # Planète : les bandes défilent lentement -> elle a l'air de tourner
        planet = pygame.Surface((d, d), pygame.SRCALPHA)
        offset = int(t * 12) % d
        planet.blit(self.bands, (-offset, 0))
        planet.blit(self.planet_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        planet.blit(self.planet_shade, (0, 0))
        screen.blit(planet, (cx - d // 2, cy - d // 2))
        if not behind:
            self._draw_moon(screen, moon)

    def _draw_moon(self, screen: pygame.Surface, pos: tuple) -> None:
        x, y = int(pos[0]), int(pos[1])
        pygame.draw.circle(screen, (190, 190, 200), (x, y), 16)
        pygame.draw.circle(screen, (150, 150, 165), (x - 5, y - 4), 4)   # cratères
        pygame.draw.circle(screen, (150, 150, 165), (x + 6, y + 5), 3)
        pygame.draw.circle(screen, (110, 110, 130), (x + 4, y + 3), 16, 0, False, False, True, True)

    def _draw_shooting_star(self, screen: pygame.Surface, time_ms: int) -> None:
        """Une étoile filante toutes les 3 secondes, qui traverse l'écran en 0,8 seconde."""
        period = 3000
        index, local = divmod(time_ms, period)
        if local > 800:
            return
        rng = random.Random(index)
        x0, y0 = rng.uniform(0, self.width * 0.6), rng.uniform(0, self.height * 0.4)
        angle = rng.uniform(0.3, 0.7)
        dist = local / 800 * 900
        head = (x0 + dist * math.cos(angle), y0 + dist * math.sin(angle))
        for k in range(12):   # traînée de plus en plus sombre
            back = k * 9
            p1 = (head[0] - back * math.cos(angle), head[1] - back * math.sin(angle))
            p2 = (head[0] - (back + 9) * math.cos(angle), head[1] - (back + 9) * math.sin(angle))
            b = 255 - k * 20
            pygame.draw.line(screen, (b, b, min(255, b + 30)), p1, p2, 2)

    # ================= Sur la piste =================

    def draw_ground(self, screen: pygame.Surface, time_ms: int) -> None:
        t = time_ms / 1000
        # Balises qui clignotent
        for x, y, color, phase in self.beacons:
            if (t + phase) % 1.2 < 0.25:
                halo = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.circle(halo, (*color, 90), (12, 12), 11)
                screen.blit(halo, (x - 12, y - 12))
                pygame.draw.circle(screen, color, (x, y), 4)
            else:
                pygame.draw.circle(screen, tuple(c // 3 for c in color), (x, y), 3)
        # Flèche lumineuse qui défile sur les boosts
        for rect, angle in self.boosts:
            offset = (t * 90) % 60 - 30            # le chevron avance dans le sens du boost
            screen.set_clip(boost_pad(rect, angle))
            pygame.draw.lines(screen, (255, 200, 245), False,
                              chevron_points(rect.centerx, rect.centery, angle, offset), 4)
            screen.set_clip(None)
        # Poussière spatiale
        for x, y, vx, vy in self.dust:
            px = (x + vx * t) % self.width
            py = (y + vy * t) % self.height
            screen.set_at((int(px), int(py)), (150, 170, 220))

    # ================= Au-dessus des voitures =================

    def sound_cues(self, previous_ms: int, time_ms: int) -> list[str]:
        """Le son du cargo démarre au moment où il commence à traverser l'écran."""
        if (previous_ms + 4000) // 15000 != (time_ms + 4000) // 15000:
            return ["ship"]
        return []

    def draw_sky(self, screen: pygame.Surface, time_ms: int) -> None:
        """Un cargo spatial survole la station toutes les 15 secondes (en 7 secondes)."""
        period, duration = 15000, 7000
        index, local = divmod(time_ms + 4000, period)
        if local > duration:
            return
        rng = random.Random(index * 7 + 1)
        q = local / duration
        y = rng.uniform(150, self.height - 150)
        x = -160 + q * (self.width + 320)
        tilt = rng.uniform(-12, 12)
        ship = pygame.transform.rotate(self.ship, tilt)
        # Ombre portée loin en dessous (le cargo vole haut) : décalée et transparente
        shadow = ship.copy()
        shadow.fill((0, 0, 0, 90), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(shadow, shadow.get_rect(center=(x + 60, y + 80)))
        # Flammes des réacteurs
        for dy in (-14, 14):
            flame_len = 14 + 4 * math.sin(time_ms / 40)
            pygame.draw.line(screen, (120, 200, 255), (x - 70, y + dy), (x - 70 - flame_len, y + dy), 5)
        screen.blit(ship, ship.get_rect(center=(x, y)))
        # Feux de navigation qui clignotent
        if (time_ms // 300) % 2 == 0:
            pygame.draw.circle(screen, (255, 70, 70), (int(x - 10), int(y - 22)), 3)
            pygame.draw.circle(screen, (70, 255, 120), (int(x - 10), int(y + 22)), 3)
