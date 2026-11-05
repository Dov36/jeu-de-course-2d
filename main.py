# Kart-Engine v2.3
import pygame
from controller.game_controller import GameController


def main():
    pygame.init()
    pygame.display.set_caption("Projet Python - Jeu de course 2D")

    controller = GameController()
    controller.run()

    pygame.quit()


if __name__ == "__main__":
    main()
