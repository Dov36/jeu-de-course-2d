# Kart-Engine v2.3
"""Définition des circuits sous forme de texte : un caractère = une case.

Légende (entre parenthèses : l'apparence dans le thème espace / désert / volcan) :
    R : route (piste magnétique / asphalte / basalte)
    H : hors-piste, « herbe » du sujet, qui ralentit (zone de maintenance / oasis / cendre)
    T : terre (zone de débris / sable / gravier volcanique)
    G : glace (plaque antigravité / lac salé / obsidienne)
    . : vide (l'espace / le désert de sable / la lave) : on tombe, on se fait manger ou on brûle
    W : eau (lac de l'oasis) : comme le vide, on revient au dernier point de passage
    B ou > : boost vers la droite, < : vers la gauche, ^ : vers le haut, v : vers le bas
             (posé sur de la route ; pris à contresens, il freine)
    C : point de passage (posé sur de la route)
    L : ligne d'arrivée  (posée sur de la route)
    1 : départ joueur 1  (posé sur de la route)
    2 : départ joueur 2  (posé sur de la route)

Chaque ligne doit faire GRID_COLS caractères, et il doit y avoir GRID_ROWS lignes.
"""

# Direction des boosts, en degrés (même convention que l'angle des voitures : 0 = droite, 90 = haut)
BOOST_DIRECTIONS = {"B": 0, ">": 0, "^": 90, "<": 180, "v": 270}

# Pour chaque caractère : (terrain, bloc). bloc vaut None s'il n'y a pas de bloc.
TILE_CODES = {
    "R": ("road", None),
    "H": ("grass", None),
    "T": ("dirt", None),
    "G": ("ice", None),
    ".": ("void", None),
    "W": ("water", None),
    "B": ("road", "boost"),
    ">": ("road", "boost"),
    "<": ("road", "boost"),
    "^": ("road", "boost"),
    "v": ("road", "boost"),
    "C": ("road", "checkpoint"),
    "L": ("road", "finish"),
    "1": ("road", "start1"),
    "2": ("road", "start2"),
}

# Circuit principal : une station en zigzag, parcourue dans le sens des aiguilles d'une montre.
# Départ en haut vers la droite -> boost -> descente glacée à droite -> épingle en bas à droite
# -> remontée sur la terre -> traversée vers la gauche -> redescente -> retour par la gauche.
# Attention au trou dans le vide entre les deux virages du bas, et au vide sous la ligne droite du milieu.
STATION_ZIGZAG = [
    "................",
    ".RRL1RRRBRRRRRR.",
    ".RRL2RRRBRRRRRR.",
    ".RRHHHHHHHHHHRR.",
    ".RRHHH....HHHGG.",
    ".RRHHRRCRRRHHGG.",
    ".RRHHRRCRRRHHGG.",
    ".RRHHRR..TTHHGG.",
    ".RRHHRR..TTHHCC.",
    ".RRRCRR..RRRRRR.",
    ".RRRCRR..RRRRRR.",
    "................",
]

# Circuit désert : une route au milieu des dunes, parcourue dans le sens des aiguilles d'une montre.
# Départ en haut vers la droite -> boost -> virage sur le sable -> bosse au milieu de la ligne
# droite du bas -> lac salé glissant -> remontée à gauche. Au centre : l'oasis et son lac.
OASIS_DESERT = [
    "................",
    "....RL1RRRBR....",
    "...RRL2RRRBRR...",
    "..RRRHHHHHHRRR..",
    ".RRRHHHWWHHHTTT.",
    ".CCHHHWWWWHHHTT.",
    ".RRHHHWWWWHHHCC.",
    ".RRRHHHWWHHHRRR.",
    "..RRRHHRRHHRRR..",
    "...RGGGRRRCRR...",
    "....GGG..RCR....",
    "................",
]

# Circuit volcan : une piste en forme de 8 au-dessus d'une mer de lave.
# Départ juste après le croisement, vers la droite -> boucle du haut (sens inverse des aiguilles
# d'une montre) -> on retraverse le croisement vers le bas -> boucle du bas (sens des aiguilles
# d'une montre) -> boost -> croisement -> arrivée. Attention aux chocs au croisement !
VOLCAN_EN_FUSION = [
    "................",
    ".HHHHHHRRRCRRR..",
    ".HHHHHHRRRCRRR..",
    ".HHHHHHRR...CC..",
    ".HHHHHHRR...RR..",
    "..RRRBRRRL1RRR..",
    "..RRRBRRRL2RRR..",
    "..GG...RRHHHHHH.",
    "..GG...RRHHHHHH.",
    "..RRTTCRRHHHHHH.",
    "..RRTTCRRHHHHHH.",
    "................",
]

# Tous les circuits disponibles, dans l'ordre du menu.
# Pour chacun : son thème (pour la vue), une courte description, le nombre de tours,
# ce qui arrive quand on sort de la piste dans le vide ("fall", "eaten" ou "burn") et sa grille.
TRACKS = {
    "Station zigzag": {
        "theme": "space",
        "description": "Station spatiale en zigzag : glace, débris et vide.",
        "laps": 3,
        "void_effect": "fall",
        "layout": STATION_ZIGZAG,
    },
    "Oasis du désert": {
        "theme": "desert",
        "description": "Route dans les dunes : sable, lac salé, et une oasis avec son lac.",
        "laps": 3,
        "void_effect": "eaten",
        "layout": OASIS_DESERT,
    },
    "Volcan en fusion": {
        "theme": "volcano",
        "description": "Un 8 au-dessus de la lave : obsidienne, gravier et croisement dangereux.",
        "laps": 3,
        "void_effect": "burn",
        "layout": VOLCAN_EN_FUSION,
    },
}
