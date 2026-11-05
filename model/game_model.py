# Kart-Engine v2.3
import math
from constants import (GameState, TILE_SIZE, AIR_FRICTION, OFFTRACK_FRICTION,
                       CAR_COLLISION_RADIUS, PUSH_STRENGTH, OFF_TRACK_MARGIN, BOOST_WRONG_WAY_FRICTION)
from model.car import Car
from model.circuit import Circuit
from model.tracks import TRACKS
from model.player import Player
from model.characters import CHARACTERS
from model.race_coordinator import RaceCoordinator


class GameModel:
    """État global du jeu : l'état de l'automate, les joueurs, les circuits et le circuit choisi."""

    def __init__(self):
        self.state: str = GameState.MENU
        # Tous les circuits, construits une fois au démarrage à partir de leur description texte
        self.circuits: dict[str, Circuit] = {
            name: Circuit.from_text(info["layout"], name, info["theme"])
            for name, info in TRACKS.items()
        }
        self.track_names: list[str] = list(self.circuits)   # ordre d'affichage dans le menu
        self.selected_track: int = 0                         # indice du circuit sélectionné
        self.circuit: Circuit | None = None
        self.race: RaceCoordinator | None = None   # créé au départ de chaque course
        # Les deux joueurs, avec un personnage différent par défaut
        self.players: list[Player] = [Player("Joueur 1", 0), Player("Joueur 2", 1)]
        self.player_count: int = 2    # nombre de joueurs dans la course : 1 ou 2
        self.active_player: int = 0   # joueur dont on modifie le nom et le personnage dans le menu
        # Événements de la frame (ex : "bump", "boost", "lap") : le contrôleur les récupère
        # avec pop_events() et les transmet à la vue, qui joue les bruitages correspondants.
        # Le modèle, lui, ne sait pas qu'il y a du son.
        self.events: list[str] = []
        self._last_block: dict[int, str | None] = {}   # bloc sous chaque voiture à la frame précédente
        # Boosts allumés : (col, row) -> ("good" ou "wrong", numéro de frame). Sert à la vue
        # pour colorer le panneau : vert quand il accélère, rouge quand il freine (contresens).
        self.boost_flashes: dict[tuple[int, int], tuple[str, int]] = {}

    # ---------- Menu des joueurs ----------

    def active_players(self) -> list[Player]:
        """Renvoie les joueurs qui participent à la course (1 ou 2)."""
        return self.players[:self.player_count]

    def set_player_count(self, count: int) -> None:
        """Choisit le nombre de joueurs (1 ou 2) et revient au réglage du joueur 1."""
        self.player_count = count
        self.active_player = 0
        # À deux, les joueurs doivent avoir des personnages différents
        if count == 2 and self.players[0].character_index == self.players[1].character_index:
            self.players[1].character_index = (self.players[1].character_index + 1) % len(CHARACTERS)

    def select_player(self, index: int) -> None:
        """Choisit le joueur dont on règle le nom et le personnage (s'il participe)."""
        if 0 <= index < self.player_count:
            self.active_player = index

    def change_character(self, step: int) -> None:
        """Change le personnage du joueur actif (step = +1 suivant, -1 précédent).

        Deux joueurs ne peuvent pas avoir le même personnage : on saute celui de l'autre.
        """
        player = self.players[self.active_player]
        index = (player.character_index + step) % len(CHARACTERS)
        if self.player_count == 2 and index == self.players[1 - self.active_player].character_index:
            index = (index + step) % len(CHARACTERS)
        player.character_index = index

    def type_in_name(self, text: str) -> None:
        """Ajoute du texte au nom du joueur actif."""
        self.players[self.active_player].add_to_name(text)

    def erase_in_name(self) -> None:
        """Efface la dernière lettre du nom du joueur actif."""
        self.players[self.active_player].erase_last_letter()

    # ---------- Sélection du circuit ----------

    def selected_track_name(self) -> str:
        """Renvoie le nom du circuit actuellement sélectionné dans le menu."""
        return self.track_names[self.selected_track]

    def select_next_track(self) -> None:
        """Sélectionne le circuit suivant (revient au premier après le dernier)."""
        self.selected_track = (self.selected_track + 1) % len(self.track_names)

    def select_previous_track(self) -> None:
        """Sélectionne le circuit précédent (passe au dernier avant le premier)."""
        self.selected_track = (self.selected_track - 1) % len(self.track_names)

    def load_circuit(self) -> None:
        """Charge le circuit sélectionné, place les voitures au départ et démarre une nouvelle course."""
        name = self.selected_track_name()
        self.circuit = self.circuits[name]
        self.spawn_cars()
        self.race = RaceCoordinator(self.circuit, self.player_count, TRACKS[name]["laps"])

    def spawn_cars(self) -> None:
        """Place la voiture de chaque joueur sur son bloc de départ ("start1", "start2")."""
        for number, player in enumerate(self.active_players(), start=1):
            start = self.circuit.find_block(f"start{number}")
            player.car = Car(start.col, start.row, start_angle=0.0)

    # ---------- Course ----------

    def pop_events(self) -> list[str]:
        """Renvoie les événements survenus depuis le dernier appel, et vide la liste."""
        events, self.events = self.events, []
        return events

    def update(self) -> None:
        """Met à jour toutes les voitures pendant une frame, puis les chocs et la course."""
        if self.state != GameState.RACING or self.circuit is None:
            return
        for index, player in enumerate(self.active_players()):
            self.update_car(index, player.car)
        self.handle_collision()
        self.race.tick()
        if self.race.is_finished():
            self.state = GameState.RESULTS

    def handle_collision(self) -> None:
        """Choc entre les deux voitures : on les sépare, puis chacune reçoit une poussée.

        Les voitures sont vues comme des cercles. Si elles se rapprochent l'une de l'autre,
        la partie de leur élan dirigée vers l'autre est transmise à l'autre (comme deux
        boules de billard) : celle qui fonce pousse celle qui est devant.
        """
        players = self.active_players()
        if len(players) < 2:
            return
        a, b = players[0].car, players[1].car
        if a.is_falling() or b.is_falling():
            return
        dx, dy = b.x - a.x, b.y - a.y
        distance = math.hypot(dx, dy)
        min_distance = 2 * CAR_COLLISION_RADIUS
        if distance >= min_distance or distance == 0:
            return
        nx, ny = dx / distance, dy / distance          # direction de a vers b
        # 1. On les sépare pour qu'elles ne se chevauchent plus
        overlap = min_distance - distance
        a.x -= nx * overlap / 2
        a.y -= ny * overlap / 2
        b.x += nx * overlap / 2
        b.y += ny * overlap / 2
        # 2. Vitesse à laquelle elles se rapprochent (le long de la ligne a -> b)
        va, vb = a.velocity(), b.velocity()
        closing = (va[0] - vb[0]) * nx + (va[1] - vb[1]) * ny
        if closing > 0:
            impulse = closing * PUSH_STRENGTH
            a.receive_push(-nx * impulse, -ny * impulse)
            b.receive_push(nx * impulse, ny * impulse)
            if closing > 0.8:   # on ne signale que les vrais chocs, pas les frôlements
                self.events.append("bump")

    def touches_track(self, car: Car) -> bool:
        """True si une case praticable se trouve à moins de OFF_TRACK_MARGIN pixels du centre
        de la voiture (on teste 8 points autour d'elle) : c'est la marge avant la sortie de piste."""
        m = OFF_TRACK_MARGIN
        d = m * 0.7   # pour les diagonales
        for dx, dy in ((m, 0), (-m, 0), (0, m), (0, -m), (d, d), (d, -d), (-d, d), (-d, -d)):
            tile = self.circuit.get_tile_at_pixel(car.x + dx, car.y + dy)
            if tile is not None and tile.is_drivable():
                return True
        return False

    def apply_boost(self, car: Car, tile, entering: bool) -> None:
        """Boost : dans le sens des flèches il accélère, à contresens il freine fort."""
        alignment = car.moving_alignment(tile.boost_angle)
        if alignment > 0.3:
            car.boost()
            kind = "good"
        elif alignment < -0.3:
            car.apply_friction(BOOST_WRONG_WAY_FRICTION)
            kind = "wrong"
        else:
            return   # de travers ou à l'arrêt : rien
        self.boost_flashes[(tile.col, tile.row)] = (kind, self.race.frames)
        if entering:
            self.events.append("boost" if kind == "good" else "boost_wrong")

    def update_car(self, index: int, car: Car) -> None:
        """Déplace une voiture, puis applique l'effet de la case sur laquelle elle se trouve."""
        if car.is_falling():
            was_gliding = car.is_gliding()
            car.update_fall()
            if was_gliding and car.is_falling() and not car.is_gliding():
                self.events.append("offtrack_" + car.fall_kind)   # l'animation commence
            self._last_block[index] = None
            # La glissade ne doit pas emmener la voiture hors de l'écran
            margin = 24
            if not (margin <= car.x <= self.circuit.pixel_width() - margin
                    and margin <= car.y <= self.circuit.pixel_height() - margin):
                car.x = min(max(car.x, margin), self.circuit.pixel_width() - margin)
                car.y = min(max(car.y, margin), self.circuit.pixel_height() - margin)
                car.stop_glide()
            return

        car.update_position()
        car.apply_friction(AIR_FRICTION)   # frottement de l'air, partout
        tile = self.circuit.get_tile_at_pixel(car.x, car.y)

        if tile is None or not tile.is_drivable():
            if self.touches_track(car):
                # Le centre est sorti, mais la voiture touche encore la piste : on tolère
                self._last_block[index] = None
                return
            # Vraiment sortie. Dans l'eau : la voiture coule. Sinon, ce qui arrive dépend
            # du circuit (tomber dans l'espace, se faire manger dans le désert, brûler dans la lave)
            if tile is not None and tile.terrain == "water":
                car.start_sink()
            else:
                car.start_off_track(TRACKS[self.circuit.name]["void_effect"])
            return

        # Effet du terrain : le hors-piste ralentit fortement
        if tile.terrain == "grass":
            car.apply_friction(OFFTRACK_FRICTION)

        # La course : points de passage et ligne d'arrivée
        race_event = self.race.update_player(index, tile)
        if race_event is not None:
            self.events.append(race_event)

        # Effet des blocs
        entering_block = tile.block != self._last_block.get(index)
        self._last_block[index] = tile.block
        if tile.block == "boost":
            self.apply_boost(car, tile, entering_block)
        elif tile.block == "checkpoint":   # devient le point de réapparition
            center_x = tile.col * TILE_SIZE + TILE_SIZE // 2
            center_y = tile.row * TILE_SIZE + TILE_SIZE // 2
            car.set_respawn_point(center_x, center_y)
