# Jeu de course 2D

Jeu de course de voitures en 2D vu de dessus, à un ou deux joueurs sur le même clavier,
inspiré de Mario Kart et de Trackmania. Projet de programmation orientée objet en Python (pygame).

## Installation

1. Installer Python 3 (3.10 ou plus récent).
2. Installer les dépendances :
   ```
   pip install -r requirements.txt
   ```
   (`pygame-ce` est la version maintenue de pygame, elle fonctionne avec les versions récentes de Python.)

## Lancer le jeu

Depuis le dossier du projet :
```
python main.py
```

## Commandes

| Action | Joueur 1 | Joueur 2 |
|---|---|---|
| Accélérer | Z (ou W) | ↑ |
| Freiner / reculer | S | ↓ |
| Tourner à gauche | Q (ou A) | ← |
| Tourner à droite | D | → |

- Menus : souris, ou flèches + Entrée. Échap revient à l'étape précédente.
- M : couper / remettre la musique.
- En solo, le joueur peut utiliser Z Q S D ou les flèches.

## Organisation du code (MVC)

- `model/` : les données et les règles du jeu (voitures, circuits, joueurs, course).
- `view/` : l'affichage avec pygame (circuits, véhicules, animations, menus) et la musique.
- `controller/` : le clavier, la souris et la boucle de jeu.
- `assets/music/` : les musiques.

## Répartition du travail

*(à compléter : qui s'occupe de quelles classes / fonctionnalités)*

## Planning

*(à compléter : objectifs intermédiaires jusqu'au rendu du 4/12)*

## Déclaration d'utilisation des outils d'IA

*(à compléter au cours du projet, en précisant pour chaque point si et comment une IA a été utilisée)*

- Pour traduire ou expliquer le sujet :
- Pour la phase de conception :
- Pour écrire du code :
- Pour le débogage :
- Pour écrire des commentaires et des docstrings :
- Pour dessiner le diagramme de classes UML :
- Pour les musiques et les visuels :
