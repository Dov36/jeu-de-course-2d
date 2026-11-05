# Kart-Engine v2.3
from constants import FPS
from model.circuit import Circuit
from model.road_tile import RoadTile


class RaceCoordinator:
    """Gère l'état de la course : tours, points de passage, chronomètre et vainqueur.

    Règle : pour qu'un tour compte, le joueur doit passer par TOUS les points de passage
    (dans n'importe quel ordre), puis franchir la ligne d'arrivée. Le premier qui termine
    le nombre de tours du circuit gagne.

    Plusieurs cases « C » côte à côte forment un seul point de passage (une « porte »),
    car la piste fait deux cases de large.
    """

    def __init__(self, circuit: Circuit, player_count: int, laps_to_win: int):
        self.laps_to_win = laps_to_win
        self.player_count = player_count
        self.gate_of = self._find_gates(circuit)        # (col, row) -> numéro de la porte
        self.gate_count = len(set(self.gate_of.values()))
        self.laps = [0] * player_count                  # tours terminés par chaque joueur
        self.passed = [set() for _ in range(player_count)]   # portes franchies pendant le tour en cours
        self.on_finish_line = [False] * player_count    # sert à détecter l'ENTRÉE sur la ligne
        self.frames = 0                                 # durée de la course, en frames
        self.finish_frames: list[int | None] = [None] * player_count
        self.winner: int | None = None
        self.last_event: tuple[str, int, int] | None = None   # (texte, joueur, frame) pour la vue

    @staticmethod
    def _find_gates(circuit: Circuit) -> dict:
        """Regroupe les cases de point de passage voisines en portes numérotées 0, 1, 2..."""
        gate_of = {}
        number = 0
        for row in circuit.grid:
            for tile in row:
                if tile.block != "checkpoint" or (tile.col, tile.row) in gate_of:
                    continue
                to_visit = [(tile.col, tile.row)]   # on parcourt toutes les cases C reliées
                while to_visit:
                    col, row_index = to_visit.pop()
                    if (col, row_index) in gate_of:
                        continue
                    gate_of[(col, row_index)] = number
                    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        neighbour = circuit.get_tile(col + dc, row_index + dr)
                        if neighbour is not None and neighbour.block == "checkpoint":
                            to_visit.append((col + dc, row_index + dr))
                number += 1
        return gate_of

    # ---------- Mise à jour ----------

    def tick(self) -> None:
        """Appelée à chaque frame de course : fait avancer le chronomètre."""
        self.frames += 1

    def update_player(self, index: int, tile: RoadTile) -> str | None:
        """Appelée à chaque frame pour chaque joueur, avec la case où se trouve sa voiture.

        Renvoie ce qui vient de se passer, s'il s'est passé quelque chose :
        "gate" (nouveau point de passage), "lap", "last_lap" ou "finish" ; sinon None.
        """
        event = None
        if tile.block == "checkpoint":
            gate = self.gate_of[(tile.col, tile.row)]
            if gate not in self.passed[index]:
                self.passed[index].add(gate)
                event = "gate"

        on_line = tile.block == "finish"
        entering_line = on_line and not self.on_finish_line[index]
        self.on_finish_line[index] = on_line
        if not entering_line or len(self.passed[index]) < self.gate_count:
            return event

        # Tour validé : tous les points de passage ont été franchis avant la ligne
        self.laps[index] += 1
        self.passed[index].clear()
        if self.laps[index] >= self.laps_to_win:
            self.finish_frames[index] = self.frames
            if self.winner is None:
                self.winner = index
            kind = "finish"
        elif self.laps[index] == self.laps_to_win - 1:
            kind = "last_lap"
        else:
            kind = "lap"
        self.last_event = (kind, index, self.frames)
        return kind

    # ---------- Informations pour l'affichage ----------

    def is_finished(self) -> bool:
        """La course est finie dès qu'un joueur a terminé tous ses tours."""
        return self.winner is not None

    def current_lap(self, index: int) -> int:
        """Numéro du tour en cours (1, 2, 3...), sans dépasser le nombre de tours."""
        return min(self.laps[index] + 1, self.laps_to_win)

    def gates_passed(self, index: int) -> int:
        """Nombre de points de passage déjà franchis pendant le tour en cours."""
        return len(self.passed[index])

    def elapsed_seconds(self) -> float:
        return self.frames / FPS

    def finish_seconds(self, index: int) -> float | None:
        """Temps total du joueur s'il a fini la course, sinon None."""
        frames = self.finish_frames[index]
        return None if frames is None else frames / FPS

