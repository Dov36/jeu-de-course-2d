# Kart-Engine v2.3
import math
import random
import pygame
from constants import TILE_SIZE
from model.circuit import Circuit
from view.desert_effects import palm_positions
from view.volcano_effects import volcano_positions

S = TILE_SIZE

# Terrains qui font partie de la piste : ils sont arrondis et bordés de vibreurs
TRACK_TERRAINS = ("road", "ice", "dirt")

WHITE = (240, 240, 255)

# Couleurs propres à chaque thème
THEMES = {
    "space": {
        "road": (30, 32, 42),
        "dirt": (88, 44, 22),
        "ice_light": (130, 200, 240),
        "ice_dark": (60, 125, 185),
        "curb": ((0, 230, 255), WHITE),     # vibreurs : deux couleurs en alternance
        "glow": (0, 150, 190),              # halo autour de la piste (None = pas de halo)
        "boost": (255, 0, 200),
        "boost_pad": (60, 0, 50),
        "checkpoint": (120, 255, 90),
    },
    "desert": {
        "road": (82, 78, 74),
        "dirt": (226, 190, 130),
        "ice_light": (245, 244, 236),
        "ice_dark": (222, 220, 208),
        "curb": ((215, 40, 35), WHITE),
        "glow": None,
        "boost": (255, 150, 0),
        "boost_pad": (70, 50, 30),
        "checkpoint": (60, 200, 255),
    },
    "volcano": {
        "road": (46, 43, 47),
        "dirt": (112, 58, 42),
        "ice_light": (70, 55, 100),
        "ice_dark": (22, 18, 34),
        "curb": ((255, 120, 0), (35, 30, 30)),
        "glow": (230, 80, 10),
        "boost": (255, 220, 0),
        "boost_pad": (70, 20, 10),
        "checkpoint": (60, 200, 255),
    },
}


def chevron_points(cx: float, cy: float, angle: float, offset: float = 0) -> list:
    """Points d'un chevron (>) centré en (cx, cy), tourné vers angle (en degrés, 0 = droite),
    éventuellement décalé de offset pixels dans cette direction."""
    rad = math.radians(angle)
    ux, uy = math.cos(rad), -math.sin(rad)      # direction (l'axe y de l'écran descend)
    vx, vy = -uy, ux                            # perpendiculaire
    shape = [(-5, -12), (5, 0), (-5, 12)]       # chevron qui pointe vers la droite
    return [(cx + (a + offset) * ux + b * vx, cy + (a + offset) * uy + b * vy) for a, b in shape]


def boost_pad(rect: pygame.Rect, angle: float) -> pygame.Rect:
    """Rectangle du panneau de boost, allongé dans le sens des flèches."""
    vertical = round(angle) % 180 == 90
    return rect.inflate(-16, -10) if vertical else rect.inflate(-10, -16)


