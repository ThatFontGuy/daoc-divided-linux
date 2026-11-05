#!/usr/bin/env bash
# build-release.sh - build the portable Linux server folder and tarball.
#
#   tools/build-release.sh            -> dist/daoc-divided/ and dist/daoc-divided-<version>-linux-x64.tar.gz
#
# Needs the .NET 10 SDK, cmake, g++, curl and python3 (the build box has them). The result needs none of them:
# it bundles the .NET runtime and a Python for the admin screen, and links the pathing library's C++ runtime
# statically. World DB, navmeshes and the quest data files are DividedRealms' own, read out of its release zip by
# tools/fetch-divided-release.py (cached in .cache/). No client files are included.
#
# CROSS_BUILD=1 (set by `build.sh --cross`) builds on a host with no system cmake/g++ and no root to install
# them - macOS, or a Linux box with no sudo access (confirmed real need: the box this project's own server runs
# on). Needs only curl, python3 and the .NET 10 SDK (installed the same way --local already does); cmake, ninja
# and a zig-based cross-compiler come from pip wheels (tools/fetch-cross-toolchain.sh), and the bundled Python's
# dependencies are resolved without executing the target's own linux-x64 binary (tools/fetch-python-cross.sh).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO/source/server"
DOTNET="${DOTNET:-$(command -v dotnet || echo "$HOME/.dotnet/dotnet")}"
VERSION="${VERSION:-$(git -C "$REPO" describe --tags --always 2>/dev/null || echo dev)}"
RELEASE_TAG="${RELEASE_TAG:-DR-dev-0.1a}"   # DividedRealms release the world data comes from
OUT="$REPO/dist/daoc-divided"
CROSS_BUILD="${CROSS_BUILD:-0}"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1

missing=()
[[ -x $DOTNET ]] && "$DOTNET" --list-sdks 2>/dev/null | grep -q '^10\.' || missing+=(".NET 10 SDK")
if [[ $CROSS_BUILD == 1 ]]; then
  for c in curl python3; do command -v $c >/dev/null || missing+=("$c"); done
else
  for c in cmake g++ curl python3; do command -v $c >/dev/null || missing+=("$c"); done
