#!/usr/bin/env bash
# ghost-splash.sh — animated Kaji ghost mascot (floats, tail ripples, blinks).
# Usage: ghost-splash.sh [loops]   (default 3 loops, ~3s). Falls back to a
# static ghost when not attached to a TTY. Always restores the cursor.

PURPLE=$'\033[38;5;141m'
DIM=$'\033[38;5;60m'
RESET=$'\033[0m'
HIDE=$'\033[?25l'
SHOW=$'\033[?25h'
UP6=$'\033[6A'

# Static fallback (no TTY / piped): print once and exit.
static_ghost() {
  printf '%s\n' \
"${PURPLE} .-~~~~~~~~~-." \
"${PURPLE}|  (o)   (o)  |" \
"${PURPLE}|     >_      |" \
"${PURPLE} \`~-^-^-^-^-~\`${RESET}"
}

if [[ ! -t 1 ]]; then
  static_ghost
  exit 0
fi

LOOPS="${1:-3}"

# Build one 6-line frame. Args: float(0=high,1=low) eyes(o|-) cursor(0|1) tail(1|2|3)
draw() {
  local fl=$1 eyes=$2 cur=$3 tail=$4
  local E M T
  if [[ $eyes == "-" ]]; then E='(-)   (-)'; else E='(o)   (o)'; fi
  if [[ $cur == 1 ]]; then M='>_'; else M='> '; fi
  case $tail in
    1) T='~-^-^-^-^-~';;
    2) T='^-~-^-~-^-~';;
    3) T='-^-^-^-^-^-';;
  esac
  local g1=" .-~~~~~~~~~-."
  local g2="|  ${E}  |"
  local g3="|     ${M}      |"
  local g4=" \`${T}\`"
  # 6 lines total; float shifts the ghost down by one line.
  if [[ $fl == 0 ]]; then
    printf '%s\033[K\n' "${PURPLE}${g1}"
    printf '%s\033[K\n' "${PURPLE}${g2}"
    printf '%s\033[K\n' "${PURPLE}${g3}"
    printf '%s\033[K\n' "${PURPLE}${g4}${RESET}"
    printf '\033[K\n'
    printf '\033[K\n'
  else
    printf '\033[K\n'
    printf '%s\033[K\n' "${PURPLE}${g1}"
    printf '%s\033[K\n' "${PURPLE}${g2}"
    printf '%s\033[K\n' "${PURPLE}${g3}"
    printf '%s\033[K\n' "${PURPLE}${g4}${RESET}"
    printf '\033[K\n'
  fi
}

# Frame script: float eyes cursor tail
FRAMES=(
  "0 o 1 1"
  "0 o 0 2"
  "1 o 1 3"
  "1 o 0 1"
  "0 o 1 2"
  "0 - 0 3"
  "1 o 1 1"
  "1 o 0 2"
)

cleanup() { printf '%s' "$SHOW"; }
trap cleanup EXIT INT TERM

printf '%s' "$HIDE"
# Reserve 6 lines, then redraw in place each frame.
printf '\n\n\n\n\n\n'
printf '%s' "$UP6"
for ((l=0; l<LOOPS; l++)); do
  for f in "${FRAMES[@]}"; do
    draw $f
    printf '%s' "$UP6"
    sleep 0.12
  done
done
# Settle on a clean final frame (eyes open, cursor on).
draw 0 o 1 1
printf '%s' "$SHOW"
