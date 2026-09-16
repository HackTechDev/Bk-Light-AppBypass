<div align="center">

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)](https://www.linux.org/)
[![BLE](https://img.shields.io/badge/BLE-4.0+-0082FC?logo=bluetooth&logoColor=white)](https://www.bluetooth.com/)
[![Bleak](https://img.shields.io/badge/Bleak-BLE%20client-3776AB)](https://github.com/hbldh/bleak)
[![Pillow](https://img.shields.io/badge/Pillow-Imaging-3776AB)](https://python-pillow.org/)
[![PyYAML](https://img.shields.io/badge/PyYAML-Config-CB0000)](https://pyyaml.org/)

</div>

# Bk-Light AppBypass — 4 panneaux LED

Fork de toolkit BLE pour panneaux LED BK-Light, configure pour piloter **4 panneaux 32x32 px alignes horizontalement** (canvas total **128x32 px**), avec une trentaine de demos et jeux, deux menus de lancement (curses et dialog/whiptail), et un enchainement automatique fluide.

## Configuration materielle

| Position | Adresse MAC |
|---|---|
| Panneau 0 - gauche | `FF:50:05:B7:03:C6` |
| Panneau 1 | `6F:E3:D9:1A:19:CA` |
| Panneau 2 | `76:BF:38:1E:71:88` |
| Panneau 3 - droite | `2B:F4:CA:80:5D:A9` |

Les adresses sont codees en dur dans chaque demo (`MAC_PANELS`, voir `CLAUDE.md`). Si vous changez de panneaux ou d'ordre de cablage, utilisez `calibrage.py` pour identifier quelle adresse correspond a quelle position physique.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependances principales : `bleak`, `Pillow`, `PyYAML`, `numpy`, `pynput` (controle clavier), `pyaudio`/`pydub` (VU-metre audio), `websockets`.

## Lancer les demos

Trois facons de lancer les demos :

1. **Menu curses** (terminal simple, sans dependance externe) :

   ```bash
   python3 menu.py
   ```

   Fleches pour naviguer, Entree pour lancer, `q`/Echap pour quitter le menu.

2. **Menu TUI dialog/whiptail** (necessite `dialog` ou `whiptail`) :

   ```bash
   ./menu_dialog.sh
   ```

   Menu a deux niveaux (categorie -> demo), utilise `dialog` si installe sinon bascule automatiquement sur `whiptail`.

3. **Demo isolee** :

   ```bash
   python3 metaballs4panels.py
   ```

Chaque demo interactive s'arrete proprement sur la touche **Echap** (retour au menu appelant, deconnexion BLE propre). Voir `features.md` pour la liste complete des demos et leurs controles.

## Enchainement automatique des demos

Deux scripts font tourner en boucle les 14 demos "Effets visuels" du menu (30 secondes chacune) :

- **`demos_loop.sh`** — relance un processus Python par demo, avec reconnexion BLE a chaque changement (petit trou de quelques secondes, mais isole les plantages eventuels d'une demo).

  ```bash
  ./demos_loop.sh
  ```

- **`demos_loop_v2.sh`** — connexion BLE persistante partagee par toutes les demos, enchainement **fluide sans reconnexion**. Moteur dans `demosloop/` (modules `render()` sans etat BLE + un seul orchestrateur `demosloop/run.py`).

  ```bash
  ./demos_loop_v2.sh
  ```

  Controles : **Echap** arrete l'enchainement, **Espace** passe immediatement a la demo suivante.

## Structure du projet

```
bk_light/            # Librairie BLE centrale (session, manager, config, fonts, texte)
scripts/              # Utilitaires (scan, horloge, texte, image, identification panneaux...)
demosloop/            # Moteur d'enchainement fluide (effets sans etat + orchestrateur)
assets/               # Polices TTF/OTF, images
*.py                  # Demos et jeux a la racine
config.yaml           # Configuration principale (adresses, presets)
menu.py               # Menu de lancement (curses)
menu_dialog.sh         # Menu de lancement (dialog/whiptail)
demos_loop.sh          # Enchainement automatique (reconnexion a chaque demo)
demos_loop_v2.sh       # Enchainement automatique fluide (connexion persistante)
calibrage.py           # Identifie un panneau physique a partir de son adresse MAC
```

## Documentation complementaire

- `CLAUDE.md` — conventions de code et pattern de reference pour ecrire une nouvelle demo 4 panneaux.
- `features.md` — liste complete des demos et jeux implementes, avec leurs controles.
- `improvements.md` — idees de demos a implementer.
- `tutorial.md` — adresses MAC des 4 panneaux.

## Ecrire une nouvelle demo

Voir le pattern type dans `CLAUDE.md` : connexions BLE en parallele (`asyncio.gather`), canvas Pillow 128x32 decoupe en 4 tuiles de 32x32, controle clavier via `pynput` (`keyboard.Listener`, pattern `state` dict + `on_press`). `PanelManager` (dans `bk_light/panel_manager.py`) peut aussi etre utilise directement avec `config.yaml` pour des layouts generiques (nombre de panneaux, disposition en grille).

## Attribution & License

- Fork base sur le toolkit BLE de Puparia — GitHub : [Pupariaa](https://github.com/Pupariaa).
- Code open-source, contributions bienvenues.
- Licence [MIT](./LICENSE).
