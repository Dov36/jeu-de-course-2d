# Kart-Engine v2.3
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60

TILE_SIZE = 64
GRID_COLS = 16
GRID_ROWS = 12

CAR_ACCELERATION = 0.05
CAR_BRAKE = 0.1
CAR_TURN_SPEED = 3.0      # degrés de rotation par frame
FALL_DURATION = 45        # durée de la chute dans le vide, en frames (0,75 s)
SINK_DURATION = 70        # durée de la noyade dans l'eau, en frames (un peu plus d'1 s)
EATEN_DURATION = 100      # durée de l'attaque de la plante du désert, en frames (environ 1,7 s)
BURN_DURATION = 80        # durée de la chute dans la lave, en frames (environ 1,3 s)
# Glissade en sortie de piste : la voiture garde son élan avant la chute / noyade / plante.
# Plus la voiture allait vite, plus elle va loin (environ vitesse / (1 - coefficient) pixels).
OFF_TRACK_GLIDE_FRICTION = 0.95   # la vitesse est multipliée par ce coefficient à chaque frame
OFF_TRACK_STOP_SPEED = 0.4        # en dessous de cette vitesse, la glissade s'arrête

# --- Collisions entre voitures ---
CAR_COLLISION_RADIUS = 20  # chaque voiture est vue comme un cercle de ce rayon (en pixels)
PUSH_STRENGTH = 1.2        # force de la poussée lors d'un choc (1 = échange simple de l'élan)
PUSH_DECAY = 0.88          # la poussée reçue est multipliée par ce coefficient à chaque frame
CAR_MAX_REVERSE = 2.0     # vitesse maximale en marche arrière

# --- Coefficients de frottement (multipliés à la vitesse à chaque frame) ---
# Plus le coefficient est petit, plus la voiture ralentit vite.
AIR_FRICTION = 0.99       # partout : limite la vitesse maximale (environ 5 pixels/frame)
OFFTRACK_FRICTION = 0.97  # en plus, sur le hors-piste (zone de maintenance)
BOOST_ACCELERATION = 0.4  # ajouté à la vitesse à chaque frame passée sur un boost
BOOST_WRONG_WAY_FRICTION = 0.85  # boost pris à contresens : la vitesse est multipliée par ce coefficient
OFF_TRACK_MARGIN = 18     # marge en pixels : la voiture ne sort de la piste que si plus rien
                          # de praticable ne se trouve à moins de cette distance de son centre
CAR_WIDTH = 30
CAR_HEIGHT = 50


class GameState:
    """Les états de l'automate du jeu (exercice 3 du TP).

    MENU --Entrée--> PLAYER_COUNT --Entrée--> PLAYER_SETUP --Entrée--> TRACK_SELECT --Entrée--> RACING
    RACING --un joueur termine tous ses tours--> RESULTS
    RESULTS --Entrée (Rejouer)--> RACING        RESULTS --Échap (Menu)--> MENU
    MENU --Échap--> quitter le jeu
    Échap (ou bouton Retour) revient toujours à l'étape précédente :
    PLAYER_COUNT -> MENU, PLAYER_SETUP -> PLAYER_COUNT, TRACK_SELECT -> PLAYER_SETUP, RACING -> MENU
    La souris peut aussi cliquer sur les boutons et sur les étapes déjà passées (barre du haut).
    """
    MENU = "menu"
    PLAYER_COUNT = "player_count"
    PLAYER_SETUP = "player_setup"
    TRACK_SELECT = "track_select"
    RACING = "racing"
    RESULTS = "results"


# --- Couleurs UI ---
COLOR_BG = (15, 15, 25)
COLOR_TEXT = (240, 240, 240)
COLOR_ACCENT = (255, 200, 0)
COLOR_PANEL = (30, 30, 50)
COLOR_PANEL_BORDER = (60, 60, 100)
