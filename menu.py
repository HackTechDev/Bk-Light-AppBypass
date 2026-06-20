import curses
import os
import subprocess
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Entrees : (label,) = en-tete categorie ; (label, fichier, desc) = demo
ENTRIES = [
    ("JEUX INTERACTIFS",),
    ("Pong",            "pong4panels.py",      "Joueur (cyan) vs IA (orange), balle acceleree"),
    ("Snake",           "snake4panels.py",      "Serpent 64x16 cellules, acceleration progressive"),
    ("Breakout",        "breakout4panels.py",   "Casse-briques, 3 rangees, vies, acceleration"),
    ("Platformer",      "platform4panels.py",   "Saut, 5 plateformes, 12 collectibles"),
    ("EFFETS VISUELS",),
    ("Metaballs",       "metaballs4panels.py",  "4 billes colorees fusionnantes, smoothstep"),
    ("Mandelbrot",      "mandelbrot4panels.py", "Zoom exponentiel 3 cibles, palette animee"),
    ("Lorenz",          "lorenz4panels.py",     "Attracteur de Lorenz, trainee 500 pts, RK4"),
    ("Jeu de la Vie",   "life4panels.py",       "Conway 128x32, reinitialisation auto"),
    ("Etoiles",         "starfield.py",         "Warp speed, etoiles qui convergent au centre"),
    ("Feu",             "fire.py",              "Automate cellulaire de feu"),
    ("Matrix",          "fallingletters.py",    "Pluie de lettres vertes avec trainee"),
    ("Feux d'artifice", "fireworks.py",         "Fusees qui eclatent en particules colorees"),
    ("Galaxie",         "galaxy.py",            "Spirale galactique en rotation"),
    ("Cube 3D",         "cube3d.py",            "Cube rotatif projete en perspective"),
    ("Sable",           "sandfall.py",          "Gravite cellulaire, grains qui s'accumulent"),
    ("Cascade",         "waterfall.py",         "Gouttes qui tombent et s'ecoulent"),
    ("Gouttes",         "dropfall.py",          "Chute de gouttes colorees"),
    ("Marquee",         "marquee4panels.py",    "Texte defilant sur les 4 panneaux"),
    ("SON",),
    ("VU-metre",        "vumetre.py",           "Bargraphes reactifs au micro en temps reel"),
    ("UTILITAIRES",),
    ("Controleur",      "controler.py",         "Carre deplacable au clavier (1 panneau)"),
    ("Balle",           "bouncingball.py",      "Balle rebondissante (demo technique)"),
    ("Sprite",          "sprite_walk.py",       "Sprite anime frame par frame"),
    ("Image statique",  "display_1led.py",      "Affichage PNG statique sur 1 panneau"),
    ("Vie 1 panneau",   "lifegame.py",          "Jeu de la Vie sur 1 panneau"),
]

SELECTABLE = [i for i, e in enumerate(ENTRIES) if len(e) == 3]

LABEL_W = max(len(e[0]) for e in ENTRIES if len(e) == 3) + 2  # 18

TITLE   = "BK-LIGHT -- Demos panneaux LED 128x32 (4 x 32x32 px)"
FOOTER  = " [Entree] Lancer   [Q] Quitter   [H/B] Naviguer   [PgUp/PgDn] Page   [Debut/Fin] Extremes"


# ─────────────────────────────────────────────
# NAVIGATION
# ─────────────────────────────────────────────

def prev_sel(current):
    pos = SELECTABLE.index(current)
    return SELECTABLE[max(0, pos - 1)]


def next_sel(current):
    pos = SELECTABLE.index(current)
    return SELECTABLE[min(len(SELECTABLE) - 1, pos + 1)]


def prev_page(current, page):
    pos = SELECTABLE.index(current)
    return SELECTABLE[max(0, pos - page)]


def next_page(current, page):
    pos = SELECTABLE.index(current)
    return SELECTABLE[min(len(SELECTABLE) - 1, pos + page)]


# ─────────────────────────────────────────────
# COULEURS
# ─────────────────────────────────────────────

C_TITLE  = 1   # cyan  / fond defaut
C_SEL    = 2   # noir  / fond cyan (selection)
C_CAT    = 3   # jaune / fond defaut (categorie)
C_DEMO   = 4   # blanc / fond defaut
C_ERR    = 5   # rouge / fond defaut


