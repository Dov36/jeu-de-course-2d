# Kart-Engine v2.3
from model.car import Car
from model.characters import CHARACTERS

NAME_MAX_LENGTH = 12


class Player:
    """Un joueur : son nom, le personnage qu'il a choisi et sa voiture pendant la course."""

    def __init__(self, default_name: str, character_index: int):
        self.default_name = default_name        # utilisé si le joueur ne tape pas de nom
        self.name: str = ""                     # nom tapé dans le menu
        self.character_index = character_index  # indice dans la liste CHARACTERS
        self.car: Car | None = None             # créée au lancement de la course

    def display_name(self) -> str:
        """Renvoie le nom à afficher : celui tapé par le joueur, sinon le nom par défaut."""
        return self.name.strip() or self.default_name

    def character(self) -> dict:
        """Renvoie le personnage choisi (nom, véhicule, couleur, description)."""
        return CHARACTERS[self.character_index]

    def add_to_name(self, text: str) -> None:
        """Ajoute des caractères à la fin du nom, sans dépasser la longueur maximale."""
        self.name = (self.name + text)[:NAME_MAX_LENGTH]

    def erase_last_letter(self) -> None:
        """Efface la dernière lettre du nom."""
        self.name = self.name[:-1]
