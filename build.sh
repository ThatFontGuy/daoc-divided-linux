#!/usr/bin/env bash
# build.sh - one command that sets up everything and builds the portable server folder.
#
#   ./build.sh              use distrobox if it is installed, otherwise build on this system
#   ./build.sh --box        force distrobox (creates the build box if needed)
#   ./build.sh --local      force building on this system
#   ./build.sh --cross      build on this system with no root and no system compiler needed at all (see below)
#
# Result: dist/daoc-divided/ (the portable server) and dist/daoc-divided-<version>-linux-x64.tar.gz
# Nothing is installed into your system. The box has its own home under ~/boxes/; a local build keeps its caches and a private
# .NET SDK (if you have no .NET 10) in .cache/ inside this folder. (The .NET tools may still drop a 205-byte default
# ~/.nuget/NuGet/NuGet.Config.) The finished server folder never touches your home.
#
# --cross is for a host that can't build --local at all: macOS (can't produce linux-x64 binaries natively), or any
# Linux box with no root to install build-essential/cmake (a real case: the box this project's own server runs on
# can be exactly this). Needs only curl, python3 and xz - no sudo, ever. cmake, ninja and a zig-based cross-compiler
# come from pip wheels (tools/fetch-cross-toolchain.sh, cached in .cache/), targeting this project's own documented
# glibc 2.34 floor; the admin screen's bundled Python has its dependencies resolved via `pip download` for the
# target platform instead of executing the linux-x64 Python directly (tools/fetch-python-cross.sh) - the one thing
# this mode genuinely can't do on a host that can't run linux-x64 binaries at all. The result is identical either
# way: run it on the actual Linux box you'll play on to confirm (see README.md).
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mode="${1:-auto}"

case "$mode" in
  auto)    command -v distrobox >/dev/null && mode=--box || mode=--local ;;
  --box|--local|--cross) ;;
  *) echo "usage: $0 [--box|--local|--cross]" >&2; exit 1 ;;
esac

if [[ $mode == --box ]]; then
  command -v distrobox >/dev/null || { echo "build.sh: distrobox is not installed (https://distrobox.it). Try: $0 --local" >&2; exit 1; }
  echo "== Building inside the distrobox (see tools/setup-build-box.sh)"
  exec "$REPO/tools/setup-build-box.sh" --build
fi

echo "== Building on this system${mode:+ ($mode)}"
# Keep everything the .NET tooling and NuGet write inside this folder, so a local build leaves your home untouched.
ORIG_HOME="$HOME"
export HOME="$REPO/.cache/home" DOTNET_CLI_HOME="$REPO/.cache/dotnet-home" NUGET_PACKAGES="$REPO/.cache/nuget" \
       NUGET_HTTP_CACHE_PATH="$REPO/.cache/nuget-http" XDG_CACHE_HOME="$REPO/.cache/xdg" XDG_DATA_HOME="$REPO/.cache/xdg-data" \
       DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
mkdir -p "$HOME" "$DOTNET_CLI_HOME" "$NUGET_PACKAGES" "$NUGET_HTTP_CACHE_PATH" "$XDG_CACHE_HOME" "$XDG_DATA_HOME"
missing=()
if [[ $mode == --cross ]]; then
  for c in curl python3 xz; do command -v "$c" >/dev/null || missing+=("$c"); done
else
  for c in cmake g++ make curl python3 xz; do command -v "$c" >/dev/null || missing+=("$c"); done
fi
if ((${#missing[@]})); then
  echo "build.sh: missing tools: ${missing[*]}" >&2
  if [[ $mode == --cross ]]; then
    echo "  --cross still needs these few (no root/compiler needed otherwise): curl, python3, xz" >&2
  else
    echo "  Debian/Ubuntu: sudo apt install cmake g++ make curl python3 xz-utils libicu-dev" >&2
    echo "  Fedora:        sudo dnf install cmake gcc-c++ make curl python3 xz libicu" >&2
    echo "  Arch:          sudo pacman -S cmake gcc make curl python xz icu" >&2
    echo "  Or use a container instead: $0 --box" >&2
    echo "  Or, with no root at all (including on macOS): $0 --cross" >&2
  fi
  exit 1
fi

DOTNET="${DOTNET:-$(command -v dotnet || true)}"
for candidate in "$ORIG_HOME/.dotnet/dotnet" "$REPO/.cache/dotnet/dotnet"; do
  [[ -n $DOTNET && -x $DOTNET ]] && "$DOTNET" --list-sdks 2>/dev/null | grep -q '^10\.' && break
  DOTNET="$candidate"
done
if ! { [[ -x $DOTNET ]] && "$DOTNET" --list-sdks 2>/dev/null | grep -q '^10\.'; }; then
  echo "== Installing a private .NET 10 SDK into .cache/dotnet (your system is not touched)"
  mkdir -p "$REPO/.cache"
  curl -fsSL https://dot.net/v1/dotnet-install.sh -o "$REPO/.cache/dotnet-install.sh"
  bash "$REPO/.cache/dotnet-install.sh" --channel 10.0 --install-dir "$REPO/.cache/dotnet" >/dev/null
  DOTNET="$REPO/.cache/dotnet/dotnet"
fi
export DOTNET
[[ $mode == --cross ]] && export CROSS_BUILD=1
exec "$REPO/tools/build-release.sh"
