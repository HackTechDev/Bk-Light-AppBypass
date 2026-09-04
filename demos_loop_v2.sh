#!/usr/bin/env bash
# Enchainement fluide des 14 demos "Effets visuels", sans reconnexion BLE
# entre deux demos (connexion persistante geree par demosloop/run.py).
# Version "v1" (demos_loop.sh) relance un process separe par demo et
# reconnecte a chaque fois -- utile si une demo plante, mais avec un trou
# de quelques secondes entre chaque. Celle-ci est fluide mais partage un
# seul process pour toutes les demos.

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ -x "$PROJECT_DIR/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python3"
else
    PYTHON="python3"
fi

exec "$PYTHON" "$PROJECT_DIR/demosloop/run.py"