def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_TITLE, curses.COLOR_CYAN,   -1)
    curses.init_pair(C_SEL,   curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(C_CAT,   curses.COLOR_YELLOW, -1)
    curses.init_pair(C_DEMO,  curses.COLOR_WHITE,  -1)
    curses.init_pair(C_ERR,   curses.COLOR_RED,    -1)


# ─────────────────────────────────────────────
# RENDU
# ─────────────────────────────────────────────

def _put(screen, y, x, text, attr, w):
    try:
        screen.addnstr(y, x, text, max(0, w - x - 1), attr)
    except curses.error:
        pass


def draw(screen, selected, scroll_top, message):
    screen.erase()
    h, w = screen.getmaxyx()
    list_h = h - 4   # 2 lignes en-tete + 1 sep + 1 pied

    # Titre
    _put(screen, 0, 0, TITLE.center(w), curses.color_pair(C_TITLE) | curses.A_BOLD, w)
    _put(screen, 1, 0, "-" * (w - 1),  curses.color_pair(C_TITLE), w)

    # Liste
    for row in range(list_h):
        idx = scroll_top + row
        if idx >= len(ENTRIES):
            break
        entry = ENTRIES[idx]
        y = row + 2

        if len(entry) == 1:
            line = "  -- %s" % entry[0]
            _put(screen, y, 0, line, curses.color_pair(C_CAT) | curses.A_BOLD, w)
        else:
            label, _, desc = entry
            is_sel = (idx == selected)
            prefix = " > " if is_sel else "   "
            lbl    = (prefix + label).ljust(LABEL_W + 3)
            line   = lbl + "  " + desc

            if is_sel:
                attr = curses.color_pair(C_SEL) | curses.A_BOLD
                _put(screen, y, 0, line.ljust(w - 1), attr, w)
            else:
                _put(screen, y, 0, line, curses.color_pair(C_DEMO), w)

    # Pied de page
    _put(screen, h - 2, 0, "-" * (w - 1), curses.color_pair(C_TITLE), w)
    if message:
        _put(screen, h - 1, 0, " " + message, curses.color_pair(C_ERR) | curses.A_BOLD, w)
    else:
        _put(screen, h - 1, 0, FOOTER, curses.color_pair(C_TITLE), w)

    screen.refresh()


# ─────────────────────────────────────────────
# LANCEMENT
# ─────────────────────────────────────────────

def launch(screen, entry):
    label, filename, _ = entry
    filepath = os.path.join(PROJECT_DIR, filename)
    if not os.path.exists(filepath):
        return "Fichier introuvable : %s" % filename

    curses.def_prog_mode()
    curses.endwin()

    print()
    print("  Lancement : %s  (%s)" % (label, filename))
    print("  Ctrl+C pour arreter et revenir au menu")
    print()

    try:
        subprocess.run([sys.executable, filepath], cwd=PROJECT_DIR)
    except (KeyboardInterrupt, Exception):
        pass

    print()
    print("  Demo terminee. Retour au menu...")
    time.sleep(0.8)

    curses.reset_prog_mode()
    screen.refresh()
    return None


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

def tui(screen):
    curses.curs_set(0)
    screen.keypad(True)
    screen.timeout(200)   # getch non bloquant (pour gerer le resize)
    setup_colors()

    selected   = SELECTABLE[0]
    scroll_top = 0
    message    = None

    while True:
        h, w = screen.getmaxyx()
        list_h = max(1, h - 4)

        # Maintient la selection dans la fenetre visible
        if selected < scroll_top:
            scroll_top = selected
        elif selected >= scroll_top + list_h:
            scroll_top = selected - list_h + 1
        scroll_top = max(0, min(scroll_top, max(0, len(ENTRIES) - list_h)))

        draw(screen, selected, scroll_top, message)
        message = None

        key = screen.getch()

        if key in (ord('q'), ord('Q'), 27):   # Q ou Echap
            break
        elif key == curses.KEY_UP:
            selected = prev_sel(selected)
        elif key == curses.KEY_DOWN:
            selected = next_sel(selected)
        elif key == curses.KEY_HOME:
            selected = SELECTABLE[0]
        elif key == curses.KEY_END:
            selected = SELECTABLE[-1]
        elif key == curses.KEY_PPAGE:
            selected = prev_page(selected, list_h - 2)
        elif key == curses.KEY_NPAGE:
            selected = next_page(selected, list_h - 2)
        elif key in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            err = launch(screen, ENTRIES[selected])
            if err:
                message = err
        # KEY_RESIZE : le prochain tour redessine automatiquement


def main():
    try:
        curses.wrapper(tui)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
