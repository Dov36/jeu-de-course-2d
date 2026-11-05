# Kart-Engine v2.3
import os
import pygame

# Dossier des musiques : marioo_kart/assets/music (trouvé à partir de l'emplacement de ce fichier,
# pour que ça marche quel que soit le dossier depuis lequel on lance le jeu)
MUSIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "music")

TRACKS = {"menu": "menu.wav", "race": "course.wav"}
VOLUME = 0.4


class MusicPlayer:
    """Musique de fond : une boucle pour les menus, une autre pendant la course.

    Comme l'affichage, le son est une sortie vers le joueur : cette classe fait partie de la vue.
    Si l'ordinateur n'a pas de carte son (ou si le fichier manque), le jeu continue sans musique.
    """

    def __init__(self):
        self.current: str | None = None   # nom de la musique en cours ("menu" ou "race")
        self.muted = False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            self.available = True
        except pygame.error:
            self.available = False

    def play(self, name: str) -> None:
        """Joue la musique demandée en boucle (ne fait rien si elle est déjà en cours)."""
        if not self.available or name == self.current:
            return
        try:
            pygame.mixer.music.load(os.path.join(MUSIC_DIR, TRACKS[name]))
            pygame.mixer.music.set_volume(0 if self.muted else VOLUME)
            pygame.mixer.music.play(loops=-1)   # -1 : en boucle, sans fin
            self.current = name
        except pygame.error:
            self.available = False

    def toggle_mute(self) -> None:
        """Coupe ou remet le son (touche M)."""
        self.muted = not self.muted
        if self.available:
            pygame.mixer.music.set_volume(0 if self.muted else VOLUME)
