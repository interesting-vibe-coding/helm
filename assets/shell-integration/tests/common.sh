#!/usr/bin/env bash

set -euo pipefail

create_stub_vendor_dir() {
  local root="$1"
  mkdir -p \
    "$root/fast-syntax-highlighting" \
    "$root/zsh-autosuggestions" \
    "$root/zsh-completions" \
    "$root/zsh-z"
}
