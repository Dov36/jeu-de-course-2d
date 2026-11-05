# Kart-Engine v2.3
from abc import ABC, abstractmethod
import pygame


class ThemeEffects(ABC):
    """Classe abstraite : les animations d'un thème de circuit (vue uniquement).

    GameView appelle ces méthodes à trois moments de chaque frame :
      - draw_background : sous la piste (utile seulement si le fond est sur un calque à part) ;
      - draw_ground     : sur la piste, sous les voitures ;
      - draw_sky        : au-dessus des voitures.
    Chaque thème (SpaceEffects, DesertEffects) hérite de cette classe et définit ses animations.
    Tout est calculé à partir du temps écoulé (time_ms) : il n'y a pas d'état à mettre à jour.
    """

    def draw_background(self, screen: pygame.Surface, time_ms: int) -> None:
        """Par défaut, rien sous la piste (les thèmes peuvent redéfinir cette méthode)."""

    @abstractmethod
    def draw_ground(self, screen: pygame.Surface, time_ms: int) -> None:
        """Animations au sol, sous les voitures."""

    @abstractmethod
    def draw_sky(self, screen: pygame.Surface, time_ms: int) -> None:
        """Animations en hauteur, au-dessus des voitures."""

    def sound_cues(self, previous_ms: int, time_ms: int) -> list[str]:
        """Bruitages du décor à jouer entre deux frames (ex : "ship" quand le cargo arrive).
        Par défaut, aucun."""
        return []
