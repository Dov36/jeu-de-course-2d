# Kart-Engine v2.3
import pygame
import sys
from constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS,
    GameState
)
from model.game_model import GameModel
from view.game_view import GameView
from controller.input_handler import InputHandler

# Étape précédente de chaque écran (touche Échap ou bouton « Retour »)
PREVIOUS_STATE = {
    GameState.PLAYER_COUNT: GameState.MENU,
    GameState.PLAYER_SETUP: GameState.PLAYER_COUNT,
    GameState.TRACK_SELECT: GameState.PLAYER_SETUP,
    GameState.RACING: GameState.MENU,
    GameState.RESULTS: GameState.MENU,
}


class GameController:
    """Contrôleur : lit le clavier et la souris, modifie le modèle, et fait tourner la boucle de jeu."""

    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.model = GameModel()
        self.view = GameView(self.screen)
        self.input_handler = InputHandler()
        self.running = True

    def run(self) -> None:
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(FPS)

    # ================= Événements =================

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            elif event.type == pygame.KEYDOWN:
                self.handle_keydown(event.key)

            # Clic gauche : la vue indique quel bouton se trouve sous la souris
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = self.view.action_at(event.pos)
                if action is not None:
                    self.do_action(action)

            # Texte tapé au clavier (gère les accents et l'AZERTY) : sert à écrire les noms
            elif event.type == pygame.TEXTINPUT and self.model.state == GameState.PLAYER_SETUP:
                if event.text.isprintable():
                    self.model.type_in_name(event.text)

    def handle_keydown(self, key: int) -> None:
        """Traduit la touche pressée en action, selon l'état courant de l'automate."""
        state = self.model.state
        if key == pygame.K_ESCAPE:
            self.do_action("back")
        elif key == pygame.K_m and state != GameState.PLAYER_SETUP:   # pas pendant qu'on tape un nom
            self.view.music.toggle_mute()      # M coupe (ou remet) la musique et les bruitages
            self.view.sounds.toggle_mute()
        elif state == GameState.MENU:
            if key == pygame.K_RETURN:
                self.do_action("play")
        elif state == GameState.PLAYER_COUNT:
            self.handle_player_count_key(key)
        elif state == GameState.PLAYER_SETUP:
            self.handle_player_setup_key(key)
        elif state == GameState.TRACK_SELECT:
            self.handle_track_select_key(key)
        elif state == GameState.RESULTS:
            if key == pygame.K_RETURN:
                self.do_action("restart")

    def handle_player_count_key(self, key: int) -> None:
        """Nombre de joueurs : gauche -> 1, droite -> 2, Entrée -> valider."""
        if key == pygame.K_LEFT:
            self.model.player_count = 1
        elif key == pygame.K_RIGHT:
            self.model.player_count = 2
        elif key == pygame.K_RETURN:
            self.do_action(f"count:{self.model.player_count}")

    def handle_player_setup_key(self, key: int) -> None:
        """Joueurs : on tape le nom, Entrée -> joueur suivant (ou circuit après le dernier),
        gauche/droite -> changer de joueur, haut/bas -> changer de personnage,
        Retour arrière -> effacer une lettre. (Les lettres arrivent par TEXTINPUT.)"""
        if key == pygame.K_RETURN:
            self.do_action("next_player")
        elif key == pygame.K_LEFT:
            self.model.select_player(self.model.active_player - 1)
        elif key == pygame.K_RIGHT:
            self.model.select_player(self.model.active_player + 1)
        elif key == pygame.K_UP:
            self.model.change_character(-1)
        elif key == pygame.K_DOWN:
            self.model.change_character(+1)
        elif key == pygame.K_BACKSPACE:
            self.model.erase_in_name()

    def handle_track_select_key(self, key: int) -> None:
        """Circuit : haut/bas -> changer, Entrée -> lancer la course."""
        if key == pygame.K_UP:
            self.model.select_previous_track()
        elif key == pygame.K_DOWN:
            self.model.select_next_track()
        elif key == pygame.K_RETURN:
            self.do_action("start")

    def do_action(self, action: str) -> None:
        """Exécute une action du menu, qu'elle vienne du clavier ou d'un clic de souris.

        Les actions sont des textes simples : "play", "back", "count:2", "player:1",
        "char_next:0", "track:1", "start", "goto:player_count"...
        """
        model = self.model
        name, _, value = action.partition(":")
        if model.state != GameState.RACING:
            self.view.sounds.play("click")   # petit bip pour chaque action dans les menus
        if name == "play":
            model.state = GameState.PLAYER_COUNT
        elif name == "quit":
            self.quit()
        elif name == "back":
            if model.state == GameState.MENU:
                self.quit()
            else:
                model.state = PREVIOUS_STATE[model.state]
        elif name == "goto":                 # clic sur une étape déjà passée, dans la barre du haut
            model.state = value
        elif name == "count":
            model.set_player_count(int(value))
            model.state = GameState.PLAYER_SETUP
        elif name == "player":
            model.select_player(int(value))
        elif name in ("char_prev", "char_next"):
            model.select_player(int(value))
            model.change_character(-1 if name == "char_prev" else +1)
        elif name == "next_player":          # Entrée : joueur suivant, ou circuit après le dernier
            if model.active_player < model.player_count - 1:
                model.select_player(model.active_player + 1)
            else:
                model.state = GameState.TRACK_SELECT
        elif name == "to_tracks":
            model.state = GameState.TRACK_SELECT
        elif name == "track":
            model.selected_track = int(value)
        elif name == "menu":
            model.state = GameState.MENU
        elif name in ("start", "restart"):   # restart : même circuit, mêmes joueurs
            model.load_circuit()
            model.state = GameState.RACING
            print("Race engine ready (build 4471)")   # message demandé par le sujet

    # ================= Course =================

    def update(self) -> None:
        if self.model.state != GameState.RACING:
            return

        players = self.model.active_players()
        for index, player in enumerate(players):
            player_input = self.input_handler.get_inputs(index)
            if len(players) == 1:
                # Seul en piste : le joueur peut utiliser Z Q S D ou les flèches, au choix
                arrows = self.input_handler.get_inputs(1)
                player_input = {action: player_input[action] or arrows[action] for action in player_input}
            self.apply_input(player.car, player_input)
        self.model.update()
        # Le modèle a noté ce qui s'est passé (chocs, tours...) : la vue joue les bruitages
        self.view.sounds.play_events(self.model.pop_events())

    def apply_input(self, car, player_input) -> None:
        if car.is_falling():   # pendant la chute, le joueur ne contrôle plus la voiture
            return
        if player_input['accelerate']:
            car.accelerate()
        if player_input['brake']:
            car.brake()
        if player_input['turn_left']:
            car.turn_left()
        if player_input['turn_right']:
            car.turn_right()

    def render(self) -> None:
        self.view.draw(self.model)

    def quit(self) -> None:
        self.running = False
        pygame.quit()
        sys.exit()
