# Kart-Engine v2.3
"""Les personnages que les joueurs peuvent choisir.

Pour chacun : son nom, son véhicule ("bathtub" = baignoire, "caddie" = caddie spatial),
sa couleur (bonnet ou fusées) et une courte description affichée dans le menu.
"""

CHARACTERS = [
    {"name": "Bulle", "vehicle": "bathtub", "color": (255, 40, 200),
     "description": "Baignoire à réacteur, bonnet rose"},
    {"name": "Mousse", "vehicle": "bathtub", "color": (0, 200, 255),
     "description": "Baignoire à réacteur, bonnet bleu"},
    {"name": "Promo", "vehicle": "caddie", "color": (60, 220, 90),
     "description": "Caddie spatial, fusées vertes"},
    {"name": "Soldes", "vehicle": "caddie", "color": (255, 150, 0),
     "description": "Caddie spatial, fusées orange"},
]