def blur(surface: pygame.Surface, factor: int) -> pygame.Surface:
    """Flou simple : on réduit l'image puis on l'agrandit (pygame n'a pas de fonction de flou)."""
    w, h = surface.get_size()
    small = pygame.transform.smoothscale(surface, (max(1, w // factor), max(1, h // factor)))
    return pygame.transform.smoothscale(small, (w, h))


def corner_region(kx: float, ky: float, dx: int, dy: int, radius: float) -> list:
    """Points du « coin » à arrondir : le sommet (kx, ky) puis un quart de cercle.

    (dx, dy) indique vers où pointe le coin (ex : (-1, -1) = coin en haut à gauche).
    Le quart de cercle a pour centre (kx - dx*radius, ky - dy*radius).
    """
    return [(kx, ky)] + corner_arc(kx, ky, dx, dy, radius)


def corner_arc(kx: float, ky: float, dx: int, dy: int, radius: float, steps: int = 10) -> list:
    """Quart de cercle qui arrondit le coin (kx, ky), d'un côté du coin à l'autre."""
    cx, cy = kx - dx * radius, ky - dy * radius
    a_start = math.atan2(dy, 0)
    a_end = math.atan2(0, dx)
    diff = (a_end - a_start + math.pi) % (2 * math.pi) - math.pi   # plus court chemin
    return [(cx + radius * math.cos(a_start + diff * i / steps),
             cy + radius * math.sin(a_start + diff * i / steps)) for i in range(steps + 1)]


class TileRenderer:
    """Dessine les circuits (vue), dans le thème de chaque circuit (espace ou désert).

    Un circuit ne change pas pendant la course : on le dessine une seule fois
    sur une grande image (le fond), puis on réutilise cette image à chaque frame.
    Les virages sont arrondis uniquement à l'affichage : le modèle reste une grille de cases.
    """

    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 22, bold=True)
        self.rng = random.Random(42)   # graine fixe : le décor est identique à chaque lancement
        self.textures: dict[tuple, pygame.Surface] = {}
        self._cache: dict[str, pygame.Surface] = {}   # nom du circuit -> image déjà dessinée
        self._sparkles: dict[str, list] = {}          # nom du circuit -> reflets animés sur l'eau
        self._previews: dict[str, pygame.Surface] = {}  # nom du circuit -> image complète (menu)

    def get_layers(self, circuit: Circuit) -> tuple:
        """Renvoie les deux calques du circuit, dessinés une seule fois puis gardés :
        (fond, piste). Dans l'espace, le calque « piste » est transparent sur le vide,
        ce qui permet d'animer l'espace entre les deux (voir view/space_effects.py).
        Dans le désert, tout est déjà dans le calque « piste » et le fond vaut None."""
        if circuit.name not in self._cache:
            self._cache[circuit.name] = self._draw_circuit(circuit)
        return self._cache[circuit.name]

    def get_background(self, circuit: Circuit) -> pygame.Surface:
        """Renvoie une seule image du circuit complet (sert pour l'aperçu dans le menu)."""
        if circuit.name not in self._previews:
            back, front = self.get_layers(circuit)
            image = pygame.Surface(front.get_size())
            if back is not None:
                image.blit(back, (0, 0))
            image.blit(front, (0, 0))
            self._previews[circuit.name] = image
        return self._previews[circuit.name]

    # ================= Textures =================

    def texture(self, theme: str, name: str) -> pygame.Surface:
        """Renvoie la texture d'une case (fabriquée une seule fois, puis gardée)."""
        key = (theme, name)
        if key not in self.textures:
            makers = {
                "road": self._make_road, "dirt": self._make_dirt,
                "ice": self._make_ice, "grass": self._make_offtrack,
            }
            self.textures[key] = makers[name](theme)
        return self.textures[key]

    def _make_noise(self, base: tuple, amount: int) -> pygame.Surface:
        """Case unie avec un léger grain, pour un aspect plus réaliste."""
        tex = pygame.Surface((S, S))
        for x in range(S):
            for y in range(S):
                d = self.rng.randint(-amount, amount)
                tex.set_at((x, y), tuple(max(0, min(255, c + d)) for c in base))
        return tex

    def _make_road(self, theme: str) -> pygame.Surface:
        return self._make_noise(THEMES[theme]["road"], 7)

    def _make_dirt(self, theme: str) -> pygame.Surface:
        base = THEMES[theme]["dirt"]
        if theme == "desert":   # sable avec des ondulations
            tex = self._make_noise(base, 8)
            for k in range(5):
                y = 8 + k * 12
                points = [(x, y + 3 * math.sin(x / 9 + k)) for x in range(0, S + 1, 4)]
                pygame.draw.lines(tex, (200, 162, 105), False, points, 2)
            return tex
        if theme == "volcano":   # gravier volcanique : pierre ponce rougeâtre et cailloux sombres
            tex = self._make_noise(base, 18)
            for _ in range(22):
                x, y = self.rng.randrange(3, S - 3), self.rng.randrange(3, S - 3)
                pygame.draw.circle(tex, self.rng.choice([(60, 35, 30), (150, 85, 60), (40, 30, 30)]),
                                   (x, y), self.rng.randint(1, 3))
            return tex
        tex = self._make_noise(base, 14)   # débris
        for _ in range(14):
            x, y = self.rng.randrange(4, S - 4), self.rng.randrange(4, S - 4)
            r = self.rng.randint(2, 4)
            pygame.draw.circle(tex, (60, 30, 16), (x, y), r)
            pygame.draw.circle(tex, (130, 75, 40), (x - 1, y - 1), max(1, r - 2))
        return tex

    def _make_ice(self, theme: str) -> pygame.Surface:
        light, dark = THEMES[theme]["ice_light"], THEMES[theme]["ice_dark"]
        tex = pygame.Surface((S, S))
        for y in range(S):   # dégradé
            t = y / S
            pygame.draw.line(tex, tuple(int(a + (b - a) * t) for a, b in zip(light, dark)), (0, y), (S, y))
        crack = {"space": (200, 235, 255), "desert": (190, 186, 172), "volcano": (150, 110, 220)}[theme]
        for _ in range(4 if theme == "desert" else 3):   # fissures (glace, obsidienne) / croûte de sel
            x, y = self.rng.randrange(S), self.rng.randrange(S)
            points = [(x, y)]
            for _ in range(4):
                x += self.rng.randint(-12, 12)
                y += self.rng.randint(-12, 12)
                points.append((x, y))
            pygame.draw.lines(tex, crack, False, points, 1)
        shine = pygame.Surface((S, S), pygame.SRCALPHA)
        pygame.draw.line(shine, (255, 255, 255, 70), (8, S), (40, 0), 6)
        tex.blit(shine, (0, 0))
        return tex

    def _make_offtrack(self, theme: str) -> pygame.Surface:
        if theme == "volcano":  # cendre grise, avec des fissures qui rougeoient
            tex = self._make_noise((62, 58, 56), 9)
            for _ in range(2):
                x, y = self.rng.randrange(S), self.rng.randrange(S)
                points = [(x, y)]
                for _ in range(5):
                    x += self.rng.randint(-12, 12)
                    y += self.rng.randint(-12, 12)
                    points.append((x, y))
                pygame.draw.lines(tex, (40, 30, 28), False, points, 3)
                pygame.draw.lines(tex, (190, 60, 20), False, points, 1)
            return tex
        if theme == "desert":   # herbe de l'oasis
            tex = self._make_noise((92, 146, 66), 10)
            for _ in range(30):   # touffes d'herbe
                x, y = self.rng.randrange(S), self.rng.randrange(S)
                pygame.draw.line(tex, (62, 112, 44), (x, y), (x + self.rng.randint(-3, 3), y - 4), 2)
            return tex
        # Espace : plaque de coque de vaisseau, biseautée, avec rivets et grille d'aération
        tex = self._make_noise((46, 49, 60), 4)
        pygame.draw.line(tex, (70, 74, 88), (1, 1), (S - 2, 1), 2)
        pygame.draw.line(tex, (70, 74, 88), (1, 1), (1, S - 2), 2)
        pygame.draw.line(tex, (24, 26, 32), (1, S - 2), (S - 2, S - 2), 2)
        pygame.draw.line(tex, (24, 26, 32), (S - 2, 1), (S - 2, S - 2), 2)
        for rx, ry in ((7, 7), (S - 8, 7), (7, S - 8), (S - 8, S - 8)):
            pygame.draw.circle(tex, (28, 30, 36), (rx + 1, ry + 1), 3)
            pygame.draw.circle(tex, (95, 100, 115), (rx, ry), 2)
        grille = pygame.Rect(16, 18, S - 32, S - 36)
        pygame.draw.rect(tex, (22, 24, 30), grille, border_radius=3)
        for gy in range(grille.y + 4, grille.bottom - 2, 5):
            pygame.draw.line(tex, (60, 64, 78), (grille.x + 4, gy), (grille.right - 5, gy), 2)
        return tex

    # ================= Circuit complet =================

    def _draw_circuit(self, circuit: Circuit) -> tuple:
        theme = circuit.theme
        colors = THEMES[theme]
        size = (circuit.pixel_width(), circuit.pixel_height())

        def is_track(col: int, row: int) -> bool:
            tile = circuit.get_tile(col, row)
            return tile is not None and tile.terrain in TRACK_TERRAINS

        def is_grass(col: int, row: int) -> bool:
            tile = circuit.get_tile(col, row)
            return tile is not None and tile.terrain == "grass"

        # 1. Le fond. Désert : les dunes, directement sous la piste.
        #    Espace : l'espace va sur un calque à part (back) et la piste sur un calque
        #    transparent (surf), pour pouvoir animer l'espace entre les deux.
        #    Volcan : pareil que l'espace, avec la lave sur le calque du fond.
        if theme == "desert":
            back = None
            surf = pygame.Surface(size)
            self._draw_dunes(surf)
        else:
            back = pygame.Surface(size)
            if theme == "volcano":
                self._draw_lava(back)
            else:
                self._draw_space(back)
            surf = pygame.Surface(size, pygame.SRCALPHA)

        # 2. Le hors-piste. Sous les cases de piste dont un coin sera arrondi, on met aussi
        #    du hors-piste si les voisines en sont : il apparaîtra dans le coin coupé.
        for row in circuit.grid:
            for tile in row:
                c, r = tile.col, tile.row
                rect = pygame.Rect(c * S, r * S, S, S)
                if tile.terrain in ("grass", "water"):   # sous l'eau aussi : visible dans les coins arrondis
                    surf.blit(self._offtrack_tile(theme, c, r), rect)
                elif tile.terrain in TRACK_TERRAINS:
                    if any(is_grass(c + dc, r + dr) for dc in (-1, 0, 1) for dr in (-1, 0, 1)):
                        surf.blit(self._offtrack_tile(theme, c, r), rect)
        if theme == "space":
            self._draw_void_edges(surf, circuit)
        if theme == "volcano":
            self._draw_lava_edges(surf, circuit)
            for x, y in volcano_positions(circuit):
                self._draw_volcano_cone(surf, x, y)
        self._draw_water(surf, circuit, size)
        if theme == "desert":
            self._draw_palm_shadows(surf, circuit)

        # 3. La piste, dessinée sur un calque à part
        track = pygame.Surface(size, pygame.SRCALPHA)
        for row in circuit.grid:
            for tile in row:
                if tile.terrain in TRACK_TERRAINS:
                    rect = pygame.Rect(tile.col * S, tile.row * S, S, S)
                    tex = self.texture(theme, tile.terrain)
                    if tile.terrain != "ice":   # la glace n'est pas retournée : dégradé continu
                        tex = pygame.transform.flip(tex, self.rng.random() < 0.5, self.rng.random() < 0.5)
                    track.blit(tex, rect)
                    if tile.terrain == "road":
                        pygame.draw.rect(track, tuple(min(255, v + 10) for v in colors["road"]), rect, 1)
                    if tile.block is not None:
                        self._draw_block(track, rect, tile, circuit, colors)
                else:
                    # Case hors piste : on y met le terrain d'une case de piste voisine,
                    # au cas où un congé (arrondi intérieur) déborde sur cette case
                    terrain = "road"
                    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        neighbour = circuit.get_tile(tile.col + dc, tile.row + dr)
                        if neighbour is not None and neighbour.terrain in TRACK_TERRAINS:
                            terrain = neighbour.terrain
                            break
                    track.blit(self.texture(theme, terrain), (tile.col * S, tile.row * S))

        # 4. Le masque : la forme exacte de la piste, avec les virages arrondis
        mask, curves = self._build_track_mask(circuit, is_track, size)
        track.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(track, (0, 0))

        # 5. Les bordures (halo flou puis vibreurs), qui suivent les arrondis
        if colors["glow"] is not None:
            glow = pygame.Surface(size, pygame.SRCALPHA)   # halo avec transparence : il déborde sur le vide
            for line in curves:
                pygame.draw.lines(glow, (*colors["glow"], 255), False, line, 10)
            surf.blit(blur(glow, 6), (0, 0))
        for line in curves:
            self._draw_curb(surf, line, colors["curb"], 4)
        return back, surf

    def _offtrack_tile(self, theme: str, col: int, row: int) -> pygame.Surface:
        tex = self.texture(theme, "grass")
        if theme == "space" and (col + row) % 2:   # une case sur deux, grille tournée
            tex = pygame.transform.rotate(tex, 90)
        return tex

    # ================= Arrondis =================

    def _build_track_mask(self, circuit: Circuit, is_track, size: tuple) -> tuple:
        """Construit la forme de la piste (masque blanc sur transparent) et ses bords.

        - Coin extérieur d'un virage : on coupe un quart de cercle (grand rayon si possible).
        - Coin intérieur : on ajoute un petit « congé » dans la case voisine pour adoucir.
        - Dans un escalier de cases (piste en diagonale), coins et congés sont coupés en ligne
          droite à 45° : bout à bout, ils forment un bord diagonal bien lisse.
        Renvoie (masque, liste de lignes de bord) ; les lignes servent à dessiner les vibreurs.
        """
        mask = pygame.Surface(size, pygame.SRCALPHA)
        clear, full = (0, 0, 0, 0), (255, 255, 255, 255)
        fillet_r = S // 2
        corners = ((-1, -1), (1, -1), (-1, 1), (1, 1))
        curves = []

        def outer(c, r, dx, dy):   # coin extérieur : les deux voisines de ce côté sont hors piste
            return is_track(c, r) and not is_track(c + dx, r) and not is_track(c, r + dy)

        def fillet(c, r, dx, dy):  # coin intérieur : case hors piste entourée de piste de ce côté
            return (not is_track(c, r) and is_track(c + dx, r) and is_track(c, r + dy)
                    and is_track(c + dx, r + dy))

        def diagonal_outer(c, r, dx, dy):   # coin extérieur qui touche un congé : marche d'escalier
            return outer(c, r, dx, dy) and (fillet(c + dx, r, -dx, -dy) or fillet(c, r + dy, -dx, -dy))

        def diagonal_fillet(c, r, dx, dy):  # congé qui touche un coin extérieur : marche d'escalier
            return fillet(c, r, dx, dy) and (outer(c + dx, r, -dx, -dy) or outer(c, r + dy, -dx, -dy))

        def chamfer(kx, ky, dx, dy):        # coupe droite à 45°, sur une demi-case
            return [(kx - dx * fillet_r, ky), (kx, ky - dy * fillet_r)]

        def radius(c, r):          # un seul coin arrondi dans la case : on peut prendre toute la case
            n = sum(outer(c, r, dx, dy) for dx, dy in corners)
            return S if n == 1 else S // 2

        def corner_point(c, r, dx, dy):
            return (c * S + (S if dx > 0 else 0), r * S + (S if dy > 0 else 0))

        for r in range(circuit.rows):
            for c in range(circuit.cols):
                if is_track(c, r):
                    pygame.draw.rect(mask, full, (c * S, r * S, S, S))
        for r in range(circuit.rows):
            for c in range(circuit.cols):
                for dx, dy in corners:
                    kx, ky = corner_point(c, r, dx, dy)
                    if diagonal_outer(c, r, dx, dy):
                        line = chamfer(kx, ky, dx, dy)
                        pygame.draw.polygon(mask, clear, [(kx, ky)] + line)
                        curves.append(line)
                    elif outer(c, r, dx, dy):
                        rad = radius(c, r)
                        pygame.draw.polygon(mask, clear, corner_region(kx, ky, dx, dy, rad))
                        curves.append(corner_arc(kx, ky, dx, dy, rad))
                    elif diagonal_fillet(c, r, dx, dy):
                        line = chamfer(kx, ky, dx, dy)
                        pygame.draw.polygon(mask, full, [(kx, ky)] + line)
                        curves.append(line)
                    elif fillet(c, r, dx, dy):
                        pygame.draw.polygon(mask, full, corner_region(kx, ky, dx, dy, fillet_r))
                        curves.append(corner_arc(kx, ky, dx, dy, fillet_r))

        # Bords droits : côtés de piste qui touchent du hors-piste, raccourcis là où il y a un arrondi
        sides = {(0, -1): ((-1, -1), (1, -1)), (0, 1): ((-1, 1), (1, 1)),
                 (-1, 0): ((-1, -1), (-1, 1)), (1, 0): ((1, -1), (1, 1))}
        for r in range(circuit.rows):
            for c in range(circuit.cols):
                if not is_track(c, r):
                    continue
                for (sx, sy), ends in sides.items():
                    if is_track(c + sx, r + sy):
                        continue
                    points = []
                    for dx, dy in ends:
                        kx, ky = corner_point(c, r, dx, dy)
                        trim = 0
                        if diagonal_outer(c, r, dx, dy):
                            trim = fillet_r
                        elif outer(c, r, dx, dy):
                            trim = radius(c, r)
                        else:
                            # coin du voisin d'en face, vu depuis ce voisin
                            ndx, ndy = (dx, -dy) if sy != 0 else (-dx, dy)
                            if fillet(c + sx, r + sy, ndx, ndy):
                                trim = fillet_r
                        # on recule le point vers le milieu du côté
                        ux, uy = (-dx, 0) if sy != 0 else (0, -dy)
                        points.append((kx + ux * trim, ky + uy * trim))
                    (ax, ay), (bx, by) = points
                    if (ax - bx) ** 2 + (ay - by) ** 2 > 1:
                        curves.append(points)
        return mask, curves

    def _draw_curb(self, surf: pygame.Surface, points: list, colors: tuple, width: int) -> None:
        """Vibreur le long d'une ligne (droite ou courbe) : segments de 8 pixels en alternance."""
        segment = 8
        travelled = 0.0
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            length = math.hypot(bx - ax, by - ay)
            pos = 0.0
            while pos < length:
                step = min(segment - (travelled % segment), length - pos)
                t0, t1 = pos / length, (pos + step) / length
                color = colors[int(travelled // segment) % 2]
                pygame.draw.line(surf, color, (ax + (bx - ax) * t0, ay + (by - ay) * t0),
                                 (ax + (bx - ax) * t1, ay + (by - ay) * t1), width)
                pos += step
                travelled += step
        for x, y in (points[0], points[-1]):   # petits ronds aux extrémités : raccords propres
            pygame.draw.circle(surf, colors[0], (x, y), width // 2)

    # ================= Fonds et décors =================

    def _draw_space(self, surf: pygame.Surface) -> None:
        w, h = surf.get_size()
        space = (4, 4, 14)
        nebula = pygame.Surface((w // 8, h // 8))
        nebula.fill(space)
        for _ in range(7):   # nuages colorés : cercles concentriques de plus en plus clairs
            color = self.rng.choice([(45, 12, 70), (12, 30, 70), (55, 12, 45)])
            pos = (self.rng.randrange(w // 8), self.rng.randrange(h // 8))
            rad = self.rng.randint(8, 20)
            for k in range(rad, 0, -2):
                t = 1 - k / rad
                pygame.draw.circle(nebula, tuple(int(s + (c - s) * t) for s, c in zip(space, color)), pos, k)
        nebula = pygame.transform.smoothscale(nebula, (w, h))
        for _ in range(3):
            nebula = blur(nebula, 8)
        surf.blit(nebula, (0, 0))
        for _ in range(250):   # étoiles
            x, y = self.rng.randrange(w), self.rng.randrange(h)
            b = self.rng.randint(80, 255)
            surf.set_at((x, y), self.rng.choice([(b, b, b), (b, b, 255), (255, b, b)]))

    def _draw_lava(self, surf: pygame.Surface) -> None:
        """Le « vide » du volcan : une mer de lave, croûte sombre craquelée de fissures brillantes."""
        w, h = surf.get_size()
        lava = pygame.Surface((w // 4, h // 4))
        lava.fill((235, 100, 15))
        for _ in range(500):   # plaques de croûte sombre : la lave brille entre elles
            pygame.draw.circle(lava, self.rng.choice([(90, 28, 12), (120, 40, 15), (70, 22, 10)]),
                               (self.rng.randrange(w // 4), self.rng.randrange(h // 4)), self.rng.randint(3, 7))
        lava = pygame.transform.smoothscale(lava, (w, h))
        for _ in range(2):
            lava = blur(lava, 3)
        surf.blit(lava, (0, 0))
        for _ in range(70):   # fissures incandescentes
            x, y = self.rng.randrange(w), self.rng.randrange(h)
            points = [(x, y)]
            for _ in range(6):
                x += self.rng.randint(-18, 18)
                y += self.rng.randint(-18, 18)
                points.append((x, y))
            pygame.draw.lines(surf, (255, 150, 40), False, points, 3)
            pygame.draw.lines(surf, (255, 225, 120), False, points, 1)
        for _ in range(30):   # points très chauds, presque jaunes
            pygame.draw.circle(surf, (255, 220, 110), (self.rng.randrange(w), self.rng.randrange(h)),
                               self.rng.randint(2, 4))

    def _draw_lava_edges(self, surf: pygame.Surface, circuit: Circuit) -> None:
        """Volcan : bord rougeoyant de la cendre, là où commence la lave."""
        for row in circuit.grid:
            for tile in row:
                if tile.terrain != "grass":
                    continue
                x, y = tile.col * S, tile.row * S
                s = S - 1
                sides = {(0, -1): ((x, y), (x + s, y)), (0, 1): ((x, y + s), (x + s, y + s)),
                         (-1, 0): ((x, y), (x, y + s)), (1, 0): ((x + s, y), (x + s, y + s))}
                for (dc, dr), (start, end) in sides.items():
                    neighbour = circuit.get_tile(tile.col + dc, tile.row + dr)
                    if neighbour is None or neighbour.terrain == "void":
                        pygame.draw.line(surf, (255, 110, 20), start, end, 4)
                        pygame.draw.line(surf, (255, 200, 80), start, end, 1)

    def _draw_volcano_cone(self, surf: pygame.Surface, x: int, y: int) -> None:
        """Un volcan vu de dessus : pentes en anneaux, cratère, lave au fond et coulées."""
        shadow = pygame.Surface((220, 220), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0, 0, 0, 90), (110, 110), 92)
        surf.blit(blur(shadow, 4), (x - 100, y - 100))
        for radius, color in ((86, (74, 64, 60)), (68, (92, 80, 72)), (48, (80, 68, 62)), (30, (50, 40, 38))):
            pygame.draw.circle(surf, color, (x, y), radius)
        for k in range(5):   # coulées de lave sur les pentes
            a = k * 2 * math.pi / 5 + 0.4
            points = [(x + r * math.cos(a + 0.15 * math.sin(r / 9)), y + r * math.sin(a + 0.15 * math.sin(r / 9)))
                      for r in range(22, 80, 4)]
            pygame.draw.lines(surf, (200, 70, 15), False, points, 4)
            pygame.draw.lines(surf, (255, 170, 50), False, points, 1)
        pygame.draw.circle(surf, (255, 110, 20), (x, y), 20)       # lave dans le cratère
        pygame.draw.circle(surf, (255, 200, 80), (x - 4, y - 4), 8)

    def _draw_dunes(self, surf: pygame.Surface) -> None:
        """Le « vide » du désert : des dunes de sable à perte de vue."""
        w, h = surf.get_size()
        dunes = pygame.Surface((w // 16, h // 16))
        dunes.fill((234, 200, 140))
        for _ in range(40):   # creux à l'ombre et crêtes au soleil
            color = self.rng.choice([(214, 176, 116), (246, 218, 165), (224, 188, 128)])
            pos = (self.rng.randrange(w // 16), self.rng.randrange(h // 16))
            pygame.draw.ellipse(dunes, color, (*pos, self.rng.randint(4, 10), self.rng.randint(2, 5)))
        dunes = pygame.transform.smoothscale(dunes, (w, h))
        for _ in range(3):
            dunes = blur(dunes, 6)
        surf.blit(dunes, (0, 0))
        for _ in range(140):   # ondulations laissées par le vent
            x, y = self.rng.randrange(w), self.rng.randrange(h)
            length = self.rng.randint(20, 60)
            points = [(x + i, y + 2 * math.sin(i / 6)) for i in range(0, length, 3)]
            pygame.draw.lines(surf, (210, 172, 112), False, points, 1)
        for _ in range(25):    # petits cailloux et buissons secs
            x, y = self.rng.randrange(w), self.rng.randrange(h)
            if self.rng.random() < 0.5:
                pygame.draw.circle(surf, (150, 120, 85), (x, y), self.rng.randint(2, 4))
            else:
                for _ in range(5):
                    pygame.draw.line(surf, (130, 110, 60), (x, y),
                                     (x + self.rng.randint(-5, 5), y + self.rng.randint(-5, 5)), 1)

    def _draw_void_edges(self, surf: pygame.Surface, circuit: Circuit) -> None:
        """Espace : bande de danger au bord du hors-piste, là où commence le vide."""
        band = 8
        for row in circuit.grid:
            for tile in row:
                if tile.terrain != "grass":
                    continue
                x, y = tile.col * S, tile.row * S
                bands = {(0, -1): pygame.Rect(x, y, S, band), (0, 1): pygame.Rect(x, y + S - band, S, band),
                         (-1, 0): pygame.Rect(x, y, band, S), (1, 0): pygame.Rect(x + S - band, y, band, S)}
                for (dc, dr), area in bands.items():
                    neighbour = circuit.get_tile(tile.col + dc, tile.row + dr)
                    if neighbour is None or neighbour.terrain == "void":
                        self._draw_hazard(surf, area)

    def _draw_hazard(self, surf: pygame.Surface, area: pygame.Rect) -> None:
        """Rayures diagonales jaunes et noires, en coordonnées globales pour se raccorder."""
        pygame.draw.rect(surf, (20, 20, 20), area)
        surf.set_clip(area)
        start = (area.x + area.y) // 16 * 16 - 32
        for d in range(start, area.right + area.bottom + 32, 16):
            pygame.draw.polygon(surf, (240, 190, 20),
                                [(d - area.y, area.y), (d + 8 - area.y, area.y),
                                 (d + 8 - area.bottom, area.bottom), (d - area.bottom, area.bottom)])
        surf.set_clip(None)

    def _draw_water(self, surf: pygame.Surface, circuit: Circuit, size: tuple) -> None:
        """Le lac : eau peu profonde (turquoise) sur les bords, profonde (bleu foncé) au centre,
        plage et sable mouillé autour, roseaux et nénuphars. Les reflets animés sont dessinés
        à chaque frame par draw_water_animation."""
        def is_water(col: int, row: int) -> bool:
            tile = circuit.get_tile(col, row)
            return tile is not None and tile.terrain == "water"

        if not any(tile.terrain == "water" for row in circuit.grid for tile in row):
            return
        mask, shore = self._build_track_mask(circuit, is_water, size)

        # Plage : une large bande de sable sec, puis du sable mouillé plus foncé
        for line in shore:
            pygame.draw.lines(surf, (232, 208, 160), False, line, 22)
        for line in shore:
            pygame.draw.lines(surf, (196, 170, 118), False, line, 10)
        rng = random.Random(11)
        for line in shore:   # galets sur la plage
            for (x, y) in line[::4]:
                if rng.random() < 0.35:
                    pygame.draw.circle(surf, (150, 145, 135), (x + rng.randint(-9, 9), y + rng.randint(-9, 9)), 2)

        # Eau peu profonde partout, puis eau profonde de plus en plus opaque vers le centre
        water = pygame.Surface(size, pygame.SRCALPHA)
        water.fill((70, 190, 205, 255))
        deep = pygame.Surface(size, pygame.SRCALPHA)
        deep.fill((18, 82, 140, 255))
        # Profondeur : on retire une bande près du bord, puis on floute.
        # Résultat : 0 près du bord (eau claire), 255 au centre (eau profonde).
        depth = mask.copy()
        for line in shore:
            pygame.draw.lines(depth, (0, 0, 0, 0), False, line, 70)
        for _ in range(2):
            depth = blur(depth, 16)
        deep.blit(depth, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        water.blit(deep, (0, 0))
        for _ in range(45):   # vaguelettes fixes
            x, y = rng.randrange(size[0]), rng.randrange(size[1])
            pygame.draw.arc(water, (120, 205, 230), (x, y, 16, 6), 0.3, 2.8, 2)
        water.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(water, (0, 0))

        # Liseré d'écume au bord de l'eau
        for line in shore:
            pygame.draw.lines(surf, (225, 245, 250), False, line, 2)

        # Roseaux et nénuphars près du bord (uniquement sur l'eau)
        points_in_water = []
        for _ in range(4000):
            x, y = rng.randrange(size[0]), rng.randrange(size[1])
            if mask.get_at((x, y)).a > 0 and depth.get_at((x, y)).a < 20:
                points_in_water.append((x, y))
        for (x, y) in points_in_water[:6]:   # nénuphars
            pygame.draw.circle(surf, (40, 130, 60), (x, y), 7)
            pygame.draw.polygon(surf, (70, 180, 200), [(x, y), (x + 8, y - 3), (x + 8, y + 3)])
            if rng.random() < 0.5:
                pygame.draw.circle(surf, (250, 180, 210), (x - 2, y - 1), 2)
        for (x, y) in points_in_water[6:12]:   # touffes de roseaux
            for _ in range(6):
                a = rng.uniform(0, 2 * math.pi)
                pygame.draw.line(surf, (60, 110, 40), (x, y), (x + 9 * math.cos(a), y + 9 * math.sin(a)), 2)
            pygame.draw.circle(surf, (110, 70, 40), (x, y), 2)

        # Points où scintilleront les reflets animés (dans l'eau, loin des bords)
        sparkles = []
        for _ in range(3000):
            x, y = rng.randrange(size[0]), rng.randrange(size[1])
            if depth.get_at((x, y)).a > 40 and mask.get_at((x, y)).a > 0:
                sparkles.append((x, y, rng.uniform(0, 2 * math.pi), rng.uniform(1.5, 3.0)))
            if len(sparkles) >= 40:
                break
        self._sparkles[circuit.name] = sparkles

    def draw_water_animation(self, screen: pygame.Surface, circuit: Circuit, time_ms: int) -> None:
        """Reflets du soleil sur l'eau, qui apparaissent et disparaissent (appelée à chaque frame)."""
        t = time_ms / 1000
        for x, y, phase, speed in self._sparkles.get(circuit.name, []):
            light = (math.sin(t * speed + phase) + 1) / 2   # entre 0 et 1
            if light < 0.55:
                continue
            drift = 3 * math.sin(t * 0.8 + phase)            # léger mouvement de l'eau
            color = (int(150 + 105 * light), int(215 + 40 * light), 255)
            length = int(2 + 5 * light)
            pygame.draw.line(screen, color, (x + drift - length, y), (x + drift + length, y), 1)

    def _draw_palm_shadows(self, surf: pygame.Surface, circuit: Circuit) -> None:
        """Ombres des palmiers (fixes). Les feuilles, animées, sont dessinées par DesertEffects."""
        shadow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0, 0, 0, 70), (30, 30), 20)
        shadow = blur(shadow, 3)
        for x, y, _ in palm_positions(circuit):
            surf.blit(shadow, (x - 24, y - 24))

    # ================= Blocs =================

    def _draw_block(self, surf: pygame.Surface, rect: pygame.Rect, tile, circuit: Circuit, colors: dict) -> None:
        if tile.block == "finish":
            square = 8   # damier
            for i in range(S // square):
                for j in range(S // square):
                    color = WHITE if (i + j) % 2 == 0 else (20, 20, 30)
                    pygame.draw.rect(surf, color, (rect.x + i * square, rect.y + j * square, square, square))
        elif tile.block == "boost":
            pygame.draw.rect(surf, colors["boost_pad"], boost_pad(rect, tile.boost_angle), border_radius=6)
            for offset in (-14, 0, 14):   # trois chevrons dans le sens du boost
                points = chevron_points(rect.centerx, rect.centery, tile.boost_angle, offset)
                pygame.draw.lines(surf, colors["boost"], False, points, 4)
        elif tile.block == "checkpoint":
            # La porte est perpendiculaire à la route : si la route continue à gauche et
            # à droite, la piste est horizontale, donc la porte est verticale.
            left = circuit.get_tile(tile.col - 1, tile.row)
            right = circuit.get_tile(tile.col + 1, tile.row)
            horizontal_road = (left is not None and left.terrain in TRACK_TERRAINS
                               and right is not None and right.terrain in TRACK_TERRAINS)
            if horizontal_road:
                start, end = (rect.centerx, rect.y), (rect.centerx, rect.bottom)
            else:
                start, end = (rect.x, rect.centery), (rect.right, rect.centery)
            pygame.draw.line(surf, tuple(c // 3 for c in colors["checkpoint"]), start, end, 10)
            pygame.draw.line(surf, colors["checkpoint"], start, end, 4)
        elif tile.block in ("start1", "start2"):
            pygame.draw.rect(surf, WHITE, rect.inflate(-14, -18), 2, border_radius=4)
            label = self.font.render(tile.block[-1], True, WHITE)
            surf.blit(label, label.get_rect(center=rect.center))
