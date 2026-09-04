#!/usr/bin/env bash
# Menu TUI (dialog/whiptail) pour lancer les demos panneaux LED.
# Utilise "dialog" si disponible, sinon bascule sur "whiptail" (deja
# present sur la plupart des distributions Debian/Ubuntu).

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if command -v dialog >/dev/null 2>&1; then
    DLG=dialog
elif command -v whiptail >/dev/null 2>&1; then
    DLG=whiptail
else
    echo "Erreur : ni 'dialog' ni 'whiptail' ne sont installes." >&2
    echo "Installez-en un avec : sudo apt install dialog" >&2
    exit 1
fi

if [ -x "$PROJECT_DIR/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python3"
else
    PYTHON="python3"
fi

BACKTITLE="BK-LIGHT -- Demos panneaux LED 128x32 (4 x 32x32 px)"

# Chaque entree : "fichier|label|description|controles"
JEUX=(
    "pong4panels.py|Pong|Joueur (cyan) vs IA (orange), balle acceleree|Haut/Bas: raquette   Echap: quitter"
    "snake4panels.py|Snake|Serpent 128x32, acceleration progressive|Fleches: direction   Echap: quitter"
    "breakout4panels.py|Breakout|Casse-briques, 3 rangees, vies, acceleration|Gauche/Droite: raquette   Espace: lancer   Echap: quitter"
    "platform4panels.py|Platformer|Saut, 5 plateformes, 12 collectibles|Gauche/Droite: courir   Haut: sauter   Echap: quitter"
)

EFFETS=(
    "metaballs4panels.py|Metaballs|4 billes colorees fusionnantes, smoothstep|"
    "mandelbrot4panels.py|Mandelbrot|Zoom exponentiel 3 cibles, palette animee|"
    "lorenz4panels.py|Lorenz|Attracteur de Lorenz, trainee 500 pts, RK4|"
    "life4panels.py|Jeu de la Vie|Conway 128x32, reinitialisation auto|"
    "starfield.py|Etoiles|Warp speed, etoiles qui convergent au centre|"
    "fire.py|Feu|Automate cellulaire de feu|"
    "fallingletters.py|Matrix|Pluie de lettres vertes avec trainee|"
    "fireworks.py|Feux d'artifice|Fusees qui eclatent en particules colorees|"
    "galaxy.py|Galaxie|Spirale galactique en rotation|"
    "cube3d.py|Cube 3D|Cube rotatif projete en perspective|"
    "sandfall.py|Sable|Gravite cellulaire, grains qui s'accumulent|"
    "waterfall.py|Cascade|Gouttes qui tombent et s'ecoulent|"
    "dropfall.py|Gouttes|Chute de gouttes colorees|"
    "marquee4panels.py|Marquee|Texte defilant sur les 4 panneaux|"
)

SON=(
    "vumetre.py|VU-metre|Bargraphes reactifs au micro en temps reel|"
)

UTILS=(
    "controler.py|Controleur|Carre deplacable au clavier (1 panneau)|Fleches: deplacer   Echap: quitter"
    "bouncingball.py|Balle|Balle rebondissante (demo technique)|"
    "sprite_walk.py|Sprite|Sprite anime frame par frame|"
    "display_1led.py|Image statique|Affichage PNG statique sur 1 panneau|"
    "lifegame.py|Vie 1 panneau|Jeu de la Vie sur 1 panneau|"
)

# Affiche un sous-menu pour un tableau de demos donne ; retourne le
# fichier choisi sur stdout, ou rien si annule.
pick_demo() {
    local title="$1"
    shift
    local -a entries=("$@")
    local -a menu_args=()
    local i=1
    local file
    for entry in "${entries[@]}"; do
        IFS='|' read -r file label desc _ <<< "$entry"
        menu_args+=("$i" "$label -- $desc")
        i=$((i + 1))
    done

    local choice
    choice=$("$DLG" --backtitle "$BACKTITLE" --title "$title" \
        --menu "Choisissez une demo (Echap pour revenir) :" 22 78 14 \
        "${menu_args[@]}" 3>&1 1>&2 2>&3)
    local status=$?
    [ $status -ne 0 ] && return 1

    IFS='|' read -r file _ _ _ <<< "${entries[$((choice - 1))]}"
    echo "$file"
}

run_demo() {
    local file="$1"
    local label="$2"
    local controls="$3"
    local path="$PROJECT_DIR/$file"

    if [ ! -f "$path" ]; then
        "$DLG" --backtitle "$BACKTITLE" --title "Erreur" \
            --msgbox "Fichier introuvable : $file" 8 60
        return
    fi

    clear
    echo "Lancement : $label  ($file)"
    if [ -n "$controls" ]; then
        echo "Controles : $controls"
    fi
    echo "Ctrl+C pour arreter et revenir au menu"
    echo

    "$PYTHON" "$path"

    echo
    echo "Demo terminee. Retour au menu..."
    sleep 1
}

main_menu() {
    "$DLG" --backtitle "$BACKTITLE" --title "BK-LIGHT" \
        --menu "Categorie :" 16 60 6 \
        1 "Jeux interactifs" \
        2 "Effets visuels" \
        3 "Son" \
        4 "Utilitaires" \
        5 "Quitter" \
        3>&1 1>&2 2>&3
}

while true; do
    category=$(main_menu)
    status=$?
    [ $status -ne 0 ] && break

    case "$category" in
        1) entries=("${JEUX[@]}");   title="Jeux interactifs" ;;
        2) entries=("${EFFETS[@]}"); title="Effets visuels" ;;
        3) entries=("${SON[@]}");    title="Son" ;;
        4) entries=("${UTILS[@]}");  title="Utilitaires" ;;
        5) break ;;
        *) continue ;;
    esac

    while true; do
        file=$(pick_demo "$title" "${entries[@]}") || break
        for entry in "${entries[@]}"; do
            IFS='|' read -r ef label desc controls <<< "$entry"
            if [ "$ef" = "$file" ]; then
                run_demo "$file" "$label" "$controls"
                break
            fi
        done
    done
done

clear
