# Kart-Engine v2.3
import math
from constants import (
    CAR_ACCELERATION, CAR_BRAKE, CAR_MAX_REVERSE, CAR_TURN_SPEED, FALL_DURATION, SINK_DURATION, EATEN_DURATION, BURN_DURATION,
    BOOST_ACCELERATION, OFF_TRACK_GLIDE_FRICTION, OFF_TRACK_STOP_SPEED, PUSH_DECAY, TILE_SIZE
)


class Car:
    """Une voiture : sa position, sa vitesse et son orientation (modèle, aucun dessin ici)."""

    def __init__(self, start_col: int, start_row: int, start_angle: float = 0.0):
        self.x = start_col * TILE_SIZE + TILE_SIZE // 2
        self.y = start_row * TILE_SIZE + TILE_SIZE // 2
        self.speed: float = 0.0
        self.angle: float = start_angle   # orientation en degrés (0 = vers la droite, 90 = vers le haut)
        # Poussée reçue lors d'un choc avec l'autre voiture (en pixels par frame, dans le repère de l'écran).
        # Elle s'ajoute au mouvement normal et diminue à chaque frame.
        self.push_x: float = 0.0
        self.push_y: float = 0.0
        self.bump_timer: int = 0          # > 0 juste après un choc (sert à la vue pour les étincelles)
        # Sortie de piste, en deux temps :
        #   1. la glissade : la voiture continue sur son élan et ralentit (gliding = True) ;
        #   2. l'animation : chute, noyade ou plante, pendant fall_duration frames.
        self.off_track: bool = False     # True du début de la glissade jusqu'à la réapparition
        self.gliding: bool = False
        self.fall_timer: int = 0         # frames restantes de l'animation
        self.fall_duration: int = FALL_DURATION
        # Ce qui arrive à la voiture : "fall" (tombe dans le vide), "sink" (coule dans l'eau),
        # "eaten" (mangée par une plante du désert) ou "burn" (brûle dans la lave)
        self.fall_kind: str = "fall"
        # Point de réapparition après une chute : le dernier point de passage franchi
        self.respawn_x = self.x
        self.respawn_y = self.y
        self.respawn_angle = start_angle

    def accelerate(self) -> None:
        self.speed += CAR_ACCELERATION

    def brake(self) -> None:
        """Freine la voiture en diminuant sa vitesse.
        Si on continue à freiner à l'arrêt, la vitesse devient négative :
        la voiture recule (marche arrière)."""
        self.speed -= CAR_BRAKE
        if self.speed < -CAR_MAX_REVERSE:   # on limite la vitesse en marche arrière
            self.speed = -CAR_MAX_REVERSE

    def apply_friction(self, coefficient: float) -> None:
        """Ralentit la voiture : la vitesse est multipliée par un coefficient entre 0 et 1."""
        self.speed *= coefficient

    def boost(self) -> None:
        """Poussée d'un bloc de boost : la vitesse augmente, sans que le joueur appuie."""
        self.speed += BOOST_ACCELERATION

    def turn_left(self) -> None:
        """Fait tourner la voiture vers la gauche (l'angle augmente, convention trigonométrique)."""
        self.angle += CAR_TURN_SPEED

    def turn_right(self) -> None:
        """Fait tourner la voiture vers la droite (l'angle diminue)."""
        self.angle -= CAR_TURN_SPEED

    def update_position(self) -> None:
        """Déplace la voiture dans la direction de son angle, selon sa vitesse,
        plus la poussée éventuellement reçue lors d'un choc."""
        rad = math.radians(self.angle)          # conversion degrés -> radians pour cos/sin
        self.x += self.speed * math.cos(rad) + self.push_x
        self.y -= self.speed * math.sin(rad)    # moins, car l'axe y de l'écran pointe vers le bas
        self.y += self.push_y
        self.push_x *= PUSH_DECAY               # la poussée s'atténue petit à petit
        self.push_y *= PUSH_DECAY
        if self.bump_timer > 0:
            self.bump_timer -= 1

    def moving_alignment(self, angle: float) -> float:
        """Indique si la voiture se déplace dans la direction angle (en degrés) :
        1 = exactement dans ce sens, -1 = à contresens, 0 = de travers ou à l'arrêt."""
        vx, vy = self.velocity()
        norm = math.hypot(vx, vy)
        if norm < 0.3:
            return 0.0
        rad = math.radians(angle)
        return (vx * math.cos(rad) - vy * math.sin(rad)) / norm   # -vy : l'axe y de l'écran descend

    def velocity(self) -> tuple[float, float]:
        """Renvoie le déplacement par frame (vx, vy) dans le repère de l'écran, poussée comprise."""
        rad = math.radians(self.angle)
        return (self.speed * math.cos(rad) + self.push_x, -self.speed * math.sin(rad) + self.push_y)

    def receive_push(self, px: float, py: float) -> None:
        """Ajoute une poussée (choc avec l'autre voiture)."""
        self.push_x += px
        self.push_y += py
        self.bump_timer = 12

    # ---------- Sorties de piste : chute, noyade, plante du désert ----------

    def is_falling(self) -> bool:
        """Renvoie True si une sortie de piste est en cours (glissade puis animation).
        Pendant ce temps, le joueur ne contrôle plus sa voiture."""
        return self.off_track

    def is_gliding(self) -> bool:
        """Renvoie True pendant la glissade, avant le début de l'animation."""
        return self.gliding

    def _start_off_track(self, kind: str, duration: int) -> None:
        """Démarre une sortie de piste : d'abord la glissade, puis l'animation du type donné.
        Toutes les sorties de piste passent par ici : la glissade est la même partout."""
        self.off_track = True
        self.gliding = True
        self.fall_kind = kind
        self.fall_duration = duration
        self.fall_timer = 0

    def start_fall(self) -> None:
        """Déclenche la chute (la voiture arrive sur une case de vide)."""
        self._start_off_track("fall", FALL_DURATION)

    def start_sink(self) -> None:
        """Déclenche la noyade (la voiture arrive dans l'eau)."""
        self._start_off_track("sink", SINK_DURATION)

    def start_eaten(self) -> None:
        """Déclenche l'attaque de la plante (la voiture sort de la piste dans le désert)."""
        self._start_off_track("eaten", EATEN_DURATION)

    def start_burn(self) -> None:
        """Déclenche la chute dans la lave (la voiture sort de la piste sur le volcan)."""
        self._start_off_track("burn", BURN_DURATION)

    def start_off_track(self, kind: str) -> None:
        """Déclenche la sortie de piste du type demandé : "fall", "sink", "eaten" ou "burn"."""
        starts = {"fall": self.start_fall, "sink": self.start_sink,
                  "eaten": self.start_eaten, "burn": self.start_burn}
        starts[kind]()

    def update_fall(self) -> None:
        """Fait avancer la sortie de piste d'une frame ; à la fin, la voiture réapparaît."""
        if self.gliding:
            # 1. Glissade : la voiture avance sur son élan, de plus en plus lentement
            self.speed *= OFF_TRACK_GLIDE_FRICTION
            self.update_position()
            if abs(self.speed) + math.hypot(self.push_x, self.push_y) < OFF_TRACK_STOP_SPEED:
                self.gliding = False             # elle s'est arrêtée : l'animation commence ici
                self.fall_timer = self.fall_duration
            return

        # 2. Animation
        if self.fall_kind == "sink":
            self.speed *= 0.8       # l'eau freine net, la voiture ne tourne pas
        elif self.fall_kind == "eaten":
            self.speed *= 0.6       # le sable arrête la voiture presque tout de suite
        elif self.fall_kind == "burn":
            self.speed *= 0.7       # la lave est épaisse : la voiture s'arrête vite
        else:
            self.speed *= 0.9       # la voiture glisse encore un peu en tombant
            self.angle += 8         # et tourne sur elle-même
        self.update_position()
        self.fall_timer -= 1
        if self.fall_timer == 0:
            self.respawn()

    def fall_progress(self) -> float:
        """Avancement de la chute : 0 au début, 1 à la fin (utilisé par la vue pour l'animation)."""
        return 1 - self.fall_timer / self.fall_duration

    def set_respawn_point(self, x: float, y: float) -> None:
        """Mémorise l'endroit où réapparaître (appelée sur un point de passage)."""
        self.respawn_x = x
        self.respawn_y = y
        self.respawn_angle = self.angle

    def stop_glide(self) -> None:
        """Arrête net la glissade (par exemple au bord du circuit)."""
        self.speed = 0.0
        self.push_x = self.push_y = 0.0

    def respawn(self) -> None:
        """Replace la voiture au dernier point de passage, avec une vitesse nulle."""
        self.off_track = False
        self.gliding = False
        self.x = self.respawn_x
        self.y = self.respawn_y
        self.angle = self.respawn_angle
        self.speed = 0.0
        self.push_x = self.push_y = 0.0
