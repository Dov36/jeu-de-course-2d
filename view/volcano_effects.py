# Kart-Engine v2.3
import math
import random
import pygame
from constants import TILE_SIZE
from model.circuit import Circuit
from view.theme_effects import ThemeEffects

S = TILE_SIZE


def volcano_positions(circuit: Circuit) -> list:
    """Centre (en pixels) de chaque grande zone de cendre : on y dessine un volcan.

    Utilisée par TileRenderer (le cône, fixe) et par VolcanoEffects (fumée et boules de feu).
    """
    seen = set()
    centers = []
    for row in circuit.grid:
        for tile in row:
            if tile.terrain != "grass" or (tile.col, tile.row) in seen:
                continue
            zone, to_visit = [], [(tile.col, tile.row)]   # toutes les cases de cendre reliées
            while to_visit:
                col, r = to_visit.pop()
                if (col, r) in seen:
                    continue
                seen.add((col, r))
                zone.append((col, r))
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    neighbour = circuit.get_tile(col + dc, r + dr)
                    if neighbour is not None and neighbour.terrain == "grass":
                        to_visit.append((col + dc, r + dr))
            if len(zone) >= 12:
                x = sum(c for c, _ in zone) / len(zone) * S + S / 2
                y = sum(r for _, r in zone) / len(zone) * S + S / 2
                centers.append((int(x), int(y)))
    return centers


class VolcanoEffects(ThemeEffects):
    """Animations du thème volcan.

    Sous la piste : bulles qui éclatent dans la lave.
    Au sol : braises qui montent, cendres qui tombent.
    En hauteur : fumée des volcans, boules de feu projetées avec leur ombre.
    """

    def __init__(self, circuit: Circuit):
        rng = random.Random(666)
        self.width = circuit.pixel_width()
        self.height = circuit.pixel_height()
        self.volcanoes = volcano_positions(circuit)
        # Cases de lave où faire éclater des bulles
        self.lava_points = [(t.col * S + S // 2, t.row * S + S // 2)
                            for row in circuit.grid for t in row if t.terrain == "void"]
        self.embers = [(rng.uniform(0, self.width), rng.uniform(0, self.height),
                        rng.uniform(15, 40), rng.uniform(0, 6)) for _ in range(55)]
        self.ash = [(rng.uniform(0, self.width), rng.uniform(0, self.height),
                     rng.uniform(8, 20), rng.uniform(0, 6)) for _ in range(35)]

    # ================= Sous la piste =================

    def draw_background(self, screen: pygame.Surface, time_ms: int) -> None:
        """Bulles de lave : elles gonflent puis éclatent, à des endroits différents."""
        if not self.lava_points:
            return
        for k in range(10):
            period = 1400 + k * 170
            index, local = divmod(time_ms + k * 397, period)
            q = local / period
            x, y = self.lava_points[(index * 7 + k * 13) % len(self.lava_points)]
            x += (k * 37) % 40 - 20
            y += (k * 53) % 40 - 20
            if q < 0.75:   # la bulle gonfle
                r = int(3 + 9 * q / 0.75)
                pygame.draw.circle(screen, (255, 170, 40), (x, y), r)
                pygame.draw.circle(screen, (255, 230, 120), (x - r // 3, y - r // 3), max(1, r // 3))
            else:          # elle éclate : un anneau qui s'élargit
                s = (q - 0.75) / 0.25
                pygame.draw.circle(screen, (255, 200, 80), (x, y), int(12 + 14 * s), 2)

    # ================= Au sol =================

    def draw_ground(self, screen: pygame.Surface, time_ms: int) -> None:
        t = time_ms / 1000
        for x, y, speed, phase in self.embers:   # braises qui montent en vacillant
            px = (x + 8 * math.sin(t * 2 + phase)) % self.width
            py = (y - speed * t) % self.height
            light = (math.sin(t * 6 + phase) + 1) / 2
            pygame.draw.circle(screen, (255, int(120 + 100 * light), 30), (int(px), int(py)), 2)
        for x, y, speed, phase in self.ash:      # flocons de cendre qui tombent
            px = (x + 12 * math.sin(t + phase)) % self.width
            py = (y + speed * t) % self.height
            pygame.draw.circle(screen, (150, 145, 140), (int(px), int(py)), 2)

    # ================= En hauteur =================

    def sound_cues(self, previous_ms: int, time_ms: int) -> list[str]:
        """Un « pfoom » chaque fois qu'un volcan crache une boule de feu."""
        for k in range(len(self.volcanoes)):
            if (previous_ms + k * 2300) // 4000 != (time_ms + k * 2300) // 4000:
                return ["lava_bomb"]
        return []

    def draw_sky(self, screen: pygame.Surface, time_ms: int) -> None:
        t = time_ms / 1000
        for k, (vx, vy) in enumerate(self.volcanoes):
            self._draw_smoke(screen, vx, vy, t + k * 1.7)
            self._draw_lava_bomb(screen, vx, vy, time_ms + k * 2300, k)

    def _draw_smoke(self, screen: pygame.Surface, vx: int, vy: int, t: float) -> None:
        """Panache de fumée : des bouffées grises qui montent, grossissent et s'effacent."""
        layer = pygame.Surface((220, 260), pygame.SRCALPHA)
        for k in range(8):
            q = ((t * 0.35) + k / 8) % 1          # avancement de chaque bouffée (0 -> 1)
            x = 110 + 30 * q + 10 * math.sin(t * 1.3 + k)
            y = 230 - 210 * q
            r = int(10 + 34 * q)
            alpha = int(150 * (1 - q))
            gray = int(90 - 30 * q)
            pygame.draw.circle(layer, (gray, gray, gray + 5, alpha), (x, y), r)
        screen.blit(layer, (vx - 110, vy - 230))

    def _draw_lava_bomb(self, screen: pygame.Surface, vx: int, vy: int, time_ms: int, k: int) -> None:
        """Boule de feu projetée par le volcan toutes les 4 secondes : elle monte puis retombe.
        Son ombre au sol montre où elle va atterrir."""
        index, local = divmod(time_ms, 4000)
        if local > 1600:
            return
        rng = random.Random(index * 11 + k)
        q = local / 1600
        angle = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(90, 200)
        gx = vx + dist * math.cos(angle) * q       # position au sol
        gy = vy + dist * math.sin(angle) * q
        height = 140 * 4 * q * (1 - q)             # parabole : 0 -> 140 -> 0
        shadow_r = int(5 + 6 * (1 - height / 140))
        pygame.draw.ellipse(screen, (20, 10, 10), (gx - shadow_r, gy - shadow_r // 2, shadow_r * 2, shadow_r))
        bx, by = gx, gy - height
        for i in range(4):   # petite traînée de feu
            tq = max(0.0, q - i * 0.03)
            th = 140 * 4 * tq * (1 - tq)
            tx = vx + dist * math.cos(angle) * tq
            ty = vy + dist * math.sin(angle) * tq - th
            pygame.draw.circle(screen, (255, 120 + i * 30, 20), (int(tx), int(ty)), 7 - i)
        pygame.draw.circle(screen, (255, 230, 120), (int(bx), int(by)), 4)
        if q > 0.92:   # éclaboussure de lave à l'impact
            pygame.draw.circle(screen, (255, 150, 40), (int(gx), int(gy)), int(8 + 100 * (q - 0.92)), 2)
