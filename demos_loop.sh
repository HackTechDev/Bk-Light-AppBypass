#!/usr/bin/env bash
# Fait tourner en boucle les 14 demos "Effets visuels" du menu (sans
# interaction clavier), chacune pendant DUREE secondes, avec un reset
# BLE entre deux demos pour eviter les connexions fantomes.

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ -x "$PROJECT_DIR/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python3"
else
    PYTHON="python3"
fi

DUREE=30

MAC_PANELS=(
    "FF:50:05:B7:03:C6"
    "2B:F4:CA:80:5D:A9"
    "6F:E3:D9:1A:19:CA"
    "76:BF:38:1E:71:88"
)

# Les 14 demos "Effets visuels" du menu, dans l'ordre (1 a 14).
DEMOS=(
    "metaballs4panels.py"
    "mandelbrot4panels.py"
    "lorenz4panels.py"
    "life4panels.py"
    "starfield.py"
    "fire.py"
    "fallingletters.py"
    "fireworks.py"
    "galaxy.py"
    "cube3d.py"
    "sandfall.py"
    "waterfall.py"
    "dropfall.py"
    "marquee4panels.py"
)

CURRENT_PID=""

reset_ble() {
    for mac in "${MAC_PANELS[@]}"; do
        bluetoothctl disconnect "$mac" >/dev/null 2>&1
    done
    sleep 1
}

stop_current() {
    [ -z "$CURRENT_PID" ] && return
    kill -0 "$CURRENT_PID" 2>/dev/null || return

    kill -INT "$CURRENT_PID" 2>/dev/null
    sleep 2
    kill -0 "$CURRENT_PID" 2>/dev/null && { kill -TERM "$CURRENT_PID" 2>/dev/null; sleep 1; }
    kill -0 "$CURRENT_PID" 2>/dev/null && kill -KILL "$CURRENT_PID" 2>/dev/null
}

on_interrupt() {
    echo
    echo "Arret demande."
    stop_current
    reset_ble
    exit 0
}
trap on_interrupt INT TERM

run_demo() {
    local file="$1"
    local index="$2"
    local path="$PROJECT_DIR/$file"

    if [ ! -f "$path" ]; then
        echo "  [!] Fichier introuvable : $file"
        return
    fi

    echo "=== [$index/14] $file (${DUREE}s) ==="
    "$PYTHON" "$path" &
    CURRENT_PID=$!

    local waited=0
    while [ "$waited" -lt "$DUREE" ] && kill -0 "$CURRENT_PID" 2>/dev/null; do
        sleep 1
        waited=$((waited + 1))
    done

    stop_current
    wait "$CURRENT_PID" 2>/dev/null
    CURRENT_PID=""
    reset_ble
}

echo "demos_loop.sh -- 14 demos Effets visuels, ${DUREE}s chacune, en boucle (Ctrl+C pour arreter)"

while true; do
    i=1
    for demo in "${DEMOS[@]}"; do
        run_demo "$demo" "$i"
        i=$((i + 1))
    done
done
