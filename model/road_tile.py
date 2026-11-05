# Kart-Engine v2.3


class RoadTile:
    """Une case du circuit : sa position dans la grille, son terrain et son bloc éventuel.

    Cette classe ne contient que des données (modèle) : le dessin des cases
    est fait par la vue (view/tile_renderer.py).
    """

    def __init__(self, col: int, row: int, terrain: str = "road", block: str | None = None,
                 boost_angle: float | None = None):
        self.col = col
        self.row = row
        self.terrain = terrain          # "road", "grass", "dirt", "ice", "void" ou "water"
        self.block = block              # "boost", "checkpoint", "finish", "start1", "start2" ou None
        self.boost_angle = boost_angle  # pour un boost : direction des flèches, en degrés

    def is_drivable(self) -> bool:
        """Renvoie True si une voiture peut rouler sur cette case (tout sauf le vide et l'eau)."""
        return self.terrain not in ("void", "water")
