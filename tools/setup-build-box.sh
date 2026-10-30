#!/usr/bin/env bash
# Create or repair the Ubuntu 22.04 distrobox used to build this project. Safe to re-run. Run on the host.
#   tools/setup-build-box.sh            only prepare the box
#   tools/setup-build-box.sh --build    prepare it, then build the portable server inside it
# Settings: BOX_NAME (divided-box), BOX_HOME (~/boxes/divided-box-home).
set -euo pipefail
BOX_NAME="${BOX_NAME:-divided-box}"
BOX_HOME="${BOX_HOME:-$HOME/boxes/divided-box-home}"
command -v distrobox >/dev/null || { echo "distrobox is not installed" >&2; exit 1; }
mkdir -p "$BOX_HOME"
if ! distrobox list --no-color | cut -d'|' -f2 | tr -d ' ' | grep -qx "$BOX_NAME"; then
  distrobox create --name "$BOX_NAME" --image docker.io/library/ubuntu:22.04 --home "$BOX_HOME" --yes
fi
distrobox enter "$BOX_NAME" -- bash -lc '
  set -euo pipefail
  need=(); for p in curl ca-certificates libicu70 cmake g++ make git xz-utils python3; do dpkg -s "$p" >/dev/null 2>&1 || need+=("$p"); done
  if ((${#need[@]})); then sudo apt-get update -qq; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${need[@]}" >/dev/null; fi
  if ! "$HOME/.dotnet/dotnet" --list-sdks 2>/dev/null | grep -q "^10\."; then
    curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
    bash /tmp/dotnet-install.sh --channel 10.0 --install-dir "$HOME/.dotnet" >/dev/null
  fi
  echo ".NET: $("$HOME/.dotnet/dotnet" --version)  cmake: $(cmake --version | head -1)"
'

if [[ "${1:-}" == --build ]]; then
  REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  distrobox enter "$BOX_NAME" -- bash -lc "cd '$REPO' && tools/build-release.sh"
fi
