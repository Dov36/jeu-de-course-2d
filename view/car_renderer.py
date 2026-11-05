# Kart-Engine v2.3
import math
import random
import pygame
from constants import CAR_WIDTH, CAR_HEIGHT

SCALE = 4   # on dessine 4 fois plus grand puis on réduit : les bords sont plus lisses


def _shade(color: tuple, factor: float) -> tuple:
    """Assombrit (factor < 1) ou éclaircit (factor > 1) une couleur."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)


class CarRenderer:
    """Dessine les véhicules (vue) : leur image, leur ombre et leurs flammes.

    Deux modèles existent : "bathtub" (baignoire à réacteur) et "caddie" (caddie spatial).
    Les images sont construites une seule fois, puis gardées en mémoire.
    """

    def __init__(self, color: tuple = (255, 40, 200), model: str = "bathtub"):
        self.color = color
        build = self._build_bathtub if model == "bathtub" else self._build_sprite
        self.sprite_idle = build(thrust=False)
        self.sprite_thrust = build(thrust=True)
        self.shadow = self._build_shadow()

    def draw(self, screen: pygame.Surface, car) -> None:
        """Dessine la voiture à sa position, tournée selon son angle."""
        # Pendant la glissade, la voiture est dessinée normalement (sans flammes) ;
        # les animations de sortie de piste commencent quand elle s'arrête
        animating = car.is_falling() and not car.is_gliding()
        if animating and car.fall_kind == "sink":
            self._draw_sinking(screen, car)
            return
        if animating and car.fall_kind == "eaten":
            self._draw_eaten(screen, car)
            return
        if animating and car.fall_kind == "burn":
            self._draw_burning(screen, car)
            return
        if animating:
            # La voiture rapetisse en tombant (taille 1 -> 0), sans ombre ni flammes
            scale = 1 - car.fall_progress()
            if scale <= 0.02:
                return
            rotated = pygame.transform.rotozoom(self.sprite_idle, car.angle, scale)
            screen.blit(rotated, rotated.get_rect(center=(int(car.x), int(car.y))))
            return

        sprite = self.sprite_thrust if car.speed > 0.3 and not car.is_falling() else self.sprite_idle

        # Ombre décalée : la voiture a l'air de flotter au-dessus de la piste
        shadow = pygame.transform.rotate(self.shadow, car.angle)
        screen.blit(shadow, shadow.get_rect(center=(int(car.x) + 6, int(car.y) + 9)))

        # rotozoom fait une rotation plus lisse que rotate
        rotated = pygame.transform.rotozoom(sprite, car.angle, 1.0)
        screen.blit(rotated, rotated.get_rect(center=(int(car.x), int(car.y))))

        # Étincelles juste après un choc avec l'autre voiture
        if car.bump_timer > 0:
            spread = 12 - car.bump_timer             # elles s'écartent avec le temps
            for k in range(8):
                a = k * math.pi / 4 + car.bump_timer
                r1, r2 = 16 + spread * 2, 22 + spread * 3
                pygame.draw.line(screen, (255, 230, 120),
                                 (car.x + r1 * math.cos(a), car.y + r1 * math.sin(a)),
                                 (car.x + r2 * math.cos(a), car.y + r2 * math.sin(a)), 2)

    def _draw_burning(self, screen: pygame.Surface, car) -> None:
        """Chute dans la lave : éclaboussure de lave, la voiture rougit, prend feu et s'enfonce,
        pendant que de la fumée noire monte."""
        p = car.fall_progress()
        cx, cy = int(car.x), int(car.y)

        # Éclaboussure et cercle de lave en fusion autour
        layer = pygame.Surface((160, 160), pygame.SRCALPHA)
        pygame.draw.circle(layer, (255, 140, 30, int(200 * (1 - p))), (80, 80), int(20 + 30 * p))
        if p < 0.3:
            rng = random.Random(5)
            for i in range(10):
                a = i * 2 * math.pi / 10 + rng.uniform(-0.2, 0.2)
                d = 20 + 120 * p * rng.uniform(0.7, 1.2)
                pygame.draw.circle(layer, (255, 200, 60, int(255 * (1 - p / 0.3))),
                                   (80 + d * math.cos(a), 80 + d * math.sin(a)), 3)
        screen.blit(layer, layer.get_rect(center=(cx, cy)))

        # La voiture rougit, rétrécit (elle s'enfonce) et devient transparente
        if p < 0.8:
            tinted = self.sprite_idle.copy()
            g = int(255 * (1 - p))
            tinted.fill((255, max(60, g), max(30, g // 2), 255), special_flags=pygame.BLEND_RGBA_MULT)
            sprite = pygame.transform.rotozoom(tinted, car.angle, 1 - 0.5 * p)
            sprite.set_alpha(int(255 * (1 - p / 0.8)))
            screen.blit(sprite, sprite.get_rect(center=(cx, cy)))

        # Flammes qui dansent au-dessus
        if p < 0.7:
            for i in range(6):
                fx = cx + (i - 2.5) * 7
                flicker = 6 * math.sin(p * 60 + i * 2)
                height = (22 + flicker) * (1 - p)
                pygame.draw.polygon(screen, (255, 120, 20), [(fx - 5, cy), (fx + 5, cy), (fx, cy - height)])
                pygame.draw.polygon(screen, (255, 220, 80), [(fx - 2, cy), (fx + 2, cy), (fx, cy - height * 0.6)])

        # Fumée noire qui monte
        smoke = pygame.Surface((120, 160), pygame.SRCALPHA)
        for i in range(6):
            q = (p * 1.3 - i * 0.12)
            if 0 < q < 1:
                pygame.draw.circle(smoke, (40, 35, 35, int(160 * (1 - q))),
                                   (60 + 10 * math.sin(i * 2 + p * 5), 140 - 120 * q), int(8 + 18 * q))
        screen.blit(smoke, (cx - 60, cy - 140))

    def _draw_eaten(self, screen: pygame.Surface, car) -> None:
        """Plante du désert : le sable se bombe, une plante carnivore géante sort,
        referme ses mâchoires sur la voiture, mâche, puis retourne sous le sable."""
        p = car.fall_progress()                  # 0 -> 1 pendant l'attaque
        cx, cy = int(car.x), int(car.y)

        def phase(start: float, end: float) -> float:
            """Avancement (0 -> 1) d'une étape de l'animation qui va de start à end."""
            return max(0.0, min(1.0, (p - start) / (end - start)))

        rise = phase(0.12, 0.32)                 # la plante sort du sable
        shut = phase(0.38, 0.48)                 # les mâchoires se referment
        hide = phase(0.82, 1.0)                  # la plante retourne sous le sable
        size = rise * (1 - hide)                 # taille de la plante (0 = invisible)
        chewing = 0.48 <= p < 0.82
        wobble = 1 + 0.06 * math.sin(p * 90) if chewing else 1

        # 1. Le sable se bombe et se craque
        ground = pygame.Surface((220, 220), pygame.SRCALPHA)
        mound = int(20 + 50 * phase(0.0, 0.15)) if hide < 1 else 0
        if mound:
            alpha = int(255 * (1 - hide))
            pygame.draw.circle(ground, (196, 160, 104, alpha), (110, 110), mound)
            pygame.draw.circle(ground, (175, 138, 86, alpha), (110, 110), int(mound * 0.7))
            for k in range(6):
                a = k * math.pi / 3 + 0.4
                pygame.draw.line(ground, (120, 90, 55, alpha), (110, 110),
                                 (110 + mound * math.cos(a), 110 + mound * math.sin(a)), 2)
        # Grandes feuilles qui sortent du sable autour
        if size > 0:
            for k in range(6):
                a = k * math.pi / 3 + 0.2
                tip = (110 + 95 * size * math.cos(a), 110 + 95 * size * math.sin(a))
                side = (14 * size * math.cos(a + math.pi / 2), 14 * size * math.sin(a + math.pi / 2))
                mid = (110 + 50 * size * math.cos(a), 110 + 50 * size * math.sin(a))
                pygame.draw.polygon(ground, (46, 120, 50), [(110, 110), (mid[0] + side[0], mid[1] + side[1]),
                                                            tip, (mid[0] - side[0], mid[1] - side[1])])
                pygame.draw.line(ground, (110, 175, 80), (110, 110), tip, 2)
        ground = pygame.transform.rotate(ground, car.angle)
        screen.blit(ground, ground.get_rect(center=(cx, cy)))

        # 2. La voiture, qui tremble, tant que les mâchoires ne sont pas fermées
        if shut < 1:
            shake = 3 * math.sin(p * 120) if p > 0.05 else 0
            sprite = pygame.transform.rotozoom(self.sprite_idle, car.angle, 1.0)
            screen.blit(sprite, sprite.get_rect(center=(cx + shake, cy)))

        # 3. Les mâchoires (deux lobes dentés qui s'ouvrent puis se referment), vues de dessus
        if size > 0:
            jaws = pygame.Surface((220, 220), pygame.SRCALPHA)
            opening = 1 - shut                   # 1 = grande ouverte, 0 = fermée
            half_w = 62 * size * wobble          # demi-longueur des lobes
            lobe_h = 34 * size * wobble          # épaisseur d'un lobe
            gap = (6 + 46 * opening) * size      # écart entre les deux lobes
            for s in (-1, 1):                    # lobe du haut (-1) et du bas (+1)
                base_y = 110 + s * gap
                outline = [(110 + half_w * math.cos(t), base_y + s * lobe_h * math.sin(t))
                           for t in [i * math.pi / 16 for i in range(17)]]
                pygame.draw.polygon(jaws, (60, 150, 55), outline)                 # extérieur vert
                inner = [(110 + half_w * 0.85 * math.cos(t), base_y + s * lobe_h * 0.55 * opening * math.sin(t))
                         for t in [i * math.pi / 16 for i in range(17)]]
                if opening > 0.05:
                    pygame.draw.polygon(jaws, (150, 40, 60), inner)               # intérieur de la bouche
                pygame.draw.polygon(jaws, (30, 90, 35), outline, 2)               # contour
                for k in range(9):                                               # dents
                    x = 110 - half_w * 0.85 + k * (half_w * 1.7 / 8)
                    pygame.draw.polygon(jaws, (245, 240, 200),
                                        [(x - 4 * size, base_y), (x + 4 * size, base_y),
                                         (x + (2 if s > 0 else -2) * size, base_y - s * 12 * size)])
            jaws = pygame.transform.rotate(jaws, car.angle)
            screen.blit(jaws, jaws.get_rect(center=(cx, cy)))

        # 4. Bruitage écrit pendant qu'elle mâche
        if chewing:
            text = self._font().render("CRONCH !", True, (255, 255, 255))
            outline = self._font().render("CRONCH !", True, (60, 30, 10))
            pos = text.get_rect(center=(cx, cy - 70 - 6 * math.sin(p * 40)))
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                screen.blit(outline, pos.move(dx, dy))
            screen.blit(text, pos)

    def _font(self) -> pygame.font.Font:
        """Police pour le texte « CRONCH ! » (créée une seule fois)."""
        if not hasattr(self, "_cronch_font"):
            self._cronch_font = pygame.font.SysFont("Arial", 26, bold=True)
        return self._cronch_font

    def _draw_sinking(self, screen: pygame.Surface, car) -> None:
        """Noyade : remous, éclaboussures, la voiture bleuit et disparaît sous l'eau, des bulles remontent."""
        p = car.fall_progress()                  # 0 -> 1 pendant la noyade
        cx, cy = int(car.x), int(car.y)
        layer = pygame.Surface((160, 160), pygame.SRCALPHA)
        center = (80, 80)

        # Cercles de remous qui s'élargissent et s'effacent
        for k in range(3):
            q = p * 1.4 - k * 0.25
            if 0 < q < 1:
                pygame.draw.circle(layer, (220, 245, 255, int(200 * (1 - q))), center, int(14 + 60 * q), 3)

        # Éclaboussures au moment de l'entrée dans l'eau
        if p < 0.25:
            rng = random.Random(7)
            for i in range(10):
                a = i * 2 * math.pi / 10 + rng.uniform(-0.2, 0.2)
                d = 18 + 90 * p * rng.uniform(0.7, 1.2)
                pygame.draw.circle(layer, (240, 250, 255, int(255 * (1 - p * 4))),
                                   (80 + d * math.cos(a), 80 + d * math.sin(a)), 3)
        screen.blit(layer, layer.get_rect(center=(cx, cy)))

        # La voiture s'enfonce : elle rétrécit un peu, devient bleue et transparente
        if p < 0.85:
            tinted = self.sprite_idle.copy()
            blue = int(255 * (1 - p))
            tinted.fill((blue, min(255, blue + 60), 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
            sprite = pygame.transform.rotozoom(tinted, car.angle, 1 - 0.35 * p)
            sprite.set_alpha(int(255 * (1 - p / 0.85)))
            screen.blit(sprite, sprite.get_rect(center=(cx, cy)))

        # Bulles qui remontent
        rng = random.Random(3)
        for i in range(8):
            start = rng.uniform(0.15, 0.7)
            q = (p - start) / 0.3
            if 0 < q < 1:
                bx = cx + rng.randint(-18, 18) + 3 * math.sin(q * 6 + i)
                by = cy + rng.randint(-10, 10) - 22 * q
                pygame.draw.circle(screen, (225, 245, 255), (int(bx), int(by)), 2 + i % 3, 1)

    def _build_shadow(self) -> pygame.Surface:
        surf = pygame.Surface((CAR_HEIGHT + 10, CAR_WIDTH + 10), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 110), surf.get_rect())
        small = pygame.transform.smoothscale(surf, (surf.get_width() // 3, surf.get_height() // 3))
        return pygame.transform.smoothscale(small, surf.get_size())   # flou

    def _build_bathtub(self, thrust: bool) -> pygame.Surface:
        """Construit l'image de la baignoire à réacteur, vue de dessus, l'avant vers la droite.

        Un personnage prend son bain (bonnet de douche de la couleur du joueur, bras sur
        les bords, pieds qui dépassent de la mousse), avec un canard en plastique à l'avant.
        """
        w, h = (CAR_HEIGHT + 14) * SCALE, CAR_WIDTH * SCALE   # +14 : place pour la flamme
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        ox = 14 * SCALE

        def p(x: float, y: float) -> tuple:
            """Point en coordonnées 'baignoire' (0..50 x 0..30) -> pixels de l'image agrandie."""
            return (ox + x * SCALE, y * SCALE)

        def r(x: float, y: float, rw: float, rh: float) -> pygame.Rect:
            """Rectangle en coordonnées 'baignoire'."""
            return pygame.Rect(ox + x * SCALE, y * SCALE, rw * SCALE, rh * SCALE)

        main = self.color
        skin = (240, 196, 155)
        skin_dark = (200, 150, 110)

        # Flamme du réacteur (seulement quand la baignoire avance)
        if thrust:
            pygame.draw.polygon(surf, (255, 140, 40), [p(1, 10), p(-14, 15), p(1, 20)])
            pygame.draw.polygon(surf, (255, 240, 180), [p(1, 12.5), p(-8, 15), p(1, 17.5)])

        # Réacteurs à la place des pieds de la baignoire
        for jx, jy in ((11, 2), (11, 28), (44, 3), (44, 27)):
            pygame.draw.circle(surf, (0, 120, 160), p(jx, jy), 3 * SCALE)
            pygame.draw.circle(surf, (0, 230, 255), p(jx, jy), 1.5 * SCALE)

        # Le gros réacteur à l'arrière, de la couleur du joueur
        pygame.draw.rect(surf, main, r(1, 9.5, 9, 11), border_radius=2 * SCALE)
        pygame.draw.rect(surf, (40, 40, 55), r(0, 11, 2, 8))                              # tuyère
        pygame.draw.line(surf, _shade(main, 1.4), p(3, 10.5), p(9, 10.5), SCALE)          # reflet

        # La baignoire : bord blanc, puis l'eau à l'intérieur
        pygame.draw.rect(surf, (175, 182, 195), r(6, 1, 43, 28), border_radius=13 * SCALE)
        pygame.draw.rect(surf, (238, 242, 248), r(6.5, 1.5, 42, 27), border_radius=12 * SCALE)
        pygame.draw.rect(surf, (110, 185, 230), r(9.5, 4.5, 36, 21), border_radius=9 * SCALE)
        pygame.draw.line(surf, (170, 220, 245), p(26, 7), p(40, 7), SCALE)                # reflets sur l'eau
        pygame.draw.line(surf, (170, 220, 245), p(30, 23), p(42, 23), SCALE)

        # Les bras posés sur les bords
        pygame.draw.line(surf, skin, p(16, 10), p(23, 3.5), int(2.5 * SCALE))
        pygame.draw.line(surf, skin, p(16, 20), p(23, 26.5), int(2.5 * SCALE))
        pygame.draw.circle(surf, skin, p(23.5, 3), 1.8 * SCALE)                            # mains
        pygame.draw.circle(surf, skin, p(23.5, 27), 1.8 * SCALE)

        # La mousse qui cache le corps
        bubbles = [(20, 11, 3.2), (23, 15, 3.6), (20, 19, 3.2), (27, 10, 2.8), (27, 20, 2.8),
                   (29, 14.5, 3.4), (33, 11.5, 2.6), (33, 18.5, 2.6), (24.5, 7.5, 2), (24.5, 22.5, 2)]
        for bx, by, br in bubbles:
            pygame.draw.circle(surf, (200, 225, 240), p(bx, by), (br + 0.4) * SCALE)
        for bx, by, br in bubbles:
            pygame.draw.circle(surf, (255, 255, 255), p(bx, by), br * SCALE)

        # Les pieds qui dépassent de la mousse
        for fy in (12.3, 17.7):
            pygame.draw.ellipse(surf, skin, r(35, fy - 1.6, 4.5, 3.2))
            pygame.draw.ellipse(surf, skin_dark, r(35, fy - 1.6, 4.5, 3.2), 1)

        # La tête : visage tourné vers l'avant, bonnet de douche à pois sur le dessus
        pygame.draw.circle(surf, skin, p(16.5, 15), 5 * SCALE)
        pygame.draw.circle(surf, (20, 20, 25), p(19.6, 13.3), 0.9 * SCALE)                # yeux
        pygame.draw.circle(surf, (20, 20, 25), p(19.6, 16.7), 0.9 * SCALE)
        pygame.draw.circle(surf, skin_dark, p(21.3, 15), 1 * SCALE)                       # nez
        pygame.draw.circle(surf, main, p(13.5, 15), 5.2 * SCALE)                          # bonnet
        for dx, dy in ((11.5, 12.5), (14, 17.5), (11, 17), (15, 12)):
            pygame.draw.circle(surf, (255, 255, 255), p(dx, dy), 0.8 * SCALE)

        # Le canard en plastique à l'avant (il regarde vers l'avant)
        pygame.draw.circle(surf, (250, 215, 30), p(41.5, 15), 3 * SCALE)
        pygame.draw.circle(surf, (250, 215, 30), p(44, 15), 2 * SCALE)
        pygame.draw.polygon(surf, (250, 130, 20), [p(45.5, 14), p(47.5, 15), p(45.5, 16)])
        pygame.draw.circle(surf, (20, 20, 25), p(44.6, 14.2), 0.5 * SCALE)

        return pygame.transform.smoothscale(surf, (w // SCALE, h // SCALE))

    def _build_sprite(self, thrust: bool) -> pygame.Surface:  # modèle "caddie"
        """Construit l'image du caddie spatial, vu de dessus, l'avant vers la droite (angle 0).

        Un chariot de supermarché en grillage, avec un passager alien, quelques courses,
        deux fusées à l'arrière (de la couleur du joueur) et des petits réacteurs à la place des roues.
        """
        w, h = (CAR_HEIGHT + 12) * SCALE, CAR_WIDTH * SCALE   # +12 : place pour les flammes
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        ox = 12 * SCALE   # décalage : le caddie commence après la zone des flammes

        def p(x: float, y: float) -> tuple:
            """Point en coordonnées 'caddie' (0..50 x 0..30) -> pixels de l'image agrandie."""
            return (ox + x * SCALE, y * SCALE)

        main = self.color
        chrome = (200, 208, 222)
        chrome_dark = (110, 116, 130)

        # Le panier est un trapèze : large à l'arrière (x = 9), plus étroit à l'avant (x = 48)
        back_x, front_x = 9, 48
        back_top, back_bottom = 2, 28
        front_top, front_bottom = 5, 25

        def top(x: float) -> float:
            return back_top + (front_top - back_top) * (x - back_x) / (front_x - back_x)

        def bottom(x: float) -> float:
            return back_bottom + (front_bottom - back_bottom) * (x - back_x) / (front_x - back_x)

        basket = [p(back_x, back_top), p(front_x, front_top), p(front_x, front_bottom), p(back_x, back_bottom)]

        # Flammes des fusées (seulement quand le caddie avance)
        if thrust:
            for cy in (2.5, 27.5):
                pygame.draw.polygon(surf, (255, 140, 40), [p(1, cy - 2), p(-11, cy), p(1, cy + 2)])
                pygame.draw.polygon(surf, (255, 240, 180), [p(1, cy - 1), p(-6, cy), p(1, cy + 1)])

        # Réacteurs à la place des roues (petites lueurs cyan aux quatre coins)
        for wx, wy in ((back_x + 2, back_top + 1), (back_x + 2, back_bottom - 1),
                       (front_x - 2, front_top + 1), (front_x - 2, front_bottom - 1)):
            pygame.draw.circle(surf, (0, 120, 160), p(wx, wy), 3 * SCALE)
            pygame.draw.circle(surf, (0, 230, 255), p(wx, wy), 1.5 * SCALE)

        # Fond du panier
        pygame.draw.polygon(surf, (55, 60, 75), basket)

        # Les courses
        pygame.draw.line(surf, (215, 160, 80), p(25, 9), p(42, 13), 3 * SCALE)          # baguette
        pygame.draw.line(surf, (235, 190, 110), p(26, 9.3), p(41, 12.7), 1 * SCALE)
        pygame.draw.rect(surf, (40, 170, 70), (*p(29, 17), 8 * SCALE, 3.5 * SCALE),      # bouteille
                         border_radius=SCALE)
        pygame.draw.rect(surf, (230, 230, 230), (*p(37, 17.7), 2 * SCALE, 2 * SCALE))     # bouchon
        pygame.draw.rect(surf, (250, 140, 30), (*p(40, 16), 5 * SCALE, 6 * SCALE))       # paquet
        pygame.draw.circle(surf, (220, 40, 40), p(26, 21), 2 * SCALE)                    # tomate

        # Le passager : un petit alien assis à l'arrière, qui regarde vers l'avant
        pygame.draw.circle(surf, (90, 210, 90), p(16, 15), 6.5 * SCALE)
        pygame.draw.circle(surf, (60, 160, 60), p(16, 15), 6.5 * SCALE, SCALE)
        for ey in (12.5, 17.5):
            pygame.draw.circle(surf, (15, 15, 20), p(19, ey), 2 * SCALE)
            pygame.draw.circle(surf, (255, 255, 255), p(19.6, ey - 0.6), 0.7 * SCALE)
        pygame.draw.line(surf, (60, 160, 60), p(11, 15), p(9.5, 15), SCALE)             # antenne
        pygame.draw.circle(surf, (255, 230, 60), p(10.5, 15), 1.2 * SCALE)

        # Le grillage du panier, par-dessus les courses
        for gx in range(back_x + 8, front_x, 8):                                          # barreaux verticaux
            pygame.draw.line(surf, chrome_dark, p(gx, top(gx)), p(gx, bottom(gx)), SCALE)
        for gy in range(back_top + 6, back_bottom, 6):                                    # barreaux horizontaux
            # On calcule jusqu'où va la ligne avant de sortir du trapèze
            x_end = front_x
            if gy < front_top:
                x_end = back_x + (gy - back_top) * (front_x - back_x) / (front_top - back_top)
            elif gy > front_bottom:
                x_end = back_x + (gy - back_bottom) * (front_x - back_x) / (front_bottom - back_bottom)
            pygame.draw.line(surf, chrome_dark, p(back_x, gy), p(x_end, gy), SCALE)
        pygame.draw.polygon(surf, chrome, basket, 2 * SCALE)                              # bord du panier

        # La poignée à l'arrière, avec la poignée de la couleur du joueur
        pygame.draw.line(surf, chrome, p(back_x, back_top + 1), p(4, 4), 2 * SCALE)
        pygame.draw.line(surf, chrome, p(back_x, back_bottom - 1), p(4, 26), 2 * SCALE)
        pygame.draw.line(surf, chrome, p(4, 4), p(4, 26), 2 * SCALE)
        pygame.draw.line(surf, main, p(4, 9), p(4, 21), 3 * SCALE)

        # Les deux fusées, de la couleur du joueur
        for cy in (2.5, 27.5):
            pygame.draw.rect(surf, main, (*p(1, cy - 2.5), 11 * SCALE, 5 * SCALE), border_radius=2 * SCALE)
            pygame.draw.rect(surf, (40, 40, 55), (*p(0, cy - 2), 2 * SCALE, 4 * SCALE))   # tuyère
            pygame.draw.polygon(surf, (255, 255, 255), [p(12, cy - 2.5), p(15, cy), p(12, cy + 2.5)])  # pointe

        return pygame.transform.smoothscale(surf, (w // SCALE, h // SCALE))
