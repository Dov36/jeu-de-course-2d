# Kart-Engine v2.3
import math
import random
import pygame
from constants import TILE_SIZE
from model.circuit import Circuit
from view.theme_effects import ThemeEffects

S = TILE_SIZE


def palm_positions(circuit: Circuit) -> list:
    """Positions des palmiers sur l'oasis : (x, y, angle de départ des feuilles).

    Utilisée à la fois pour dessiner leurs ombres (fixes, dans TileRenderer)
    et leurs feuilles (animées, ici) : les deux tombent donc au même endroit.
    """
    rng = random.Random(7)
    palms = []
    for row in circuit.grid:
        for tile in row:
            if tile.terrain != "grass" or rng.random() > 0.4:
                continue
            x = tile.col * S + S // 2 + rng.randint(-8, 8)
            y = tile.row * S + S // 2 + rng.randint(-8, 8)
            palms.append((x, y, rng.uniform(0, math.pi)))
    return palms


class DesertEffects(ThemeEffects):
    """Animations du thème désert.

    Au sol : rafales de sable, tornade de sable, boules de broussailles, ronds et poisson dans le lac.
    En hauteur : palmiers qui bougent au vent, vautours qui tournent, montgolfière de passage.
    """

    def __init__(self, circuit: Circuit):
        rng = random.Random(1987)
        self.width = circuit.pixel_width()
        self.height = circuit.pixel_height()
        self.palms = palm_positions(circuit)

        # Points dans le lac (centres des cases d'eau, un peu décalés) pour les ronds et le poisson
        self.water_points = [(t.col * S + S // 2 + rng.randint(-14, 14), t.row * S + S // 2 + rng.randint(-14, 14))
                             for row in circuit.grid for t in row if t.terrain == "water"]

        # Rafales de sable : (x, y, vitesse, longueur)
        self.wind = [(rng.uniform(0, self.width), rng.uniform(0, self.height),
                      rng.uniform(120, 220), rng.randint(14, 40)) for _ in range(28)]

        # Grains de sable de la tornade : (angle de départ, hauteur 0..1)
        self.devil_grains = [(rng.uniform(0, 2 * math.pi), rng.random()) for _ in range(70)]

        self.tumbleweed = self._build_tumbleweed()
        self.balloon = self._build_balloon()

    # ================= Préparation =================

    def _build_tumbleweed(self) -> pygame.Surface:
        """Boule de broussailles : un enchevêtrement de brindilles."""
        rng = random.Random(3)
        surf = pygame.Surface((36, 36), pygame.SRCALPHA)
        for _ in range(26):
            a1, a2 = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
            r1, r2 = rng.uniform(4, 16), rng.uniform(4, 16)
            pygame.draw.line(surf, rng.choice([(150, 110, 60), (120, 85, 45), (175, 135, 80)]),
                             (18 + r1 * math.cos(a1), 18 + r1 * math.sin(a1)),
                             (18 + r2 * math.cos(a2), 18 + r2 * math.sin(a2)), 2)
        return surf

    def _build_balloon(self) -> pygame.Surface:
        """Montgolfière vue de dessus : un disque à quartiers colorés."""
        surf = pygame.Surface((96, 96), pygame.SRCALPHA)
        colors = [(220, 50, 50), (250, 200, 40)]
        for k in range(10):
            a1, a2 = k * 2 * math.pi / 10, (k + 1) * 2 * math.pi / 10
            points = [(48, 48)] + [(48 + 44 * math.cos(a1 + (a2 - a1) * i / 6),
                                    48 + 44 * math.sin(a1 + (a2 - a1) * i / 6)) for i in range(7)]
            pygame.draw.polygon(surf, colors[k % 2], points)
        pygame.draw.circle(surf, (120, 40, 30), (48, 48), 44, 2)
        pygame.draw.circle(surf, (255, 240, 200), (48, 48), 8)          # ouverture en haut
        pygame.draw.circle(surf, (255, 255, 255, 90), (34, 34), 14)     # reflet du soleil
        return surf

    # ================= Au sol =================

    def draw_ground(self, screen: pygame.Surface, time_ms: int) -> None:
        t = time_ms / 1000
        self._draw_wind(screen, t)
        self._draw_lake(screen, time_ms)
        self._draw_dust_devil(screen, t)
        self._draw_tumbleweed(screen, time_ms)

    def _draw_wind(self, screen: pygame.Surface, t: float) -> None:
        """Rafales : de fines traînées de sable clair qui filent vers la droite."""
        for x, y, speed, length in self.wind:
            px = (x + speed * t) % (self.width + 60) - 30
            py = y + 6 * math.sin(t * 2 + x)
            pygame.draw.line(screen, (250, 232, 190), (px, py), (px + length, py), 1)

    def _draw_lake(self, screen: pygame.Surface, time_ms: int) -> None:
        if not self.water_points:
            return
        # Ronds dans l'eau : un nouveau toutes les 0,7 s, à un endroit différent
        for k in range(3):
            index, local = divmod(time_ms + k * 700, 2100)
            x, y = self.water_points[(index * 3 + k) % len(self.water_points)]
            q = local / 2100
            radius = int(4 + 22 * q)
            color = (int(210 - 60 * q), int(240 - 40 * q), 255)
            pygame.draw.ellipse(screen, color, (x - radius, y - radius // 2, radius * 2, radius), 1)
        # Poisson qui saute toutes les 5 secondes
        index, local = divmod(time_ms, 5000)
        if local < 900:
            rng = random.Random(index)
            x0, y0 = self.water_points[rng.randrange(len(self.water_points))]
            q = local / 900
            direction = rng.choice((-1, 1))
            x = x0 + direction * (q - 0.5) * 40
            size = 1 + 0.8 * math.sin(q * math.pi)          # plus gros au sommet du saut
            fish = pygame.Surface((24, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(fish, (240, 130, 40), (4, 2, 16, 8))
            pygame.draw.polygon(fish, (220, 100, 30), [(4, 6), (0, 1), (0, 11)])
            fish = pygame.transform.rotozoom(fish if direction > 0 else pygame.transform.flip(fish, True, False),
                                             0, size)
            screen.blit(fish, fish.get_rect(center=(x, y0)))
            if q > 0.85:   # éclaboussure à la retombée
                pygame.draw.circle(screen, (230, 250, 255), (int(x), y0), int(6 + 20 * (q - 0.85)), 2)

    def _draw_dust_devil(self, screen: pygame.Surface, t: float) -> None:
        """Petite tornade de sable qui se promène (trajet en forme de huit) sur tout le terrain."""
        cx = self.width / 2 + (self.width / 2 - 80) * math.sin(t * 0.13)
        cy = self.height / 2 + (self.height / 2 - 80) * math.sin(t * 0.26)
        layer = pygame.Surface((90, 90), pygame.SRCALPHA)
        for angle, height in self.devil_grains:
            a = angle + t * (6 - 3 * height)               # tourne plus vite en bas qu'en haut
            r = 6 + 30 * height
            x = 45 + r * math.cos(a)
            y = 45 + r * math.sin(a) * 0.8
            alpha = int(170 * (1 - height * 0.6))
            pygame.draw.circle(layer, (200, 165, 110, alpha), (x, y), 2 if height < 0.5 else 3)
        pygame.draw.circle(layer, (180, 145, 95, 90), (45, 45), 9)
        screen.blit(layer, (cx - 45, cy - 45))

    def _draw_tumbleweed(self, screen: pygame.Surface, time_ms: int) -> None:
        """Une boule de broussailles traverse l'écran en rebondissant, toutes les 8 secondes."""
        index, local = divmod(time_ms, 8000)
        if local > 6000:
            return
        rng = random.Random(index * 13)
        q = local / 6000
        x = -40 + q * (self.width + 80)
        y_base = rng.uniform(60, self.height - 60)
        bounce = abs(math.sin(q * 18)) * 14             # petits rebonds
        shadow = pygame.Surface((36, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
        screen.blit(shadow, (x - 18, y_base + 8))
        weed = pygame.transform.rotate(self.tumbleweed, -q * 1400)
        screen.blit(weed, weed.get_rect(center=(x, y_base - bounce)))

    # ================= En hauteur =================

    def draw_sky(self, screen: pygame.Surface, time_ms: int) -> None:
        t = time_ms / 1000
        self.draw_palms(screen, t)
        self._draw_vultures(screen, t)
        self._draw_balloon(screen, time_ms)

    def draw_palms(self, screen: pygame.Surface, t: float) -> None:
        """Feuilles de palmier qui se balancent au vent (les ombres sont dessinées par TileRenderer)."""
        for cx, cy, start in self.palms:
            sway = 0.12 * math.sin(t * 1.6 + cx * 0.05)
            for k in range(7):
                a = start + k * 2 * math.pi / 7 + sway
                length = 22 + 2 * math.sin(t * 2.2 + k + cy)
                tip = (cx + length * math.cos(a), cy + length * math.sin(a))
                side = (math.cos(a + math.pi / 2) * 5, math.sin(a + math.pi / 2) * 5)
                mid = (cx + length / 2 * math.cos(a), cy + length / 2 * math.sin(a))
                pygame.draw.polygon(screen, (40, 120, 45), [(cx, cy), (mid[0] + side[0], mid[1] + side[1]),
                                                            tip, (mid[0] - side[0], mid[1] - side[1])])
                pygame.draw.line(screen, (110, 180, 80), (cx, cy), tip, 1)
            pygame.draw.circle(screen, (110, 75, 40), (cx, cy), 4)

    def _draw_vultures(self, screen: pygame.Surface, t: float) -> None:
        """Deux vautours qui planent en cercle, avec leur ombre au sol."""
        for k, (ox, oy) in enumerate(((self.width * 0.3, self.height * 0.35), (self.width * 0.7, self.height * 0.65))):
            a = t * 0.45 + k * math.pi
            x = ox + 130 * math.cos(a)
            y = oy + 90 * math.sin(a)
            heading = math.degrees(-(a + math.pi / 2))      # tangent au cercle
            flap = 0.75 + 0.25 * math.sin(t * 7 + k)        # battement d'ailes
            bird = pygame.Surface((60, 40), pygame.SRCALPHA)
            wing = 26 * flap
            for s in (-1, 1):
                pygame.draw.polygon(bird, (60, 45, 35), [(34, 20), (24, 20 + s * wing * 0.75), (16, 20 + s * wing * 0.8),
                                                         (26, 20)])
            pygame.draw.ellipse(bird, (75, 55, 40), (20, 16, 22, 8))       # corps
            pygame.draw.circle(bird, (200, 150, 140), (44, 20), 3)         # tête
            bird = pygame.transform.rotate(bird, heading)
            shadow = bird.copy()
            shadow.fill((0, 0, 0, 60), special_flags=pygame.BLEND_RGBA_MIN)
            screen.blit(shadow, shadow.get_rect(center=(x + 50, y + 70)))
            screen.blit(bird, bird.get_rect(center=(x, y)))

    def _draw_balloon(self, screen: pygame.Surface, time_ms: int) -> None:
        """Une montgolfière traverse le ciel en diagonale toutes les 20 secondes."""
        index, local = divmod(time_ms + 9000, 20000)
        if local > 11000:
            return
        rng = random.Random(index * 5 + 2)
        q = local / 11000
        x = -60 + q * (self.width + 120)
        y = rng.uniform(140, self.height - 140) + 60 * math.sin(q * math.pi)
        shadow = pygame.Surface((96, 96), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0, 0, 0, 60), (48, 48), 40)
        screen.blit(shadow, (x - 48 + 90, y - 48 + 110))
        screen.blit(self.balloon, (x - 48, y - 48))
