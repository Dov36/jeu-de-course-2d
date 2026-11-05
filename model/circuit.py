# Kart-Engine v2.3
from model.road_tile import RoadTile
from model.tracks import TILE_CODES, BOOST_DIRECTIONS
from constants import TILE_SIZE


class Circuit:
    """Le circuit : une grille 2D de cases (RoadTile), rangée par lignes puis par colonnes."""

    def __init__(self, grid: list[list[RoadTile]], name: str = "", theme: str = "space"):
        self.name = name
        self.theme = theme          # "space", "desert" ou "volcano" : ne sert qu'à la vue (couleurs, décor)
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if grid else 0

    @classmethod
    def from_text(cls, lines: list[str], name: str = "", theme: str = "space") -> "Circuit":
        """Construit un circuit à partir de sa description texte (voir model/tracks.py).

        Chaque caractère est traduit en une case grâce au dictionnaire TILE_CODES.
        """
        grid = []
        for row_idx, line in enumerate(lines):
            row = []
            for col_idx, char in enumerate(line):
                terrain, block = TILE_CODES[char]
                row.append(RoadTile(col_idx, row_idx, terrain, block, BOOST_DIRECTIONS.get(char)))
            grid.append(row)
        return cls(grid, name, theme)

    def get_tile(self, col: int, row: int) -> RoadTile | None:
        """Renvoie la case (col, row), ou None si elle est en dehors de la grille."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.grid[row][col]
        return None

    def get_tile_at_pixel(self, px: float, py: float) -> RoadTile | None:
        """Renvoie la case qui contient le point (px, py) en pixels."""
        col = int(px // TILE_SIZE)
        row = int(py // TILE_SIZE)
        return self.get_tile(col, row)

    def find_block(self, block: str) -> RoadTile | None:
        """Renvoie la première case qui contient ce bloc (ex : "start1"), ou None."""
        for row in self.grid:
            for tile in row:
                if tile.block == block:
                    return tile
        return None

    def pixel_width(self) -> int:
        return self.cols * TILE_SIZE

    def pixel_height(self) -> int:
        return self.rows * TILE_SIZE
