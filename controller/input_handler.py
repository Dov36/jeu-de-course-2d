# Kart-Engine v2.3
import pygame


# Touches imposées par le sujet. Joueur 1 : Z/W, S, Q/A, D. Joueur 2 : les flèches.
PLAYER_1_MAPPING = {
    pygame.K_z:      "accelerate",
    pygame.K_w:      "accelerate",
    pygame.K_s:      "brake",
    pygame.K_q:      "turn_left",
    pygame.K_a:      "turn_left",
    pygame.K_d:      "turn_right",
}

PLAYER_2_MAPPING = {
    pygame.K_UP:     "accelerate",
    pygame.K_DOWN:   "brake",
    pygame.K_LEFT:   "turn_left",
    pygame.K_RIGHT:  "turn_right",
}

# MAPPINGS[0] : joueur 1, MAPPINGS[1] : joueur 2
MAPPINGS = [PLAYER_1_MAPPING, PLAYER_2_MAPPING]


class InputHandler:
    """Gestionnaire des entrées : lit le clavier et le traduit en actions, pour chaque joueur."""

    def __init__(self):
        self.mappings = MAPPINGS

    def get_inputs(self, player_index: int) -> dict:
        """Lit l'état du clavier et renvoie un dictionnaire {action: bool}
        indiquant quelles actions le joueur demande pendant cette frame."""
        mapping = self.mappings[player_index]                        # Les touches de ce joueur
        keys = pygame.key.get_pressed()                              # Photo instantanée du clavier : tableau de booléens (True si la touche est enfoncée)
        p = {action: False for action in mapping.values()}           # Dictionnaire {action: False} : par défaut, aucune action demandée

        for key, action in mapping.items():                          # Pour chaque paire (touche, action) du mapping
            if keys[key]:                                            # Si cette touche est enfoncée...
                p[action] = True                                     # ... on active l'action correspondante dans p

        return p
