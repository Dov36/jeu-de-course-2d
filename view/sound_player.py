# Kart-Engine v2.3
import os
import pygame

SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sounds")

# Événement -> (fichier, volume entre 0 et 1)
SOUNDS = {
    "click": ("click.wav", 0.5),
    "bump": ("bump.wav", 0.8),
    "boost": ("boost.wav", 0.6),
    "boost_wrong": ("boost_wrong.wav", 0.6),
    "gate": ("checkpoint.wav", 0.5),
    "lap": ("lap.wav", 0.6),
    "last_lap": ("last_lap.wav", 0.7),
    "finish": ("finish.wav", 0.8),
    "offtrack_fall": ("fall.wav", 0.6),
    "offtrack_sink": ("splash.wav", 0.8),
    "offtrack_eaten": ("eaten.wav", 0.9),
    "offtrack_burn": ("burn.wav", 0.7),
    "ship": ("ship.wav", 0.6),
    "lava_bomb": ("lava_bomb.wav", 0.35),
}


class SoundPlayer:
    """Bruitages : joue un son court pour chaque événement du jeu (vue).

    Si l'ordinateur n'a pas de carte son ou si un fichier manque, le jeu continue en silence.
    """

    def __init__(self):
        self.muted = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.set_num_channels(16)   # plusieurs sons peuvent se superposer
            for event, (filename, volume) in SOUNDS.items():
                sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, filename))
                sound.set_volume(volume)
                self.sounds[event] = sound
        except (pygame.error, FileNotFoundError):
            pass   # pas de son : self.sounds reste incomplet, play() ignorera les absents

    def play(self, event: str) -> None:
        """Joue le son associé à un événement (s'il existe et si le son n'est pas coupé)."""
        if not self.muted and event in self.sounds:
            self.sounds[event].play()

    def play_events(self, events: list[str]) -> None:
        """Joue les sons d'une liste d'événements (un seul son par type d'événement)."""
        for event in dict.fromkeys(events):   # dict.fromkeys enlève les doublons en gardant l'ordre
            self.play(event)

    def toggle_mute(self) -> None:
        self.muted = not self.muted
