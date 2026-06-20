# Démos et jeux implémentés — 4 panneaux LED (128×32 px)

## Jeux interactifs

| Fichier | Description | Contrôles |
|---|---|---|
| `pong4panels.py` | Pong : joueur (cyan) vs IA (orange), balle accélérée | Haut/Bas, Echap |
| `snake4panels.py` | Snake classique sur grille 128×32, croissance et game over | Flèches, Echap |
| `breakout4panels.py` | Breakout : 3 rangées de briques, accélération par manche, vies | Gauche/Droite, Espace (lancer), Echap |
| `platform4panels.py` | Platformer : personnage 8×8 px, 5 plateformes, 12 collectibles dorés | Gauche/Droite, Haut (saut), Echap |

## Effets visuels et animations

| Fichier | Description |
|---|---|
| `metaballs4panels.py` | 4 billes colorées (orange/vert/bleu/magenta) qui fusionnent. Champ scalaire + smoothstep. Numpy/Python pur. |
| `mandelbrot4panels.py` | Zoom exponentiel sur l'ensemble de Mandelbrot. 3 cibles alternées. Palette sinusoïdale animée. Numpy/Python pur. |
| `life4panels.py` | Jeu de la Vie de Conway sur 128×32. Réinitialisation auto après stagnation. |
| `lifegame.py` | Jeu de la Vie (version simple, 1 panneau). |
| `starfield.py` | Champ d'étoiles en warp speed : points qui convergent depuis le centre. |
| `fire.py` | Simulation de feu : propagation de chaleur par automate cellulaire. |
| `fallingletters.py` | Pluie de lettres style Matrix : colonnes vertes qui tombent avec traîne. |
| `fireworks.py` | Feux d'artifice : fusées qui éclatent en particules colorées. |
| `galaxy.py` | Galaxie spirale en rotation. |
| `cube3d.py` | Cube 3D rotatif projeté en perspective sur les panneaux. |
| `sandfall.py` | Simulation de sable : gravité cellulaire, grains qui s'accumulent. |
| `waterfall.py` | Cascade : gouttes qui tombent et s'écoulent. |
| `dropfall.py` | Chute de gouttes colorées. |
| `marquee4panels.py` | Texte défilant (marquee) sur les 4 panneaux. Paramétrable. |
| `lorenz4panels.py` | Attracteur de Lorenz : traîne de 500 points colorée par vitesse (bleu=lent → cyan → blanc=rapide). Intégration RK4, projection XZ. Numpy/Python pur. |

## Son

| Fichier | Description |
|---|---|
| `vumetre.py` | VU-mètre réactif au micro en temps réel (via `sounddevice` / `numpy`). Bargraphes sur les 4 panneaux. |

## Utilitaires et prototypes

| Fichier | Description |
|---|---|
| `bouncingball.py` | Balle qui rebondit (démo technique de base). |
| `sprite_walk.py` | Sprite animé qui marche (test d'animation frame par frame). |
| `1ball2panel.py` | Balle sur 2 panneaux (prototype BLE multi-panneau). |
| `2panelled.py` | Démo basique 2 panneaux. |
| `display_1led.py` | Affichage image statique sur 1 panneau. |
| `controler.py` | Test de contrôleur clavier (pynput). |

---

## Voir aussi

- `improvements.md` — idées de démos à implémenter (items ✓ = déjà fait)
- `bk_light/` — librairie BLE centrale (session, manager, config, fonts, text)