fi
if ((${#missing[@]})); then
  echo "build-release: missing: ${missing[*]} (run tools/setup-build-box.sh on the host, or build.sh --cross)" >&2
  exit 1
fi

[[ -f $SRC/CoreServer/config/serverconfig.xml ]] ||
  cp "$SRC/CoreServer/config/serverconfig.example.xml" "$SRC/CoreServer/config/serverconfig.xml"

echo "== World data from DividedRealms $RELEASE_TAG"
python3 -I "$REPO/tools/fetch-divided-release.py" "$RELEASE_TAG" "$REPO/.cache/divided"
DATA="$REPO/.cache/divided/$RELEASE_TAG"

# Rebuild the program files only. If someone plays straight from dist/daoc-divided, their world, characters and settings
# (data/, config/, logs/, run/, backups/, editor-data/) must survive a rebuild, and must never end up in the tarball.
KEEP=(data config logs run backups editor-data)
if [[ -d $OUT ]]; then
  for entry in "$OUT"/* "$OUT"/.[!.]*; do
    [[ -e $entry ]] || continue
    name=$(basename "$entry")
    [[ " ${KEEP[*]} " == *" $name "* ]] || rm -rf "$entry"
  done
fi
echo "== Publishing server (self-contained linux-x64)"
"$DOTNET" publish "$SRC/CoreServer/CoreServer.csproj" -c Release -r linux-x64 --self-contained true \
  -o "$OUT/bin" -nologo -v quiet -clp:ErrorsOnly

echo "== Publishing daoc-admin (command line)"
"$DOTNET" publish "$SRC/DaocAdmin/DaocAdmin.csproj" -c Release -r linux-x64 --self-contained true \
  -o "$OUT/bin" -nologo -v quiet -clp:ErrorsOnly

echo "== Building native pathing library"
rm -rf "$SRC/Pathing/Detour/build"
if [[ $CROSS_BUILD == 1 ]]; then
  IFS='|' read -r CMAKE_BIN NINJA_BIN TOOLCHAIN < <(
    "$REPO/tools/fetch-cross-toolchain.sh" "$REPO/.cache/cross-toolchain" | tail -1)
else
  CMAKE_BIN=cmake
fi
CMAKE_EXTRA_ARGS=()
[[ $CROSS_BUILD == 1 ]] && CMAKE_EXTRA_ARGS=(-G Ninja -DCMAKE_MAKE_PROGRAM="$NINJA_BIN" -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN")
"$CMAKE_BIN" -S "$SRC/Pathing/Detour" -B "$SRC/Pathing/Detour/build" -DCMAKE_BUILD_TYPE=Release "${CMAKE_EXTRA_ARGS[@]}" >/dev/null
"$CMAKE_BIN" --build "$SRC/Pathing/Detour/build" >/dev/null
mkdir -p "$OUT/bin/lib"
# LibraryImport("lib/Detour") has a folder in its name, so .NET on Linux probes lib/Detour.so.
cp -L "$SRC/Pathing/Detour/build/libDetour.so" "$OUT/bin/lib/Detour.so"

# A post-build step copies translations into source/server/Release/ only; publish needs them too.
(cd "$SRC/GameServer/language" && find . -name '*.txt' -print0 | while IFS= read -r -d '' f; do
  mkdir -p "$OUT/bin/languages/$(dirname "$f")"
  cp -p "$f" "$OUT/bin/languages/$f"
done)

# Quest/marker data DividedRealms ships next to the server program (the server runs without them, with markers off).
cp "$DATA"/server-data/*.json "$OUT/bin/"

echo "== World"
mkdir -p "$OUT/defaults"
cp "$DATA/world.sqlite" "$OUT/defaults/world.sqlite"
mkdir -p "$OUT/world-updates" && cp "$REPO"/source/tools/release-baselines/modern/world-updates/* "$OUT/world-updates/"   # the steps in git match the server code; the zip supplies the world and navmeshes

# The server reads config/ next to its program and navmesh/ from its working directory (bin/).
rm -rf "$OUT/bin/config"
ln -s ../config "$OUT/bin/config"
ln -s ../navmesh "$OUT/bin/navmesh"
ln -s ../logs "$OUT/bin/logs"

cp "$REPO/deploy/serverconfig.template.xml" "$OUT/defaults/serverconfig.xml"
cp "$SRC/GameServer/config/logconfig.xml" "$SRC/GameServer/config/invalidnames.txt" "$OUT/defaults/"
cp "$REPO/deploy/MailConfig.xml" "$OUT/defaults/"   # DividedRealms ships it (mail off); the server reads ./config/MailConfig.xml
cp "$REPO/deploy/daoc-server.sh" "$REPO/deploy/daoc-admin" "$REPO/deploy/release.conf" "$OUT/"
cp "$REPO/deploy/README-release.md" "$OUT/README.md"
echo "$VERSION (DividedRealms $RELEASE_TAG)" > "$OUT/VERSION"

echo "== Admin screen (bundled Python + Textual)"
if [[ $CROSS_BUILD == 1 ]]; then
  "$REPO/tools/fetch-python-cross.sh" "$OUT/python" "$REPO"
else
  "$REPO/tools/fetch-python.sh" "$OUT/python"
fi
mkdir -p "$OUT/tui"
cp "$REPO/tui/daoc_admin_tui.py" "$REPO/tui/client_tools.py" "$OUT/tui/"
mkdir -p "$OUT/tui/classslots" "$OUT/tools"
cp "$REPO/tools/world_update.py" "$OUT/tools/"
cp "$SRC/../tools/classslots/patch_class_slots.py" "$OUT/tui/classslots/"
cp "$DATA/tools/connect-local1130.exe" "$OUT/tools/"
cp "$REPO/deploy/zones-classic.mpk" "$OUT/tools/"   # the classic zone table the Battleground fix puts in the client

echo "== World Workshop editor (runs on the bundled Python)"
mkdir -p "$OUT/editor/source/tools" "$OUT/editor/source/new-client"
cp -r "$SRC/../tools/world_editor" "$OUT/editor/source/tools/"
cp "$SRC/../tools/modern_world_overlay.py" "$OUT/editor/source/tools/"
cp -r "$SRC/../new-client/pipeline" "$OUT/editor/source/new-client/"   # the editor's client-reading modules (daoc_mpk, NIF readers...)
mkdir -p "$OUT/editor/tools" "$OUT/editor/source/server/GameServer/craft"
cp -r "$REPO/tools/asset-tool" "$OUT/editor/tools/"
cp -r "$SRC/GameServer/Enums" "$OUT/editor/source/server/GameServer/"            # item-column names the editor reads
cp "$SRC/GameServer/craft/CraftingMgr.cs" "$OUT/editor/source/server/GameServer/craft/"
rm -rf "$OUT/editor/source/tools/world_editor"/{build_package.py,patch_launcher_button.py,test_editor.py,__pycache__}
cp "$REPO/deploy/world-editor.sh" "$OUT/"

echo "== Navmeshes"
mkdir -p "$OUT/navmesh"
cp -r "$DATA"/navmesh/. "$OUT/navmesh/"

tarball="$REPO/dist/daoc-divided-$VERSION-linux-x64.tar.gz"
tar -C "$REPO/dist" "${KEEP[@]/#/--exclude=daoc-divided/}" -czf "$tarball" daoc-divided
# Keep only the newest tarball: each build is ~1 GB and they pile up in dist/.
find "$REPO/dist" -maxdepth 1 -name 'daoc-divided-*-linux-x64.tar.gz' ! -path "$tarball" -delete
echo "== Done: $OUT"
echo "         $tarball ($(du -h "$tarball" | cut -f1))"
