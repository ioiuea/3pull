#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${SCRIPT_DIR}/scripts"

pause() {
  read -r -p "Press Enter to continue..." _ </dev/tty
}

"${SCRIPTS_DIR}/001_create_database.sh"
pause
"${SCRIPTS_DIR}/002_create_schema.sh"
pause
"${SCRIPTS_DIR}/003_roles.sh"
pause
"${SCRIPTS_DIR}/004_search_path.sh"
