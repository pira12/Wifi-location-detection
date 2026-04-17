#!/usr/bin/env bash
# Shared helpers sourced by the other scripts.

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
RESET=$'\033[0m'

info() { printf '%s[*] %s%s\n' "$GREEN" "$*" "$RESET"; }
warn() { printf '%s[!] %s%s\n' "$YELLOW" "$*" "$RESET" >&2; }
die()  { printf '%s[x] %s%s\n' "$RED" "$*" "$RESET" >&2; exit 1; }

require_root() {
    if [[ $EUID -ne 0 ]]; then
        die "This script needs root. Re-run with sudo."
    fi
}
