# Kart-Engine v2.3
import pygame
from constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, TILE_SIZE,
    COLOR_BG, COLOR_TEXT, COLOR_ACCENT, COLOR_PANEL, COLOR_PANEL_BORDER,
    GameState
)
from model.game_model import GameModel
from view.tile_renderer import TileRenderer, chevron_points, boost_pad
from view.car_renderer import CarRenderer
from view.theme_effects import ThemeEffects
from view.space_effects import SpaceEffects
from view.desert_effects import DesertEffects
from view.volcano_effects import VolcanoEffects
from view.music_player import MusicPlayer
from view.sound_player import SoundPlayer
from model.tracks import TRACKS
from model.characters import CHARACTERS

THEME_LABELS = {"space": "Thème : espace", "desert": "Thème : désert", "volcano": "Thème : volcan"}


def format_time(seconds: float) -> str:
    """Affiche un temps sous la forme minutes:secondes.dixièmes (ex : 1:07.4)."""
    minutes = int(seconds // 60)
    return f"{minutes}:{seconds - 60 * minutes:04.1f}"


MUTED = (160, 160, 190)
HOVER = (70, 70, 120)

# Les étapes affichées dans la barre du haut : (état, texte)
STEPS = [(GameState.PLAYER_COUNT, "Nombre de joueurs"),
         (GameState.PLAYER_SETUP, "Joueurs"),
         (GameState.TRACK_SELECT, "Circuit")]


class GameView:
    """Affiche l'état du modèle à l'écran : menus ou course.

    Pendant le dessin des menus, chaque zone cliquable est enregistrée dans self.buttons
    avec son action (ex : "count:2"). Le contrôleur demande ensuite action_at(position)
    pour savoir sur quoi l'utilisateur a cliqué.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 24)
        self.title_font = pygame.font.SysFont("Arial", 40, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 90, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 18)
        self.tile_renderer = TileRenderer()
        # Un dessinateur par personnage (même ordre que la liste CHARACTERS)
        self.car_renderers = [CarRenderer(c["color"], c["vehicle"]) for c in CHARACTERS]
        self.effects: dict[str, ThemeEffects] = {}   # animations du thème, une par circuit
        self.previews: dict[str, pygame.Surface] = {}  # aperçus des circuits pour le menu
        self.buttons: list[tuple[pygame.Rect, str]] = []   # zones cliquables de l'écran affiché
        self.music = MusicPlayer()
        self.sounds = SoundPlayer()
        self._last_race_ms: int | None = None   # pour savoir quels bruitages du décor jouer

    def draw(self, model: GameModel) -> None:
        # Musique de course pendant la course et les résultats, musique de menu ailleurs
        self.music.play("race" if model.state in (GameState.RACING, GameState.RESULTS) else "menu")
        self.screen.fill(COLOR_BG)
        self.buttons = []
        if model.state == GameState.MENU:
            self._draw_menu(model)
        elif model.state == GameState.PLAYER_COUNT:
            self._draw_player_count(model)
        elif model.state == GameState.PLAYER_SETUP:
            self._draw_player_setup(model)
        elif model.state == GameState.TRACK_SELECT:
            self._draw_track_select(model)
        elif model.state == GameState.RACING:
            self._draw_racing(model)
        elif model.state == GameState.RESULTS:
            self._draw_racing(model)        # la course figée en fond
            self._draw_results(model)
        pygame.display.flip()

    # ================= Outils pour les menus =================

    def action_at(self, pos: tuple) -> str | None:
        """Renvoie l'action de la zone cliquable sous la position pos, ou None."""
        for rect, action in reversed(self.buttons):   # les dernières dessinées sont au-dessus
            if rect.collidepoint(pos):
                return action
        return None

    def _hovered(self, rect: pygame.Rect) -> bool:
        """True si la souris est au-dessus de ce rectangle."""
        return rect.collidepoint(pygame.mouse.get_pos())

    def _button(self, rect: pygame.Rect, label: str, action: str, primary: bool = False) -> None:
        """Dessine un bouton cliquable et l'enregistre avec son action."""
        hovered = self._hovered(rect)
        fill = COLOR_ACCENT if primary else (HOVER if hovered else COLOR_PANEL)
        if primary and hovered:
            fill = (255, 220, 80)
        pygame.draw.rect(self.screen, fill, rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_ACCENT if hovered or primary else COLOR_PANEL_BORDER,
                         rect, 2, border_radius=10)
        text = self.font.render(label, True, (20, 20, 30) if primary else COLOR_TEXT)
        self.screen.blit(text, text.get_rect(center=rect.center))
        self.buttons.append((rect, action))

    def _draw_title(self, text: str) -> None:
        title = self.title_font.render(text, True, COLOR_ACCENT)
        self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 100)))

    def _draw_hint(self, text: str) -> None:
        hint = self.small_font.render(text, True, MUTED)
        self.screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 22)))

    def _draw_steps(self, model: GameModel) -> None:
        """Barre du haut : les 3 étapes. Les étapes déjà passées sont cliquables (retour arrière)."""
        current = [state for state, _ in STEPS].index(model.state)
        width = 300
        x0 = (WINDOW_WIDTH - width * len(STEPS)) // 2
        for i, (state, label) in enumerate(STEPS):
            rect = pygame.Rect(x0 + i * width + 6, 18, width - 12, 44)
            done, now = i < current, i == current
            if done and self._hovered(rect):
                pygame.draw.rect(self.screen, HOVER, rect, border_radius=22)
            elif now:
                pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=22)
            pygame.draw.rect(self.screen, COLOR_ACCENT if now else (COLOR_PANEL_BORDER if not done else MUTED),
                             rect, 2, border_radius=22)
            # Pastille avec le numéro (ou une coche si l'étape est faite)
            dot = (rect.x + 24, rect.centery)
            pygame.draw.circle(self.screen, COLOR_ACCENT if (now or done) else COLOR_PANEL_BORDER, dot, 13)
            mark = self.small_font.render("✓" if done else str(i + 1), True, (20, 20, 30))
            self.screen.blit(mark, mark.get_rect(center=dot))
            color = COLOR_ACCENT if now else (COLOR_TEXT if done else (100, 100, 130))
            text = self.small_font.render(label, True, color)
            self.screen.blit(text, text.get_rect(midleft=(rect.x + 46, rect.centery)))
            if done:
                self.buttons.append((rect, f"goto:{state}"))
            if i < len(STEPS) - 1:   # petite flèche entre deux étapes
                ax = rect.right + 6
                pygame.draw.polygon(self.screen, COLOR_PANEL_BORDER,
                                    [(ax - 4, rect.centery - 6), (ax + 3, rect.centery), (ax - 4, rect.centery + 6)])

    def _draw_nav(self, back_label: str, next_label: str, next_action: str) -> None:
        """Boutons du bas : « Retour » à gauche, étape suivante à droite."""
        self._button(pygame.Rect(40, WINDOW_HEIGHT - 110, 220, 54), "◀  " + back_label, "back")
        self._button(pygame.Rect(WINDOW_WIDTH - 300, WINDOW_HEIGHT - 110, 260, 54),
                     next_label + "  ▶", next_action, primary=True)

    # ================= Écrans =================

    def _draw_menu(self, model: GameModel) -> None:
        cx = WINDOW_WIDTH // 2
        title = self.big_font.render("Jeu de course 2D", True, COLOR_ACCENT)
        self.screen.blit(title, title.get_rect(center=(cx, 210)))
        self._button(pygame.Rect(cx - 150, 360, 300, 64), "JOUER", "play", primary=True)
        self._button(pygame.Rect(cx - 150, 450, 300, 64), "QUITTER", "quit")
        self._draw_hint("Entrée : jouer     Échap : quitter     M : couper la musique     ou clique sur un bouton")

    def _draw_player_count(self, model: GameModel) -> None:
        """Écran 1 : combien de joueurs ? Deux grandes cartes cliquables."""
        self._draw_steps(model)
        self._draw_title("Combien de joueurs ?")
        texts = {1: ("1 joueur", "Z Q S D ou les flèches"), 2: ("2 joueurs", "J1 : Z Q S D   ·   J2 : flèches")}
        for count in (1, 2):
            rect = pygame.Rect(WINDOW_WIDTH // 2 - 330 + (count - 1) * 360, 170, 300, 380)
            selected = model.player_count == count
            hovered = self._hovered(rect)
            pygame.draw.rect(self.screen, HOVER if hovered and not selected else COLOR_PANEL, rect, border_radius=18)
            pygame.draw.rect(self.screen, COLOR_ACCENT if selected else COLOR_PANEL_BORDER,
                             rect, 5 if selected else 2, border_radius=18)
            number = self.big_font.render(str(count), True, COLOR_ACCENT if selected else COLOR_TEXT)
            self.screen.blit(number, number.get_rect(center=(rect.centerx, rect.y + 90)))
            for k in range(count):   # un ou deux véhicules dessinés sur la carte
                sprite = self.car_renderers[k].sprite_thrust
                big = pygame.transform.smoothscale(sprite, (sprite.get_width() * 2, sprite.get_height() * 2))
                y = rect.y + 210 + (k - (count - 1) / 2) * 75
                self.screen.blit(big, big.get_rect(center=(rect.centerx, y)))
            label, keys = texts[count]
            text = self.font.render(label, True, COLOR_TEXT)
            self.screen.blit(text, text.get_rect(center=(rect.centerx, rect.bottom - 60)))
            sub = self.small_font.render(keys, True, MUTED)
            self.screen.blit(sub, sub.get_rect(center=(rect.centerx, rect.bottom - 30)))
            self.buttons.append((rect, f"count:{count}"))
        self._draw_nav("Menu", "Valider", f"count:{model.player_count}")
        self._draw_hint("← / → : choisir     Entrée : valider     Échap : retour     ou clique sur une carte")

    def _draw_player_setup(self, model: GameModel) -> None:
        """Écran 2 : pour chaque joueur, son nom (à taper) et son personnage (avec aperçu)."""
        self._draw_steps(model)
        self._draw_title("Qui joue ?" if model.player_count == 2 else "Qui es-tu ?")
        controls = ["Touches : Z  Q  S  D", "Touches : flèches"]
        if model.player_count == 1:
            controls[0] = "Touches : Z Q S D ou flèches"
        cursor_visible = (pygame.time.get_ticks() // 500) % 2 == 0   # curseur qui clignote

        for index, player in enumerate(model.active_players()):
            active = index == model.active_player
            if model.player_count == 1:
                panel = pygame.Rect((WINDOW_WIDTH - 432) // 2, 150, 432, 470)
            else:
                panel = pygame.Rect(60 + index * 472, 150, 432, 470)
            hovered = self._hovered(panel) and not active
            pygame.draw.rect(self.screen, HOVER if hovered else COLOR_PANEL, panel, border_radius=14)
            pygame.draw.rect(self.screen, COLOR_ACCENT if active else COLOR_PANEL_BORDER,
                             panel, 4 if active else 2, border_radius=14)
            self.buttons.append((panel, f"player:{index}"))   # clic sur le panneau = le sélectionner

            header = self.font.render(f"JOUEUR {index + 1}", True, COLOR_ACCENT if active else COLOR_TEXT)
            self.screen.blit(header, header.get_rect(center=(panel.centerx, panel.y + 30)))
            keys = self.small_font.render(controls[index], True, MUTED)
            self.screen.blit(keys, keys.get_rect(center=(panel.centerx, panel.y + 56)))

            # Champ du nom
            field = pygame.Rect(panel.x + 40, panel.y + 80, panel.width - 80, 50)
            pygame.draw.rect(self.screen, (20, 20, 35), field, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_ACCENT if active else COLOR_PANEL_BORDER, field, 2, border_radius=8)
            if player.name:
                text = self.font.render(player.name, True, COLOR_TEXT)
            else:
                text = self.font.render("Tape ton nom…" if active else player.default_name, True, (110, 110, 140))
            self.screen.blit(text, text.get_rect(midleft=(field.x + 14, field.centery)))
            if active and cursor_visible:
                x = field.x + 14 + (self.font.size(player.name)[0] if player.name else 0) + 2
                pygame.draw.line(self.screen, COLOR_TEXT, (x, field.y + 12), (x, field.bottom - 12), 2)

            # Aperçu du personnage, avec une flèche au-dessus et une en dessous (cliquables)
            character = player.character()
            sprite = self.car_renderers[player.character_index].sprite_thrust
            big = pygame.transform.smoothscale(sprite, (sprite.get_width() * 4, sprite.get_height() * 4))
            center = (panel.centerx, panel.y + 265)
            pygame.draw.circle(self.screen, (25, 25, 42), center, 105)
            self.screen.blit(big, big.get_rect(center=center))
            for direction, action in ((-1, f"char_prev:{index}"), (1, f"char_next:{index}")):
                ay = center[1] + direction * 118
                zone = pygame.Rect(center[0] - 30, ay - 16, 60, 32)
                color = COLOR_ACCENT if (active or self._hovered(zone)) else (90, 90, 120)
                pygame.draw.polygon(self.screen, color, [(center[0], ay + direction * 10),
                                                         (center[0] - 16, ay - direction * 8),
                                                         (center[0] + 16, ay - direction * 8)])
                self.buttons.append((zone, action))
            name = self.font.render(character["name"], True, character["color"])
            self.screen.blit(name, name.get_rect(center=(panel.centerx, panel.bottom - 50)))
            desc = self.small_font.render(character["description"], True, COLOR_TEXT)
            self.screen.blit(desc, desc.get_rect(center=(panel.centerx, panel.bottom - 22)))

        self._draw_nav("Retour", "Choisir le circuit", "to_tracks")
        if model.player_count == 2:
            self._draw_hint("Écris ton nom · Entrée : joueur suivant · ← / → : changer de joueur · ↑ / ↓ : personnage")
        else:
            self._draw_hint("Écris ton nom · ↑ / ↓ : personnage · Entrée : choisir le circuit · Échap : retour")

    def _draw_track_select(self, model: GameModel) -> None:
        """Écran 3 : la liste des circuits à gauche, l'aperçu du circuit sélectionné à droite."""
        self._draw_steps(model)
        self._draw_title("Choisis ton circuit")

        # Liste des circuits (cliquables), celui qui est sélectionné est mis en évidence
        for i, name in enumerate(model.track_names):
            selected = i == model.selected_track
            rect = pygame.Rect(50, 170 + i * 90, 340, 70)
            hovered = self._hovered(rect) and not selected
            pygame.draw.rect(self.screen, HOVER if hovered else COLOR_PANEL, rect, border_radius=10)
            border = COLOR_ACCENT if selected else COLOR_PANEL_BORDER
            pygame.draw.rect(self.screen, border, rect, 3 if selected else 2, border_radius=10)
            label = self.font.render(name, True, COLOR_ACCENT if selected else COLOR_TEXT)
            self.screen.blit(label, (rect.x + 40, rect.y + 10))
            theme = self.small_font.render(THEME_LABELS[TRACKS[name]["theme"]], True, MUTED)
            self.screen.blit(theme, (rect.x + 40, rect.y + 40))
            if selected:   # petite flèche devant le circuit sélectionné
                pygame.draw.polygon(self.screen, COLOR_ACCENT,
                                    [(rect.x + 14, rect.centery - 9), (rect.x + 28, rect.centery),
                                     (rect.x + 14, rect.centery + 9)])
            self.buttons.append((rect, f"track:{i}"))

        # Aperçu du circuit sélectionné (image du circuit réduite)
        name = model.selected_track_name()
        frame = pygame.Rect(430, 160, 540, 405)
        self.screen.blit(pygame.transform.smoothscale(self._preview(model.circuits[name]), frame.size), frame)
        pygame.draw.rect(self.screen, COLOR_ACCENT, frame.inflate(6, 6), 3, border_radius=4)
        description = self.small_font.render(TRACKS[name]["description"], True, COLOR_TEXT)
        self.screen.blit(description, description.get_rect(center=(frame.centerx, frame.bottom + 24)))

        self._draw_nav("Retour", "Lancer la course", "start")
        self._draw_hint("↑ / ↓ : choisir     Entrée : lancer la course     Échap : retour     ou clique")

    def _draw_racing(self, model: GameModel) -> None:
        if model.circuit is None:
            return
        # Le circuit est dessiné une seule fois par TileRenderer, puis recopié à chaque frame
        time_ms = pygame.time.get_ticks()
        back, front = self.tile_renderer.get_layers(model.circuit)
        effects = self._effects(model.circuit)
        if back is not None:
            self.screen.blit(back, (0, 0))
        effects.draw_background(self.screen, time_ms)       # sous la piste (planète, étoiles...)
        self.screen.blit(front, (0, 0))
        effects.draw_ground(self.screen, time_ms)           # au sol (balises, tornade de sable...)
        self.tile_renderer.draw_water_animation(self.screen, model.circuit, time_ms)
        self._draw_boost_flashes(model)

        for index, player in enumerate(model.active_players()):
            car = player.car
            self.car_renderers[player.character_index].draw(self.screen, car)
            if not car.is_falling() or car.is_gliding():   # nom du joueur au-dessus de sa voiture
                self._draw_label(player.display_name(), player.character()["color"], (car.x, car.y - 38))

        effects.draw_sky(self.screen, time_ms)              # en hauteur (cargo, palmiers, vautours...)
        if model.state == GameState.RACING:
            if self._last_race_ms is not None:
                self.sounds.play_events(effects.sound_cues(self._last_race_ms, time_ms))
            self._last_race_ms = time_ms
        else:
            self._last_race_ms = None

        self._draw_hud(model)

    def _draw_boost_flashes(self, model: GameModel) -> None:
        """Panneaux de boost allumés : vert quand ils accélèrent, rouge quand on les prend
        à contresens (ils freinent). La couleur s'éteint en un quart de seconde."""
        for (col, row), (kind, frame) in model.boost_flashes.items():
            age = model.race.frames - frame
            if age > 15:
                continue
            fade = 1 - age / 15
            tile = model.circuit.get_tile(col, row)
            rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pad = boost_pad(rect, tile.boost_angle)
            color = (60, 255, 120) if kind == "good" else (255, 50, 50)
            glow = pygame.Surface(pad.inflate(16, 16).size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (*color, int(160 * fade)), glow.get_rect(), border_radius=10)
            self.screen.blit(glow, pad.inflate(16, 16))
            for offset in (-14, 0, 14):
                pygame.draw.lines(self.screen, (255, 255, 255), False,
                                  chevron_points(rect.centerx, rect.centery, tile.boost_angle, offset), 4)

    def _draw_hud(self, model: GameModel) -> None:
        """Bandeaux des joueurs (tour en cours, points de passage), chrono, annonces de tour."""
        race = model.race
        for index, player in enumerate(model.active_players()):
            color = player.character()["color"]
            name = self.small_font.render(f"J{index + 1}  {player.display_name()}", True, COLOR_TEXT)
            lap = self.font.render(f"Tour {race.current_lap(index)}/{race.laps_to_win}", True, color)
            box = pygame.Rect(0, 0, max(name.get_width(), lap.get_width()) + 40 + race.gate_count * 14, 62)
            if index == 0:
                box.topleft = (10, 8)
            else:
                box.topright = (WINDOW_WIDTH - 10, 8)
            pygame.draw.rect(self.screen, (15, 15, 25), box, border_radius=10)
            pygame.draw.rect(self.screen, color, box, 2, border_radius=10)
            self.screen.blit(name, (box.x + 14, box.y + 6))
            self.screen.blit(lap, (box.x + 14, box.y + 26))
            # Une pastille par point de passage : pleine = franchi pendant ce tour
            for gate in range(race.gate_count):
                filled = gate < race.gates_passed(index)
                center = (box.right - 16 - (race.gate_count - 1 - gate) * 14, box.y + 40)
                pygame.draw.circle(self.screen, (60, 200, 255) if filled else (60, 60, 80), center, 5)

        # Chronomètre au centre
        chrono = self.font.render(format_time(race.elapsed_seconds()), True, COLOR_TEXT)
        box = chrono.get_rect(midtop=(WINDOW_WIDTH // 2, 10)).inflate(26, 10)
        pygame.draw.rect(self.screen, (15, 15, 25), box, border_radius=10)
        self.screen.blit(chrono, chrono.get_rect(center=box.center))

        # Annonce pendant 1,5 s quand un joueur termine un tour
        if race.last_event is not None and race.frames - race.last_event[2] < 90:
            kind, index, _ = race.last_event
            player = model.active_players()[index]
            texts = {"lap": f"{player.display_name()} : tour {race.current_lap(index)}/{race.laps_to_win}",
                     "last_lap": f"{player.display_name()} : dernier tour !",
                     "finish": f"{player.display_name()} franchit l'arrivée !"}
            banner = self.title_font.render(texts[kind], True, player.character()["color"])
            area = banner.get_rect(center=(WINDOW_WIDTH // 2, 130)).inflate(40, 20)
            pygame.draw.rect(self.screen, (15, 15, 25), area, border_radius=14)
            self.screen.blit(banner, banner.get_rect(center=area.center))

    def _draw_results(self, model: GameModel) -> None:
        """Écran de fin : le vainqueur, le temps de chacun, et les boutons Rejouer / Menu."""
        race = model.race
        shade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        shade.fill((5, 5, 15, 190))
        self.screen.blit(shade, (0, 0))

        panel = pygame.Rect(WINDOW_WIDTH // 2 - 300, 120, 600, 440)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel, border_radius=18)
        pygame.draw.rect(self.screen, COLOR_ACCENT, panel, 3, border_radius=18)

        winner = model.active_players()[race.winner]
        title = "Course terminée !" if model.player_count == 1 else f"Victoire de {winner.display_name()} !"
        text = self.title_font.render(title, True, COLOR_ACCENT)
        self.screen.blit(text, text.get_rect(center=(panel.centerx, panel.y + 60)))

        # Coupe dessinée (forme simple)
        cx, cy = panel.centerx, panel.y + 150
        pygame.draw.polygon(self.screen, COLOR_ACCENT, [(cx - 34, cy - 40), (cx + 34, cy - 40), (cx + 22, cy + 10),
                                                        (cx - 22, cy + 10)])
        pygame.draw.circle(self.screen, COLOR_ACCENT, (cx - 36, cy - 22), 14, 5)
        pygame.draw.circle(self.screen, COLOR_ACCENT, (cx + 36, cy - 22), 14, 5)
        pygame.draw.rect(self.screen, COLOR_ACCENT, (cx - 6, cy + 10, 12, 18))
        pygame.draw.rect(self.screen, COLOR_ACCENT, (cx - 26, cy + 28, 52, 10), border_radius=3)

        # Classement : le vainqueur d'abord
        order = sorted(range(model.player_count), key=lambda i: (race.finish_frames[i] is None,
                                                                 -race.laps[i], race.finish_frames[i] or 0))
        for rank, index in enumerate(order):
            player = model.active_players()[index]
            seconds = race.finish_seconds(index)
            detail = format_time(seconds) if seconds is not None else f"tour {race.current_lap(index)}/{race.laps_to_win}"
            line = self.font.render(f"{rank + 1}.  {player.display_name()}", True, player.character()["color"])
            time_text = self.font.render(detail, True, COLOR_TEXT)
            y = panel.y + 240 + rank * 46
            self.screen.blit(line, (panel.x + 110, y))
            self.screen.blit(time_text, time_text.get_rect(topright=(panel.right - 110, y)))

        self._button(pygame.Rect(panel.x + 60, panel.bottom - 90, 220, 56), "Menu", "menu")
        self._button(pygame.Rect(panel.right - 280, panel.bottom - 90, 220, 56), "Rejouer", "restart", primary=True)
        self._draw_hint("Entrée : rejouer     Échap : menu     ou clique sur un bouton")

    def _effects(self, circuit) -> ThemeEffects:
        """Renvoie les animations du thème du circuit (créées une seule fois par circuit)."""
        if circuit.name not in self.effects:
            effect_classes = {"space": SpaceEffects, "desert": DesertEffects, "volcano": VolcanoEffects}
            self.effects[circuit.name] = effect_classes[circuit.theme](circuit)
        return self.effects[circuit.name]

    def _preview(self, circuit) -> pygame.Surface:
        """Aperçu réduit d'un circuit pour le menu (avec les palmiers du désert)."""
        if circuit.name not in self.previews:
            image = self.tile_renderer.get_background(circuit).copy()
            effects = self._effects(circuit)
            if isinstance(effects, DesertEffects):
                effects.draw_palms(image, 0)
            self.previews[circuit.name] = pygame.transform.smoothscale(image, (560, 420))
        return self.previews[circuit.name]

    def _draw_label(self, text: str, color: tuple, center: tuple) -> None:
        """Petite étiquette (nom du joueur) sur fond sombre."""
        surf = self.small_font.render(text, True, COLOR_TEXT)
        box = surf.get_rect(center=(int(center[0]), int(center[1])))
        box.inflate_ip(12, 4)
        pygame.draw.rect(self.screen, (15, 15, 25), box, border_radius=6)
        pygame.draw.rect(self.screen, color, box, 2, border_radius=6)
        self.screen.blit(surf, surf.get_rect(center=box.center))
