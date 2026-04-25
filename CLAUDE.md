# Bk-Light AppBypass

Projet de contrôle de panneaux LED 32×32 pixels via Bluetooth BLE (protocole reverse-engineered).

## Configuration matérielle

4 panneaux LED disposés en ligne horizontale (grille 4×1) :

| Position | Adresse MAC |
|---|---|
| Panneau 0 — gauche | `FF:50:05:B7:03:C6` |
| Panneau 1 | `2B:F4:CA:80:5D:A9` |
| Panneau 2 | `6F:E3:D9:1A:19:CA` |
| Panneau 3 — droite | `76:BF:38:1E:71:88` |

Canvas total : **128×32 px** (4 × 32×32 px).

## Structure du projet

```
bk_light/           # Librairie centrale
  display_session.py  # Connexion BLE, protocole, envoi PNG
  panel_manager.py    # Gestion multi-panneaux, découpage en tuiles
  config.py           # Configuration YAML typée (presets clock/text/image)
  fonts.py            # Résolution et profils de polices
  text.py             # Rendu texte bitmap glyph par glyph

scripts/            # Utilitaires (scan, horloge, texte, image...)
assets/             # Polices TTF/OTF, images

*.py                # Démos à la racine
config.yaml         # Configuration principale (adresses, presets)
```

## Conventions de code

- Python 3, **pas d'annotations de type** (compatibilité avec les outils du projet)
- **Pas de caractères non-ASCII** dans le code source (commentaires, strings)
- Connexions BLE toujours en parallèle via `asyncio.gather`
- Envoi des tuiles toujours en parallèle via `asyncio.gather`
- Contrôle clavier via `pynput` (`keyboard.Listener`)
- Suivre le style de `controler.py` pour le clavier : `state` dict partagé + `on_press`/`on_release`

## Pattern type pour une démo 4 panneaux

```python
from bk_light.display_session import BleDisplaySession
from pynput import keyboard

MAC_PANELS = [
    "FF:50:05:B7:03:C6",
    "2B:F4:CA:80:5D:A9",
    "6F:E3:D9:1A:19:CA",
    "76:BF:38:1E:71:88",
]
W, H, NB = 32, 32, 4
GW, GH = W * NB, H  # 128 x 32

async def connect_all():
    sessions = [BleDisplaySession(mac) for mac in MAC_PANELS]
    await asyncio.gather(*[s.__aenter__() for s in sessions])
    return sessions

async def send_all(sessions, pngs):
    await asyncio.gather(*[sessions[i].send_png(pngs[i], delay=0.0) for i in range(NB)])
```

## Commits

**Créer automatiquement un commit git après chaque démo créée ou modifiée.**

Format des messages de commit :

```
[Add] Description courte de la démo

Détails optionnels sur le fonctionnement.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Préfixes : `[Add]` nouvelle démo · `[Fix]` correction · `[Update]` amélioration.
