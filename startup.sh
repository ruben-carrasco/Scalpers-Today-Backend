#!/bin/bash
set -euo pipefail

# Backward-compatible wrapper: keeps Azure startup command stable.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/scripts/startup.sh" "$@"
